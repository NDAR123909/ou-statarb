# 03 — What has frame drift actually cost?

**Answer in one line: on the instrumented record, mislabelling cost nothing and
frame drift cost one stop. The sample is nine closes and two drift events, which
is not enough to act on — and the anchor case this task was handed does not
survive a check against the primary prices.**

Audit date 2026-09-09. Recomputed from `track_record/phase1_submission/`
(`reasoning.jsonl`, 1,271 records; `fills/*.json`, 19 snapshots) and the
`entry_frame()` implementation at `deploy/ltp_agent.py:357–385`. No figure is
taken from prose — including, as instructed, the worked example in
`LTP_STRATEGY.md` and the one in this task's own brief. This is evidence for a
human decision, not a recommendation to act.

---

## Summary of answers

| Question | Answer |
|---|---|
| 1. Coverage | **9 of 27** closes instrumented (6 exits, 3 stops); 18 predate 2026-08-06. Everything below is that subset of 9. |
| 2a. μ movement | **7 of 9 have `mu_shift_sigma` exactly 0.0** — the frame never moved. 2 are material: −0.611σ and +6.443σ. Direction: one toward, one away. **No systematic bias detectable at n=2.** |
| 2b. σ movement | σ moves only when μ moves (same refit). Ratios **0.947** and **2.047** — the second is σ roughly **doubling**, not the 40% collapse this brief states. |
| 3. Re-labelling | **Zero exits change label.** All six survive re-derivation in the entry frame. The mislabelling cost is nil on this sample. |
| 4. Re-timing | **1 of 3 stops** would not have fired in the entry frame — KAS/ETC 2026-08-20. It is the only one. |
| 5. Cost | (a) P&L: one stop, **−9.66 realised**, against a counterfactual near **+14.5**. (b) Mislabelling: **zero**. MDD channel: **untouched**. |
| 6. Design bar | Stated below. **Not reached in either direction.** |
| 7. Limits | n=2 drift events, 12 days, 3 pairs, one regime. "Not enough data" is the honest read. |

---

## 0. A correction to this task's brief, established before anything else

This task supplied the KAS/ETC 2026-08-20 stop as a solved anchor case and said
not to re-derive it. I did not re-derive the *convention* — the code at
`ltp_agent.py:375–381` confirms it exactly as stated, and my task-01 note
calling it undocumented was wrong. But the brief also asserts the three logged
numbers are "fully consistent" and that **σ collapsed 40%**, and the instruction
was to work from primary records. That check fails.

The brief's derivation uses only the three logged fields against each other. It
never brings in the entry z or the two price prints. When those are added:

```
epoch frame for KAS/ETC (beta 0.9721173236), recovered from the two
clean closes in the same refit epoch (08-19 09:00 and 08-19 16:00,
both mu_shift = 0 so entry frame == live frame):

    sigma0 = 0.01085687        mu0 = -5.42792565
    (both closes give identical values to 8 dp)

independent check — the 08-19 18:00 entry, not used in the fit:
    (s0 - mu0)/sigma0 = -1.3719   vs logged entry z  -1.3719   ✓
```

That frame is therefore correct. Now apply it at the stop:

```
log-spread at entry  s0 = -5.44282001
log-spread at stop   s1 = -5.46357217      delta = -0.02075216  (spread FELL)
position is side = +1, LONG the spread — a fall is adverse ✓ (realised -9.66)

TRUE   z_in_entry_coords = (s1 - mu0)/sigma0 = -3.2833
LOGGED z_in_entry_coords =                     +3.5970
```

**The logged value has the wrong sign, and it cannot be rescued by any choice of
parameters.** At the stop the spread sits *below* any plausible entry-frame
equilibrium for this pair — it entered below the mean at z=−1.37 and then fell
further — so `(s − μ₀)` is negative and `z_in_entry_coords = (s − μ₀)/σ₀` must be
negative for any positive σ₀. A positive value is impossible, not merely
unlikely. Reconstructing σ₀ from the logged +3.597 returns **σ₀ = −0.004176**,
which is what an impossible value looks like.

Two consequences.

