# Deep review synthesis — `ai_deep_review.jsonl.gz`

Synthesis of the adversarial review corpus in
`track_record/phase1_submission/ai_deep_review.jsonl.gz`: 3,424 reviews written
2026-08-12 to 2026-08-21 against the OU pairs-trading agent's conclusions.

Written 2026-09-09, after Phase I closed. This document only reads the corpus and
the project's own records; it changes nothing and recommends nothing that has not
been checked against a number.

---

## 1. What the corpus actually is

Reconstructing the record structure from `deploy/ai_deep_review.py` matters,
because the shape of the corpus determines what "convergence" in it is worth.

| Property | Value |
|---|---|
| Reviews | 3,424 |
| Conversations | 511 (483 complete 7-round arcs) |
| Topics | 38 — 32 candidate-pair topics, 6 strategy topics |
| Model | `MiniMax-M3`, **all 3,424 reviews** |
| Rounds | 7, escalating, cumulative context |
| Passes | `pass_index` 1 (1,953), 2 (1,051), unlabelled (420) |

Two structural facts govern everything below.

**The corpus is one model, not a panel.** Every review came from `MiniMax-M3`. So
agreement between reviews is *replication of one model under resampling*, not
independent corroboration. Where 400 reviews say the same thing, that is evidence
about the stability of one model's priors, and only weakly evidence about the
world. This is not a defect of the exercise — the script is honest that later
passes are "compliance volume, not new analysis" — but it caps what any tally in
this document can mean, and I have tried not to launder repetition into confidence.

**Rounds are fixed prompts, not free exploration.** Round *n* is always the same
question, so a claim's round is a fact about what it was asked, not about what it
found:

| Round | Prompt |
|---|---|
| 1 | The topic itself (pair fit, or a conclusion under review) |
| 2 | "Name the single measurement that would most change your answer" |
| 3 | "Argue the OPPOSITE, then say which the evidence supports" |
| 4 | "What should the next 20 round trips look like? Give falsifiable predictions" |
| 5 | **The risk-budget / constraint prompt** |
| 6 | "What have the operators not asked you? Which framing assumption is wrong?" |
| 7 | "Rank your claims by confidence; say what is thin about the bottom three" |

Round 7 is the most useful layer in the corpus: the model separates numbers it was
*given* from numbers it *inferred*, and it does this consistently and well.

---

## 2. The round-5 exclusion, and a correction to it

You asked me to discount round 5 because it reasoned from an understated
drawdown-headroom figure. That is right, and the corpus lets me locate the defect
exactly — but the instruction is both slightly too broad and materially too narrow.

Round 5 is `FOLLOWUPS[3]`, the constraint prompt. Before commit `eef2526`
(2026-08-12 19:27:29 UTC) it read: *"Roughly 100 USDT of drawdown headroom sits
above the elimination floor."* That 100 was the distance to the **self-imposed kill
switch** (916.25), not to the **competition elimination floor** (800). The fix
replaced it with both numbers stated separately.

**Too broad.** The corpus straddles the fix. Only 57 of 486 round-5 records were
generated before it; 429 used the corrected prompt that names both floors.

**Too narrow, and this is the part that matters.** Each conversation carries its
full history forward, and rounds 6 and 7 explicitly reason *over* it — round 6 asks
what was missed across the conversation, round 7 asks the model to rank the claims
it made in the conversation. So in the 57 pre-fix conversations, the bad number is
inside the context of rounds 6 and 7. Discarding round 5 alone leaves it in.

The contamination is directly visible:

| Rounds 6–7 | n | cite "100 USDT headroom" | cite both floors correctly |
|---|---|---|---|
| In pre-fix conversations | 114 | 7.9% | 0.0% |
| In post-fix conversations | 854 | 0.0% | 28.6% |

So I applied your rule and then extended it:

- **Excluded:** all 486 round-5 records (your instruction, applied in full).
- **Also excluded:** the 114 round-6/7 records from the 57 pre-fix conversations,
  which inherit the bad figure through conversation context.
- **Retained:** rounds 1–4 of pre-fix conversations. The constraint prompt is
  introduced *at* round 5, so nothing before it can have seen the figure.

