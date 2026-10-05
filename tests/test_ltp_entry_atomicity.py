"""
An entry is two legs or none.

2026-10-03 15:00: the agent entered 1000SHIB/DOGE short-spread. Leg a (a ~509
USDT 1000SHIB short) filled. Leg b was refused at preview --
`RCLI26005 automation maxTotalNotional exceeded` -- and the RapidXError
unwound the whole bar before the state recorded anything. The agent believed
it was flat; the venue held a naked memecoin short for an hour, until the next
bar's `reconcile_positions` found and closed it. It cost nothing that hour. A
5% move would have cost more than any Phase II stop.

The cause was the automation session's `maxTotalNotional`: a CUMULATIVE
budget of opening notional per 24h session, counted at each order's
`maxNotional` ceiling, with closes exempt -- not the cap on exposure the code
comment and the operator's consent text both describe. Inferred from that
day's 22 orders (it fits all of them; executed notional would not have
crossed 4000, the ceilings did), so the defence has two layers and both are
tested here: skip an entry the budget cannot hold both legs of, and unwind
anything that fails part-way regardless.
"""

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import deploy.ltp_agent as agent                                     # noqa: E402
from deploy.ltp_agent import AgentConfig, automation_max_total      # noqa: E402
from deploy.ltp_broker import RapidXBroker, RapidXError, RapidXResult  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A, B = "BINANCE_PERP_1000SHIB_USDT", "BINANCE_PERP_DOGE_USDT"
C, D = "BINANCE_PERP_ETH_USDT", "BINANCE_PERP_BTC_USDT"


def _refusal():
    return RapidXError(RapidXResult(False, "BLOCKED", "RCLI26005",
                                    "automation maxTotalNotional exceeded.",
                                    {}), "order place-preview")


# --------------------------------------------- the broker's budget model --

class ScriptedVenue(RapidXBroker):
    """The real RapidXBroker over a scripted CLI. The 'venue' enforces the
    budget on the rule inferred from 10-03 -- so these tests pin OUR
    accounting against that rule; the evidence for the rule is the ledger."""

    def __init__(self, cap):
        super().__init__()
        self.cap, self.venue_spent = cap, 0.0

    def _run(self, args, input_obj=None, write=False):
        ok = lambda data: RapidXResult(True, "OK", "", "", data)  # noqa: E731
        if args == ["automation", "start"]:
            self.venue_spent = 0.0
            return ok({"automationSessionId": "ras_test"})
        if args == ["order", "place-preview"]:
            mn = float(input_obj["maxNotional"])
            if self.venue_spent + mn > self.cap:
                return RapidXResult(False, "BLOCKED", "RCLI26005",
                                    "automation maxTotalNotional exceeded.", {})
            self.venue_spent += mn
            return ok({"previewId": "p", "confirmation": {"submitToken": "t"}})
        if args == ["order", "place"]:
            return ok({})
        if args == ["order", "query"]:
            return ok({"orderId": "1", "orderState": "FILLED"})
        raise AssertionError(f"unexpected CLI call {args}")

    def open(self, sym, mn):
        return self.place_market(sym, "SELL", "SHORT", 1.0, max_notional=mn,
                                 client_order_id="c")


def _start(v, cap="4000"):
    v.start_automation(["X"], max_per_order="1000", max_total=cap,
                       expires_s=86400, consent_text="operator's words")


def test_no_session_means_no_budget_to_check():
    """The deploy check calls this: a broker with no session answers None, so
    a dry run (or the old broker missing the method) is distinguishable."""
    assert RapidXBroker().budget_left() is None


def test_the_10_03_sequence_reproduces_on_the_budget_rule():
    """The day's own ceilings, from the ledger. From the ~10-02 19:00 session
    renewal: three entries, then 15:00's leg a fills and leg b is refused;
    18:00's leg a is refused outright; a new session takes the 19:00 entry."""
    v = ScriptedVenue(cap=4000.0)
    _start(v)
    for mn in (555.46, 479.48, 557.59, 481.31, 558.87, 489.26):  # 20:00 00:00 08:00
        v.open(A, mn)
    assert v.budget_left() == pytest.approx(4000 - 3121.97)
    v.open(A, 559.75)                                   # 15:00 leg a: fills
    assert v.budget_left() == pytest.approx(4000 - 3681.72)
    with pytest.raises(RapidXError, match="RCLI26005"):
        v.open(B, 490.14)                               # 15:00 leg b: refused
    # A refused preview spends nothing, on the venue or in our count.
    assert v.budget_left() == pytest.approx(4000 - 3681.72)
    with pytest.raises(RapidXError, match="RCLI26005"):
        v.open(A, 559.88)                               # 18:00 leg a: refused
    _start(v)                                           # 19:00: renewal
    assert v.budget_left() == 4000.0
    v.open(A, 559.88)
    v.open(B, 490.14)                                   # filled, as it was


