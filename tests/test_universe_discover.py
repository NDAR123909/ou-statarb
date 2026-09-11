"""
Guards on the instrument probe.

The tool exists because there is no listing endpoint: all 53 RapidX
capabilities take a symbol as input and none returns a list, so the universe
can only be probed name by name. Its whole value is the three-way
classification established on 2026-09-10 with a deliberate control probe --
and if that collapses back into a binary the tool starts reporting typos as
"the venue does not have it", which is the conclusion that nearly buried WTI
crude for a day.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.ltp_broker import RapidXError, RapidXResult      # noqa: E402
from deploy.universe_discover import (                       # noqa: E402
    CRYPTO_BASES, MALFORMED, UNSUPPORTED, probe, sweep,
)


class _FakeBroker:
    """Stands in for the CLI. `script` maps symbol -> payload or Exception."""

    def __init__(self, script):
        self.script = script
        self.calls = []

    def symbol_info(self, symbol):
        self.calls.append(symbol)
        out = self.script.get(symbol, RapidXError(
            RapidXResult(False, "BUSINESS_ERROR", UNSUPPORTED,
                         "RapidX upstream business error 401011", {}),
            "market get-symbol-info"))
        if isinstance(out, Exception):
            raise out
        return out


def _err(code, message="x"):
    return RapidXError(RapidXResult(False, "FAIL", code, message, {}),
                       "market get-symbol-info")


def test_a_live_symbol_carries_its_spec_through():
    b = _FakeBroker({"OKX_PERP_CL_USDT": {
        "originalSymbol": "CL-USDT-SWAP", "state": "live",
        "contractSize": "0.1", "minSize": "1", "minNotional": "0",
        "tickSize": "0.01", "defaultLeverage": "5", "safeLeverage": "10"}})
    row = probe(b, "OKX_PERP_CL_USDT")
    assert row["state"] == "live"
    assert row["original"] == "CL-USDT-SWAP"
    assert row["contract_size"] == "0.1"
    # minNotional and contract size decide whether a 1,000 USDT book can trade
    # it at all, so they travel with the symbol rather than being re-fetched.
    assert row["min_notional"] == "0" and row["min_size"] == "1"


def test_malformed_and_unsupported_stay_distinct():
    """The whole point. RCLI12001 never reached the venue -- it means we spelled
    it wrong, and OKX's own `CL-USDT-SWAP` returns exactly that. RCLI22001 means
    the venue was asked and said no. Collapsing them turns a naming convention
    into a false negative about the universe."""
    b = _FakeBroker({"A": _err(MALFORMED), "B": _err(UNSUPPORTED)})
    assert probe(b, "A")["state"] == "malformed"
    assert probe(b, "B")["state"] == "unsupported"


def test_an_unexpected_failure_is_error_not_unsupported():
    """A timeout or a broken CLI must never be recorded as 'the venue does not
    list this'. That is an absence of evidence wearing the costume of one."""
    b = _FakeBroker({"A": _err("RCLI99999"), "B": RuntimeError("boom")})
    assert probe(b, "A")["state"] == "error"
    assert probe(b, "B")["state"] == "error"


def test_an_empty_payload_is_not_reported_as_live():
    b = _FakeBroker({"A": {}})
    assert probe(b, "A")["state"] == "error"


def test_a_sweep_survives_every_name_failing():
    """A discovery run that dies on the first bad name reports the venue as
    empty. Every row must come back, whatever happened to it."""
    b = _FakeBroker({})
    rows = sweep(b, ["OKX"], ["AAA", "BBB", "CCC"])
    assert len(rows) == 3
    assert {r["state"] for r in rows} == {"unsupported"}
    assert [r["base"] for r in rows] == ["AAA", "BBB", "CCC"]
    assert b.calls == ["OKX_PERP_AAA_USDT", "OKX_PERP_BBB_USDT",
                       "OKX_PERP_CCC_USDT"]


def test_the_sweep_covers_the_live_book():
    """A manifest that omits what we already trade cannot be diffed against
    the current universe, which is the main thing it is for."""
    assert "BTC" in CRYPTO_BASES and "ETH" in CRYPTO_BASES
    assert len(CRYPTO_BASES) == 30


def test_symbols_are_built_in_the_rapidx_convention():
    """`OKX_PERP_<BASE>_USDT`, documented in KlinesInput's own description --
    which we did not read, and so spent a morning concluding that OKX's native
    `CL-USDT-SWAP` meant the instrument was unavailable."""
    b = _FakeBroker({})
    sweep(b, ["BINANCE", "OKX"], ["CL"])
    assert b.calls == ["BINANCE_PERP_CL_USDT", "OKX_PERP_CL_USDT"]
