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

---

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
