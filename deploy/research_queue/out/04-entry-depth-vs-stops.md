# 04 — Does entry depth predict stop-outs?

**No. Past |z| = 1 the stop rate is flat — 44%, 50%, 43% across the 1–2, 2–3
and 3+ buckets (Fisher exact p = 1.00 for mid versus deep) — and the deep bucket
is the second most profitable in the book. Both proposed controls lose money,
and neither cuts the left tail, because the left tail is not where they are
aiming.**

Audit date 2026-09-13. Recomputed from `track_record/phase1_submission/`
(`reasoning.jsonl`, 1,271 records; `fills/*.json`, 19 snapshots). No figure is
taken from prose, including the numbers in this task's own brief. This is
evidence for a human decision, not a recommendation to act.

---

## Summary of answers

| Question | Answer |
|---|---|
| 1. Entry table | 38 `enter` records. **4 never opened** (notional 0) — and all four are deep. 34 risk-bearing, 31 with a known outcome, 22 venue-verified P&L. |
| 2. The denominator | Stop rate: **0/13 (0%)** below \|z\|=1, then **4/9, 1/2, 3/7 — 44%, 50%, 43%**. A step at 1, flat above it. |
| 3. Concentration | Yes — the 3+ bucket's +22.97 is 58% one trade. But it is concentrated in a **winner**, which weakens the case for a control, not strengthens it. |
| 4. Distance to stop | Arithmetically identical to depth (buffer = 3.5 − \|z\|). The independent cut — position within the band — is non-monotone with 2-to-6 trade cells. |
| 5. Counterfactuals | Taper: **−12.94**. Refusal: **−25.86**, and MDD gets *worse*. Matched for cost, a **flat size cut beats the taper on drawdown**. |
| 6. Does the sample support a conclusion? | For "deeper is riskier": **yes, it is rejected** (p = 1.00). For anything positive: no. |
| 7. Limits | The 2026-09-12 entry that prompted this **is not in the data**. Band changed mid-record. 3 closes missing. |

---

## Method

**Matching.** Entries are paired to closes sequentially per pair: an `enter`
opens, and the next `exit` / `stop` / `refit_drop` / `news_derisk` /
`kill_switch` on that pair closes it. Where a second `enter` arrives on a pair
with one already open, the earlier is recorded as unmatched rather than
silently dropped.

**P&L.** Venue-reconciled `net_pnl` from the fills snapshots where the trip
exists (22 of 31); otherwise decision-price P&L from the ledger's own prints,
`side · qa·Δpa − side · qb·Δpb` (9 of 31). Both are labelled per row.

**Buffer.** `stop_z` is 3.5 throughout (`AgentConfig.stop_z`), so
buffer = 3.5 − |z_entry|, and relative position in the tradeable band is
(|z| − band)/(3.5 − band).

**The four entries I excluded, and why it matters.** The fills record four
`enter` decisions on 2026-07-20 with `notional: 0`, no legs and no fills:

| entry | pair | z | fill trip |
|---|---|---|---|
| 07-20 01:00 | ETC/KAS | −3.173 | notional 0, no legs |
| 07-20 02:00 | ETC/KAS | −3.004 | notional 0, no legs |
| 07-20 03:00 | ETC/KAS | −3.009 | notional 0, no legs |
| 07-20 05:00 | ETC/KAS | −3.073 | notional 0, no legs |

These are the day-one `maxNotional` failures. They are logged decisions that
never became positions, so they never bore risk and could never have stopped.
**All four sit in the deepest bucket.** Counting them would put the 3+ stop rate
at 3/11 = 27% instead of 3/7 = 43% — it would flatter exactly the bucket under
test. They are excluded from every rate below and listed in the table for
completeness.

---

## 1. The entry table

38 `enter` records, 2026-07-19 → 2026-08-21. `rel` is position within the
tradeable band. P&L source: `venue` = reconciled fills, `decision` = ledger
prices.

