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
from deploy.ltp_analyst import StrategyAnalyst                       # noqa: E402
from deploy.ltp_stream import NewsStream                             # noqa: E402


# How far the re-estimated equilibrium has to move, in units of the entry's
# sigma, before an exit is described as partly the target moving rather than
# the spread returning. A tenth of a sigma is small enough to catch the effect
# early and large enough not to annotate ordinary refit noise.
MU_SHIFT_MATERIAL = 0.10


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
    ("BINANCE_PERP_AR_USDT", "BINANCE_PERP_FIL_USDT"),       # decentralized storage
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
    # MEASURED 2026-08-02, was 5e-4 assumed. The venue charges exactly 1.75 bps
    # per side -- five significant figures across 22 fills, fee == tradingFee,
    # zero rebate, execType TAKER throughout (deploy/fills_report.py). 2e-4 is
    # a margin over that against a schedule change, not against measurement
    # error. Expected to be inert: band_diagnostic puts cost_z at 0.01-0.08 for
    # every candidate, so costs are ~8% of the entry band and sweeping the fee
    # to zero admits no new pairs. Disclosed in LTP_STRATEGY.md, 2026-08-02.
    taker_fee: float = 2e-4
    stop_z: float = 3.5
    max_hold_mult: float = 3.0
    # SANDBOX RISK BUDGET (Phase I, from 2026-07-28). Halved from 0.004.
    # Track A Phase I advances the top 30 of a 29-team field, so rank here is
    # worth nothing and only the 800 USDT floor matters. That makes Phase I
    # what its name says -- a sandbox -- and the corrected band optimiser
    # (see LTP_STRATEGY.md) is being tested live to get real crypto evidence
    # before Phase II, where ranking and the prize actually exist. Scaling
    # size scales return and drawdown together without changing Sharpe, so
    # halving it costs nothing in evidence while bounding the downside.
    risk_per_pair: float = 0.002
    # Entry bands must clear this many standard errors of the FITTED mean.
    min_entry_se: float = 1.0
    max_pairs: int = 4
    max_gross_mult: float = 2.0       # gross notional cap, x NAV
    per_leg_cap_mult: float = 0.5     # single leg cap, x NAV
    dd_halt: float = 0.12             # flatten + halt at 12% off peak; the
                                      # contest eliminates at equity < 800U,
                                      # so this always fires first (>= 880)
    state_path: str = "deploy/ltp_state.json"
    # Durable drawdown high-water mark, kept in its OWN file so clearing the
    # disposable operational state (rm ltp_state.json, e.g. to force a refit)
    # can never silently re-anchor the kill switch to a lower equity. Seeded
    # to the funded starting equity, which is also the peak's floor.
    hwm_path: str = "deploy/ltp_hwm.json"
    initial_equity: float = 1000.0
    # Minutes before an announced venue maintenance window to go flat.
    maintenance_lead_minutes: int = 30


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


def load_hwm(path: str) -> float:
    """The durable drawdown high-water mark, or 0.0 if it doesn't exist yet.
    Deliberately a separate file from the operational state so a state wipe
    can't lower it."""
    p = Path(path)
    if not p.exists():
        return 0.0
    try:
        return float(json.loads(p.read_text()).get("peak_equity", 0.0))
    except (ValueError, OSError):
        return 0.0


def save_hwm(path: str, value: float) -> None:
    """Persist the high-water mark. Monotonic by construction at the call
    sites (always max'd with the prior value), so this only ever ratchets up."""
    Path(path).write_text(json.dumps({"peak_equity": float(value)}))


def anchor_peak(cfg: "AgentConfig", state: dict) -> float:
    """Set state['peak_equity'] to the highest of the operational state, the
    durable high-water-mark file, and the funded floor; persist it and return
    it. Called once at startup so a wiped state can't lower the kill-switch
    anchor."""
    peak = max(float(state.get("peak_equity", 0.0)),
               load_hwm(cfg.hwm_path), cfg.initial_equity)
    state["peak_equity"] = peak
    save_hwm(cfg.hwm_path, peak)
    return peak


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


