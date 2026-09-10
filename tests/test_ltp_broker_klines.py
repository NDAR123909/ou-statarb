"""
The kline parser must survive both venues' response shapes.

RapidX returns Binance and OKX candles in materially different forms, and
`ltp_broker.klines()` happens to handle both -- by accident, not by design:

    field        Binance                  OKX
    timestamp    1789056000000 (int)      "1789070400000" (STRING)
    row order    ascending                DESCENDING, newest first
    columns      12                       9

`int()` accepts numeric strings, the trailing `.sort_index()` corrects the
reversal, and only positions 0 and 4 are ever read, which align across both.
Remove any one of those three and OKX silently returns an empty frame -- the
parser swallows everything in a bare `except`, and `fetch_panel` drops a
symbol with no data without a word. That is the same silent-drop that hid
ETC/KAS from the 2026-09-09 universe scan for a day.

So the accidents are pinned here as a contract. Fixtures are literal rows
captured from the live CLI on 2026-09-10, rapidx-cli 1.0.44.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BINANCE_ROWS = [
    [1789056000000, "77218.60", "77280.00", "76760.00", "77172.00", "5962.524",
     1789059599999, "459017197.68200", 143757, "2946.011", "226839332.36970", "0"],
    [1789059600000, "77172.10", "77300.00", "77100.00", "77250.00", "100.0",
     1789063199999, "1.0", 1, "1.0", "1.0", "0"],
]

# Note the ordering: OKX returns NEWEST FIRST.
OKX_ROWS = [
    ["1789070400000", "100.46", "100.46", "100.05", "100.32", "468874",
     "46887.4", "4700434.93", "0"],
    ["1789066800000", "99.69", "100.57", "99.69", "100.46", "830190",
     "83019", "8313197.6", "0"],
]


def _parse(candles):
    """The body of `RapidXBroker.klines`, isolated from the subprocess call."""
    times = pd.to_datetime([int(c[0]) for c in candles], unit="ms", utc=True)
    closes = [float(c[4]) for c in candles]
    return (pd.DataFrame({"time": times, "close": closes})
            .dropna().set_index("time").sort_index())


def test_binance_rows_parse():
    df = _parse(BINANCE_ROWS)
    assert list(df["close"]) == [77172.0, 77250.0]


def test_okx_string_timestamps_parse():
    """OKX stamps are quoted. int() accepts them; a stricter cast would not."""
    assert isinstance(OKX_ROWS[0][0], str)
    assert len(_parse(OKX_ROWS)) == 2


def test_okx_rows_are_reversed_and_the_parser_fixes_it():
    """The fixture is newest-first. Without sort_index the series would run
    backwards and every fitted half-life and z path would be garbage --
    silently, because nothing downstream checks monotonicity."""
    assert int(OKX_ROWS[0][0]) > int(OKX_ROWS[1][0]), "fixture must be reversed"
    df = _parse(OKX_ROWS)
    assert df.index.is_monotonic_increasing
    assert list(df["close"]) == [100.46, 100.32]


def test_close_is_column_four_on_both_venues():
    """OKX ships 9 columns to Binance's 12. Only 0 and 4 are read, and they
    align -- so a parser that reached for a later index would break on OKX."""
    assert len(BINANCE_ROWS[0]) == 12 and len(OKX_ROWS[0]) == 9
    assert _parse(BINANCE_ROWS)["close"].iloc[-1] == 77250.0
    assert _parse(OKX_ROWS)["close"].iloc[-1] == 100.32
