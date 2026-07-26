"""
Tests for the reasoning-depth layer (deploy/ltp_analyst.py).

Two properties matter and are pinned here, because both are safety rather
than cosmetics: the analyst may only ever REDUCE risk (a "broken" regime can
veto an entry; nothing else it says can create or enlarge a position), and it
must fail open — no key, no SDK, a malformed reply, or an exhausted token
budget all degrade to "no analysis, no veto" so the systematic strategy keeps
trading rather than halting on an LLM problem.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy.ltp_analyst import StrategyAnalyst, _extract_json


# --- the veto may only reduce risk ------------------------------------------

def test_broken_regime_vetoes():
    veto = StrategyAnalyst.anomaly_veto(
        {"regime": "broken", "confidence": "high", "rationale": "monotonic 12h drift"})
    assert veto is not None
    assert "monotonic 12h drift" in veto


def test_normal_and_stressed_do_not_veto():
    # "stressed" is informational: it is logged, but it must NOT block trading,
    # or ordinary volatility would silently switch the strategy off.
    for regime in ("normal", "stressed"):
        assert StrategyAnalyst.anomaly_veto({"regime": regime,
                                             "rationale": "x"}) is None


def test_missing_or_junk_assessment_does_not_veto():
    for assessment in ({}, {"regime": None}, {"regime": "catastrophic"},
                       {"rationale": "no regime field"}):
        assert StrategyAnalyst.anomaly_veto(assessment) is None


# --- fail-open --------------------------------------------------------------

def _no_ai_env(monkeypatch):
    for var in ("LTP_AI_BASE_URL", "LTP_AI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LTP_COMPETITION_MODE", "1")


def test_assess_spread_fails_open_without_gateway(monkeypatch):
    _no_ai_env(monkeypatch)
    out = StrategyAnalyst().assess_spread(
        pair="ETC/KAS", z=-3.2, entry_z=3.0, exit_z=1.5, stop_z=3.5,
        half_life=18.0, beta=0.25, z_path=[-1.0, -2.0, -3.2],
        news_note="news sentinel: ETC=none, KAS=none", holding=False)
    assert out == {}
    assert StrategyAnalyst.anomaly_veto(out) is None      # and so cannot veto


def test_review_refit_fails_open_without_gateway(monkeypatch):
    _no_ai_env(monkeypatch)
    assert StrategyAnalyst().review_refit([], {}, []) == {}


def test_exhausted_budget_stops_calls(monkeypatch):
    """Above the spend ceiling the analyst goes quiet rather than burning the
    day's allocation out from under the news sentinel."""
    _no_ai_env(monkeypatch)
    analyst = StrategyAnalyst(max_daily_spend=8.0)
    monkeypatch.setattr(analyst, "spend_today", lambda: 9.5)
    assert analyst.within_budget() is False
    assert analyst.review_refit([], {}, []) == {}


def test_unreadable_budget_meter_proceeds(monkeypatch):
    """An unreadable meter must not silently disable analysis — the organizer
    caps the daily allocation regardless."""
    _no_ai_env(monkeypatch)
    analyst = StrategyAnalyst()
    monkeypatch.setattr(analyst, "spend_today", lambda: None)
    assert analyst.within_budget() is True


# --- defensive parsing (the gateway won't honour structured outputs) --------

def test_extract_json_handles_bare_fenced_and_prose():
    obj = '{"regime": "normal", "confidence": "high"}'
    assert _extract_json(obj)["regime"] == "normal"
    assert _extract_json(f"```json\n{obj}\n```")["regime"] == "normal"
    assert _extract_json(f"Here is my read:\n{obj}\nHope that helps.")[
        "confidence"] == "high"
    assert _extract_json("no json at all") is None
    assert _extract_json("") is None