def refit(broker: RapidXBroker, cfg: AgentConfig, state: dict,
          analyst=None) -> None:
    """Weekly-refit equivalent: selection + OU fit + cost-aware bands."""
    symbols = sorted({t for p in CANDIDATES for t in p})
    logp = fetch_panel(broker, symbols, cfg)
    if logp.empty:
        log("refit: no data panel, keeping previous fits")
        return

    # Canonical orientation. Engle-Granger is not symmetric: regressing A on B
    # is a different test from B on A, so the order a pair happens to be typed
    # in silently decides whether a genuinely cointegrated pair is found (live
    # scan: SOL/AVAX fails, AVAX/SOL passes at ADF p=0.0024). Resolve it with a
    # rule fixed in ADVANCE rather than by trying both and keeping the winner:
    # the MORE volatile series becomes the dependent variable, so the cleaner
    # series is the regressor. That is the standard errors-in-variables
    # mitigation -- noise in a regressor attenuates beta -- and because the
    # rule never inspects a p-value it adds no multiple testing at all.
    usable = [(a, b) if np.std(np.diff(logp[a].values)) >=
                        np.std(np.diff(logp[b].values)) else (b, a)
              for a, b in CANDIDATES
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
    reject_counts: dict = {}
    log(f"refit: {len(passed)}/{len(table)} candidates pass the gate")
    if len(passed) < len(table):
        # Why the rest were rejected — surfaced in the live logs so a quiet
        # day is legible (genuine no-cointegration vs a tunable mismatch).
        reject_counts = table.loc[~table.passed,
                                  "reject_reason"].value_counts().to_dict()
        log(f"refit: rejects {reject_counts}")

    fits = {}
    for _, row in passed.iterrows():
        a, b = row.a, row.b
        m = fit_spread_model(logp[a].values, logp[b].values)
        roundtrip = 2.0 * cfg.taker_fee * (1.0 + abs(m.beta))
        # n_obs is the window the OU was fitted on, so the optimiser refuses
        # entry bands sitting inside the uncertainty of the fitted mean. This
        # binds on slow-reverting pairs (a 267h half-life on 960 bars leaves
        # the mean known only to ~0.9 sigma) and is inert on the fast ones.
        bands = optimal_bands(m.ou, roundtrip, n_obs=len(logp[a].values),
                              min_entry_se=cfg.min_entry_se)
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
            "side": old.get(k, {}).get("side", 0),
            "notional": old.get(k, {}).get("notional"),
            # The entry coordinates must survive the refit that replaces `mu`
            # and `sigma`, or an open position loses all record of the
            # equilibrium it was actually opened against.
            "entry_mu": old.get(k, {}).get("entry_mu"),
            "entry_sigma": old.get(k, {}).get("entry_sigma")}
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

    # STRATEGY ADAPTATION (Track A reasoning audit): the organizer LLM reads
    # today's selection outcome and records an honest account of how the
    # tradeable universe is adapting. Advisory only — it never edits the
    # selection, and a failure here must not disturb the refit.
    if analyst is not None:
        rows = [{"pair": f"{r.a.split('_')[2]}/{r.b.split('_')[2]}",
                 "adf_p": float(r.adf_pvalue), "hurst": float(r.hurst),
                 "half_life": float(r.half_life), "beta": float(r.beta),
                 "crossings": int(r.crossings)}
                for _, r in passed.iterrows()]
        review = analyst.review_refit(rows, reject_counts, sorted(old.keys()))
        if review:
            log(f"  ai refit review: {str(review.get('assessment', ''))[:160]}")
            ledger("ai_refit_review", passed=int(len(passed)),
                   tested=int(len(table)), active=sorted(keep_keys), **review)


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


def entry_frame(pair: dict, spread: float) -> dict:
    """Where the spread sits against the equilibrium the position was OPENED
    on, versus the re-estimated one it is being judged by now.

    `mu` and `sigma` are recomputed at every refit over a trailing
    3*half_life window. On a trending spread the target walks toward the price
    and can overtake it, so a position exits "reverted" having never returned
    to where it was entered. That happened on 2026-08-05: z fell 0.83 while the
    spread ROSE 0.0101, closing -4.11 under a reasoning line that claimed the
    mean-reversion cycle had completed. It had not; the mean had moved.

    Returns {} when there is nothing to compare -- a position opened before
    this was recorded, or a degenerate sigma -- so callers can treat absence as
    "unknown" rather than as agreement.
    """
    mu0, sig0 = pair.get("entry_mu"), pair.get("entry_sigma")
    if mu0 is None or not sig0 or sig0 <= 0:
        return {}
    z_entry_frame = (spread - mu0) / sig0
    live_mu = pair.get("mu")
    mu_shift = None if live_mu is None else (live_mu - mu0) / sig0
    return {
        "z_in_entry_coords": float(z_entry_frame),
        "mu_shift_sigma": None if mu_shift is None else float(mu_shift),
        # The load-bearing flag: did the spread actually come back to the level
        # we entered against, or did the reference point come to us?
        "equilibrium_reestimated": bool(
            mu_shift is not None and abs(mu_shift) >= MU_SHIFT_MATERIAL),
    }