| # | entry | pair | sd | z | \|z\| | band | buffer | rel | outcome | hold h | P&L | src |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 07-20 01:00 | ETC/KAS | +1 | −3.173 | 3.17 | 3.0 | 0.33 | 0.35 | *never opened* | — | — | — |
| 2 | 07-20 02:00 | ETC/KAS | +1 | −3.004 | 3.00 | 3.0 | 0.50 | 0.01 | *never opened* | — | — | — |
| 3 | 07-20 03:00 | ETC/KAS | +1 | −3.009 | 3.01 | 3.0 | 0.49 | 0.02 | *never opened* | — | — | — |
| 4 | 07-20 05:00 | ETC/KAS | +1 | −3.073 | 3.07 | 3.0 | 0.43 | 0.15 | *never opened* | — | — | — |
| 5 | 07-20 05:16 | ETC/KAS | +1 | −3.310 | 3.31 | 3.0 | 0.19 | 0.62 | **stop** | 1.7 | −4.22 | decision |
| 6 | 07-20 21:00 | TAO/RENDER | +1 | −3.021 | 3.02 | 3.0 | 0.48 | 0.04 | **stop** | 4.0 | −3.89 | decision |
| 7 | 07-21 16:00 | TAO/RENDER | +1 | −3.437 | 3.44 | 3.0 | 0.06 | 0.87 | reverted | 3.0 | +2.20 | decision |
| 8 | 07-25 04:00 | TAO/RENDER | −1 | +3.180 | 3.18 | 3.0 | 0.32 | 0.36 | reverted | 15.0 | +9.10 | decision |
| 9 | 07-26 06:00 | TAO/RENDER | −1 | +3.340 | 3.34 | 3.0 | 0.16 | 0.68 | reverted | 4.0 | +8.79 | decision |
| 10 | 07-26 18:00 | TAO/RENDER | −1 | +3.083 | 3.08 | 3.0 | 0.42 | 0.17 | **stop** | 2.0 | −2.42 | decision |
| 11 | 07-26 22:00 | TAO/RENDER | −1 | +3.011 | 3.01 | 3.0 | 0.49 | 0.02 | *no close logged* | — | — | — |
| 12 | 07-28 04:15 | AVAX/SOL | +1 | −1.174 | 1.17 | 0.6 | 2.33 | 0.20 | reverted | 17.8 | +7.06 | venue |
| 13 | 07-29 04:00 | AVAX/SOL | +1 | −1.245 | 1.25 | 0.6 | 2.25 | 0.22 | reverted | 22.0 | +2.71 | venue |
| 14 | 07-30 10:00 | AVAX/SOL | +1 | −0.678 | 0.68 | 0.6 | 2.82 | 0.03 | reverted | 2.0 | +3.53 | venue |
| 15 | 07-30 16:00 | AVAX/SOL | +1 | −0.886 | 0.89 | 0.6 | 2.61 | 0.10 | reverted | 10.0 | +1.64 | venue |
| 16 | 07-31 03:00 | AVAX/SOL | +1 | −0.956 | 0.96 | 0.6 | 2.54 | 0.12 | reverted | 2.0 | +3.01 | venue |
| 17 | 07-31 11:00 | AVAX/SOL | −1 | +0.794 | 0.79 | 0.6 | 2.71 | 0.07 | reverted | 3.0 | +5.68 | venue |
| 18 | 07-31 19:00 | AVAX/SOL | −1 | +0.684 | 0.68 | 0.6 | 2.82 | 0.03 | reverted | 2.0 | +3.15 | venue |
| 19 | 08-01 01:01 | AVAX/SOL | +1 | −0.772 | 0.77 | 0.6 | 2.73 | 0.06 | reverted | 1.0 | +1.37 | venue |
| 20 | 08-01 01:02 | FIL/AR | −1 | +0.719 | 0.72 | 0.6 | 2.78 | 0.04 | *no close logged* | — | — | — |
| 21 | 08-01 05:00 | AVAX/SOL | −1 | +1.167 | 1.17 | 0.6 | 2.33 | 0.20 | reverted | 1.4 | +1.78 | venue |
| 22 | 08-01 08:00 | AVAX/SOL | +1 | −1.386 | 1.39 | 0.6 | 2.11 | 0.27 | **stop** | 11.0 | −6.31 | venue |
| 23 | 08-02 05:00 | AVAX/SOL | −1 | +1.737 | 1.74 | 0.6 | 1.76 | 0.39 | **stop** | 13.0 | −9.91 | venue |
| 24 | 08-03 14:00 | AVAX/SOL | −1 | +0.717 | 0.72 | 0.4 | 2.78 | 0.10 | reverted | 38.0 | −4.29 | venue |
| 25 | 08-07 21:01 | KAS/ETC | −1 | +1.273 | 1.27 | 0.4 | 2.23 | 0.28 | refit_drop | 24.0 | −2.73 | venue |
| 26 | 08-08 21:01 | FIL/AR | −1 | +1.240 | 1.24 | 0.4 | 2.26 | 0.27 | reverted | 26.0 | +6.03 | venue |
| 27 | 08-10 10:00 | FIL/AR | +1 | −0.647 | 0.65 | 0.6 | 2.85 | 0.02 | refit_drop | 10.0 | +2.19 | venue |
| 28 | 08-10 20:01 | XLM/XRP | −1 | +2.333 | 2.33 | 0.6 | 1.17 | 0.60 | **stop** | 11.0 | −5.97 | venue |
| 29 | 08-12 21:00 | XLM/XRP | −1 | +0.635 | 0.63 | 0.6 | 2.87 | 0.01 | refit_drop | 23.0 | −0.62 | venue |
| 30 | 08-17 19:01 | KAS/ETC | +1 | −0.894 | 0.89 | 0.6 | 2.61 | 0.10 | reverted | 9.0 | +6.48 | venue |
| 31 | 08-19 01:00 | KAS/ETC | +1 | −0.701 | 0.70 | 0.6 | 2.80 | 0.03 | reverted | 8.0 | +12.09 | venue |
| 32 | 08-19 10:00 | KAS/ETC | −1 | +0.877 | 0.88 | 0.6 | 2.62 | 0.10 | reverted | 6.0 | +6.28 | venue |
| 33 | 08-19 18:00 | KAS/ETC | +1 | −1.372 | 1.37 | 0.6 | 2.13 | 0.27 | **stop** | 8.0 | −9.66 | venue |
| 34 | 08-20 11:00 | KAS/ETC | −1 | +3.205 | 3.21 | 0.6 | 0.29 | 0.90 | reverted | 5.0 | **+13.40** | venue |
| 35 | 08-20 17:00 | KAS/ETC | +1 | −2.544 | 2.54 | 0.6 | 0.96 | 0.67 | refit_drop | 2.0 | +2.89 | decision |
| 36 | 08-20 19:01 | ETC/KAS | −1 | +0.806 | 0.81 | 0.6 | 2.69 | 0.07 | *no close logged* | — | — | — |
| 37 | 08-20 22:00 | ETC/KAS | −1 | +0.974 | 0.97 | 0.6 | 2.53 | 0.13 | reverted | 5.0 | +6.44 | decision |
| 38 | 08-21 05:00 | ETC/KAS | −1 | +1.195 | 1.19 | 0.6 | 2.31 | 0.21 | **stop** | 5.0 | **−18.52** | decision |

