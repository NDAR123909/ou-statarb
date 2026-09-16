# 02 — Did the one-sided re-entry block earn its keep?

**Unproven on P&L, and the sample is not ten — it is two.** The ten logged
refusals are two blocking episodes, and they point opposite ways: one prevented
≈ **+7.97** of losses, the other cost ≈ **−11.5** of profit, netting ≈ **−3.7**.
But the block improved max drawdown from **2.273% to 1.779%**, and MDD is 15% of
the score and never heals. **Return-reducing and risk-reducing, on n = 2.**

And the newer question this brief added answers cleanly in the negative: the
re-entry shape `side_blocked` does *not* cover stops out at **20%** in Phase I —
identical to the shape it does cover, and below the book's 26% base rate.

Audit date 2026-09-16. Recomputed from `track_record/phase1_submission/`
(`reasoning.jsonl`, 1,271 records; `fills/*.json`, 19 snapshots) and the control
as implemented at `deploy/ltp_agent.py:874–914` and `:845–849`. No figure is
taken from prose, including the numbers in this brief. This is evidence for a
human decision, not a recommendation to act — the control is `CLAUDE.md`
invariant 4.

---

## 0. A coverage limit that has to come first

**The 2026-09-15 material in this brief is not in the data I can reach.** The
repo's ledger is the Phase I submission archive: 1,271 records ending
**2026-08-21 16:00**. Phase II went live 2026-09-08 and its ledger
(`ltp_state_history.jsonl`) is on the droplet, which this session cannot read —
a standing open commitment says so in as many words.

So I could not verify, and have not used:

- the live `blocked=1` on `1000SHIB/DOGE` from the 2026-09-15 20:00 stop;
- the 01:00 → 12:01 churn sequence quoted in the brief;
- the −3.54 stop that followed the 07:00 re-entry.

Everything below is Phase I only: **ten refusals, both in August**. Where the
brief asks for a comparison against the 09-15 cluster, I give the Phase I base
rate instead and say what it would take to place that day against it.

---

## Summary

| Question | Answer |
|---|---|
| 1. The blocks | Ten refusals, **two episodes**: XLM/XRP 08-11 (5) and KAS/ETC 08-20 (5). |
| 2–3. Counterfactual | Episode A: block **saved +7.97**. Episode B: block **cost −11.5**. Net ≈ **−3.7**. |
| 3. Concentration | Total. Each episode is one decision, and they cancel. **Two observations, not ten.** |
| 3b. Where in \|z\| | 7 of 10 sit in the 1–3 "damage" zone — but the forward paths **contradict** the base-rate argument. |
| 3c. Uncovered re-entries | Same-side after a non-stop close: **2 stops / 10 = 20%**. Opposite-side: **20%**. Base rate 26%. **No elevated risk.** |
| 4. The deciding question | **Return-reducing AND risk-reducing.** MDD 2.273% → **1.779%** for ≈ −3.7 USDT. |
| 5. Is ten enough? | **No — and it is two, not ten.** |

---

## Method

**The control, as implemented.** `ltp_agent.py:879–882` — entry requires
`entry_z < z < stop_z` (short) or `−stop_z < z < −entry_z` (long), and
`blocked != −1` / `!= +1` respectively. `:1073` sets `blocked` on a stop.
`:845–849` heals it: a `+1` block clears when `z > −entry_z`, a `−1` block when
`z < entry_z`. The `skip` is logged **only** when the block is what stopped the
trade, never on a quiet bar — so the ten are ten genuine refusals, not noise.

**One structural fact the entry branch forces, and it governs the whole
counterfactual:** entry happens only when `side == 0`. One position per pair,
one action per bar. So a refusal that recurs across five consecutive bars is
**one forgone trade, not five** — after the first entry the agent would have
been holding, and the later signals would never have been evaluated as entries.
Treating the ten refusals as ten forgone trades would overstate the block's cost
by roughly 3×. I replay the agent's actual logic with the block removed instead.

**P&L.** The z path is hourly and entries execute at the bar's decision price,
so no interpolation is needed for fills. Counterfactual P&L uses each pair's own
realised rate of P&L per unit of z, taken from an actual trade on that pair in
the same refit epoch — the method `stop_analysis.py` uses:

