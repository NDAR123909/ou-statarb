"""
Tests for the profit-taking exit condition.

Regression: the exit used `abs(z) < exit_z`, a symmetric band. That agreed
with the intended behaviour only because the band optimiser was pinning
exit_z at 1.5 for every pair. Fixing the optimiser produced exit_z = 0.0 --
"take profit when the spread returns to its mean" -- and `abs(z) < 0.0` is
never true, so a live position had NO reachable profit exit and could only
leave via the structural-break stop or the max-hold clock.

The exit is directional because the position is: a long spread is opened
below the mean and profits as z rises, so it should close once z climbs back
to -exit_z. The short side mirrors.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def reverted(side: float, z: float, exit_z: float) -> bool:
    """Mirror of the condition in ltp_agent.trade_step."""
    return (side > 0 and z >= -exit_z) or (side < 0 and z <= exit_z)


# --- exit_z = 0 must be reachable (the live failure) -------------------------

def test_long_spread_takes_profit_at_the_mean():
    assert not reverted(+1, -1.17, 0.0)     # still below the mean: hold
    assert not reverted(+1, -0.30, 0.0)
    assert reverted(+1, 0.00, 0.0)          # reached the mean: take profit
    assert reverted(+1, +0.40, 0.0)         # overshot: still an exit


def test_short_spread_takes_profit_at_the_mean():
    assert not reverted(-1, +1.17, 0.0)
    assert reverted(-1, 0.00, 0.0)
    assert reverted(-1, -0.40, 0.0)


# --- behaviour with a positive exit band is unchanged ------------------------

def test_positive_exit_band_matches_the_old_behaviour():
    """For exit_z > 0 the directional form agrees with the symmetric one on
    the path a position actually travels, so nothing regresses."""
    for z in (-3.0, -2.0, -1.6):
        assert not reverted(+1, z, 1.5)     # far below: hold
    for z in (-1.5, -1.0, 0.0, 1.0):
        assert reverted(+1, z, 1.5)         # back inside the band: exit
    for z in (3.0, 2.0, 1.6):
        assert not reverted(-1, z, 1.5)
    for z in (1.5, 1.0, 0.0, -1.0):
        assert reverted(-1, z, 1.5)


def test_a_flat_pair_is_never_reported_as_reverted():
    for z in (-2.0, 0.0, 2.0):
        assert not reverted(0, z, 0.0)
        assert not reverted(0, z, 1.5)


# --- the agent uses exactly this condition -----------------------------------

def test_agent_source_uses_the_directional_form():
    """Guards against a refactor quietly restoring the symmetric test."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "deploy", "ltp_agent.py")).read()
    assert "reverted = (side > 0 and z >= -exit_z)" in src
    assert "reverted = abs(z) <" not in src
