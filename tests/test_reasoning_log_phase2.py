"""
Guards on the Phase II Reasoning Log package -- and on any phase's window.

The organizer requires the Phase II log "within one week after the competition
ends" (2026-10-28). Until that day the packager read the whole ledger and
every fills snapshot, which after Phase II would have shipped mostly Phase I
under a Phase II label. These pin the properties that make a phase's package
honest:

- it holds exactly that phase's records, and counts the rest;
- the advisory layer is too large to publish, so it stays out of git and
  out of the email but stays hashed;
- a dry run cannot be mistaken for the submission;
- a final build cannot ship a narrative with blanks in it.
"""

import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import deploy.reasoning_log as rl                                    # noqa: E402
from deploy.export_phase_ledger import PHASE_II_OPEN                 # noqa: E402

GMT8 = ZoneInfo("Asia/Shanghai")
P2 = rl.PHASES["II"]
BEFORE_BELL = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)
AFTER_BELL = datetime(2026, 11, 5, 0, 30, tzinfo=timezone.utc)

ROWS = [
    {"ts": "2026-07-25T08:00:00+00:00", "event": "enter", "pair": "FIL/AR"},
    {"ts": "2026-08-30T08:00:00+00:00", "event": "ai_deep_review",
     "review": "build window"},
    {"ts": "2026-09-08T15:59:59+00:00", "event": "refit"},          # before
    {"ts": "2026-09-08T16:00:00+00:00", "event": "refit"},          # opens: in
    {"ts": "2026-10-03T15:00:01+00:00", "event": "operation", "op": "place"},
    {"ts": "2026-10-03T16:00:06+00:00", "event": "reconcile"},
    {"ts": "2026-10-20T23:00:05+00:00", "event": "skip",
     "reason": "anomaly_veto"},
    {"ts": "2026-10-21T08:05:00+00:00", "event": "stop", "trigger": "intrabar"},
    {"ts": "2026-10-22T09:00:05+00:00", "event": "stop", "trigger": "bar"},
    {"ts": "2026-09-15T20:00:05+00:00", "event": "stop"},           # pre-10-05
    {"ts": "2026-10-23T09:00:00+00:00", "event": "ai_deep_review",
     "review": "in phase"},
    {"ts": "2026-11-04T15:59:59+00:00", "event": "nav"},            # last in
    {"ts": "2026-11-04T16:00:00+00:00", "event": "nav"},            # after
    {"ts": "2026-11-04T16:30:00+00:00", "event": "ai_deep_review",
     "review": "the spend pass after the bell"},
    {"event": "operation", "op": "place"},                          # undated
]
IN_WINDOW = 9


def _ledger(path, rows=ROWS):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def _narrative(tmp_path, text="# Phase II\nAll numbers final.\n"):
    p = tmp_path / "narrative.md"
    p.write_text(text)
    return p


# ------------------------------------------------------------- the windows --

def test_the_windows_are_the_phases_the_organizer_announced():
    """Phase II opened 00:00 GMT+8 09-09; scoring stops 23:59 GMT+8 11-04
    (organizer, 2026-10-27). The window ends at the end of that competition
    day, one minute after the bell, so nothing scored is cut."""
    since, until = rl._instant(P2.since), rl._instant(P2.until)
    assert since == datetime(2026, 9, 9, 0, 0, tzinfo=GMT8)
    assert until == datetime(2026, 11, 5, 0, 0, tzinfo=GMT8)
    bell = datetime(2026, 11, 4, 23, 59, tzinfo=GMT8)
    assert since < bell < until
    # One opening instant across the repo, not two that can drift apart.
    assert since == rl._instant(PHASE_II_OPEN)

    p1 = rl.PHASES["I"]
    assert rl._instant(p1.since) == datetime(2026, 7, 20, 0, 0, tzinfo=GMT8)
    assert rl._instant(p1.until) == datetime(2026, 8, 22, 0, 0, tzinfo=GMT8)


