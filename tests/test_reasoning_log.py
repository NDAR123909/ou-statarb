"""
Guards on the Phase I Reasoning Log package.

The organizer states that failing to submit affects eligibility to advance, so
this is the one artefact whose defects cost the competition rather than a
metric. These pin the properties that make it honest: the advisory layer stays
separated and labelled, no record is silently dropped, and the manifest can
actually be checked against the files.
"""

import gzip
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.reasoning_log import (ADVISORY_EVENTS, copy_fills,  # noqa: E402
                                  sha256_of, split_ledger, write_manifest)


def _ledger(tmp_path, rows):
    p = tmp_path / "ltp_ledger.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p


ROWS = [
    {"ts": "2026-07-20T08:00:00+00:00", "event": "enter", "pair": "FIL/AR",
     "reasoning": "z beyond the entry band"},
    {"ts": "2026-07-20T10:00:00+00:00", "event": "operation", "op": "place",
     "result": "filled"},
    {"ts": "2026-08-01T08:00:00+00:00", "event": "ai_spread_assessment",
     "pair": "FIL/AR"},
    {"ts": "2026-08-13T09:00:00+00:00", "event": "ai_deep_review",
     "topic": "stop_geometry", "review": "x" * 4000},
    {"ts": "2026-08-13T09:01:00+00:00", "event": "ai_deep_review",
     "topic": "entry_band", "review": "y" * 4000},
    {"ts": "2026-08-14T20:00:00+00:00", "event": "stop", "pair": "XLM/XRP"},
]


def test_the_advisory_layer_is_separated_not_mixed_in(tmp_path):
    """~25 of 26 MB of the ledger is a layer that never touched a trade.
    Submitting it unlabelled inside the reasoning file would inflate the
    apparent decision reasoning about twentyfold, which for a Reasoning Audit
    is the same defect as under-logging."""
    out = tmp_path / "sub"
    split = split_ledger(_ledger(tmp_path, ROWS), out)

    reasoning = [json.loads(l) for l in
                 (out / "reasoning.jsonl").read_text().splitlines()]
    assert {r["event"] for r in reasoning} == {
        "enter", "operation", "ai_spread_assessment", "stop"}
    assert not any(r["event"] in ADVISORY_EVENTS for r in reasoning)

    with gzip.open(out / "ai_deep_review.jsonl.gz", "rt") as fh:
        advisory = [json.loads(l) for l in fh]
    assert len(advisory) == 2
    assert all(r["event"] == "ai_deep_review" for r in advisory)
    assert split["counts"] == {"reasoning": 4, "advisory": 2, "unparseable": 0}


def test_every_record_lands_in_exactly_one_file(tmp_path):
    """A submission that drops records is worse than one that is too big."""
    out = tmp_path / "sub"
    split = split_ledger(_ledger(tmp_path, ROWS), out)
    counts = split["counts"]
    assert counts["reasoning"] + counts["advisory"] == len(ROWS)
    assert sum(split["tally"].values()) == len(ROWS)


def test_unparseable_lines_are_counted_never_silently_skipped(tmp_path):
    """An audit is entitled to know the log had lines we could not read."""
    p = tmp_path / "ltp_ledger.jsonl"
    p.write_text(json.dumps(ROWS[0]) + "\n"
                 + "{truncated mid-writ\n"
                 + "\n"                       # blank lines are not corruption
                 + json.dumps(ROWS[5]) + "\n")
    out = tmp_path / "sub"
    split = split_ledger(p, out)
    assert split["counts"]["unparseable"] == 1
    assert split["counts"]["reasoning"] == 2

    manifest = write_manifest(out, split, []).read_text()
    assert "unparseable lines skipped         1" in manifest


def test_the_manifest_digests_match_the_files_it_ships(tmp_path):
    """'Tamper-evident' has to mean a stranger can check it, not that we say
    so. A manifest whose hashes do not verify is worse than none."""
    out = tmp_path / "sub"
    split = split_ledger(_ledger(tmp_path, ROWS), out)
    manifest = write_manifest(out, split, []).read_text()

    for name in ("reasoning.jsonl", "ai_deep_review.jsonl.gz"):
        digest = sha256_of(out / name)
        assert f"{digest}" in manifest, name
        assert name in manifest


def test_the_manifest_labels_which_events_were_advisory(tmp_path):
    """The reader must be able to tell, without our prose, which rows drove
    trades and which did not."""
    out = tmp_path / "sub"
    split = split_ledger(_ledger(tmp_path, ROWS), out)
    manifest = write_manifest(out, split, []).read_text()
    assert "[advisory]" in manifest and "[reasoning]" in manifest
    line = next(l for l in manifest.splitlines() if "ai_deep_review " in l)
    assert "[advisory]" in line
    line = next(l for l in manifest.splitlines() if l.strip().startswith("enter"))
    assert "[reasoning]" in line
    # And it must say plainly that the advisory layer is not decision reasoning.
    assert "Not in the" in manifest and "decision path" in manifest


def test_fills_snapshots_are_copied_so_the_package_stands_alone(tmp_path):
    """decision -> order -> execution is only complete with these, and the
    venue forgets executions after ~7 days, so they are irreplaceable."""
    tr = tmp_path / "track_record"
    tr.mkdir()
    (tr / "fills_2026-08-13.json").write_text('{"summary": {}}')
    (tr / "fills_2026-08-14.json").write_text('{"summary": {}}')
    (tr / "equity.csv").write_text("not a fills snapshot")

    out = tmp_path / "sub"
    out.mkdir()
    copied = copy_fills(tr, out)
    assert [p.name for p in copied] == ["fills_2026-08-13.json",
                                        "fills_2026-08-14.json"]
    assert (out / "fills" / "fills_2026-08-13.json").exists()
    assert not (out / "fills" / "equity.csv").exists()


def test_it_never_modifies_the_ledger_it_reads(tmp_path):
    """The source of truth for the whole competition. Read-only, and pinned."""
    led = _ledger(tmp_path, ROWS)
    before = sha256_of(led)
    split_ledger(led, tmp_path / "sub")
    assert sha256_of(led) == before

    import inspect
    import deploy.reasoning_log as m
    src = inspect.getsource(m)
    for forbidden in ('LEDGER.open("w"', "unlink(", "rmtree(", '"a")'):
        assert forbidden not in src, forbidden