| pair | beta | σ_eq | calibrating trade | rate (USDT per z) |
|---|---|---|---|---|
| XLM/XRP | 1.925336 | 0.0104839 | 08-10 20:01 → 08-11 07:00, −4.93 over Δz +1.354 | **−3.6445** |
| KAS/ETC | 0.932658 | 0.0065020 | 08-20 11:00 → 16:00, +13.50 over Δz −4.731 | **−2.8526** |

**Costs**, as the brief specifies: `2 × taker_fee × (1 + |beta|)` with the
measured taker fee of **1.752 bps/side** from the fills snapshots, converted to
z units by dividing by σ_eq. This reproduces the realised fees on both
calibrating trades, which is the check that it is right:

| pair | modelled round-trip | realised fees on that trip |
|---|---|---|
| XLM/XRP | 0.0978 z = **0.356 USDT** | **0.35628** |
| KAS/ETC | 0.1042 z = **0.297 USDT** | **0.29589** |

**Frame check.** Task 03 found this book's z readings can shift under a refit,
so before trusting any z path I confirmed the frame was constant across each
window. Refits are daily at ~19:00–20:00 UTC; none falls inside either refusal
window. For KAS/ETC the check is exact — the implied σ from the 02:00 stop to
the 11:00 entry is 0.00650197 against 0.00650197 from the 11:00→16:00 trade,
**ratio 1.000**. So the 10:00 → 11:00 jump from −1.114 to +3.205 is a **real
4.3σ move in one hour**, not a coordinate change.

---

## 1. The ten refusals, reconstructed

All ten are `reason="side_blocked"`; they are the only `skip` records in the
ledger. `entry_z` was 0.60 on every one.

| # | refused at | pair | side wanted | z | \|z\| | \|z\|/band | 3.5−\|z\| | regime | triggering stop |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 08-11 12:00 | XLM/XRP | −1 | +3.195 | 3.195 | 5.33 | 0.305 | stressed | 08-11 07:00, z=+3.686 |
| 2 | 08-11 14:00 | XLM/XRP | −1 | +3.418 | 3.418 | 5.70 | 0.082 | stressed | " |
| 3 | 08-11 17:00 | XLM/XRP | −1 | +2.702 | 2.702 | 4.50 | 0.798 | stressed | " |
| 4 | 08-11 18:00 | XLM/XRP | −1 | +2.257 | 2.257 | 3.76 | 1.243 | **broken** | " |
| 5 | 08-11 19:00 | XLM/XRP | −1 | +2.690 | 2.690 | 4.48 | 0.810 | stressed | " |
| 6 | 08-20 06:00 | KAS/ETC | +1 | −3.130 | 3.130 | 5.22 | 0.370 | stressed | 08-20 02:00, z=−4.752 |
| 7 | 08-20 07:00 | KAS/ETC | +1 | −2.790 | 2.790 | 4.65 | 0.710 | stressed | " |
| 8 | 08-20 08:00 | KAS/ETC | +1 | −2.370 | 2.370 | 3.95 | 1.130 | stressed | " |
| 9 | 08-20 09:00 | KAS/ETC | +1 | −2.116 | 2.116 | 3.53 | 1.384 | stressed | " |
| 10 | 08-20 10:00 | KAS/ETC | +1 | −1.114 | 1.114 | 1.86 | 2.386 | normal | " |

**Two episodes, five refusals each.**

**How long each block lasted, and how it ended — the two differ, and one of them
is not the documented mechanism.**

- **Episode B (KAS/ETC)** ended as designed: the `+1` block heals when
  `z > −0.60`, and at 11:00 z reached +3.205. **Duration 9 bars** (02:00 →
  11:00). The pair then entered *short* the same bar — the opposite side, which
  was never blocked.
- **Episode A (XLM/XRP)** did **not** heal. z was still +2.690 at the last
  refusal, far outside the +0.60 threshold. The 08-11 20:00 refit passed
  **0 of 15** candidates, so XLM/XRP left `state["pairs"]` entirely. `blocked`
  is carried across a refit only for pairs the refit keeps (`:302–306`), so when
  the pair re-entered the universe at the 08-12 20:00 refit it came back with
  `blocked = 0`. **Duration 13 bars, terminated by eviction rather than by
  healing.**