**The σ direction reverses.** Taking `mu_shift_sigma = +6.443` and the live z as
logged, against the price-anchored frame:

```
mu_live    = mu0 + 6.443*sigma0 = -5.35797711   (mu moved UP by +0.0699
                                                 while the spread fell — AWAY
                                                 from the long position)
sigma_live = (s1 - mu_live)/z   =  0.02222197
sigma_live / sigma0             =  2.047        (sigma roughly DOUBLED)
```

The brief says σ collapsed 40% and that the tightening amplified the residual.
The mechanism actually runs the other way: **μ moving away tripled the raw
deviation** (−0.0356 → −0.1056 in log-spread), and **σ doubling halved it back**,
for a net ≈1.45× inflation of |z|. Same event, opposite attribution. The brief
was right that σ drift matters as much as μ drift and right that the two must be
reported separately — it had the sign of this instance backwards.

**The operational conclusion is unaffected.** −3.2833 is inside the ±3.5 band, so
the stop does not fire in the entry frame under the corrected value either. The
brief's headline finding survives; its supporting number does not. I use −3.2833
throughout and flag where it matters.

I cannot say from the ledger *why* the field is wrong. `entry_mu` and
`entry_sigma` are not logged, only quantities derived from them, so whether the
fault is a stale snapshot, a sign error, or the wrong `spread` argument is not
recoverable from these records. It is the only such case in the nine.

---

## 1. Coverage

`entry_frame()` shipped 2026-08-06. Across the phase:

| | count |
|---|---|
| `exit` + `stop` records, all time | **27** |
| carrying the frame fields | **9** (6 exits, 3 stops) |
| predating the instrumentation | **18** (13 exits, 5 stops) |

**Coverage is 33%.** The instrumented window is 2026-08-09 23:00 → 2026-08-21
10:00 — twelve days, three pairs (FIL/AR, XLM/XRP, KAS/ETC ∪ ETC/KAS). Every
figure from here on is over those nine closes and nothing else. The July record,
the whole AVAX/SOL era, and the 6.75σ stop of 2026-08-01 are all uninstrumented
and cannot be assessed for frame drift at all.

---

## 2. How far the frame moves

### 2a. μ

| `mu_shift_sigma` | closes |
|---|---|
| exactly 0.000 | **7** |
| ≥ 0.10 (the `MU_SHIFT_MATERIAL` threshold) | **2** |
| between 0 and 0.10 | 0 |

The distribution is not a distribution. It is a point mass at zero and two
outliers: **−0.611σ** (FIL/AR) and **+6.443σ** (KAS/ETC). Nothing lands in
between, which the mechanism explains — μ changes only at a refit, so a hold
either spans one or it does not:

| pair | close | hold | refits in hold | `mu_shift_sigma` |
|---|---|---|---|---|
| FIL/AR | 08-09 23:00 | 26.0h | **1** | −0.611 |
| XLM/XRP | 08-11 07:00 | 11.0h | 0 | 0.000 |
| KAS/ETC | 08-18 04:00 | 9.0h | 0 | 0.000 |
| KAS/ETC | 08-19 09:00 | 8.0h | 0 | 0.000 |
| KAS/ETC | 08-19 16:00 | 6.0h | 0 | 0.000 |
| KAS/ETC | 08-20 02:00 | 8.0h | **1** | +6.443 |
| KAS/ETC | 08-20 16:00 | 5.0h | 0 | 0.000 |
| ETC/KAS | 08-21 03:00 | 5.0h | 0 | 0.000 |
| ETC/KAS | 08-21 10:00 | 5.0h | 0 | 0.000 |

Exactly the two holds that spanned a refit are the two that drifted. **Exposure
is a function of hold length**: refits run roughly daily (35 over ~33 days) and
instrumented holds are 5–26h, so most positions close before the frame can move.
Two of nine, 22%, matches that base rate.

**Direction: no systematic bias.** One case moved the equilibrium *toward* the
position and one *away*:

- **FIL/AR** — short spread entered at z=+1.240. μ moved −0.611σ, following the
  falling spread down, i.e. **toward** the position. Effect: live z (−0.058) sat
  closer to the exit threshold than entry-frame z (−0.665). The drift made the
  position look *less* reverted than it actually was.
