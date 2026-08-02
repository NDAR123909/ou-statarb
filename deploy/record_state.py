"""
deploy/record_state.py — append today's live state to a committed history.

The review log records what we DECIDED; this records what was TRUE. Written
because a session's memory of "we're at #9 with equity 1006" went stale within
two days while the file still asserted it, and a later session starting cold
would have believed it. State that is generated cannot drift; state that is
remembered does.

It appends one JSON line per run to `track_record/ltp_state_history.jsonl`:
equity, peak, drawdown, kill-switch headroom, halted flag, active pairs and
their bands, open positions, and the ledger event tally. Read-only against the
exchange — it opens no automation session and places no orders, exactly like
`status.py`, whose report it reuses.

Idempotent per day by default: re-running replaces the day's row rather than
duplicating it, so a cron plus a manual run cannot double-count.

    set -a; source /root/ltp.env; set +a
    python deploy/record_state.py            # append/replace today's row
    python deploy/record_state.py --show 7   # print the last 7 rows

Suggested cron on the droplet (23:50 UTC, just before the contest's daily
NAV cut):
    50 23 * * * cd /root/ou-statarb && set -a && . /root/ltp.env && set +a && \\
        .venv/bin/python deploy/record_state.py >> /var/log/ltp_record.log 2>&1

The history is only durable once it leaves the droplet. To commit and push it,
append to that cron line:

    && git add track_record/ \\
    && git commit -m "track: daily state $(date -u +%F)" || true \\
    && git push origin claude/offline-competition-deploy-nuk5tz

`|| true` on the commit is deliberate: a day with no change must not fail the
job. **Prerequisite, and it is not optional** — the droplet's remote is HTTPS
with no stored credential, so an interactive `git push` prompts for a username
and password. Cron has no TTY to answer that, and the push will hang or fail
silently while the log keeps reporting a healthy append. Install a deploy key
or a stored PAT first and verify with a real (non-`--dry-run`) push from a
non-interactive shell before trusting the cron.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.ltp_agent import AgentConfig                    # noqa: E402
from deploy.status import build_report                      # noqa: E402

HISTORY = Path(__file__).resolve().parent.parent / "track_record" / \
    "ltp_state_history.jsonl"


def _row(rep: dict) -> dict:
    """The durable subset: enough to reconstruct the trajectory later."""
    return {
        "date": rep["ts"][:10],
        "ts": rep["ts"],
        "equity": rep.get("equity"),
        "peak_equity": rep.get("peak_equity"),
        "drawdown_pct": rep.get("drawdown_pct"),
        "kill_level": rep.get("kill_level"),
        "headroom_to_kill": rep.get("headroom_to_kill"),
        "headroom_to_floor": rep.get("headroom_to_floor"),
        "halted": rep.get("halted"),
        "bar": rep.get("bar"),
        "news_gate": (rep.get("news_gate") or {}).get("status"),
        "pairs": [{k: p.get(k) for k in
                   ("pair", "side", "z", "entry_z", "exit_z", "half_life_h",
                    "beta", "hold_bars")}
                  for p in rep.get("pairs", [])],
        "open_positions": rep.get("open_positions", []),
        "ledger_tally": rep.get("ledger_tally", {}),
    }


def _load() -> list[dict]:
    if not HISTORY.exists():
        return []
    rows = []
    for line in HISTORY.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass          # never let one bad line lose the whole history
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--show", type=int, metavar="N",
                    help="print the last N recorded rows and exit")
    ap.add_argument("--allow-duplicate", action="store_true",
                    help="append even if today is already recorded")
    args = ap.parse_args()

    if args.show:
        for row in _load()[-args.show:]:
            print(f"{row.get('date')}  equity={row.get('equity')}  "
                  f"dd={row.get('drawdown_pct')}%  "
                  f"halted={row.get('halted')}  "
                  f"pairs={[p.get('pair') for p in row.get('pairs', [])]}")
        return 0

    rep = build_report(AgentConfig(), use_marks=True, ledger_n=0)
    row = _row(rep)

    rows = _load()
    if not args.allow_duplicate and any(r.get("date") == row["date"]
                                        for r in rows):
        rows = [r for r in rows if r.get("date") != row["date"]]
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text("".join(json.dumps(r, default=float) + "\n"
                                   for r in rows))
        note = "replaced today's row"
    else:
        note = "appended"

    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a") as fh:
        fh.write(json.dumps(row, default=float) + "\n")

    eq = row["equity"]
    print(f"{note}: {row['date']} equity="
          f"{'unavailable' if eq is None else f'{eq:.2f}'} "
          f"dd={row['drawdown_pct']}% halted={row['halted']} "
          f"pairs={[p['pair'] for p in row['pairs']]}")
    print(f"history: {HISTORY} ({len(rows) + 1} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