def test_a_phase_window_keeps_only_that_phases_records(tmp_path):
    out = tmp_path / "sub"
    split = rl.split_ledger(_ledger(tmp_path / "l.jsonl"), out,
                            P2.since, P2.until)
    kept = [json.loads(l) for l in
            (out / "reasoning.jsonl").read_text().splitlines()]
    with gzip.open(out / "ai_deep_review.jsonl.gz", "rt") as fh:
        advisory = [json.loads(l) for l in fh]

    assert all(P2.since <= r["ts"] < P2.until for r in kept + advisory)
    assert [r["review"] for r in advisory] == ["in phase"]
    assert len(kept) + len(advisory) == IN_WINDOW
    # The boundaries, exactly: the opening instant is in, the bell's minute is
    # in, the end of the competition day is out.
    stamps = {r["ts"] for r in kept}
    assert "2026-09-08T16:00:00+00:00" in stamps
    assert "2026-11-04T15:59:59+00:00" in stamps
    assert "2026-11-04T16:00:00+00:00" not in stamps
    # Nothing is silently lost: everything left out is counted, by side.
    assert split["window"] == {"since": P2.since, "until": P2.until,
                               "before": 3, "after": 2, "undated": 1}
    assert sum(split["tally"].values()) == IN_WINDOW
    assert sum(split["tally"].values()) + 3 + 2 + 1 == len(ROWS)


def test_records_left_out_are_stated_in_the_manifest(tmp_path):
    out = tmp_path / "sub"
    split = rl.split_ledger(_ledger(tmp_path / "l.jsonl"), out,
                            P2.since, P2.until)
    text = rl.write_manifest(out, split, [], P2, built=AFTER_BELL).read_text()
    assert "Track A Phase II Reasoning Log" in text
    assert f"Window  {P2.since} <= ts < {P2.until}" in text
    assert "Outside the window, not packaged: 3 before, 2 after, 1 undated" in text
    assert "EVENT TALLY (inside the window)" in text


def test_stops_are_counted_by_which_check_fired(tmp_path):
    """From 2026-10-05 a stop is either the hourly bar's or the five-minute
    sample's. An audit should not have to grep for that split."""
    out = tmp_path / "sub"
    split = rl.split_ledger(_ledger(tmp_path / "l.jsonl"), out,
                            P2.since, P2.until)
    assert split["stops"] == {"intrabar": 1, "bar": 1, "unlabelled": 1}
    text = rl.write_manifest(out, split, [], P2, built=AFTER_BELL).read_text()
    assert re.search(r"^  intrabar\s+1$", text, re.M)
    assert re.search(r"^  bar\s+1$", text, re.M)
    assert re.search(r"^  unlabelled\s+1$", text, re.M)
    # Paths that exist but never fired are listed at zero.
    assert re.search(r"^  automation_budget\s+0$", text, re.M)
    assert re.search(r"^  anomaly_veto\s+1$", text, re.M)


# --------------------------------------------------------------- the fills --

def test_fills_snapshots_are_kept_by_their_date(tmp_path):
    tr = tmp_path / "track_record"
    tr.mkdir()
    for d in ("2026-09-07", "2026-09-08", "2026-09-09", "2026-11-04",
              "2026-11-05"):
        (tr / f"fills_{d}.json").write_text("{}")
    (tr / "fills_latest.json").write_text("{}")      # no date: not placeable

    out = tmp_path / "sub"
    first, last = rl.fills_dates(P2.since, P2.until)
    assert (first, last) == (date(2026, 9, 8), date(2026, 11, 4))
    copied = rl.copy_fills(tr, out, first, last)
    # 09-08's snapshot is kept: Phase II opened at 16:00 that day, and a
    # snapshot overlaps the week before it, so keeping it can add records
    # from outside the window but never drop one inside it.
    assert [p.name for p in copied] == ["fills_2026-09-08.json",
                                        "fills_2026-09-09.json",
                                        "fills_2026-11-04.json"]


