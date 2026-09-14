# 04 — Does entry depth predict stop-outs? · **GATE**

**Blocks:** any change to entry-depth sizing, and the "make the AI's role
demonstrable" agenda item.

**Why it is a gate.** On 2026-09-12 the agent entered `1000SHIB/DOGE` at
**z = +3.41 against a stop at 3.5** — a 0.09σ buffer before the structural-break
stop would have fired. It reverted to +0.83 and the position is up ~+7.92
unrealised. The agent's own analyst rated the regime **stressed** and wrote
*"proximity to the break-stop warrants elevated caution"*, and the architecture
had nowhere to put that: `broken` vetoes, `critical` news vetoes, `watch` news
halves, `stressed` does nothing.

The temptation is to add a control. **Do not, until this task answers whether
the risk is real** — the single observation we have is *favourable*, which is
the more dangerous kind, because it feels like confirmation rather than luck.

**The underlying gap is documented, not speculative.** `optimal_bands`
maximises profit-per-hour from first-passage times **assuming positions run to
reversion**, and takes no stop parameter. Our own review prompt states the
consequence: *"the band should therefore be chosen on stop geometry, which it
cannot see."* So the band says "enter past ±0.40" in a world with no stop, while
`ltp_agent.py` permits entries anywhere in `entry_z < |z| < stop_z` and sizes
them identically. A trade at 0.41 and a trade at 3.41 get the same risk budget.

**And the theory cuts both ways.** In OU terms a deeper entry means *more*
expected reversion — it is the better trade, not the worse one. The stop exists
because deep z might instead mean the relationship broke. Which effect dominates
is empirical, and we have 39 lifetime entries with `z` recorded on every one.

**A hint, and only a hint.** The eight stops entered at
z = −3.31, −3.02, +3.08, −1.39, +1.74, +2.33, −1.37, +1.19 — three of eight
beyond |3.0|. **The denominator is missing**, and it is the whole question.

---

## PROMPT

> You are testing whether one risk control is needed before anyone builds it.
> Work from primary records; do not accept any figure stated in prose anywhere
> in this repo, including the numbers quoted in this task file.
>
> **Background.** The agent trades mean reversion of a spread measured in z
> (standard deviations from a fitted equilibrium). It ENTERS when |z| exceeds a
> cost-aware band, typically 0.4–0.6, and it STOPS OUT at |z| = 3.5, where the
> working hypothesis flips from "temporarily stretched" to "the relationship
> broke". Entries are currently permitted anywhere between the band and the
> stop, and position size does not depend on z at all.
>
> The question: **does entering deeper — closer to the stop — make a trade more
> likely to stop out, and does it make money or lose it?**
>
> **Data, all in this repo:**
> - `track_record/phase1_submission/reasoning.jsonl` — `enter` records carry
>   `z` at entry, the pair, side, `entry_z` band, fitted `half_life`, `beta`,
>   `nav` and the risk budget `g`. Closing records are `exit` (with `reason`),
>   `stop`, and `refit_drop`. Match each entry to its close by pair and time.
> - `track_record/phase1_submission/fills/*.json` — 19 dated snapshots
>   reconciled against the venue, with executed prices, fees and realised P&L.
>
> **Answer these, in order:**
>
> 1. **Build the entry table.** Every `enter` record with its entry |z|, how it
>    closed (`exit` / `stop` / `refit_drop` / still open), hold duration, and
>    realised P&L where the fills support it. State how many entries you could
>    and could not match to a close, and how many have venue-verified P&L
>    rather than decision-price P&L only.
>
> 2. **THE DENOMINATOR.** Bucket entries by depth — a sensible cut is
>    |z| < 1, 1–2, 2–3, 3+ — and report, per bucket: how many entries, how many
>    stopped, the stop RATE, mean and median P&L, and the worst case. **The stop
>    rate conditional on depth is the number this whole task exists for.**
>
> 3. **Is the relationship monotone, or is it an artefact of a few trades?**
>    Report the concentration: if one or two deep entries dominate a bucket's
>    P&L, say so. With ~39 entries the deepest bucket may hold only a handful,
>    and a rate computed on four observations is not a rate.
>
> 4. **Distance to the stop, not just depth.** The band varies by pair and
>    refit, so `stop_z − |z_entry|` is the quantity that actually measures the
>    buffer. Redo the key cut on that. A 3.0 entry against a 0.4 band is a
>    different trade from a 3.0 entry against a 1.5 band.
>
> 5. **What would the alternatives have cost?** For each entry, compute what a
>    linear taper `size_mult = (stop_z − |z|) / (stop_z − entry_z)` would have
>    done to realised P&L, and separately what a hard refusal above |z| > 2.5
>    would have done. Report both totals against what actually happened.
>    **Include the effect on the WORST trades, not just the sum** — a control
>    that loses money on average while cutting the left tail can still be
>    correct, because MDD is 15% of the score and never heals.
>
> 6. **Say whether the sample supports a conclusion.** 39 entries, one market
>    regime, and the deep bucket is probably small. **"Not enough data" is a
>    good answer** and better than a confident one this sample cannot carry.
>    If it is your answer, say what sample size or what measurement would
>    settle it.
>
> 7. **State what the records cannot tell you** — unmatched entries, missing
>    fills, anything where you interpolated.
>
> **Then give a bottom line in one paragraph:** on this evidence, should entry
> depth affect position size, and if so by how much?
>
> Write your answer to `deploy/research_queue/out/04-entry-depth-vs-stops.md`
> with your per-entry working table, so the arithmetic can be checked without
> re-running you.
>
> **Scope — do not deviate:**
> - Work only inside this repo folder.
> - Create only the output file named above. Modify nothing else.
> - **Never modify `deploy/WEEKLY_REVIEW.md` or `deploy/LTP_STRATEGY.md`** —
>   they are append-only project records.
> - State your method and say plainly where a figure is sampled, estimated or
>   assumed rather than measured.
> - This is evidence for a human decision, not a recommendation to act. You are
>   testing whether a control is needed, and "it is not" is as useful a result
>   as "it is".

---

## What a finished answer looks like

A per-entry table, a stop rate by depth bucket **with its denominator**, the
same cut on distance-to-stop, counterfactual totals for both proposed controls
including their effect on the worst trades, and an honest read on whether 39
entries can carry the conclusion.

**If depth does not predict stop-outs, the correct action is to do nothing** —
and to say so in the record, so the next session that sees a frightening entry
does not re-propose this from scratch.

**If it does**, the control should be arithmetic — distance to the stop,
computed, ideally from the first-passage machinery already in
`statarb/thresholds.py` — and **not** a sizing lever handed to the language
model. The model called this risk correctly on 2026-09-12, but building AI
influence on one favourable observation would be manufacturing the thing the
Reasoning Log claims we do not do.