- **KAS/ETC** — long spread entered at z=−1.372. μ moved +6.443σ **up** while the
  spread fell, i.e. **away** from the position, inflating |z| and firing a stop.

One each way, from a sample of two. **Treating this as a one-directional μ bias
would not be supported by these records.** The brief's instruction to call it
frame drift rather than μ bias is borne out.

### 2b. σ

σ has no logged field. Recovered as the brief describes, from the two z readings
plus the price-anchored frame:

| close | σ_live/σ₀ | effect |
|---|---|---|
| the 7 zero-drift closes | **1.000 exactly** | `z_in_entry_coords` equals `z` bit-for-bit |
| FIL/AR 08-09 | **0.947** | −5%, negligible against a 0.61σ μ move |
| KAS/ETC 08-20 | **2.047** | σ doubled — see §0 |

σ drift is not an independent hazard here: it occurs only when μ drift occurs,
because both are recomputed by the same refit. Where it does occur it is not
second-order — in the KAS/ETC case the σ term offsets roughly half the μ term,
so a conclusion attributing the whole 1.45× inflation to μ would have the wrong
mechanism with a roughly right total, exactly as the brief warned. Note this cuts
the opposite way from the brief's own reading: σ moved *against* the drift, not
with it.

FIL/AR's fields are self-consistent and yield a positive, plausible σ₀ (0.008432,
in line with the 0.0065–0.0153 range seen across pairs), but it is the only
instrumented close in its refit epoch, so unlike KAS/ETC it has **no independent
cross-check**. I report it as consistent, not as verified.

---

## 3. Re-labelling the exits

The exit rule is directional, not absolute (`ltp_agent.py:1010`):

```python
reverted = (side > 0 and z >= -exit_z) or (side < 0 and z <= exit_z)
```

`exit_z` was 0.00 for every instrumented close (confirmed from the `bands` in the
governing `refit` record, and echoed in each reasoning line as "< 0.00"). Applying
the identical test to `z_in_entry_coords`:

| # | pair | close | side | live z | entry-frame z | reported | in entry frame | changed? |
|---|---|---|---|---|---|---|---|---|
| 1 | FIL/AR | 08-09 23:00 | −1 | −0.0579 | −0.6654 | reverted | reverted | no |
| 3 | KAS/ETC | 08-18 04:00 | +1 | +0.1989 | +0.1989 | reverted | reverted | no |
| 4 | KAS/ETC | 08-19 09:00 | +1 | +1.8951 | +1.8951 | reverted | reverted | no |
| 5 | KAS/ETC | 08-19 16:00 | −1 | −0.3210 | −0.3210 | reverted | reverted | no |
| 7 | KAS/ETC | 08-20 16:00 | −1 | −1.5258 | −1.5258 | reverted | reverted | no |
| 8 | ETC/KAS | 08-21 03:00 | −1 | −0.0475 | −0.0475 | reverted | reverted | no |

**Corrected exit-reason tally, beside the reported one:**

| reason | reported | corrected |
|---|---|---|
| reverted | 6 | **6** |
| would not have been an exit | — | **0** |

**No exit in the instrumented record was a loss dressed up by a moving target.**
Five could not have been — their frames never moved. The sixth (FIL/AR) had a
real −0.611σ μ move, and it still clears the exit test in its own entry frame:
a short spread at entry-frame z=−0.665 is past the z≤0 threshold, more decisively
than the live −0.058 was. It was also a **winner** (+6.03 net on fills), not a
loss. The honesty question comes back clean on this sample.

**One defect found, in the conservative direction.** `reversion_note()`
(`ltp_agent.py:388–400`) fired on FIL/AR and wrote into the permanent record:

> *"in the entry's own coordinates the spread is at z=-0.67, **not inside
> ±0.00**. The reversion is partly the target moving, not only the spread
> returning."*