def reversion_note(frame: dict, exit_z: float) -> str:
    """One sentence for the reasoning log, honest about which happened."""
    if not frame:
        return ""
    if not frame.get("equilibrium_reestimated"):
        return ""
    return (f" NOTE: the equilibrium was re-estimated by "
            f"{frame['mu_shift_sigma']:+.2f} sigma during this hold, so the "
            f"exit is measured against a different mean than the entry — in "
            f"the entry's own coordinates the spread is at "
            f"z={frame['z_in_entry_coords']:+.2f}, not inside ±{exit_z:.2f}. "
            f"The reversion is partly the target moving, not only the spread "
            f"returning.")


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


def track_news_gate(state: dict, sentinel: NewsSentinel, previous: str) -> None:
    """Surface sentinel health loudly, and persist it for `status.py`.

    The sentinel fails OPEN on purpose — an LLM outage must not halt a working
    strategy, and the z-stop, vol-targeted sizing and gross cap all still
    apply. But failing open *silently* turns a risk control into a placebo:
    entries would quietly stop being screened for delistings and hacks, and a
    daily glance would show a perfectly healthy agent. The competition's AI
    allocation is USD 10/day with no rollover and nothing granted once it is
    spent, so 'quota' in particular is a predictable whole-day outage.

    Logged on TRANSITION rather than every bar, so a long outage is one loud
    event instead of hourly noise, and the ledger shows precisely the window
    in which screening was inactive.
    """
    state["news_gate"] = {"status": sentinel.status,
                          "error": sentinel.last_error[:200],
                          "rated": len(sentinel.verdicts),
                          "ts": sentinel.last_refresh}

    # Persist the verdicts themselves, every refresh. Previously the hourly
    # sentiment call left NO trace unless a trade happened that bar — the
    # per-asset severities lived in memory and were flattened into one prose
    # sentence inside an entry's `reasoning`. An auditor pulling the ledger
    # for a quiet stretch would have seen no evidence that sentiment analysis
    # ran at all, which is the one audit theme we have claimed longest. This
    # costs no extra AI call: it writes down what was already computed.
    # `no_news` is logged too — "we looked and nothing was relevant" is itself
    # evidence the sentinel ran on cadence.
    ledger("news_assessment", status=sentinel.status,
           rated=len(sentinel.verdicts), assets=sorted(sentinel.verdicts),
           verdicts={a: {"severity": v.get("severity"),
                         "rationale": str(v.get("rationale", ""))[:300]}
                     for a, v in sentinel.verdicts.items()},
           refreshed_at=sentinel.last_refresh,
           error=sentinel.last_error[:200])

    if sentinel.status == previous:
        return
    if sentinel.degraded:
        log(f"NEWS GATE DEGRADED ({sentinel.status}): entries are no longer "
            f"screened for event risk. {sentinel.last_error[:160]}")
        ledger("sentinel_degraded", status=sentinel.status,
               error=sentinel.last_error[:300],
               reasoning=(
                   f"The news sentinel stopped returning verdicts ("
                   f"{sentinel.status}). It fails open by design, so the "
                   f"systematic strategy keeps trading and the z-stop, "
                   f"vol-targeted sizing and gross cap remain in force — but "
                   f"until this clears, entries are NOT screened for "
                   f"structural events and 'watch' ratings are not halving "
                   f"size. Recorded so the audit can see exactly which "
                   f"decisions were made without event-risk screening."))
    elif previous in NewsSentinel.DEGRADED_STATES:
        log(f"news gate restored ({sentinel.status}); "
            f"{len(sentinel.verdicts)} assets rated")
        ledger("sentinel_restored", status=sentinel.status,
               rated=len(sentinel.verdicts))


def parse_maintenance_windows(spec: str) -> list[tuple[datetime, datetime]]:
    """Parse LTP_MAINTENANCE_WINDOWS: "START/END,START/END" in ISO-8601 UTC.

    Announced venue upgrades disable the place/cancel order APIs, which means
    the agent temporarily cannot de-risk — the same condition as being down,
    just with the outage on their side. Pausing for a scheduled blackout is an
    OPERATIONAL fact, not a market prediction, so it does not compromise the
    "the math decides trades" contract.

    Malformed entries are skipped rather than raised: a typo in an env var
    must never stop a live agent from trading."""
    out: list[tuple[datetime, datetime]] = []
    for chunk in (spec or "").split(","):
        chunk = chunk.strip()
        if not chunk or "/" not in chunk:
            continue
        start_s, _, end_s = chunk.partition("/")
        try:
            start = datetime.fromisoformat(start_s.strip().replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_s.strip().replace("Z", "+00:00"))
        except ValueError:
            log(f"maintenance: ignoring unparseable window {chunk!r}")
            continue
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end > start:
            out.append((start, end))
        else:
            log(f"maintenance: ignoring window with end <= start: {chunk!r}")
    return out


