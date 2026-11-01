"""
The operator's entry freeze -- it can only refuse risk.

Decided at the final review (2026-11-01). The team was 2nd, one point clear
of 3rd, with three days left. The ×1.5 decision had been "a variance choice
for a top-3 objective" while outside the top three; inside it, the same
objective calls for less variance. Under the reproduced scorer, freezing moved
the chance of a top-3 finish from ~75-78% to ~95-97%.

A freeze that blocked an exit or a stop would turn "less variance" into an
unmanaged position, which is the one failure that matters here. So these pin
both halves: a live signal is refused and recorded, and everything that closes
risk still closes it.
"""

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import deploy.ltp_agent as agent                                     # noqa: E402
from deploy.ltp_agent import AgentConfig, entries_frozen             # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A, B = "BINANCE_PERP_1000SHIB_USDT", "BINANCE_PERP_DOGE_USDT"
KEY = f"{A}|{B}"


class Venue:
    def __init__(self, prices, nav=1037.70):
        self.prices, self.nav = prices, nav
        self.placed: list[str] = []
        self.closed: list[str] = []
        self.op_context: dict = {}

    def equity_usdt(self):
        return self.nav

    def mark_price(self, symbol):
        return self.prices[symbol]

    def round_qty(self, symbol, qty):
        return round(qty, 6)

    def meets_min_notional(self, symbol, qty, price):
        return True

    def budget_left(self):
        return 12000.0

    def place_market(self, symbol, side, position_side, qty, max_notional,
                     client_order_id):
        self.placed.append(symbol)
        return {"orderState": "FILLED"}

    def close_position(self, symbol, position_side, max_notional):
        self.closed.append(symbol)
        return {}


def _pair(side=0, **kw):
    p = {"a": A, "b": B, "beta": 0.857, "mu": -3.18, "sigma": 0.005,
         "entry_z": 0.6, "exit_z": 0.0, "half_life": 19.6, "dvol": 0.002,
         "side": side, "hold": 28 if side else 0, "blocked": 0,
         "notional": 760.0 if side else 0.0,
         "entry_mu": -3.18, "entry_sigma": 0.005, "entry_beta": 0.857}
    p.update(kw)
    return p


def _prices(z, pair):
    lb = np.log(0.075)
    la = pair["mu"] + z * pair["sigma"] + pair["beta"] * lb
    return {A: float(np.exp(la)), B: 0.075}


@pytest.fixture
def run(tmp_path, monkeypatch):
    ledger = tmp_path / "l.jsonl"
    monkeypatch.setattr(agent, "_LEDGER_PATH", str(ledger))
    switch = tmp_path / "ENTRY_FREEZE"
    cfg = AgentConfig(state_path=str(tmp_path / "s.json"),
                      hwm_path=str(tmp_path / "h.json"),
                      entry_freeze_path=str(switch))

    def _run(z, pair, frozen, state=None):
        if frozen:
            switch.write_text("")
        elif switch.exists():
            switch.unlink()
        state = state or {"peak_equity": 1039.78, "halted": False, "bar": 1,
                          "pairs": {KEY: pair}}
        venue = Venue(_prices(z, pair))
        agent.trade_step(venue, cfg, state, dry=False)
        recs = ([json.loads(l) for l in ledger.read_text().splitlines()]
                if ledger.exists() else [])
        return recs, venue, state
    return _run


def _ev(recs, event):
    return [r for r in recs if r["event"] == event]


# ---------------------------------------------------------- refusing risk --

def test_frozen_a_live_signal_is_refused_and_recorded(run):
    pair = _pair()
    recs, venue, state = run(0.8, pair, frozen=True)     # beyond the 0.6 band
    assert venue.placed == [] and _ev(recs, "enter") == []
    skip, = _ev(recs, "skip")
    assert skip["reason"] == "entry_freeze" and skip["side_wanted"] == -1
    assert "frozen" in skip["reasoning"] and "not a view" in skip["reasoning"]
    assert pair["side"] == 0


def test_unfrozen_the_same_signal_enters(run):
    """The control: without the file nothing changes, and no freeze record."""
    pair = _pair()
    recs, venue, state = run(0.8, pair, frozen=False)
    assert venue.placed == [A, B]
    assert len(_ev(recs, "enter")) == 1
    assert _ev(recs, "entry_freeze") == [] and _ev(recs, "skip") == []