The "inside ±exit_z" framing is the old absolute-value test that the exit rule
itself abandoned — and with `exit_z = 0`, `abs(z) < 0` is never true, so the note
will always report *any* entry-frame z as "not inside". Under the rule actually
in force, z=−0.67 on a short is a valid exit. **The note over-flags: it accuses
the only exit it examined of something the exit rule would not.** That is the
safe direction for an honesty check to fail in, but it means the flag cannot be
read as evidence of mislabelling, and the one place the record confesses to frame
drift is a place where the label was in fact sound.

---

## 4. Re-timing the stops

Stop rule: `(side > 0 and z < -3.5) or (side < 0 and z > 3.5)`.

| # | pair | stop | side | live z | entry-frame z | fires live | fires in entry frame | net (fills) |
|---|---|---|---|---|---|---|---|---|
| 2 | XLM/XRP | 08-11 07:00 | −1 | +3.6864 | +3.6864 | yes | **yes** | −5.97 |
| 6 | KAS/ETC | 08-20 02:00 | +1 | −4.7518 | **−3.2833** † | yes | **NO** | −9.66 |
| 9 | ETC/KAS | 08-21 10:00 | −1 | +4.1038 | +4.1038 | yes | **yes** | — ‡ |

† corrected per §0; the logged +3.5970 gives the same verdict.
‡ closed after the final snapshot; decision-price P&L −18.52, corroborated by a
NAV delta of −18.56.

**The KAS/ETC stop of 2026-08-20 is the only frame-induced stop in the
instrumented record, and it is the case already on file.** Its entry-frame
excursion was −3.28σ — adverse, but inside the band, and it never reached 3.5σ in
the coordinates the position was opened in. The stop fired because the
equilibrium moved out from under it.

**Counterfactual, from primary prices.** Marking the position (long 16,957 KAS,
short 67.76 ETC, entered at 0.02589 / 6.298) at every later decision print:

| when | event | KAS | ETC | mark-to-market | z (entry frame) |
|---|---|---|---|---|---|
| 08-20 02:00 | **stop fired** | 0.026695 | 6.6398 | **−9.51** | −3.283 |
| 08-20 11:00 | enter | 0.028363 | 6.7032 | **+14.48** | **+1.447** |
| 08-20 16:00 | exit | 0.028073 | 6.8520 | −0.53 | −1.466 |
| 08-20 19:01 | refit_drop | 0.027950 | 6.8200 | −0.43 | −1.449 |
| 08-21 03:00 | exit | 0.029263 | 7.0349 | +7.25 | −0.001 |
| 08-21 10:00 | stop | 0.029200 | 7.4504 | −21.96 | −5.336 |

Nine hours after the stop, the position was worth **+14.48** and its entry-frame
z had crossed to +1.447 — past the `exit_z = 0` threshold, so a held position
would have taken profit there rather than run on. Against the realised **−9.66**,
that is a swing of roughly **+24 USDT, about 2.3% of the 1,035 NAV at the time**.

Two things keep that from being a clean number. The path between 02:00 and 11:00
is not reconstructible — `ai_spread_assessment` records carry z but no prices, so
I cannot locate the crossing or say whether the exit would have come earlier and
smaller. And by 08-21 the same position would have been −21.96, so the sign of
the counterfactual depends on an exit rule firing, which is exactly the thing the
stop pre-empted. **The firm part is the realised −9.66 on a stop the entry frame
would not have triggered. The +24 swing is a plausible upper reading of one
event, not a measurement.**

---

## 5. The cost, split

### (a) P&L attributable to the frame moving

**One event.** KAS/ETC 2026-08-20: **−9.66 net realised** (fills: gross −9.354,
fees 0.309), on a stop that does not fire in the entry frame. Best available
counterfactual puts the opportunity cost near **−24** including forgone profit,
with the caveats above.

Nothing else in the instrumented record contributes. The other two stops fire
identically in both frames; five of six exits had no frame movement at all; the
sixth was a winner whose label holds.

### (b) Mislabelling, where the P&L is unchanged but the stated reason is wrong

**Zero.** Every reported exit reason survives re-derivation in the entry frame.
The Reasoning Log's exit-reason tally and win rate are, for the instrumented
subset, accurate as published.