def maintenance_state(now: datetime, windows: list, lead_minutes: int) -> str:
    """'active' inside a window, 'prepare' in the run-up to one, else 'clear'."""
    for start, end in windows:
        if start <= now < end:
            return "active"
        lead = start - pd.Timedelta(minutes=lead_minutes).to_pytimedelta()
        if lead <= now < start:
            return "prepare"
    return "clear"


# A verdict older than this did not screen the bar it is attached to. The
# sentinel refreshes hourly, so two hours is already an outage or an idle book.
NEWS_STALE_H = 2.0


def verdict_age_hours(sentinel: NewsSentinel | None,
                      now: datetime | None = None) -> float | None:
    """Hours since the sentinel last refreshed, or None if never/unparseable."""
    try:
        stamp = datetime.fromisoformat(str(sentinel.last_refresh))
    except (AttributeError, TypeError, ValueError):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return ((now or datetime.now(timezone.utc)).timestamp()
            - stamp.timestamp()) / 3600.0


def screening_provenance(sentinel: NewsSentinel | None, assessment: dict,
                         a: str, b: str, now: datetime | None = None) -> dict:
    """Structured record of which gates actually screened this decision.

    The reasoning prose already distinguishes a screened entry from an
    unscreened one, but only in words. The audit correlates AI decision logs
    with executed orders programmatically, so the provenance has to be
    machine-readable: `df[df.event=='enter']` should answer "was this trade
    screened, by what, and with what verdict" without parsing English.
    """
    ba, bb = base_asset(a), base_asset(b)
    if sentinel is None:
        news = {"news_status": "disabled", "news_severity": {}}
        screened = False
    else:
        # The sentinel only refreshes for assets of ALREADY-active pairs
        # (`ltp_agent.py`, the bar loop: `assets = active_assets()`), and that
        # list is computed BEFORE the refit that adds new ones. So a pair
        # selected out of a drought can be entered while the sentinel holds
        # verdicts that never covered its legs -- and this record used to stamp
        # that entry `news_status: ok`. A log that claims a screening which did
        # not happen is worse than one that says nothing.
        severity = {ba: (sentinel.verdicts.get(ba.upper()) or {}).get("severity"),
                    bb: (sentinel.verdicts.get(bb.upper()) or {}).get("severity")}
        age = verdict_age_hours(sentinel, now=now)
        missing = sorted(k for k, v in severity.items() if v is None)
        stale = age is not None and age > NEWS_STALE_H
        # Precedence matters: a degraded sentinel must keep reporting WHY it is
        # down (`quota`, `api_error`, ...). "missing_legs" on a quota outage
        # would describe the symptom and lose the cause.
        status = sentinel.status
        if sentinel.degraded:
            pass
        elif missing:
            status = "missing_legs"          # never rated: this leg is unscreened
        elif stale:
            status = "stale"                 # rated, but not for this bar
        news = {"news_status": status,
                "news_severity": severity,
                "news_age_h": None if age is None else round(age, 2),
                "news_refreshed_at": sentinel.last_refresh or None,
                "news_unrated_legs": missing or None}
        screened = ((not sentinel.degraded) and bool(sentinel.verdicts)
                    and not missing and not stale)
    return {"screened": screened,
            "regime": (assessment or {}).get("regime"),
            "regime_confidence": (assessment or {}).get("confidence"),
            **news}