That is worth recording on its own: **the block's effective life is bounded by
the refit cycle, not only by the heal condition.** A pair the refit drops loses
its block silently. Neither the docstring nor the skip's own reasoning line says
so.

---

## 2–3. The counterfactual, and what it totals

Replaying the agent's entry logic with the block removed, and nothing else
changed.

### Episode A — XLM/XRP, 2026-08-11

Path from the stop: 07:00 +3.686 **stop** · 08:00 +4.117 · 09:00 +4.402 ·
10:00 +3.789 · 11:00 +3.659 · 12:00 +3.195 · 13:00 +3.801 · 14:00 +3.418 ·
15:00 +4.718 · 16:00 +3.769 · 17:00 +2.702 · 18:00 +2.257 · 19:00 +2.690

Bars 08:00–11:00 are all above 3.5, so no entry is possible there even without
the block — `short_zone` excludes anything beyond the stop.

| entered | closed | side | z in | z out | why | Δz | P&L |
|---|---|---|---|---|---|---|---|
| 08-11 12:00 | 08-11 13:00 | −1 | +3.195 | +3.801 | **stop** | +0.606 | **−2.564** |
| 08-11 14:00 | 08-11 15:00 | −1 | +3.418 | +4.718 | **stop** | +1.300 | **−5.095** |
| 08-11 17:00 | 08-11 20:00 | −1 | +2.702 | +2.690 * | refit_drop * | −0.012 * | **−0.312** * |
| | | | | | | **total** | **−7.971** |

\* estimated, not measured — see §6. The 08-11 20:00 refit passed 0/15, so an
open position would have been flattened there; z at 20:00 is not logged and I
use the 19:00 reading of +2.690.

Refusals 4 and 5 (18:00, 19:00) produce no separate trade: the 17:00 position
would still have been open.

**Actual, with the block: no XLM/XRP trades at all between the 07:00 stop and
the 08-12 21:00 entry. The block saved +7.97.**

### Episode B — KAS/ETC, 2026-08-20

Path: 02:00 −4.752 **stop** · 03:00 −4.627 · 04:00 −3.548 · 05:00 −3.923 ·
06:00 −3.130 · 07:00 −2.790 · 08:00 −2.370 · 09:00 −2.116 · 10:00 −1.114 ·
11:00 **+3.205** · 12:00 +0.530 · 13:00 +1.063 · 14:00 +0.734 · 15:00 +0.172 ·
16:00 −1.526

Bars 03:00–05:00 are beyond −3.5, so the first possible entry is 06:00.

| entered | closed | side | z in | z out | why | Δz | P&L |
|---|---|---|---|---|---|---|---|
| 08-20 06:00 | 08-20 11:00 | +1 | −3.130 | +3.205 | reverted | +6.335 | **+17.774** |
| 08-20 13:00 | 08-20 16:00 | −1 | +1.063 | −1.526 | reverted | −2.589 | **+7.088** |
| | | | | | | **total** | **+24.862** |

The second row matters and is easy to miss. Holding a long into 11:00 means the
bar **exits** rather than enters, so the +13.40 short the agent actually took at
11:00 never happens. At 12:00 z is +0.530, inside the ±0.60 band, so no entry;
the short instead opens at 13:00 and captures less.

**Actual, with the block: one trade, 11:00 → 16:00 short, venue-reconciled
+13.399 net (gross +13.695, fees 0.29589). The block cost ≈ −11.5.**

### The total, and its concentration

| | P&L with the block | without | effect of the block |
|---|---|---|---|
| Episode A (XLM/XRP) | 0.00 | −7.971 | **+7.971** |
| Episode B (KAS/ETC) | +13.399 | +24.862 | **−11.463** |
| **net** | | | **≈ −3.5** |

On a single consistent decision-price basis the net is −3.69; using the venue
figure where one exists, −3.46. **Call it −3.5, about 0.34% of the ~1,035 NAV.**

**Concentration is total, and it is the finding.** This is not ten observations
averaging out — it is **two decisions that cancel**. Episode B's entire cost is
one hypothetical trade; episode A's entire saving is two prevented stops within
three hours of each other. Reverse either one and the sign of the total flips.

