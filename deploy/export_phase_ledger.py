"""
deploy/export_phase_ledger.py — publish a phase's trading ledger to track_record/.

The raw ledger is gitignored on purpose: `.gitignore` says only `track_record/**`
is "the product", and operational state stays on the droplet. But the research
lane reads the *repo*, so anything not published is invisible to it — and on
2026-09-16 that cost us. Task 02 was dispatched against a brief citing Phase II
material that existed only on the droplet; Cowork opened by saying so and scoped
itself to Phase I, which was the right call and should not have been necessary.

This is the deliberate path between the two. It is read-only with respect to
trading: no broker calls, no automation session, no writes to agent state.

**Two decisions are baked in, and both are defaults rather than laws.**

*Deep reviews are excluded.* `ai_deep_review` records are ~99% of the raw ledger
by volume — 67 MB against 311 KB for everything else on the first run — and they
are advisory rather than audit chain. The 2026-09-09..09-21 window is also
independently known to be contaminated: `constraint_prompt()` was briefing those
reviews on Phase I constants, telling them the phase was over. `--include-reviews`
opts back in for anyone who wants them anyway.

*The cut defaults to the Phase II open.* 2026-09-08T16:00 UTC is 00:00 GMT+8 on
09-09, which is when the organizer's clock started. Pass `--since` for any other
window.

**The write is atomic.** The output is committed by a cron and by the Wednesday
dispatch runbook, both of which take whatever is on disk. A run interrupted
half-way must not leave a truncated file that looks complete, so this writes to
a temp file beside the target and renames only on success.

    python deploy/export_phase_ledger.py              # Phase II, no reviews
    python deploy/export_phase_ledger.py --since 2026-07-20 --out track_record/phase1.jsonl
    python deploy/export_phase_ledger.py --include-reviews
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "deploy" / "ltp_ledger.jsonl"
DEFAULT_OUT = REPO / "track_record" / "ltp_ledger_phase2.jsonl"

# Phase II opened 16:00 UTC = 00:00 GMT+8 on 2026-09-09. Timestamps in the
# ledger are ISO-8601 with a UTC offset, so a plain string compare against this
# prefix orders correctly without parsing every line.
PHASE_II_OPEN = "2026-09-08T16:00"

# Advisory bulk, not audit chain. See the module docstring.
BULK_EVENTS = frozenset({"ai_deep_review"})

# What the staleness note tells the operator to run. The env load is part of the
# command, not a footnote: on 2026-09-23 this note said "Run deploy/status.py",
# the operator did exactly that in a fresh SSH shell, and equity, positions and
# spend all came back UNAVAILABLE on a healthy agent. The subshell keeps the
# credentials out of the interactive shell afterwards.
STATUS_CMD = ("( set -a; source /root/ltp.env; set +a; "
              ".venv/bin/python deploy/status.py )")


def export(ledger: Path = LEDGER, out: Path = DEFAULT_OUT,
           since: str = PHASE_II_OPEN,
           include_reviews: bool = False) -> dict:
    """Filter `ledger` into `out`. Returns a summary dict; writes atomically.

    Raises FileNotFoundError if the ledger is missing — that is a real failure
    and must not be mistaken for "the phase had no activity", which is what an
    empty output file would look like to whoever reads it next.
    """
    if not ledger.exists():
        raise FileNotFoundError(f"no ledger at {ledger}")

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")

    kept = skipped_bulk = malformed = 0
    first = last = ""
    events: dict[str, int] = {}

    try:
        with ledger.open() as src, tmp.open("w") as dst:
            for line in src:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                ts = rec.get("ts", "")
                if ts < since:
                    continue
                ev = rec.get("event", "")
                if ev in BULK_EVENTS and not include_reviews:
                    skipped_bulk += 1
                    continue
                dst.write(line if line.endswith("\n") else line + "\n")
                kept += 1
                events[ev] = events.get(ev, 0) + 1
                if not first:
                    first = ts
                last = ts
        os.replace(tmp, out)            # atomic; the half-written file never lands
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise

    return {"kept": kept, "skipped_bulk": skipped_bulk, "malformed": malformed,
            "first": first, "last": last, "events": events, "out": str(out)}


def age_hours(ts: str, now: datetime | None = None) -> float | None:
    """Hours since `ts`, or None if it cannot be parsed.

    The dispatch runbook tells the operator to check that the newest record is
    recent. Computing it here beats making them subtract timestamps by hand at
    the point where getting it wrong means dispatching against stale data.
    """
    try:
        stamp = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return ((now or datetime.now(timezone.utc)) - stamp).total_seconds() / 3600.0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="publish a phase's trading ledger into track_record/")
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--since", default=PHASE_II_OPEN,
                    help=f"ISO-8601 prefix; default {PHASE_II_OPEN} (Phase II open)")
    ap.add_argument("--include-reviews", action="store_true",
                    help="keep ai_deep_review records (they are ~99% of the file)")
    args = ap.parse_args()

    try:
        s = export(args.ledger, args.out, args.since, args.include_reviews)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    bad = f", {s['malformed']} malformed skipped" if s["malformed"] else ""
    print(f"{s['kept']} records -> {s['out']}"
          f"   ({s['skipped_bulk']} bulk excluded{bad})")
    print("  events: " + ", ".join(f"{k}:{v}" for k, v in
                                   sorted(s["events"].items(), key=lambda kv: -kv[1])))
    print(f"  first record: {s['first'] or '(none)'}")

    hrs = age_hours(s["last"]) if s["last"] else None
    stale = "" if hrs is None else f"   ({hrs:.1f}h old)"
    print(f"  last record:  {s['last'] or '(none)'}{stale}")

    # A quiet ledger is ambiguous: an empty universe silences the sentinel (see
    # `ltp_agent.py`, `if assets:`), so "idle and healthy" and "dead" look alike
    # from here. Say so rather than picking one -- `status.py` is what settles it.
    if hrs is not None and hrs > 3.0:
        print(f"  NOTE: newest record is {hrs:.1f}h old. That is normal if the "
              f"universe is empty (no pairs -> nothing to screen -> no records). "
              f"Tell idle from stopped before relying on this file:\n"
              f"        {STATUS_CMD}")
    if s["kept"] == 0:
        print("  WARNING: nothing matched. Check --since against the ledger's "
              "own timestamps before publishing this.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
