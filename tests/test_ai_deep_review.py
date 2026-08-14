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

import json
import os
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.ai_deep_review import (AI_SPEND_FLOOR, ANGLES,  # noqa: E402
                                   CONSTRAINT_INDEX, DAILY_TARGET,
                                   ELIMINATION_FLOOR, EQUITY_AS_OF,
                                   EQUITY_AT_REVIEW, FOLLOWUPS, KILL_SWITCH,
                                   PHASE_I_END, SYSTEM, TOPUP_BELOW,
                                   FLOOR_GRACE_H, SPEND_CEILING,
                                   _duration_hours, constraint_prompt,
                                   days_left, floor_state, followups,
                                   ledger_prompts, over_ceiling,
                                   period_age_hours, record_facts,
                                   recent_events, strategy_prompts)


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
    # ...and when the live snapshot is unavailable it must SAY those figures
    # are dated rather than presenting them as current.
    assert "treat them as dated" in p


def test_the_record_block_is_measured_when_a_snapshot_exists():
    """The briefing used to hardcode "13 round trips, median hold 2.0h". By
    2026-08-13 the median hold was 23.0h and refit-drops had gone from ~10% of
    closes to 60%, so the reviewer was reasoning about a strategy that had
    stopped behaving that way. Derived now."""
    facts = {"as_of": "2026-08-13", "funding": 0.337, "summary": {
        "round_trips": 5, "gross_pnl": 0.4136, "fees_paid": 1.5165,
        "net_pnl": -1.1029, "win_rate": 0.4, "worst": -5.6092,
        "median_hold_h": 23.02, "measured_fee_bps_per_side": 1.748,
        "slippage_bps_mean": 0.91,
        "exit_reasons": {"refit_drop": 3, "reverted": 1, "stop": 1}}}
    p = strategy_prompts(facts=facts)[0][1]
    assert "5 completed round trips" in p
    assert "3 refit_drop" in p                  # the mix, most common first
    assert "23.0h" in p
    assert "2026-08-13" in p
    # The stale fallback must be gone entirely, not merely appended to.
    assert "median hold 2.0h" not in p
    # Fees exceeding gross is the kind of thing a reviewer derives late or not
    # at all, so the briefing states it outright.
    assert "paid more to trade than the trades earned" in p


def test_record_facts_survives_a_missing_or_junk_snapshot(tmp_path):
    """A corrupt snapshot must degrade the briefing to the labelled fallback,
    never take the daily pass down -- that pass is what clears the floor."""
    assert record_facts(tmp_path) is None                      # none present
    (tmp_path / "track_record").mkdir()
    (tmp_path / "track_record" / "fills_2026-08-13.json").write_text("{oops")
    assert record_facts(tmp_path) is None                      # unparseable
    (tmp_path / "track_record" / "fills_2026-08-14.json").write_text(
        json.dumps({"summary": {"round_trips": 0}}))
    assert record_facts(tmp_path) is None                      # empty window


def test_the_review_layer_cannot_starve_the_layers_that_gate_trades():
    """The agent's own news and spread assessments share this budget, and if
    they go dark the news gate fails OPEN -- entries stop being screened. An
    advisory layer must never be able to cause that."""
    assert DAILY_TARGET < SPEND_CEILING < 10.0     # 10.00/day is the budget
    assert SPEND_CEILING <= 8.0                    # >= 2.00 left for the agent
    assert over_ceiling(SPEND_CEILING) is True
    assert over_ceiling(SPEND_CEILING - 0.01) is False
    # An unreadable meter must NOT stop the run: missing the floor is
    # disqualification, overspending only darkens a gate that fails open.
    assert over_ceiling(None) is False
    # And the ceiling has to be enforced where the target is, or --target
    # simply walks past it.
    import inspect
    import deploy.ai_deep_review as m
    src = inspect.getsource(m.main)
    assert src.count("over_ceiling(") >= 2, "ceiling not checked in the loop"


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