**A note on the agenda's claim that a block sat "directly in front of the best
trade of the phase."** It did not, and the truth is more interesting. The block
was on the **long** side; the +13.40 winner was a **short**, which was never
blocked, and it fired the same bar the block healed. What the block actually
stood in front of was a *long* that would have made **+17.77** — more than the
trade that was taken. The block did not delay the best trade; it substituted a
good trade for a better one.

---

## 3b. Where the refusals sat in |z|

| bucket | refusals | which |
|---|---|---|
| \|z\| 1–2 | 1 | #10 (1.114) |
| \|z\| 2–3 | 6 | #3, #4, #5, #7, #8, #9 |
| \|z\| 3+ | 3 | #1 (3.195), #2 (3.418), #6 (3.130) |

**Seven of ten sit in the 1–3 band** where task 04 found this book's losses
concentrated, and all ten sit well above the 0.60 entry band (|z|/band 1.86 to
5.70). On the base rate, that is the argument the brief hoped for.

**The forward paths do not support it.** Both trades that would actually have
stopped out came from the **3+** refusals (#1 at 3.195 → stopped; #2 at 3.418 →
stopped). Every refusal in the 1–3 band, in episode B, would have made money —
they are the bars of a spread on its way to a 6.3σ reversion. The 1–3 region is
where this book lost money *across the phase*; it is not where these particular
refusals were heading.

So the honest reading is: **the zone argument is a prior, and here the actual
outcomes beat it.** It should not be written down as a finding. Note also that
the depth split here runs opposite to task 04's phase-wide result — on n=2
stops, which settles nothing either way.

---

## 3c. The re-entry shape the block does not cover

`side_blocked` fires only after a **stop**. A reverted or refit-dropped exit
followed by a same-side re-entry passes straight through. Counting every close
on the whole record that is followed by a re-entry on the same underlying —
treating `KAS/ETC` and `ETC/KAS` as one pair and flipping the side when the
orientation reverses:

**27 close → re-entry transitions, of which 20 follow a non-stop close.**

| window after a non-stop close | re-entries | of which **same side** |
|---|---|---|
| ≤ 1 bar | 2 | **0** |
| ≤ 3 bars | 8 | **3** |
| ≤ 6 bars | 12 | **5** |

**Base rate:** of the 20 re-entries after a non-stop close, **10 are same-side —
50%.** Same-side re-entry is a coin flip, not an anomaly. Median gap to
re-entry is about 6 hours. So "three round trips in six hours" is a statement
about churn frequency on an active pair, not about side.

**Outcomes — this is the comparison the brief asks for:**

| population | n | reverted | stopped | refit_drop | **stop rate** |
|---|---|---|---|---|---|
| same-side re-entry after a non-stop close | 10 | 8 | 2 | 0 | **20%** |
| opposite-side re-entry after a non-stop close | 10 | 6 | 2 | 2 | **20%** |
| whole book, all risk-bearing entries (task 04) | 31 | — | 8 | — | 26% |

**The uncovered population is not worse. It is identical to the covered one and
slightly better than the book.** On Phase I evidence the block is not scoped too
narrowly — there is nothing extra to catch.

**One caveat that cuts the other way, and it deserves its own line.** The single
worst trade of Phase I — ETC/KAS entered 2026-08-21 05:00 at z=+1.195, stopped
at 10:00 for **−18.52** — *was* a same-side re-entry **2 bars** after a non-stop
exit. That is exactly the shape the 09-15 review flagged. Of the three quick
(≤3 bar) same-side re-entries in the record, one stopped and it was the worst
loss in the book:

| re-entered | pair | side | gap | outcome |
|---|---|---|---|---|
| 07-31 03:00 | AVAX/SOL | +1 | 1h | reverted |
| 08-20 22:00 | ETC/KAS | +1 | 3h | reverted (+6.44) |
| **08-21 05:00** | **ETC/KAS** | **−1** | **2h** | **stop (−18.52)** |

One event in three. Against a 26% base rate that is unremarkable arithmetic and
suggestive narrative, and the two should not be confused. It does mean the
2026-09-15 pattern has **one Phase I precedent** rather than none.

---

## 4. The question that actually decides it