def test_a_day_with_no_snapshot_is_named_not_assumed(tmp_path):
    fills = [tmp_path / f"fills_2026-09-{d:02d}.json" for d in (8, 9, 11, 12)]
    gaps = rl.missing_snapshot_days(fills, date(2026, 9, 8), date(2026, 9, 12),
                                    AFTER_BELL)
    assert gaps == [date(2026, 9, 10)]
    # The build day's snapshot is written at 23:55 and may not exist yet.
    built = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)
    assert rl.missing_snapshot_days(fills[:2], date(2026, 9, 8),
                                    date(2026, 9, 12), built) == [
        date(2026, 9, 10), date(2026, 9, 11)]


# ------------------------------------------------------------ the guards --

def test_a_phase_is_required(capsys):
    """Run bare, the old script packaged the whole ledger. It must now refuse
    to guess which phase is meant."""
    with pytest.raises(SystemExit):
        rl.main([])


def test_a_partial_build_is_refused_where_the_cron_publishes(tmp_path):
    """The droplet commits everything under track_record/ every night. A dry
    run there would be published as if it were the submission."""
    out = rl.TRACK_RECORD / "phase2_submission_pytest_must_not_exist"
    try:
        rc = rl.main(["--phase", "II", "--ledger",
                      str(_ledger(tmp_path / "deploy" / "ltp_ledger.jsonl")),
                      "--out", str(out)], now=BEFORE_BELL)
        assert rc == 1
        assert not out.exists()
    finally:
        if out.exists():
            shutil.copytree(out, tmp_path / "leftover")   # evidence, then fail
            pytest.fail(f"{out} was created")


def test_a_dry_run_elsewhere_says_it_is_not_the_submission(tmp_path):
    out = tmp_path / "dry" / "phase2_submission"
    rc = rl.main(["--phase", "II", "--ledger",
                  str(_ledger(tmp_path / "deploy" / "ltp_ledger.jsonl")),
                  "--out", str(out), "--narrative",
                  str(_narrative(tmp_path, f"x {rl.PLACEHOLDER}: rank]\n"))],
                 now=BEFORE_BELL)
    assert rc == 0                      # placeholders are fine before the bell
    text = (out / "MANIFEST.txt").read_text()
    assert "STATUS  PARTIAL" in text and "NOT A SUBMISSION" in text


def test_a_final_build_is_refused_while_the_narrative_has_blanks(tmp_path):
    out = tmp_path / "final" / "phase2_submission"
    # Wrapped across a line, as a Markdown paragraph wraps one.
    blank = "final rank **[FINAL AFTER THE\n   BELL: rank.]**\n"
    rc = rl.main(["--phase", "II", "--ledger",
                  str(_ledger(tmp_path / "deploy" / "ltp_ledger.jsonl")),
                  "--out", str(out), "--narrative",
                  str(_narrative(tmp_path, blank))], now=AFTER_BELL)
    assert rc == 1
    assert not out.exists()


def test_a_blank_is_found_however_it_wraps_or_is_cased():
    """The first version matched one exact string, and the Phase II narrative
    already held a placeholder wrapped mid-marker that it would have missed --
    found by this test's predecessor on its first run."""
    assert rl.blanks("a\n**[FINAL AFTER THE\n   BELL: firings]**") == [2]
    assert rl.blanks("[final after the bell: rank]") == [1]
    assert rl.blanks("[ Final: rank]") == [1]
    assert rl.blanks("the final numbers, in [brackets]") == []
    text = open(os.path.join(rl.REPO, "deploy", P2.narrative)).read()
    assert len(rl.blanks(text)) == len(re.findall(r"\[\s*final", text, re.I))


# ---------------------------------------------------------- end to end --

