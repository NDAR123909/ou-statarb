"""
Tests for the announced-maintenance guard.

The venue schedules upgrades that disable the place/cancel order APIs. During
one, the agent can still see prices but cannot exit, stop, or de-risk anything
it holds -- and if a window catches it mid-entry, it holds a naked directional
leg it cannot close. So it goes flat in the run-up and opens nothing until the
window closes.

This is deliberately NOT market discretion: "don't hold positions you cannot
exit during an announced order-API blackout" is an operational fact, unlike
"reduce risk before the Fed", which would be a price prediction and is exactly
the behaviour this agent refuses.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy.ltp_agent import parse_maintenance_windows, maintenance_state

# The real 2026-07-30 notice: 14:00 GMT+8 == 06:00 UTC.
SPEC = "2026-07-30T06:00:00Z/2026-07-30T08:00:00Z"


def _at(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


# --- parsing -----------------------------------------------------------------

def test_parses_a_single_window():
    got = parse_maintenance_windows(SPEC)
    assert got == [(_at("2026-07-30T06:00:00Z"), _at("2026-07-30T08:00:00Z"))]


def test_parses_several_windows():
    assert len(parse_maintenance_windows(
        f"{SPEC},2026-08-05T01:00:00Z/2026-08-05T02:00:00Z")) == 2


def test_naive_timestamps_are_treated_as_utc():
    got = parse_maintenance_windows(
        "2026-07-30T06:00:00/2026-07-30T08:00:00")
    assert got[0][0].tzinfo is timezone.utc


def test_malformed_input_is_skipped_not_raised():
    """A typo in an env var must never stop a live agent from trading."""
    for spec in ("", "   ", "garbage", "no-slash-here",
                 "2026-13-45T99:00:00Z/nonsense",
                 "2026-07-30T08:00:00Z/2026-07-30T06:00:00Z"):   # end <= start
        assert parse_maintenance_windows(spec) == []


def test_good_window_survives_a_bad_neighbour():
    got = parse_maintenance_windows(f"garbage,{SPEC}")
    assert len(got) == 1


# --- state machine -----------------------------------------------------------

def test_clear_well_before_the_window():
    assert maintenance_state(_at("2026-07-30T03:00:00Z"),
                             parse_maintenance_windows(SPEC), 30) == "clear"


def test_prepare_inside_the_lead_time():
    w = parse_maintenance_windows(SPEC)
    assert maintenance_state(_at("2026-07-30T05:31:00Z"), w, 30) == "prepare"
    assert maintenance_state(_at("2026-07-30T05:59:00Z"), w, 30) == "prepare"
    # just outside the lead time is still clear
    assert maintenance_state(_at("2026-07-30T05:29:00Z"), w, 30) == "clear"


def test_active_inside_the_window():
    w = parse_maintenance_windows(SPEC)
    assert maintenance_state(_at("2026-07-30T06:00:00Z"), w, 30) == "active"
    assert maintenance_state(_at("2026-07-30T07:59:00Z"), w, 30) == "active"


def test_clear_again_once_the_window_ends():
    w = parse_maintenance_windows(SPEC)
    assert maintenance_state(_at("2026-07-30T08:00:00Z"), w, 30) == "clear"
    assert maintenance_state(_at("2026-07-30T09:00:00Z"), w, 30) == "clear"


def test_no_windows_configured_is_always_clear():
    now = datetime.now(timezone.utc)
    for offset in (-10, 0, 10):
        assert maintenance_state(now + timedelta(hours=offset), [], 30) == "clear"


def test_lead_time_is_configurable():
    w = parse_maintenance_windows(SPEC)
    assert maintenance_state(_at("2026-07-30T04:30:00Z"), w, 30) == "clear"
    assert maintenance_state(_at("2026-07-30T04:30:00Z"), w, 120) == "prepare"
