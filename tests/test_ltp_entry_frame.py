"""
An exit must say whether the spread came back, or the target came to us.

`mu` is re-estimated at every refit over a trailing 3*half_life window, so on a
trending spread the equilibrium walks toward the price and can overtake it. The
position then closes "reverted" having never returned to where it was opened.

Observed live on 2026-08-05: a short spread entered at z=+0.717 exited at
z=-0.109 tagged `reverted`, while the spread itself ROSE 0.0101 — a -4.11 loss
under a reasoning line asserting "the mean-reversion cycle completed". It had
not. Solving back, the mean had moved ~1.3 sigma during the 38-hour hold.

Nothing here changes what the agent trades. It changes what the agent can be
caught claiming, which for a Reasoning Audit is the same kind of defect as the
three logging holes closed on 2026-08-02.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.ltp_agent import (                          # noqa: E402
    MU_SHIFT_MATERIAL, entry_frame, reversion_note,
)


def _pair(entry_mu=-0.2164, entry_sigma=0.02, mu=None):
    return {"entry_mu": entry_mu, "entry_sigma": entry_sigma,
            "mu": entry_mu if mu is None else mu, "sigma": entry_sigma}


def test_a_still_equilibrium_reports_the_same_z_and_no_annotation():
    # Spread returns to the entry mean, and the mean never moved.
    frame = entry_frame(_pair(), spread=-0.2164)
    assert round(frame["z_in_entry_coords"], 3) == 0.0
    assert round(frame["mu_shift_sigma"], 6) == 0.0
    assert frame["equilibrium_reestimated"] is False
    assert reversion_note(frame, 0.0) == ""


def test_the_live_2026_08_05_exit_is_flagged():
    """Entry mu -0.216437, sigma ~0.02. The spread rose to -0.206343 while the
    re-estimated mean rose further still, to about -0.190."""
    pair = _pair(entry_mu=-0.216437, entry_sigma=0.02, mu=-0.190)
    frame = entry_frame(pair, spread=-0.206343)

    # In the coordinates it was ENTERED on, the spread has not come back --
    # it moved AWAY from the mean, which for a short spread is the loss.
    assert frame["z_in_entry_coords"] > 0.4
    assert frame["mu_shift_sigma"] > 1.0
    assert frame["equilibrium_reestimated"] is True

    note = reversion_note(frame, 0.0)
    assert "re-estimated" in note
    assert "not only the spread returning" in note
    assert "+1.3" in note or "+1.32" in note


def test_ordinary_refit_noise_is_not_annotated():
    """The flag has to stay rare or it stops meaning anything."""
    small = _pair(mu=-0.2164 + 0.5 * MU_SHIFT_MATERIAL * 0.02)
    frame = entry_frame(small, spread=-0.2164)
    assert frame["equilibrium_reestimated"] is False
    assert reversion_note(frame, 0.0) == ""

    big = _pair(mu=-0.2164 + 1.5 * MU_SHIFT_MATERIAL * 0.02)
    assert entry_frame(big, spread=-0.2164)["equilibrium_reestimated"] is True


def test_a_drift_in_either_direction_counts():
    """A long spread is hurt by the mean drifting DOWN, so the test is on the
    magnitude, not the sign."""
    down = _pair(mu=-0.2164 - 0.5 * 0.02)
    assert entry_frame(down, spread=-0.2164)["equilibrium_reestimated"] is True
    assert entry_frame(down, spread=-0.2164)["mu_shift_sigma"] < 0


def test_missing_or_degenerate_entry_coordinates_return_nothing():
    """Absence must read as 'unknown', never as 'the mean held steady' — a
    position opened before this shipped has no entry frame to compare."""
    assert entry_frame({"mu": 0.0, "sigma": 0.02}, spread=0.0) == {}
    assert entry_frame(_pair(entry_sigma=0.0), spread=0.0) == {}
    assert entry_frame(_pair(entry_sigma=None), spread=0.0) == {}
    assert entry_frame(_pair(entry_mu=None), spread=0.0) == {}
    assert reversion_note({}, 0.0) == ""


def test_the_entry_snapshot_survives_a_refit():
    """The refit replaces mu and sigma wholesale. If the entry coordinates go
    with them, an open position loses all record of what it was opened
    against — which is exactly the state that hid the 2026-08-05 exit."""
    import re
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "deploy", "ltp_agent.py")) as fh:
        src = fh.read()
    block = src[src.index('state["pairs"] = {'):][:600]
    for key in ("entry_mu", "entry_sigma"):
        assert re.search(rf'"{key}": old\.get', block), (
            f"{key} is not carried across the refit, so it is destroyed the "
            f"first time a held pair is re-fitted")


def test_both_close_paths_record_the_frame():
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "deploy", "ltp_agent.py")) as fh:
        src = fh.read()
    for event in ('ledger("stop"', 'ledger("exit"'):
        i = src.index(event)
        assert "**frame" in src[i:i + 400], (
            f"{event} does not carry the entry-frame fields, so the mean "
            f"having moved would be invisible on that path")
