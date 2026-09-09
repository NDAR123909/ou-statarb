# 03 — What has frame drift actually cost us?

**Run this ahead of task 02.** Nothing formally blocks on it, but it is the
only mechanism two independent analyses have converged on, and it touches both
the honesty of our exit labels and the timing of our stops.

## Why this one

The agent re-estimates `mu` and `sigma` at every refit, from the last three
half-lives of spread. A position held across a refit is therefore **judged in a
coordinate frame that is not the one it was entered in.**

This is documented, not a surprise. `LTP_STRATEGY.md`'s 2026-08-06 addendum
works a case through in full: a short AVAX/SOL spread entered at z=+0.717 and
exited at z=−0.109 tagged `reverted`, reasoning line *"the mean-reversion cycle
completed."* It had not. On the entry's own hedge ratio **the spread rose
0.0101 while z fell 0.827** — opposite directions — and the position closed at
−4.11. Two refits fired during the 38-hour hold and the equilibrium moved ~1.3σ
while the spread moved only 0.5σ. The reversion target chased the price and
overtook it.

That addendum ends with the sentence this task exists to answer:

> **"the cost was never written down."**

It shipped the instrumentation instead — `entry_mu` and `entry_sigma`
snapshotted at open and carried across refits, and `entry_frame()` reporting
`z_in_entry_coords`, `mu_shift_sigma` and `equilibrium_reestimated` on every
`exit` and `stop`. That has been live since **2026-08-06**. Nobody has read it
back.

**Two independent hits, neither looking for it.** The deep-review synthesis
(2026-09-09) called μ re-estimation walking toward open positions *"the corpus's
one real contribution."* The overshoot audit the same day, auditing something
else entirely, found the KAS/ETC stop of 2026-08-20 reading **3.597σ in entry
coordinates against 4.752σ refitted** — a 0.097σ overshoot or a 1.25σ one
depending which logged number you believe. Two analyses converging on one
mechanism from different directions is the strongest signal this project has
produced in a week.

**Note the direction is not fixed.** "μ walks toward the position" shrinks |z|
and makes stops fire late; the KAS/ETC case has refitted z *larger* than entry
z, so the frame moved the other way. Both `mu` and `sigma` are re-estimated, so
either can dominate. Treat this as **frame drift**, not as a one-directional μ
bias, and let the data say which way it actually runs.

## The convention, and a solved worked example — do not re-derive these

Task 01 reported the `z_in_entry_coords` convention as undocumented and its
sign inconsistent on the KAS/ETC stop. It is neither, and the resolution is
your anchor case. `ltp_agent.py:355–383`:

```python
z_entry_frame = (spread - mu0) / sig0     # current spread, ENTRY frame
mu_shift      = (live_mu - mu0) / sig0    # equilibrium move, in ENTRY sigmas
```

Unadjusted for position side. Solving KAS/ETC 2026-08-20 from its three logged
numbers:

```
(s − mu₀)/σ₀        = +3.597     (logged z_in_entry_coords)
(mu_live − mu₀)/σ₀  = +6.443     (logged mu_shift_sigma)
  ⟹ (s − mu_live)/σ₀ = −2.846
(s − mu_live)/σ_live = −4.752    (logged z)
  ⟹ σ_live/σ₀ = 0.599
```

**Fully consistent. σ collapsed 40% during the hold**, and the sign flip is the
equilibrium *overtaking* the spread — mu moving up past where the price sat.
Both effects ran at once and the σ tightening is what amplified a −2.846σ₀
residual into a −4.75σ reading. In entry coordinates the stop overshot the 3.5
band by **0.097σ**; in refitted coordinates it reads 1.25σ past.

Two things follow for your work. **σ drift matters as much as μ drift** and the
`mu_shift_sigma` field alone will not capture it — you will have to infer
σ_live/σ₀ from the two z readings, as above, wherever both are logged. And **a
sign flip between the two frames is a signal, not a data error**: it means the
equilibrium crossed the price during the hold, which is the strongest form of
the effect being measured.

---

## PROMPT

