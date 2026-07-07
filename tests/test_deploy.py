"""Tests for the deployment harness: snapshot idempotency, strategy decisions."""

import json
from datetime import date

import numpy as np
import pandas as pd

from statarb.broker import Fill
from deploy.snapshot import take_snapshot, EQUITY_COLUMNS
from deploy.run_strategy import (
    StrategyConfig, refit_models, run_daily, load_state, save_state,
)


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


# --------------------------------------------------------------------------- #
#  Strategy runner                                                            #
# --------------------------------------------------------------------------- #
class FakeExecBroker:
    """Fills every order instantly at the given prices; tracks positions."""

    def __init__(self, prices, equity=1_000_000.0):
        self.px = dict(prices)
        self._equity = equity
        self.book = {}
        self.submitted = []

    def account_snapshot(self):
        return {"equity": self._equity, "cash": self._equity,
                "long_market_value": 0.0, "short_market_value": 0.0,
                "buying_power": 2 * self._equity, "last_equity": self._equity}

    def all_positions(self):
        return [{"symbol": s, "qty": q, "avg_entry_price": self.px[s],
                 "current_price": self.px[s], "market_value": q * self.px[s],
                 "unrealized_pl": 0.0, "side": "long" if q > 0 else "short"}
                for s, q in self.book.items() if q]

    def position(self, symbol):
        return self.book.get(symbol, 0.0)

    def submit(self, symbol, qty):
        qty = float(int(round(qty)))
        self.book[symbol] = self.book.get(symbol, 0.0) + qty
        self.submitted.append((symbol, qty))
        return Fill(0, symbol, qty, self.px[symbol], 0.0,
                    order_id=f"o{len(self.submitted)}", filled=True,
                    status="filled")


def _panel(z_last, n=400, beta=0.8, seed=7):
    """Two log-price series whose spread is small noise, last value z_last
    stationary sigmas away from the mean."""
    rng = np.random.default_rng(seed)
    lb = np.cumsum(rng.normal(0, 0.01, n)) + np.log(100.0)
    spread = rng.normal(0, 0.01, n)
    spread[-1] = z_last * np.std(spread[:-1], ddof=1)
    la = beta * lb + spread + 0.5
    idx = pd.bdate_range("2025-01-01", periods=n)
    return pd.DataFrame({"AAA": np.exp(la), "BBB": np.exp(lb)}, index=idx)


def _model(bars, beta=0.8, entry=1.5, exit_=0.3):
    return {"a": "AAA", "b": "BBB", "beta": beta, "half_life": 8.0,
            "adf_pvalue": 0.001, "entry_z": entry, "exit_z": exit_,
            "z_window": 30, "max_hold": 24}


def _state(models):
    return {"last_run": None, "last_refit": None, "models": models,
            "positions": {}, "blocked": {}}


def test_entry_opens_both_legs_hedged():
    bars = _panel(z_last=+3.0)          # rich spread -> short A, long B
    broker = FakeExecBroker({"AAA": float(bars["AAA"].iloc[-1]),
                             "BBB": float(bars["BBB"].iloc[-1])})
    state = _state({"AAA/BBB": _model(bars)})
    orders = run_daily(broker, state, bars, StrategyConfig(), "2026-07-07")

    entries = [o for o in orders if o["action"] == "entry"]
    assert len(entries) == 2
    pos = state["positions"]["AAA/BBB"]
    assert pos["qty_a"] < 0 and pos["qty_b"] > 0        # short spread
    # hedge ratio in dollars ~ beta
    da = abs(pos["qty_a"]) * broker.px["AAA"]
    db = abs(pos["qty_b"]) * broker.px["BBB"]
    assert abs(db / da - 0.8) < 0.05


