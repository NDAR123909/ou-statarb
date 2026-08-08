"""
A declined entry must leave a trace.

`blocked` is the one-sided re-entry guard: after a stop, that side stays shut
until z heals back inside the entry band (invariant 4). It lived purely in
runtime state, so a signal refused by a risk control looked identical to a bar
where no signal existed. Under a Reasoning Audit that correlates logged
decisions against executed orders, "we declined this" and "nothing happened"
are not the same claim.

Same bug class as refit_drop (no decision record) and size_mult (risk halved,
journal only), both closed 2026-08-02. This is the last one known.

The trap here is over-logging: `want == 0` is the common case on a quiet bar,
and firing an event every time would bury the signal in noise. It must fire
only when the block is genuinely what stopped the trade.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AGENT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "deploy", "ltp_agent.py")


def _entry_branch() -> str:
    with open(AGENT) as fh:
        src = fh.read()
    i = src.index("blocked = pair.get(\"blocked\", 0)")
    return src[i:i + 2600]


def test_a_blocked_signal_is_logged_as_a_skip():
    branch = _entry_branch()
    assert 'reason="side_blocked"' in branch, (
        "a signal refused by the re-entry block writes no ledger event, so it "
        "is indistinguishable from a bar with no signal at all")
    for field in ("blocked=", "side_wanted=", "reasoning="):
        assert field in branch, f"side_blocked skip is missing {field}"


def test_it_fires_only_when_the_block_is_what_stopped_the_trade():
    """`want == 0` on a quiet bar must stay silent, or the event is noise."""
    branch = _entry_branch()
    guard = re.search(
        r"if \(short_zone and blocked == -1\) or \(long_zone and blocked == \+1\):",
        branch)
    assert guard, (
        "the skip must be guarded on the signal actually being inside an "
        "entry zone; logging every want==0 bar buries it")
    # The guard has to come before the ledger call, not after.
    assert guard.start() < branch.index('reason="side_blocked"')


def test_the_block_semantics_are_not_inverted():
    """`blocked` stores the side that stopped: +1 blocks LONG, -1 blocks SHORT.
    Getting this backwards would re-admit exactly the side that just broke."""
    branch = _entry_branch()
    assert "if short_zone and blocked != -1:" in branch
    assert "elif long_zone and blocked != +1:" in branch
    with open(AGENT) as fh:
        src = fh.read()
    assert 'pair["blocked"] = +1 if side > 0 else -1' in src, (
        "the stop no longer records which side broke")


def test_the_healing_threshold_reported_matches_the_heal_condition():
    """The reasoning tells the auditor when the block clears. If that number
    disagrees with the code that actually clears it, the log is lying."""
    branch = _entry_branch()
    assert 'heal_at = -pair["entry_z"] if blocked == +1 else pair["entry_z"]' \
        in branch
    with open(AGENT) as fh:
        src = fh.read()
    # The live heal: blocked +1 clears once z rises past -entry_z; -1 mirrors.
    assert 'if pair.get("blocked", 0) == +1 and z > -pair["entry_z"]:' in src
    assert 'elif pair.get("blocked", 0) == -1 and z < pair["entry_z"]:' in src


def test_skip_reasons_stay_a_closed_vocabulary():
    """`skip` rows are grouped by `reason` in analysis, so the set has to stay
    enumerable rather than drifting into free text."""
    with open(AGENT) as fh:
        src = fh.read()
    reasons = set(re.findall(r'ledger\("skip", pair=short_name,\s*reason="(\w+)"',
                             src))
    assert reasons == {"gross_cap", "min_notional", "anomaly_veto",
                       "news_veto", "side_blocked"}, reasons
