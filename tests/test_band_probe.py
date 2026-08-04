"""
Guards on the band diagnostic's two blind spots.

Both cost real analysis time before being fixed:

  * The fee-sweep columns are MULTIPLIERS of cfg.taker_fee, but their labels
    were hardcoded strings. After taker_fee changed 5e-4 -> 2e-4 the column
    reading "2.5bp" was really 1.0bp, and two runs either side of that change
    were compared as if the fee were constant -- producing a confident and
    wrong conclusion about why a band moved.
  * The optimiser reports only an argmax, and its a_grid starts at 0.4, so a
    reported 0.4 cannot be told apart from an optimum that lies below the grid.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.band_diagnostic import (                   # noqa: E402
    CUR_A, PROBE_A, entry_rate_curve, fee_label,
)
from statarb.ou import OUParams                        # noqa: E402


def test_fee_labels_are_derived_from_the_config_not_hardcoded():
    """A label that can silently stop being true is worse than no label."""
    assert fee_label(5e-4, 1.00, "live") == "5.00bp live"
    assert fee_label(5e-4, 0.50, "half") == "2.50bp half"
    # The same column, after the config changed, must NOT still read 2.5bp.
    assert fee_label(2e-4, 0.50, "half") == "1.00bp half"
    assert fee_label(2e-4, 1.00, "live") == "2.00bp live"
    assert fee_label(2e-4, 0.00, "free") == "0.00bp free"


def test_the_probe_grid_reaches_below_the_live_grid_floor():
    """Otherwise the clamping question cannot even be asked."""
    assert PROBE_A[0] < CUR_A[0], (
        "the probe must go below the live a_grid floor of "
        f"{CUR_A[0]}, or 'optimal' and 'clamped' stay indistinguishable")
    assert CUR_A[0] == 0.4


def _ou(half_life_bars=17.6, sigma_eq=0.02):
    theta = np.log(2.0) / half_life_bars
    return OUParams(theta=theta, mu=0.0,
                    sigma=sigma_eq * np.sqrt(2.0 * theta),
                    sigma_eq=sigma_eq, half_life=half_life_bars)


def test_the_rate_curve_covers_the_whole_probe_and_flags_untradeable_cells():
    curve = entry_rate_curve(_ou(), roundtrip_cost=0.0006, entries=PROBE_A)
    assert len(curve) == len(PROBE_A)
    priced = [(a, r) for a, r in curve if r is not None]
    assert priced, "a viable pair must price somewhere on the probe"
    # Entries at or under the exit band cannot make money and must be None,
    # not a fabricated rate.
    assert all(r is None for a, r in curve if a <= 0.1)


def test_a_high_cost_pair_prices_nowhere_rather_than_returning_a_number():
    """cost_z above the widest band means untradeable -- it must not silently
    report the least-bad cell as though it were profitable."""
    curve = entry_rate_curve(_ou(sigma_eq=0.0005), roundtrip_cost=0.01,
                             entries=PROBE_A)
    assert all(r is None for _, r in curve)


def test_lower_costs_move_the_unconstrained_optimum_toward_a_tighter_entry():
    """The direction that matters: cheaper execution wants a tighter band, and
    at some point that optimum passes below what the live grid can report."""
    def argmax(cost):
        priced = [(a, r) for a, r in
                  entry_rate_curve(_ou(), cost, PROBE_A) if r is not None]
        return max(priced, key=lambda p: p[1])[0]

    assert argmax(0.0020) >= argmax(0.0006) >= argmax(0.0)
