"""
Guards on the fills reconciliation.

This report is the input to a cost decision -- whether the 5 bps per leg the
cost model assumes is anywhere near what the venue charges -- so the arithmetic
under it has to be pinned. The specific traps, each of which produced a wrong
number by hand before being fixed here:

  * an `enter` whose orders were all rejected did NOT open a position (day one
    produced four of these). Counting them inflates the trade count and
    deflates the win rate, and worse, letting one occupy the pair's slot makes
    the next real close pair with the wrong entry;
  * slippage has to be SIGNED by trade direction, or paying up on a buy and
    selling down cancel out to a comfortable zero;
  * a close with no matching open still has to be reported, not dropped --
    that is exactly the refit-drop audit hole the report is meant to expose.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.fills_report import (                      # noqa: E402
    load_ledger, round_trips, slippage_bps, summarise, trip_slippage,
)

PAIR = "AVAX/SOL"
A = "BINANCE_PERP_AVAX_USDT"
B = "BINANCE_PERP_SOL_USDT"


def _op(ts, decision, symbol, side, qty, price, oid):
    return {"ts": ts, "event": "operation", "op": "place", "decision": decision,
            "pair": PAIR, "symbol": symbol, "side": side, "quantity": qty,
            "order_id": oid, "order_state": "FILLED",
            "executed_qty": str(qty), "executed_price": str(price)}


def _short_spread_round_trip():
    """Sell the spread at 05:00, buy it back at 09:00. Short 63 AVAX @ 6.50,
    long 2.78 SOL @ 73.58; close at 6.40 / 73.00."""
    return [
        {"ts": "2026-08-02T05:00:20+00:00", "event": "enter", "pair": PAIR,
         "side": -1, "z": 1.74, "price_a": 6.51, "price_b": 73.53,
         "beta": 0.492, "nav": 1035.18},
        _op("2026-08-02T05:00:30+00:00", "enter", A, "SELL", 63.0, 6.50, "o1"),
        _op("2026-08-02T05:00:44+00:00", "enter", B, "BUY", 2.78, 73.58, "o2"),
        {"ts": "2026-08-02T09:00:10+00:00", "event": "exit", "pair": PAIR,
         "side": -1, "z": -0.02, "reason": "reverted", "hold_bars": 4,
         "price_a": 6.40, "price_b": 73.00},
        _op("2026-08-02T09:00:20+00:00", "reverted", A, "BUY", 63.0, 6.40, "o3"),
        _op("2026-08-02T09:00:30+00:00", "reverted", B, "SELL", 2.78, 73.00, "o4"),
    ]


def test_round_trip_pnl_from_executed_prices():
    trips = round_trips(_short_spread_round_trip())
    assert len(trips) == 1
    t = trips[0]
    assert t.opened and t.closed
    assert t.reason == "reverted"

    # short AVAX: 63 * (6.40 - 6.50) * -1 = +6.30
    # long  SOL : 2.78 * (73.00 - 73.58)  = -1.6124
    assert round(t.legs["a"].pnl, 4) == 6.3
    assert round(t.legs["b"].pnl, 4) == -1.6124
    assert round(t.gross_pnl, 4) == 4.6876
    assert round(t.hold_hours, 3) == 3.997
    # entry notional, both legs: 63*6.50 + 2.78*73.58
    assert round(t.notional, 2) == 614.05


def test_rejected_entry_did_not_open_and_does_not_steal_the_next_close():
    """Day one: four `enter` decisions whose orders were all rejected."""
    rows = [{"ts": "2026-08-01T00:00:00+00:00", "event": "enter", "pair": PAIR,
             "side": 1, "z": -1.2, "price_a": 6.0, "price_b": 70.0}]
    rows += _short_spread_round_trip()

    trips = round_trips(rows)
    phantom = [t for t in trips if not t.opened]
    assert len(phantom) == 1, "a fill-less entry must not count as opened"

    real = [t for t in trips if t.opened]
    assert len(real) == 1
    # The close must have paired with the REAL entry, not the rejected one.
    assert real[0].entry["ts"].startswith("2026-08-02T05:00")
    assert real[0].closed

    s = summarise(trips)
    assert s["round_trips"] == 1
    assert s["never_opened"] == 1


def test_close_without_a_matching_open_is_still_reported():
    """The refit-drop hole: operations with no decision behind them."""
    rows = [
        {"ts": "2026-08-02T00:01:00+00:00", "event": "exit", "pair": "FIL/AR",
         "side": 1, "reason": "reverted", "price_a": 0.71, "price_b": 1.73},
        _op("2026-08-02T00:01:52+00:00", "close",
            "BINANCE_PERP_FIL_USDT", "SELL", 554.3, 0.7009, "x1"),
    ]
    trips = round_trips(rows)
    assert len(trips) == 1
    assert trips[0].close is not None
    assert not trips[0].opened      # no entry price, so no gross P&L claimed
    assert trips[0].gross_pnl is None


def test_slippage_is_signed_so_adverse_is_always_positive():
    # Bought above the decision price -> we paid up -> adverse.
    assert round(slippage_bps(100.0, 100.1, "BUY"), 6) == 10.0
    # Sold below the decision price -> we sold down -> also adverse.
    assert round(slippage_bps(100.0, 99.9, "SELL"), 6) == 10.0
    # Favourable fills carry the opposite sign rather than cancelling out.
    assert round(slippage_bps(100.0, 99.9, "BUY"), 6) == -10.0
    assert round(slippage_bps(100.0, 100.1, "SELL"), 6) == -10.0
    assert slippage_bps(None, 100.0, "BUY") is None
    assert slippage_bps(100.0, None, "BUY") is None


def test_trip_slippage_uses_the_opposite_side_on_the_close():
    trips = round_trips(_short_spread_round_trip())
    slips = trip_slippage(trips[0])
    assert len(slips) == 4
    # Leg a opened SELL at 6.50 against an intended 6.51 -> adverse 15.4 bps.
    assert round(slips[0], 1) == 15.4
    # It closed BUY at 6.40 against an intended 6.40 -> flat.
    assert round(slips[1], 1) == 0.0


def test_fee_lookup_is_summed_per_leg_and_survives_a_failing_order():
    from deploy.fills_report import attach_fees

    class Broker:
        def executions(self, order_id):
            if order_id == "o3":
                raise RuntimeError("upstream said no")
            return [{"fee": "0.10"}, {"fee": "0.05"}]

    trips = round_trips(_short_spread_round_trip())
    priced = attach_fees(trips, Broker())
    assert priced == 2
    # leg a: entry o1 priced (0.15), exit o3 raised -> only the entry counts.
    assert round(trips[0].legs["a"].fee, 4) == 0.15
    assert round(trips[0].legs["b"].fee, 4) == 0.30

    s = summarise(trips)
    assert s["fees_paid"] == 0.45
    assert s["net_pnl"] == round(4.6876 - 0.45, 4)


def test_load_ledger_skips_malformed_lines(tmp_path):
    p = tmp_path / "l.jsonl"
    p.write_text(json.dumps({"event": "enter"}) + "\n{ this is not json\n"
                 + json.dumps({"event": "exit"}) + "\n")
    assert len(load_ledger(p)) == 2


def test_summarise_on_an_empty_ledger_does_not_divide_by_zero():
    s = summarise([])
    assert s["round_trips"] == 0
    assert s["win_rate"] is None
    assert s["gross_pnl"] is None