The block's effect on the **distribution**, computed by applying the
counterfactual P&L to the ledger's own 79 NAV prints in time order:

| scenario | max drawdown | set at |
|---|---|---|
| **actual — block in force** | **1.779%** | 2026-08-21 10:00 |
| no block, episode A only | **2.273%** | 2026-08-17 19:01 |
| no block, episode B only | 1.760% | 2026-08-21 10:00 |
| **no block, both** | **2.273%** | 2026-08-17 19:01 |

**The block improved max drawdown by 0.494 percentage points — a 28% relative
reduction — at a cost of about 3.5 USDT.**

Episode A is what does it: two stops totalling −7.66 inside three hours on
2026-08-11, landing on an equity path that was already near a local trough.
Episode B's extra profit slightly *improves* the drawdown in isolation (1.760%),
but it cannot offset episode A because MDD takes the worst point, not the
average.

**Verdict on the framing the brief asks for: the block is return-reducing AND
risk-reducing.**

- Worst single outcome without the block: **−5.095**. With it: **0** in episode
  A, +13.40 in episode B.
- It removed both tails — the −5.10 stop and the +17.77 winner.
- Under the scoring — 40% Sharpe, 25% PnL, 20% ROI, 15% MDD, MDD monotone — it
  trades 0.34% of NAV in PnL/ROI terms for half a point of permanent drawdown,
  and it cuts the dispersion of daily returns, which is the Sharpe denominator.
  On a book whose Phase I weakness was named in the record as *return per unit
  of drawdown*, that is the side of the trade the score rewards.

**I am not going to convert that into a score delta.** Sharpe here is computed
on ~20 daily returns and the record already establishes that one −0.8% day moved
it from 9.30 to 5.66; a two-episode perturbation cannot be resolved against that
noise, and quoting a number would be inventing precision.

---

## 5. Is ten enough?

**No, and the honest count is worse than ten.**

- **Ten refusals are two blocking episodes.** The entry branch fires once per
  pair, so the five consecutive skips in each cluster are one decision observed
  five times. The effective sample is **n = 2**.
- **They disagree, and by more than their total.** +7.97 against −11.46, netting
  −3.5. Two observations pointing opposite ways, with a net an order of
  magnitude smaller than either component, is the signature of a sample that
  cannot separate signal from draw.
- **The logging gap is real and unquantified.** `side_blocked` shipped
  2026-08-09 23:28 (the restart is in the record). The eight stops in Phase I
  are spread across 07-20 to 08-21, so **five of them predate the logging** and
  any blocks they set are invisible. The ten are not the population.
- **One regime, two pairs, eleven days.** Nine of the ten refusals were logged
  under a `stressed` or `broken` regime rating.

**What would settle it.** The block's value is almost entirely a drawdown
argument, so the measurement has to be a drawdown one: roughly **15–20 blocking
episodes**, which at the Phase I rate of two per month is most of a Phase II, and
spanning more than one volatility regime. The cheaper route is the same one task
04 landed on — the outcome of each refusal is a **first-passage question**
(given z, κ and σ_eq, what is P(stop before exit)?), and `statarb/thresholds.py`
already computes it. Scoring that probability against the realised forward path
for every refusal, and for every *unblocked* entry as a control group, tests the
control on the whole record rather than on two episodes.

---

## 6. What the records cannot tell you

1. **The whole of Phase II**, including everything this brief's 09-15 update
   describes. The ledger ends 2026-08-21; the live ledger is on the droplet.
2. **A 25-hour hole in the XLM/XRP z path**, 08-11 19:00 → 08-12 20:01, because
   the pair left the candidate set at the 0/15 refit. Refusals 3–5 have their
   outcome determined by an inferred refit-drop at 20:00 whose **z is not
   logged**; I used the 19:00 reading of +2.690 and the resulting −0.312 is an
   estimate, not a measurement. It is also the smallest of the three figures in
   episode A, so the episode's sign does not depend on it.
3. **That a refit_drop would have fired at all** on 08-11 20:00 is an inference
   from the mechanism (`flatten` on any pair the refit does not keep) plus the
   08-13 precedent, not an observed event — no position was open to drop.
4. **Blocks before 2026-08-09** are unrecorded. Five of the eight stops predate
   the logging.
