"""
deploy/stop_analysis.py — what every z-stop actually cost, and why.

The z-stop is the escape hatch for the LTCM failure mode: past `stop_z` the
working hypothesis flips from "temporarily stretched" to "the relationship
broke", the position is cut, and that side is blocked. It is insurance, and
insurance is judged on the premium against the claims — not on the times it
paid out badly.

Three August excursions on AVAX/SOL made the question concrete, and they do not
all point the same way:

    Aug 1  stopped at z = -10.25 against a 3.5 band   -> 6.75 sigma LATE
    Aug 2  stopped at z = +3.63                       -> 0.13 sigma late
    Aug 4  reached +3.38, never stopped, reverted     -> the band let it breathe

If stops routinely fire far past the band, the defect is the hourly sampling
interval, not the level, and the fix is intra-bar monitoring. If they fire at
the band and the spread then reverts anyway, the defect is the level, and
`stop_z` is mis-calibrated to post-break volatility. Those are different repairs
and the ledger can tell them apart.

For every stop this reports:

  * OVERSHOOT — how far past `stop_z` it actually fired. This is the cost of
    looking once an hour, and it converts directly to money.
  * REVERSION — whether the spread came back after the stop, how far it went
    first, and how long it took. This is the cost of the insurance itself.
  * COUNTERFACTUALS — what the loss would have been stopping exactly at the
    band, and what holding to the best subsequent level would have returned.

P&L is linear in z (position value moves as `g * sigma * dz`), so the rate is
derived from each trade's own entry and stop records and applied to the
counterfactual z levels. No model, no fitting: only what the ledger recorded.

    python deploy/stop_analysis.py
    python deploy/stop_analysis.py --json out.json

Read-only. It opens nothing, places nothing, and touches no live state.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.fills_report import load_ledger, _f, _ts, LEDGER    # noqa: E402

# How long after a stop to keep watching the spread. Three days covers several
# half-lives on every pair we trade, which is long enough to see a reversion
# that was actually going to happen and short enough that a later, unrelated
# excursion is not mistaken for one.
WATCH_HOURS = 72.0


@dataclass
class StopCase:
    pair: str
    stop_ts: datetime
    entry_ts: datetime | None
    entry_z: float | None
    stop_z_reading: float          # z actually observed when the stop fired
    band: float                    # the stop_z the agent was configured with
    side: int
    hold_bars: int | None
    pnl: float | None              # realised, from decision prices
    path_after: list[tuple[datetime, float]] = field(default_factory=list)

    # ---------------------------------------------------------- measures --
    @property
    def overshoot(self) -> float | None:
        """How far past the band it fired. Zero means the band was honoured."""
        if self.band is None:
            return None
        return max(0.0, abs(self.stop_z_reading) - self.band)

    @property
    def rate_per_z(self) -> float | None:
        """P&L per unit of z, from this trade's own numbers."""
        if (self.pnl is None or self.entry_z is None
                or abs(self.stop_z_reading - self.entry_z) < 1e-9):
            return None
        return self.pnl / (self.stop_z_reading - self.entry_z)

    @property
    def loss_at_band(self) -> float | None:
        """What stopping exactly at the band would have cost -- i.e. the loss
        with a monitoring interval short enough to catch the crossing."""
        r = self.rate_per_z
        if r is None or self.entry_z is None:
            return None
        signed_band = self.band if self.stop_z_reading > 0 else -self.band
        return r * (signed_band - self.entry_z)

    @property
    def overshoot_cost(self) -> float | None:
        """The money the hourly sampling interval cost on this trade."""
        if self.pnl is None or self.loss_at_band is None:
            return None
        return self.pnl - self.loss_at_band

    @property
    def best_after(self) -> tuple[datetime, float] | None:
        """The most favourable z reached after the stop, i.e. the best exit a
        held position would have found."""
        if not self.path_after:
            return None
        # Favourable means back toward the mean: smallest |z|.
        return min(self.path_after, key=lambda p: abs(p[1]))

    @property
    def reverted(self) -> bool:
        """Did the spread come back inside the band after we cut it?"""
        b = self.best_after
        return b is not None and abs(b[1]) < self.band

    @property
    def hold_would_have(self) -> float | None:
        """P&L if the position had been held to the best subsequent level.

        This is the counterfactual that flatters holding, deliberately: it uses
        hindsight to pick the exit. If even THIS is not much better than the
        realised loss, the stop cost nothing and the question is settled.
        """
        r, b = self.rate_per_z, self.best_after
        if r is None or b is None or self.entry_z is None:
            return None
        return r * (b[1] - self.entry_z)

    @property
    def hours_to_best(self) -> float | None:
        b = self.best_after
        if b is None:
            return None
        return (b[0] - self.stop_ts).total_seconds() / 3600.0


