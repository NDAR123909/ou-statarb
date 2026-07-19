"""
Regression tests for the LTP agent's kill switch vs. bad equity reads.

The live shakeout exposed the failure these pin: when the portfolio overview
returned all-zero balances (a defunded/transitioning account), equity_usdt()
summed to 0.0, the agent read that as a 100% drawdown, and it flattened the
book and looped the kill switch hourly on phantom losses. The fix: an
implausibly low nav is treated as a bad read and the bar is skipped — while a
genuine drawdown past 12% still trips the kill switch. These tests lock both
halves in place so the guard can't be refactored away.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import deploy.ltp_agent as agent


class FakeBroker:
    """Minimal duck-typed broker: only what trade_step touches when the book
    is flat (no pairs). equity_usdt is the dial under test."""

    def __init__(self, equity: float):
        self._equity = equity
        self.op_context: dict = {}
        self.on_operation = None

    def equity_usdt(self) -> float:
        return self._equity

    def open_orders(self) -> list:
        return []

    def cancel_all(self, symbol=None) -> None:
        pass


def _run(equity: float, peak: float = 1000.0, halted: bool = False):
    """Run one trade_step against a flat book; capture ledger events."""
    cfg = agent.AgentConfig()
    state = {"peak_equity": peak, "halted": halted, "pairs": {}, "bar": 5}
    events: list[tuple[str, dict]] = []
    original = agent.ledger
    agent.ledger = lambda ev, **f: events.append((ev, f))
    try:
        agent.trade_step(FakeBroker(equity), cfg, state, dry=False)
    finally:
        agent.ledger = original
    return state, [ev for ev, _ in events]


def test_zero_equity_read_does_not_trip_kill_switch():
    # The exact live failure: overview returns 0 -> must NOT flatten/halt.
    state, events = _run(equity=0.0, peak=1000.0)
    assert state["halted"] is False
    assert "kill_switch" not in events
    assert "bad_read" in events
    # a bad read must not pollute the drawdown peak
    assert state["peak_equity"] == 1000.0


def test_partial_read_below_floor_is_skipped():
    # e.g. one of three sub-accounts missing -> implausibly low, not a loss.
    state, events = _run(equity=400.0, peak=1000.0)   # 40% of peak
    assert state["halted"] is False
    assert "bad_read" in events
    assert "kill_switch" not in events


def test_real_drawdown_still_trips_kill_switch():
    # 15% drawdown: past the 12% halt and well above the 50% bad-read floor,
    # so the safety mechanism must still fire.
    state, events = _run(equity=850.0, peak=1000.0)
    assert state["halted"] is True
    assert "kill_switch" in events


def test_healthy_equity_trades_normally():
    state, events = _run(equity=1000.0, peak=1000.0)
    assert state["halted"] is False
    assert "kill_switch" not in events
    assert "bad_read" not in events


def test_drawdown_just_below_threshold_does_not_halt():
    # 11% down: under the 12% halt, above the floor -> normal trading.
    state, events = _run(equity=890.0, peak=1000.0)
    assert state["halted"] is False
    assert "kill_switch" not in events
    assert "bad_read" not in events
