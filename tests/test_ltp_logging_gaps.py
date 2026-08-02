"""
Every path that moves money or changes risk must record what it did.

Four instances of one bug class surfaced on 2026-08-02, all in the same shape:
the entry path is well instrumented and everything else is thin. These are
behavioural contracts, not style preferences -- Track A is scored on a
Reasoning Audit that correlates logged decisions against executed orders, so a
control that acts silently is indistinguishable from one that never fired.

  * a refit-drop close wrote NO ledger event, so two orders reached the venue
    with no decision behind them and no reasoning for the exit;
  * the news sentinel's size_mult halved a position -- on the single worst
    trade of the competition -- leaving only a journal line;
  * close_position emitted neither the executed price nor the quantity, so the
    ledger could not say what any exit was done at.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "deploy", "ltp_agent.py")
BROKER = os.path.join(ROOT, "deploy", "ltp_broker.py")


def _src(path):
    with open(path) as fh:
        return fh.read()


def test_refit_drop_logs_a_decision_before_it_closes():
    src = _src(AGENT)
    i = src.find('pair.get("flatten")')
    assert i != -1, "the refit-drop branch is gone"
    branch = src[i:i + 1800]
    assert 'ledger("refit_drop"' in branch, (
        "a refit-drop close writes no decision event, so its orders appear in "
        "the audit with nothing behind them")
    assert "reasoning=" in branch, "refit_drop must explain why it exited"
    assert 'decision="refit_drop"' in branch, (
        "the operations must chain to the decision that caused them")
    # The ledger call has to come BEFORE the close, so a failed close still
    # leaves a record of the intent.
    assert branch.index('ledger("refit_drop"') < branch.index("leg_close("), (
        "log the decision before acting on it")


def test_a_news_size_reduction_is_recorded_in_the_ledger():
    src = _src(AGENT)
    assert 'ledger("size_reduced"' in src, (
        "size_mult reduces risk without leaving a ledger trace; a risk "
        "control that acts silently cannot be audited")
    i = src.find('ledger("size_reduced"')
    call = src[i:i + 1200]
    for field in ("mult=", "g_before=", "g_after=", "reasoning="):
        assert field in call, f"size_reduced is missing {field}"
    # And the entry row itself must carry it, so the correlation is
    # programmatic rather than a prose read.
    j = src.find('ledger("enter"')
    assert "size_mult=size_mult" in src[j:j + 900], (
        "the enter record reports a post-multiplier `g` with no indication "
        "the size was reduced")


def test_close_position_emits_the_outcome_not_just_an_acknowledgement():
    src = _src(BROKER)
    i = src.find('self._emit("close"')
    while i != -1:
        chunk = src[i:i + 700]
        if "result=" in chunk and "residual_qty" in chunk:
            break                       # the readback emit, not the error ones
        i = src.find('self._emit("close"', i + 1)
    assert i != -1, "the close readback emit is gone"
    chunk = src[i:i + 700]
    for field in ("executed_price=", "executed_qty=", "order_id="):
        assert field in chunk, (
            f"close operations omit {field}, so the ledger cannot say what an "
            f"exit was done at -- place_market emits it and close must too")


def test_place_and_close_agree_on_their_outcome_fields():
    """The asymmetry between the two emitters is what caused the gap."""
    src = _src(BROKER)
    place = src[src.find('self._emit("place"'):][:600]
    for field in ("executed_price=", "executed_qty=", "order_id="):
        assert field in place, f"place_market lost {field}"


def test_the_close_response_shape_is_recorded_when_a_field_is_missing():
    """The venue documents none of its field names and its CSV export is
    broken, so a miss must leave enough behind to diagnose from the ledger
    rather than from another live probing session."""
    src = _src(BROKER)
    assert "response_keys" in src, (
        "when the close response yields no order id or price, record its keys")
