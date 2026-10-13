"""
x1.5, fixed through 2026-11-04 -- and the four limits it has to fit.

Decided at the week 10 review (2026-10-11/12) by the operator, on a stated
premise: **a variance choice, not a claim of edge.** The per-trip edge measured
t = 0.22 over 31 Phase II trips; under the reproduced scorer, x1.5 moved the
simulated chance of a top-3 finish ~20% -> ~27% and of finishing 12th or worse
~29% -> ~35%, median unchanged (WEEKLY_REVIEW.md, week 10).

The decision had a trap in it, found on 2026-10-08: `risk_per_pair` was not
what sized trades. `per_leg_cap_mult` (0.5 x NAV) had bound every entry since
10-02, so raising the risk budget alone would have changed nothing. And a
second, found while building: each leg goes to the venue with a ceiling of
1.1 x its notional, the hedge leg is |beta| x the first, and the automation
session refuses any order over 1000 -- so at 0.75 x NAV a pair with |beta|
above ~1.2 (ETH/BTC has run 1.16-1.20) would have been refused on every entry.
These tests pin all of it, so the next change to one limit fails here until
someone has looked at the others.
"""

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import deploy.ltp_agent as agent                                     # noqa: E402
from deploy.ltp_agent import AUTOMATION_MAX_PER_ORDER, AgentConfig  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A, B = "BINANCE_PERP_1000SHIB_USDT", "BINANCE_PERP_DOGE_USDT"
C, D = "BINANCE_PERP_ETH_USDT", "BINANCE_PERP_BTC_USDT"


def test_the_decision_is_what_the_config_says():
    """x1.5 is two numbers moving together. Changing either is a new decision:
    edit this test, LTP_STRATEGY.md and the review log in the same commit."""
    cfg = AgentConfig()
    assert cfg.risk_per_pair == 0.003          # 0.002 until 2026-10-12
    assert cfg.per_leg_cap_mult == 0.75        # 0.5 until 2026-10-12
    # ...and nothing else moved with them.
    assert cfg.max_gross_mult == 2.0
    assert cfg.dd_halt == 0.12
    assert cfg.stop_z == 3.5


def test_the_session_is_opened_with_the_same_per_order_cap_the_clamp_uses():
    src = open(os.path.join(ROOT, "deploy", "ltp_agent.py")).read()
    assert "max_per_order=str(int(AUTOMATION_MAX_PER_ORDER))" in src
    assert 'max_per_order="1000"' not in src, "a second copy of the cap came back"
    assert AUTOMATION_MAX_PER_ORDER == 1000.0


# ------------------------------------------------- trade_step, end to end --

class Venue:
    def __init__(self, prices, nav):
        self.prices, self.nav = prices, nav
        self.placed: list[tuple[str, float]] = []
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
        self.placed.append((symbol, round(max_notional, 2)))
        return {"orderState": "FILLED"}

    def close_position(self, *a, **k):
        raise AssertionError("nothing here should close")


def _pair(a=A, b=B, beta=0.875, dvol=0.002, mu=-3.18):
    return {"a": a, "b": b, "beta": beta, "mu": mu, "sigma": 0.005,
            "entry_z": 0.6, "exit_z": 0.0, "half_life": 15.0, "dvol": dvol,
            "side": 0, "hold": 0, "blocked": 0}


def _prices(z, pair, lb):
    la = pair["mu"] + z * pair["sigma"] + pair["beta"] * lb
    return {pair["a"]: float(np.exp(la)), pair["b"]: float(np.exp(lb))}


@pytest.fixture
def step(tmp_path, monkeypatch):
    ledger = tmp_path / "l.jsonl"
    monkeypatch.setattr(agent, "_LEDGER_PATH", str(ledger))
    cfg = AgentConfig(state_path=str(tmp_path / "s.json"),
                      hwm_path=str(tmp_path / "h.json"))

    def _run(venue, pairs):
        state = {"peak_equity": 1020.95, "halted": False, "bar": 1,
                 "pairs": pairs}
        agent.trade_step(venue, cfg, state, dry=False)
        return [json.loads(l) for l in ledger.read_text().splitlines()]
    return _run


def _enter(recs):
    return [r for r in recs if r["event"] == "enter"]


def test_a_cap_bound_pair_now_takes_three_quarters_of_nav_per_leg(step):
    """The 10-02 -> 10-07 regime: the vol target wants more than the cap, so the
    cap decides -- 0.75 x NAV now, against 0.5 before."""
    pair = _pair(dvol=0.002)                 # 0.003 * 1005 / 0.002 >> cap
    v = Venue(_prices(0.8, pair, np.log(0.093)), nav=1005.15)
    rec, = _enter(step(v, {"k": pair}))
    assert rec["g"] == pytest.approx(0.75 * 1005.15)
    # Both ceilings fit the per-order cap with room to spare at this beta.
    assert all(mn <= AUTOMATION_MAX_PER_ORDER for _, mn in v.placed)


def test_a_vol_bound_pair_is_exactly_one_and_a_half_times_its_old_size(step):
    """ALGO/HBAR on 10-08 entered at g 229.85 under the old budget -- the vol
    target, not the cap. The same pair is now 1.5 x that."""
    pair = _pair(dvol=0.0088)
    v = Venue(_prices(0.8, pair, np.log(0.093)), nav=1005.15)
    rec, = _enter(step(v, {"k": pair}))
    assert rec["g"] == pytest.approx(0.003 * 1005.15 / 0.0088)
    assert rec["g"] == pytest.approx(1.5 * 0.002 * 1005.15 / 0.0088)


@pytest.mark.parametrize("beta", [1.16, 1.2, 1.6, 2.5])
def test_a_high_beta_hedge_leg_is_shrunk_to_fit_not_refused(step, beta):
    """Without the clamp the hedge leg's ceiling is 1.1 x beta x 0.75 x NAV:
    ~995 at beta 1.2, 1,327 at 1.6 -- refused, unwound, every bar."""
    # mu chosen so leg a trades near 3,000 whatever the beta (a test fixture
    # choice: an unrealistic price would round the quantity to zero instead).
    mu = np.log(3000.0) - beta * np.log(62000.0)
    pair = _pair(a=C, b=D, beta=beta, dvol=0.002, mu=mu)
    v = Venue(_prices(0.8, pair, np.log(62000.0)), nav=1005.15)
    rec, = _enter(step(v, {"k": pair}))
    assert [s for s, _ in v.placed] == [C, D]
    assert all(mn <= AUTOMATION_MAX_PER_ORDER for _, mn in v.placed)
    assert rec["g"] <= 0.75 * 1005.15


def test_one_pair_at_a_time_a_second_signal_is_a_logged_gross_cap_skip(step):
    """The stated cost of x1.5: a cap-bound pair's gross is ~1.4 x NAV, so a
    second entry would breach the 2 x NAV cap and is skipped -- in the ledger,
    not in silence."""
    first = _pair(dvol=0.002)
    second = _pair(a="BINANCE_PERP_SOL_USDT", b="BINANCE_PERP_AVAX_USDT",
                   beta=0.9, dvol=0.002, mu=1.9)
    prices = {**_prices(0.8, first, np.log(0.093)),
              **_prices(0.8, second, np.log(30.0))}
    v = Venue(prices, nav=1005.15)
    recs = step(v, {"first": first, "second": second})
    assert [r["pair"] for r in _enter(recs)] == ["1000SHIB/DOGE"]
    skip, = [r for r in recs if r["event"] == "skip"]
    assert skip["reason"] == "gross_cap" and skip["pair"] == "SOL/AVAX"
    assert first["side"] == -1 and second["side"] == 0
