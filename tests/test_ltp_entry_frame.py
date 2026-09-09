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


def _pair(entry_mu=-0.2164, entry_sigma=0.02, mu=None, entry_beta=1.0):
    return {"entry_mu": entry_mu, "entry_sigma": entry_sigma,
            "entry_beta": entry_beta,
            "mu": entry_mu if mu is None else mu, "sigma": entry_sigma}


def _frame(pair, spread):
    """entry_frame with leg prices that reproduce `spread` on beta=1.0.

    The frame must be rebuilt from the LEGS on the entry beta, so the helper
    supplies them: log_a = spread, log_b = 0 gives log_a - 1.0*log_b = spread.
    """
    return entry_frame(pair, spread, log_a=spread, log_b=0.0)


def test_a_still_equilibrium_reports_the_same_z_and_no_annotation():
    # Spread returns to the entry mean, and the mean never moved.
    frame = _frame(_pair(), spread=-0.2164)
    assert round(frame["z_in_entry_coords"], 3) == 0.0
    assert round(frame["mu_shift_sigma"], 6) == 0.0
    assert frame["equilibrium_reestimated"] is False
    assert reversion_note(frame, 0.0, side=1) == ""


def test_the_live_2026_08_05_exit_is_flagged():
    """Entry mu -0.216437, sigma ~0.02. The spread rose to -0.206343 while the
    re-estimated mean rose further still, to about -0.190."""
    pair = _pair(entry_mu=-0.216437, entry_sigma=0.02, mu=-0.190)
    frame = _frame(pair, spread=-0.206343)

    # In the coordinates it was ENTERED on, the spread has not come back --
    # it moved AWAY from the mean, which for a short spread is the loss.
    assert frame["z_in_entry_coords"] > 0.4
    assert frame["mu_shift_sigma"] > 1.0
    assert frame["equilibrium_reestimated"] is True

    note = reversion_note(frame, 0.0, side=-1)
    assert "re-estimated" in note
    assert "not only the spread returning" in note
    assert "would NOT have triggered this exit" in note
    assert "+1.3" in note or "+1.32" in note


def test_ordinary_refit_noise_is_not_annotated():
    """The flag has to stay rare or it stops meaning anything."""
    small = _pair(mu=-0.2164 + 0.5 * MU_SHIFT_MATERIAL * 0.02)
    frame = _frame(small, spread=-0.2164)
    assert frame["equilibrium_reestimated"] is False
    assert reversion_note(frame, 0.0, side=1) == ""

    big = _pair(mu=-0.2164 + 1.5 * MU_SHIFT_MATERIAL * 0.02)
    assert _frame(big, spread=-0.2164)["equilibrium_reestimated"] is True


def test_a_drift_in_either_direction_counts():
    """A long spread is hurt by the mean drifting DOWN, so the test is on the
    magnitude, not the sign."""
    down = _pair(mu=-0.2164 - 0.5 * 0.02)
    assert _frame(down, spread=-0.2164)["equilibrium_reestimated"] is True
    assert _frame(down, spread=-0.2164)["mu_shift_sigma"] < 0


def test_missing_or_degenerate_entry_coordinates_return_nothing():
    """Absence must read as 'unknown', never as 'the mean held steady' — a
    position opened before this shipped has no entry frame to compare."""
    assert _frame({"mu": 0.0, "sigma": 0.02}, spread=0.0) == {}
    assert _frame(_pair(entry_sigma=0.0), spread=0.0) == {}
    assert _frame(_pair(entry_sigma=None), spread=0.0) == {}
    assert _frame(_pair(entry_mu=None), spread=0.0) == {}
    assert reversion_note({}, 0.0, side=1) == ""

    # No entry beta, or no leg prices, means the frame CANNOT be rebuilt. It
    # must refuse rather than fall back to the caller's live-beta spread --
    # that fallback is the 2026-09-09 bug, and it fails silently and plausibly.
    assert _frame(_pair(entry_beta=None), spread=0.0) == {}
    assert entry_frame(_pair(), spread=0.0) == {}
    assert entry_frame(_pair(), spread=0.0, log_a=0.0) == {}