> You are measuring what a known, documented mechanism has cost. Work from
> primary records; do not accept any figure stated in prose anywhere in this
> repo, including the worked example in `LTP_STRATEGY.md`.
>
> **Background you need.** The agent enters a position at some spread level and
> computes z against a fitted equilibrium `mu` and scale `sigma`. Both are
> re-estimated at every refit. A position held across a refit is therefore
> judged against a moving frame: its z can change without the spread moving at
> all. Exits fire on z, stops fire on z at 3.5σ, so both are affected.
>
> **Data, all in this repo:**
> - `track_record/phase1_submission/reasoning.jsonl` — one JSON object per
>   line. `exit` and `stop` records carry, **since 2026-08-06 only**:
>   `z_in_entry_coords` (z recomputed in the frame the position was opened in),
>   `mu_shift_sigma` (how far the equilibrium moved during the hold, in units
>   of the entry sigma) and `equilibrium_reestimated` (true when
>   `|mu_shift_sigma| >= 0.10`). Records also carry the exit reason, the pair,
>   the side, and z at decision. `enter` records carry the entry z and fit.
>   `refit` records carry each pair's bands and half-life and are timestamped,
>   so you can tell which holds spanned a refit.
> - `track_record/phase1_submission/fills/*.json` — 19 dated snapshots
>   reconciled against the venue, with executed prices, fees, exit reasons and
>   the venue's own realised P&L.
>
> **Answer these, in order:**
>
> 1. **Coverage first.** The instrumentation shipped 2026-08-06. How many
>    `exit` and `stop` records have these fields and how many predate them?
>    Every later figure is over the instrumented subset only — say so plainly
>    and give its size before quoting anything from it.
>
> 2. **How far does the frame move, in BOTH parameters?** Distribution of
>    `mu_shift_sigma` across the instrumented closes: how often does it exceed
>    the 0.10σ materiality threshold, and what is the tail? Does it move
>    **toward** open positions (shrinking |z|, flattering exits and delaying
>    stops) or **away**, or neither systematically? A systematic direction is a
>    bias; noise is not.
>
>    **Then do the same for sigma**, which has no logged field of its own.
>    Where both `z` and `z_in_entry_coords` are present, recover the ratio the
>    way the worked example in this file does — a σ that tightens amplifies the
>    residual and can dominate the μ term entirely. Report the two effects
>    separately; a conclusion that attributes σ tightening to μ drift would be
>    wrong about the mechanism even with the right total.
>
> 3. **Re-label the exits.** For each instrumented `exit` tagged as a reversion,
>    compare z at decision against `z_in_entry_coords`. **How many exits would
>    not have been exits in the frame they were entered in?** Give a corrected
>    exit-reason tally beside the reported one.
>
>    This is the honesty question, not just a performance one. Our Reasoning
>    Log reports exit reasons and a win rate; if some reversions were losses
>    the moving target converted into apparent successes, those numbers
>    overstate what the strategy did.
>
> 4. **Re-time the stops.** For each instrumented `stop`, compare the trigger
>    in refitted coordinates against entry coordinates. Would it have fired
>    earlier, later, or not at all in the entry frame? Quantify the P&L
>    difference where the fills support it. The 2026-08-20 KAS/ETC stop is the
>    known case — check whether it is the only one.
>
> 5. **Total the cost, and be careful what you call cost.** Separate:
>    (a) P&L attributable to the frame moving rather than the spread reverting;
>    (b) mislabelling, where the P&L is unchanged but the stated reason is
>    wrong. These are different failures with different remedies, and (b) can
>    be large while (a) is zero.
>
>    Weight it against the scoring: **40% Sharpe, 25% PnL, 20% return, 15% MDD,
>    and MDD is monotonically non-decreasing** so a late stop deepens a drawdown
>    that never heals. A small P&L effect concentrated in the left tail matters
>    more than its size suggests.
>
> 6. **What would the evidence have to show to justify changing this?** Do not
>    propose a change. State the design question honestly: a position could be
>    judged in the frame it was entered in (frozen `mu`/`sigma` until close) or
>    in the current one. **Both have failure modes** — a frozen frame will not
>    register a genuine structural break, and a trailing frame chases the
>    position. Say what the data would need to look like to favour either, and
>    whether what you found reaches that bar.
>
> 7. **State what the records cannot tell you.** The instrumented sample is
>    small and comes from one regime. **"Not enough data to conclude" is a good
>    answer** and better than a confident one this sample cannot carry.
>
> **Then give a bottom line in one paragraph:** what has frame drift cost, in
> P&L and in the accuracy of what we have claimed, and is it big enough to act
> on?
>
> Write your answer to `deploy/research_queue/out/03-frame-drift-cost.md`,
> including a per-close working table so the arithmetic can be checked without
> re-running you.
>
> **Scope — do not deviate:**
> - Work only inside this repo folder.
> - Create only the output file named above. Modify nothing else.
> - **Never modify `deploy/WEEKLY_REVIEW.md` or `deploy/LTP_STRATEGY.md`** —
>   they are append-only project records.
> - State your method and say plainly where a figure is sampled, estimated or
>   assumed rather than measured.
> - This is evidence for a human decision, not a recommendation to act. The
>   trailing mean is documented, intentional behaviour, and a negative finding
>   is an input to a decision rather than authority to change a live strategy.

---

## What a finished answer looks like

A coverage statement, a distribution of frame movement with its direction, a
corrected exit-reason tally beside the reported one, a re-timed stop table, a
cost split into P&L and mislabelling, and an honest read on whether the sample
supports acting.

**The mislabelling half may matter more than the P&L half.** This project's
stated value is that its record can be trusted; an exit reported as
"mean-reversion cycle completed" that was a loss dressed up by a moving target
is a defect in the record itself, and it is the kind an audit would find.
