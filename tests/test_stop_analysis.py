"""
Guards on the stop counterfactual.

This decides between two different repairs to a live risk control, so the
arithmetic under it has to be pinned and its sign conventions have to be
unambiguous:

  * OVERSHOOT must measure distance past the band, not |z|. A stop at -10.25
    against a 3.5 band overshot by 6.75, and reading that as 10.25 would blame
    the level for what the sampling interval did.
  * The counterfactual rate comes from each trade's OWN entry and stop, so a
    trade whose sigma differs from another's is not compared on a shared
    fiction.
  * "Reverted" must mean the spread came back INSIDE the band, not merely that
    it moved a little -- otherwise every stop looks vindicated or every stop
    looks wrong, depending on which way you squint.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.stop_analysis import (                     # noqa: E402
    StopCase, stop_cases, summarise, z_series, _verdict,
)

PAIR = "AVAX/SOL"
T0 = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)


def _iso(hours):
    return (T0 + timedelta(hours=hours)).isoformat()


def _enter(z, hours=0, qa=62.0, qb=2.71, pa=6.4, pb=73.0, side=1):
    return {"ts": _iso(hours), "event": "enter", "pair": PAIR, "side": side,
            "z": z, "qa": qa, "qb": qb, "price_a": pa, "price_b": pb}


def _stop(z, hours, pa, pb, side=1):
    return {"ts": _iso(hours), "event": "stop", "pair": PAIR, "side": side,
            "z": z, "price_a": pa, "price_b": pb, "hold_bars": hours}


def _tick(z, hours):
    return {"ts": _iso(hours), "event": "ai_spread_assessment",
            "pair": PAIR, "z": z}


def test_overshoot_is_distance_past_the_band_not_absolute_z():
    """The Aug 1 case: z=-10.25 against a 3.5 band is 6.75 late."""
    rows = [_enter(-1.39), _stop(-10.25, 11, 6.1, 71.0, side=1)]
    (case,) = stop_cases(rows, band=3.5)
    assert round(case.overshoot, 2) == 6.75
    assert case.stop_z_reading == -10.25

    # A stop that honours the band overshoots by zero, never by a negative.
    rows = [_enter(1.74, side=-1), _stop(3.63, 13, 6.5, 73.0, side=-1)]
    (case,) = stop_cases(rows, band=3.5)
    assert round(case.overshoot, 2) == 0.13
    rows = [_enter(1.74, side=-1), _stop(3.40, 13, 6.5, 73.0, side=-1)]
    (case,) = stop_cases(rows, band=3.5)
    assert case.overshoot == 0.0


def test_counterfactual_uses_the_trades_own_rate():
    """Loss is linear in z, and the slope comes from this trade, not a global
    assumption -- sigma differs between fits, so a shared rate would be a
    fiction dressed as a measurement."""
    # Long the spread: 62 AVAX at 6.40 -> 6.10 is -18.60; short 2.71 SOL at
    # 73.00 -> 72.00 is +2.71. Net -15.89 over dz = -10.25 - (-1.39) = -8.86.
    rows = [_enter(-1.39), _stop(-10.25, 11, 6.10, 72.00)]
    (case,) = stop_cases(rows, band=3.5)
    assert round(case.pnl, 2) == -15.89
    assert round(case.rate_per_z, 3) == round(-15.89 / -8.86, 3)

    # Stopping at the band would have cost the rate times (-3.5 - -1.39).
    expected = case.rate_per_z * (-3.5 - -1.39)
    assert round(case.loss_at_band, 2) == round(expected, 2)
    # ... and the overshoot cost is the difference, a NEGATIVE number because
    # the extra distance was extra loss.
    assert case.overshoot_cost < 0
    assert round(case.overshoot_cost, 2) == round(case.pnl - expected, 2)


def test_reversion_requires_coming_back_inside_the_band():
    rows = [_enter(-1.39), _stop(-10.25, 11, 6.10, 72.00),
            _tick(-8.0, 12), _tick(-4.0, 13), _tick(-1.03, 18)]
    (case,) = stop_cases(rows, band=3.5)
    assert case.reverted is True
    assert round(case.best_after[1], 2) == -1.03
    assert round(case.hours_to_best, 1) == 7.0
    # Holding to that level would have lost far less than the stop realised.
    assert case.hold_would_have > case.pnl

    # A spread that never comes back has not reverted, however much it wiggles.
    rows = [_enter(-1.39), _stop(-10.25, 11, 6.10, 72.00),
            _tick(-9.0, 12), _tick(-11.0, 20)]
    (case,) = stop_cases(rows, band=3.5)
    assert case.reverted is False


def test_a_later_stop_does_not_borrow_the_earlier_ones_entry():
    rows = [
        _enter(-1.39, hours=0),
        _stop(-10.25, 11, 6.10, 72.00),
        _enter(1.74, hours=21, side=-1),
        _stop(3.63, 34, 6.50, 73.00, side=-1),
    ]
    cases = sorted(stop_cases(rows, band=3.5), key=lambda c: c.stop_ts)
    assert len(cases) == 2
    assert cases[0].entry_z == -1.39
    assert cases[1].entry_z == 1.74


def test_an_exit_between_trades_clears_the_open_entry():
    """A stop must never pair with an entry that a reverted exit already
    closed, or its P&L and its z span both belong to the wrong trade."""
    rows = [
        _enter(-1.39, hours=0),
        {"ts": _iso(4), "event": "exit", "pair": PAIR, "side": 1,
         "reason": "reverted", "z": -0.02, "price_a": 6.5, "price_b": 73.2},
        _stop(3.63, 34, 6.50, 73.00, side=-1),
    ]
    (case,) = stop_cases(rows, band=3.5)
    assert case.entry_z is None, "the stop borrowed a closed trade's entry"
    assert case.pnl is None


def test_the_watch_window_does_not_reach_into_a_later_excursion():
    from deploy.stop_analysis import WATCH_HOURS
    rows = [_enter(-1.39), _stop(-10.25, 11, 6.10, 72.00),
            _tick(-2.0, 12), _tick(-0.1, 12 + WATCH_HOURS + 5)]
    (case,) = stop_cases(rows, band=3.5)
    assert round(case.best_after[1], 2) == -2.0, "watch window leaked"


def test_z_series_is_pair_scoped_and_ordered():
    rows = [_tick(1.0, 5), {"ts": _iso(1), "event": "ai_spread_assessment",
                            "pair": "FIL/AR", "z": 9.9}, _tick(2.0, 2)]
    series = z_series(rows, PAIR)
    assert [round(z, 1) for _, z in series] == [2.0, 1.0]


def test_the_verdict_names_a_repair_or_refuses_to_pick_one():
    """Two different defects are on the table -- a late sampling interval and a
    mis-calibrated level -- and guessing between them is worse than saying the
    evidence is mixed."""
    late = [StopCase(PAIR, T0, None, -1.4, -10.25, 3.5, 1, None, None)]
    assert "sampling interval" in _verdict(late, [6.75])

    at_band = StopCase(PAIR, T0, None, 1.74, 3.6, 3.5, -1, None, None)
    at_band.path_after = [(T0 + timedelta(hours=2), 0.1)]
    assert "mis-calibrated" in _verdict([at_band], [0.1])

    held = StopCase(PAIR, T0, None, 1.74, 3.6, 3.5, -1, None, None)
    held.path_after = [(T0 + timedelta(hours=2), 4.9)]
    assert "doing its job" in _verdict([held], [0.1])

    assert _verdict([], []) == "no stops recorded"


def test_summary_counts_do_not_divide_by_zero_on_an_empty_ledger():
    s = summarise([])
    assert s["stops"] == 0
    assert s["median_overshoot_sigma"] is None
    assert s["verdict_hint"] == "no stops recorded"
