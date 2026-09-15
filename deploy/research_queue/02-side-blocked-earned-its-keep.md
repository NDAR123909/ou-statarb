# 02 — Did the one-sided re-entry block earn its keep?

**Blocks:** nothing. Run it when the queue reaches it.

**Why it matters anyway.** Of the five refusal paths the agent has, **exactly
one has ever fired**: the one-sided re-entry block. After a z-stop, that side
stays shut until the spread heals back inside the entry band. It has refused
entries **ten times** on a book that generates very few signals at all, so it
is a material fraction of everything the strategy ever wanted to do — and the
Reasoning Log says in writing that *"whether it protected us or cost us is an
open question we are carrying into Phase II."* This closes it, or establishes
that it cannot be closed at this sample size.

**Two things to know before starting.**

1. **`side_blocked` logging only shipped 2026-08-09.** Blocks before that date
   happened but were not recorded. The ten are the logged ones, not all of
   them. Do not describe them as the complete population.
2. **This is `CLAUDE.md` invariant 4.** A negative result does not mean rip it
   out; it means bring evidence to a human decision. The control exists
   because re-entering a spread that just broke structurally is how a
   mean-reversion book turns one loss into several.

## Updated 2026-09-13, after task 04 — read this before dispatching

Task 04 asked a structurally identical question about a different control
("does entry depth predict stop-outs?"), answered **no**, and produced three
things this brief did not know when it was written on 09-11.

**1. A method that found both candidate controls failing.** Counterfactuals
were scored not only on the P&L sum but on **the worst trades and on maximum
drawdown**, and that is what settled it: refusing entries above |z| 2.5 gives
up 69% of realised profit, avoids three of the *smallest* stops, keeps **all
five worst trades**, and makes drawdown slightly **worse**. A linear taper's
drawdown benefit was beaten by a flat size cut of identical P&L cost. **Use the
same cuts here.** A control that reduces total P&L can still be correct if it
cuts the left tail, and one that raises P&L can still be wrong if it does not —
MDD is 15% of the score and never heals.

**2. A finding that bears on this question directly, and may invert it.** The
losses are concentrated in the **middle**: |z| < 1 made +46.96, **|z| 1–3 lost
−32.63**, |z| 3+ made +22.97, and **all five worst trades entered between 1.19
and 2.33**.

`side_blocked` refuses re-entry after a stop, while z is healing back toward
the band — which routes it through **exactly that 1–3 region**. So the question
may not be "did the block cost us the trades it refused?" but "**is the block
the only thing standing between us and the zone where our money actually
died?**" Measure where, in |z| terms, each refusal sat. If the ten refusals
cluster in 1–3, that is the strongest argument for the control that exists, and
it is one nobody has made.

**3. A trap in the ledger.** Four `enter` records from 2026-07-20 carry
`notional: 0` with no legs in the fills — day-one `maxNotional` failures that
never became positions. Task 04 found all four sitting in the bucket under
test, where counting them shifted a stop rate from 43% to 27%. **Exclude
non-risk-bearing entries and say how many you excluded.** Risk-bearing total is
34, outcome-known 31, of which 22 have venue-verified P&L.

**And one caution about what "deep" means.** `entry_z` has only ever taken
three values — **0.4, 0.6 and 3.0** — so an entry's absolute |z| conflates
"chosen deep" with "the band happened to be 3.0 that week". Where depth matters
to your analysis, cut on **|z| / entry_z** or on distance to the stop, not on
|z| alone.

---

## Updated 2026-09-15 — a live block, and a re-entry shape the block does not cover

**The control is firing right now.** The 2026-09-15 20:00 stop on
`1000SHIB/DOGE` set `blocked=1`, so for the first time this task can be
answered partly against a block that is live rather than only archived ones.

**And the day that produced it contains the more interesting finding.** Our own
`day_trades` deep review, working from the 24-hour ledger, found this:

```
01:00  exit  short 1000SHIB/DOGE  z=-0.293
02:00  enter long                 z=-0.701
05:00  exit  long                 z=+0.051   (3-bar hold)
07:00  enter long                 z=-0.957   <- stopped at 20:00, -3.54
12:01  enter short NEAR/ICP       z=+2.371
```

Three round trips on one pair in six hours, and its verdict was *"the entry
gate is not actually gating — it's being re-triggered by the same pair's
noise."*

**Look at 05:00 → 07:00: exit long, re-enter LONG two bars later.**
`side_blocked` does not cover that. It blocks a side only after a **stop**; a
*reverted* exit followed by an immediate same-side re-entry passes straight
through, and on this day that re-entry is the one that went on to stop out.

So the task now has a second question beside its original one. The original:
*did the block cost us the trades it refused?* The new one: **is the block
scoped too narrowly — does the damage come from re-entries it was never
designed to catch?** Both are answerable from the same ledger, and the second
may matter more, because a control that fires rarely and correctly is cheap
while a gap that fires often is not.

Two cautions on the second question. A cooldown is **not** in the stated
methodology, and adding one would suppress genuine signals on the most active
pair — the deep review argued both sides of exactly this and landed on "the
ledger alone cannot separate them." And three round trips is n=3. **Measure the
rate across the whole record before treating one day as a pattern.**