def test_the_budget_follows_the_configured_total():
    v = ScriptedVenue(cap=12000.0)
    _start(v, cap="12000")
    assert v.budget_left() == 12000.0


# ------------------------------------------------ the cap, from the env --

def test_the_cap_defaults_to_the_original_4000():
    assert automation_max_total({}) == "4000"
    assert automation_max_total({"LTP_AUTOMATION_MAX_TOTAL": "  "}) == "4000"


def test_the_cap_reads_the_env_and_normalises_it():
    assert automation_max_total({"LTP_AUTOMATION_MAX_TOTAL": "12000"}) == "12000"
    assert automation_max_total({"LTP_AUTOMATION_MAX_TOTAL": "12000.0"}) == "12000"
    assert automation_max_total({"LTP_AUTOMATION_MAX_TOTAL": "8000.5"}) == "8000.5"


@pytest.mark.parametrize("bad", ["abc", "0", "-5", "nan", "inf"])
def test_a_bad_cap_refuses_to_start_rather_than_guess(bad):
    with pytest.raises(ValueError):
        automation_max_total({"LTP_AUTOMATION_MAX_TOTAL": bad})


def test_the_session_is_started_with_the_configured_cap():
    src = open(os.path.join(ROOT, "deploy", "ltp_agent.py")).read()
    i = src.index("sid = broker.start_automation(")
    assert "max_total=max_total" in src[i:i + 200]
    assert 'max_total="4000"' not in src, "the literal cap came back"


# -------------------------------------------------- trade_step, end to end --

class Venue:
    """Duck-typed broker for trade_step: scriptable refusals, a live-position
    set the closes act on, and a record of every order and its context."""

    def __init__(self, prices, nav=1000.0, budget=None, refuse=(),
                 close_fails=False):
        self.prices, self.nav, self._budget = prices, nav, budget
        self.refuse, self.close_fails = set(refuse), close_fails
        self.placed, self.closed, self.contexts = [], [], []
        self.live: set[str] = set()
        self.op_context: dict = {}

    def equity_usdt(self):
        return self.nav

    def mark_price(self, symbol):
        return self.prices[symbol]

    def round_qty(self, symbol, qty):
        return round(qty, 4)

    def meets_min_notional(self, symbol, qty, price):
        return True

    def budget_left(self):
        return self._budget

    def place_market(self, symbol, side, position_side, qty, max_notional,
                     client_order_id):
        self.contexts.append(("place", symbol, dict(self.op_context)))
        if symbol in self.refuse:
            raise _refusal()
        self.placed.append((symbol, side, round(max_notional, 2)))
        self.live.add(symbol)
        return {"orderState": "FILLED"}

    def close_position(self, symbol, position_side, max_notional):
        self.contexts.append(("close", symbol, dict(self.op_context)))
        if self.close_fails:
            raise RuntimeError("venue down")
        if symbol not in self.live:
            return None
        self.live.discard(symbol)
        self.closed.append(symbol)
        return {}


def _pair(a=A, b=B, **kw):
    p = {"a": a, "b": b, "beta": 0.875, "mu": -3.18, "sigma": 0.005,
         "entry_z": 0.6, "exit_z": 0.0, "half_life": 14.9, "dvol": 0.004,
         "side": 0, "hold": 0, "blocked": 0}
    p.update(kw)
    return p


def _prices(z, pair, lb=np.log(0.093)):
    la = pair["mu"] + z * pair["sigma"] + pair["beta"] * lb
    return {pair["a"]: float(np.exp(la)), pair["b"]: float(np.exp(lb))}


@pytest.fixture
def run(tmp_path, monkeypatch):
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(agent, "_LEDGER_PATH", str(ledger))
    cfg = AgentConfig(state_path=str(tmp_path / "s.json"),
                      hwm_path=str(tmp_path / "h.json"))

    def _run(venue, pairs):
        state = {"peak_equity": 1000.0, "halted": False, "bar": 9,
                 "pairs": pairs}
        agent.trade_step(venue, cfg, state, dry=False)
        recs = [json.loads(l) for l in ledger.read_text().splitlines()] \
            if ledger.exists() else []
        return state, recs
    return _run


def _events(recs):
    return [r["event"] for r in recs if r["event"] != "nav"]