def test_a_quiet_bar_refuses_nothing_so_writes_no_skip(run):
    recs, venue, _ = run(0.2, _pair(), frozen=True)       # inside the band
    assert _ev(recs, "skip") == [] and venue.placed == []


def test_a_blocked_side_is_still_reported_as_blocked(run):
    """The freeze is checked after the re-entry block, so a signal the block
    refused keeps its own, truer reason."""
    recs, _, _ = run(0.8, _pair(blocked=-1), frozen=True)
    skip, = _ev(recs, "skip")
    assert skip["reason"] == "side_blocked"


# ------------------------------------------------- closing risk still works --

def test_frozen_an_open_position_still_exits_on_reversion(run):
    pair = _pair(side=-1)                                 # short spread
    recs, venue, _ = run(-0.1, pair, frozen=True)         # crossed exit_z = 0
    exit_, = _ev(recs, "exit")
    assert exit_["reason"] == "reverted"
    assert venue.closed == [A, B] and venue.placed == []
    assert pair["side"] == 0


def test_frozen_an_open_position_still_stops(run):
    pair = _pair(side=-1)
    recs, venue, _ = run(4.13, pair, frozen=True)         # past the 3.5 stop
    stop, = _ev(recs, "stop")
    assert stop["trigger"] == "bar"
    assert venue.closed == [A, B] and venue.placed == []
    assert pair["side"] == 0 and pair["blocked"] == -1


def test_frozen_the_intrabar_stop_still_fires(tmp_path, monkeypatch):
    """The five-minute path never reads the switch; pinned so it never does."""
    monkeypatch.setattr(agent, "_LEDGER_PATH", str(tmp_path / "l.jsonl"))
    switch = tmp_path / "ENTRY_FREEZE"
    switch.write_text("")
    cfg = AgentConfig(entry_freeze_path=str(switch))
    pair = _pair(side=-1)
    state = {"pairs": {KEY: pair}, "halted": False, "peak_equity": 1039.78}
    venue = Venue(_prices(3.9, pair))
    readings: dict = {}
    agent.sample_open_positions(venue, cfg, state, readings)
    assert agent.intrabar_stop(venue, cfg, state, readings, dry=False)
    assert venue.closed == [A, B]


# --------------------------------------------------------- the audit trail --

def test_the_switch_is_recorded_once_each_way(run):
    """Even with no signal at all, the ledger says the book was frozen, so a
    flat stretch cannot be read as the strategy choosing to sit out."""
    pair = _pair()
    recs, _, state = run(0.2, pair, frozen=True)
    recs, _, state = run(0.2, pair, frozen=True, state=state)
    on = _ev(recs, "entry_freeze")
    assert len(on) == 1 and on[0]["active"] is True
    assert "2026-11-01" in on[0]["reasoning"]

    recs, venue, state = run(0.8, pair, frozen=False, state=state)
    off = [r for r in _ev(recs, "entry_freeze") if r["active"] is False]
    assert len(off) == 1
    assert venue.placed == [A, B]              # and entries resume


def test_the_switch_is_a_file_read_every_bar(tmp_path):
    p = tmp_path / "ENTRY_FREEZE"
    cfg = AgentConfig(entry_freeze_path=str(p))
    assert not entries_frozen(cfg)
    p.write_text("")
    assert entries_frozen(cfg)


def test_the_default_switch_lives_in_deploy_and_is_never_committed():
    assert AgentConfig().entry_freeze_path == "deploy/ENTRY_FREEZE"
    with open(os.path.join(ROOT, ".gitignore")) as fh:
        assert "deploy/ENTRY_FREEZE" in fh.read().split()


def test_status_never_says_entry_ready_while_frozen():
    """'No ENTRY-READY' is a restart condition; under the freeze the flag must
    not promise a trade that will not happen."""
    with open(os.path.join(ROOT, "deploy", "status.py")) as fh:
        src = fh.read()
    assert '"signal, but FROZEN" if rep["entries_frozen"]' in src
    assert 'line("entries", "FROZEN' in src