This inverts the expectation in this task's own brief, which anticipated that
"the mislabelling half may matter more than the P&L half." On the record that can
actually be checked, the mislabelling half is empty and the P&L half is one stop.
The 2026-08-05 AVAX/SOL case that motivated the instrumentation remains the
documented example — but it predates the fields by a day and is not in the
measurable set, so it cannot be counted here and I have not counted it.

### Weighting against the score

The brief is right that a small P&L effect in the left tail can outrank its size,
because MDD is monotonically non-decreasing and carries 15%. On this event it did
not:

| | max drawdown | set at |
|---|---|---|
| before the 08-20 stop | 1.637% | 2026-08-08 21:01 |
| including the 08-20 stop | **1.637%** | 2026-08-08 21:01 |
| full phase | 1.779% | 2026-08-21 10:00 |
| full phase, that stop's print removed | **1.779%** | 2026-08-21 10:00 |

The frame-induced stop **did not touch max drawdown**. It took NAV from 1,045.14
to 1,035.51 — a 0.92% dip against a running drawdown already at 1.637% from
2026-08-08, and the phase maximum was set the following day by a different stop.
Removing its print entirely changes nothing. The MDD channel, the one where this
mechanism could have punched above its weight, registered the event at zero.

(These are NAV prints from the ledger's 79 decision-time records, peak 1,056.68.
That is a different series from the 3.7% figure quoted elsewhere in the project,
which is computed on a denser equity series; the two are not comparable and I
have not mixed them.)

The Sharpe channel (40%) is where a −9.66 loss on ~20 daily returns would bite
hardest, but I cannot compute the delta: it needs a daily return series
reconstructed under a counterfactual whose path is unobserved. Stating a Sharpe
impact here would be inventing one.

---

## 6. What the evidence would have to show

Not a proposal. The design axis, and where this sample lands on it.

**The two options, and their failure modes.** Judge a position in the frame it
was opened in (freeze `mu`/`sigma` until close) and a genuine structural break
goes unregistered — the position rides a broken relationship with no stop, which
is the failure the z-stop exists to prevent. Judge it in the current frame and
the target chases the position — which is what fired the 08-20 stop.

**What would favour freezing.** Frame drift would need to be (i) frequent enough
to matter, (ii) systematically directed against open positions, and (iii)
materially costly. Observed: **2 of 9 closes drift at all**; direction is **one
toward, one away**; cost is **one stop**. (i) is marginal, (ii) is absent, (iii)
rests on a single event. Nothing here reaches the bar.

**What would favour the trailing frame as it stands.** Drift-induced triggers
would need to be catching genuine breaks that the entry frame would have missed.
The single case runs the other way: the KAS/ETC spread recovered to entry-frame
z=+1.45 within nine hours, so the break the trailing frame signalled was not one.
That is one observation against, which is not a case either.

**The bar for either is roughly the same and it is not close.** Both hypotheses
need drift events in double digits across more than one regime, with the
direction consistent, before the sample can distinguish them from noise. Two
events in twelve days on three pairs cannot. Note also that the two options are
not exhaustive — the frame used to *screen and enter* need not be the frame used
to *judge an open position*, and the fields to test that split are already being
logged. I raise the axis because the evidence bears on it; choosing on it is a
human decision and this sample does not inform it.

---

## 7. What these records cannot tell you

1. **Two-thirds of the phase.** 18 of 27 closes predate the instrumentation,
   including all of July, the entire AVAX/SOL era, and the 6.75σ stop of
   2026-08-01. Frame drift on those is not assessable at all — and task 01's
   refit-during-hold proxy, which cleared them, is a proxy, not the measurement.
2. **n = 2.** Two material drift events is not a distribution. Every statement
   about direction, magnitude and cost rests on them, and one of the two has a
   corrupted logged field.
3. **One regime, twelve days, three pairs**, all in the closing stretch of Phase
   I. Refit cadence, hold length and volatility all fix the exposure rate, and
   none of them was varied.
4. **The intra-hold frame path.** `ai_spread_assessment` records carry z but no
   prices, so the frame can only be observed at the close. When during a hold the
   equilibrium moved, and how the two frames diverged in between, is not
   recoverable.