# ------------------------------------------------------------- assembly --
def z_series(rows: list[dict], pair: str) -> list[tuple[datetime, float]]:
    """Every recorded z for one pair, in time order.

    Assembled from all event types that carry one -- hourly
    `ai_spread_assessment` records are the dense source, with `enter`, `exit`
    and `stop` filling in the decision bars.
    """
    out = []
    for r in rows:
        if r.get("pair") != pair:
            continue
        z, t = _f(r.get("z")), _ts(r)
        if z is not None and t is not None:
            out.append((t, z))
    out.sort(key=lambda p: p[0])
    return out


def _decision_pnl(enter: dict, close: dict) -> float | None:
    """P&L from the decision-time prices either end of the trade.

    Not the same as the filled P&L -- `fills_report.py` is the authority there
    -- but it is self-contained in the ledger, and it is measured over the same
    two z readings the counterfactual uses, which is what makes the ratio
    meaningful.
    """
    qa, qb = _f(enter.get("qa")), _f(enter.get("qb"))
    pa0, pb0 = _f(enter.get("price_a")), _f(enter.get("price_b"))
    pa1, pb1 = _f(close.get("price_a")), _f(close.get("price_b"))
    side = enter.get("side")
    if None in (qa, qb, pa0, pb0, pa1, pb1) or side in (None, 0):
        return None
    s = 1.0 if side > 0 else -1.0
    # side>0 is long the spread: long leg a, short leg b.
    return s * qa * (pa1 - pa0) - s * qb * (pb1 - pb0)


def stop_cases(rows: list[dict], band: float) -> list[StopCase]:
    rows = sorted(rows, key=lambda r: r.get("ts", ""))
    cases: list[StopCase] = []
    open_enter: dict[str, dict] = {}

    for r in rows:
        ev, pair = r.get("event"), r.get("pair")
        if ev == "enter":
            open_enter[pair] = r
        elif ev in ("exit", "refit_drop", "news_derisk", "kill_switch"):
            open_enter.pop(pair, None)
        elif ev == "stop":
            entry = open_enter.pop(pair, None)
            t = _ts(r)
            if t is None:
                continue
            cases.append(StopCase(
                pair=pair,
                stop_ts=t,
                entry_ts=_ts(entry) if entry else None,
                entry_z=_f(entry.get("z")) if entry else None,
                stop_z_reading=_f(r.get("z")) or 0.0,
                band=band,
                side=r.get("side") or (entry or {}).get("side") or 0,
                hold_bars=r.get("hold_bars"),
                pnl=_decision_pnl(entry, r) if entry else None,
            ))

    for case in cases:
        series = z_series(rows, case.pair)
        case.path_after = [
            (t, z) for t, z in series
            if 0 < (t - case.stop_ts).total_seconds() <= WATCH_HOURS * 3600]
    return cases


# -------------------------------------------------------------- summary --
def summarise(cases: list[StopCase]) -> dict:
    over = [c.overshoot for c in cases if c.overshoot is not None]
    costs = [c.overshoot_cost for c in cases if c.overshoot_cost is not None]
    reverted = [c for c in cases if c.reverted]
    return {
        "stops": len(cases),
        "median_overshoot_sigma": (round(statistics.median(over), 2)
                                   if over else None),
        "max_overshoot_sigma": round(max(over), 2) if over else None,
        "stops_within_0_5_sigma_of_band": sum(1 for o in over if o <= 0.5),
        "stops_beyond_1_sigma_of_band": sum(1 for o in over if o > 1.0),
        "total_overshoot_cost": round(sum(costs), 2) if costs else None,
        "reverted_within_watch": f"{len(reverted)}/{len(cases)}",
        "verdict_hint": _verdict(cases, over),
    }