def test_the_entry_snapshot_survives_a_refit():
    """The refit replaces mu and sigma wholesale. If the entry coordinates go
    with them, an open position loses all record of what it was opened
    against — which is exactly the state that hid the 2026-08-05 exit."""
    import re
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "deploy", "ltp_agent.py")) as fh:
        src = fh.read()
    block = src[src.index('state["pairs"] = {'):][:1400]
    for key in ("entry_mu", "entry_sigma", "entry_beta"):
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


# --------------------------------------------------------------------------
# The regression this file did not have: a beta that MOVED.
#
# Every test above holds beta fixed, so the frame could be rebuilt on the live
# beta and nothing would notice. The live 2026-08-20 KAS/ETC stop is the case
# where it moved, and there `z_in_entry_coords` was logged as +3.597 when the
# truth was -3.283 -- wrong in sign and in magnitude, in the field the
# Reasoning Log cites as evidence of honest frame accounting.
#
# mu0 and sigma0 below are not guesses. They are recovered from the five
# in-epoch price prints between the 08-18 and 08-19 refits, and every one of
# the ten point-pairs returns the same values to eight decimals; they then
# reproduce all five logged z readings to six. Making +3.597 true would need
# sigma0 = -0.0099, which is what impossible looks like.
# --------------------------------------------------------------------------

import math

KAS_MU0, KAS_SIG0 = -5.42792565, 0.01085687
KAS_BETA_ENTRY = 0.9721173236438992     # fitted with mu0/sigma0
KAS_BETA_REFIT = 0.9326583952255416     # after the refit during the hold
KAS_PRICE_A, KAS_PRICE_B = 0.026695, 6.63976937          # at the stop


def _kas_pair():
    return {"entry_mu": KAS_MU0, "entry_sigma": KAS_SIG0,
            "entry_beta": KAS_BETA_ENTRY,
            "mu": KAS_MU0 + 6.4427890684070634 * KAS_SIG0,
            "sigma": KAS_SIG0 * 2.047}


def test_the_frame_is_rebuilt_on_the_entry_beta_not_the_live_one():
    la, lb = math.log(KAS_PRICE_A), math.log(KAS_PRICE_B)
    live_spread = la - KAS_BETA_REFIT * lb        # what the caller computes
    frame = entry_frame(_kas_pair(), live_spread, log_a=la, log_b=lb)

    # The truth, from the entry beta.
    assert round(frame["z_in_entry_coords"], 3) == -3.283
    # The number that was actually logged for eight months of this field's
    # life. If this ever comes back, the beta is being ignored again.
    assert round(frame["z_in_entry_coords"], 3) != 3.597


def test_the_stop_did_not_overshoot_in_its_own_coordinates():
    """The operational consequence, and the reason task 01's row 7 is an upper
    bound: at -3.28 the 3.5 band was honoured. The 1.25 sigma 'overshoot' was
    an artefact of measuring a new-beta spread against an old-beta frame."""
    la, lb = math.log(KAS_PRICE_A), math.log(KAS_PRICE_B)
    frame = entry_frame(_kas_pair(), la - KAS_BETA_REFIT * lb,
                        log_a=la, log_b=lb)
    assert abs(frame["z_in_entry_coords"]) < 3.5


def test_the_note_tests_its_own_claim_instead_of_asserting_it():
    """It used to fire on any material mu_shift and assert the spread was
    'not inside +/-exit_z', borrowing the symmetric abs(z) < exit_z form the
    exit rule had already abandoned as unable to express exit_z = 0. So it
    never checked. The record's one confession of frame drift was a false
    alarm on a +6.03 winner."""
    # A long position whose entry-frame z is well past the exit band: the
    # equilibrium moved, and it would NOT have exited on its own coordinates.
    moved = _pair(mu=-0.2164 + 2.0 * 0.02)
    assert reversion_note(_frame(moved, spread=-0.2564), 0.0, side=1) != ""

    # Same drift, but the spread genuinely came back past the exit band in the
    # entry frame too. The exit was honest and the note must stay silent.
    assert reversion_note(_frame(moved, spread=-0.1964), 0.0, side=1) == ""
