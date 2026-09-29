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


# --------------------------------------------------------------------------
# The same bug class, one line over: `mu_shift_sigma` across two betas.
#
# The 09-09 fix rebuilt the SPREAD on the entry beta and left `mu_shift`
# comparing `entry_mu` (fitted on beta0) with a live `mu` fitted on beta1. A
# refit that moves beta shifts the spread's LEVEL by ~(beta1-beta0)*mean(log_b)
# -- nothing to do with the equilibrium -- and a small sigma0 turns that into
# double-digit sigmas. Found at the 2026-09-27 review; every nonzero Phase II
# shift was >=90% this.
# --------------------------------------------------------------------------

import numpy as np                                        # noqa: E402

from deploy.ltp_agent import (                            # noqa: E402
    live_mu_on_entry_beta, window_mean_on_beta,
)


def _stationary_pair(beta0=0.7119, dbeta=0.023, shift_sigmas=0.0, seed=7):
    """A spread stationary on beta0 (optionally with a real equilibrium shift
    added late), a position opened at bar 800, and a refit at bar 900 that
    fits a different beta -- the 09-15 geometry."""
    rng = np.random.default_rng(seed)
    n, hl = 960, 13.0
    lb = np.log(0.083) + np.cumsum(rng.normal(0, 0.004, n))   # DOGE-like leg
    eps = np.zeros(n)
    for t in range(1, n):                                     # AR(1) noise
        eps[t] = 0.5 * eps[t - 1] + rng.normal(0, 0.003)
    la = -3.18 + beta0 * lb + eps
    w = int(3 * hl)
    s0 = la[:800] - beta0 * lb[:800]
    mu0, sig0 = float(np.mean(s0[-w:])), float(np.std(s0[-w:], ddof=1))
    la = la.copy()
    la[850:] += shift_sigmas * sig0                           # a REAL move
    beta1 = beta0 + dbeta
    s1 = la[:900] - beta1 * lb[:900]
    pair = {"entry_mu": mu0, "entry_sigma": sig0, "entry_beta": beta0,
            "beta": beta1, "mu": float(np.mean(s1[-w:])),
            "sigma": float(np.std(s1[-w:], ddof=1)),
            "mu_entry_beta": window_mean_on_beta(la[:900], lb[:900], beta0, hl),
            "mu_entry_beta_basis": beta0}
    return pair, la[899], lb[899]


def _shifts(**kw):
    pair, la, lb = _stationary_pair(**kw)
    old = (pair["mu"] - pair["entry_mu"]) / pair["entry_sigma"]   # the old line
    frame = entry_frame(pair, la - pair["beta"] * lb, log_a=la, log_b=lb)
    return old, frame


def test_a_beta_change_alone_no_longer_moves_the_shift():
    """The exact property: the refit's beta must not enter the shift at all.
    The old line swings by tens of sigma across plausible beta changes -- the
    09-26 (+0.0018), 09-15 (+0.023) and 09-27 ETH/BTC (-0.042) sizes -- while
    the new one is identical to machine precision."""
    runs = [_shifts(dbeta=d) for d in (0.0018, 0.023, -0.042)]
    olds = [o for o, _ in runs]
    news = [f["mu_shift_sigma"] for _, f in runs]
    assert max(olds) - min(olds) > 10          # the artefact, reproduced
    assert max(news) - min(news) < 1e-9        # the fix: beta-invariant
    assert all(f["mu_shift_basis"] == "entry_beta" for _, f in runs)


def test_a_genuine_equilibrium_move_still_registers_exactly():
    """The fix must not blind the field. A real 2-sigma move in the spread,
    on the entry beta, adds exactly 2.00 to the shift."""
    _, still = _shifts(shift_sigmas=0.0)
    _, moved = _shifts(shift_sigmas=2.0)
    assert abs((moved["mu_shift_sigma"] - still["mu_shift_sigma"]) - 2.0) < 1e-9
    assert moved["equilibrium_reestimated"] is True


def test_a_value_computed_for_another_position_is_never_used():
    """`mu_entry_beta` survives until the next refit. If the position closes
    and a new one opens on a different beta inside that window, the old value
    is for the wrong spread -- so it is tagged, and a mismatched tag means
    'unavailable', never 'no drift'."""
    pair, la, lb = _stationary_pair()
    pair["mu_entry_beta_basis"] = pair["entry_beta"] + 0.05
    frame = entry_frame(pair, la - pair["beta"] * lb, log_a=la, log_b=lb)
    assert frame["mu_shift_sigma"] is None
    assert frame["mu_shift_basis"] == "unavailable"
    assert frame["equilibrium_reestimated"] is False
    assert reversion_note(frame, 0.0, side=-1) == ""
    # ...while the entry-frame z, which never depended on it, is still there.
    assert frame["z_in_entry_coords"] is not None


def test_an_unchanged_beta_uses_the_live_mean_directly():
    p = {"beta": 0.8, "mu": -1.0}
    assert live_mu_on_entry_beta(p, 0.8) == -1.0
    assert live_mu_on_entry_beta({"beta": 0.9, "mu": -1.0}, 0.8) is None


def test_the_refit_reexpresses_held_pairs_on_their_entry_beta():
    with open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "deploy", "ltp_agent.py")) as fh:
        src = fh.read()
    block = src[src.index("def refit("):src.index("def leg_close(")]
    assert "window_mean_on_beta(" in block
    assert '"mu_entry_beta_basis"' in block


# The week 8 table, pinned. These are the record's own numbers, recomputed
# from the ledger's enter/stop prints; if the decomposition is wrong, this is
# where it should fail rather than in a paragraph nobody re-reads.

def _decompose(b0, pa0, pb0, z0, pa1, pb1, ze, ms, b1):
    s0e = math.log(pa0) - b0 * math.log(pb0)
    s0c = math.log(pa1) - b0 * math.log(pb1)
    sig0 = (s0c - s0e) / (ze - z0)
    artefact = -(b1 - b0) * math.log(pb1) / sig0
    return sig0, artefact, ms - artefact


def test_the_2026_09_15_thirteen_sigma_drift_was_the_beta_change():
    sig0, art, same = _decompose(
        0.7118725634324035, 0.00515347, 0.08266, -0.9568413930801298,
        0.00500676, 0.08083938, -3.991, 13.242116734981003, 0.735)
    assert round(sig0, 5) == 0.00429
    assert 13.0 < art < 14.0          # the whole reported 13.24
    assert abs(same) < 0.6            # on one beta: nothing material


def test_the_2026_09_26_stop_shift_was_the_beta_change():
    sig0, art, same = _decompose(
        0.8401811669626558, 0.00594101, 0.09851, 0.608,
        0.00607, 0.09839, 7.3334732640404, 1.1186371304814982, 0.842)
    assert round(sig0, 6) == 0.003346
    assert abs(same) < 0.3
