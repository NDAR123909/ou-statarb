"""
LTP Liquidity Arena competition agent: OU pairs trading on crypto perps.

This is the statarb pipeline pointed at the contest's 50-symbol Binance-perp
whitelist, on hourly bars. Nothing about the math changes — select_pairs
(FDR + split-half stability), fit_spread_model, and cost-aware optimal_bands
are imported from the package — only the clock (hours, not days) and the
venue (RapidX simulation, hedge mode, 1,000 USDT) are new.

Competition rules this agent treats as hard invariants:
  - equity < 800 USDT (NAV < 0.8) means ELIMINATION. The kill switch here
    flattens everything at 12% from peak and refuses to trade again — peak
    starts at 1,000, so it always fires at >= 880, above the 800 floor. The
    process keeps running after a halt: a dead agent can't de-risk, and the
    ledger keeps recording. (The old >=90% uptime elimination rule was
    removed from the official rules, 2026-07.)
  - 1 order write per 5 seconds (enforced inside RapidXBroker).
  - Automation consent must come from the human operator, verbatim, via
    LTP_AUTOMATION_CONSENT_TEXT. The agent will not invent it.

Known modeling gaps, deliberately accepted for Phase 1 and logged for the
post-mortem: perp funding-rate carry is not modeled (both legs pay/receive
funding and the net is usually small at these horizons but nonzero); fees
are assumed taker at 5 bps until userFeeRate says otherwise.

Run:  python deploy/ltp_agent.py            (needs LTP_* env + rapidx CLI)
      python deploy/ltp_agent.py --dry-run  (no orders, prints intents)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from statarb.selection import SelectionConfig, select_pairs          # noqa: E402
from statarb.ou import fit_spread_model                              # noqa: E402
from statarb.thresholds import optimal_bands                         # noqa: E402
from deploy.ltp_broker import RapidXBroker, RapidXError              # noqa: E402
from deploy.ltp_news import NewsSentinel                             # noqa: E402
from deploy.ltp_stream import NewsStream                             # noqa: E402


def base_asset(symbol: str) -> str:
    """BINANCE_PERP_XAUT_USDT -> XAUT"""
    return symbol.split("_")[2]

# Sector-restricted candidates from the contest whitelist. Same philosophy as
# the equity book: the economic grouping IS the multiple-testing correction.
# One ticker, one pair (absolute position tracking would otherwise collide).
# The gold pair is the strongest link — two tokenized claims on vault metal;
# the rest are narrative sectors that the gate must confirm before trading.
CANDIDATES = [
    ("BINANCE_PERP_XAUT_USDT", "BINANCE_PERP_PAXG_USDT"),    # tokenized gold
    ("BINANCE_PERP_XMR_USDT", "BINANCE_PERP_ZEC_USDT"),      # privacy coins
    ("BINANCE_PERP_LTC_USDT", "BINANCE_PERP_BCH_USDT"),      # bitcoin forks
    ("BINANCE_PERP_XRP_USDT", "BINANCE_PERP_XLM_USDT"),      # payment networks
    ("BINANCE_PERP_BTC_USDT", "BINANCE_PERP_ETH_USDT"),      # majors
    ("BINANCE_PERP_SOL_USDT", "BINANCE_PERP_AVAX_USDT"),     # high-perf L1s
    ("BINANCE_PERP_ADA_USDT", "BINANCE_PERP_DOT_USDT"),      # 2017-era L1s
    ("BINANCE_PERP_NEAR_USDT", "BINANCE_PERP_ICP_USDT"),     # compute platforms
    ("BINANCE_PERP_HBAR_USDT", "BINANCE_PERP_ALGO_USDT"),    # enterprise L1s
    ("BINANCE_PERP_DOGE_USDT", "BINANCE_PERP_1000SHIB_USDT"),# memecoins
    ("BINANCE_PERP_UNI_USDT", "BINANCE_PERP_AAVE_USDT"),     # DeFi blue chips
    ("BINANCE_PERP_TAO_USDT", "BINANCE_PERP_RENDER_USDT"),   # AI/compute
    ("BINANCE_PERP_LINK_USDT", "BINANCE_PERP_QNT_USDT"),     # middleware
    ("BINANCE_PERP_ETC_USDT", "BINANCE_PERP_KAS_USDT"),      # proof-of-work
]


@dataclass
class AgentConfig:
    interval: str = "1h"
    bars_per_year: int = 24 * 365
    lookback_bars: int = 960          # ~40 days of hourly bars
    refit_every_bars: int = 24        # re-run selection daily
    min_half_life: float = 6.0        # bars (hours): faster is microstructure
    max_half_life: float = 168.0      # one week; slower won't cycle in Phase 1
    fdr_q: float = 0.10
    # Hedge-ratio band, widened from the equity default (0.25/4.0). Crypto
    # pairs have far wider volatility ratios than paired equities, so a
    # genuinely cointegrated spread can carry a beta outside the tighter
    # equity band. Widened after live data showed it rejecting ETC/KAS
    # (beta 0.218, stable across halves, ADF p=0.005) purely on the floor.
    # See LTP_STRATEGY.md 2026-07-18. The cointegration/stability/Hurst
    # gates are untouched — this only fixes an asset-class mismatch.
    min_abs_beta: float = 0.20
    max_abs_beta: float = 5.0
    taker_fee: float = 5e-4           # 5 bps per leg per trade, until measured
    stop_z: float = 3.5
    max_hold_mult: float = 3.0
    risk_per_pair: float = 0.004      # 40 bps of NAV per bar of spread vol
    max_pairs: int = 4
    max_gross_mult: float = 2.0       # gross notional cap, x NAV
    per_leg_cap_mult: float = 0.5     # single leg cap, x NAV
    dd_halt: float = 0.12             # flatten + halt at 12% off peak; the
                                      # contest eliminates at equity < 800U,
                                      # so this always fires first (>= 880)
    state_path: str = "deploy/ltp_state.json"


def log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}",
          flush=True)


_LEDGER_PATH = "deploy/ltp_ledger.jsonl"


def ledger(event: str, **fields) -> None:
    """Append one decision record. Every enter/exit/stop/skip lands here with
    enough context that the phase-1 post-mortem is a pandas one-liner:
    pd.read_json('deploy/ltp_ledger.jsonl', lines=True)."""
    rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "event": event, **fields}
    with open(_LEDGER_PATH, "a") as f:
        f.write(json.dumps(rec, default=float) + "\n")


def ledger_operation(op: dict) -> None:
    """Broker callback: log one order/trade operation with its final result.
    Track A requires every place/cancel/close to appear in the log tied to
    the Agent's reasoning. The `decision`/`pair` fields come from the
    broker's op_context, set at each decision site, so operations chain back
    to the decision that caused them."""
    ledger("operation", **op)


# ---------------------------------------------------------------- state io --
def load_state(path: str) -> dict:
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return {"peak_equity": 0.0, "halted": False, "pairs": {}, "bar": 0}


def save_state(path: str, state: dict) -> None:
    Path(path).write_text(json.dumps(state, indent=2, default=float))


# ------------------------------------------------------------------- fitting --
def fetch_panel(broker: RapidXBroker, symbols: list[str],
                cfg: AgentConfig) -> pd.DataFrame:
    frames = {}
    for s in symbols:
        df = broker.klines(s, cfg.interval, cfg.lookback_bars)
        if len(df) >= cfg.lookback_bars // 2:
            frames[s] = df["close"]
        else:
            log(f"  data: {s} has {len(df)} bars, excluded this refit")
    if not frames:
        return pd.DataFrame()
    panel = pd.DataFrame(frames).dropna()
    return np.log(panel)


def refit(broker: RapidXBroker, cfg: AgentConfig, state: dict) -> None:
    """Weekly-refit equivalent: selection + OU fit + cost-aware bands."""
    symbols = sorted({t for p in CANDIDATES for t in p})
    logp = fetch_panel(broker, symbols, cfg)
    if logp.empty:
        log("refit: no data panel, keeping previous fits")
        return

    usable = [(a, b) for a, b in CANDIDATES
              if a in logp.columns and b in logp.columns]
    sel_cfg = SelectionConfig(
        fdr_q=cfg.fdr_q,
        min_half_life=cfg.min_half_life,
        max_half_life=cfg.max_half_life,
        periods_per_year=cfg.bars_per_year,
        min_crossings_per_year=8.0 * (cfg.bars_per_year / 252),  # same density
        min_abs_beta=cfg.min_abs_beta,
        max_abs_beta=cfg.max_abs_beta,
    )
    table = select_pairs(logp, candidates=usable, cfg=sel_cfg)
    passed = table[table.passed]
    log(f"refit: {len(passed)}/{len(table)} candidates pass the gate")
    if len(passed) < len(table):
        # Why the rest were rejected — surfaced in the live logs so a quiet
        # day is legible (genuine no-cointegration vs a tunable mismatch).
        reasons = table.loc[~table.passed, "reject_reason"].value_counts()
        log(f"refit: rejects {reasons.to_dict()}")

    fits = {}
    for _, row in passed.iterrows():
        a, b = row.a, row.b
        m = fit_spread_model(logp[a].values, logp[b].values)
        roundtrip = 2.0 * cfg.taker_fee * (1.0 + abs(m.beta))
        bands = optimal_bands(m.ou, roundtrip)
        if not bands.tradeable:
            log(f"  {a.split('_')[2]}/{b.split('_')[2]}: costs eat the edge, skipped")
            continue
        spread = logp[a].values - m.beta * logp[b].values
        fits[f"{a}|{b}"] = {
            "a": a, "b": b, "beta": m.beta,
            "half_life": m.ou.half_life,
            "mu": float(np.mean(spread[-int(3 * m.ou.half_life):])),
            "sigma": float(np.std(spread[-int(max(3 * m.ou.half_life, 24)):],
                                  ddof=1)),
            "entry_z": bands.entry_z, "exit_z": bands.exit_z,
            "dvol": float(np.std(np.diff(spread), ddof=1)),
        }

    # keep the fastest-reverting max_pairs; preserve live trade state
    keep = sorted(fits.values(), key=lambda f: f["half_life"])[: cfg.max_pairs]
    keep_keys = {f"{f['a']}|{f['b']}" for f in keep}
    old = state["pairs"]
    state["pairs"] = {
        k: {**fits[k],
            "hold": old.get(k, {}).get("hold", 0),
            "blocked": old.get(k, {}).get("blocked", 0),
            "side": old.get(k, {}).get("side", 0)}
        for k in keep_keys
    }
    # anything dropped by the refit gets flattened by the trade step
    for k, v in old.items():
        if k not in keep_keys and v.get("side", 0) != 0:
            state["pairs"][k] = {**v, "flatten": True}
    log(f"refit: active {sorted(k.replace('BINANCE_PERP_', '').replace('_USDT', '') for k in keep_keys)}")
    ledger("refit", passed=int(len(passed)), tested=int(len(table)),
           active=sorted(keep_keys),
           bands={k: {"entry_z": f["entry_z"], "exit_z": f["exit_z"],
                      "half_life": f["half_life"]} for k, f in fits.items()})


# ------------------------------------------------------------------ trading --
def leg_close(broker: RapidXBroker, pair: dict, nav: float,
              dry: bool, decision: str = "close") -> None:
    broker.op_context = {"decision": decision,
                         "pair": f"{base_asset(pair['a'])}/{base_asset(pair['b'])}"}
    for sym, pos_side in ((pair["a"], "LONG" if pair["side"] > 0 else "SHORT"),
                          (pair["b"], "SHORT" if pair["side"] > 0 else "LONG")):
        if dry:
            log(f"  DRY: close {sym} {pos_side}")
            continue
        broker.close_position(sym, pos_side, max_notional=2 * nav)
    broker.op_context = {}
    pair["side"], pair["hold"] = 0, 0


def flatten_everything(broker: RapidXBroker, state: dict, nav: float,
                       dry: bool) -> None:
    if dry:
        log("  DRY: cancel-all")
    else:
        broker.op_context = {"decision": "kill_switch", "pair": "*"}
        # cancel-all is best-effort: closing positions is what protects the
        # account, so a cancel failure must not block the leg closes below.
        try:
            broker.cancel_all()
        except RapidXError as exc:
            log(f"  cancel-all failed (closing positions anyway): {exc}")
        broker.op_context = {}
    for pair in state["pairs"].values():
        if pair.get("side", 0) != 0:
            leg_close(broker, pair, nav, dry, decision="kill_switch")


def derisk(broker: RapidXBroker, cfg: AgentConfig, state: dict,
           critical_assets: set[str], dry: bool) -> None:
    """Flatten open positions with a leg rated critical by streaming news.

    This is the only action the streaming path can take, and it is strictly
    risk-reducing: close and step aside. Re-entry stays blocked by the
    sentinel verdicts until the news picture clears at a later refresh."""
    if not critical_assets or state["halted"]:
        return
    nav = broker.equity_usdt()
    for key, pair in list(state["pairs"].items()):
        if pair.get("side", 0) == 0:
            continue
        hit = {base_asset(pair["a"]), base_asset(pair["b"])} & critical_assets
        if not hit:
            continue
        short_name = f"{base_asset(pair['a'])}/{base_asset(pair['b'])}"
        log(f"  {short_name}: NEWS DE-RISK — {sorted(hit)} rated critical, "
            f"flattening within seconds of the headline")
        ledger("news_derisk", pair=short_name, assets=sorted(hit), nav=nav,
               dry=dry,
               reasoning=(f"Streaming news rated {', '.join(sorted(hit))} "
                          f"critical while a position was open. Mean reversion "
                          f"presumes the historical relationship holds; a "
                          f"structural event invalidates that premise, so the "
                          f"position is flattened immediately rather than at "
                          f"the next hourly bar, and re-entry stays blocked "
                          f"while the verdict stands."))
        try:
            leg_close(broker, pair, nav, dry, decision="news_derisk")
        except RapidXError as exc:
            log(f"  {short_name}: de-risk close failed ({exc}); retrying "
                f"at next bar")


def trade_step(broker: RapidXBroker, cfg: AgentConfig, state: dict,
               dry: bool, sentinel: NewsSentinel | None = None) -> None:
    nav = broker.equity_usdt()

    # A bad equity read must never be mistaken for a drawdown. A funded
    # account cannot legitimately read <= 0, and a market-neutral,
    # leverage-capped book cannot halve in a single bar — the kill switch
    # trips gradually at 88% of peak, far above this 50% floor, so a real
    # drawdown is never masked here. An implausibly low nav is a failed or
    # partial overview read (a defunded/transitioning account, a transient
    # API glitch): skip the bar without polluting the peak or firing the
    # kill switch, and retry next bar. (Without this, a one-off nav=0 read
    # computes a 100% drawdown and flattens the book on phantom losses.)
    if nav <= 0 or (state["peak_equity"] > 0
                    and nav < 0.5 * state["peak_equity"]):
        log(f"  implausible equity read (nav={nav:.2f} vs peak "
            f"{state['peak_equity']:.2f}); treating as a bad read, skipping bar")
        ledger("bad_read", nav=nav, peak=state["peak_equity"])
        return

    state["peak_equity"] = max(state["peak_equity"], nav)
    dd = 1.0 - nav / state["peak_equity"] if state["peak_equity"] > 0 else 0.0

    if state["halted"]:
        # Halt has latched: never open new risk again. Keep RE-attempting the
        # flatten each bar until the book is actually flat — a de-risk retry,
        # not just monitoring — so a flatten that failed mid-way completes.
        log(f"halted (kill switch); equity {nav:.2f} — de-risking, monitoring only")
        try:
            flatten_everything(broker, state, nav, dry)
        except RapidXError as exc:
            log(f"  halted de-risk retry failed (will retry next bar): {exc}")
        return
    if dd >= cfg.dd_halt:
        log(f"KILL SWITCH: drawdown {dd:.1%} >= {cfg.dd_halt:.0%} — "
            f"flattening everything and halting (contest eliminates at 800U)")
        ledger("kill_switch", nav=nav, peak=state["peak_equity"], drawdown=dd)
        # Latch the halt BEFORE flattening, so even if the flatten cannot
        # complete (API hiccup), we never open new risk and the halted branch
        # above retries the flatten on subsequent bars.
        state["halted"] = True
        try:
            flatten_everything(broker, state, nav, dry)
        except RapidXError as exc:
            log(f"  kill-switch flatten failed (will retry while halted): {exc}")
        return

    gross = 0.0
    prices: dict[str, float] = {}
    for key, pair in list(state["pairs"].items()):
        a, b = pair["a"], pair["b"]
        try:
            prices[a] = prices.get(a) or broker.mark_price(a)
            prices[b] = prices.get(b) or broker.mark_price(b)
        except (RapidXError, KeyError) as exc:  # data hiccup: skip this bar
            log(f"  {key}: no mark price ({exc}), skipping bar")
            continue
        if pair.get("side", 0) != 0:
            gross += (1 + abs(pair["beta"])) * pair.get("notional", 0.0)

    for key, pair in list(state["pairs"].items()):
        a, b = pair["a"], pair["b"]
        if a not in prices or b not in prices:
            continue
        spread = np.log(prices[a]) - pair["beta"] * np.log(prices[b])
        if pair["sigma"] <= 0:
            continue
        z = (spread - pair["mu"]) / pair["sigma"]
        short_name = f"{a.split('_')[2]}/{b.split('_')[2]}"

        # heal the post-stop one-sided block once z is back inside the band
        if pair.get("blocked", 0) == +1 and z > -pair["entry_z"]:
            pair["blocked"] = 0
        elif pair.get("blocked", 0) == -1 and z < pair["entry_z"]:
            pair["blocked"] = 0

        if pair.get("flatten") and pair.get("side", 0) != 0:
            log(f"  {short_name}: dropped by refit, flattening")
            leg_close(broker, pair, nav, dry)
            del state["pairs"][key]
            continue

        side = pair.get("side", 0)
        if side == 0:
            # No entries beyond the stop: past stop_z the working hypothesis
            # is 'relationship broke', and buying it there just schedules an
            # immediate stop-out with two round trips of fees.
            want = 0
            if pair["entry_z"] < z < cfg.stop_z and pair.get("blocked", 0) != -1:
                want = -1
            elif -cfg.stop_z < z < -pair["entry_z"] and pair.get("blocked", 0) != +1:
                want = +1
            if want == 0:
                continue
            g = cfg.risk_per_pair * nav / max(pair["dvol"], 1e-9)
            g = min(g, cfg.per_leg_cap_mult * nav)
            if sentinel is not None:
                mult = sentinel.size_mult(base_asset(a), base_asset(b))
                if mult < 1.0:
                    log(f"  {short_name}: news 'watch' rating, sizing x{mult}")
                g *= mult
            add = (1 + abs(pair["beta"])) * g
            if gross + add > cfg.max_gross_mult * nav:
                log(f"  {short_name}: entry skipped, gross cap")
                ledger("skip", pair=short_name, reason="gross_cap", z=z,
                       gross=gross, add=add, nav=nav)
                continue
            qa = broker.round_qty(a, g / prices[a])
            qb = broker.round_qty(b, abs(pair["beta"]) * g / prices[b])
            if (qa <= 0 or qb <= 0
                    or not broker.meets_min_notional(a, qa, prices[a])
                    or not broker.meets_min_notional(b, qb, prices[b])):
                log(f"  {short_name}: below min notional at NAV {nav:.0f}, skipped")
                ledger("skip", pair=short_name, reason="min_notional", z=z,
                       qa=qa, qb=qb, nav=nav)
                continue
            news_note = sentinel.note(base_asset(a), base_asset(b)) if sentinel \
                else "news sentinel disabled"
            if sentinel is not None:
                rationale = sentinel.veto(base_asset(a), base_asset(b))
                if rationale:
                    log(f"  {short_name}: NEWS VETO — {rationale}")
                    ledger("skip", pair=short_name, reason="news_veto", z=z,
                           news=rationale, nav=nav,
                           reasoning=(f"Quantitative entry signal was live "
                                      f"(z={z:+.2f} beyond band {pair['entry_z']:.2f}) "
                                      f"but the news sentinel rated a leg critical: "
                                      f"{rationale}. Mean reversion presumes the "
                                      f"historical relationship holds; a structural "
                                      f"event invalidates that premise, so no entry."))
                    continue
            ts = int(time.time())
            log(f"  {short_name}: ENTER {'long' if want > 0 else 'short'} spread "
                f"z={z:+.2f} g={g:.1f} USDT")
            ledger("enter", pair=short_name, side=want, z=z, g=g,
                   qa=qa, qb=qb, price_a=prices[a], price_b=prices[b],
                   beta=pair["beta"], entry_z=pair["entry_z"],
                   half_life=pair["half_life"], nav=nav, dry=dry,
                   reasoning=(f"Spread z={z:+.2f} crossed the cost-aware optimal "
                              f"entry band ±{pair['entry_z']:.2f} (fitted OU "
                              f"half-life {pair['half_life']:.0f}h; band maximizes "
                              f"expected profit per hour net of fees via first-"
                              f"passage times). {'Buying' if want > 0 else 'Selling'} "
                              f"the spread: risk-budgeted {g:.0f} USDT against "
                              f"hedge ratio beta={pair['beta']:.2f}. Pair passed "
                              f"FDR-corrected cointegration + split-half stability "
                              f"at the last refit. {news_note}."))
            if not dry:
                broker.op_context = {"decision": "enter", "pair": short_name}
                broker.place_market(a, "BUY" if want > 0 else "SELL",
                                    "LONG" if want > 0 else "SHORT",
                                    qa, max_notional=1.1 * g,
                                    client_order_id=f"ou-{ts}-a")
                broker.place_market(b, "SELL" if want > 0 else "BUY",
                                    "SHORT" if want > 0 else "LONG",
                                    qb, max_notional=1.1 * abs(pair["beta"]) * g,
                                    client_order_id=f"ou-{ts}-b")
                broker.op_context = {}
            pair["side"], pair["hold"] = want, 0
            pair["notional"] = g
            gross += add
        else:
            pair["hold"] = pair.get("hold", 0) + 1
            stopped = (side > 0 and z < -cfg.stop_z) or \
                      (side < 0 and z > cfg.stop_z)
            stale = pair["hold"] >= cfg.max_hold_mult * pair["half_life"]
            reverted = abs(z) < pair["exit_z"]
            if stopped:
                log(f"  {short_name}: Z-STOP z={z:+.2f}, closing + blocking side")
                ledger("stop", pair=short_name, side=side, z=z,
                       hold_bars=pair["hold"], price_a=prices[a],
                       price_b=prices[b], nav=nav, dry=dry,
                       reasoning=(f"Spread blew past the structural-break stop "
                                  f"(z={z:+.2f} vs stop {cfg.stop_z}). The working "
                                  f"hypothesis flips from 'temporarily stretched' "
                                  f"to 'relationship broke'; position cut and this "
                                  f"side blocked until z heals inside the entry "
                                  f"band — never average into a broken spring."))
                leg_close(broker, pair, nav, dry, decision="stop")
                pair["blocked"] = +1 if side > 0 else -1
            elif reverted or stale:
                why = "reverted" if reverted else "max_hold"
                log(f"  {short_name}: EXIT z={z:+.2f} ({why})")
                reason_text = (
                    f"Spread reverted inside the exit band (z={z:+.2f} < "
                    f"{pair['exit_z']:.2f}); the mean-reversion cycle completed."
                    if reverted else
                    f"Held {pair['hold']} bars, {cfg.max_hold_mult:.0f}x the "
                    f"fitted half-life of {pair['half_life']:.0f}h, without "
                    f"reverting. The model was wrong about the reversion speed; "
                    f"stop paying carry to find out how wrong.")
                ledger("exit", pair=short_name, side=side, z=z, reason=why,
                       hold_bars=pair["hold"], price_a=prices[a],
                       price_b=prices[b], nav=nav, dry=dry,
                       reasoning=reason_text)
                leg_close(broker, pair, nav, dry, decision=why)


# --------------------------------------------------------------------- main --
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch data and print intents; place no orders")
    ap.add_argument("--once", action="store_true",
                    help="run a single bar then exit (for cron-style hosts)")
    args = ap.parse_args()
    cfg = AgentConfig()
    broker = RapidXBroker(on_operation=ledger_operation)
    state = load_state(cfg.state_path)

    check = broker.self_check()
    if not check.ok:
        log(f"self-check failed: {check.status} {check.message}")
        sys.exit(1)
    log("self-check PASS")

    consent = os.environ.get("LTP_AUTOMATION_CONSENT_TEXT", "").strip()
    session_started = 0.0

    def ensure_session() -> None:
        """(Re)start the 24h automation session before it lapses."""
        nonlocal session_started
        if args.dry_run or time.time() - session_started < 23 * 3600:
            return
        symbols = sorted({t for p in CANDIDATES for t in p})
        # Per-order cap is 1x NAV (1000): the risk-sizing puts ~0.5x NAV of
        # notional on a leg, but the order's safety ceiling is 1.1x that, and
        # the hedge leg of a higher-beta pair scales with beta — so 500 was
        # below the ceiling and blocked legitimate orders (RCLI26005). 1000
        # clears both legs of the selected pairs and still sits under the 2x
        # leverage limit. Total stays 4000 as a coarse net; the strategy's own
        # gross cap (max_gross_mult=2x) is the real total-exposure limiter.
        sid = broker.start_automation(
            symbols, max_per_order="1000", max_total="4000",
            expires_s=24 * 3600, consent_text=consent)
        session_started = time.time()
        log(f"automation session {sid}")

    if not args.dry_run and not consent:
        log("LTP_AUTOMATION_CONSENT_TEXT is not set. Automation consent "
            "must be written by the human operator (see deploy/README_ltp.md); "
            "refusing to trade without it. Use --dry-run to test.")
        sys.exit(1)

    sentinel = NewsSentinel()

    def active_assets() -> list[str]:
        return [base_asset(s) for p in state["pairs"].values()
                for s in (p["a"], p["b"])]

    stream = NewsStream(sentinel, active_assets)
    if stream.start():
        log("news stream: live (sub-minute de-risking armed)")
    else:
        log("news stream: websockets not installed, hourly poll only")
        stream = None

    while True:
        try:
            ensure_session()
            if state["bar"] % cfg.refit_every_bars == 0:
                refit(broker, cfg, state)
            assets = active_assets()
            if assets:
                sentinel.refresh(assets)
            trade_step(broker, cfg, state, args.dry_run, sentinel)
        except RapidXError as exc:
            log(f"bar error (will retry next bar): {exc}")
        state["bar"] += 1
        save_state(cfg.state_path, state)
        if args.once:
            break
        # Sleep to the top of the next hour (the bar close) — but wake
        # instantly if the news stream flags a critical event, de-risk,
        # then resume waiting out the remainder of the bar.
        deadline = time.time() + max(60.0, 3600 - (time.time() % 3600) + 5)
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            if stream is None:
                time.sleep(remaining)
                break
            if stream.urgent.wait(timeout=remaining):
                stream.urgent.clear()
                try:
                    derisk(broker, cfg, state, stream.take_critical(),
                           args.dry_run)
                except RapidXError as exc:
                    log(f"de-risk error (positions retried next bar): {exc}")
                save_state(cfg.state_path, state)


if __name__ == "__main__":
    main()
