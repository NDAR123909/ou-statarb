"""
Guards on the ledger export.

The raw ledger is gitignored and lives only on the droplet; this is the one path
by which a phase's trading records reach the repo, which is what the research
lane reads. On 2026-09-16 task 02 was dispatched against a brief citing Phase II
data that was not published, and Cowork had to scope itself down to Phase I. The
tool exists so that cannot recur; these tests exist so the tool cannot quietly
publish something wrong instead.

The dangerous failure here is not a crash. It is a file that looks complete and
is not -- truncated by an interrupted run, or silently missing the records a
research task needs -- because a cron and the Wednesday runbook both commit
whatever is on disk without looking.
"""

import json
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.export_phase_ledger import (BULK_EVENTS, PHASE_II_OPEN,  # noqa: E402
                                        age_hours, export)


def _ledger(tmp_path, rows):
    p = tmp_path / "ltp_ledger.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def _rows():
    return [
        {"ts": "2026-08-01T10:00:00+00:00", "event": "enter"},      # before the cut
        {"ts": "2026-09-08T15:59:00+00:00", "event": "stop"},       # before, just
        {"ts": "2026-09-08T16:00:00+00:00", "event": "refit"},      # ON the cut
        {"ts": "2026-09-09T01:00:00+00:00", "event": "enter"},
        {"ts": "2026-09-09T02:00:00+00:00", "event": "ai_deep_review"},
        {"ts": "2026-09-10T03:00:00+00:00", "event": "stop"},
    ]


def test_the_cut_is_inclusive_of_its_own_boundary(tmp_path):
    """Phase II opened AT 16:00 UTC. A record stamped exactly then belongs to
    the phase; dropping it would lose the opening refit, which is the one that
    chose what the phase started trading."""
    out = tmp_path / "out.jsonl"
    s = export(_ledger(tmp_path, _rows()), out, PHASE_II_OPEN)
    kept = [json.loads(l) for l in out.read_text().splitlines()]
    assert [r["ts"] for r in kept] == ["2026-09-08T16:00:00+00:00",
                                       "2026-09-09T01:00:00+00:00",
                                       "2026-09-10T03:00:00+00:00"]
    assert s["kept"] == 3 and s["skipped_bulk"] == 1


def test_only_the_declared_bulk_events_are_dropped(tmp_path):
    """The exclusion is a size decision, not a judgement about which records
    matter. If it ever widens to cover a trading record -- an enter, a stop, a
    skip -- a research task would compute a rate on a silently truncated
    denominator, which is this project's most-repeated error."""
    assert BULK_EVENTS == {"ai_deep_review"}
    out = tmp_path / "out.jsonl"
    export(_ledger(tmp_path, _rows()), out, PHASE_II_OPEN)
    events = {json.loads(l)["event"] for l in out.read_text().splitlines()}
    assert "ai_deep_review" not in events
    assert {"refit", "enter", "stop"} <= events


def test_reviews_can_be_opted_back_in(tmp_path):
    out = tmp_path / "out.jsonl"
    s = export(_ledger(tmp_path, _rows()), out, PHASE_II_OPEN,
               include_reviews=True)
    assert s["kept"] == 4 and s["skipped_bulk"] == 0


def test_a_malformed_line_is_skipped_and_counted_not_fatal(tmp_path):
    """A partial final line is what a ledger being appended to looks like when
    it is read mid-write. Dying there would mean the export fails precisely on
    the busiest days."""
    p = tmp_path / "ltp_ledger.jsonl"
    p.write_text(json.dumps({"ts": "2026-09-09T01:00:00+00:00",
                             "event": "enter"}) + "\n{\"ts\": \"2026-09-09T0")
    out = tmp_path / "out.jsonl"
    s = export(p, out, PHASE_II_OPEN)
    assert s["kept"] == 1 and s["malformed"] == 1


def test_a_missing_ledger_raises_rather_than_publishing_emptiness(tmp_path):
    """An empty output file and a missing input look identical to whoever reads
    the published file next, and one of them means "the phase had no activity".
    Fail loudly instead."""
    with pytest.raises(FileNotFoundError):
        export(tmp_path / "nope.jsonl", tmp_path / "out.jsonl")
    assert not (tmp_path / "out.jsonl").exists()


def test_an_interrupted_run_leaves_no_half_written_file(tmp_path):
    """The cron and the dispatch runbook both commit whatever is on disk. A
    truncated file that looks complete is worse than no file, so the write goes
    to a temp path and is renamed only on success."""
    out = tmp_path / "out.jsonl"
    out.write_text('{"ts": "PREEXISTING"}\n')

    class Boom(Exception):
        pass

    # Interrupt mid-stream: the export is several records in, with the temp file
    # already open and partly written, when this fires.
    p = _ledger(tmp_path, _rows())
    orig = json.loads

    calls = {"n": 0}

    def flaky(s, *a, **k):
        calls["n"] += 1
        if calls["n"] > 3:
            raise Boom
        return orig(s, *a, **k)

    json.loads = flaky
    try:
        with pytest.raises(Boom):
            export(p, out, PHASE_II_OPEN)
    finally:
        json.loads = orig

    # the previous contents survive untouched, and no .tmp is left behind
    assert out.read_text() == '{"ts": "PREEXISTING"}\n'
    assert not list(tmp_path.glob("*.tmp"))


def test_age_hours_is_computed_not_eyeballed():
    """The runbook tells the operator to check the newest record is recent.
    Making them subtract ISO timestamps by hand at that moment is how a stale
    dispatch happens."""
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    assert age_hours("2026-09-21T10:00:00+00:00", now) == pytest.approx(2.0)
    assert age_hours("2026-09-20T12:00:00+00:00", now) == pytest.approx(24.0)
    assert age_hours("not a timestamp") is None
    assert age_hours(None) is None


def test_the_staleness_note_gives_a_command_that_works(tmp_path, monkeypatch,
                                                       capsys):
    """On 2026-09-23 the note said "Run deploy/status.py"; the operator ran
    exactly that in a fresh SSH shell and equity, positions and spend all read
    UNAVAILABLE on a healthy agent, because nothing had loaded /root/ltp.env.
    The note is the instruction someone follows at the moment of doubt, so it
    must carry the env load itself."""
    from deploy import export_phase_ledger as m
    ledger = _ledger(tmp_path, [{"ts": "2026-09-09T01:00:00+00:00",
                                 "event": "refit"}])
    monkeypatch.setattr(sys, "argv", ["x", "--ledger", str(ledger),
                                      "--out", str(tmp_path / "o.jsonl")])
    assert m.main() == 0
    printed = capsys.readouterr().out
    assert "NOTE" in printed
    assert m.STATUS_CMD in printed
    assert "set -a" in m.STATUS_CMD and "/root/ltp.env" in m.STATUS_CMD
    assert m.STATUS_CMD.index("set -a") < m.STATUS_CMD.index("deploy/status.py")


def test_the_default_cut_is_the_phase_open_and_says_why():
    """2026-09-08T16:00 UTC is 00:00 GMT+8 on 09-09 -- the organizer's clock,
    not ours. A future session changing this must change it knowingly."""
    assert PHASE_II_OPEN == "2026-09-08T16:00"
    import inspect
    import deploy.export_phase_ledger as m
    assert "GMT+8" in inspect.getsource(m)
