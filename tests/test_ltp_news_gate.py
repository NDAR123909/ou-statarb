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
    # `news_assessment` is emitted on EVERY refresh (the audit trail of the
    # hourly sentiment call); transitions are the separate, rarer signal.
    return state, ([ev for ev, _ in events if ev != "news_assessment"],
                   [f for ev, f in events if ev == "news_assessment"])


def test_going_dark_is_logged_once_on_transition():
    state, (events, _) = _track("quota", previous="ok", error="insufficient quota")
    assert events == ["sentinel_degraded"]
    assert state["news_gate"]["status"] == "quota"


def test_staying_dark_does_not_spam_the_ledger():
    _, (events, _) = _track("quota", previous="quota", error="insufficient quota")
    assert events == []                 # one loud event, not one per bar


def test_recovery_is_logged():
    _, (events, _) = _track("ok", previous="quota", verdicts={"TAO": {}})
    assert events == ["sentinel_restored"]


def test_healthy_operation_logs_no_transition_but_records_state():
    state, (events, _) = _track("ok", previous="ok", verdicts={"TAO": {}})
    assert events == []
    assert state["news_gate"]["status"] == "ok"
    assert state["news_gate"]["rated"] == 1


def test_quiet_news_window_is_not_reported_as_failure():
    _, (events, _) = _track("no_news", previous="ok")
    assert events == []


# --- the hourly sentiment call always leaves a trace -------------------------

def test_every_refresh_records_the_verdicts():
    """Previously the hourly sentiment call left NO ledger trace unless a
    trade happened, so a quiet stretch looked like the sentinel never ran."""
    verdicts = {"TAO": {"severity": "none", "rationale": "ordinary commentary"},
                "RENDER": {"severity": "watch", "rationale": "large unlock"}}
    _, (_, assessments) = _track("ok", previous="ok", verdicts=verdicts)
    assert len(assessments) == 1
    rec = assessments[0]
    assert rec["status"] == "ok" and rec["rated"] == 2
    assert rec["verdicts"]["RENDER"]["severity"] == "watch"
    assert "large unlock" in rec["verdicts"]["RENDER"]["rationale"]


def test_quiet_window_still_records_that_the_sentinel_ran():
    _, (_, assessments) = _track("no_news", previous="no_news")
    assert len(assessments) == 1
    assert assessments[0]["status"] == "no_news"
    assert assessments[0]["rated"] == 0


# --- screening provenance is machine-readable --------------------------------

TAO, REN = "BINANCE_PERP_TAO_USDT", "BINANCE_PERP_RENDER_USDT"


def _sentinel(status, verdicts=None):
    s = NewsSentinel()
    s.status, s.verdicts = status, verdicts or {}
    return s


def test_provenance_marks_a_screened_entry():
    """The audit correlates AI logs with orders programmatically, so 'was this
    trade screened, by what, with what verdict' must be filterable without
    parsing English out of the reasoning prose."""
    s = _sentinel("ok", {"TAO": {"severity": "none"},
                         "RENDER": {"severity": "watch"}})
    prov = agent.screening_provenance(s, {"regime": "normal",
                                          "confidence": "high"}, TAO, REN)
    assert prov["screened"] is True
    assert prov["news_status"] == "ok"
    assert prov["news_severity"] == {"TAO": "none", "RENDER": "watch"}
    assert prov["regime"] == "normal" and prov["regime_confidence"] == "high"


def test_provenance_marks_an_unscreened_entry():
    """A trade taken while the gate was dark must be distinguishable from a
    screened one in structured data, not only in the narrative."""
    prov = agent.screening_provenance(_sentinel("quota"), {}, TAO, REN)
    assert prov["screened"] is False
    assert prov["news_status"] == "quota"
    assert prov["news_severity"] == {"TAO": None, "RENDER": None}
    assert prov["regime"] is None


def test_provenance_without_a_sentinel_at_all():
    prov = agent.screening_provenance(None, {}, TAO, REN)
    assert prov["screened"] is False and prov["news_status"] == "disabled"


# --- staleness: a verdict that did not screen the bar it is attached to ----

def test_provenance_marks_a_stale_verdict_instead_of_claiming_ok():
    """The sentinel only refreshes for assets of ALREADY-active pairs, and that
    list is built before the refit that adds new ones. So a pair selected out
    of a drought could be entered while the sentinel held verdicts hours old --
    and the record stamped that entry `news_status: ok`. A log that claims a
    screening which did not happen is worse than one that says nothing."""
    from datetime import datetime, timedelta, timezone
    from deploy.ltp_agent import screening_provenance

    now = datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)

    class S:
        status, degraded = "ok", False
        verdicts = {"XLM": {"severity": "none"}, "XRP": {"severity": "none"}}
        last_refresh = (now - timedelta(hours=22)).isoformat(timespec="seconds")

    p = screening_provenance(S(), {}, "BINANCE_PERP_XLM_USDT",
                             "BINANCE_PERP_XRP_USDT", now=now)
    assert p["news_status"] == "stale"
    assert p["screened"] is False
    assert 21.9 < p["news_age_h"] < 22.1

    S.last_refresh = (now - timedelta(minutes=20)).isoformat(timespec="seconds")
    fresh = screening_provenance(S(), {}, "BINANCE_PERP_XLM_USDT",
                                 "BINANCE_PERP_XRP_USDT", now=now)
    assert fresh["news_status"] == "ok" and fresh["screened"] is True


def test_provenance_names_legs_that_were_never_rated_at_all():
    """The drought case is worse than staleness: a newly selected pair's legs
    may have no verdict at any age. That entry is unscreened, and the field has
    to say so rather than reporting a severity of None as if it were a rating.
    """
    from datetime import datetime, timezone
    from deploy.ltp_agent import screening_provenance

    now = datetime(2026, 8, 14, 18, 0, tzinfo=timezone.utc)

    class S:
        status, degraded = "ok", False
        verdicts = {"XLM": {"severity": "none"}}          # XRP never rated
        last_refresh = now.isoformat(timespec="seconds")

    p = screening_provenance(S(), {}, "BINANCE_PERP_XLM_USDT",
                             "BINANCE_PERP_XRP_USDT", now=now)
    assert p["news_status"] == "missing_legs"
    assert p["news_unrated_legs"] == ["XRP"]
    assert p["screened"] is False


def test_the_glance_is_not_buried_by_the_advisory_review_layer():
    """The review pass writes ~380 ledger rows a night. It buried enter/exit/
    stop completely -- 20 of 20 rows in the operator's daily glance were
    `ai_deep_review`. Hidden from the tail, still counted in the tally."""
    import json
    import tempfile
    from pathlib import Path
    from deploy.status import _tail_ledger

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "led.jsonl"
        rows = [{"ts": "2026-08-14T09:00:00+00:00", "event": "enter",
                 "pair": "FIL/AR"}]
        rows += [{"ts": "2026-08-14T17:00:00+00:00", "event": "ai_deep_review",
                  "topic": f"t{i}"} for i in range(50)]
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

        shown, tally = _tail_ledger(str(p), 8)
        assert [r["event"] for r in shown] == ["enter"]
        # ...but the volume must stay visible somewhere.
        assert tally["ai_deep_review"] == 50 and tally["enter"] == 1
