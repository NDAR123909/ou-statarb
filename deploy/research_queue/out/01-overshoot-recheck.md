# 01 — Recheck of the −10.67 overshoot cost

**Status: the number is arithmetically correct and reproduces exactly. It is
also stale, mislabelled in one respect, and — the part that decides the
monitor — it is an upper bound whose recoverable fraction the logs cannot
measure.**

Audit date 2026-09-09. Recomputed from `track_record/phase1_submission/`
(`reasoning.jsonl`, 1,271 records; `fills/*.json`, 19 snapshots). No figure
below is taken from prose; every one is recomputed or reproduced from a tool
run against the archived ledger. This is evidence for a human decision, not a
recommendation to act.

---

## Summary of answers

| Question | Answer |
|---|---|
| 1. How many stops? | **Eight.** Five is the count as of 2026-08-02, the day the claim was written. Nothing was excluded; the figure was frozen and never recomputed. |
| 2. Recomputed cost | **−10.67 reproduces exactly** on those five. On all eight it is **−18.71**. |
| 3. The 6.75σ exit | **A genuine structural-break stop.** Not a spike, not a fill anomaly, not a gap in the records. Verified three independent ways. |
| 4. Concentration | Within the five, **one event is 44%** and two are 78%. Across all eight, the largest is **25%** and the top two 46%. |
| 5. Recoverable fraction | **Not measurable.** Bounded above at **−6.30 of −10.67 (59%)** and −9.07 of −18.71 (48%). The lower bound is **zero**. N = 5/15/30 min cannot be distinguished from these records. |
| 6. What the logs cannot say | The intra-bar path — for every stop, at every cadence. This is the binding gap. |

---

## Method, stated before the numbers

**The definition.** I used the one already implemented in
`deploy/stop_analysis.py`, which is also the definition the PROMPT proposes:

- `pnl` — P&L from the decision-time prices at each end of the trade,
  `side · qa·(pa₁−pa₀) − side · qb·(pb₁−pb₀)`, from the `enter` and `stop`
  records.
- `rate_per_z = pnl / (z_stop − z_entry)` — P&L per unit of z, taken from each
  trade's own two readings. P&L is linear in z because position value moves as
  `g · σ · dz`.
- `loss_at_band = rate_per_z · (±3.5 − z_entry)` — what stopping exactly at the
  band would have cost.
- **`overshoot_cost = pnl − loss_at_band`** — the money the hourly sampling
  interval cost on that trade.

**Why I did not redefine it.** The claim under test was produced by this
definition, so reproducing it is the only way to tell a wrong number from a
stale one. Where the definition itself is load-bearing I say so below
(§ "Three ways this definition can mislead").

**Reproduction.** Running the untouched tool against the archived ledger:

```
python deploy/stop_analysis.py \
  --ledger track_record/phase1_submission/reasoning.jsonl --stop-z 3.5
```

I then reimplemented the same arithmetic independently and got the same
numbers to the cent, and added the 4.0σ counterfactual the tool does not
compute.

**Basis.** Decision prices, not fills — that is what the original used, and it
is the only basis available for all eight stops (see the retention gap in §6).
Fills are used as an independent cross-check where they exist.

---

## 1. How many stops — reconciling `stop: 8` against "five"

**Eight stops, all live.** Every one carries `dry: false`. There is no
dry-run exclusion, no filtered subset, and no missing rationale.

The five are simply **the stops that existed on 2026-08-02**, the date the
decision was opened. Sorted by time, the split is clean:

| # | Stop | In the −10.67? |
|---|---|---|
| 1 | ETC/KAS 2026-07-20 07:00 | yes |
| 2 | TAO/RENDER 2026-07-21 01:00 | yes |
| 3 | TAO/RENDER 2026-07-26 20:00 | yes |
| 4 | AVAX/SOL 2026-08-01 19:00 | yes |
| 5 | AVAX/SOL 2026-08-02 18:00 | yes |
| 6 | XLM/XRP 2026-08-11 07:00 | **no — after the cut** |
| 7 | KAS/ETC 2026-08-20 02:00 | **no — after the cut** |
| 8 | ETC/KAS 2026-08-21 10:00 | **no — after the cut** |