def test_the_risk_budget_is_read_live_rather_than_hardcoded():
    """EQUITY_AT_REVIEW was written on 2026-08-09 and equity was 1016.66 four
    days later. The constant survives only as a labelled fallback; the live
    reading is what the reviewer should normally be given."""
    live = constraint_prompt(date(2026, 8, 13), equity=1016.66)
    assert "1016.66" in live
    assert "216.66" in live                    # headroom above the 800 floor
    assert "reading of" not in live            # not labelled stale when live

    stale = constraint_prompt(date(2026, 8, 13))
    assert f"{EQUITY_AT_REVIEW:.2f}" in stale
    # A fallback the reviewer cannot tell is a fallback is worse than no
    # number, so it has to announce its own date.
    assert EQUITY_AS_OF in stale and "unreadable" in stale


def test_followups_substitute_the_live_budget_into_the_right_prompt():
    """Counting to the constraint prompt by index breaks the moment a question
    is inserted above it, and it would break silently."""
    assert FOLLOWUPS[CONSTRAINT_INDEX] == constraint_prompt()
    turns = followups(equity=1016.66, today=date(2026, 8, 13))
    assert len(turns) == len(FOLLOWUPS)
    assert "1016.66" in turns[CONSTRAINT_INDEX]
    # Every other follow-up must be untouched.
    for i, (a, b) in enumerate(zip(turns, FOLLOWUPS)):
        if i != CONSTRAINT_INDEX:
            assert a == b, i


def test_the_daily_target_clears_the_organizer_floor_with_margin():
    """The floor is enforced by disqualification, so aiming AT it is aiming to
    fail on any run that comes up a cent short."""
    assert AI_SPEND_FLOOR == 1.00
    assert DAILY_TARGET > AI_SPEND_FLOOR
    # The top-up must not no-op while the period is still under the floor.
    assert TOPUP_BELOW > AI_SPEND_FLOOR
    assert TOPUP_BELOW <= DAILY_TARGET


def test_the_two_candidate_angles_ask_genuinely_different_questions():
    """Two angles exist to give the daily pass breadth from real material. If
    they converge into the same question, that is padding wearing a numeral."""
    a1, a2 = ANGLES[1], ANGLES[2]
    assert a1 != a2
    # The second explicitly forbids re-litigating the first, which is the
    # property that keeps them from collapsing together.
    assert "do NOT re-litigate whether the pair" in a2
    # ...and asks about execution rather than validity.
    for probe in ("reach the exit before", "median of 2.0 hours"):
        assert probe in a2, probe
    assert "split-half statistics" in a1


def _write_ledger(tmp_path, rows):
    p = tmp_path / "led.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return p


def test_ledger_prompts_are_built_from_the_days_own_decisions(tmp_path):
    """The part of the daily pass that cannot go stale. If it silently falls
    back to generic text the whole freshness argument collapses."""
    now = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    rows = [
        {"ts": "2026-08-13T09:00:00+00:00", "event": "enter", "pair": "FIL/AR",
         "side": -1, "z": 0.62},
        {"ts": "2026-08-13T11:00:00+00:00", "event": "skip", "pair": "FIL/AR",
         "reason": "side_blocked", "z": 0.71},
        {"ts": "2026-08-01T09:00:00+00:00", "event": "stop", "pair": "OLD/PAIR"},
    ]
    topics = dict(ledger_prompts(hours=24.0, now=now,
                                 path=_write_ledger(tmp_path, rows)))
    assert "day_trades" in topics and "day_refusals" in topics
    assert "FIL/AR" in topics["day_trades"]
    assert "side_blocked" in topics["day_refusals"]
    # The stale row is outside the window and must not appear anywhere.
    assert not any("OLD/PAIR" in t for t in topics.values())
    # A quiet-day topic must NOT be emitted when there was activity.
    assert "day_idle" not in topics


