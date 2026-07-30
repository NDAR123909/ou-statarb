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