**So the counts do not disagree and nothing was excluded for an unwritten
reason.** The number was correct when written and was carried forward through
the 2026-08-09 and 2026-08-16 reviews without recomputation, while three more
stops accumulated. The doubt on record is answered, and the answer is the less
interesting of the two possibilities: not a filtering error, a staleness error.

**One correction to the claim as stated in this queue file.** It reads
"−8.31 is attributed to a single trade." That is not what the source says.
`WEEKLY_REVIEW.md` line 821 says *"two events account for −8.31 of the −10.67"*
— and it is right. −8.31 is the sum of the **two** largest contributors:

    AVAX/SOL 2026-08-01  (6.75σ over)  −4.7153
    ETC/KAS  2026-07-20  (1.08σ over)  −3.5863
                                       ────────
                                       −8.3015  ≈ −8.31

Worth fixing in the queue file, because "one trade carries −8.31" and "two do"
lead to different reads of the concentration question in §4.

---

## 2. The recomputed cost — per-stop working table

Band ±3.50. `over` = σ past the band before the stop actually fired. `dec P&L`
= decision-price P&L. `@3.5` = counterfactual loss stopping exactly at the
band. `cost` = the overshoot cost. `@4.0` and `recov` are mine, not the
original tool's: the counterfactual at the proposed monitor's lower tier, and
the most a 4.0σ monitor could possibly recover. `z_prev` is the last logged z
strictly before the stop bar, and `gap` the hours since it.

| # | pair | stop | entry z | stop z | over | dec P&L | @3.5 | **cost** | @4.0 | recov ceiling | z_prev | gap | ever >4.0σ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ETC/KAS | 07-20 07:00 | −3.31 | −4.58 | 1.08 | −4.22 | −0.63 | **−3.59** | −2.29 | −1.93 | −3.31 | 1.7h | yes |
| 2 | TAO/RENDER | 07-21 01:00 | −3.02 | −3.70 | 0.20 | −3.89 | −2.72 | **−1.16** | — | 0 | −3.02 | 4.0h | no |
| 3 | TAO/RENDER | 07-26 20:00 | 3.08 | 3.65 | 0.15 | −2.42 | −1.77 | **−0.65** | — | 0 | 3.08 | 2.0h | no |
| 4 | AVAX/SOL | 08-01 19:00 | −1.39 | −10.25 | 6.75 | −6.19 | −1.48 | **−4.72** | −1.83 | −4.37 | −2.70 | 1.0h | yes |
| 5 | AVAX/SOL | 08-02 18:00 | 1.74 | 3.63 | 0.13 | −8.18 | −7.62 | **−0.55** | — | 0 | 3.03 | 1.0h | no |
| | | | | | | | **five-stop total** | **−10.67** | | −6.30 | | | |
| 6 | XLM/XRP | 08-11 07:00 | 2.33 | 3.69 | 0.19 | −4.93 | −4.25 | **−0.68** | — | 0 | 3.11 | 1.0h | no |
| 7 | KAS/ETC | 08-20 02:00 | −1.37 | −4.75 | 1.25 | −9.51 | −5.99 | **−3.52** | −7.39 | −2.11 | −3.18 | 1.0h | yes ⚠ |
| 8 | ETC/KAS | 08-21 10:00 | 1.19 | 4.10 | 0.60 | −18.52 | −14.67 | **−3.84** | −17.86 | −0.66 | 2.79 | 1.0h | yes |
| | | | | | | | **eight-stop total** | **−18.71** | | **−9.07** | | | |

⚠ row 7 is frame-corrupted — see §3b.

