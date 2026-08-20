"""
deploy/reasoning_log.py — assemble the Track A Phase I Reasoning Log submission.

The organizer requires each team to submit its Reasoning Log by **2026-08-24
23:59 GMT+8 (15:59 UTC)** and states that failing to submit affects eligibility
to advance. Phase I is worth exactly two things — advancement and evidence —
and this is the one item that can forfeit the first regardless of where we
finish, so it is built as a script rather than assembled by hand at a deadline.

**The problem is volume, not substance.** `ltp_ledger.jsonl` is ~26 MB, of
which roughly 25 MB is `ai_deep_review`: an ADVISORY layer that never touched a
trading decision. Nothing imports it, the agent never reads the ledger
(`_LEDGER_PATH` appears twice in `ltp_agent.py` — the constant and an append),
and they are separate processes. That is pinned by
`tests/test_ai_deep_review.py::test_it_places_no_orders_and_touches_no_agent_state`.

So the split is by **role**, not by size. Submitting the advisory layer
unlabelled inside the main file would inflate the apparent reasoning volume
about twentyfold and misrepresent what actually drove trades — which, for a
Reasoning Audit, is the same class of defect as an under-logged decision.

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

Read-only with respect to trading and to the ledger: it reads the ledger and
writes a separate output directory, and never modifies its source.

    python deploy/reasoning_log.py                    # build into track_record/
    python deploy/reasoning_log.py --archive          # ...and a .tar.gz to email
    python deploy/reasoning_log.py --out /tmp/sub     # somewhere else
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "deploy" / "ltp_ledger.jsonl"
FILLS_GLOB = "fills_*.json"
DEFAULT_OUT = REPO / "track_record" / "phase1_submission"

# Events produced by the advisory review layer, which never reached a trading
# decision. Split out and labelled rather than dropped: it IS part of the
# team's AI usage and the organizer asked about that separately, but presenting
# it as decision reasoning would be an overclaim.
ADVISORY_EVENTS = ("ai_deep_review",)


def sha256_of(path: Path) -> str:
    """Streaming digest — the ledger is tens of MB and need not be resident."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_ledger(ledger: Path, out_dir: Path) -> dict:
    """Write reasoning.jsonl and ai_deep_review.jsonl.gz; return the tally.

    Malformed lines are counted rather than silently skipped. A submission that
    quietly drops records it could not parse is exactly the kind of thing an
    audit is entitled to be told about.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    reasoning_path = out_dir / "reasoning.jsonl"
    advisory_path = out_dir / "ai_deep_review.jsonl.gz"

    tally: dict[str, int] = {}
    counts = {"reasoning": 0, "advisory": 0, "unparseable": 0}
    first_ts, last_ts = None, None

    with reasoning_path.open("w", encoding="utf-8") as reasoning, \
            gzip.open(advisory_path, "wt", encoding="utf-8") as advisory:
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                counts["unparseable"] += 1
                continue
            event = record.get("event", "?")
            tally[event] = tally.get(event, 0) + 1
            stamp = record.get("ts")
            if stamp:
                first_ts = stamp if first_ts is None else min(first_ts, stamp)
                last_ts = stamp if last_ts is None else max(last_ts, stamp)
            if event in ADVISORY_EVENTS:
                advisory.write(line + "\n")
                counts["advisory"] += 1
            else:
                reasoning.write(line + "\n")
                counts["reasoning"] += 1

    return {"tally": tally, "counts": counts,
            "first_ts": first_ts, "last_ts": last_ts,
            "files": [reasoning_path, advisory_path]}


def copy_fills(track_record: Path, out_dir: Path) -> list[Path]:
    """Bring the dated fills snapshots into the package.

    They are the outcome half of the audit chain and they are irreplaceable:
    `transaction executions` serves roughly seven days and then refuses, so
    anything not snapshotted at the time is gone. Copied rather than referenced
    so the submission is self-contained in an email.
    """
    dest = out_dir / "fills"
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for snap in sorted(track_record.glob(FILLS_GLOB)):
        target = dest / snap.name
        shutil.copyfile(snap, target)
        copied.append(target)
    return copied


def copy_narrative(out_dir: Path) -> Path | None:
    """Bring the written explanation into the package.

    Kept in `deploy/` under version control rather than generated, so it is
    reviewable and diffable like anything else we ship.
    """
    src = REPO / "deploy" / "REASONING_LOG.md"
    if not src.exists():
        return None
    dest = out_dir / "REASONING_LOG.md"
    shutil.copyfile(src, dest)
    return dest


def write_manifest(out_dir: Path, split: dict, fills: list[Path]) -> Path:
    """Counts, sizes and SHA-256 per file.

    The project's stated goal is a tamper-evident record. A manifest costs
    nothing and turns "trust this file" into "check this file".
    """
    manifest = out_dir / "MANIFEST.txt"
    narrative = out_dir / "REASONING_LOG.md"
    files = [p for p in split["files"] if p.exists()] + fills
    if narrative.exists():
        files.insert(0, narrative)
    counts, tally = split["counts"], split["tally"]

    lines = [
        "LTP Liquidity Arena 2026 — Track A Phase I Reasoning Log",
        "Team NDAR",
        f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Ledger covers {split['first_ts']} .. {split['last_ts']}",
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
        "  fills/                   dated execution snapshots reconciled",
        "                           against the venue -- the outcome half of",
        "                           the chain.",
        "",
        f"  records in reasoning.jsonl        {counts['reasoning']}",
        f"  records in ai_deep_review.jsonl   {counts['advisory']}",
        f"  unparseable lines skipped         {counts['unparseable']}",
        f"  fills snapshots                   {len(fills)}",
        "",
        "EVENT TALLY (whole ledger)",
    ]
    for event, n in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])):
        role = "advisory" if event in ADVISORY_EVENTS else "reasoning"
        lines.append(f"  {event:<28}{n:>7}   [{role}]")

    lines += ["", "SHA-256"]
    for path in files:
        lines.append(f"  {sha256_of(path)}  {path.stat().st_size:>10}  "
                     f"{path.relative_to(out_dir)}")

    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def make_archive(out_dir: Path) -> Path:
    """One .tar.gz for the email. The directory stays for browsing in git."""
    archive = out_dir.parent / f"{out_dir.name}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(out_dir, arcname=out_dir.name)
    return archive


def main() -> int:
    ap = argparse.ArgumentParser(description="build the Reasoning Log package")
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--archive", action="store_true",
                    help="also write a .tar.gz next to the output directory")
    args = ap.parse_args()

    if not args.ledger.exists():
        print(f"no ledger at {args.ledger}", file=sys.stderr)
        return 1

    print(f"reading {args.ledger} "
          f"({args.ledger.stat().st_size / 1e6:.1f} MB) ...")
    split = split_ledger(args.ledger, args.out)
    fills = copy_fills(args.ledger.parent.parent / "track_record", args.out)
    narrative = copy_narrative(args.out)
    if narrative is None:
        print("** deploy/REASONING_LOG.md missing -- the package would ship "
              "raw records with no explanation **", file=sys.stderr)
    manifest = write_manifest(args.out, split, fills)

    counts = split["counts"]
    print(f"\n  reasoning.jsonl         {counts['reasoning']:>7} records  "
          f"{(args.out / 'reasoning.jsonl').stat().st_size / 1e6:>6.2f} MB")
    print(f"  ai_deep_review.jsonl.gz {counts['advisory']:>7} records  "
          f"{(args.out / 'ai_deep_review.jsonl.gz').stat().st_size / 1e6:>6.2f} MB")
    print(f"  fills snapshots         {len(fills):>7} files")
    if counts["unparseable"]:
        print(f"  ** {counts['unparseable']} unparseable lines skipped "
              f"(recorded in the manifest) **", file=sys.stderr)
    print(f"  manifest                {manifest}")

    if args.archive:
        archive = make_archive(args.out)
        size = archive.stat().st_size / 1e6
        print(f"\n  archive  {archive}  {size:.2f} MB")
        if size > 20.0:
            print("  ** over 20 MB — likely too large to email; send a repo "
                  "link instead **", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