## PROMPT

> You are testing whether a risk control paid for itself. Work from primary
> records; do not accept any figure stated in prose anywhere in this repo.
>
> **Data, all in this repo:**
> - `track_record/phase1_submission/reasoning.jsonl` — one JSON object per
>   line. Relevant events: `skip` with `reason=side_blocked` (the refusals),
>   `stop` (what triggered each block), `enter` / `exit`, and `refit` records
>   carrying each pair's fitted bands and half-life.
> - `track_record/phase1_submission/fills/*.json` — 19 dated snapshots
>   reconciled against the venue, with executed prices, fees and realised P&L.
>
> **The control:** after a z-stop fires at 3.5σ, that *side* of that pair is
> blocked from re-entry until z heals back inside the entry band. The other
> side stays open. It has fired ten times since logging began 2026-08-09.
>
> **Answer these, in order:**
>
> 1. **Reconstruct each block.** For each `side_blocked` skip: which pair,
>    which side, what z at the moment of refusal, which stop had triggered the
>    block, and how long the block stayed on before z healed.
>
> 2. **Build the counterfactual.** For each refused entry, follow the z path
>    forward from the refusal and determine what would have happened had it
>    been taken at the bands in force at the time: would it have reached its
>    exit band, hit the 3.5σ stop, or hit the 3× half-life max-hold clock?
>    Estimate the P&L of each, net of the two-leg cost model — round-trip cost
>    is `2 × taker_fee × (1 + |beta|)`, and the measured taker fee for the
>    period is in the fills snapshots.
>
> 3. **Total it.** Did the block cost money or save it, and how much? Report
>    concentration: if one refusal dominates the total, say so — the agenda
>    notes that one block sat *directly in front of the best trade of the
>    phase*, and a total driven by that single event is a different kind of
>    evidence from ten consistent ones.
>
> 3b. **Where did the refusals sit in |z|?** Task 04 found the losses
>    concentrated in |z| 1–3, with all five worst trades entering between 1.19
>    and 2.33. A block that fires while z heals back toward the band routes
>    through that region by construction. Report the |z| of each refusal, and
>    whether the refused entries would have landed in the zone that has
>    actually lost this book money. **If they cluster there, that is the
>    strongest argument for the control that exists and nobody has made it
>    yet.**
>
> 3c. **Count the re-entries the block does NOT cover.** `side_blocked` fires
>    only after a stop. Count every case where a pair **exited** (any reason
>    other than a stop) and was re-entered **on the same side** within a short
>    window — report the counts at 1, 3 and 6 bars, across the whole record,
>    not just the 2026-09-15 cluster. For each, what happened next: reverted,
>    stopped, or dropped at a refit? **Then compare that population's outcomes
>    against the stop-then-blocked population the rest of this task is about.**
>    If the uncovered re-entries lose more often or more deeply than the
>    covered ones, the block is scoped too narrowly and that is a bigger
>    finding than whether it earned its keep. Give the base rate too — how
>    often does same-side re-entry happen at all — so "three in six hours" can
>    be read against the norm rather than as an anecdote.
>
> 4. **THE QUESTION THAT ACTUALLY DECIDES THIS, and it is not total P&L.**
>    This competition scores **40% on Sharpe**, 25% PnL, 20% return, 15% max
>    drawdown — and MDD is monotonically non-decreasing, so a drawdown once
>    recorded never heals. A control that gives up some expected return to cut
>    the left tail can *improve* the score while *losing* money in raw PnL.
>
>    So compute both: the effect on total P&L, and the effect on the
>    **distribution** — the variance of the refused trades' outcomes, their
>    worst case, and whether taking them would have deepened max drawdown.
>    State whether the block is return-reducing, risk-reducing, both, or
>    neither. **"It cost us money" is not by itself a verdict against it.**
>
> 5. **Say whether ten is enough.** Ten observations, from one market regime,
>    with a logging gap before 2026-08-09 that hides an unknown number of
>    earlier blocks. Give your honest read on whether any conclusion is
>    supportable at this sample size, and what the result would need to look
>    like to be convincing either way. **"Not enough data to conclude" is a
>    perfectly good answer** and is better than a confident one that the sample
>    cannot support.
>
> 6. **State what the records cannot tell you.** Where the z path is too coarse
>    to determine whether an entry would have filled, or where bands changed
>    mid-block, say so rather than interpolating and presenting the
>    interpolation as a finding.
>
> **Then give a bottom line in one paragraph:** on this evidence, is the
> one-sided re-entry block earning its keep, costing us, or unproven?
>
> Write your answer to
> `deploy/research_queue/out/02-side-blocked-earned-its-keep.md`, including
> your per-block working table so the arithmetic can be checked without
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
>   control you are testing is a stated project invariant; a negative finding
>   is an input to a decision, not authority to remove it.

---

## What a finished answer looks like

A per-block table, a P&L total with its concentration stated, a separate
verdict on the risk-distribution effect, an honest read on whether n=10
supports any conclusion, and a one-paragraph bottom line.

The most likely useful outcome is **"unproven, and here is what would settle
it"** — which tells us what to instrument, and is worth more than a confident
answer the sample cannot carry.