Exact values, so the arithmetic can be rechecked without re-running anything:
−3.5863, −1.1630, −0.6504, −4.7153, −0.5532 (sum **−10.6682**), then −0.6795,
−3.5214, −3.8435 (eight-stop sum **−18.7126**).

**Median overshoot: 0.20σ over the five, 0.40σ over all eight.** Four of the
eight fired within 0.5σ of the band; three fired more than 1σ past it.

**Cross-checks.** Decision-price P&L is corroborated independently:

| stop | decision P&L | venue fill (gross) | NAV delta | verdict |
|---|---|---|---|---|
| ETC/KAS 07-20 | −4.22 | *aged out* | −4.33 | agrees |
| TAO/RENDER 07-21 | −3.89 | *aged out* | −4.07 | agrees |
| TAO/RENDER 07-26 | −2.42 | *aged out* | −2.48 | agrees |
| AVAX/SOL 08-01 | −6.19 | **−6.20** | +3.13 † | agrees with fills |
| AVAX/SOL 08-02 | −8.18 | −9.69 | −8.72 | fills 1.5 worse |
| XLM/XRP 08-11 | −4.93 | −5.61 | −5.84 | fills 0.7 worse |
| KAS/ETC 08-20 | −9.51 | −9.35 | −9.63 | agrees |
| ETC/KAS 08-21 | −18.52 | *no snapshot* | −18.56 | agrees with NAV |

† NAV moved on other open positions in that window, so the NAV check is not
clean for that row; the fills check is, and it agrees to one cent.

Where fills exist and differ, they are **worse** than decision prices. So
−10.67 and −18.71, computed on decision prices, are if anything mild
underestimates of realised overshoot — not inflated ones.

**The "roughly a third of all losses" half of the claim.** Recomputed over the
full phase: all identified losses at decision prices total **−64.69** across 31
closed trades (stops −57.85, refit-drops −2.72, losing reversions −4.12). So:

- −10.67 against the full-phase loss base is **16%**, not a third.
- −18.71 against the same base is **29%** — which is "roughly a third".

The proportional claim survives, but only when numerator and denominator are
updated together. Quoted as "−10.67 ≈ a third of all losses" it is now wrong at
both ends: the numerator is 75% understated and the denominator has doubled.

---

## 3. The 6.75σ exit — genuine, and the σ scale is what makes it look impossible

**Verdict: a real structural break in the AVAX/SOL relationship. Not a data
spike, not a fill anomaly, not a gap.** Four independent checks, all agreeing:

**a. The venue's own money matches the ledger's arithmetic to one cent.**
Decision-price P&L −6.19; fills snapshot gross −6.20; the venue's per-leg
`rpnl` sums to −8.832 + 2.632 = **−6.20**. A z reading corrupted by a data
error would not produce a P&L that reconciles with the exchange's own realised
figure.

**b. Execution was ordinary.** Slippage on the four legs was
0.87 / 0.0 / −2.74 / 1.73 bps; fees 0.105 USDT. Nothing resembling a bad fill.

**c. The move persisted.** z went −10.245 (19:00) → −9.547 (20:00) → −8.911
(21:00). A one-print spike snaps back on the next bar. This did not; it decayed
slowly, which is what a broken relationship looks like.

**d. The magnitude is ordinary once converted out of σ.** Using the entry
record (β = 0.4915) and the two decision prints, the implied σ_eq for this pair
is **35.4 bps of log-spread**. So:

- the 7.55σ single-bar move = **2.7% of relative price** between AVAX and SOL;
- the full 10.25σ excursion = **3.6%**.

A 2.7% one-hour divergence between two large-cap alts, on 2026-08-01 in the
middle of the referenced 07-31/08-01 sell-off, is unremarkable. **The "6.75σ"
framing makes the event sound impossible only because σ_eq is tiny** — it is
fitted on a quiet cointegration residual, and when the relationship breaks the
natural volatility scale is an order of magnitude larger. The event needs no
exotic explanation and the sample is **n=8, not n=3**. The doubt raised in the
deep-review synthesis is answered, and answered against the synthesis.