def reconcile_positions(broker: RapidXBroker, state: dict, dry: bool) -> None:
    """Make the exchange the source of truth about what we are holding.

    State and reality can disagree in two directions, and both are dangerous:

      - The exchange holds a position the strategy has no record of. Causes
        seen live: a wiped or stale state file, and a crash (or an API error)
        between placing the first and second leg of an entry. Nothing will
        ever exit or stop that position, and because the pair still reads as
        flat the agent can open a SECOND position in the same direction.
      - The strategy believes it holds a pair the exchange has already closed,
        so its side, hold clock and gross-exposure accounting are all wrong.

    Anything the strategy cannot account for is FLATTENED rather than adopted.
    Adopting would mean reconstructing the entry price, the hold clock and the
    hedge ratio the legs were originally sized under -- and a mis-adopted pair
    is a mis-hedged pair, which is a directional bet wearing a market-neutral
    costume. Flattening costs one round trip of fees, always reduces risk, and
    the strategy re-enters cleanly on its own terms if the signal still holds.

    The half-open case (one leg live, one not) is the worst of all: naked
    directional exposure in a book whose entire premise is being hedged. It is
    closed on sight.
    """
    live: dict[str, dict] = {}
    for p in broker.positions():
        if abs(broker._position_qty(p)) > 0:
            sym = p.get("sym") or p.get("symbol")
            if sym:
                live[sym] = p

    def _close(sym: str, why: str, pair_key: str) -> None:
        pos = live.get(sym, {})
        val = abs(float(pos.get("positionValue") or 0.0)) or 1000.0
        log(f"  reconcile: {why} — closing unmanaged {sym}")
        ledger("reconcile", action=why, symbol=sym, pair=pair_key,
               qty=broker._position_qty(pos), dry=dry,
               reasoning=(
                   f"The exchange reports an open {sym} position that the "
                   f"strategy's own state does not account for ({why}). An "
                   f"unmanaged position has no exit, no stop and no place in "
                   f"the gross-exposure budget, and a pair that reads as flat "
                   f"can be entered again on top of it. It is closed rather "
                   f"than adopted, because adopting it would mean guessing the "
                   f"hedge ratio it was sized under."))
        if not dry:
            broker.op_context = {"decision": "reconcile", "pair": pair_key}
            broker.close_position(sym, pos.get("positionSide") or "LONG",
                                  max_notional=max(2.0 * val, 100.0))
            broker.op_context = {}
        live.pop(sym, None)

    # 1. pairs the state believes are open: confirm both legs really are
    for key, pair in state.get("pairs", {}).items():
        if pair.get("side", 0) == 0:
            continue
        a_live, b_live = pair["a"] in live, pair["b"] in live
        if a_live and b_live:
            continue                       # consistent, leave it alone
        if not a_live and not b_live:
            log(f"  reconcile: {key} recorded open but the exchange is flat; "
                f"clearing stale side")
            ledger("reconcile", action="clear_stale_side", pair=key,
                   side=pair.get("side"), dry=dry)
            pair["side"], pair["hold"] = 0, 0
        else:
            _close(pair["a"] if a_live else pair["b"], "half_open_pair", key)
            pair["side"], pair["hold"] = 0, 0

    # 2. anything still live that no open pair accounts for is an orphan
    expected = {s for pair in state.get("pairs", {}).values()
                if pair.get("side", 0) != 0 for s in (pair["a"], pair["b"])}
    for sym in list(live):
        if sym not in expected:
            _close(sym, "unknown_position", "*")


