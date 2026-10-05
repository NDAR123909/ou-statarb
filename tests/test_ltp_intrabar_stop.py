"""
The intra-bar stop: the hourly stop's own rule, checked every five minutes.

Six Phase II stops overshot the 3.5 band waiting for the top of the hour --
about 8.5 USDT in all, most of it on 09-26 (z 2.90 -> 5.38 inside one bar) and
09-17 (2.82 -> 4.13). The monitor that would have caught them was dropped on
2026-09-13 for want of evidence; the week 9 review (2026-10-05) reversed that
on two changed facts: top 3 became the goal, and the `z_sample` records
deployed 09-29 make every firing auditable after the fact.

What these tests hold it to, because it is a new code path that closes live
positions:
  - it fires ONLY on `stop_crossed` -- the very function the hourly bar calls
    -- so it is the same rule, sooner, and forbids no entries;
  - only on the side held, never on a favourable move, never when flat,
    halted or switched off;
  - it does exactly what the hourly stop does: the same record (tagged with
    its trigger), both legs closed, the side blocked (invariant 4);
  - it acts on the reading the sampler logged, with no second price read;
  - the sampler itself still never acts (its 09-27 test is untouched);
  - a failed close is contained, and the bar re-checks.
"""

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import deploy.ltp_agent as agent                                 # noqa: E402
from deploy.ltp_agent import (                                   # noqa: E402
    AgentConfig, intrabar_stop, sample_open_positions, stop_crossed,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A, B = "BINANCE_PERP_1000SHIB_USDT", "BINANCE_PERP_DOGE_USDT"
KEY = f"{A}|{B}"


@pytest.fixture
def ledger_file(tmp_path, monkeypatch):
    p = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(agent, "_LEDGER_PATH", str(p))
    return p


def _records(p, event=None):
    if not p.exists():
        return []
    rows = [json.loads(l) for l in p.read_text().splitlines()]
    return [r for r in rows if event is None or r["event"] == event]


class Venue:
    """Reads, plus closes. Opening anything fails the test: this path may
    only ever reduce risk."""

    def __init__(self, prices=None, nav=1000.0, close_fails=False):
        self.prices, self.nav, self.close_fails = prices or {}, nav, close_fails
        self.mark_calls, self.closed, self.contexts = 0, [], []
        self.op_context: dict = {}

    def mark_price(self, symbol):
        self.mark_calls += 1
        return self.prices[symbol]

    def equity_usdt(self):
        return self.nav

    def close_position(self, symbol, position_side, max_notional):
        self.contexts.append((symbol, dict(self.op_context), max_notional))
        if self.close_fails:
            raise RuntimeError("venue down")
        self.closed.append(symbol)
        return {}

    def place_market(self, *a, **k):
        raise AssertionError("the intra-bar path opened a position")


def _pair(**kw):
    p = {"a": A, "b": B, "beta": 0.84, "mu": -3.18, "sigma": 0.005,
         "sigma_fixed": 0.004, "entry_mu": -3.18, "entry_sigma": 0.005,
         "entry_beta": 0.84, "side": -1, "hold": 5, "blocked": 0,
         "entry_z": 0.6, "exit_z": 0.0, "half_life": 13.0}
    p.update(kw)
    return p


def _prices_at(z, pair):
    lb = np.log(0.098)
    la = pair["mu"] + z * pair["sigma"] + pair["beta"] * lb
    return {A: float(np.exp(la)), B: 0.098}


def _tick(z, cfg=None, halted=False, close_fails=False, nav=1000.0, **kw):
    """One sample wake as the loop runs it: sample, then the stop."""
    cfg = cfg or AgentConfig()
    pair = _pair(**kw)
    state = {"pairs": {KEY: pair}, "halted": halted, "peak_equity": 1020.95}
    venue = Venue(_prices_at(z, pair), nav=nav, close_fails=close_fails)
    readings: dict = {}
    sample_open_positions(venue, cfg, state, readings)
    fired = intrabar_stop(venue, cfg, state, readings, dry=False)
    return fired, pair, venue


# ------------------------------------------------------------ the rule --

@pytest.mark.parametrize("side", [-1, +1])
@pytest.mark.parametrize("z", [-5.38, -3.51, -3.5, -2.0, 0.0, 2.0, 3.5, 3.51, 5.38])
def test_the_rule_is_the_hourly_stops_rule_verbatim(side, z):
    """`stop_crossed` replaced this exact expression in trade_step; the two
    must agree everywhere, boundaries included (3.5 itself does not fire)."""
    old = (side > 0 and z < -3.5) or (side < 0 and z > 3.5)
    assert stop_crossed(side, z, 3.5) == old


def test_the_hourly_bar_and_the_sample_call_the_same_function():
    src = open(os.path.join(ROOT, "deploy", "ltp_agent.py")).read()
    step = src[src.index("def trade_step("):src.index("def main(")]
    assert "stopped = stop_crossed(side, z, cfg.stop_z)" in step
    assert 'trigger="bar"' in step
    ib = src[src.index("def intrabar_stop("):src.index("def flatten_everything(")]
    assert "stop_crossed(" in ib and 'trigger="intrabar"' in ib


# ------------------------------------------------------ when it fires --

def test_a_short_spread_past_the_stop_is_closed_between_bars(ledger_file):
    """09-26's shape: a short spread at +5.38 mid-hour."""
    fired, pair, venue = _tick(5.38)
    assert fired == 1
    assert venue.closed == [A, B]
    assert pair["side"] == 0 and pair["blocked"] == -1     # short side shut
    stop, = _records(ledger_file, "stop")
    assert stop["trigger"] == "intrabar"
    assert stop["z"] == pytest.approx(5.38)
    assert stop["z_fixed"] == pytest.approx(5.38 * 0.005 / 0.004)
    assert "five-minute reading" in stop["reasoning"]
    assert "z_in_entry_coords" in stop                      # the frame, as hourly
    # The operations chain back to a `stop` decision, like the hourly one.
    assert all(c[1]["decision"] == "stop" for c in venue.contexts)


def test_a_long_spread_past_the_stop_is_closed_and_blocks_long(ledger_file):
    fired, pair, venue = _tick(-3.61, side=+1)
    assert fired == 1 and pair["blocked"] == +1


@pytest.mark.parametrize("z", [3.49, 2.9, 0.0])
def test_inside_the_stop_nothing_happens(ledger_file, z):
    # (z = 3.5 exactly is pinned on `stop_crossed` itself above: rebuilding a
    # spread from prices returns 3.5000000001, which says nothing about code.)
    fired, pair, venue = _tick(z)
    assert fired == 0 and venue.closed == [] and pair["side"] == -1
    assert _records(ledger_file, "stop") == []


def test_a_favourable_move_is_not_a_stop(ledger_file):
    """A short spread at z -4 is deep in profit. Taking profit is the bar's
    job (the exit band); this path only ever cuts losses."""
    fired, pair, venue = _tick(-4.0)
    assert fired == 0 and pair["side"] == -1
    fired, pair, venue = _tick(+4.0, side=+1)
    assert fired == 0 and pair["side"] == +1


def test_halted_flat_or_switched_off_it_does_nothing(ledger_file):
    assert _tick(5.38, halted=True)[0] == 0
    assert _tick(5.38, cfg=AgentConfig(intrabar_stop=False))[0] == 0
    fired, pair, venue = _tick(5.38, side=0)
    assert fired == 0 and venue.mark_calls == 0             # flat: no reads


def test_it_acts_on_the_logged_reading_without_reading_again(ledger_file):
    fired, pair, venue = _tick(4.13)
    assert venue.mark_calls == 2                            # the sample's two
    sample, = _records(ledger_file, "z_sample")
    stop, = _records(ledger_file, "stop")
    assert stop["z"] == sample["z"]
    assert stop["price_a"] == sample["price_a"]


def test_a_reading_for_the_other_side_is_ignored(ledger_file):
    """Defensive: the stop acts only if the pair is still held on the side
    the sample measured."""
    pair = _pair()
    state = {"pairs": {KEY: pair}, "halted": False, "peak_equity": 1000.0}
    readings = {KEY: {"z": 5.0, "spread": 0.0, "frame": {}, "price_a": 1.0,
                      "price_b": 1.0, "side": +1}}
    assert intrabar_stop(Venue(), AgentConfig(), state, readings, False) == 0


# ------------------------------------------------------ when it fails --

def test_a_failed_close_is_contained_and_left_for_the_bar(ledger_file):
    """leg_close clears `side` only once both legs are closed, so a failure
    leaves the position marked held -- and the hourly bar stops it again."""
    fired, pair, venue = _tick(5.38, close_fails=True)
    assert fired == 0
    assert pair["side"] == -1 and pair["blocked"] == 0


def test_a_bad_equity_read_falls_back_to_the_peak(ledger_file):
    fired, pair, venue = _tick(5.38, nav=0.0)
    assert fired == 1
    assert all(c[2] == pytest.approx(2 * 1020.95) for c in venue.contexts)


# --------------------------------------- the sampler and the loop --

def test_the_sampler_alone_still_never_acts(ledger_file):
    """Its 2026-09-27 contract. Filling `readings` is the only new thing."""
    pair = _pair()
    state = {"pairs": {KEY: pair}}
    readings: dict = {}
    venue = Venue(_prices_at(5.38, pair))
    assert sample_open_positions(venue, AgentConfig(), state, readings) == 1
    assert venue.closed == [] and pair["side"] == -1
    assert readings[KEY]["z"] == pytest.approx(5.38)
    assert readings[KEY]["side"] == -1


def test_the_loop_samples_then_stops_and_saves_only_when_it_fired():
    src = open(os.path.join(ROOT, "deploy", "ltp_agent.py")).read()
    loop = src[src.index("sample_s = 60.0 * cfg.z_sample_minutes"):]
    i = loop.index("sample_open_positions(broker, cfg, state, readings)")
    j = loop.index("if intrabar_stop(broker, cfg, state, readings,")
    assert i < j < loop.index("save_state(cfg.state_path, state)", j)
    # ...inside the same maintenance guard the samples already obey.
    guard = loop.index('!= "active":')
    assert guard < i


def test_the_hourly_stop_still_fires_and_says_so(tmp_path, monkeypatch):
    """The hourly path now goes through `stop_position`; same behaviour,
    plus `trigger: "bar"`."""
    ledger = tmp_path / "l.jsonl"
    monkeypatch.setattr(agent, "_LEDGER_PATH", str(ledger))
    cfg = AgentConfig(state_path=str(tmp_path / "s.json"),
                      hwm_path=str(tmp_path / "h.json"))
    pair = _pair(dvol=0.004)
    state = {"pairs": {KEY: pair}, "halted": False, "peak_equity": 1000.0,
             "bar": 3}
    venue = Venue(_prices_at(4.13, pair))
    agent.trade_step(venue, cfg, state, dry=False)
    stop, = _records(ledger, "stop")
    assert stop["trigger"] == "bar" and stop["hold_bars"] == 6
    assert venue.closed == [A, B]
    assert pair["side"] == 0 and pair["blocked"] == -1
