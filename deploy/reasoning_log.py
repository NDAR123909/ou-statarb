"""
deploy/reasoning_log.py — assemble a Track A Reasoning Log submission, one phase
at a time.

The organizer requires a Reasoning Log for each phase. Phase I's was due
**2026-08-24 23:59 GMT+8 (15:59 UTC)** and failing to submit affected
eligibility to advance. Phase II's is due *"within one week after the
competition ends"* (organizer, 2026-10-28), read conservatively as **2026-11-11
15:59 UTC**. It is built as a script rather than assembled by hand at a
deadline.

**Each package covers one phase's window, and nothing else.** Until 2026-10-28
this script read the whole ledger and copied every fills snapshot. That was
right on 2026-08-21, when the ledger held only Phase I. Run after Phase II, it
would have packaged mostly Phase I under a Phase II label. So `--phase` is now
required, and it selects a window from `PHASES`:

- ledger records are kept when `since <= ts < until`;
- fills snapshots are kept by the date in their file name;
- records outside the window are counted in the manifest, never silently
  dropped;
- a record with no readable timestamp cannot be placed in a phase, so it is
  counted as undated.

**The problem is volume, not substance.** The ledger is dominated by
`ai_deep_review`: an ADVISORY layer that never touched a trading decision.
Nothing imports it, the agent never reads the ledger (`_LEDGER_PATH` appears
twice in `ltp_agent.py`: the constant and an append), and they are separate
processes. That is pinned by
`tests/test_ai_deep_review.py::test_it_places_no_orders_and_touches_no_agent_state`.

So the split is by **role**, not by size. Submitting the advisory layer
unlabelled inside the main file would drown the decisions that drove trades in
analysis that drove none of them. For a Reasoning Audit, that is the same class
of defect as an under-logged decision. The exact counts and sizes go in
MANIFEST.txt rather than into prose here, because a ratio typed into a document
goes stale the next time the script runs.

    reasoning.jsonl          every decision, operation and refit, plus the
                             hourly ai_spread_assessment / news_assessment /
                             ai_refit_review records the agent actually
                             consulted. This is the audit chain:
                             decision -> reasoning -> order.
    ai_deep_review.jsonl.gz  the advisory layer, compressed and labelled as
                             not being in the decision path.
    fills/                   the outcome side. decision -> order -> execution
                             is only complete with these, and the venue serves
                             ~7 days of executions before forgetting, so these
                             dated snapshots are the only durable record of
                             what was realised.
    MANIFEST.txt             row counts, byte sizes, a full event tally and
                             SHA-256 per file.

**Phase II's advisory layer is too large to email, or to publish from the
droplet.** Phase I's ~3,400 deep reviews compressed to 9.2 MB; Phase II runs
~21,000. Everything under `track_record/` is committed by the droplet's nightly
`git add track_record/`. A file over GitHub's 100 MB limit would make that push
fail, and every later one with it, silently. So for Phase II:

- the file stays in the package and in the manifest, with its SHA-256;
- a `.gitignore` written into the package keeps it out of git;
- the emailed archive leaves it out;
- it is delivered separately, and anyone can check it against the digest.

**Two refusals guard the deadline:**

- **A build before the window closes is PARTIAL.** The manifest says so, and
  the build is refused anywhere under `track_record/`, where the cron would
  publish it as if it were the submission.
- **A final build is refused while the narrative still carries a
  `[FINAL AFTER THE BELL` placeholder.**

Read-only with respect to trading and to the ledger: it reads the ledger and
writes a separate output directory, and never modifies its source.

    python deploy/reasoning_log.py --phase II --out /root/p2dry   # dry run
    python deploy/reasoning_log.py --phase II --archive           # the final
    python deploy/reasoning_log.py --phase I                      # Phase I's window
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import sys
import tarfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "deploy" / "ltp_ledger.jsonl"
TRACK_RECORD = REPO / "track_record"
FILLS_GLOB = "fills_*.json"

# Events produced by the advisory review layer, which never reached a trading
# decision. Split out and labelled rather than dropped: it IS part of the
# team's AI usage and the organizer asked about that separately, but presenting
# it as decision reasoning would be an overclaim.
ADVISORY_EVENTS = ("ai_deep_review",)

# Written into a narrative wherever a number can only be known after the phase
# closes. A final build refuses to ship a document that still contains one.
PLACEHOLDER = "[FINAL AFTER THE BELL"
# What the refusal actually matches: any bracketed FINAL, in any case, however
# a Markdown paragraph wraps it. Matching PLACEHOLDER exactly missed one the
# Phase II narrative already held, split across a line inside the marker.
_BLANK = re.compile(r"\[\s*final\b", re.I)


@dataclass(frozen=True)
class Phase:
    """One scored phase: the window its package covers, and what ships with it.

    `until` is exclusive. `unpublished` names package files that are kept out
    of git and out of the emailed archive. They are still built, still hashed
    in the manifest, and delivered separately.
    """
    label: str
    since: str
    until: str
    narrative: str          # file under deploy/
    out_name: str           # directory under track_record/
    unpublished: tuple[str, ...] = ()


PHASES = {
    # 00:00 GMT+8 07-20 -> 00:00 GMT+8 08-22, one minute after the 23:59 bell.
    # The package actually sent was built at 2026-08-21T16:13:20Z from the
    # whole ledger, so it also held the 16:00:23 bar after the bell. A rebuild
    # gives the scored window, not a byte-copy of what was sent.
    "I": Phase("Phase I", since="2026-07-19T16:00:00+00:00",
               until="2026-08-21T16:00:00+00:00",
               narrative="REASONING_LOG.md", out_name="phase1_submission"),
    # 00:00 GMT+8 09-09 (export_phase_ledger.PHASE_II_OPEN) -> 00:00 GMT+8
    # 11-05, one minute after the 23:59 bell (organizer, 2026-10-27).
    "II": Phase("Phase II", since="2026-09-08T16:00:00+00:00",
                until="2026-11-04T16:00:00+00:00",
                narrative="REASONING_LOG_PHASE2.md",
                out_name="phase2_submission",
                unpublished=("ai_deep_review.jsonl.gz",)),
}


def sha256_of(path: Path) -> str:
    """Streaming digest — the ledger is tens of MB and need not be resident."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _instant(stamp) -> datetime | None:
    """An ISO timestamp as an aware datetime; naive means UTC.

    None for an absent or unreadable stamp. A window cannot place such a
    record in a phase, and guessing one would be worse than counting it.
    """
    if not stamp:
        return None
    try:
        t = datetime.fromisoformat(str(stamp))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def blanks(text: str) -> list[int]:
    """Line numbers of every placeholder left in a narrative."""
    return [text.count("\n", 0, m.start()) + 1 for m in _BLANK.finditer(text)]


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def split_ledger(ledger: Path, out_dir: Path, since: str | None = None,
                 until: str | None = None) -> dict:
    """Write reasoning.jsonl and ai_deep_review.jsonl.gz; return the tally.

    With a window, only records with `since <= ts < until` are written and
    tallied. Every record left out is counted as before, after or undated in
    `window`, so the manifest can say what the package does not contain.

    Malformed lines are counted rather than silently skipped. A submission that
    quietly drops records it could not parse is exactly the kind of thing an
    audit is entitled to be told about.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    reasoning_path = out_dir / "reasoning.jsonl"
    advisory_path = out_dir / "ai_deep_review.jsonl.gz"
    lo, hi = _instant(since), _instant(until)
    windowed = lo is not None or hi is not None
    outside = {"before": 0, "after": 0, "undated": 0}

    tally: dict[str, int] = {}
    # Which risk controls actually fired. "Five refusal paths exist" and "one
    # of them has ever triggered" are very different claims, and an audit is
    # entitled to the second rather than the first.
    refusals: dict[str, int] = {}
    # Which stop fired: the hourly bar or the five-minute sample. The field
    # exists from 2026-10-05; stops before it carry none.
    stops: dict[str, int] = {}
    counts = {"reasoning": 0, "advisory": 0, "unparseable": 0}
    first_ts, last_ts = None, None

    # Streamed, not read whole: by Phase II's close the ledger is ~200 MB, and
    # this runs on the droplet beside the live agent.
    with ledger.open(encoding="utf-8") as source, \
            reasoning_path.open("w", encoding="utf-8") as reasoning, \
            gzip.open(advisory_path, "wt", encoding="utf-8") as advisory:
        for line in source:
            line = line.rstrip("\r\n")
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                counts["unparseable"] += 1
                continue
            stamp = record.get("ts")
            if windowed:
                t = _instant(stamp)
                if t is None:
                    outside["undated"] += 1
                    continue
                if lo is not None and t < lo:
                    outside["before"] += 1
                    continue
                if hi is not None and t >= hi:
                    outside["after"] += 1
                    continue
            event = record.get("event", "?")
            tally[event] = tally.get(event, 0) + 1
            if event in ("skip", "size_reduced"):
                why = record.get("reason") or event
                refusals[why] = refusals.get(why, 0) + 1
            if event == "stop":
                trigger = record.get("trigger") or "unlabelled"
                stops[trigger] = stops.get(trigger, 0) + 1
            if stamp:
                first_ts = stamp if first_ts is None else min(first_ts, stamp)
                last_ts = stamp if last_ts is None else max(last_ts, stamp)
            if event in ADVISORY_EVENTS:
                advisory.write(line + "\n")
                counts["advisory"] += 1
            else:
                reasoning.write(line + "\n")
                counts["reasoning"] += 1

    window = ({"since": since, "until": until, **outside} if windowed
              else None)
    return {"tally": tally, "counts": counts, "refusals": refusals,
            "stops": stops, "window": window,
            "first_ts": first_ts, "last_ts": last_ts,
            "files": [reasoning_path, advisory_path]}


def fills_dates(since: str, until: str) -> tuple[date, date]:
    """The snapshot dates a window covers, inclusive at both ends.

    Each snapshot reconciles roughly the week before it, so consecutive ones
    overlap. Including the day the window opens and the day it closes can
    therefore add records from outside it, but never miss one inside it; the
    reader matches fills to decisions by timestamp anyway.
    """
    return (_instant(since).date(),
            (_instant(until) - timedelta(microseconds=1)).date())


def _snapshot_date(path: Path) -> date | None:
    try:
        return date.fromisoformat(path.stem[len("fills_"):])
    except ValueError:
        return None


def copy_fills(track_record: Path, out_dir: Path, first: date | None = None,
               last: date | None = None) -> list[Path]:
    """Bring the dated fills snapshots into the package.

    They are the outcome half of the audit chain and they are irreplaceable:
    `transaction executions` serves roughly seven days and then refuses, so
    anything not snapshotted at the time is gone. Copied rather than referenced
    so the submission is self-contained in an email.

    With `first`/`last`, only snapshots dated inside them are copied. A file
    whose name carries no date cannot be placed in a phase, so it is left out.
    """
    dest = out_dir / "fills"
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for snap in sorted(track_record.glob(FILLS_GLOB)):
        if first is not None or last is not None:
            day = _snapshot_date(snap)
            if (day is None or (first is not None and day < first)
                    or (last is not None and day > last)):
                continue
        target = dest / snap.name
        shutil.copyfile(snap, target)
        copied.append(target)
    return copied


def missing_snapshot_days(fills: list[Path], first: date, last: date,
                          built: datetime) -> list[date]:
    """Days in [first, last] with no snapshot in the package.

    Coverage is stated, not assumed. The build day itself is never reported:
    its snapshot is written at 23:55 UTC and may simply not exist yet.
    """
    have = {_snapshot_date(p) for p in fills}
    end = min(last, built.date() - timedelta(days=1))
    days, day = [], first
    while day <= end:
        if day not in have:
            days.append(day)
        day += timedelta(days=1)
    return days


def copy_narrative(out_dir: Path, src: Path | None = None) -> Path | None:
    """Bring the written explanation into the package, as REASONING_LOG.md.

    Kept in `deploy/` under version control rather than generated, so it is
    reviewable and diffable like anything else we ship. Each phase has its
    own; Phase I's stays exactly as it was submitted.
    """
    src = src or REPO / "deploy" / "REASONING_LOG.md"
    if not src.exists():
        return None
    dest = out_dir / "REASONING_LOG.md"
    shutil.copyfile(src, dest)
    return dest


def keep_out_of_git(out_dir: Path, names: tuple[str, ...]) -> Path | None:
    """A `.gitignore` inside the package, so the nightly cron skips `names`.

    Nested rather than added to the repository's own `.gitignore`, because the
    droplet commits from its own branch, `live/track-record`, whose root
    `.gitignore` is not this one. A rule that travels with the package holds
    wherever the package is built.
    """
    if not names:
        return None
    path = out_dir / ".gitignore"
    path.write_text(
        "# Written by deploy/reasoning_log.py. Too large to publish through the\n"
        "# droplet's nightly `git add track_record/`. Delivered separately and\n"
        "# pinned by its SHA-256 in MANIFEST.txt.\n"
        + "".join(f"{name}\n" for name in names), encoding="utf-8")
    return path


def write_manifest(out_dir: Path, split: dict, fills: list[Path],
                   phase: Phase | None = None, partial: bool = False,
                   built: datetime | None = None,
                   fill_span: tuple[date, date] | None = None) -> Path:
    """Counts, sizes and SHA-256 per file.

    The project's stated goal is a tamper-evident record. A manifest costs
    nothing and turns "trust this file" into "check this file".
    """
    phase = phase or PHASES["I"]
    built = built or datetime.now(timezone.utc)
    window = split.get("window")
    stops = split.get("stops", {})
    manifest = out_dir / "MANIFEST.txt"
    narrative = out_dir / "REASONING_LOG.md"
    files = [p for p in split["files"] if p.exists()] + fills
    if narrative.exists():
        files.insert(0, narrative)
    counts, tally = split["counts"], split["tally"]

    lines = [
        f"LTP Liquidity Arena 2026 — Track A {phase.label} Reasoning Log",
        "Team NDAR",
        f"Generated {built.isoformat(timespec='seconds')}",
    ]
    if partial:
        lines.append(f"STATUS  PARTIAL -- built before the window closes at "
                     f"{window['until'] if window else '?'}. "
                     f"A dry run. NOT A SUBMISSION.")
    else:
        lines.append("STATUS  final")
    if window:
        lines += [
            f"Window  {window['since'] or 'start of ledger'} <= ts < "
            f"{window['until'] or 'end of ledger'}",
            f"Outside the window, not packaged: {window['before']} before, "
            f"{window['after']} after, {window['undated']} undated",
            f"Records span {split['first_ts']} .. {split['last_ts']}",
        ]
    else:
        lines.append(f"Ledger covers {split['first_ts']} .. {split['last_ts']}")
    lines += [
        "",
        "CONTENTS",
        "  REASONING_LOG.md         how to read these records: architecture,",
        "                           the decision -> order -> execution chain,",
        "                           and a stated list of known gaps.",
        "  reasoning.jsonl          the audit chain: every decision, operation",
        "                           and refit, plus the hourly AI assessments",
        "                           the agent actually consulted.",
        "  ai_deep_review.jsonl.gz  ADVISORY analysis layer. Not in the",
        "                           decision path: nothing imports it, the",
        "                           agent never reads the ledger, and they run",
        "                           as separate processes. Included for",
        "                           completeness of AI usage, NOT presented as",
        "                           decision reasoning.",
    ]
    if "ai_deep_review.jsonl.gz" in phase.unpublished:
        lines += [
            "                           NOT in the emailed archive: too large.",
            "                           Delivered separately; check it against",
            "                           its SHA-256 below.",
        ]
    lines += [
        "  fills/                   dated execution snapshots reconciled",
        "                           against the venue -- the outcome half of",
        "                           the chain.",
        "",
        f"  records in reasoning.jsonl        {counts['reasoning']}",
        f"  records in ai_deep_review.jsonl   {counts['advisory']}",
        f"  unparseable lines skipped         {counts['unparseable']}",
        f"  fills snapshots                   {len(fills)}",
    ]
    if fill_span:
        gaps = missing_snapshot_days(fills, *fill_span, built)
        lines.append(f"  days with no fills snapshot       "
                     f"{', '.join(d.isoformat() for d in gaps) or 'none'}")
    lines += [
        "",
        f"EVENT TALLY ({'inside the window' if window else 'whole ledger'})",
    ]
    for event, n in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])):
        role = "advisory" if event in ADVISORY_EVENTS else "reasoning"
        lines.append(f"  {event:<28}{n:>7}   [{role}]")

    named = ("side_blocked", "news_veto", "anomaly_veto", "gross_cap",
             "min_notional", "automation_budget", "size_reduced")
    lines += ["", "RISK CONTROLS THAT ACTUALLY FIRED",
              "  (paths that never fired are listed too, at zero -- an audit",
              "   should not have to infer a control's silence from absence)"]
    for name in named:
        lines.append(f"  {name:<28}{split['refusals'].get(name, 0):>7}")
    for name, n in sorted(split["refusals"].items()):
        if name not in named:
            lines.append(f"  {name:<28}{n:>7}")

    lines += ["", "STOPS BY TRIGGER",
              "  (`trigger` exists from 2026-10-05; every stop before it is",
              "   unlabelled and was the hourly-bar stop, the only one there was)"]
    for name in ("bar", "intrabar"):
        lines.append(f"  {name:<28}{stops.get(name, 0):>7}")
    for name, n in sorted(stops.items()):
        if name not in ("bar", "intrabar"):
            lines.append(f"  {name:<28}{n:>7}")

    lines += ["", "SHA-256"]
    for path in files:
        note = ("   <- not in the emailed archive; delivered separately"
                if path.name in phase.unpublished else "")
        lines.append(f"  {sha256_of(path)}  {path.stat().st_size:>10}  "
                     f"{path.relative_to(out_dir)}{note}")

    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def make_archive(out_dir: Path, dest_dir: Path | None = None,
                 exclude: tuple[str, ...] = ()) -> Path:
    """One .tar.gz for the email. The directory stays for browsing in git.

    `exclude` names files left out of the archive (they ship separately); the
    package's own `.gitignore` is never sent.
    """
    dest_dir = dest_dir or out_dir.parent
    archive = dest_dir / f"{out_dir.name}.tar.gz"
    skip = set(exclude) | {".gitignore"}

    def keep(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        return None if Path(info.name).name in skip else info

    with tarfile.open(archive, "w:gz") as tar:
        tar.add(out_dir, arcname=out_dir.name, filter=keep)
    return archive


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="build one phase's Reasoning Log package")
    ap.add_argument("--phase", choices=sorted(PHASES), required=True,
                    help="which phase's window to package")
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--out", type=Path, default=None,
                    help="default: track_record/<phase>_submission")
    ap.add_argument("--since", help="override the window's start (ISO, UTC)")
    ap.add_argument("--until", help="override the window's end, exclusive")
    ap.add_argument("--narrative", type=Path, default=None,
                    help="default: the phase's file under deploy/")
    ap.add_argument("--archive", action="store_true",
                    help="also write a .tar.gz for the email")
    args = ap.parse_args(argv)

    phase = PHASES[args.phase]
    since, until = args.since or phase.since, args.until or phase.until
    if _instant(since) is None or _instant(until) is None:
        print(f"unreadable window: {since!r} .. {until!r}", file=sys.stderr)
        return 1
    out = args.out or TRACK_RECORD / phase.out_name
    narrative_src = args.narrative or REPO / "deploy" / phase.narrative
    now = now or datetime.now(timezone.utc)
    partial = now < _instant(until)

    if not args.ledger.exists():
        print(f"no ledger at {args.ledger}", file=sys.stderr)
        return 1
    if partial and _under(out, TRACK_RECORD):
        print(f"** refusing: the {phase.label} window closes at {until}, so "
              f"this build is partial, and {out} is under track_record/, "
              f"which the droplet's nightly cron publishes. Use --out "
              f"somewhere else for a dry run. **", file=sys.stderr)
        return 1
    left = (blanks(narrative_src.read_text(encoding="utf-8"))
            if narrative_src.exists() else [])
    if left:
        if not partial:
            print(f"** refusing: {narrative_src} still has placeholders at "
                  f"line(s) {', '.join(map(str, left))}. Fill them before "
                  f"building the package that gets sent. **", file=sys.stderr)
            return 1
        print(f"  note: {len(left)} placeholder(s) left in the narrative -- "
              f"expected before the window closes")

    print(f"{phase.label}: {since} <= ts < {until}"
          + ("   ** PARTIAL: the window has not closed **" if partial else ""))
    print(f"reading {args.ledger} "
          f"({args.ledger.stat().st_size / 1e6:.1f} MB) ...")
    split = split_ledger(args.ledger, out, since, until)
    first, last = fills_dates(since, until)
    fills = copy_fills(args.ledger.parent.parent / "track_record", out,
                       first, last)
    narrative = copy_narrative(out, narrative_src)
    if narrative is None:
        print(f"** {narrative_src} missing -- the package would ship raw "
              f"records with no explanation **", file=sys.stderr)
    keep_out_of_git(out, phase.unpublished)
    manifest = write_manifest(out, split, fills, phase, partial, now,
                              (first, last))

    counts, window = split["counts"], split["window"]
    print(f"\n  reasoning.jsonl         {counts['reasoning']:>7} records  "
          f"{(out / 'reasoning.jsonl').stat().st_size / 1e6:>6.2f} MB")
    print(f"  ai_deep_review.jsonl.gz {counts['advisory']:>7} records  "
          f"{(out / 'ai_deep_review.jsonl.gz').stat().st_size / 1e6:>6.2f} MB")
    print(f"  fills snapshots         {len(fills):>7} files  "
          f"({first} .. {last})")
    print(f"  outside the window      {window['before']} before, "
          f"{window['after']} after, {window['undated']} undated")
    if counts["unparseable"]:
        print(f"  ** {counts['unparseable']} unparseable lines skipped "
              f"(recorded in the manifest) **", file=sys.stderr)
    print(f"  manifest                {manifest}")

    if args.archive:
        # Never under track_record/: the nightly cron would publish it.
        dest = REPO if _under(out, TRACK_RECORD) else out.parent
        archive = make_archive(out, dest, phase.unpublished)
        size = archive.stat().st_size / 1e6
        print(f"\n  archive  {archive}  {size:.2f} MB")
        if size > 20.0:
            print("  ** over 20 MB — likely too large to email; send a repo "
                  "link instead **", file=sys.stderr)
        for name in phase.unpublished:
            print(f"  {name} is NOT in the archive: deliver it separately "
                  f"({(out / name).stat().st_size / 1e6:.2f} MB); its SHA-256 "
                  f"is in the manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
