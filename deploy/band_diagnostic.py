"""
deploy/band_diagnostic.py — read-only study of the cost-aware band optimizer.

Two questions, no live changes and no orders:

1. HOW WRONG ARE THE LIVE BANDS? Every live pair reports entry 3.0 / exit
   1.5 — the exact corner of `optimal_bands`' search grids. The cause is a
   unit mismatch in the optimizer's greedy comparison: it compares a raw
   `rate` against a stored `rate * sigma_eq`. With sigma_eq ~0.03 in
   log-price units, the incumbent's bar is deflated ~30x, so almost any later
   grid cell "wins" and the search walks to the corner instead of the
   optimum. `corrected_bands()` below runs the SAME objective with the
   comparison done in one unit, and the two are printed side by side.

2. WOULD CHEAPER EXECUTION UNLOCK PAIRS? Costs enter as `cost_z =
   roundtrip_cost / sigma_eq`, and `optimal_bands` refuses any pair whose
   reversion amplitude can't pay the toll — which is what killed the
   pre-registered XAUT/PAXG gold anchor. Rather than build maker/limit
   execution on an assumption, this sweeps the fee down (100% / 50% / 25% /
   0% of the assumed 5 bps taker) and reports which pairs become tradeable
   and how the bands tighten. That is the actual evidence for or against
   spending a week on limit execution.

    set -a; source /root/ltp.env; set +a
    python deploy/band_diagnostic.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.ltp_broker import RapidXBroker                        # noqa: E402
from deploy.ltp_agent import AgentConfig, fetch_panel, CANDIDATES  # noqa: E402
from statarb.ou import fit_spread_model                           # noqa: E402
from statarb.thresholds import optimal_bands, ou_expected_passage_time  # noqa: E402


def corrected_bands(ou, roundtrip_cost, a_grid, b_grid):
    """`optimal_bands` with the comparison unit mismatch removed.

    Kept here rather than patched into statarb/ so this stays a read-only
    measurement: the live agent is untouched until we have seen the numbers.
    Returns (entry_z, exit_z, cycle_bars, rate) or None if untradeable."""
    theta = ou.theta
    sigma_std = np.sqrt(2.0 * theta)
    cost_z = roundtrip_cost / ou.sigma_eq
    best, best_rate = None, -np.inf
    for a in a_grid:
        for b in b_grid:
            if b >= a - 0.1:
                continue
            profit = (a - b) - cost_z
            if profit <= 0:
                continue
            cycle = (ou_expected_passage_time(-a, -b, theta, sigma_std)
                     + ou_expected_passage_time(-b, -a, theta, sigma_std))
            if cycle <= 0:
                continue
            rate = profit / cycle
            if rate > best_rate:          # both sides raw -- the actual fix
                best_rate = rate
                best = (float(a), float(b), float(cycle))
    return (best + (best_rate,)) if best else None

# The shipped defaults, restated so the comparison is explicit.
CUR_A = np.arange(0.4, 3.01, 0.2)
CUR_B = np.arange(0.0, 1.51, 0.25)
# Deliberately far past any plausible optimum, so saturation here would mean
# something is wrong with the objective rather than with the grid.
WIDE_A = np.arange(0.4, 6.01, 0.2)
WIDE_B = np.arange(0.0, 4.01, 0.2)

FEE_STEPS = [("taker 5.0bp (assumed today)", 1.00),
             ("2.5bp  (maker ~half)", 0.50),
             ("1.25bp (maker ~quarter)", 0.25),
             ("0.0bp  (free, lower bound)", 0.00)]


def _short(a: str, b: str) -> str:
    return f"{a.split('_')[2]}/{b.split('_')[2]}"


def main() -> int:
    cfg = AgentConfig()
    broker = RapidXBroker()
    symbols = sorted({s for p in CANDIDATES for s in p})
    print(f"fetching {len(symbols)} symbols ({cfg.lookback_bars} bars) ...")
    logp = fetch_panel(broker, symbols, cfg)
    if logp.empty:
        print("no data panel — aborting.")
        return 1

    print("\n" + "=" * 78)
    print(f"1. SHIPPED vs CORRECTED OPTIMISER   (stop_z={cfg.stop_z})")
    print("=" * 78)
    print(f"{'pair':<12}{'hl(h)':>7}{'cost_z':>8}   "
          f"{'SHIPPED e,x':>14}{'cyc_h':>9}   {'CORRECTED e,x':>15}"
          f"{'cyc_h':>8}{'x rate':>9}")

    fits = {}
    for a, b in CANDIDATES:
        if a not in logp.columns or b not in logp.columns:
            continue
        la, lb = logp[a].values, logp[b].values
        # canonical orientation, same rule the agent uses
        if np.std(np.diff(la)) < np.std(np.diff(lb)):
            a, b, la, lb = b, a, lb, la
        try:
            m = fit_spread_model(la, lb)
        except Exception:
            continue
        if not np.isfinite(m.ou.half_life) or m.ou.sigma_eq <= 0:
            continue
        fits[_short(a, b)] = m

        roundtrip = 2.0 * cfg.taker_fee * (1.0 + abs(m.beta))
        cost_z = roundtrip / m.ou.sigma_eq
        ship = optimal_bands(m.ou, roundtrip, CUR_A, CUR_B)
        fix = corrected_bands(m.ou, roundtrip, CUR_A, CUR_B)

        if ship.tradeable:
            # the shipped rate, recomputed raw so the two are comparable
            ship_rate = ((ship.entry_z - ship.exit_z - cost_z)
                         / ship.cycle_days) if ship.cycle_days > 0 else 0.0
            ship_txt = f"{ship.entry_z:>7.1f},{ship.exit_z:<6.2f}"
            ship_cyc = f"{ship.cycle_days:>9.0f}"
        else:
            ship_rate, ship_txt, ship_cyc = 0.0, f"{'untradeable':>14}", f"{'--':>9}"
        if fix:
            fix_txt = f"{fix[0]:>8.1f},{fix[1]:<6.2f}"
            fix_cyc = f"{fix[2]:>8.0f}"
            ratio = (fix[3] / ship_rate) if ship_rate > 0 else float("inf")
            ratio_txt = f"{ratio:>8.1f}x"
        else:
            fix_txt, fix_cyc, ratio_txt = f"{'untradeable':>15}", f"{'--':>8}", f"{'--':>9}"
        print(f"{_short(a, b):<12}{m.ou.half_life:>7.1f}{cost_z:>8.2f}   "
              f"{ship_txt}{ship_cyc}   {fix_txt}{fix_cyc}{ratio_txt}")

    print("\ncyc_h = expected hours per round trip. 'x rate' = how many times "
          "more\nprofit per hour the corrected bands earn than the shipped "
          "ones.")

    print("\n" + "=" * 78)
    print("2. WOULD CHEAPER EXECUTION UNLOCK PAIRS?  (CORRECTED optimiser)")
    print("=" * 78)
    header = f"{'pair':<12}" + "".join(f"{lbl.split()[0]:>16}"
                                       for lbl, _ in FEE_STEPS)
    print(header)
    print(f"{'':12}" + "".join(f"{'entry,exit':>16}" for _ in FEE_STEPS))
    unlocked: dict[str, list[str]] = {lbl: [] for lbl, _ in FEE_STEPS}
    for name, m in fits.items():
        cells = []
        base_tradeable = None
        for lbl, mult in FEE_STEPS:
            rt = 2.0 * cfg.taker_fee * mult * (1.0 + abs(m.beta))
            ob = corrected_bands(m.ou, rt, CUR_A, CUR_B)
            if ob:
                cells.append(f"{ob[0]:>7.1f},{ob[1]:<7.2f}")
                unlocked[lbl].append(name)
            else:
                cells.append(f"{'--':>16}")
            if base_tradeable is None:
                base_tradeable = bool(ob)
        print(f"{name:<12}" + "".join(cells))

    print("\ntradeable pair COUNT by fee level:")
    for lbl, _ in FEE_STEPS:
        print(f"   {lbl:<28} {len(unlocked[lbl]):>2}  "
              f"{sorted(unlocked[lbl])}")

    base = set(unlocked[FEE_STEPS[0][0]])
    half = set(unlocked[FEE_STEPS[1][0]])
    gained = sorted(half - base)
    print("\n" + "=" * 78)
    print(f"HALVING EXECUTION COST would newly admit: {gained or 'NOTHING'}")
    print("(cost only gates the band economics here; every pair must still "
          "pass\n the untouched ADF/FDR/split-half/Hurst selection gates to "
          "trade at all.)")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
