"""Tests for the deployment harness: snapshot idempotency and file shape."""

import json
from datetime import date

import pandas as pd

from deploy.snapshot import take_snapshot, EQUITY_COLUMNS


class FakeBroker:
    """Just enough of AlpacaPaperBroker's surface for the snapshot."""

    def __init__(self, equity=100_000.0, day="2026-07-07"):
        self._equity = equity
        self._day = day

    def trading_date(self):
        return date.fromisoformat(self._day)

    def account_snapshot(self):
        return {
            "equity": self._equity,
            "cash": self._equity - 30_000.0,
            "long_market_value": 20_000.0,
            "short_market_value": -10_000.0,
            "buying_power": 2 * self._equity,
            "last_equity": self._equity,
        }

    def all_positions(self):
        return [
            {"symbol": "KO", "qty": 100.0, "avg_entry_price": 60.0,
             "current_price": 61.0, "market_value": 6100.0,
             "unrealized_pl": 100.0, "side": "long"},
            {"symbol": "PEP", "qty": -50.0, "avg_entry_price": 170.0,
             "current_price": 169.0, "market_value": -8450.0,
             "unrealized_pl": 50.0, "side": "short"},
        ]

    def todays_fills(self):
        return [{"order_id": "abc", "symbol": "KO", "qty": 100.0,
                 "price": 60.0, "submitted_at": None,
                 "filled_at": f"{self._day}T09:30:01-04:00",
                 "status": "filled"}]


def test_snapshot_writes_row_and_json(tmp_path):
    row = take_snapshot(FakeBroker(), tmp_path)
    df = pd.read_csv(tmp_path / "equity.csv")
    assert list(df.columns) == EQUITY_COLUMNS
    assert len(df) == 1
    assert df.iloc[0]["equity"] == 100_000.0
    # gross = 20k long + 10k short over 100k equity
    assert abs(df.iloc[0]["gross_leverage"] - 0.30) < 1e-9
    assert row["n_positions"] == 2 and row["n_fills"] == 1

    detail = json.loads((tmp_path / "positions" / "2026-07-07.json").read_text())
    assert detail["date"] == "2026-07-07"
    assert len(detail["positions"]) == 2
    assert detail["fills"][0]["symbol"] == "KO"


def test_snapshot_rerun_same_day_no_duplicate(tmp_path):
    take_snapshot(FakeBroker(equity=100_000.0), tmp_path)
    take_snapshot(FakeBroker(equity=100_500.0), tmp_path)   # same day, re-run
    df = pd.read_csv(tmp_path / "equity.csv")
    assert len(df) == 1                       # replaced, not appended
    assert df.iloc[0]["equity"] == 100_500.0  # latest values win


def test_snapshot_appends_across_days(tmp_path):
    take_snapshot(FakeBroker(day="2026-07-06"), tmp_path)
    take_snapshot(FakeBroker(day="2026-07-07"), tmp_path)
    df = pd.read_csv(tmp_path / "equity.csv", dtype={"date": str})
    assert list(df["date"]) == ["2026-07-06", "2026-07-07"]
    assert (tmp_path / "positions" / "2026-07-06.json").exists()
    assert (tmp_path / "positions" / "2026-07-07.json").exists()