def test_the_phase2_package_end_to_end(tmp_path):
    repo = tmp_path / "repo"
    ledger = _ledger(repo / "deploy" / "ltp_ledger.jsonl")
    tr = repo / "track_record"
    tr.mkdir()
    for d in ("2026-08-20", "2026-09-09", "2026-11-04"):
        (tr / f"fills_{d}.json").write_text('{"summary": {}}')
    out = repo / "out" / "phase2_submission"

    rc = rl.main(["--phase", "II", "--ledger", str(ledger), "--out", str(out),
                  "--narrative", str(_narrative(tmp_path)), "--archive"],
                 now=AFTER_BELL)
    assert rc == 0

    text = (out / "MANIFEST.txt").read_text()
    assert "STATUS  final" in text
    assert (out / "REASONING_LOG.md").read_text().startswith("# Phase II")
    assert sorted(p.name for p in (out / "fills").iterdir()) == [
        "fills_2026-09-09.json", "fills_2026-11-04.json"]
    # The advisory file is in the package and hashed ...
    digest = rl.sha256_of(out / "ai_deep_review.jsonl.gz")
    line = next(l for l in text.splitlines() if digest in l)
    assert "delivered separately" in line
    # ... and kept out of git by a rule that travels with the package ...
    assert "ai_deep_review.jsonl.gz" in (out / ".gitignore").read_text()
    # ... and out of the email.
    archive = out.parent / "phase2_submission.tar.gz"
    with tarfile.open(archive) as tar:
        names = {os.path.relpath(n, "phase2_submission") for n in tar.getnames()}
    assert "ai_deep_review.jsonl.gz" not in names
    assert ".gitignore" not in names
    assert {"MANIFEST.txt", "REASONING_LOG.md", "reasoning.jsonl",
            "fills/fills_2026-09-09.json"} <= names


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_the_nightly_git_add_never_stages_the_advisory_file(tmp_path):
    """Exactly what the droplet's 23:58 cron runs: `git add track_record/`. A
    ~60 MB file staged there would fail that push, and every later one."""
    repo = tmp_path / "droplet"
    out = repo / "track_record" / "phase2_submission"
    rl.split_ledger(_ledger(tmp_path / "l.jsonl"), out, P2.since, P2.until)
    rl.keep_out_of_git(out, P2.unpublished)

    run = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True,  # noqa: E731
                                    capture_output=True, text=True).stdout
    run("init", "-q")
    run("add", "track_record/")
    staged = run("ls-files").split()
    assert "track_record/phase2_submission/reasoning.jsonl" in staged
    assert "track_record/phase2_submission/.gitignore" in staged
    assert not any(s.endswith("ai_deep_review.jsonl.gz") for s in staged)


def test_the_ledger_is_streamed_not_read_whole():
    """~200 MB by the close, read on the droplet beside the live agent. Read
    whole, plus its split lines, that is ~0.4 GB on a small machine."""
    import inspect
    src = inspect.getsource(rl.split_ledger)
    assert "read_text" not in src and "readlines" not in src
    assert "for line in source" in src


def test_the_phase2_narrative_discloses_what_went_wrong():
    """The document is sent to the organizer once. These are the facts an
    auditor is entitled to find in it rather than in our review log."""
    text = open(os.path.join(rl.REPO, "deploy", P2.narrative)).read()
    for must in (
        "2026-10-03",            # the naked leg, and the reconcile that closed it
        "entry_unwound",         # ... and the fix
        "0 days remain",         # the deep-review prompt defect
        "09-09 → 09-21",         # ... and its window
        "+91.96 sigma",          # false magnitudes in published exit reasoning
        "mu_shift_basis",
        "`trigger`",             # hourly vs intra-bar stops
        "Organizing Committee",  # post-bell closes are not agent operations
        "delivered by link",     # the advisory layer's delivery
        "executed_price",        # closes carry no price; fills/ does
        "not a claim of\nedge",  # x1.5, as it was decided
    ):
        assert must in text, must