Two supporting details. The agent's own contemporaneous assessment at 19:00
called it *"a discontinuous break in the AVAX/SOL cointegration relationship"*
and at 20:00 *"a ~7.5 sigma jump… in a single hour with no intermediate
oscillation."* That is a characterisation from the same hourly data, so it is
not independent evidence about the intra-bar path — but it is the operator's
contemporaneous read and it points the same way. Separately, the only other
pair under assessment that hour (FIL/AR) was calm throughout — z 0.33 → 0.10 →
0.09 — so this was pair-specific, not a market-wide print failure.

### 3b. A different exit *is* corrupted — KAS/ETC 2026-08-20

This one was not on the queue's list of doubts and it should have been.

    z                        −4.752      (refitted frame)
    z_in_entry_coords        +3.597
    mu_shift_sigma            6.443
    equilibrium_reestimated   true

**One refit fired during this trade's 8-hour hold** — the only stop in the
phase for which that is true (checked against all 35 `refit` events). The
equilibrium moved 6.44σ while the position was open. `stop_analysis` computes
`rate_per_z = pnl / (z_stop − z_entry)` using the refitted-frame z against the
entry-frame entry z, so both the rate and the counterfactual mix two coordinate
systems.

Measured in the frame the trade was entered in, the excursion was **3.597σ — an
overshoot of 0.097σ**, i.e. the band was honoured almost exactly. Measured in
the refitted frame it reads 1.25σ past. **The same stop is either a 13×
overshoot or essentially none, depending on which logged number you use**, and
the ledger does not document the convention for `z_in_entry_coords` — its sign
is also inconsistent with the entry-frame reading for a long position, which I
cannot resolve from the records.

Consequence: row 7's **−3.52 should be treated as an upper bound with a
plausible floor near zero**, and its −2.11 recovery ceiling likewise. The
eight-stop total is therefore better stated as **−18.71, of which up to −3.5 is
frame artefact rather than sampling cost.**

**This does not touch the −10.67.** I checked every one of the five: **zero
refits fired during any of their holds**, so μ cannot have been re-estimated
mid-trade and their raw z readings are in the entry frame. The frame risk is
real, it is now demonstrated, and it is confined to a stop that is not in the
claim under test.

---

## 4. Concentration

Overshoot cost is one event wearing a plural, and less so once the record is
complete.

| Basis | Total | Largest single | Top two |
|---|---|---|---|
| The five (as claimed) | −10.67 | −4.72 = **44%** | −8.30 = **78%** |
| All eight | −18.71 | −4.72 = **25%** | −8.56 = **46%** |

Within the five, four fifths of the cost is two trades and nearly half is one.
The three later stops dilute this substantially — the concentration argument is
noticeably weaker on the full record than on the frozen one.

More decisive than the money: **four of the eight stops never reached 4.0σ at
all** (rows 2, 3, 5, 6 — exits at 3.70, 3.65, 3.63, 3.69). Their combined
−3.04 of overshoot cost is unreachable by a 4.0–4.5σ monitor **by construction,
at any cadence, however fast**. Within the five, that is −2.36 of the −10.67
excluded before any timing question is even asked.

---

## 5. THE DECIDING QUESTION — what a 4.0–4.5σ monitor could actually recover

### The ceiling

Assuming the monitor fires the instant z touches 4.0, with zero latency, zero
slippage, and P&L linear in z — every assumption favourable:

| Basis | Overshoot cost | Recovery ceiling | Ceiling as % |
|---|---|---|---|
| The five (the −10.67) | −10.67 | **−6.30** | **59%** |
| All eight | −18.71 | **−9.07** | **48%** |
| All eight, discounting the corrupted row 7 | −18.71 | −6.96 | 37% |

**−10.67 is not the prize. −6.30 is the ceiling on the prize**, and 69% of that
ceiling (−4.37) sits in the single AVAX/SOL event.