**Working corpus: 2,824 of 3,424 records.** Nothing in the ranking in §6 rests on
an excluded record. Where I quote an excluded review it is labelled and used only
to illustrate the contamination, never as support.

One note for the record: the 429 clean round-5 reviews are usable evidence and I
have set them aside only because you asked. They do not change the ranking below —
I checked — but they are the one place the corpus discusses position sizing against
the real risk budget, and if that question comes back they are worth rereading.

---

## 3. The finding that governs the rest: the most convergent claim is a prompt artefact

The single most repeated substantive claim in the corpus is that the agent's median
hold of **2.0 hours** is wildly inconsistent with **fitted half-lives of 17–26h**.
It appears in 44.8% of clean strategy reviews and 31.4% of clean pair reviews. In
the round-7 confidence rankings it is repeatedly placed in the top two, described as
"the dominant unaddressed issue" and "structural," with the model noting the
supporting numbers were *given* rather than inferred — its highest evidence grade.

The numbers were indeed given. They are also wrong.

**Where they came from.** Both halves are hardcoded, not measured:

- `deploy/ai_deep_review.py:397` — inside the angle-2 prompt sent for *every*
  candidate pair, *every* day: *"holds a median of 2.0 hours against fitted
  half-lives of 17-26 hours."* Static string; never updated from the ledger.
- `RECORD_FALLBACK` (line ~630) — used whenever the live snapshot could not be
  read: *"median hold 2.0h against fitted half-lives of 17-26h"*, labelled as
  *"the 2026-08-09 reading."*

**What the project's own records say.** From
`track_record/phase1_submission/fills/`:

| Snapshot | Round trips | Median hold |
|---|---|---|
| 2026-08-02 | 11 | 3.0 h |
| 2026-08-04 | 10 | 2.5 h |
| 2026-08-07 | 3 | 13.0 h |
| **2026-08-09** | **3** | **26.0 h** |
| 2026-08-13 | 5 | 23.0 h |
| 2026-08-16 | 3 | 11.0 h |
| 2026-08-20 | 5 | 8.0 h |

**No snapshot ever reported 2.0h.** The lowest is 2.5h. The 2026-08-09 snapshot —
the exact reading the fallback claims to quote — reports **26.0h**, which sits
*inside* the 17–26h band. Across all 29 closed round trips in Phase I the median
hold is **8.0h**. The fallback's companion figures are equally unmatched: it claims
13 round trips and +9.41 net, while the 08-09 snapshot records 3 round trips and
−0.99 net. Only its fee (1.752 bps) and slippage (0.57 bps) match.

The second term fails too. The strategy prompt asserts "fitted half-lives of
17-26h" as a global property, but across 463 half-lives quoted in the pair reviews'
own fitted numbers the median is **53.6h**; only **21.4%** fall inside 17–26h,
**72.8%** are above 26h and **23.3%** exceed 100h. (The gate's actual band is
6–168h.)

**So the mismatch reviewers were asked to explain was manufactured at both ends.**
On the date the fallback cites, hold and half-life agreed.

This does not make the reviews bad. Given the premise, the reasoning about it is
often excellent — models were asked to explain a discrepancy and explained it. But
it means the corpus's strongest apparent consensus measures the prompt, not the
strategy, and three widely-repeated downstream claims collapse with it:

- that the entry band must be too tight (the inference from a 2h hold);
- that fitted half-lives are systematically over-estimated by 2–3×;
- that the agent is "harvesting overshoot, not mean reversion" — i.e. trading
  momentum while believing it trades reversion.

Each is a reasonable deduction from a false premise. None is independently
supported anywhere in the corpus.

**The general lesson, which holds across the corpus:** frequency here is
anti-correlated with novelty. The most-repeated claims are the ones the prompt
planted; the sharpest ones appear once or twice (§5, §6).

