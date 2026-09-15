# 01 — Recheck the −10.67 overshoot cost · **GATE**

**Blocks:** the sub-hourly intra-bar risk monitor decision, open since
2026-08-02 and carried past the 2026-08-09 and 2026-08-16 reviews without
being made.

**Why it is a gate.** The Phase II agenda says it plainly: *"Check the −10.67
overshoot arithmetic before anything else touches the stop. If it is wrong, the
intra-bar monitor's case largely evaporates."* The entire argument for building
the monitor rests on one number that has never been recomputed from primary
records, and two independent doubts have since been raised about it. Building a
risk control on an unverified figure would be the same mistake as the deep
review's fabricated 2.0h median hold — a number that read like a measurement,
went unchecked for a month, and steered ~45% of reviews.

**The claim under test:** *"Measured cost of not having a sub-hourly risk
check: −10.67 USDT across five stops, roughly a third of all losses"* — of
which **−8.31 comes from two events**, the stops that fired at 1.08σ and 6.75σ
past the band.

> **Correction, 2026-09-09.** This file originally said −8.31 came from *a
> single trade*. It does not, and no source said it did — `WEEKLY_REVIEW.md`
> line 821 and `ai_deep_review.py` line 798 both say two events, and the "one
> trade" was invented while writing this task. Left visible rather than quietly
> edited: a task file whose entire purpose is to check somebody else's numbers
> introduced a wrong one of its own, which is the exact failure it was auditing.
> Cowork caught it from the primary records.

**Two doubts already on record:**
1. The ledger totals report **`stop: 8`**, not five. Either three stops are
   excluded from the −10.67 for a reason nobody wrote down, or the counts
   disagree.
2. The deep-review synthesis flagged that one of these exits sits at **6.75σ**
   and questioned *whether it is a stop at all* rather than a data spike or a
   fill anomaly. If it is not, the sample is n=3 and −8.31 of the total may be
   an artefact.

---

## PROMPT

> You are auditing one number that a risk-control decision rests on. Recompute
> it from primary records; do not accept any figure stated in prose.
>
> **Data, all in this repo:**
> - `track_record/phase1_submission/reasoning.jsonl` — one JSON object per
>   line. Decision events include `stop`, `exit`, `enter`, `refit_drop`. Entry
>   and stop records carry the pair, side, z at decision, fitted `mu` /
>   `sigma` / `beta` / `half_life`, and the entry and stop bands.
> - `track_record/phase1_submission/fills/*.json` — 19 dated snapshots
>   reconciled against the venue's own execution records, with executed prices,
>   fees, exit reasons and the venue's own realised P&L. These are the only
>   durable record of what was actually realised; the venue serves ~7 days of
>   executions and then forgets.
>
> **The claim:** not having a sub-hourly risk check cost **−10.67 USDT across
> five stops**, of which **−8.31 came from one trade**. The agent's structural
> break stop is at **3.5σ** and it only evaluates once per hourly bar, so
> between bars z can overshoot well past 3.5 before anything acts.
>
> **Answer these, in order:**
>
> 1. **How many stops are there?** The ledger totals report `stop: 8`; the
>    claim says five. Reconcile that. If stops were excluded, identify which
>    and infer why from the records — and say clearly if no reason is
>    recoverable.
>
> 2. **Recompute the overshoot cost from the fills.** State your definition
>    explicitly before computing: presumably the difference between the P&L
>    realised at the actual exit z and the P&L that a fill exactly at z = 3.5
>    would have produced. If the records support a different or better
>    definition, use it and say why. Show the per-stop table.
>
> 3. **Test the 6.75σ exit.** Is it a genuine structural-break stop, or a data
>    spike, a fill anomaly, or a gap? Use the executed prices, the surrounding
>    z path, the venue's own `rpnl`, and the fee and slippage figures in the
>    snapshot. This one exit may carry most of the total, so the whole case may
>    rest on it.
>
> 4. **Report concentration.** How much of the recomputed total comes from the
>    single largest contributor? A number that is one event wearing a plural is
>    a different kind of evidence from five consistent ones.
>
> 5. **THE QUESTION THAT ACTUALLY DECIDES THIS — and it is not the same as the
>    total.** The proposed monitor is two-tier at **4.0–4.5σ**, read-only: it
>    may close or stop, never open. So the recoverable amount is not the full
>    overshoot cost. It is only the part where z spent long enough between 4.0
>    and the eventual exit for a sub-hourly pass to have acted.
>
>    For each stop, reconstruct the intra-bar path as far as the records allow
>    and ask: **would a monitor checking every N minutes actually have caught
>    it?** Report the recoverable fraction at N = 5, 15 and 30 minutes. If the
>    move from 3.5σ to the exit happened inside a single print, the monitor
>    recovers nothing there no matter how fast it runs.
>
>    **−10.67 is an upper bound on the prize. The recoverable fraction is the
>    prize.** Say which is which throughout.
>
> 6. **State what the records cannot tell you.** Intra-bar paths may not be
>    reconstructible from hourly data; say so where that is the case rather
>    than interpolating and presenting the interpolation as a finding. A clear
>    "this is not knowable from what we logged" is a useful result — it tells
>    us what to instrument next.
>
> **Then give a bottom line in one paragraph:** does the case for the intra-bar
> monitor survive, and at what monitor cadence, or does it evaporate?
>
> Write your answer to `deploy/research_queue/out/01-overshoot-recheck.md`.
> Include your per-stop working table so the arithmetic can be checked without
> re-running you.
>
> **Scope — do not deviate:**
> - Work only inside this repo folder.
> - Create only the output file named above. Modify nothing else.
> - **Never modify `deploy/WEEKLY_REVIEW.md` or `deploy/LTP_STRATEGY.md`** —
>   they are append-only project records.
> - State your method and say plainly where a figure is sampled, estimated or
>   assumed rather than measured. Prevalence and confidence claims must carry
>   how they were derived.
> - This is evidence for a human decision, not a recommendation to act.

---

## What a finished answer looks like

A per-stop table, a recomputed total with its definition stated, a verdict on
the 6.75σ exit, recoverable fractions at three monitor cadences, an explicit
list of what the logs cannot support, and a one-paragraph bottom line.

**Any of these three outcomes is a good result**, and the third is the most
valuable because it tells us what to log:

- the number holds and the monitor is worth building;
- the number does not hold and a decision open since 2026-08-02 closes as "no";
- the records cannot answer it, and the next thing to build is the
  instrumentation rather than the monitor.
