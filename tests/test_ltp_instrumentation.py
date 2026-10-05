"""
The 2026-09-27 logging pass: five read-only additions, and one promise.

The promise is the part worth testing hardest: **nothing here changes what the
agent trades.** The z sampler runs inside the live agent's sleep loop, between
bars, holding the same broker that places orders. So its tests use a broker
that raises on anything but a read, and they check that state comes out
byte-identical. The refit additions run inside `refit()`, whose failure would
not kill the agent (the loop catches it) but would silently freeze every fit
at yesterday's values -- so `refit()` is run end to end here, not just its
helpers.

What the pass is for: a stop on 2026-09-26 jumped from z 2.90 to 5.38 inside
one hourly bar and nothing could say when it crossed 3.5; task 05 found window
and half-life collinear and asked for a fixed-window counterfactual; task 05's
question 4b needed rejected candidates' half-lives; and the scorer's MDD (3.1%)
and Sharpe (-0.06) could not be reproduced for want of hourly NAV.
"""

import copy
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import deploy.ltp_agent as agent                          # noqa: E402
from deploy.ltp_agent import (                            # noqa: E402
    AgentConfig, candidate_records, fixed_window_z, next_wake,
    sample_open_positions,
)
from deploy.status import GLANCE_HIDE, _tail_ledger, banked_mdd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


class ReadOnlyBroker:
    """Answers reads; any other attribute -- place, close, cancel, a session
    -- fails the test. `__getattr__` only fires for names not defined here, so
    this is an allow-list of exactly the reads the code under test may make."""

    def __init__(self, prices=None, nav=1000.0, klines=None, fail=False):
        self.prices, self.nav, self._klines, self.fail = prices or {}, nav, klines, fail
        self.mark_calls = 0

    def mark_price(self, symbol):
        self.mark_calls += 1
        if self.fail:
            raise agent.RapidXError("venue down")
        return self.prices[symbol]

    def equity_usdt(self):
        return self.nav

    def klines(self, symbol, interval, limit):
        return self._klines[symbol]

    def __getattr__(self, name):
        raise AssertionError(f"read-only code touched broker.{name}")


A, B = "BINANCE_PERP_1000SHIB_USDT", "BINANCE_PERP_DOGE_USDT"


def _held_pair(**kw):
    p = {"a": A, "b": B, "beta": 0.84, "mu": -3.18, "sigma": 0.005,
         "sigma_fixed": 0.004, "entry_mu": -3.18, "entry_sigma": 0.005,
         "entry_beta": 0.84, "side": -1, "hold": 5, "blocked": 0,
         "entry_z": 0.6, "exit_z": 0.0, "half_life": 13.0}
    p.update(kw)
    return p


def _prices_at(z, pair):
    """Leg prices that put the live spread at `z`."""
    lb = np.log(0.098)
    la = pair["mu"] + z * pair["sigma"] + pair["beta"] * lb
    return {A: float(np.exp(la)), B: 0.098}


# ------------------------------------------------------------ the sampler --

def test_a_flat_book_is_not_sampled_at_all(ledger_file):
    """No position, no reads: the sampler costs nothing on an idle book."""
    broker = ReadOnlyBroker()
    state = {"pairs": {f"{A}|{B}": _held_pair(side=0)}}
    assert sample_open_positions(broker, AgentConfig(), state) == 0
    assert broker.mark_calls == 0
    assert _records(ledger_file) == []


def test_a_sample_logs_z_three_ways_and_changes_nothing(ledger_file):
    pair = _held_pair()
    state = {"pairs": {f"{A}|{B}": pair}, "bar": 7}
    before = copy.deepcopy(state)
    broker = ReadOnlyBroker(prices=_prices_at(5.38, pair))

    assert sample_open_positions(broker, AgentConfig(), state) == 1
    rec, = _records(ledger_file, "z_sample")
    assert rec["z"] == pytest.approx(5.38)                  # the live frame
    assert rec["z_entry"] == pytest.approx(5.38)            # unchanged frame
    assert rec["z_fixed"] == pytest.approx(5.38 * 0.005 / 0.004)
    assert rec["pair"] == "1000SHIB/DOGE" and rec["side"] == -1
    assert rec["stop_z"] == 3.5
    # Past the stop, and it did NOTHING: no order (the broker would have
    # raised), no state change. Acting on a sample is `intrabar_stop`'s job
    # (2026-10-05, tests/test_ltp_intrabar_stop.py), never the sampler's.
    assert state == before
    assert _records(ledger_file, "stop") == []