5. **Sizing of the refused entries** is assumed equal to the calibrating trade's
   on the same pair. `g = risk_per_pair × nav / dvol` does not depend on z, so
   this is close, but `dvol` is refit-dependent and the refused entries are
   hypothetical.
6. **P&L linear in z** over the counterfactual ranges, including episode B's
   6.3σ move. That is the same assumption `stop_analysis.py` makes and it is
   least safe at the largest excursion — which is the one carrying the block's
   entire measured cost.
7. **Whether the 08-11 block would have healed before eviction.** z was +2.690
   at 19:00 and the pair was evicted at 20:00; a fall below +0.60 in that hour
   is unobserved. It does not change the outcome — the block ends either way.

---

## Bottom line

**Unproven on P&L, favourable on risk, and the sample is two — not ten.** The
ten logged refusals are two blocking episodes that disagree: on XLM/XRP the
block prevented three trades worth **−7.97**, two of which would have stopped out
within an hour of entry; on KAS/ETC it prevented a long that would have made
**+17.77** and forced the agent into a later, smaller short, costing about
**−11.5** — so the net is roughly **−3.5 USDT, 0.34% of NAV**, and the sign of
that total flips if either episode is reversed. What survives the arithmetic is
not the P&L but the shape: the block **removed both tails**, and because
max drawdown is monotone it kept a permanent 0.494 points off the record —
**1.779% against 2.273%** without it, a 28% relative reduction bought for a third
of a percent of NAV. Under a 15% MDD weight on a book whose stated Phase I
weakness was return per unit of drawdown, that is the side of the trade the score
pays for, and it is why "it cost us money" is not a verdict against it. The
brief's newer worry does **not** reproduce in Phase I: same-side re-entry after a
non-stop close stops out at **20% on n=10**, identical to opposite-side re-entry
and below the book's 26% base rate, and same-side re-entry is a 50% coin flip
rather than a pathology — though the single worst trade of the phase (−18.52)
was exactly that shape, two bars after a reverted exit, which is one precedent
and not a pattern. Two findings are worth keeping regardless of the verdict:
the block's stated lifetime is wrong — on XLM/XRP it ended by **pair eviction at
a 0/15 refit**, not by z healing, because `blocked` does not survive a pair
leaving the universe — and the agenda's note that a block sat in front of the
best trade of the phase is **not what happened**: the winner was on the
unblocked side, and what the block actually displaced was a better trade on the
blocked one. **On this evidence the control should stay** — not because it is
proven, but because n=2 is no basis for removing a stated invariant whose only
measured effect on the scored metric is favourable. What would settle it is
15–20 episodes, or the first-passage probability in `thresholds.py` scored
against every refusal and every unblocked entry as a control.

---

## Provenance

- `track_record/phase1_submission/reasoning.jsonl` — 10 `skip` (all
  `side_blocked`), 8 `stop`, 38 `enter`, 19 `exit`, 4 `refit_drop`, 35 `refit`,
  79 NAV prints; span 2026-07-19 20:07 → 2026-08-21 16:00.
- `track_record/phase1_submission/fills/*.json` — 19 snapshots; both calibrating
  trades venue-reconciled, and both realised fee figures reproduce the brief's
  cost model to within 0.002 USDT.
- Control mechanics read from `deploy/ltp_agent.py`: `:845–849` (heal),
  `:874–914` (the skip and the entry zones), `:1073` (block set on stop),
  `:302–306` (what survives a refit), `:853–872` (refit_drop precedes entry).
- Context read before starting, per `CLAUDE.md`: `deploy/WEEKLY_REVIEW.md`
  standing context, newest entries, Open commitments; `deploy/LTP_STRATEGY.md`
  §`side_blocked`. Used for provenance and for the Phase II boundary only — no
  figure in this file comes from either.
- **Measured** — all ten refusals and their fields, both z paths, both frame
  checks, both calibrations, the cost model, the 3c counts and outcomes, and
  every drawdown figure.
- **Estimated, labelled in place** — the −0.312 refit-drop close in episode A
  (z at 20:00 not logged).
- **Assumed** — equal sizing for refused entries, and P&L linear in z.

*Created: this file only. No other file was modified.*