def test_stop_flattens_and_blocks_reentry():
    bars = _panel(z_last=-8.0)          # long spread side, blown through stop
    #  (the outlier inflates its own rolling std, so the measured z is ~ -4.4)
    broker = FakeExecBroker({"AAA": float(bars["AAA"].iloc[-1]),
                             "BBB": float(bars["BBB"].iloc[-1])})
    state = _state({"AAA/BBB": _model(bars)})
    # already long the spread
    broker.book = {"AAA": 100.0, "BBB": -80.0}
    state["positions"]["AAA/BBB"] = {"qty_a": 100.0, "qty_b": -80.0,
                                     "g": 1000.0, "side": 1,
                                     "entered": "2026-07-01",
                                     "entry_z": -2.0, "hold": 3}
    orders = run_daily(broker, state, bars, StrategyConfig(), "2026-07-07")

    stops = [o for o in orders if o["action"] == "stop"]
    assert len(stops) == 2
    assert broker.book["AAA"] == 0.0 and broker.book["BBB"] == 0.0
    assert state["blocked"]["AAA/BBB"] == +1            # long side blocked
    assert "AAA/BBB" not in state["positions"]

    # same z next day: still below -entry, but the long side is blocked
    orders2 = run_daily(broker, state, bars, StrategyConfig(), "2026-07-08")
    assert not [o for o in orders2 if o["action"] == "entry"]
    assert "AAA/BBB" not in state["positions"]


def test_reconcile_adopts_broker_truth():
    bars = _panel(z_last=0.0)
    broker = FakeExecBroker({"AAA": float(bars["AAA"].iloc[-1]),
                             "BBB": float(bars["BBB"].iloc[-1])})
    state = _state({"AAA/BBB": _model(bars)})
    # ledger says we hold, broker says the fills never happened
    state["positions"]["AAA/BBB"] = {"qty_a": 100.0, "qty_b": -80.0,
                                     "g": 1000.0, "side": 1,
                                     "entered": "2026-07-01",
                                     "entry_z": -2.0, "hold": 1}
    orders = run_daily(broker, state, bars, StrategyConfig(), "2026-07-07")
    recon = [o for o in orders if o["action"] == "reconcile"]
    assert len(recon) == 1
    assert "AAA/BBB" not in state["positions"]          # dropped, no orders sent
    assert not broker.submitted


def test_model_dropped_flattens_position():
    bars = _panel(z_last=0.0)
    broker = FakeExecBroker({"AAA": float(bars["AAA"].iloc[-1]),
                             "BBB": float(bars["BBB"].iloc[-1])})
    broker.book = {"AAA": 100.0, "BBB": -80.0}
    state = _state({})                                   # refit dropped the pair
    state["positions"]["AAA/BBB"] = {"qty_a": 100.0, "qty_b": -80.0,
                                     "g": 1000.0, "side": 1,
                                     "entered": "2026-07-01",
                                     "entry_z": -2.0, "hold": 1}
    run_daily(broker, state, bars, StrategyConfig(), "2026-07-07")
    assert broker.book["AAA"] == 0.0 and broker.book["BBB"] == 0.0
    assert "AAA/BBB" not in state["positions"]


def test_refit_finds_planted_cointegrated_pair():
    """A strongly cointegrated pair among unrelated names must survive the
    gate and carry cost-aware bands."""
    rng = np.random.default_rng(3)
    n = 378
    lb = np.cumsum(rng.normal(0, 0.012, n)) + np.log(80.0)
    # OU spread with a ~8 day half-life, sd chosen to clear costs comfortably
    spread = np.zeros(n)
    for t in range(1, n):
        spread[t] = 0.917 * spread[t - 1] + rng.normal(0, 0.008)
    la = 0.9 * lb + spread + 1.0
    lc = np.cumsum(rng.normal(0, 0.015, n)) + np.log(50.0)   # unrelated
    idx = pd.bdate_range("2025-01-01", periods=n)
    logp = pd.DataFrame({"AAA": la, "BBB": lb, "CCC": lc}, index=idx)

    cfg = StrategyConfig(candidates=[("AAA", "BBB"), ("AAA", "CCC")])
    models = refit_models(logp, cfg)
    assert "AAA/BBB" in models and "AAA/CCC" not in models
    m = models["AAA/BBB"]
    assert 0.8 < m["beta"] < 1.0
    assert m["entry_z"] > m["exit_z"] >= 0.0
    assert m["z_window"] >= 15 and m["max_hold"] >= 5


def test_state_roundtrip(tmp_path):
    p = tmp_path / "state.json"
    s = load_state(p)
    s["last_run"] = "2026-07-07"
    s["blocked"]["KO/PEP"] = -1
    save_state(p, s)
    s2 = load_state(p)
    assert s2["last_run"] == "2026-07-07"
    assert s2["blocked"]["KO/PEP"] == -1