def test_a_failed_read_costs_one_sample_never_the_loop(ledger_file):
    broker = ReadOnlyBroker(fail=True)
    state = {"pairs": {f"{A}|{B}": _held_pair()}}
    assert sample_open_positions(broker, AgentConfig(), state) == 0
    assert _records(ledger_file) == []


def test_samples_fall_on_the_five_minute_marks_and_never_near_the_bar():
    hour = 1_000_000 * 3600.0                 # an exact top of the hour
    deadline = hour + 3600 + 5                # the next bar, at :00:05
    wake, is_sample = next_wake(hour + 5 + 10, deadline, 300)   # 00:00:15
    assert is_sample and wake == hour + 300                     # 00:05:00
    wake, is_sample = next_wake(hour + 55 * 60, deadline, 300)  # 00:55:00
    # 01:00:00 is 5 s before the bar -- inside the 60 s guard -- so no sample:
    # sleep straight to the bar.
    assert (wake, is_sample) == (deadline, False)
    for now in np.arange(hour + 6, deadline, 17.0):
        w, s = next_wake(now, deadline, 300)
        assert w <= deadline and (not s or w <= deadline - 60)


def test_sampling_can_be_switched_off():
    assert next_wake(100.0, 3605.0, 0) == (3605.0, False)


def test_the_sleep_loop_still_derisks_on_urgent_news():
    """The loop was restructured to add samples. The critical-news path it
    existed for must still be there, and the deadline must be fixed before
    the first wait so no sample can push the bar back."""
    src = open(os.path.join(ROOT, "deploy", "ltp_agent.py")).read()
    loop = src[src.index("# Sleep to the top of the next hour"):]
    assert "stream.urgent.wait(timeout=timeout)" in loop
    assert "derisk(broker, cfg, state, stream.take_critical()" in loop
    assert loop.index("deadline = time.time()") < loop.index("while True:")
    assert "deadline =" not in loop[loop.index("while True:"):]


# ------------------------------------------------------- fixed-window z --

def test_fixed_window_z_uses_the_live_mean_and_the_fixed_sigma():
    assert fixed_window_z({"mu": 1.0, "sigma_fixed": 0.5}, 2.0) == 2.0
    assert fixed_window_z({"mu": 1.0}, 2.0) is None          # pre-deploy fit
    assert fixed_window_z({"mu": 1.0, "sigma_fixed": 0.0}, 2.0) is None


def test_every_decision_record_carries_the_counterfactual():
    src = open(os.path.join(ROOT, "deploy", "ltp_agent.py")).read()
    for event in ('ledger("enter"', 'ledger("stop"', 'ledger("exit"'):
        i = src.index(event)
        assert "z_fixed=fixed_window_z(pair, spread)" in src[i:i + 300], event


# ------------------------------------------------ refit, per candidate --

def _table(rows):
    base = dict(beta=0.8, adf_pvalue=0.01, hurst=0.3, crossings=50,
                beta_first_half=0.8, beta_second_half=0.8,
                passed=False, reject_reason="half-life out of band")
    return pd.DataFrame([{**base, **r} for r in rows])


def test_candidates_say_which_end_of_the_band_they_failed():
    t = _table([
        dict(a=A, b=B, half_life=3.0),                        # too fast
        dict(a=A, b=B, half_life=400.0),                      # trending
        dict(a=A, b=B, half_life=20.0, passed=True, reject_reason=""),
        dict(a=A, b=B, half_life=float("nan"), adf_pvalue=float("nan"),
             reject_reason="degenerate price series"),
    ])
    recs = candidate_records(t, AgentConfig())
    assert [r["band_side"] for r in recs] == ["below", "above", "in", None]
    assert recs[2]["passed"] is True and recs[2]["reason"] == ""
    assert recs[3]["half_life"] is None and recs[3]["adf_p"] is None
    json.dumps(recs, allow_nan=False)          # NaN would corrupt the ledger