def test_a_quiet_day_gets_one_honest_topic_not_four_empty_ones(tmp_path):
    """Manufacturing four topics about nothing is exactly the padding this
    script has to avoid, and the quiet itself is a real question."""
    now = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    rows = [{"ts": "2026-08-13T10:00:00+00:00", "event": "ai_spread_assessment",
             "pair": "FIL/AR"}]
    topics = dict(ledger_prompts(hours=24.0, now=now,
                                 path=_write_ledger(tmp_path, rows)))
    assert list(topics) == ["day_idle"]
    assert "loosening" in topics["day_idle"]


def test_recent_events_survives_a_corrupt_or_missing_ledger(tmp_path):
    """A half-written line must not take the daily pass down -- the floor is
    cleared by this script and nothing else."""
    assert recent_events(path=tmp_path / "nope.jsonl") == []
    p = tmp_path / "led.jsonl"
    p.write_text('{"ts": "2026-08-13T10:00:00+00:00", "event": "enter"}\n'
                 '{"ts": "not-a-date", "event": "enter"}\n'
                 'not json at all\n'
                 '{"event": "no timestamp"}\n')
    got = recent_events(hours=24.0,
                        now=datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
                        path=p)
    assert len(got) == 1


def test_the_floor_alarm_stays_quiet_only_while_a_run_is_still_due():
    """The meter zeroes at every reset, so a naive check alarms every morning
    for hours, on schedule, correctly, and uselessly -- and an operator who
    scrolls past it daily will scroll past the one that matters."""
    # The period running 2026-08-13 16:00 UTC -> 2026-08-14 16:00 UTC. The
    # gateway states the END, in GMT+8: 2026-08-15T00:00+08:00 is 08-14 16:00Z.
    info = {"budget_reset_at": "2026-08-15T00:00:00+08:00",
            "budget_duration": "1d"}
    just_after = datetime(2026, 8, 13, 16, 30, tzinfo=timezone.utc)
    much_later = datetime(2026, 8, 13, 23, 0, tzinfo=timezone.utc)

    assert floor_state(0.0007, info, now=just_after) == "pending"
    assert floor_state(0.0007, info, now=much_later) == "short"
    assert floor_state(1.2093, info, now=just_after) == "clear"
    # An unreadable meter must alarm: a floor nobody can see is the one missed.
    assert floor_state(None, info, now=just_after) == "unknown"
    # ...and so must a period whose age cannot be established. Suppressing on
    # ignorance is the failure this whole guard exists to avoid.
    assert floor_state(0.0007, {}, now=just_after) == "short"


def test_the_grace_window_covers_both_scheduled_passes():
    """16:30 and 20:30 against a 16:00 reset -- the window has to outlast the
    top-up or the alarm fires while a run is still due to fix it."""
    assert FLOOR_GRACE_H > 4.5
    info = {"budget_reset_at": "2026-08-15T00:00:00+08:00",
            "budget_duration": "1d"}
    at_topup = datetime(2026, 8, 13, 20, 30, tzinfo=timezone.utc)
    assert period_age_hours(info, now=at_topup) == 4.5
    assert floor_state(0.5, info, now=at_topup) == "pending"


def test_period_age_reads_the_duration_rather_than_assuming_a_day():
    """`budget_duration` is "1d" today. If the organizer ever shortens it, an
    assumed 24h would silence the alarm for most of the new period."""
    twelve = {"budget_reset_at": "2026-08-13T12:00:00+00:00",
              "budget_duration": "12h"}
    noon = datetime(2026, 8, 13, 6, 0, tzinfo=timezone.utc)
    assert period_age_hours(twelve, now=noon) == 6.0
    # Unparseable duration falls back to a day rather than to zero, so the
    # window errs toward alarming rather than toward silence.
    assert _duration_hours("nonsense") == 24.0
    assert _duration_hours("1d") == 24.0
    assert _duration_hours("90m") == 1.5


def test_the_elimination_floor_agrees_with_the_one_status_reports():
    """Two modules each hardcode 800. They are the same competition rule, so a
    change to one that misses the other is the bug this catches."""
    from deploy.status import ELIMINATION_FLOOR as status_floor
    assert status_floor == ELIMINATION_FLOOR


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
