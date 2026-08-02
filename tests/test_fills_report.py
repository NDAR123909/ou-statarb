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
from datetime import datetime

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


def test_a_failing_symbol_fetch_is_reported_not_swallowed():
    from deploy.fills_report import attach_executions

    class Broker:
        def executions(self, order_id=None, symbol=None):
            raise RuntimeError("upstream said no")

    trips = round_trips(_short_spread_round_trip())
    stat = attach_executions(trips, Broker())
    assert stat["symbols_failed"] == 2
    assert stat["legs_priced"] == 0
    # The ledger-derived entry prices survive; only the venue half is missing.
    assert trips[0].opened


def _close_op_without_a_price(ts, symbol, oid):
    """What `close_position` actually writes: the order id and whether the
    position went flat, but no executed_price and no executed_qty -- unlike
    `place_market`, which emits both. Every exit price in the report has to be
    recovered from the venue because of this."""
    return {"ts": ts, "event": "operation", "op": "close", "decision": "reverted",
            "pair": PAIR, "symbol": symbol, "position_side": "NONE",
            "result": "closed", "residual_qty": None, "order_id": oid}


def test_exit_prices_are_recovered_from_executions_when_the_close_logged_none():
    from deploy.fills_report import attach_executions

    rows = [
        {"ts": "2026-08-02T05:00:20+00:00", "event": "enter", "pair": PAIR,
         "side": -1, "z": 1.74, "price_a": 6.51, "price_b": 73.53},
        _op("2026-08-02T05:00:30+00:00", "enter", A, "SELL", 63.0, 6.50, "o1"),
        _op("2026-08-02T05:00:44+00:00", "enter", B, "BUY", 2.78, 73.58, "o2"),
        {"ts": "2026-08-02T09:00:10+00:00", "event": "exit", "pair": PAIR,
         "side": -1, "z": -0.02, "reason": "reverted",
         "price_a": 6.40, "price_b": 73.00},
        _close_op_without_a_price("2026-08-02T09:00:20+00:00", A, "o3"),
        _close_op_without_a_price("2026-08-02T09:00:30+00:00", B, "o4"),
    ]

    trips = round_trips(rows)
    # Before the venue is asked, the round trip has no exit and no P&L.
    assert trips[0].opened and not trips[0].closed
    assert trips[0].gross_pnl is None

    # The venue is asked by SYMBOL, because a close carries no order id.
    # createAt is epoch ms, a little BEFORE the operation that reports it.
    def ms(iso):
        return int(datetime.fromisoformat(iso).timestamp() * 1000)

    class Broker:
        rows = {
            A: [{"transactionId": "t1", "price": "6.50", "quantity": "63",
                 "fee": "0.02", "createAt": ms("2026-08-02T05:00:25+00:00")},
                {"transactionId": "t3", "price": "6.40", "quantity": "63",
                 "fee": "0.02", "rpnl": "6.30",
                 "createAt": ms("2026-08-02T09:00:15+00:00")}],
            B: [{"transactionId": "t2", "price": "73.58", "quantity": "2.78",
                 "fee": "0.01", "createAt": ms("2026-08-02T05:00:40+00:00")},
                {"transactionId": "t4", "price": "73.00", "quantity": "2.78",
                 "fee": "0.01", "rpnl": "-1.6124",
                 "createAt": ms("2026-08-02T09:00:25+00:00")}],
        }

        def executions(self, order_id=None, symbol=None, **kw):
            return list(self.rows[symbol])

    stat = attach_executions(trips, Broker())
    assert stat["exit_prices"] == 2
    assert stat["entry_prices"] == 0      # entries already had a logged price
    assert stat["legs_unmatched"] == 0
    assert trips[0].closed
    assert round(trips[0].gross_pnl, 4) == 4.6876
    # The venue's own rpnl must corroborate the reconstruction, not replace it.
    assert round(trips[0].venue_pnl, 4) == 4.6876
    assert round(trips[0].fees, 4) == 0.06


def test_vwap_weights_partial_fills_rather_than_averaging_them():
    from deploy.fills_report import _vwap
    # 90 units at 10.00 and 10 at 20.00 is 11.00 weighted, 15.00 unweighted.
    fills = [{"price": "10.00", "qty": "90"}, {"price": "20.00", "qty": "10"}]
    assert round(_vwap(fills), 6) == 11.0
    # With no quantity reported there is nothing to weight by; say so by
    # falling back rather than silently treating one fill as the whole order.
    assert round(_vwap([{"price": "10.0"}, {"price": "20.0"}]), 6) == 15.0
    assert _vwap([{"nothing": "useful"}]) is None