**Three reviews came close to catching it.** 3.4% of clean reviews question the
supplied facts at all, and several caught *internal* inconsistency in per-pair fits
— "the numbers are internally inconsistent (HL says 53h, path shows ~24h cycles)",
"the path reverted roughly 2–3x faster than the fitted half-life predicts." That
instinct was right and was aimed at the correct target. But no reviewer could check
the hold figure, because none was given the fills record. Reviewers were told to
attack the conclusions; they were not given the means to audit the premises.

---

## 4. Where the reviews converge — and what each convergence is worth

| Claim | Prevalence (clean) | Independent? | Verdict |
|---|---|---|---|
| Half-life vs 2.0h hold mismatch | 44.8% strat / 31.4% pair | No — planted | **Dead** (§3) |
| n=5 stops cannot support any stop retune | 36.7% strat | Yes | **Survives** |
| Sharpe is noise-dominated; the score cannot resolve small changes | 12.3% strat | Yes | **Survives** |
| Two of five stops carry 78% of overshoot cost | near-universal where asked | Given arithmetic | **Survives, but see below** |
| Don't trade these candidate pairs now | 87 of 88 replicate groups (99%) | Weakly | **Survives, low information** |
| μ re-estimation walks toward the open position | 18.5% strat / 17.6% pair | Yes | **Survives — strongest new claim** |
| Waiting has a real cost (idle days drag Sharpe) | 16.4% strat | Yes | **Survives, contested** |

Four of these deserve comment.

**The 99% agreement on "don't trade" is worth less than it looks.** Of 154 same-pair, same-day
replicate groups, 88 yielded a classifiable verdict on both passes; 87 of those 88
agreed — all "no." That looks like overwhelming consensus. But it is one model
agreeing with itself on the conservative option, and the near-unanimity should be
read as such. The rate at which a reviewer instructed to be adversarial declines to
trade is not a measurement of the market.

**The stop-concentration statistic is arithmetic, not evidence.** "Two of five
stops carry −8.31 of −10.67" is exact and reviewers correctly graded it as given.
But it is a concentration ratio computed by ranking a sample of five, and the corpus
itself makes the point: *"With n=5, the top-two concentration ratio has an
interquartile range that comfortably spans 40% to 95% under any reasonable parent
distribution. The arithmetic is not wrong; the inference drawn from it is
overconfident by an order of magnitude."* The number survives; the heavy-tail
interpretation does not.

**The n=5 objection survives everything thrown at it.** It is the most robust
result in the corpus. It appears in round 1, is attacked in round 3, and survives
in round 7 in both directions — reviewers repeatedly note that n=5 blocks positive
claims *for* the monitor and *against* it equally. The corpus's own best statement:
*"The reviewer is making a positive claim on a sample that does not support positive
claims in either direction."*

**The μ-drift mechanism is the one place the corpus adds something.** It is
developed furthest in the `mu_drift` topic and recurs, unprompted, in 17.6% of pair
reviews on entirely different questions. Unlike the stop debate it does not rest on
sample size at all, and the corpus's sharpest argument says so: *"The mechanism is
identifiable, the bias is sign-asymmetric against the open position, and the
existing stop data corroborates it. The operators should not be waiting for n."*
See §6, rank 1.

---

## 5. Where the reviews genuinely contradict each other

Excluding contradictions traceable to fact drift (§7), four real splits remain.

**5.1 Entry band: widen to 0.8σ, or stay at 0.4σ?**
The clearest live disagreement, and both sides are numerate.

*Widen* (6.2% strat, 5.2% pair): edge-to-risk is 0.8/2.7 = 0.296 versus 0.4/3.1 =
0.129, a 2.3× improvement; and the frequency penalty is negligible — at the fitted
κ ≈ 0.031/h the crossing-rate ratio between 0.4σ and 0.8σ is ≈ 1.015. If that holds,
the "twice as large and twice as rare" premise in the conclusion under review fails
outright on its second half.

*Stay* : edge-to-risk ratios computed on a light-tailed process invert under heavy
tails, so the 0.4σ entry's smaller stop-territory is worth more than the conditional
calculation shows; and a sparser return series raises the variance of a Sharpe
already estimated on ~20 daily returns.

