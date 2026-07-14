"""
LTP Liquidity Arena competition agent: OU pairs trading on crypto perps.

This is the statarb pipeline pointed at the contest's 50-symbol Binance-perp
whitelist, on hourly bars. Nothing about the math changes — select_pairs
(FDR + split-half stability), fit_spread_model, and cost-aware optimal_bands
are imported from the package — only the clock (hours, not days) and the
venue (RapidX simulation, hedge mode, 1,000 USDT) are new.

Competition rules this agent treats as hard invariants:
  - 20% max drawdown means DISQUALIFICATION. The kill switch here flattens
    everything at 12% from peak and refuses to trade again; the process
    keeps running so the >=90% uptime requirement survives the halt.
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
    taker_fee: float = 5e-4           # 5 bps per leg per trade, until measured
    stop_z: float = 3.5
    max_hold_mult: float = 3.0
    risk_per_pair: float = 0.004      # 40 bps of NAV per bar of spread vol
    max_pairs: int = 4
    max_gross_mult: float = 2.0       # gross notional cap, x NAV
    per_leg_cap_mult: float = 0.5     # single leg cap, x NAV
    dd_halt: float = 0.12             # flatten + halt (contest DQ is 0.20)
    state_path: str = "deploy/ltp_state.json"


def log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}",
          flush=True)


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
    )
    table = select_pairs(logp, candidates=usable, cfg=sel_cfg)
    passed = table[table.passed]
    log(f"refit: {len(passed)}/{len(table)} candidates pass the gate")

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


# ------------------------------------------------------------------ trading --
def leg_close(broker: RapidXBroker, pair: dict, nav: float,
              dry: bool) -> None:
    for sym, pos_side in ((pair["a"], "LONG" if pair["side"] > 0 else "SHORT"),
                          (pair["b"], "SHORT" if pair["side"] > 0 else "LONG")):
        if dry:
            log(f"  DRY: close {sym} {pos_side}")
            continue
        broker.close_position(sym, pos_side, max_notional=2 * nav)
    pair["side"], pair["hold"] = 0, 0


def flatten_everything(broker: RapidXBroker, state: dict, nav: float,
                       dry: bool) -> None:
    broker.cancel_all() if not dry else log("  DRY: cancel-all")
    for pair in state["pairs"].values():
        if pair.get("side", 0) != 0:
            leg_close(broker, pair, nav, dry)


def trade_step(broker: RapidXBroker, cfg: AgentConfig, state: dict,
               dry: bool) -> None:
    nav = broker.equity_usdt()
    state["peak_equity"] = max(state["peak_equity"], nav)
    dd = 1.0 - nav / state["peak_equity"] if state["peak_equity"] > 0 else 0.0

    if state["halted"]:
        log(f"halted (dd kill switch); equity {nav:.2f}, uptime heartbeat only")
        return
    if dd >= cfg.dd_halt:
        log(f"KILL SWITCH: drawdown {dd:.1%} >= {cfg.dd_halt:.0%} — "
            f"flattening everything and halting (contest DQ is at 20%)")
        flatten_everything(broker, state, nav, dry)
        state["halted"] = True
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
            add = (1 + abs(pair["beta"])) * g
            if gross + add > cfg.max_gross_mult * nav:
                log(f"  {short_name}: entry skipped, gross cap")
                continue
            qa = broker.round_qty(a, g / prices[a])
            qb = broker.round_qty(b, abs(pair["beta"]) * g / prices[b])
            if (qa <= 0 or qb <= 0
                    or not broker.meets_min_notional(a, qa, prices[a])
                    or not broker.meets_min_notional(b, qb, prices[b])):
                log(f"  {short_name}: below min notional at NAV {nav:.0f}, skipped")
                continue
            ts = int(time.time())
            log(f"  {short_name}: ENTER {'long' if want > 0 else 'short'} spread "
                f"z={z:+.2f} g={g:.1f} USDT")
            if not dry:
                broker.place_market(a, "BUY" if want > 0 else "SELL",
                                    "LONG" if want > 0 else "SHORT",
                                    qa, max_notional=1.1 * g,
                                    client_order_id=f"ou-{ts}-a")
                broker.place_market(b, "SELL" if want > 0 else "BUY",
                                    "SHORT" if want > 0 else "LONG",
                                    qb, max_notional=1.1 * abs(pair["beta"]) * g,
                                    client_order_id=f"ou-{ts}-b")
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
                leg_close(broker, pair, nav, dry)
                pair["blocked"] = +1 if side > 0 else -1
            elif reverted or stale:
                log(f"  {short_name}: EXIT z={z:+.2f} "
                    f"({'reverted' if reverted else 'max hold'})")
                leg_close(broker, pair, nav, dry)


# --------------------------------------------------------------------- main --
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch data and print intents; place no orders")
    ap.add_argument("--once", action="store_true",
                    help="run a single bar then exit (for cron-style hosts)")
    args = ap.parse_args()
    cfg = AgentConfig()
    broker = RapidXBroker()
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
        sid = broker.start_automation(
            symbols, max_per_order="500", max_total="4000",
            expires_s=24 * 3600, consent_text=consent)
        session_started = time.time()
        log(f"automation session {sid}")

    if not args.dry_run and not consent:
        log("LTP_AUTOMATION_CONSENT_TEXT is not set. Automation consent "
            "must be written by the human operator (see deploy/README_ltp.md); "
            "refusing to trade without it. Use --dry-run to test.")
        sys.exit(1)

    while True:
        try:
            ensure_session()
            if state["bar"] % cfg.refit_every_bars == 0:
                refit(broker, cfg, state)
            trade_step(broker, cfg, state, args.dry_run)
        except RapidXError as exc:
            log(f"bar error (will retry next bar): {exc}")
        state["bar"] += 1
        save_state(cfg.state_path, state)
        if args.once:
            break
        # sleep to the top of the next hour, the bar close
        now = time.time()
        time.sleep(max(60.0, 3600 - (now % 3600) + 5))


if __name__ == "__main__":
    main()