def trade_step(broker: RapidXBroker, cfg: AgentConfig, state: dict,
               dry: bool, sentinel: NewsSentinel | None = None,
               analyst=None) -> None:
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
    save_hwm(cfg.hwm_path, state["peak_equity"])   # ratchet the durable mark
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

        # rolling z path, kept in state so the analyst (and the audit) can see
        # the shape of the divergence, not just its latest value
        z_path = (pair.get("z_path") or [])[-23:] + [round(float(z), 3)]
        pair["z_path"] = z_path

        # MARKET ANOMALY DETECTION (Track A reasoning audit): the organizer
        # LLM judges whether this spread still behaves like the mean-reverting
        # process the model assumes. Logged every bar; a "broken" verdict can
        # only VETO an entry below — never open, size up, or re-enter.
        assessment = {}
        if analyst is not None and not dry:
            news_note = (sentinel.note(base_asset(a), base_asset(b))
                         if sentinel else "news sentinel disabled")
            assessment = analyst.assess_spread(
                pair=short_name, z=float(z), entry_z=pair["entry_z"],
                exit_z=pair["exit_z"], stop_z=cfg.stop_z,
                half_life=pair["half_life"], beta=pair["beta"],
                z_path=z_path, news_note=news_note,
                holding=pair.get("side", 0) != 0)
            if assessment:
                ledger("ai_spread_assessment", pair=short_name, z=float(z),
                       holding=pair.get("side", 0) != 0, **assessment)
            elif getattr(analyst, "degraded", False):
                # A missing assessment must not be indistinguishable from a bar
                # that was never assessed -- same blind spot the news gate had.
                ledger("ai_assessment_unavailable", pair=short_name, z=float(z),
                       status=analyst.status, error=analyst.last_error[:300])

        # heal the post-stop one-sided block once z is back inside the band
        if pair.get("blocked", 0) == +1 and z > -pair["entry_z"]:
            pair["blocked"] = 0
        elif pair.get("blocked", 0) == -1 and z < pair["entry_z"]:
            pair["blocked"] = 0

        if pair.get("flatten") and pair.get("side", 0) != 0:
            log(f"  {short_name}: dropped by refit, flattening")
            # This close used to write nothing at all: the two orders reached
            # the venue tagged decision="close" with no decision record behind
            # them anywhere, so the audit chain began at the operations and no
            # reasoning explained why a position was exited. Every other close
            # path -- stop, exit, news_derisk, kill_switch, maintenance --
            # logs one. Found 2026-08-02.
            ledger("refit_drop", pair=short_name, side=pair["side"], z=float(z),
                   hold_bars=pair.get("hold", 0), price_a=prices[a],
                   price_b=prices[b], nav=nav, dry=dry,
                   reasoning=(f"The latest refit no longer selects this pair, "
                              f"so the cointegration evidence that justified "
                              f"holding it is gone (z={z:+.2f}, held "
                              f"{pair.get('hold', 0)} bars). Mean reversion is "
                              f"a bet on a relationship the model has stopped "
                              f"believing in; carrying the position on a "
                              f"hypothesis we just rejected would be a "
                              f"directional trade in a market-neutral "
                              f"costume. Closed at the refit, not at a stop."))
            leg_close(broker, pair, nav, dry, decision="refit_drop")
            del state["pairs"][key]
            continue

        side = pair.get("side", 0)
        if side == 0:
            # No entries beyond the stop: past stop_z the working hypothesis
            # is 'relationship broke', and buying it there just schedules an
            # immediate stop-out with two round trips of fees.
            blocked = pair.get("blocked", 0)
            short_zone = pair["entry_z"] < z < cfg.stop_z
            long_zone = -cfg.stop_z < z < -pair["entry_z"]
            want = 0
            if short_zone and blocked != -1:
                want = -1
            elif long_zone and blocked != +1:
                want = +1
            if want == 0:
                # The one-sided re-entry block used to decline entries in total
                # silence -- `blocked` lived in runtime state and nowhere else,
                # so a signal refused by a risk control was indistinguishable
                # from a bar where nothing happened. That is the same gap as
                # refit_drop and size_mult, and it is the last one known.
                # Logged only when the block is what actually stopped the
                # trade, never on a quiet bar.
                if (short_zone and blocked == -1) or (long_zone and blocked == +1):
                    heal_at = -pair["entry_z"] if blocked == +1 else pair["entry_z"]
                    ledger("skip", pair=short_name, reason="side_blocked",
                           z=float(z), blocked=blocked,
                           side_wanted=-1 if short_zone else +1,
                           entry_z=pair["entry_z"], nav=nav,
                           reasoning=(
                               f"Signal at z={z:+.2f} is inside the entry band "
                               f"±{pair['entry_z']:.2f}, but this side stopped "
                               f"out earlier and stays blocked until z heals "
                               f"back past {heal_at:+.2f}. Re-entering the side "
                               f"that just broke would be averaging into a "
                               f"spread the model has already judged broken "
                               f"once; the opposite side remains available."),
                           **screening_provenance(sentinel, assessment, a, b))
                continue
            g = cfg.risk_per_pair * nav / max(pair["dvol"], 1e-9)
            g = min(g, cfg.per_leg_cap_mult * nav)
            size_mult = 1.0
            if sentinel is not None:
                size_mult = sentinel.size_mult(base_asset(a), base_asset(b))
                if size_mult < 1.0:
                    log(f"  {short_name}: news 'watch' rating, "
                        f"sizing x{size_mult}")
                    # A risk control that acts and leaves no ledger trace is
                    # indistinguishable from one that never fired. On
                    # 2026-08-01 this halved the position on the single worst
                    # trade of the competition -- turning a -12 into a -6 --
                    # and the only evidence was a journal line that scrolls
                    # away. The audit correlates decisions with orders; a
                    # size reduction is a decision.
                    ledger("size_reduced", pair=short_name, mult=size_mult,
                           z=float(z), g_before=g, g_after=g * size_mult,
                           nav=nav,
                           reasoning=(f"News sentinel rates a leg 'watch': "
                                      f"elevated event risk short of the "
                                      f"critical threshold that would veto "
                                      f"the entry outright. The trade still "
                                      f"passes every statistical gate, so it "
                                      f"is taken at half risk rather than "
                                      f"skipped — the gate can only reduce "
                                      f"exposure, never add it."),
                           **screening_provenance(sentinel, assessment, a, b))
                g *= size_mult
            add = (1 + abs(pair["beta"])) * g
            if gross + add > cfg.max_gross_mult * nav:
                log(f"  {short_name}: entry skipped, gross cap")
                ledger("skip", pair=short_name, reason="gross_cap", z=z,
                       gross=gross, add=add, nav=nav,
                       **screening_provenance(sentinel, assessment, a, b))
                continue
            qa = broker.round_qty(a, g / prices[a])
            qb = broker.round_qty(b, abs(pair["beta"]) * g / prices[b])
            if (qa <= 0 or qb <= 0
                    or not broker.meets_min_notional(a, qa, prices[a])
                    or not broker.meets_min_notional(b, qb, prices[b])):
                log(f"  {short_name}: below min notional at NAV {nav:.0f}, skipped")
                ledger("skip", pair=short_name, reason="min_notional", z=z,
                       qa=qa, qb=qb, nav=nav,
                       **screening_provenance(sentinel, assessment, a, b))
                continue
            news_note = sentinel.note(base_asset(a), base_asset(b)) if sentinel \
                else "news sentinel disabled"
            # Anomaly veto: the analyst judged the spread structurally broken,
            # so the mean-reversion premise does not hold. Risk-reducing only.
            if analyst is not None and assessment:
                broken = analyst.anomaly_veto(assessment)
                if broken:
                    log(f"  {short_name}: ANOMALY VETO — {broken}")
                    ledger("skip", pair=short_name, reason="anomaly_veto", z=z,
                           assessment=assessment, nav=nav,
                           **screening_provenance(sentinel, assessment, a, b),
                           reasoning=(
                               f"The quantitative entry signal was live "
                               f"(z={z:+.2f} beyond the cost-aware band "
                               f"{pair['entry_z']:.2f}), but the spread's live "
                               f"regime was rated broken rather than merely "
                               f"stretched: {broken}. Mean reversion presumes "
                               f"the spread is a spring; when the evidence says "
                               f"the relationship itself has changed, entering "
                               f"would be betting on a spring that has snapped, "
                               f"so no position is opened."))
                    continue
            if sentinel is not None:
                rationale = sentinel.veto(base_asset(a), base_asset(b))
                if rationale:
                    log(f"  {short_name}: NEWS VETO — {rationale}")
                    ledger("skip", pair=short_name, reason="news_veto", z=z,
                           news=rationale, nav=nav,
                           **screening_provenance(sentinel, assessment, a, b),
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
                   # `g` is already multiplied, so without this the reduction
                   # is invisible in the row that records the trade.
                   size_mult=size_mult,
                   **screening_provenance(sentinel, assessment, a, b),
                   reasoning=(f"Spread z={z:+.2f} crossed the cost-aware optimal "
                              f"entry band ±{pair['entry_z']:.2f} (fitted OU "
                              f"half-life {pair['half_life']:.0f}h; band maximizes "
                              f"expected profit per hour net of fees via first-"
                              f"passage times). {'Buying' if want > 0 else 'Selling'} "
                              f"the spread: risk-budgeted {g:.0f} USDT against "
                              f"hedge ratio beta={pair['beta']:.2f}. Pair passed "
                              f"FDR-corrected cointegration + split-half stability "
                              f"at the last refit. {news_note}."
                              + (f" Spread-regime analysis: "
                                 f"{assessment.get('regime')} — "
                                 f"{assessment.get('rationale', '')}"
                                 if assessment else "")))
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
            # Snapshot the equilibrium this position was opened against. `mu`
            # is re-estimated every refit over a trailing 3*half_life window,
            # so in a trending spread the target walks toward the price and can
            # overtake it: the position then exits "reverted" while the spread
            # never came back to where we entered. Observed 2026-08-05 -- z fell
            # 0.83 while the spread ROSE 0.0101, a -4.11 loss on an exit whose
            # reasoning claimed the cycle had completed. Keeping the entry
            # coordinates lets the exit say which of the two actually happened.
            pair["entry_mu"] = pair["mu"]
            pair["entry_sigma"] = pair["sigma"]
            gross += add
        else:
            pair["hold"] = pair.get("hold", 0) + 1
            stopped = (side > 0 and z < -cfg.stop_z) or \
                      (side < 0 and z > cfg.stop_z)
            stale = pair["hold"] >= cfg.max_hold_mult * pair["half_life"]
            # Directional, not symmetric. A long spread was entered below the
            # mean and profits as z RISES, so it exits once z climbs back to
            # -exit_z; the short side mirrors. The old `abs(z) < exit_z` form
            # happened to agree on the path that matters while exit_z was
            # permanently 1.5 (the band-optimiser bug), but it cannot express
            # exit_z = 0 -- "take profit at the mean" -- because abs(z) < 0 is
            # never true. That left a position with no reachable profit exit,
            # reachable only via the stop or the max-hold clock.
            exit_z = pair["exit_z"]
            reverted = (side > 0 and z >= -exit_z) or (side < 0 and z <= exit_z)
            frame = entry_frame(pair, spread)
            if stopped:
                log(f"  {short_name}: Z-STOP z={z:+.2f}, closing + blocking side")
                ledger("stop", pair=short_name, side=side, z=z,
                       hold_bars=pair["hold"], price_a=prices[a],
                       price_b=prices[b], nav=nav, dry=dry, **frame,
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
                    + reversion_note(frame, exit_z)
                    if reverted else
                    f"Held {pair['hold']} bars, {cfg.max_hold_mult:.0f}x the "
                    f"fitted half-life of {pair['half_life']:.0f}h, without "
                    f"reverting. The model was wrong about the reversion speed; "
                    f"stop paying carry to find out how wrong.")
                ledger("exit", pair=short_name, side=side, z=z, reason=why,
                       hold_bars=pair["hold"], price_a=prices[a],
                       price_b=prices[b], nav=nav, dry=dry, **frame,
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
    # Anchor the drawdown peak from the durable high-water mark so a state
    # wipe (e.g. forcing a refit) can't re-anchor the kill switch downward.
    log(f"drawdown peak anchored at {anchor_peak(cfg, state):.2f} USDT")

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
    # Reasoning-depth layer: anomaly detection + strategy adaptation, logged
    # for the Track A audit. Analyses only; it can veto an entry, never open one.
    analyst = StrategyAnalyst()

    def active_assets() -> list[str]:
        return [base_asset(s) for p in state["pairs"].values()
                for s in (p["a"], p["b"])]

    stream = NewsStream(sentinel, active_assets)
    if stream.start():
        log("news stream: live (sub-minute de-risking armed)")
    else:
        log("news stream: websockets not installed, hourly poll only")
        stream = None

    windows = parse_maintenance_windows(
        os.environ.get("LTP_MAINTENANCE_WINDOWS", ""))
    if windows:
        log("maintenance windows: " + ", ".join(
            f"{a.isoformat()} -> {b.isoformat()}" for a, b in windows))
    maint = "clear"

    while True:
        try:
            ensure_session()
            # Announced venue upgrades take the place/cancel order APIs down,
            # so the agent cannot exit or stop anything while one is running.
            # Go flat in the run-up and open nothing during: a scheduled
            # blackout is an operational fact, not a market call.
            prev_maint, maint = maint, maintenance_state(
                datetime.now(timezone.utc), windows,
                cfg.maintenance_lead_minutes)
            if maint != prev_maint:
                log(f"maintenance state: {prev_maint} -> {maint}")
                ledger("maintenance", state=maint, previous=prev_maint,
                       reasoning=(
                           "The venue announced a maintenance window in which "
                           "the place/cancel order APIs are unavailable. While "
                           "it runs the agent cannot exit, stop, or de-risk a "
                           "position, so it goes flat beforehand and opens "
                           "nothing until the window closes. This is an "
                           "operational response to a scheduled outage, not a "
                           "view on the market."))
            if state["bar"] % cfg.refit_every_bars == 0:
                refit(broker, cfg, state, analyst)
            # Reality check before acting: a restart, a wiped state file or a
            # failure between an entry's two legs can leave the exchange
            # holding something the strategy doesn't know about. Run this
            # BEFORE trade_step so nothing is ever stacked on top of an
            # unmanaged position.
            if maint == "active":
                # Orders would be refused; skip the write paths entirely
                # rather than generate a bar of avoidable errors.
                log("maintenance active: trading suspended this bar")
                state["bar"] += 1
                save_state(cfg.state_path, state)
                if args.once:
                    break
                time.sleep(max(60.0, 3600 - (time.time() % 3600) + 5))
                continue
            reconcile_positions(broker, state, args.dry_run)
            if maint == "prepare":
                nav_now = broker.equity_usdt()
                log("maintenance imminent: flattening before the window")
                flatten_everything(broker, state, nav_now, args.dry_run)
            assets = active_assets()
            if assets:
                previous_gate = sentinel.status
                sentinel.refresh(assets)
                track_news_gate(state, sentinel, previous_gate)
            trade_step(broker, cfg, state, args.dry_run, sentinel,
                       analyst)
        except RapidXError as exc:
            log(f"bar error (will retry next bar): {exc}")
        except Exception as exc:
            # An always-on agent must not die on a data or model problem: a
            # single bad symbol (constant series, NaN, a numerical edge case
            # in a fit) used to propagate out of refit and kill the process,
            # which then restarted straight back into the same refit. Log it
            # loudly, keep the state, and let the next bar retry -- a live
            # agent that is down cannot de-risk.
            log(f"UNEXPECTED bar error ({type(exc).__name__}: {exc}); "
                f"continuing to next bar")
            ledger("bar_error", error_type=type(exc).__name__, error=str(exc)[:500])
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