### The recoverable fraction at N = 5, 15, 30 minutes: not measurable

For **every one of the eight stops**, the last logged z before the stop bar was
inside the band (−3.31, −3.02, +3.08, −2.70, +3.03, +3.11, −3.18, +2.79). In
each case the crossing of 3.5 — and of 4.0 where it happened at all — occurred
**inside a single sampling interval with no intermediate observation**.

The ledger's z is strictly hourly: of 607 z readings, all but a handful are
stamped at minute :00 or :01, and the off-cycle ones are entry/exit decisions,
not extra samples. `ai_spread_assessment` records carry no prices, only z. There
is no sub-hourly price or z series anywhere in the repository.

**So N = 5, 15 and 30 minutes all produce the same answer from these records:
unknown, bounded above by the table in §5.1 and below by zero.** If a crossing
was a single print, the monitor recovers nothing there however fast it runs.

### What it would take, stated as an assumption and not as a finding

To show the shape of the dependence — **this is a counterfactual under an
assumption the records cannot support, not a measurement**:

*If* z moved linearly in time within the bar, and a monitor sampling every N
minutes fired on average N/2 after the crossing:

| | ceiling | N=5 min | N=15 min | N=30 min |
|---|---|---|---|---|
| The five | −6.30 | −5.98 (56%) | −5.33 (50%) | −4.37 (41%) |
| All eight | −9.07 | −8.22 (44%) | −6.90 (37%) | −5.38 (29%) |

Linear-in-time is the assumption **most** favourable to the monitor — it is the
slowest path from below-band to the exit level. The opposite extreme, a jump,
returns zero at every cadence. The AVAX/SOL event that carries most of the
prize is the one the operator's own contemporaneous note describes as
discontinuous, which if taken at face value moves that −4.37 toward the zero
end. **The true value lies somewhere in [0, −6.30] and these records cannot
locate it within that range.**

Note also that the cadences differ by only 15 percentage points across a 6×
change in N. Under this assumption the monitor's value is far more sensitive to
*whether the move was continuous* than to how fast it is polled — which is
another way of saying the unmeasured variable dominates the design choice.

---

## 6. What these records cannot tell you

Stated plainly, because these are the instrumentation gaps, and one of them is
the whole answer.

1. **The intra-bar path, for every stop.** No sub-hourly z, no sub-hourly
   prices, no tick or minute data anywhere in the repo. This is the binding
   gap: it makes the recoverable fraction — the actual decision variable —
   unmeasurable at any cadence.
2. **Whether μ was re-estimated during the five stops in the claim.** The
   `mu_shift_sigma` / `z_in_entry_coords` / `equilibrium_reestimated` fields
   first appear on **2026-08-09T23:00**, after all five. I substituted a proxy —
   refit events during each hold, which is recoverable — and it clears all five.
   But the direct check is not available for exactly the stops that matter.
3. **The `z_in_entry_coords` convention.** Undocumented, and for KAS/ETC
   2026-08-20 its sign is inconsistent with the entry-frame reading for a long
   position. That stop's cost cannot be pinned down in either frame.
4. **Realised P&L for the three July stops.** The venue serves ~7 days of
   executions and the earliest snapshot is 2026-08-02, so rows 1–3 have
   `gross_pnl: null` in fills. Their decision-price P&L is corroborated only by
   NAV deltas (which agree to within 0.2). Three of the five stops in the claim
   have **no venue-verified P&L at all**.
5. **Realised P&L for the final stop.** ETC/KAS 2026-08-21 closed after the last
   snapshot (2026-08-20). Its −18.52 — the largest single decision-price loss of
   the phase — rests on the ledger and a NAV delta (−18.56), never on a
   reconciled fill.
6. **Whether P&L is actually linear in z over a 10σ excursion.** The whole
   counterfactual method rests on it. It is a good approximation near the band
   and an untested extrapolation at −10.25σ, where it sets the largest single
   number in the table.

