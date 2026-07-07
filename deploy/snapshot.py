"""
Daily snapshot of the Alpaca paper account into the public track record.

This is the half of the harness that makes the record VERIFIABLE: every run
appends one row of account state to track_record/equity.csv and writes the
full position/fill detail to track_record/positions/YYYY-MM-DD.json. The git
commit that follows is the timestamp — the history of this file, not any claim
in a README, is the track record.

Design constraints (from the deployment plan, non-negotiable):

  idempotent   re-running on the same day REPLACES that day's row and json
               rather than appending a duplicate. Intra-day re-runs just
               refresh; the committed history still shows every change.
  atomic       both files are written to a temp file and os.replace()d, so a
               crash mid-run can never leave a partial row for someone to
               explain away later.
  loud         auth errors raise in the broker constructor; nothing here
               catches them. A silent gap in the record is worse than a red
               workflow run.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

EQUITY_COLUMNS = [
    "date", "equity", "cash", "long_market_value", "short_market_value",
    "gross_leverage", "buying_power", "n_positions", "n_fills",
]


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def take_snapshot(broker, root: Path) -> dict:
    """
    Pull account state from `broker` and persist it under `root`.

    `broker` needs account_snapshot(), all_positions(), todays_fills() and
    trading_date() — AlpacaPaperBroker in production, a stub in tests.
    Returns the equity row that was written.
    """
    root = Path(root)
    (root / "positions").mkdir(parents=True, exist_ok=True)

    date = str(broker.trading_date())
    account = broker.account_snapshot()
    positions = broker.all_positions()
    fills = broker.todays_fills()

    gross = account["long_market_value"] + abs(account["short_market_value"])
    row = {
        "date": date,
        "equity": account["equity"],
        "cash": account["cash"],
        "long_market_value": account["long_market_value"],
        "short_market_value": account["short_market_value"],
        "gross_leverage": round(gross / account["equity"], 4)
                          if account["equity"] > 0 else 0.0,
        "buying_power": account["buying_power"],
        "n_positions": len(positions),
        "n_fills": len(fills),
    }

    # equity.csv: read, drop any row for today, append the fresh one.
    csv_path = root / "equity.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"date": str})
    else:
        df = pd.DataFrame(columns=EQUITY_COLUMNS)
    df = df[df["date"] != date]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df = df.sort_values("date").reset_index(drop=True)
    _atomic_write(csv_path, df.to_csv(index=False))

    # positions/YYYY-MM-DD.json: the full detail behind the row.
    detail = {
        "date": date,
        "taken_at_utc": datetime.now(timezone.utc).isoformat(),
        "account": account,
        "positions": positions,
        "fills": fills,
    }
    _atomic_write(root / "positions" / f"{date}.json",
                  json.dumps(detail, indent=2, default=str))

    return row


def main() -> int:
    from statarb.broker import AlpacaPaperBroker

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("track_record")
    broker = AlpacaPaperBroker()          # raises loudly on bad/missing keys
    row = take_snapshot(broker, root)
    print("snapshot written:", row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
