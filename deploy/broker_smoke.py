"""
One-shot integration test of AlpacaPaperBroker against the REAL paper API.

This exists because the broker had never touched the live endpoint before the
deployment work — every response-shape assumption in broker.py is checked here
once, loudly, instead of failing silently at 21:35 UTC on a market day. Run it
by hand (with ALPACA_KEY_ID / ALPACA_SECRET_KEY exported) or via the
broker-smoke GitHub Actions workflow.

What it exercises, in order:
  auth        constructor validates the account
  clock       market_open / trading_date
  data        latest trades + adjusted daily bars (records which feed answered)
  account     snapshot fields, position lookup for a symbol we don't hold
  orders      submits a 1-share market order in Ford:
                market open   -> expects a real fill, then unwinds it
                market closed -> expects a resting order, then cancels it
  fills       todays_fills() parses without error

It leaves the account exactly as it found it (position unwound or order
canceled). Exits nonzero on the first failure.
"""

from __future__ import annotations

import sys
import traceback

from statarb.broker import AlpacaPaperBroker

TEST_SYMBOL = "F"          # cheap, extremely liquid — a $12 test order
BAR_SYMBOLS = ["KO", "PEP"]


def main() -> int:
    print("== auth ==")
    broker = AlpacaPaperBroker()
    print("account active, equity =", broker.equity())

    print("\n== clock ==")
    is_open = broker.market_open()
    print("market_open =", is_open, "| trading_date =", broker.trading_date())

    print("\n== data: latest trades ==")
    px = broker.prices(BAR_SYMBOLS + [TEST_SYMBOL])
    print(px, "| feed =", broker.last_feed_used)
    assert all(p > 0 for p in px.values()), "non-positive price"

    print("\n== data: adjusted daily bars ==")
    bars = broker.daily_bars(BAR_SYMBOLS, lookback_days=30)
    print(bars.tail(3).to_string(), "\nrows =", len(bars),
          "| feed =", broker.last_feed_used)
    assert len(bars) >= 20, f"expected ~30 daily bars, got {len(bars)}"
    assert list(bars.columns) == sorted(BAR_SYMBOLS) or \
        set(bars.columns) == set(BAR_SYMBOLS), f"bad columns {bars.columns}"

    print("\n== account ==")
    snap = broker.account_snapshot()
    print(snap)
    assert snap["equity"] > 0
    print("positions:", broker.all_positions())
    print(f"position({TEST_SYMBOL}) =", broker.position(TEST_SYMBOL))

    print("\n== orders ==")
    fill = broker.submit(TEST_SYMBOL, 1)
    print("submit +1:", fill)
    if is_open:
        assert fill.filled and fill.price > 0, f"expected a fill, got {fill}"
        unwind = broker.submit(TEST_SYMBOL, -1)
        print("unwind -1:", unwind)
        assert unwind.filled, f"unwind did not fill: {unwind}"
    else:
        assert not fill.filled and fill.order_id, \
            f"expected a resting order after hours, got {fill}"
        broker.cancel(fill.order_id)
        print("canceled resting order", fill.order_id)

    print("\n== today's fills ==")
    fills = broker.todays_fills()
    print(f"{len(fills)} fill(s) today")
    for f in fills[:5]:
        print(" ", f)

    print("\nSMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        print("\nSMOKE TEST FAILED")
        sys.exit(1)
