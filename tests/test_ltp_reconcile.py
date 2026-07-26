"""
Tests for startup/per-bar position reconciliation.

These pin the fix for a failure that actually happened live: the state file
was cleared while a pair was open, so the agent restarted believing it was
flat while the exchange still held ~1,193 USDT of gross exposure. Nothing
would ever have exited or stopped that position, and because the pair read as
flat the agent could have opened a second one in the same direction on top of
it. The same inconsistency arises without any human error if the process dies
between placing the two legs of an entry.

The contract: the exchange is the source of truth about what we hold, and
anything the strategy cannot account for is closed rather than adopted.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import deploy.ltp_agent as agent

A = "BINANCE_PERP_TAO_USDT"
B = "BINANCE_PERP_RENDER_USDT"


def _pos(sym, qty, value=500.0):
    return {"sym": sym, "positionQty": str(qty), "positionSide": "NONE",
            "positionValue": str(value)}


class FakeBroker:
    def __init__(self, positions):
        self._positions = positions
        self.closed: list[str] = []
        self.op_context: dict = {}

    def positions(self):
        return self._positions

    @staticmethod
    def _position_qty(p):
        try:
            return float(p.get("positionQty", 0.0))
        except (TypeError, ValueError):
            return 0.0

    def close_position(self, symbol, position_side, max_notional):
        self.closed.append(symbol)
        return {}


def _run(positions, pairs, dry=False):
    broker = FakeBroker(positions)
    state = {"pairs": pairs}
    events: list[tuple[str, dict]] = []
    original = agent.ledger
    agent.ledger = lambda ev, **f: events.append((ev, f))
    try:
        agent.reconcile_positions(broker, state, dry)
    finally:
        agent.ledger = original
    actions = [f.get("action") for ev, f in events if ev == "reconcile"]
    return broker, state, actions


def _pair(side=0):
    return {"a": A, "b": B, "side": side, "hold": 3}


def test_orphaned_position_is_closed():
    """The live failure: state wiped, exchange still holding both legs."""
    broker, state, actions = _run([_pos(A, -2.5), _pos(B, 466.6)],
                                  {f"{A}|{B}": _pair(side=0)})
    assert sorted(broker.closed) == sorted([A, B])
    assert actions == ["unknown_position", "unknown_position"]


def test_half_open_pair_is_flattened():
    """A crash between the two legs leaves naked directional exposure — the
    one thing a market-neutral book must never carry."""
    broker, state, actions = _run([_pos(A, -2.5)], {f"{A}|{B}": _pair(side=-1)})
    assert broker.closed == [A]
    assert "half_open_pair" in actions
    assert state["pairs"][f"{A}|{B}"]["side"] == 0


def test_stale_side_is_cleared_when_exchange_is_flat():
    """State thinks it holds a pair the exchange already closed: correct the
    accounting, close nothing."""
    broker, state, actions = _run([], {f"{A}|{B}": _pair(side=1)})
    assert broker.closed == []
    assert actions == ["clear_stale_side"]
    assert state["pairs"][f"{A}|{B}"]["side"] == 0
    assert state["pairs"][f"{A}|{B}"]["hold"] == 0


def test_consistent_open_pair_is_left_alone():
    """The normal case must be untouched — reconciliation may not churn a
    healthy position."""
    broker, state, actions = _run([_pos(A, -2.5), _pos(B, 466.6)],
                                  {f"{A}|{B}": _pair(side=-1)})
    assert broker.closed == []
    assert actions == []
    assert state["pairs"][f"{A}|{B}"]["side"] == -1


def test_flat_everywhere_is_a_no_op():
    broker, state, actions = _run([], {f"{A}|{B}": _pair(side=0)})
    assert broker.closed == []
    assert actions == []


def test_zero_quantity_positions_are_ignored():
    """RapidX returns closed positions with qty 0; they are not holdings."""
    broker, state, actions = _run([_pos(A, 0), _pos(B, 0)],
                                  {f"{A}|{B}": _pair(side=0)})
    assert broker.closed == []
    assert actions == []


def test_dry_run_reports_but_does_not_close():
    broker, state, actions = _run([_pos(A, -2.5)], {f"{A}|{B}": _pair(side=0)},
                                  dry=True)
    assert broker.closed == []                 # no live order in a dry run
    assert actions == ["unknown_position"]     # but it is still reported