The same conversation that argued to widen then dismantled its own EV estimate in
round 7: the +40 USDT differential rests on three unverified scaling assumptions and
a guessed trade rate, with a true range of roughly 2×. Its own verdict —
**"the evidence cannot cleanly separate them, and the gap is narrow"** — is the
honest reading. Note the widening case is partly downstream of the dead 2.0h premise
(the "band too tight" inference), which weakens it further.

**5.2 Is the 6.75σ stop the same kind of event as the other four?**
A minority claim (12 reviews) with outsized consequences. A 6.75σ overshoot past a
3.5σ band is a 10.25σ excursion; under the fitted OU parameters its expected waiting
time is absurd — one review computes ~2×10²² bars. Two readings:

- *Fat tails the OU misses* — the stop is calibrated to the wrong distribution.
- *Not a statistical event at all* — a refit-drop misclassified as a stop, a venue
  halt, a margin close, or a z-computation error.

If the second is right, the genuine stop sample is **n=3**, and every tail claim in
the corpus loses its basis. Both readings are consistent with everything given. This
is cheap to settle and nothing settles it (§6, rank 2).

**5.3 Is the empty-refit run a regime, or a gate artefact?**
No convergence at all — this is the corpus's most even split. Classifying the
diagnosis across 433 pair round-1 reviews:

| Diagnosis | Count | Share |
|---|---|---|
| Artefact of the 07-31/08-01 shock | 55 | 12.7% |
| Genuine loss of cointegration | 40 | 9.2% |
| Both / explicitly unidentifiable | 65 | 15.0% |
| Mixed | 98 | 22.6% |
| Unclassifiable | 175 | 40.4% |