### Three ways this definition can mislead, independent of the arithmetic

- **It prices only the sampling interval, not the decision.** `@3.5` assumes a
  fill exactly at the band with no slippage. A monitor firing into the move that
  produced 2.7% in an hour would not fill at the band, so the realised recovery
  would be smaller than any figure above.
- **It is silent on false positives.** Every number here is the benefit side.
  The proposed monitor is read-only and may only close or stop — but four of
  eight stops already fired below 4.0σ and reverted, and XLM/XRP 08-11 kept
  running to 4.40σ after its stop, so the tier would also close positions the
  hourly rule currently lets breathe. No cost is estimated anywhere in this file
  and none is derivable from these records.
- **The tool's own verdict has flipped.** Run on the five stops it printed
  *"stops fire LATE → the sampling interval is the defect."* Run on all eight it
  prints: **"stops fire at the band and the spread does NOT always revert → the
  stop is doing its job; leave it alone."** Same code, same threshold, three more
  observations.

---

## Bottom line

The −10.67 is not wrong: it reproduces to the cent from the primary ledger under
the definition that produced it, and the 6.75σ exit that carries 44% of it is a
genuine structural break — verified against the venue's own realised P&L,
ordinary slippage, a slow post-stop decay, and a σ_eq of 35 bps that makes the
move a 2.7% price divergence rather than a statistical impossibility, so the
sample is eight and not three. What the number is, is **stale and
mis-framed**: five stops became eight, the cost became −18.71, the "third of all
losses" became 16% on the old numerator and 29% on the updated one, and the same
tool run on the complete record now prints the opposite verdict — *the stop is
doing its job; leave it alone*. Against the monitor specifically the case is
weaker still, because −10.67 was never the prize: four of eight stops never
reached the 4.0σ tier and are unrecoverable by construction, the ceiling on what
a perfect zero-latency monitor could have saved is **−6.30 of the −10.67 (59%)**
or −9.07 of −18.71 (48%), and 69% of that ceiling sits in one event that the
operator's own contemporaneous note calls discontinuous. **The honest answer to
"at what cadence" is that these records cannot say** — every stop crossed the
band inside a single unobserved interval, the ledger holds nothing finer than
hourly z, and the recoverable fraction is bounded only by [0, −6.30]. That is
the third outcome the queue file anticipated, and it names the next thing to
build: **the case for the intra-bar monitor cannot be closed either way on this
evidence, and the instrumentation — sub-hourly z capture on open positions, plus
the frame fields that only began logging on 2026-08-09 — is what has to come
first.** One 90-minute logging change would answer at the next stop what a month
of re-reading this ledger cannot.

---

## Provenance

- `track_record/phase1_submission/reasoning.jsonl` — 1,271 records; 8 `stop`,
  19 `exit`, 38 `enter`, 4 `refit_drop`, 35 `refit`.
- `track_record/phase1_submission/fills/*.json` — 19 daily snapshots,
  2026-08-02 → 2026-08-20; 7 of the 8 stops appear, 4 with realised P&L.
- Reproduction: `deploy/stop_analysis.py --ledger
  track_record/phase1_submission/reasoning.jsonl --stop-z 3.5`, unmodified.
  `--stop-z` is passed explicitly only to avoid importing `AgentConfig`, which
  pulls in `statsmodels` (not installed here); 3.5 is that config's value.
- The `@4.0` counterfactual, the recovery ceilings, the refit-during-hold check,
  the σ_eq derivation and the cadence sensitivity are mine, computed
  independently of the tool; the tool's own columns were reproduced to the cent
  before adding them.
- **Measured** — all costs, overshoots, totals, concentrations, ceilings,
  cross-checks, refit counts, σ_eq. **Assumed** — the linear-in-time table in §5
  and the N/2 firing delay, both labelled in place. **Not knowable from these
  records** — everything in §6.

*Created: this file only. No other file was modified.*
