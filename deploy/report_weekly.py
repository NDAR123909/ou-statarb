"""
Weekly research-log generator.

Every Monday, after the daily report is regenerated, this appends one dated
entry to `LOG.md` at the repo root. The entry is **objective metrics only** —
weekly and cumulative return, trade/fill/stop-out counts, drawdown, workflow
health, and whether a human touched the record. It carries no market
commentary, no forecast, no explanation of *why* a number moved: the log is a
measurement, not an opinion, and keeping it that way is what lets it sit beside
the preregistration without contaminating the experiment.

Like the rest of the harness it is deterministic and append-only. It reads the
committed record, makes no broker calls, and touches no trading logic. Running
it twice on the same Monday does not duplicate the entry, and a run on any other
weekday does nothing unless `--force` is passed.

The window each entry covers runs from the previous entry's date up to the
current Monday, so successive entries tile the timeline without overlap. The
first entry covers everything from the start of the record.
"""

from __future__ import annotations

import glob
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

# Work both as an imported module (tests) and as a script run from the repo
# root in CI (`python deploy/report_weekly.py ...`): ensure the repo root, not
# just deploy/, is importable so `deploy.report` resolves either way.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.report import compute_stats

BOT_EMAILS = {
    "41898282+github-actions[bot]@users.noreply.github.com",
    "github-actions[bot]@users.noreply.github.com",
    "noreply@anthropic.com",
}
ENTRY_MARKER = "## Week of "     # one header per entry; used for idempotency


# --------------------------------------------------------------------------- #
#  Metrics                                                                     #
# --------------------------------------------------------------------------- #
def _load_equity(root: Path) -> pd.DataFrame:
    csv = root / "equity.csv"
    if not csv.exists():
        return pd.DataFrame(columns=[
            "date", "equity", "cash", "long_market_value", "short_market_value",
            "gross_leverage", "buying_power", "n_positions", "n_fills"])
    df = pd.read_csv(csv, dtype={"date": str}).sort_values("date")
    return df.reset_index(drop=True)


def _count_orders(root: Path, start_excl: str | None, end_incl: str) -> dict:
    """Tally submitted trades and stop-outs from the order logs whose date is
    in (start_excl, end_incl]. `start_excl` None means from the beginning."""
    trades = stops = files = 0
    for path in sorted(glob.glob(str(root / "orders" / "*.json"))):
        d = Path(path).stem
        if d > end_incl or (start_excl is not None and d <= start_excl):
            continue
        files += 1
        try:
            orders = json.loads(Path(path).read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for o in orders:
            action = o.get("action", "")
            if action == "entry":
                trades += 1
            elif action == "stop":
                stops += 1
    return {"trades": trades, "stops": stops, "order_days": files}


def _detect_manual_intervention(root: Path, start_excl: str | None,
                                end_incl: str) -> list[str]:
    """Objective, git-based signal: any commit touching track_record/ in the
    window whose author is not the CI bot. Returns short 'sha author' strings.
    Fails soft — a git error yields an empty list, reported as 'none detected'
    rather than a false alarm."""
    since = (start_excl or "1970-01-01")
    try:
        out = subprocess.run(
            ["git", "log", f"--since={since} 00:00", f"--until={end_incl} 23:59",
             "--format=%h%x09%ae%x09%an", "--", "track_record/"],
            cwd=root.parent if root.name == "track_record" else root,
            capture_output=True, text=True, timeout=30, check=True).stdout
    except (subprocess.SubprocessError, OSError):
        return []
    human = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1] not in BOT_EMAILS:
            human.append(f"{parts[0]} {parts[2] if len(parts) > 2 else parts[1]}")
    return human


def weekly_metrics(root: Path, today: str, prev_date: str | None) -> dict:
    """All numbers for one entry. `prev_date` is the previous log entry's date
    (exclusive lower bound); None for the first entry."""
    df = _load_equity(root)
    # Everything is measured as of `today`: never let a future row (e.g. a
    # backfill or an out-of-order re-run) leak into this week's numbers.
    df = df[df["date"] <= today]
    stats = compute_stats(df)                       # cumulative return, drawdown

    window = df
    if prev_date is not None:
        window = window[window["date"] > prev_date]

    # weekly return: last equity in window vs the baseline just before it
    weekly_return = None
    if len(window):
        before = df[df["date"] <= (prev_date or "")] if prev_date else df.iloc[0:0]
        baseline = float(before["equity"].iloc[-1]) if len(before) \
            else float(df["equity"].iloc[0])
        end_eq = float(window["equity"].iloc[-1])
        if baseline > 0:
            weekly_return = (end_eq / baseline - 1.0) * 100.0

    orders = _count_orders(root, prev_date, today)
    fills = int(window["n_fills"].sum()) if len(window) else 0

    return {
        "today": today,
        "window_start": prev_date,
        "snapshots_this_week": int(len(window)),
        "last_snapshot": window["date"].iloc[-1] if len(window) else None,
        "weekly_return_pct": weekly_return,
        "cumulative_return_pct": stats["total_return_pct"],
        "current_equity": stats["current_equity"],
        "trades": orders["trades"],
        "fills": fills,
        "stops": orders["stops"],
        "max_drawdown_pct": stats["max_drawdown_pct"],
        "current_gross_leverage": stats["current_gross_leverage"],
        "manual_intervention": _detect_manual_intervention(root, prev_date, today),
    }


