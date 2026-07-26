"""
Tests for news-gate failure visibility.

The sentinel fails OPEN by design: an LLM outage must not halt a working
strategy, and the z-stop, vol-targeted sizing and gross cap all still apply.
But failing open *silently* turns a risk control into a placebo — entries
would quietly stop being screened for delistings and hacks while a daily
glance showed a perfectly healthy agent. The competition's AI allocation is
USD 10/day with no rollover, so quota exhaustion is a predictable whole-day
outage, not a transient blip, and must be named as such.

These pin: every failure path records WHY, quota is distinguished from other
API errors, the reasoning note never implies screening that did not happen,
and the transition (not every bar) is what gets logged.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import deploy.ltp_agent as agent
from deploy.ltp_news import NewsSentinel, classify_api_error


class _Err(Exception):
    def __init__(self, msg, status_code=None):
        super().__init__(msg)
        self.status_code = status_code


# --- quota is distinguished from ordinary failure ---------------------------

def test_quota_errors_are_named():
    assert classify_api_error(_Err("rate limited", status_code=429)) == "quota"
    for msg in ("insufficient quota", "credit balance too low",
                "daily allocation exceeded", "Too Many Requests"):
        assert classify_api_error(_Err(msg)) == "quota", msg


def test_other_errors_are_plain_api_errors():
    assert classify_api_error(_Err("connection reset")) == "api_error"
    assert classify_api_error(_Err("bad gateway", status_code=502)) == "api_error"


# --- degraded vs merely quiet -----------------------------------------------

def test_degraded_only_for_real_failures():
    s = NewsSentinel()
    for bad in NewsSentinel.DEGRADED_STATES:
        s.status = bad
        assert s.degraded is True, bad
    for fine in ("ok", "no_news"):
        s.status = fine
        assert s.degraded is False, fine


def test_note_admits_when_entry_was_not_screened():
    """The reasoning log must not imply event-risk screening that never ran."""
    s = NewsSentinel()
    s.status, s.last_error = "quota", "insufficient quota"
    note = s.note("TAO", "RENDER")
    assert "DOWN" in note and "quota" in note
    assert "NOT screened" in note

    s.status, s.verdicts = "no_news", {}
    quiet = s.note("TAO", "RENDER")
    assert "DOWN" not in quiet          # a quiet window is not a failure


# --- the agent surfaces it ---------------------------------------------------

def _track(status, previous, error="", verdicts=None):
    s = NewsSentinel()
    s.status, s.last_error = status, error
    s.verdicts = verdicts or {}
    state: dict = {}
    events: list[tuple[str, dict]] = []
    original = agent.ledger
    agent.ledger = lambda ev, **f: events.append((ev, f))
    try:
        agent.track_news_gate(state, s, previous)
    finally:
        agent.ledger = original
    return state, [ev for ev, _ in events]


def test_going_dark_is_logged_once_on_transition():
    state, events = _track("quota", previous="ok", error="insufficient quota")
    assert events == ["sentinel_degraded"]
    assert state["news_gate"]["status"] == "quota"


def test_staying_dark_does_not_spam_the_ledger():
    _, events = _track("quota", previous="quota", error="insufficient quota")
    assert events == []                 # one loud event, not one per bar


def test_recovery_is_logged():
    _, events = _track("ok", previous="quota", verdicts={"TAO": {}})
    assert events == ["sentinel_restored"]


def test_healthy_operation_is_silent_but_recorded():
    state, events = _track("ok", previous="ok", verdicts={"TAO": {}})
    assert events == []
    assert state["news_gate"]["status"] == "ok"
    assert state["news_gate"]["rated"] == 1


def test_quiet_news_window_is_not_reported_as_failure():
    _, events = _track("no_news", previous="ok")
    assert events == []
