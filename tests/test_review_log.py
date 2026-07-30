"""
Guards on the durable record that survives context loss.

This project runs over months, across many sessions, and the assistant's
working context is reset repeatedly. Everything written to a FILE survives;
everything that stays in conversation does not. On 2026-07-28/30 four
commitments made in chat ("I'll look at that Sunday") were lost in a single
session, and the review log still described the entry band as ~3.0 after it had
changed to 0.6 — a future session would have read a stale premise as fact.

Documentation drifts because nothing fails when it is forgotten; tests survive
because CI fails without them. So the record is coupled to shipping: if
`deploy/WEEKLY_REVIEW.md` goes stale, the build goes red. That converts an
intention into an enforcement.
"""

import os
import re
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REVIEW = os.path.join(ROOT, "deploy", "WEEKLY_REVIEW.md")
STRATEGY = os.path.join(ROOT, "deploy", "LTP_STRATEGY.md")
CLAUDE_MD = os.path.join(ROOT, "CLAUDE.md")

# Generous: weekly reviews are the cadence, so ~10 days allows a late Sunday
# plus slack. Tight enough that a month of undocumented change cannot pass.
MAX_AGE_DAYS = 10

_DATE = re.compile(r"(20\d\d)-(\d\d)-(\d\d)")


def _dates_in(path: str) -> list[date]:
    with open(path) as fh:
        out = []
        for y, m, d in _DATE.findall(fh.read()):
            try:
                out.append(date(int(y), int(m), int(d)))
            except ValueError:
                pass          # e.g. a version string that looks like a date
        return out


def test_review_log_exists_and_is_substantive():
    assert os.path.exists(REVIEW), "the durable record is missing"
    with open(REVIEW) as fh:
        body = fh.read()
    assert len(body) > 4000, "review log looks truncated"
    for heading in ("Standing context", "Open commitments", "agenda"):
        assert heading in body, f"review log lost its '{heading}' section"


def test_review_log_is_not_stale():
    """The most recent dated entry must be recent.

    If this fails, the fix is not to bump a date: it is to append what actually
    happened -- what changed, what was promised, and what is now out of date --
    so the next session starting cold inherits it.
    """
    dates = [d for d in _dates_in(REVIEW) if d <= date.today()]
    assert dates, "no dated entries in the review log"
    age = (date.today() - max(dates)).days
    assert age <= MAX_AGE_DAYS, (
        f"deploy/WEEKLY_REVIEW.md's newest entry is {age} days old "
        f"(limit {MAX_AGE_DAYS}). Append the current state, decisions and "
        f"open commitments rather than editing the date.")


def test_open_commitments_section_is_present():
    """The section that catches "I'll look at that Sunday" promises."""
    with open(REVIEW) as fh:
        body = fh.read()
    idx = body.find("## Open commitments")
    assert idx != -1, "the Open commitments section was removed"
    # a table or list must actually follow the heading
    following = body[idx:idx + 2500]
    assert "|" in following or "- " in following, (
        "Open commitments section has no entries or table")


def test_claude_md_points_at_the_durable_record():
    """A cold session must be told to read the record before acting."""
    with open(CLAUDE_MD) as fh:
        body = fh.read()
    assert "WEEKLY_REVIEW.md" in body, (
        "CLAUDE.md no longer points at the review log, so a fresh session "
        "would not know to read it")
    assert "LTP_STRATEGY.md" in body


def test_cold_start_protocol_is_documented():
    """The record is kept fresh by the tests above; this keeps it READ.

    A reset session does not feel reset -- it will answer a narrow question
    confidently from a premise that changed weeks ago. So the operator has a
    trigger phrase, and the protocol behind it names an ordered set of sources
    and a mandatory summary-back. If either the phrase or the read order goes
    missing, the protocol has quietly rotted in exactly the way it exists to
    prevent, and this fails.
    """
    with open(CLAUDE_MD) as fh:
        body = fh.read()

    assert "Cold start" in body, "the cold-start protocol section is gone"
    assert "read the record and tell me where we are" in body, (
        "the operator's trigger phrase is no longer documented, so the "
        "protocol has no way to be invoked")

    # The sources a cold session must actually open, in the order given.
    for source in ("CLAUDE.md",
                   "deploy/WEEKLY_REVIEW.md",
                   "deploy/LTP_STRATEGY.md",
                   "track_record/ltp_state_history.jsonl",
                   "git log",
                   "deploy/status.py"):
        assert source in body, f"cold-start read order lost {source}"

    # The stop is the load-bearing part: report first, act second.
    idx = body.find("Cold start")
    section = body[idx:body.find("### Session close-out", idx)]
    assert "summarise back" in section.lower() or \
           "summarize back" in section.lower(), (
        "the cold-start protocol no longer requires reporting state back "
        "before acting")
    assert "disagree" in section, (
        "the protocol no longer requires flagging sources that conflict -- "
        "that is the finding a cold start exists to produce")


def test_review_log_points_at_the_cold_start_protocol():
    """The record should tell a cold reader how it is meant to be entered."""
    with open(REVIEW) as fh:
        body = fh.read()
    assert "Cold start" in body, (
        "WEEKLY_REVIEW.md no longer mentions the cold-start protocol")


def test_strategy_doc_records_the_disclosed_changes():
    """LTP_STRATEGY.md is the pre-registration: behavioural changes are
    disclosed there, not silently made. Spot-check the load-bearing ones."""
    with open(STRATEGY) as fh:
        body = fh.read()
    for marker in ("optimal_bands",        # the band-optimiser bug
                   "exit_z",               # the unreachable-exit bug
                   "sandbox",              # Phase I risk decision
                   "min_entry_se"):        # the estimation-error floor
        assert marker in body, f"LTP_STRATEGY.md no longer discloses {marker}"