def _verdict(cases: list[StopCase], over: list[float]) -> str:
    """State which repair the evidence points at, or that it does not.

    Deliberately blunt about an inconclusive read: two different defects are
    on the table and picking one on a coin-flip is worse than saying so.
    """
    if not cases or not over:
        return "no stops recorded"
    late = sum(1 for o in over if o > 1.0)
    at_band = sum(1 for o in over if o <= 0.5)
    reverted = sum(1 for c in cases if c.reverted)
    if late and late >= at_band:
        return ("stops fire LATE -> the sampling interval is the defect, "
                "not the level (intra-bar monitoring)")
    if at_band and reverted == len(cases):
        return ("stops fire AT the band and the spread reverts every time -> "
                "the level may be mis-calibrated (stop_z)")
    if at_band and reverted < len(cases):
        return ("stops fire at the band and the spread does NOT always revert "
                "-> the stop is doing its job; leave it alone")
    return "mixed / insufficient evidence to choose a repair"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--stop-z", type=float, default=None,
                    help="band to measure against; default reads AgentConfig")
    ap.add_argument("--json", metavar="PATH")
    args = ap.parse_args()

    band = args.stop_z
    if band is None:
        from deploy.ltp_agent import AgentConfig       # noqa: PLC0415
        band = AgentConfig().stop_z

    rows = load_ledger(Path(args.ledger))
    cases = stop_cases(rows, band)

    print("=" * 78)
    print(f"stop analysis  —  band ±{band:.2f}, watching {WATCH_HOURS:.0f}h "
          f"after each stop")
    print("=" * 78)
    if not cases:
        print("  no stop events in the ledger")
        return 0

    print(f"  {'pair':12s} {'when':16s} {'entry z':>8s} {'stop z':>8s} "
          f"{'over':>6s} {'pnl':>8s} {'@band':>8s} {'cost':>7s} "
          f"{'best after':>11s} {'hrs':>5s}")
    for c in sorted(cases, key=lambda c: c.stop_ts):
        b = c.best_after
        def fmt(v, w=8, p=2):
            return f"{v:>{w}.{p}f}" if isinstance(v, float) else f"{'-':>{w}}"
        print(f"  {c.pair:12s} {c.stop_ts.strftime('%Y-%m-%d %H:%M')} "
              f"{fmt(c.entry_z)} {fmt(c.stop_z_reading)} "
              f"{fmt(c.overshoot, 6)} {fmt(c.pnl)} {fmt(c.loss_at_band)} "
              f"{fmt(c.overshoot_cost, 7)} "
              f"{fmt(b[1] if b else None, 11)} {fmt(c.hours_to_best, 5, 1)}")

    print()
    for k, v in summarise(cases).items():
        print(f"  {k:32s} {v}")

    print("\n  reading the columns")
    print("    over   = sigma past the band before the stop actually fired.")
    print("             Large values are a MONITORING failure, not a level one.")
    print("    @band  = what the loss would have been stopping exactly at the")
    print("             band. 'cost' is the difference — the price of looking")
    print("             once an hour.")
    print("    best after = most favourable z reached within the watch window.")
    print("             Inside the band means the spread reverted and the stop")
    print("             forfeited a recovery — the honest cost of insurance.")

    if args.json:
        Path(args.json).write_text(json.dumps({
            "band": band,
            "summary": summarise(cases),
            "cases": [{
                "pair": c.pair, "stop_ts": c.stop_ts.isoformat(),
                "entry_ts": c.entry_ts.isoformat() if c.entry_ts else None,
                "entry_z": c.entry_z, "stop_z_reading": c.stop_z_reading,
                "overshoot": c.overshoot, "pnl": c.pnl,
                "loss_at_band": c.loss_at_band,
                "overshoot_cost": c.overshoot_cost,
                "rate_per_z": c.rate_per_z,
                "best_after_z": c.best_after[1] if c.best_after else None,
                "hours_to_best": c.hours_to_best,
                "reverted": c.reverted,
                "hold_would_have": c.hold_would_have,
            } for c in sorted(cases, key=lambda c: c.stop_ts)],
        }, indent=2, default=str))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