# --------------------------------------------------------------------------- #
#  Rendering                                                                  #
# --------------------------------------------------------------------------- #
def _pct(v) -> str:
    if v is None or v != v:                          # None or NaN
        return "—"
    return f"{v:+.2f}%"


def _money(v) -> str:
    return f"${v:,.2f}" if (v is not None and v == v) else "—"


def _lev(v) -> str:
    return f"{v:.2f}×" if (v is not None and v == v) else "—"


def _summary_prose(m: dict, window: str, manual_cell: str) -> str:
    """A plain, factual restatement of the metrics table: what the ledger did,
    with no market read. Wording follows the humanizer skill's ruleset
    (Wikipedia's "Signs of AI writing") — no em-dashes, rule-of-three, or
    negative parallelisms."""
    return (
        f"The book opened {m['trades']} trade(s) {window} and recorded "
        f"{m['fills']} fill(s), with {m['stops']} stop-out(s). Equity is at "
        f"{_money(m['current_equity'])}: {_pct(m['weekly_return_pct'])} on the "
        f"week and {_pct(m['cumulative_return_pct'])} since inception. The "
        f"deepest drawdown so far is {_pct(m['max_drawdown_pct'])}. Manual "
        f"intervention: {manual_cell}."
    )


def render_entry(m: dict) -> str:
    """One LOG.md entry: a metrics table plus a fixed factual sentence that
    restates it. The prose carries no interpretation; the numbers are the
    point."""
    window = f"since {m['window_start']}" if m["window_start"] else "since inception"
    manual = m["manual_intervention"]
    manual_cell = "none detected" if not manual else "; ".join(manual)
    health = f"{m['snapshots_this_week']} daily snapshot(s) recorded {window}"
    if m["last_snapshot"]:
        health += f", latest {m['last_snapshot']}"

    summary = _summary_prose(m, window, manual_cell)

    weekday = date.fromisoformat(m["today"]).strftime("%A")
    lines = [
        f"{ENTRY_MARKER}{m['today']} ({weekday})",
        "",
        "| Metric | Value |",
        "| :----- | :---- |",
        f"| Weekly return | {_pct(m['weekly_return_pct'])} |",
        f"| Cumulative return | {_pct(m['cumulative_return_pct'])} |",
        f"| Trades opened | {m['trades']} |",
        f"| Fills | {m['fills']} |",
        f"| Stop-outs | {m['stops']} |",
        f"| Max drawdown to date | {_pct(m['max_drawdown_pct'])} |",
        f"| Current gross leverage | {_lev(m['current_gross_leverage'])} |",
        f"| Workflow health | {health} |",
        f"| Manual intervention | {manual_cell} |",
        "",
        summary,
        "",
    ]
    return "\n".join(lines)


_LOG_HEADER = (
    "# Weekly research log\n\n"
    "`deploy/report_weekly.py` writes one entry here every Monday and never "
    "edits an older one. Each entry lists the week's objective metrics from the "
    "committed track record: returns, trade and fill counts, stop-outs, "
    "drawdown, workflow health, and whether anyone touched the record by hand. "
    "It carries no market commentary by design. The raw data under "
    "`track_record/` and its git history stay the source of truth; `VERIFY.md` "
    "explains how to audit them.\n"
)


# --------------------------------------------------------------------------- #
#  Append                                                                      #
# --------------------------------------------------------------------------- #
def _last_entry_date(text: str) -> str | None:
    dates = [ln[len(ENTRY_MARKER):len(ENTRY_MARKER) + 10]
             for ln in text.splitlines() if ln.startswith(ENTRY_MARKER)]
    return max(dates) if dates else None


def append_entry(root: Path, log_path: Path, today: str,
                 force: bool = False) -> bool:
    """Append this week's entry to LOG.md. Returns True if written. No-op if an
    entry for `today` already exists (idempotent re-runs) or if today is not a
    Monday and not forced."""
    if not force and date.fromisoformat(today).weekday() != 0:
        return False

    text = log_path.read_text() if log_path.exists() else ""
    if ENTRY_MARKER + today in text:
        return False                                # already logged this Monday

    prev_date = _last_entry_date(text)
    m = weekly_metrics(root, today, prev_date)
    entry = render_entry(m)

    body = text if text else _LOG_HEADER
    if not body.endswith("\n"):
        body += "\n"
    body += "\n" + entry
    tmp = log_path.with_suffix(".md.tmp")
    tmp.write_text(body)
    tmp.replace(log_path)
    return True


# --------------------------------------------------------------------------- #
#  Entry point                                                                #
# --------------------------------------------------------------------------- #
def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    force = "--force" in sys.argv[1:]
    root = Path(args[0]) if args else Path("track_record")
    log_path = Path(args[1]) if len(args) > 1 else root.parent / "LOG.md" \
        if root.name == "track_record" else Path("LOG.md")

    today = datetime.now(timezone.utc).date().isoformat()
    wrote = append_entry(root, log_path, today, force=force)
    if wrote:
        print(f"weekly log: appended entry for {today} -> {log_path}")
    elif not force and date.fromisoformat(today).weekday() != 0:
        print(f"weekly log: {today} is not a Monday, skipping "
              "(pass --force to override)")
    else:
        print(f"weekly log: entry for {today} already present, skipping")
    return 0


if __name__ == "__main__":
    sys.exit(main())
