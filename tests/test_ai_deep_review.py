"""
Guards on the deep-review pass.

It exists for two reasons at once, and the tests care about the first: the
analysis must be real. The live agent only ever assesses pairs it is holding,
so the fourteen candidates rejected at each refit get no individual review --
that is the gap. The second reason is a deadline (the organizer requires AI
spend above 1 USD or the team is disqualified), and a script written under that
pressure is exactly the kind that quietly becomes token-burning. These pin the
properties that keep it from becoming that.
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.ai_deep_review import (ELIMINATION_FLOOR, EQUITY_AT_REVIEW,  # noqa: E402
                                   FOLLOWUPS, KILL_SWITCH, PHASE_I_END,
                                   SYSTEM, constraint_prompt, days_left,
                                   strategy_prompts)


def test_the_reviewer_is_told_to_attack_not_approve():
    """A reviewer that manufactures agreement produces tokens and no
    information, which is the failure mode this whole script risks."""
    low = SYSTEM.lower()
    assert "not here to approve" in low
    assert "argue against" in low
    # ...and equally must not be pushed into manufacturing objections.
    assert "manufactures objections" in low
    assert "cite them" in low


def test_every_strategy_prompt_states_a_conclusion_and_asks_for_attack():
    """Each call has to carry a falsifiable claim of ours. A prompt that just
    says 'discuss the strategy' is padding wearing a question mark."""
    prompts = dict(strategy_prompts())
    assert set(prompts) == {"stop_geometry", "entry_band", "regime", "mu_drift"}
    for topic, p in prompts.items():
        assert "CONCLUSION UNDER REVIEW" in p, topic
        assert any(k in p for k in ("Attack this", "Is that right",
                                    "Which effect dominates", "Is waiting right")), topic


def test_prompts_carry_the_real_measured_numbers():
    """The model can only find our errors if it is given what we measured. If
    these drift out of the prompt the review degrades to opinion."""
    p = strategy_prompts()[0][1]
    for fact in ("1.75 bps",          # the measured fee
                 "0.57 bps",          # measured slippage
                 "+0.385",            # funding, net received
                 "3.7%",              # banked max drawdown
                 "9.30 to 5.66",      # the Sharpe collapse
                 "-10.67",            # total overshoot cost
                 "median hold 2.0h"):
        assert fact in p, fact


def test_the_stop_prompt_supplies_the_evidence_against_our_own_position():
    """We concluded the intra-bar monitor is worth building. The prompt has to
    hand over the strongest counter-arguments, or the review is theatre."""
    p = dict(strategy_prompts())["stop_geometry"]
    assert "4 of 5 stops were followed" in p       # stopping cost the recovery
    assert "noise filter" in p                     # monitoring adds stop-outs
    assert "already banked at 3.7%" in p           # MDD protection is spent


def test_reviews_are_written_to_the_ledger_with_their_full_text():
    """Track A correlates logged reasoning against trading decisions. A review
    that only prints to a terminal cannot be audited and did not happen."""
    import inspect
    import deploy.ai_deep_review as m
    src = inspect.getsource(m)
    i = src.index('ledger("ai_deep_review"')
    call = src[i:i + 220]
    for field in ("topic=", "model=", "review=text"):
        assert field in call, field


def test_the_constraint_prompt_does_not_confuse_the_two_floors():
    """The first pass told the reviewer it had "roughly 100 USDT of drawdown
    headroom above the elimination floor". That 100 is the distance to our own
    kill switch; the floor is more than twice as far. Every highest-EV answer
    in that pass was reasoning from half the real risk budget, and two
    reviewers smelled it without being able to see it. Pinned, not trusted.
    """
    p = constraint_prompt(date(2026, 8, 12))
    assert "{:.2f}".format(EQUITY_AT_REVIEW - ELIMINATION_FLOOR) in p
    assert "{:.2f}".format(EQUITY_AT_REVIEW - KILL_SWITCH) in p
    # The kill switch has to be labelled as our choice, or the reviewer reads
    # the nearer number as the one that ends the competition -- which is
    # exactly the error being fixed.
    assert "self-imposed" in p
    # And the two must stay distinguishable: our halt fires first, by design.
    assert ELIMINATION_FLOOR < KILL_SWITCH < EQUITY_AT_REVIEW
    # The wrong figure must not survive anywhere in the asked prompts.
    assert not any("100 USDT of drawdown headroom" in f for f in FOLLOWUPS)


def test_days_remaining_is_derived_rather_than_typed():
    """"Nine days remain" was written into the prompt on 2026-08-12 and would
    have been silently wrong on the 13th. Three tests rotted on the calendar in
    week 3 and failed loudly; a prompt rots in silence, so derive it."""
    assert days_left(date(2026, 8, 12)) == 9
    assert days_left(date(2026, 8, 20)) == 1
    assert days_left(PHASE_I_END) == 0
    assert days_left(date(2026, 9, 1)) == 0          # never negative
    assert "9 days remain" in constraint_prompt(date(2026, 8, 12))


def test_it_places_no_orders_and_touches_no_agent_state():
    """Read-only with respect to trading, under time pressure, is the whole
    safety argument for running this on a live competition account."""
    import inspect
    import deploy.ai_deep_review as m
    src = inspect.getsource(m)
    # Match invocations, not prose -- the module docstring says the words
    # "no automation session" and a substring check would trip on its own
    # promise.
    for forbidden in ("place_market(", "close_position(", "cancel_all(",
                      "save_state(", "flatten_everything(",
                      "automation_session", "op_context"):
        assert forbidden not in src, forbidden
    # The only write it is permitted is the ledger.
    assert src.count("open(") == 0, "writes a file directly"