No pair holds a stable diagnosis across passes. So: **the action converges (99% "do
not trade") while the reason does not.** The conclusion under review — "this is a
market-wide loss of stability properties, and the correct response is to wait" —
is therefore only half-supported. Waiting is well-supported; the causal story
behind it is not, and it should not be recorded as though it were.

**5.4 Does waiting cost anything?**
*"Idle days drag the Sharpe mean exactly as small losses do"* is true only under the
null of no edge. If the strategy has positive expectancy, idle days are strictly
worse than small losing trades. The corpus never resolves this, because it never
establishes whether the edge is real — which, after the fee correction from 5.0 to
1.75 bps/side, several reviews argue is now the open question: *"the operators had
assumed 2.5× the true fee and still produced only +9.41 net, so the alpha before
costs is modest."*

---

## 6. Surviving claims, ranked by how much they would change a trading decision

Ranked by decision impact: how much would act on this change position sizing, gate
configuration, or capital at risk. Confidence is mine, after the filtering in §2 and
the correction in §3 — it is not the corpus's own confidence, which over-rates
planted premises.

### Rank 1 — μ is re-estimated during an open position, and walks toward it
**Impact: high. Confidence: high. Status: unaddressed.**

μ is the trailing mean of the last 3 half-lives, refit on a schedule that ignores
open positions. On the 2026-08-05 trade, two refits fired inside a 38-hour hold; the
spread rose 0.0101 while z fell 0.827 — opposite directions. The reversion target
chased the price and overtook it.

Why this outranks everything else: **the bias is sign-asymmetric and it is
structural, not statistical.** A short entered at z>0 has price above μ; further
upward drift pulls the trailing mean *up with the position*, against it. A long at
z<0 is *helped* by the same drift. The estimator systematically hurts the side that
is already extended — the exact opposite of what a mean-reversion system should do
to its open positions, and it compounds entry adverse selection.

The operators' defence — freezing μ means holding to a stale mean, and n=1 — does
not hold. n=1 is the wrong objection to a mechanism that is identifiable from its
structure rather than its sample. And "adapting to genuine regime change" is not
what a 3-half-life window does during a 38-hour hold: it adapts to *the trade's own
price action*. A genuine break would need to be large relative to σ, persistent
beyond one half-life, and visible in the other leg. No such gate exists.

**The claim that makes this urgent, and that no one has tested:** the μ-drift
mechanism and the stop overshoots may be the same failure at different amplitudes.
If μ walks toward an open position, the 3.5σ band walks with it — so the
"structural-break stop" is firing in a moving reference frame. The 1.08σ overshoot
is the visible near-miss; the 6.75σ event is what it looks like at amplitude. If
this holds, the entire stop-geometry debate (§5.1, §5.2) has been arguing about the
wrong object, and the fix is upstream of the stop.

*Proposed remedies, corpus's own ranking:* (a) refit μ mid-trade only when the new
residual exceeds ~2.5σ against *entry-time* μ and σ; (b) freeze μ per trade and let
the band stop handle genuine breaks; (c) two-speed μ — fast for entry scoring, slow
(EWMA, ≥5× the fast window) for exit and stop evaluation. (c) is the most-recommended
and its named failure mode is fast/slow disagreement at regime boundaries, bounded
because the band stop is the right exit there anyway.

**Check first (cheap, from data already held):** the distribution of refit count per
open trade, and Δμ measured against entry-time μ over each hold. If most trades see
zero mid-hold refits, this is a rare-event problem and drops several ranks. If two
refits in 38h is typical, it is systematic and the sign asymmetry makes it costly.

### Rank 2 — The 6.75σ stop may not be a stop
**Impact: high. Confidence: low, but it is one query. Status: untested.**

If that event is an operational artefact — misclassified refit-drop, venue halt,
margin close, data error — then the genuine stop sample is n=3, the "78% of cost in
two outliers" statistic loses its subject, and the case for any intra-bar monitor
collapses with it. If it is a real statistical event, the OU tail assumption is
wrong and the stop is calibrated to the wrong distribution. **These imply opposite
actions, the cost of distinguishing them is one look at the order book and venue
status around a single known timestamp, and no one has looked.** Highest
information-per-unit-effort item in the corpus.

### Rank 3 — The stop level should not be retuned on this evidence
**Impact: high (as a brake). Confidence: high. Status: consistent with current config.**

The most robust survivor. n=5 (possibly n=3, per rank 2) supports no positive claim
about stop geometry in either direction. Separately, the conclusion under review is
internally inconsistent on its own terms: an intra-bar monitor triggering at
4.0–4.5σ is *less* sensitive than the existing 3.5σ stop, so it fires later, not
earlier — while the evidence offered for it ("4 of 5 stops reverted within 72h")
argues the stop is already too sensitive. Multiple reviews caught this independently.
A monitor at 4.0σ would also not have caught the 6.75σ event and would have caught
nothing else.

The corpus's best framing: the change is a free option under a noise-dominated
score, but "free" is not a reason to make it. **Leaving stop_z at 3.5 is the
supported action; the stated reasoning for the monitor is not.**

### Rank 4 — The scored metric cannot see most of what is being debated
**Impact: high on prioritisation. Confidence: high. Status: acknowledged, under-applied.**

Sharpe carries 40% of the score and is computed on ~20 daily returns; one −0.8% day
moved it from 9.30 to 5.66. Against that noise floor, the monitor, the band choice,
and most of the stop debate are invisible to the score. This cuts symmetrically and
the corpus catches both directions: the change cannot help the score, and it cannot
hurt it. The operational consequence is about attention, not parameters — effort
spent on changes the score cannot resolve is effort not spent on rank 1 and rank 2,
which are about whether the machinery is correct rather than whether it is optimal.

### Rank 5 — "Wait" is right; the reason given for it is not established
**Impact: medium. Confidence: high on the split. Status: recorded reason is over-stated.**

99% verdict convergence on not trading, near-zero convergence on why (§5.3). The
`day_fits` review adds a concrete falsifier the corpus mostly missed: on 2026-08-12
the ledger shows an `enter` event, so *that* day's record is not consistent with
"no pair is tradeable" — one pair cleared all six gates and was traded. The two
regimes are distinguished by the **gate-audit table** — candidates evaluated,
rejections per filter, filter-by-filter margin of the survivor, pre/post-refit pass
rates — which is not derivable from the event log and which only 3 conversations
asked for. A mis-firing gate is monocausal (one filter kills >70% of otherwise-clean
candidates); a genuinely empty opportunity set is distributed.

Recommend keeping the "wait" action and downgrading the recorded justification from
"market-wide loss of stability properties" to "no candidate cleared the gate; cause
not established."

### Rank 6 — The FDR family is probably ill-defined
**Impact: medium-high if true. Confidence: moderate. Status: raised in 3 conversations, never answered.**

Benjamini-Hochberg controls false discovery across a *family* of tests. If the
family is "every cointegration test run today," tests on the same pair across
overlapping lookback windows are not independent, and the BH assumption is violated
— which would make the gate reject at the wrong rate in a way that looks exactly
like a regime. This bears directly on rank 5: a mis-specified FDR correction is a
gate *measuring the wrong thing*, and correcting it is not a loosening, which is the
distinction the operators explicitly asked for and the corpus almost entirely
failed to supply. Nearly invisible by frequency (7 reviews), high value.

Related and equally thin (15 reviews): a Hurst filter at a fixed cutoff treats
H=0.505±0.02 identically to H=0.95. If rejections cluster near the cutoff, the gate
is rejecting on estimation noise.

### Rank 7 — Entry-band widening
**Impact: medium. Confidence: low. Status: not actionable as it stands.**

The κ-based crossing-rate calculation (ratio ≈ 1.015) is the corpus's best single
piece of new arithmetic and it does refute the "twice as rare" half of the
conclusion under review. But the EV case for widening was withdrawn by its own
author in round 7, and part of its motivation traces back to the dead 2.0h premise.
The measurement that would settle it — realised win rate at 0.4σ vs 0.8σ on ≥30
trades each — needs roughly 4× the entire Phase I trade count. **Not settleable on
this record.** The crossing-rate result is worth keeping; the recommendation is not.

### Rank 8 — Entry friction may exceed what the record acknowledges
**Impact: low-medium. Confidence: low. Status: untested, cheap.**

Signal z at decision versus realised z at fill. If fills land 0.2–0.5σ adverse, the
"enter at z, exit at 0" trade is really "enter at z−δ, exit at 0+ε" with a smaller
edge. The model itself graded the 0.2–0.5σ figure as a guess built on an assumed
30–50 bps hourly spread volatility. Raised in only 2 conversations, and it is one
join on data already held.

---

## 7. Three ways this corpus misleads a reader who takes it at face value

**7.1 Fact drift reads as disagreement.** The briefing is rebuilt daily and moved
substantially over the ten days: equity 1024.78 → 1016.56 → 1020.30 → 1045.14 →
1037.96; days remaining 9 → 0; the record block is a rolling ~7-day window whose
trade count fell 13 → 5 → 4 → 3 → 2 → 5 as trading slowed. Reviews dated 08-13 and
08-19 answering "the same" question were answering about different books. Several
apparent contradictions in the corpus are two correct answers to two different
states. Any future reading must condition on `ts`.

**7.2 A stale fallback outlived its label.** `RECORD_FALLBACK` is honestly marked
"treat them as dated" — good practice that did its job. It is also, per §3, not a
faithful record of the date it names. The failure was not staleness; it was a
hand-typed block that drifted from its source and kept a label asserting it hadn't.
The module comment two lines above it anticipates exactly this: *"a number written
out by hand goes stale in silence, and a stale number inside a prompt is
indistinguishable, to whoever reads the output, from a lie."* The constraint prompt
was fixed this way; the record block and the angle-2 prompt were not.

**7.3 Volume reads as depth.** 3,424 reviews is 511 conversations, and 1,051 of
those records carry `pass_index` 2 — repeat passes over already-exhausted topics,
which the script itself labels "compliance volume, not new analysis." The corpus's own `day_trades` review noticed the shape of this
from the inside: a 24-hour ledger showing 1 entry, 21 spread assessments, 21 news
assessments — and **340 deep reviews**. The review layer generated an order of
magnitude more events than the agent it was reviewing. Counting rows overstates the
evidence by roughly 7×; counting conversations is the honest denominator.

---

## 8. Predictions that can now be scored

Round 4 asked for falsifiable predictions. Phase I has closed, so some can be
checked against `fills/`.

**Falsified.** A 2026-08-15 `stop_geometry` review predicted, as the claim it was
most confident in and the one whose failure would "kill my position fastest":
*"the next 20 trades will produce net P&L in [−3.0, +1.5] USDT, central estimate
−0.75. The book will not be net profitable after fees."* The final two rolling
windows recorded net **+24.42** (08-19) and **+28.59** (08-20), on win rates of 0.75
and 0.80. The prediction's own stated falsifier — net > +2.0 — was tripped
decisively. The reviewer named the correct consequence: if this fails, *"my entire
'fee donor' framework is wrong."*

**Not resolvable.** Most round-4 predictions were specified over "the next 20 round
trips." Phase I closed with 29 closed round trips *in total*; only ~6 closed after
08-15. The horizon the predictions were written against never arrived. This is worth
noting as a design point: asking for predictions over 20 trades from a book doing
roughly 4 per week guarantees most of them expire unscored.

**Directionally wrong.** The pessimistic consensus of the later reviews — thin
alpha, fees eating the edge, structurally non-viable at current cadence — is not
what the last week of Phase I recorded. Two caveats keep this from being a verdict:
the rolling windows are ~7 days and overlap, so +28.59 is not 29 trades' worth of
independent evidence; and a good final week is exactly the kind of small-sample
result the corpus spent 3,424 reviews correctly warning against. The reviewers'
epistemics were better than their forecast. Both facts should be recorded.

---

## 9. What to measure, in order

Ordered by information gained per unit of effort. Every item uses data already held.

1. **Venue and ledger state around the 6.75σ stop timestamp.** One lookup. Decides
   whether the stop sample is n=5 or n=3, and whether the tail debate has a subject.
2. **Refit count per open trade, and Δμ against entry-time μ over each hold.**
   Decides whether rank 1 is systematic or rare. One ledger pass.
3. **The gate-audit table** — candidates evaluated, rejections per filter, survivor
   margins, pre/post-refit pass rates. The only thing that separates a dead market
   from a mis-firing gate (rank 5). Requires gate instrumentation, not just the
   event log.
4. **The FDR family definition, written down.** Then whether overlapping-window
   tests on the same pair are being treated as independent (rank 6). Desk check.
5. **Signal z at decision versus realised z at fill,** per trade (rank 8). One join.
6. **Realised versus fitted half-life on post-entry paths.** Requested in 42
   conversations, the most-asked measurement in the corpus. Note it was largely
   asked in service of explaining the false 2.0h premise — but it is worth running
   anyway, now against the true median hold of 8.0h.

And one repair, outside the measurement list: **the angle-2 prompt at
`ai_deep_review.py:397` and `RECORD_FALLBACK` still contain the 2.0h figure.** Any
future review run will reproduce the artefact described in §3. This synthesis does
not modify code; flagging it so the next run does not inherit it.

---

## 10. Provenance

- **Source:** `track_record/phase1_submission/ai_deep_review.jsonl.gz`, 3,424
  records, 2026-08-12 → 2026-08-21, all `MiniMax-M3`.
- **Structure recovered from:** `deploy/ai_deep_review.py` at the current checkout,
  plus `git log` on that file to date the constraint-prompt fix (`eef2526`,
  2026-08-12 19:27:29 UTC).
- **Ground truth for §3 and §8:** the 19 daily snapshots in
  `track_record/phase1_submission/fills/`. These are the project's own records; no
  external data was used.
- **Conversations reconstructed** by grouping consecutive records on
  (topic, pass_index) with monotonically increasing round: 511 conversations, 483
  complete.
- **Excluded from all conclusions:** 486 round-5 records and 114 inherited
  round-6/7 records. Working corpus 2,824.
- **Method:** structural analysis and ground-truth checks are exact. Prevalence
  percentages come from regex classifiers over review text and are *indicative, not
  precise* — they undercount paraphrase and occasionally miscount negation. They are
  used here to rank and to detect splits, never as the sole support for a claim.
  Every claim in §6 was read in full in at least one primary review.
- **Reading depth:** all six strategy topics read end-to-end across complete
  conversations; pair topics sampled and classified in aggregate.

*Nothing in this document modifies the strategy, the agent, or any other file.*