def test_funding_summary_shows_its_working_when_amounts_look_empty():
    """A zero total and an unreadable amount field are indistinguishable in a
    number, and only one of them means funding is free."""
    from deploy.fills_report import funding_summary

    class Broker:
        def statement(self, coin="USDT", **kw):
            return [{"statementType": "FUNDING_FEE", "weirdAmountName": "-0.3"}]

    out = funding_summary(Broker())
    assert out["amounts_parsed"] == 0
    assert "sample_row" in out, "must expose the raw shape, not just a zero"
    assert out["sample_row"]["weirdAmountName"] == "-0.3"


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


def test_history_window_is_derived_from_the_ledger_not_a_hardcoded_date():
    """The venue defaults to 7 days if `begin` is omitted, so a month-long
    competition would silently report only its last week -- and a truncated
    post-mortem that looks complete is worse than no post-mortem."""
    from deploy.fills_report import history_window

    trips = round_trips(_short_spread_round_trip())
    begin_ms, end_ms = history_window(trips)
    entry = datetime.fromisoformat("2026-08-02T05:00:30+00:00").timestamp()
    exit_ = datetime.fromisoformat("2026-08-02T09:00:30+00:00").timestamp()
    assert begin_ms == int((entry - 3600.0) * 1000)
    assert end_ms == int((exit_ + 3600.0) * 1000)

    assert history_window([]) == (None, None)


def test_the_window_and_an_explicit_limit_reach_the_broker():
    from deploy.fills_report import attach_executions, FILL_LIMIT

    seen = []

    class Broker:
        def executions(self, order_id=None, symbol=None, begin_ms=None,
                       end_ms=None, limit=None):
            seen.append((symbol, begin_ms, end_ms, limit))
            return []

    attach_executions(round_trips(_short_spread_round_trip()), Broker())
    assert len(seen) == 2
    for symbol, begin_ms, end_ms, limit in seen:
        assert symbol in (A, B)
        assert begin_ms is not None and end_ms is not None
        assert begin_ms < end_ms
        assert limit == FILL_LIMIT


def test_hitting_the_fill_limit_is_counted_as_truncation(capsys):
    from deploy.fills_report import attach_executions, FILL_LIMIT

    class Broker:
        def executions(self, symbol=None, **kw):
            return [{"transactionId": str(i), "price": "1", "quantity": "1",
                     "createAt": "0"} for i in range(FILL_LIMIT)]

    stat = attach_executions(round_trips(_short_spread_round_trip()), Broker())
    assert stat["symbols_truncated"] == 2
    assert "truncated" in capsys.readouterr().err


def test_a_long_history_is_sliced_into_windows_the_venue_accepts():
    """RapidX rejects a wide begin/end span with upstream 400001 'Exceed
    dayTime limit', so a competition longer than one slice -- the normal case
    after week two -- must be fetched in pieces."""
    from deploy.fills_report import slice_window, MAX_WINDOW_S

    day = 86_400_000
    windows = slice_window(0, 15 * day)
    assert len(windows) == 3
    assert windows[0][0] == 0 and windows[-1][1] == 15 * day
    # Contiguous, no gaps: a gap would drop trades silently.
    for (_, prev_end), (next_begin, _) in zip(windows, windows[1:]):
        assert prev_end == next_begin
    assert all(hi - lo <= MAX_WINDOW_S * 1000 for lo, hi in windows)

    # A short span stays a single call, and an unknown span asks for the
    # venue's own default rather than inventing one.
    assert len(slice_window(0, day)) == 1
    assert slice_window(None, None) == [(None, None)]


def test_fills_repeated_across_a_window_edge_are_counted_once():
    from deploy.fills_report import fetch_symbol_fills

    stat = {"fills_fetched": 0, "symbols_failed": 0, "symbols_truncated": 0,
            "windows_failed": 0, "sample_fill_keys": None}

    class Broker:
        def executions(self, symbol=None, **kw):
            return [{"transactionId": "dup", "price": "1", "quantity": "1",
                     "createAt": "0"}]

    pools = fetch_symbol_fills(Broker(), [A], stat, 0, 15 * 86_400_000)
    assert len(pools[A]) == 1, "the same transaction must not be banked twice"
    assert stat["fills_fetched"] == 1


def test_one_failing_window_does_not_discard_the_others():
    from deploy.fills_report import fetch_symbol_fills

    stat = {"fills_fetched": 0, "symbols_failed": 0, "symbols_truncated": 0,
            "windows_failed": 0, "sample_fill_keys": None}

    class Broker:
        calls = 0

        def executions(self, symbol=None, begin_ms=None, **kw):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("Exceed dayTime limit")
            return [{"transactionId": f"t{self.calls}", "price": "1",
                     "quantity": "1", "createAt": str(begin_ms)}]

    pools = fetch_symbol_fills(Broker(), [A], stat, 0, 15 * 86_400_000)
    assert len(pools[A]) == 2, "a partial history beats none"
    assert stat["windows_failed"] == 1
    assert stat["symbols_failed"] == 1