5. **Why the KAS/ETC field is wrong.** `entry_mu` and `entry_sigma` are never
   logged — only quantities derived from them — so a stale snapshot, a sign
   error, and a wrong `spread` argument are indistinguishable from the ledger.
6. **FIL/AR is unverifiable.** Its frame fields are self-consistent and yield a
   plausible positive σ₀, but it is the only instrumented close in its refit
   epoch, so there is no independent anchor of the kind that exposed the KAS/ETC
   error. If a second such field is wrong, this sample cannot tell.
7. **The counterfactual.** The +24 swing on the 08-20 stop depends on an
   unobserved nine-hour path and on an exit rule firing at a level I can see only
   at its endpoints.

---

## Bottom line

Frame drift is real, it is documented, and on the record that can actually be
measured it has cost **one stop and no mislabelling**: 9 of 27 closes carry the
fields, 7 of those 9 never saw the frame move at all, and the two that did split
one toward the position and one away — so there is no directional bias in this
sample, only two events. The measurable P&L cost is the **−9.66 realised** on the
KAS/ETC stop of 2026-08-20, a stop that does not fire in the frame the position
was entered in and whose spread had recovered to a profitable exit level nine
hours later, putting a plausible but unmeasured opportunity cost near **−24**,
about 2.3% of NAV at the time; against that, **max drawdown was untouched** — the
one scoring channel where this mechanism could have outweighed its size registered
it at zero. On the honesty question the record comes back **clean**: all six
instrumented exits survive re-derivation in their entry frames, the reported
exit-reason tally is correct as published, and the single case where the agent
flagged itself for frame drift turns out to be a sound exit flagged by a note that
uses a test the exit rule no longer applies. Set against that, two things sharpen
rather than soften the concern: the anchor case handed to this task has a logged
`z_in_entry_coords` that **cannot be correct at any positive σ** — the true
entry-frame z is −3.28, not +3.60, and σ **doubled** rather than collapsing 40% —
so one of the two instrumented drift records is itself wrong and the mechanism
was being described backwards; and two-thirds of the phase, including every large
stop before August 9, has no frame data at all. **Not big enough to act on, and
not measured well enough to act on:** two events cannot separate a frozen frame
from a trailing one, and the first thing this record argues for is fixing and
widening the instrumentation — log `entry_mu` and `entry_sigma` themselves, assert
that `z_in_entry_coords` and the spread agree in sign, and correct the
`reversion_note` test — so that the next drift event produces evidence instead of
another number that has to be audited.

---

## Provenance

- `track_record/phase1_submission/reasoning.jsonl` — 27 `exit`+`stop` records,
  38 `enter`, 35 `refit`, 79 NAV prints.
- `track_record/phase1_submission/fills/*.json` — 19 snapshots; realised P&L for
  6 of the 9 instrumented closes (two closed after the final snapshot, one aged
  out).
- Convention verified against `deploy/ltp_agent.py:357–385` (`entry_frame`),
  `:388–400` (`reversion_note`), `:1004–1011` (the stop and exit tests),
  `:999–1000` (the entry snapshot), `MU_SHIFT_MATERIAL = 0.10` at `:58`.
- **Measured** — coverage counts, all `mu_shift_sigma` values, refits-per-hold,
  the recovered KAS/ETC epoch frame (σ₀, μ₀, cross-checked out-of-sample against
  an entry z it was not fitted to), the corrected entry-frame z, both σ ratios,
  the relabel and re-timing tests, all P&L from fills or decision prices, the MDD
  series.
- **Estimated** — the +24 opportunity cost on the 08-20 stop, from decision-price
  marks at later timestamps; the path between them is unobserved.
- **Assumed** — nothing. Where a value could not be derived it is listed in §7.
- Reproduction: the epoch frame is fitted from the 08-19 09:00 and 08-19 16:00
  closes and validated against the 08-19 18:00 entry; all log-spreads use
  `log(price_a) − beta·log(price_b)` with the entry record's own beta.

*Created: this file only. No other file was modified.*