**Counts.** 38 logged → 4 never opened → **34 risk-bearing** → 3 with no close
in the ledger (#11, #20, #36) → **31 with a known outcome**. Of those 31,
**22 have venue-verified P&L** and 9 have decision-price P&L only; none has
neither. Outcomes: 19 reverted, 8 stopped, 4 refit-dropped.

---

## 2. The denominator

Across the 31 risk-bearing entries with a known outcome:

| bucket | n | stops | **stop rate** | 95% CI (Wilson) | mean P&L | median | worst | total |
|---|---|---|---|---|---|---|---|---|
| \|z\| < 1 | 13 | 0 | **0.0%** | 0.0 – 22.8% | +3.61 | +3.15 | −4.29 | **+46.96** |
| 1 – 2 | 9 | 4 | **44.4%** | 18.9 – 73.3% | −3.28 | −2.73 | **−18.52** | **−29.56** |
| 2 – 3 | 2 | 1 | **50.0%** | 9.5 – 90.5% | −1.54 | −1.54 | −5.97 | −3.07 |
| 3 + | 7 | 3 | **42.9%** | 15.8 – 75.0% | +3.28 | +2.20 | −4.22 | **+22.97** |

**The relationship is not monotone. It is a step at |z| = 1 and flat above it.**

- Shallow (|z| < 1) vs everything deeper: 0/13 against 8/18, **Fisher exact
  p = 0.0096**. Real in this sample.
- Mid (1 ≤ |z| < 3) vs deep (|z| ≥ 3): 5/11 against 3/7, **Fisher exact
  p = 1.0000**. **No evidence whatsoever.** This is the comparison the task
  exists to make, and it comes back empty.

**And the flatness is the striking part, because the mechanics predict a steep
rise.** The adverse move required to reach the stop shrinks eightfold across the
buckets:

| bucket | mean buffer to the stop | observed stop rate |
|---|---|---|
| \|z\| < 1 | 2.71σ | 0% |
| 1 – 2 | 2.19σ | 44% |
| 2 – 3 | 1.06σ | 50% |
| 3 + | **0.28σ** | **43%** |

A 3+ entry needs roughly a quarter of a sigma to go wrong and stops out no more
often than one needing 2.19σ. That is what the OU argument predicts — a deeper
entry carries more expected reversion, and here it very nearly exactly offsets
the smaller buffer. The evidence points the opposite way from the fear.

**There is a second effect, running the same direction.** Among the eight stops,
depth and loss are strongly inversely related:

| entry | pair | \|z\| | buffer | loss |
|---|---|---|---|---|
| 08-21 05:00 | ETC/KAS | 1.19 | 2.31 | **−18.52** |
| 08-19 18:00 | KAS/ETC | 1.37 | 2.13 | −9.66 |
| 08-01 08:00 | AVAX/SOL | 1.39 | 2.11 | −6.31 |
| 08-02 05:00 | AVAX/SOL | 1.74 | 1.76 | −9.91 |
| 08-10 20:01 | XLM/XRP | 2.33 | 1.17 | −5.97 |
| 07-20 21:00 | TAO/RENDER | 3.02 | 0.48 | −3.89 |
| 07-26 18:00 | TAO/RENDER | 3.08 | 0.42 | −2.42 |
| 07-20 05:16 | ETC/KAS | 3.31 | 0.19 | −4.22 |

Spearman ρ = **+0.857**, Pearson r = +0.777 (n = 8, so indicative rather than
established). Mean loss given a stop: **−11.10** in the 1–2 bucket, −5.97 in
2–3, **−3.51** in 3+. This is largely arithmetic rather than luck — realised
loss is roughly the P&L rate per z times the buffer crossed, and a deep entry
has almost no buffer to cross. Being arithmetic is what makes it likely to
persist.

Put together: **the losing region is the middle.**

| | n | total P&L |
|---|---|---|
| \|z\| < 1 | 13 | **+46.96** |
| 1 ≤ \|z\| < 3 | 11 | **−32.63** |
| \|z\| ≥ 3 | 7 | **+22.97** |

Both tails made money. A depth taper penalises the profitable right tail and
leaves the middle alone.

---

## 3. Is it an artefact of a few trades?

Partly, and the concentration runs against the control.

**The 3+ bucket (n = 7, +22.97).** One trade, KAS/ETC 2026-08-20 at |z| = 3.21,
contributes **+13.40 — 58% of the bucket total** and 30% of its gross flow. The
next two, TAO/RENDER at +9.10 and +8.79, carry another 78% between them. Strip
the single largest and the bucket is +9.57 on six trades — still positive, still
a 50% stop rate, still no worse than the middle.

The important point is the direction: **the bucket is dominated by a winner.**
Concentration usually weakens a positive claim; here it would have to be
concentrated in *losses* to support the control, and it is not. The three deep
stops are the three **smallest** stops in the entire record.

**The era confound is larger than the concentration.** The entry band changed
mid-record, and it changes what "deep" means:

| era | band | n | stops | rate | \|z\| range | total P&L |
|---|---|---|---|---|---|---|
| 2026-07-20 → 07-27 | **3.0** | 6 | 3 | 50.0% | 3.02 – 3.44 | +9.57 |
| 2026-07-28 → 08-21 | 0.4 / 0.6 | 25 | 5 | 20.0% | 0.63 – 3.21 | +27.73 |

Under the 3.0 band the agent *could not* enter shallower than 3.0 — every entry
in that era is mechanically in the 3+ bucket, sitting at its own band with a
buffer of at most 0.5σ by construction. Six of the seven entries in the deepest
bucket come from that configuration. **So "3+ has a 43% stop rate" is largely a
statement about the 3.0-band fortnight, not about depth.** The single 3+ entry
from the modern configuration (#34) reverted for +13.40.

---

## 4. Distance to the stop

The buffer cut is **arithmetically identical** to the depth cut, because
`stop_z` never changed: buffer = 3.5 − |z|, a strictly decreasing function of
depth. Reporting it separately adds no information, and I state that rather than
presenting the same table twice as if it were a second test.

| buffer | n | stops | rate | total P&L |
|---|---|---|---|---|
| > 2.5σ | 13 | 0 | 0.0% | +46.96 |
| 1.5 – 2.5σ | 9 | 4 | 44.4% | −29.56 |
| 0.5 – 1.5σ | 2 | 1 | 50.0% | −3.07 |
| < 0.5σ | 7 | 3 | 42.9% | +22.97 |

The genuinely independent cut — the one that separates "3.0 against a 3.0 band"
from "3.0 against a 0.6 band" — is position within the tradeable band,
(|z| − band)/(3.5 − band):

| rel. position | n | stops | rate | total P&L |
|---|---|---|---|---|
| 0.00 – 0.25 | 19 | 3 | 15.8% | +33.67 |
| 0.25 – 0.50 | 6 | 3 | **50.0%** | −13.48 |
| 0.50 – 0.75 | 4 | 2 | **50.0%** | +1.50 |
| 0.75 – 1.00 | **2** | **0** | **0.0%** | **+15.60** |

Non-monotone again, and the deepest-relative cell is two trades (#7 and #34),
both of which reverted profitably. **A rate computed on two observations is not
a rate**, and I am not going to treat it as one — but it is the cell a depth
control would penalise hardest, and it contains no losses at all.

---

## 5. What the alternatives would have cost

Both counterfactuals assume P&L scales linearly with position size (fees and
notional both scale, so this is close but not exact), and the refusal
counterfactual assumes refused capital sits idle — in practice it would have
been available for other entries, which this record cannot model.

| | total P&L | Δ vs actual | worst single trade | max drawdown † |
|---|---|---|---|---|
| **actual** | **+37.30** | — | −18.52 | 2.23% |
| linear taper `(3.5−\|z\|)/(3.5−band)` | +24.36 | **−12.94** | −14.72 | 1.60% |
| hard refusal `\|z\| > 2.5` | +11.44 | **−25.86** | **−18.52** | **2.26%** |

† realised P&L applied in close-time order from 1000, ignoring unrealised marks
and the three entries with no logged close. An approximation, labelled as one.

**The hard refusal is the clearer failure.** It gives up 25.86 — 69% of all
realised profit — to refuse eight entries, and it **does not improve drawdown at
all** (2.23% → 2.26%, marginally worse). It avoids three stops worth −10.53 and
forgoes winners worth +36.38. The worst trade in the book is **completely
untouched**, because it entered at |z| = 1.19.

**The effect on the five worst trades — the whole point of a tail control:**

| entry | \|z\| | actual | tapered | refused? |
|---|---|---|---|---|
| 08-21 05:00 | 1.19 | −18.52 | −14.72 | kept |
| 08-02 05:00 | 1.74 | −9.91 | −6.02 | kept |
| 08-19 18:00 | 1.37 | −9.66 | −7.09 | kept |
| 08-01 08:00 | 1.39 | −6.31 | −4.60 | kept |
| 08-10 20:01 | 2.33 | −5.97 | −2.40 | kept |
| **sum** | | **−50.36** | −34.83 | **−44.39 survives** |

**Every one of the five worst trades is a shallow or mid-depth entry. The
refusal control keeps all five.** A depth filter aimed at |z| > 2.5 is aimed at
a part of the distribution that contains none of the damage.

**And the taper's drawdown benefit is not a depth effect.** Matched for
identical P&L cost, a flat across-the-board size cut does better:

| | final | max drawdown |
|---|---|---|
| depth taper | 1024.36 | 1.60% |
| **flat size × 0.653** | 1024.36 | **1.48%** |

The taper's mean weight across the 31 entries is 0.739 — it is mostly a 26%
blanket size reduction wearing a depth costume, and the depth-varying part makes
the drawdown slightly *worse* than spreading the same cut evenly. **On this
record the depth signal has negative information value for sizing.** If the
operators want less drawdown, the honest lever is leverage, and it should be
argued for as leverage.

---

## 6. Does the sample support a conclusion?

**For the negative claim, yes — and that is the claim being tested.** The gate
asks whether deeper entries stop out more. Mid versus deep returns Fisher exact
p = 1.0000 on 11 and 7 observations, the deep bucket is net +22.97, its stops
are the smallest in the record, and both proposed controls lose money on the
realised path. A control needs positive evidence to justify building it, and
there is none here in any direction. **"Do nothing" is well supported.**

**For any positive claim, no.** The buckets hold 13, 9, 2 and 7 trades; the
Wilson intervals span 19–73% and 16–75% and overlap almost completely. The one
result that clears significance — 0/13 below |z| = 1, p = 0.0096 — is confounded
three ways: that bucket is entirely from the 0.4/0.6-band era, it is dominated
by two good runs on two pairs (AVAX/SOL in late July, KAS/ETC in late August),
and a shallow entry mechanically needs a far larger adverse move to stop. It
should be read as "shallow entries did well in this sample", not as a law. It
also points the opposite way from the proposed control.

**What would settle it.** The deep bucket needs enough stops for its rate to
have a usable interval — roughly 25–30 entries at |z| ≥ 2.5 to bring a 43% rate
inside ±15 points, which at the observed cadence is several months, and it must
span more than one band configuration so depth is not confounded with the era.
The cheaper route is not more trades but a better measurement: the first-passage
machinery in `statarb/thresholds.py` already prices the probability of reaching
the stop before the exit given κ, σ_eq and the entry z. **Computing that
probability per entry and comparing it against the realised stop outcomes would
test the hypothesis on all 31 trades at once, rather than on the 7 that happen
to be deep.** That is a desk calculation, not a waiting game.

---

## 7. What the records cannot tell you

1. **The observation that prompted this task is not in the data.** The ledger
   ends 2026-08-21 16:00. The 2026-09-12 `1000SHIB/DOGE` entry at z = +3.41 does
   not appear in `reasoning.jsonl`, and neither does any Phase II activity. I
   could not verify it, its regime rating, or its unrealised P&L. For what it is
   worth, a |z| of 3.41 implies a buffer of 0.09σ, which would be the second
   smallest in the whole record — the smallest is 0.06σ on entry #7, which
   reverted for +2.20.
2. **Three risk-bearing entries have no logged close** (#11 TAO/RENDER at
   |z| = 3.01, #20 FIL/AR at 0.72, #36 ETC/KAS at 0.81). Their fill trips show
   real notional, so they took risk; their outcomes are unknown. One is a deep
   entry, so the 3+ bucket is 7 known outcomes out of 8 positions taken.
3. **Nine of 31 P&L figures are decision-price, not venue-reconciled** — the
   three July stops and the deep TAO/RENDER winners aged out before the first
   snapshot, and the final two closed after the last one. Where both exist they
   agree to within ~1.5, with fills generally slightly worse.
4. **The band changed mid-record** (3.0 → 0.6 → 0.4 → 0.6), so depth is
   confounded with configuration, pair and calendar. Six of seven deep entries
   are from the 3.0-band fortnight on two pairs.
5. **One regime.** Thirty-one trades across five pairs in thirty-three days, with
   a market-wide sell-off sitting in the middle of it.
6. **Both counterfactuals are approximations.** Linear P&L in size is close but
   not exact; refused capital would not really have sat idle; and the drawdown
   figures are reconstructed from realised P&L in close order, not from the NAV
   path the agent actually experienced.
7. **Nothing here tests the analyst's judgement.** The question of whether a
   `stressed` regime rating carries information is a different question on a
   different sample, and this record cannot speak to it.

---

## Bottom line

**On this evidence, entry depth should not affect position size.** Past |z| = 1
the stop rate is flat — 44%, 50%, 43% — and mid-versus-deep returns Fisher exact
p = 1.00, which is as close to "no signal" as a test can report; the deep bucket
made **+22.97** on seven trades, its three stops are the three smallest losses in
the entire record, and the strong inverse relation between entry depth and stop
loss (ρ = +0.857) is arithmetic rather than luck, because a deep entry has almost
no buffer left to lose across. The damage lives in the **middle**: entries
between 1 and 3 sigma cost −32.63, and all five of the worst trades in the book —
including the worst, at −18.52 — entered between 1.19 and 2.33, where a
depth control is not looking. Both proposals fail on their own terms: the hard
refusal gives up 69% of realised profit, avoids three of the smallest stops,
leaves every one of the five worst trades in place and makes drawdown *worse*;
the taper costs 12.94 and its drawdown benefit is beaten by a flat size cut of
identical cost, which means the depth signal is not merely uninformative for
sizing but slightly harmful. The honest caveats are real — the deep bucket is
six-sevenths a single fortnight when the band was 3.0, the 2026-09-12 entry that
prompted this is not in the data, and no bucket here could carry a positive
finding — but they do not rescue the control, because a control needs evidence
*for* it and there is none in any direction. **The action this record supports is
to do nothing, and to write down that it was checked**: 31 outcome-known entries
say deep entries are not the risk, and the next session that sees a frightening
z should be pointed at this file rather than re-deriving the fear. If the
question is reopened, the cheap way to settle it is not more trades but the
first-passage probability already implemented in `statarb/thresholds.py`,
computed per entry and scored against the realised outcomes, which tests the
hypothesis on all 31 trades instead of the seven that happen to be deep.

---

## Provenance

- `track_record/phase1_submission/reasoning.jsonl` — 38 `enter`, 19 `exit`,
  8 `stop`, 4 `refit_drop`, 35 `refit`; span 2026-07-19 20:07 → 2026-08-21 16:00.
- `track_record/phase1_submission/fills/*.json` — 19 snapshots; 37 trips indexed
  by entry timestamp; 22 of the 31 matched entries carry venue-reconciled
  `net_pnl`.
- `stop_z = 3.5` from `deploy/ltp_agent.py:115`; entry bands read from each
  entry's own `entry_z` field.
- **Measured** — every count, stop rate, Wilson interval, Fisher exact p,
  Spearman/Pearson coefficient, bucket total, concentration share and
  counterfactual total.
- **Approximated, and labelled in place** — the drawdown reconstructions in §5
  (realised P&L in close order from 1000), and the linear-P&L-in-size assumption
  behind both counterfactuals.
- **Excluded, with reason given** — the four 2026-07-20 `enter` records whose
  fill trips show `notional: 0` and no legs.
- Statistics computed directly (Wilson score interval, hypergeometric two-sided
  Fisher exact); no external libraries were needed or used.

*Created: this file only. No other file was modified.*