def test_a_refused_hedge_leg_is_unwound_in_the_same_bar(run):
    """The 10-03 failure, replayed: leg a fills, leg b is refused. Leg a must
    be closed NOW -- not at the next bar's reconcile -- and the record must
    carry the venue's reason."""
    pair = _pair()
    v = Venue(_prices(0.8, pair), refuse={B})
    state, recs = run(v, {"k": pair})

    assert v.live == set(), "a leg of the pair is still open at the venue"
    assert v.closed == [A]
    assert _events(recs) == ["enter", "entry_unwound"]
    rec = recs[-1]
    assert rec["failed_leg"] == "b" and "RCLI26005" in rec["error"]
    assert rec["unwind"] == {A: "closed", B: "was_flat"}
    assert "naked" in rec["reasoning"]
    # Flat, and NOT blocked: the plumbing failed, not the spread.
    assert pair["side"] == 0 and pair["blocked"] == 0
    # The closes are attributed to the unwind decision in the operation log.
    closes = [c for c in v.contexts if c[0] == "close"]
    assert all(c[2]["decision"] == "entry_unwound" for c in closes)
    assert v.op_context == {}


def test_a_refused_first_leg_opens_nothing(run):
    """18:00 on 10-03: leg a refused. Nothing placed, nothing left open, and
    the reason is in the record instead of only the journal."""
    pair = _pair()
    v = Venue(_prices(0.95, pair), refuse={A})
    state, recs = run(v, {"k": pair})

    assert v.placed == [] and v.live == set()
    assert not any(c[0] == "place" and c[1] == B for c in v.contexts)
    assert _events(recs) == ["enter", "entry_failed"]
    assert recs[-1]["unwind"] == {A: "was_flat"}
    assert "RCLI26005" in recs[-1]["error"]
    assert pair["side"] == 0


def test_an_entry_the_budget_cannot_hold_is_skipped_before_any_order(run):
    """The first line of defence: with 878.03 left (10-03 15:00's position)
    and two legs to place, neither is placed and no `enter` is recorded."""
    pair = _pair()
    v = Venue(_prices(0.62, pair), budget=4000 - 3121.97)
    state, recs = run(v, {"k": pair})

    assert v.contexts == []
    assert _events(recs) == ["skip"]
    skip = recs[-1]
    assert skip["reason"] == "automation_budget"
    assert skip["need"] > skip["left"] == pytest.approx(878.03)
    # `need` is exactly the two ceilings place_entry would pass.
    g = min(AgentConfig().risk_per_pair * 1000.0 / pair["dvol"],
            AgentConfig().per_leg_cap_mult * 1000.0)
    assert skip["need"] == pytest.approx(round(1.1 * g, 2)
                                         + round(1.1 * pair["beta"] * g, 2))
    assert pair["side"] == 0


def test_an_entry_that_fits_the_budget_goes_ahead(run):
    pair = _pair()
    v = Venue(_prices(0.8, pair), budget=12000.0)
    state, recs = run(v, {"k": pair})
    assert [s for s, *_ in v.placed] == [A, B]
    assert pair["side"] == -1 and _events(recs) == ["enter"]


def test_one_pairs_failed_entry_no_longer_skips_another_pairs_stop(run):
    """Latent until a second pair is held: an exception in one pair's entry
    used to abort the whole bar, so every pair after it went unchecked --
    including a stop."""
    entering = _pair()
    held = _pair(a=C, b=D, beta=1.16, mu=-3.9, side=-1, hold=3,
                 entry_mu=-3.9, entry_sigma=0.005, entry_beta=1.16)
    prices = {**_prices(0.8, entering), **_prices(4.0, held, lb=np.log(62000))}
    v = Venue(prices, refuse={A})
    v.live |= {C, D}
    state, recs = run(v, {"enter_first": entering, "held": held})

    assert held["side"] == 0 and held["blocked"] == -1
    assert {C, D} <= set(v.closed)
    assert "stop" in _events(recs)


def test_an_unwind_that_fails_is_reported_not_raised(run):
    """If the venue will not close either, the record says so and the bar
    carries on; the next bar's reconcile is the backstop, as on 10-03."""
    pair = _pair()
    v = Venue(_prices(0.8, pair), refuse={B}, close_fails=True)
    state, recs = run(v, {"k": pair})
    rec = recs[-1]
    assert rec["event"] == "entry_unwound"
    assert rec["unwind"][A].startswith("FAILED")
    assert pair["side"] == 0          # state flat -> reconcile closes leg a


def test_venue_errors_reach_the_ledger_not_only_the_journal():
    """Two 10-03 `enter` decisions had no orders and no stated reason; the
    RCLI26005 text lived only in the systemd journal, which rotates."""
    src = open(os.path.join(ROOT, "deploy", "ltp_agent.py")).read()
    i = src.index("except RapidXError as exc:\n            log(f\"bar error")
    assert 'ledger("bar_error", error_type="RapidXError"' in src[i:i + 600]
