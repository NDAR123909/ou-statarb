"""
Guards on the research queue's reach.

The research lane (Claude Cowork) reads a *branch*, not the repository. A brief
that cites data the branch does not carry gets answered on whatever is left, and
the answer looks complete. That happened on 2026-09-16 (task 02 was briefed with
Phase II figures that existed only on the droplet), and it nearly happened again
on 2026-09-23: the Phase II slice had been published — to `live/track-record` —
and the brief said "both phases are in the repo", while the dispatch runbook
branched from a branch that carried neither. Found on a cold start the night
before task 05's dispatch, by reading, which is not a mechanism.

This is the mechanism. Every `track_record/` file an open brief names must be
either on this branch or pulled onto the research branch by the runbook's
step 1. Prose saying so has now been wrong twice; this cannot be.
"""

import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "deploy", "research_queue")
README = os.path.join(QUEUE, "README.md")

_TRACK_PATH = re.compile(r"track_record/[\w./-]+\.(?:jsonl|txt|json|csv)")
_PULL = re.compile(r"git checkout origin/live/track-record -- (.+)")


def _open_briefs() -> list[str]:
    """Top-level NN-*.md only: done/ and out/ are history, not dispatchable."""
    return sorted(glob.glob(os.path.join(QUEUE, "[0-9][0-9]-*.md")))


def _pulled_by_runbook() -> set[str]:
    with open(README) as fh:
        text = fh.read()
    pulled: set[str] = set()
    for m in _PULL.finditer(text):
        pulled.update(m.group(1).split())
    return pulled


def test_the_runbook_fetches_the_droplet_branch_before_pulling_from_it():
    """A checkout from `origin/live/track-record` against a stale remote ref
    hands the tool yesterday's slice with no error, so the fetch must precede
    it."""
    with open(README) as fh:
        text = fh.read()
    fetch = text.find("git fetch origin live/track-record")
    pull = text.find("git checkout origin/live/track-record --")
    assert fetch != -1 and pull != -1, "step 1 no longer pulls the Phase II inputs"
    assert fetch < pull, "step 1 pulls from live/track-record before fetching it"


def test_the_runbook_pulls_the_phase_ii_slice_and_state_history():
    pulled = _pulled_by_runbook()
    assert "track_record/ltp_ledger_phase2.jsonl" in pulled
    assert "track_record/ltp_state_history.jsonl" in pulled


def test_every_track_record_file_a_brief_names_reaches_the_research_branch():
    """The invariant itself. Fails if a brief cites a file that is neither
    committed here, nor checked out onto the research branch by the runbook's
    step 1, nor by the brief's OWN dispatch note -- i.e. data the tool being
    asked about it cannot see. Widened 2026-09-29 from `.jsonl` only, when
    task 07 became the first brief to need a `.txt` input."""
    readme_pulls = _pulled_by_runbook()
    missing = []
    for brief in _open_briefs():
        with open(brief) as fh:
            text = fh.read()
        own_pulls = {p for m in _PULL.finditer(text) for p in m.group(1).split()}
        for path in sorted(set(_TRACK_PATH.findall(text))):
            if (not os.path.exists(os.path.join(ROOT, path))
                    and path not in readme_pulls and path not in own_pulls):
                missing.append(f"{os.path.basename(brief)}: {path}")
    assert not missing, (
        "brief(s) cite data the research branch will not carry: "
        + "; ".join(missing)
        + ". Commit it here, add it to the step 1 pull in "
          "deploy/research_queue/README.md, or give the brief a Dispatch note "
          "that checks it out.")


def test_the_check_is_not_vacuous():
    """If briefs stop naming data, the invariant above passes on nothing. Its
    first guard pointed at task 05 and went silent when 05 moved to done/ --
    exactly the failure it existed to prevent. Now: every open brief that
    names a file only its own dispatch note pulls must actually contain that
    pull, and the check must see at least one data path across the queue."""
    seen = 0
    for brief in _open_briefs():
        with open(brief) as fh:
            text = fh.read()
        seen += len(set(_TRACK_PATH.findall(text)))
        if "universe_scan_task07.txt" in text:
            assert ("git checkout origin/live/track-record -- "
                    "track_record/universe_scan_task07.txt") in text
    if _open_briefs():
        assert seen > 0, "open briefs name no data at all -- check the regex"