def _panel(n=960, seed=3):
    """Every candidate symbol as an independent random walk, except
    1000SHIB/DOGE, built cointegrated with a ~15-bar half-life."""
    rng = np.random.default_rng(seed)
    syms = sorted({s for p in agent.CANDIDATES for s in p})
    logs = {s: np.log(10.0) + np.cumsum(rng.normal(0, 0.01, n)) for s in syms}
    phi = np.exp(-np.log(2) / 15.0)
    ou = np.zeros(n)
    for t in range(1, n):
        ou[t] = phi * ou[t - 1] + rng.normal(0, 0.01)
    logs[B] = np.log(0.098) + np.cumsum(rng.normal(0, 0.004, n))
    logs[A] = -3.18 + 0.84 * logs[B] + ou
    return {s: pd.DataFrame({"close": np.exp(v)}) for s, v in logs.items()}


def test_refit_end_to_end_writes_the_new_fields(ledger_file, tmp_path):
    cfg = AgentConfig(state_path=str(tmp_path / "s.json"),
                      hwm_path=str(tmp_path / "h.json"))
    broker = ReadOnlyBroker(klines=_panel())
    state = {"peak_equity": 1000.0, "halted": False, "pairs": {}, "bar": 0}

    agent.refit(broker, cfg, state)
    rec, = _records(ledger_file, "refit")
    assert len(rec["candidates"]) == rec["tested"] == 15
    assert {c["band_side"] for c in rec["candidates"]} <= {"below", "above",
                                                            "in", None}
    assert isinstance(rec["rejects"], dict)
    key = next(k for k in state["pairs"] if "1000SHIB" in k and "DOGE" in k)
    band = rec["bands"][key]
    for field in ("beta", "mu", "sigma", "sigma_window", "sigma_fixed"):
        assert band[field] is not None, field
    assert state["pairs"][key]["sigma_fixed"] > 0

    # Now HOLD that pair, on a beta the next refit will not reproduce, and
    # refit again: the live mean must be re-expressed on the entry beta.
    held = state["pairs"][key]
    held.update(side=-1, entry_beta=held["beta"] + 0.02,
                entry_mu=held["mu"], entry_sigma=held["sigma"])
    agent.refit(broker, cfg, state)
    after = state["pairs"][key]
    assert after["mu_entry_beta_basis"] == held["entry_beta"]
    assert after["mu_entry_beta"] != after["mu"]      # a different spread
    assert after["side"] == -1                         # trading state kept


# ------------------------------------------------------------ hourly NAV --

def test_every_good_bar_logs_nav_and_a_bad_read_does_not(ledger_file, tmp_path):
    cfg = AgentConfig(state_path=str(tmp_path / "s.json"),
                      hwm_path=str(tmp_path / "h.json"))
    state = {"peak_equity": 1013.16, "halted": False, "pairs": {}, "bar": 9}
    agent.trade_step(ReadOnlyBroker(nav=1004.74), cfg, state, dry=True)
    rec, = _records(ledger_file, "nav")
    assert rec["nav"] == 1004.74 and rec["peak"] == 1013.16 and rec["bar"] == 9
    assert rec["dd"] == pytest.approx(1 - 1004.74 / 1013.16)

    # A phantom zero must never enter the drawdown series.
    agent.trade_step(ReadOnlyBroker(nav=0.0), cfg, state, dry=True)
    assert len(_records(ledger_file, "nav")) == 1
    assert len(_records(ledger_file, "bad_read")) == 1


def test_banked_mdd_never_falls_on_recovery():
    """The whole point: current drawdown fell to 2.26% on 2026-09-21 while the
    scored figure sat at 2.88%. The banked number is a max, not a reading."""
    recs = [{"ts": "2026-09-28T00:00:05", "dd": 0.010},
            {"ts": "2026-09-28T01:00:05", "dd": 0.031},
            {"ts": "2026-09-28T02:00:05", "dd": 0.004}]      # recovered
    out = banked_mdd(recs)
    assert out["mdd_pct"] == 3.1 and out["n"] == 3
    assert out["since"] == "2026-09-28T00:00:05"
    assert banked_mdd([]) is None
    # A record without `dd` is rebuilt from nav and peak, not skipped.
    assert banked_mdd([{"ts": "x", "nav": 950.0, "peak": 1000.0}])["mdd_pct"] == 5.0


def test_the_glance_hides_data_records_but_still_counts_them(tmp_path):
    p = tmp_path / "l.jsonl"
    rows = ([{"event": "enter"}] + [{"event": "z_sample"}] * 30
            + [{"event": "nav"}] * 5)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    shown, tally = _tail_ledger(str(p), 8)
    assert [r["event"] for r in shown] == ["enter"]
    assert tally["z_sample"] == 30 and tally["nav"] == 5
    assert {"z_sample", "nav"} <= set(GLANCE_HIDE)
