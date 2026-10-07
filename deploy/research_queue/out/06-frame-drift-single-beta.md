# 06 — How much frame drift is there, measured on one beta?

Audit 2026-10-07. I recomputed every number here from the primary records listed in §0. No figure is taken from prose. That includes the week 8 decomposition table under test, this task's brief, and my own task 03 answer, which turns out to need correcting. This is evidence for a human decision, not a recommendation to act.

---

## The answer first: the week 8 table is half right

**The artefact column survives. Every pre-fix nonzero `mu_shift_sigma` is dominated by the beta-level term.** I reproduced it independently. Where the in-hold refit's frame can be fitted from priced records on an exact beta, the old formula reproduces the logged value to four decimals: 12.5476, 5.9244 and 91.9634. The mechanism is not in doubt.

**The same-beta column does not hold as written:**

- **ETH/BTC 09-27, "~+0.7", is wrong.** On one beta the shift is **+0.16**, range −0.28 to +0.60. The table used the 3-dp state-row beta 1.159. The exact live beta, 1.1587286683, was already in the ledger on the 09-27 15:00 `enter`. Because ln BTC ≈ 11.34, rounding alone moved the result by 0.6σ₀.
- **09-21, "~−0.1", is ≈ 0.** On the exact beta from the 09-21 09:00 `enter`, the value is −0.015, range −0.05 to +0.02. That is below the 0.10 flag.
- **09-15 "~−0.3" and 09-26 "~−0.1" cannot be signed.** Only 3-dp betas exist for either, and the rounding alone spans about ±0.3σ₀. The full ranges are −0.50 to +0.26 and −0.50 to +0.21.
  - The three corrections built on the 09-15 row still stand in substance: the 09-15 entry, week 7 decision 1, and the task 03 row. The 13.24 was the artefact, nothing material can be shown on one beta, and σ₁/σ₀ is 0.96–1.12.
  - The "−0.3σ" those corrections quote is a central value, not a measurement.
- **09-14, "~+1.4", survives.** It is +1.49, range +1.36 to +1.62. It is the only large one.
- **"Every nonzero Phase II shift is ≥90% this artefact" overstated.**
  - By the table's own numbers, 09-14 was 88%.
  - There is a **sixth pre-fix close the table predates: the 09-28 17:00 stop.** There the artefact is only **64%** of the logged 1.28, and the same-beta shift is **+0.47** (range +0.30 to +0.63).
  - The record still calls the pre-fix closes "the five".

## Two findings larger than the table

**1. The record's 2026-09-09 Phase I correction has the same defect.**

The brief says Phase I close records carry no leg prices. **All 27 Phase I `exit`/`stop` records carry `price_a` and `price_b`.** With those prices, plus exact in-hold betas from later `enter` records, both Phase I events can be reconstructed exactly. The reconstructed frames reproduce, to five decimals, the logged values they were not fitted to, including the corrupted ones.

- **KAS/ETC 2026-08-20: σ shrank to 0.599×; it did not double.**
  - The record says "σ_live/σ₀ = 2.047; μ moved away and tripled the raw deviation; σ doubling damped it back". That appears in `WEEKLY_REVIEW.md` (09-09), the `LTP_STRATEGY.md` 09-09 addendum, a test fixture, and my own task 03 answer.
  - That figure paired an entry-beta spread with a live-beta mean. This is the bug class under test here.
  - On one beta, the mean moved **−0.14σ₀, toward the long position**. The +6.44 is about 102% artefact.
  - The stop fired because the ruler shrank, not because the mean moved.
  - The paragraph that was retracted on 09-09 as wrong ("σ collapsed 40%, σ_live/σ₀ = 0.599") was right about σ.
- **FIL/AR 2026-08-09: the true entry-frame z at the exit is +0.133, not −0.665.**
  - −0.665 is the pre-09-09 hybrid coordinate, exactly as with KAS/ETC.
  - A short spread at +0.133 with `exit_z` 0 had not reverted in its own frame. The entry frame would have exited 7 hours later.
  - The 09-09 "second retraction" says the record's only admission of frame drift (the reversion note on the FIL/AR exit) was a false alarm. That retraction rests on −0.665 and is wrong.
  - The note's number was wrong, but its claim was right: on one beta the mean moved **+0.20σ₀ toward the position**.
  - Task 03's "zero exits change label" becomes **one**.

**2. Equilibrium drift is not distinguishable from refit noise in this record. The frame disagreement that changes outcomes is σ.**

- No same-beta shift in either phase lies outside the noise band implied by the spreads' own fitted autocorrelation. That band's 95% bound is 0.85–2.65σ₀.
- The 0.10 flag would fire on about 90% of refits even with no drift at all.
- Yet in **8 of the 10 holds that spanned a refit, the entry frame would have closed at a different hourly bar: 7 later, 1 earlier.**
- **The two stops the entry frame would not have taken (09-28, KAS/ETC 08-20) were both σ shrinking at the refit.** σ₁/σ₀ was 0.61–0.70 and 0.60 respectively. The mean did not move them.

---

## 0. Dispatch state, data, method

**The folder was not on the dispatched branch. I changed nothing about that.**

- The repo is checked out at a **detached `origin/live/track-record`** (`e7dff87`, the droplet's branch).
- The reflog shows `research/06-frame-drift-single-beta` checked out at 12:25:23 local time, then `origin/live/track-record` 10 seconds later. That is presumably step 0 of the dispatch: the 10-07 entry says the export was read there.
- On that checkout this brief does not exist and `deploy/` is weeks stale. The `CLAUDE.md` it carries still says Phase I runs to 08-21.
- I read the following from `research/06-frame-drift-single-beta` (`2a006c2`) with `git show`, read-only:
  - this brief;
  - `deploy/ltp_agent.py`, and its pre-09-09 form at `da7aadb^`;
  - `deploy/WEEKLY_REVIEW.md` and `deploy/LTP_STRATEGY.md`;
  - `deploy/research_queue/out/03-frame-drift-cost.md`;
  - `track_record/phase1_submission/reasoning.jsonl`, which is identical to the working-tree copy apart from line endings.
- I read the two `track_record/*.jsonl` files from the working tree, which *is* `origin/live/track-record`.
- I wrote this file into that working tree, untracked. It carries over when the research branch is checked out. Nothing was committed or pushed.

**`track_record/ltp_ledger_phase2.jsonl` is present.**

- 2,199 records.
- First record: 2026-09-09 15:00:56, a `refit`. Nothing precedes it, although the brief describes the slice as starting at 09-08 16:00.
- **Last record: 2026-10-07 19:00:22 UTC.** It is an `ai_spread_assessment` of 1000SHIB/DOGE at z −3.51, `holding: false`, regime "broken". That is the 19:00 bar, five hours after the 13:45 intra-bar stop.
- Export commit `e7dff87` "track: refresh phase II ledger slice", 19:14:07 UTC.
- `ltp_state_history.jsonl` has 69 rows, the last at 2026-10-06 23:50.

**What the code logs** (`entry_frame`; pre-09-09 form at `da7aadb^`):

| period | `z_in_entry_coords` | `mu_shift_sigma` |
|---|---|---|
| before 2026-09-09 | (ln a − **β₁**·ln b − μ₀)/σ₀ — hybrid | (μ₁ − μ₀)/σ₀, μ₁ fitted on **β₁** |
| 09-09 → 09-29 21:15 | (ln a − **β₀**·ln b − μ₀)/σ₀ — correct | (μ₁ − μ₀)/σ₀, μ₁ fitted on **β₁** — cross-beta |
| after 09-29 21:15 (`mu_shift_basis: "entry_beta"`) | correct | (μ₁′ − μ₀)/σ₀, μ₁′ = the live window's mean of ln a − **β₀**·ln b |

**The identity everything rests on.** μ₁ = mean_W(ln a) − β₁·m_b, and μ₁′ = mean_W(ln a) − β₀·m_b. Here m_b is the mean of ln p_b over the in-hold refit's μ window W, of length int(3·hl₁) bars. So:

- reported (pre-fix) = same-beta shift − Δβ·m_b/σ₀
- **artefact = −Δβ·m_b/σ₀**
- Δβ = β₁ − β₀

**Entry frame (σ₀, μ₀).** I used the two points the brief names. Each gives s = ln a − β₀·ln b = μ₀ + z·σ₀: the `enter` print, and the close's `z_in_entry_coords` with its prices on β₀. Where more records share the entry frame, I fitted all of them as a check. Those are other decision records in the entry's refit epoch, and the `z_entry` of five-minute samples.

**Live frame (β₁, μ₁, σ₁).** With an exact β₁ and two or more priced records in the in-hold epoch, I fitted (μ₁, σ₁). Then (μ₁ − μ₀)/σ₀ must reproduce the logged pre-fix value, which is an independent check of (μ₀, σ₀). Otherwise μ₁ = μ₀ + reported·σ₀ (exact), and σ₁ follows from the close's live z as a function of β₁.

**Direction convention.** A shift is **toward** the position when side × shift < 0. In that case the equilibrium moved toward the spread's entry-side level, which pulls live z toward the exit: the 08-05 "target came to us" pattern. It is **away** when side × shift > 0, which pushes live z toward the stop. Task 03's toward/away labels were assigned to cross-beta values and are void; they were also not consistent with this convention.

---

## 1. Reproduce or refute the decomposition

Every Phase II close with a nonzero `mu_shift_sigma` is listed: six pre-fix closes and the two post-fix closes the amendment names. Both post-fix values are verified below, at 0.527036 and 0.417781.

**Inputs, straight from the ledger:**

| # | close (UTC) | pair | side | entry record | β₀ (entry, exact) | z at entry | entry prices a / b | close prices a / b | z (live) | `z_in_entry_coords` | `mu_shift_sigma` logged | basis |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 09-14 12:01 exit | 1000SHIB/DOGE | -1 | 09-12 12:01 | 0.6648952777 | +3.4116 | 0.00538703 / 0.08505 | 0.005232 / 0.08403 | -0.1600 | +1.3930 | 12.5476 | none (pre-fix) |
| 2 | 09-15 20:00 stop | 1000SHIB/DOGE | +1 | 09-15 07:00 | 0.7118725634 | -0.9568 | 0.00515347 / 0.08266 | 0.00500676 / 0.08083938 | -3.5415 | -3.9908 | 13.2421 | none (pre-fix) |
| 3 | 09-21 07:00 exit | 1000SHIB/DOGE | -1 | 09-20 05:00 | 0.7894401572 | +0.9118 | 0.00539358 / 0.08545796 | 0.005533 / 0.089 | -0.2501 | -0.2125 | 5.9244 | none (pre-fix) |
| 4 | 09-26 17:00 stop | 1000SHIB/DOGE | -1 | 09-26 01:00 | 0.8401811670 | +0.6080 | 0.00594101 / 0.09851 | 0.00607 / 0.09839 | +5.3753 | +7.3335 | 1.1186 | none (pre-fix) |
| 5 | 09-27 12:00 exit | ETH/BTC | -1 | 09-26 13:00 | 1.2009384295 | +0.8934 | 2687.99 / 84009.3 | 2709.33 / 84885.9 | -0.0793 | +0.0190 | 91.9634 | none (pre-fix) |
| 6 | 09-28 17:00 stop | 1000SHIB/DOGE | +1 | 09-28 08:00 | 0.8464509781 | -1.3070 | 0.00560871 / 0.09246228 | 0.00567921 / 0.09432075 | -3.6051 | -1.9031 | 1.2807 | none (pre-fix) |
| 7 | 09-30 19:54 exit | 1000SHIB/DOGE | -1 | 09-29 10:00 | 0.8528050620 | +0.6829 | 0.005808 / 0.09550336 | 0.00570808 / 0.09378 | -0.0599 | +0.4483 | 0.5270 | entry_beta |
| 8 | 10-03 07:01 exit | 1000SHIB/DOGE | -1 | 10-03 00:00 | 0.8632052442 | +1.3242 | 0.00572597 / 0.09285 | 0.00569367 / 0.09288737 | -0.2933 | +0.1170 | 0.4178 | entry_beta |

**Entry frame, live beta, and Δβ.** The two-point entry frame is exact. Wherever more points exist, the fit over all of them returns the same σ₀ and μ₀ to the last digit shown, with residuals of order 1e-13 in z. On 10-03 the `refit` record carries the frame, and it matches. For #1, #3 and #5 there is no second entry-frame point. The independent check there is the live frame: it is fitted from 6, 3 and 3 priced records on the exact β₁, and gives (μ₁ − μ₀)/σ₀ = **12.5476, 5.9244, 91.9634**, which is the logged value each time.

| # | close | σ₀ (two-point) | μ₀ (two-point) | independent check of the entry frame | in-hold refit | live β source | β₁ | β₁ range used | Δβ = β₁ − β₀ |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 09-14 12:01 | 0.01049168 | -3.62090978 | no third entry-frame point; checked through the live frame (logged cross-beta value reproduced exactly, see above) | 09-14 12:00 (hl 18.67 h) | enter 09-14T13:00 (exact) | 0.7118725634 | exact | +0.046977 |
| 2 | 09-15 20:00 | 0.00429365 | -3.48926450 | 7 points, max residual 3e-13 z | 09-15 12:00 (hl 15.23 h) | state row 2026-09-15 (3 dp) | 0.7350000000 | ±0.0005 → [0.7345, 0.7355] | +0.023127 |
| 3 | 09-21 07:00 | 0.00581650 | -3.28603926 | 6 points, max residual 5e-13 z | 09-20 10:00 (hl 13.98 h) | enter 09-21T09:00 (exact) | 0.8035820542 | exact | +0.014142 |
| 4 | 09-26 17:00 | 0.00334603 | -3.18070910 | 6 points, max residual 1e-13 z | 09-26 09:00 (hl 13.04 h) | state row 2026-09-26 (3 dp) | 0.8420000000 | ±0.0005 → [0.8415, 0.8425] | +0.001819 |
| 5 | 09-27 12:00 | 0.00521376 | -5.72516872 | no third entry-frame point; checked through the live frame (logged cross-beta value reproduced exactly, see above) | 09-27 09:00 (hl 34.82 h) | enter 09-27T15:00 (exact) | 1.1587286683 | exact | -0.042210 |
| 6 | 09-28 17:00 | 0.00730326 | -3.15852763 | 6 points, max residual 2e-13 z | 09-28 09:01 (hl 13.42 h) | state row 2026-09-28 (3 dp) | 0.8490000000 | ±0.0005 → [0.8485, 0.8495] | +0.002549 |
| 7 | 09-30 19:54 | 0.00777532 | -3.15093605 | 251 points, max residual 1e-13 z | 09-30 08:01 (hl 14.87 h) | refit record (exact) | 0.8543961756 | exact | +0.001591 |
| 8 | 10-03 07:01 | 0.00497374 | -3.11768937 | 248 points, max residual 4e-13 z; refit record σ 0.0049737435 μ -3.117689366 — identical | 10-03 07:00 (hl 14.88 h) | refit record (exact) | 0.8754360966 | exact | +0.012231 |

**The decomposition** (pre-fix closes; m_b and its range are explained in §3):

| # | close | reported (cross-beta) | artefact −Δβ·m_b/σ₀ | **same-beta shift** (bridge m_b, central β₁) | same-beta with close-print m_b | range: β₁ rounding × m_b ±2 sd | σ₁/σ₀ | week 8 table: Δβ / artefact / same-beta | artefact share of reported |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 09-14 12:01 exit | 12.5476 | 11.059 | **+1.489** | +1.459 | [+1.36, +1.62] | 0.409 (fit, 6 pts) | +0.047 / ~11.12 / ~+1.4 | 88% |
| 2 | 09-15 20:00 stop | 13.2421 | 13.360 | **-0.118** | -0.306 | [-0.50, +0.26] | 0.96 – 1.12 (β-dependent) | +0.023 / ~13.55 / ~-0.3 | 101% |
| 3 | 09-21 07:00 exit | 5.9244 | 5.939 | **-0.015** | +0.043 | [-0.05, +0.02] | 1.021 (fit, 3 pts) | +0.015 / ~6.06 / ~-0.1 | 100% |
| 4 | 09-26 17:00 stop | 1.1186 | 1.264 | **-0.145** | -0.142 | [-0.50, +0.21] | 1.33 – 1.46 (β-dependent) | +0.002 / ~1.26 / ~-0.1 | 113% |
| 5 | 09-27 12:00 exit | 91.9634 | 91.804 | **+0.160** | +0.083 | [-0.28, +0.60] | 0.809 (fit, 3 pts) | -0.042 / ~91.29 / ~+0.7 | 100% |
| 6 | 09-28 17:00 stop | 1.2807 | 0.815 | **+0.465** | +0.457 | [+0.30, +0.63] | 0.61 – 0.70 (β-dependent) | not in the table (close is 09-28, the table was written 09-27) | 64% |

The "artefact share" column is the artefact as a percentage of the logged value. The σ₁/σ₀ column is the ruler change at the in-hold refit. Where β₁ is only known to 3 dp, σ₁ depends on it, and the range is shown.

**Verdict on the week 8 table:**

- **Artefact column: reproduced.** Within 0.01–0.5σ₀ on magnitudes of 1.1–92σ₀. The differences are the m_b substitute and, for ETH/BTC, the rounded beta.
- **Same-beta column: two rows wrong, two unsignable, one right.**
  - Wrong: ETH/BTC (+0.7 → +0.16) and 09-21 (−0.1 → ≈0). In both, the table used a 3-dp beta where the exact beta was in the ledger.
  - Unsignable: 09-15 and 09-26, which have only 3-dp betas.
  - Right: 09-14 (+1.4 → +1.49).
- **Omitted, by date:** the 09-28 stop. Its shift is the largest determinable pre-fix one after 09-14.
- **The claim "≥90% artefact" does not hold for 09-14 (88%) or 09-28 (64%).**

## 2. Where the live beta came from, and what rounding does

The best source per case is in the table above.

- **An exact β₁ exists for three of the six pre-fix closes:** 09-14, 09-21 and ETH/BTC, each from an `enter` record after the in-hold refit and before the next one.
- **The three without one are all stops** (09-15, 09-26, 09-28). That is not chance. A stop blocks re-entry on that side, so no `enter` follows inside the epoch, and only the 3-dp state row carries β₁.
- **The two post-fix closes** take β₁ from the `refit` record, which carries it exactly from 09-30 08:01.
- **No other record narrows the three 3-dp cases.** In each, the stop is the only priced record of the pair in its epoch. `ai_spread_assessment`, `skip` and state rows carry z but no prices.

How the ±0.0005 rounding propagates, at m_b fixed:

| close | ±0.0005·\|m_b\|/σ₀ | result |
|---|---|---|
| 09-15 stop | ±0.29σ₀ | same-beta −0.41 … +0.17 before m_b uncertainty — **spans "material" in both directions and spans the sign. I do not choose.** |
| 09-26 stop | ±0.35σ₀ | −0.49 … +0.20 — **spans material both ways and the sign. I do not choose.** |
| 09-28 stop | ±0.16σ₀ | +0.31 … +0.62 — stays material and positive |
| ETH/BTC (had it been rounded) | ±1.09σ₀ | this is how the table reached +0.7 |

Measured on the two post-fix closes (§3), rounding alone moved the estimate by **+0.12σ₀ and +0.21σ₀**. **Rounding is the weak input, not the window mean.**

## 3. `mu` is a window mean: the m_b substitute, and its measured error

The ledger never carries mean(ln p_b) over the refit window. I compared three substitutes:

- **(a) the close's own print**, as the brief suggests;
- **(b) the mean of the b-leg prints that fall inside the window**;
- **(c) a bridge estimate.** This treats ln p_b as a random walk and conditions on every b-leg print from 48 h before the window to the close. The window mean is then Gaussian: its mean is the piecewise-linear interpolation, flat beyond the end prints. Its sd comes from the Brownian-bridge covariance.

The hourly volatility comes from the record's own prints:

| leg | hourly vol | source |
|---|---|---|
| DOGE | 0.83%/h | 103 decision-print gaps (0.70%/h from 717 five-minute increments; the larger is used) |
| BTC | 0.26%/h measured; **0.64%/h used** | only 5 increments; 0.64%/h is the χ² 95% upper bound |
| ETC | 0.87%/h | 21 increments |
| AR | **assumed** 0.83%/h | its 3 increments give 0.12%/h, which I do not trust |

**I use (c) as the central value** and report (a) beside it.

| # | close | μ window: w = int(3·hl₁) bars, span (bar closes) | ln p_b prints inside window | (a) close print | (b) mean of in-window prints | (c) bridge estimate ± sd |
|---|---|---|---|---|---|---|
| 1 | 09-14 12:01 | 56 bars, 09-12 05:00 → 09-14 12:00 | 1 (range -2.46452 … -2.46452) | -2.47658 | -2.46452 | -2.46979 ± 0.01432 |
| 2 | 09-15 20:00 | 45 bars, 09-13 16:00 → 09-15 12:00 | 6 (range -2.49302 … -2.47658) | -2.51529 | -2.48306 | -2.48029 ± 0.00852 |
| 3 | 09-21 07:00 | 41 bars, 09-18 18:00 → 09-20 10:00 | 5 (range -2.46093 … -2.41039) | -2.41912 | -2.43654 | -2.44284 ± 0.00690 |
| 4 | 09-26 17:00 | 39 bars, 09-24 19:00 → 09-26 09:00 | 5 (range -2.34060 … -2.31344) | -2.31882 | -2.32217 | -2.32550 ± 0.00672 |
| 5 | 09-27 12:00 | 104 bars, 09-23 02:00 → 09-27 09:00 | 1 (range 11.33868 … 11.33868) | 11.34906 | 11.33868 | 11.33959 ± 0.01096 (± 0.02718 at the upper vol) |
| 6 | 09-28 17:00 | 40 bars, 09-26 18:00 → 09-28 09:00 | 5 (range -2.38095 … -2.32371) | -2.36105 | -2.34377 | -2.33605 ± 0.00493 |

The windows are taken as contiguous hourly bars ending at the refit hour. The 10-01 entry records that the live panel was never truncated, but that is an assumption here, not a measurement.

**Measured error, on the two post-fix closes.** For these, the refit record's μ₁ and the logged same-beta value fix m_b exactly: m_b = (μ₀ + logged·σ₀ − μ₁)/Δβ. The cross-beta value the pre-fix code *would* have logged, (μ₁ − μ₀)/σ₀, is constructed from the refit record, not logged. I applied the §1/§3 procedure to it as if the field were absent:

| close | logged same-beta (truth) | emulated pre-fix value (μ₁ − μ₀)/σ₀ | exact m_b (from the logged value and the refit record) | m_b substitute | its error | reconstructed same-beta, exact β₁ | error vs logged | same, with the 3-dp β₁ (range) | error from rounding alone |
|---|---|---|---|---|---|---|---|---|---|
| 09-30 19:54 | 0.5270 | 1.0110 | -2.36488 | close print: -2.36680 | -0.00192 | 0.5266 | -0.0004 | 0.854: +0.647 [+0.495, +0.799] | +0.121 |
| 09-30 19:54 | 0.5270 | 1.0110 | -2.36488 | bridge, decision prints only (the pre-fix information set): -2.35587 | +0.00902 | 0.5289 | +0.0018 | 0.854: +0.649 [+0.497, +0.800] | +0.120 |
| 09-30 19:54 | 0.5270 | 1.0110 | -2.36488 | bridge incl. 5-min z_samples: -2.35950 | +0.00538 | 0.5281 | +0.0011 | 0.854: +0.648 [+0.497, +0.800] | +0.120 |
| 10-03 07:01 | 0.4178 | 6.2226 | -2.36054 | close print: -2.37637 | -0.01583 | 0.3789 | -0.0389 | 0.875: +0.587 [+0.348, +0.826] | +0.208 |
| 10-03 07:01 | 0.4178 | 6.2226 | -2.36054 | bridge, decision prints only (the pre-fix information set): -2.36462 | -0.00408 | 0.4078 | -0.0100 | 0.875: +0.615 [+0.377, +0.853] | +0.207 |
| 10-03 07:01 | 0.4178 | 6.2226 | -2.36054 | bridge incl. 5-min z_samples: -2.35734 | +0.00320 | 0.4257 | +0.0079 | 0.875: +0.632 [+0.395, +0.869] | +0.207 |

- **σ₀/μ₀ reconstruction error: zero** to the precision logged.
- **m_b substitution error, with the exact β₁:** at most **0.04σ₀** with the close print, and at most **0.01σ₀** with the bridge on decision prints only. Decision prints are the information set the pre-fix closes had. The bridge's actual misses were 0.99 and 0.54 of its stated sd, so its error bars are honest on n = 2.
- **3-dp rounding error alone: +0.12σ₀ and +0.21σ₀.** That is the dominant error whenever an exact β₁ is missing.
- **When the close print is a bad substitute.** The close print is poor when the b leg moves after the window closes. On KAS/ETC (§4), ETC rose 5% between the window's end and the stop. The close print would put the same-beta shift at −0.44, against −0.14 from the bridge and −0.16 from the in-window mean.

---

## 4. Phase I's two events: determinable after all

The brief expected these to be compromised twice over, and to be possibly undeterminable. They are not, because the prices exist.

Before 09-09, the close's `z_in_entry_coords` is the hybrid (ln a − β₁·ln b − μ₀)/σ₀. Once β₁ is known exactly, that is still a valid equation in (μ₀, σ₀): s = ln a − β₁·ln b = μ₀ + z·σ₀. For both events β₁ is known exactly, from an `enter` after the in-hold refit in the same epoch. Each reconstruction is checked against values it was not fitted to.

| | **FIL/AR 08-09 23:00 exit** (side −1) | **KAS/ETC 08-20 02:00 stop** (side +1) |
|---|---|---|
| entry | 08-08 21:01, β₀ 0.7768718801, z +1.2402, prices 0.7178 / 1.809 | 08-19 18:00, β₀ 0.9721173236, z −1.3719, prices 0.02589 / 6.298 |
| close prices; live z | 0.70286159 / 1.79747834; −0.0579 | 0.026695 / 6.63976937; −4.7518 |
| logged `z_in_entry_coords` (hybrid) / `mu_shift_sigma` (cross-beta) | −0.6654 / −0.6106 | +3.5970 / +6.4428 |
| in-hold refit; β₁ (exact, source) | 08-09 21:00, hl 21.59 h; **0.7966167339** (08-10 10:00 `enter`); Δβ +0.019745 | 08-19 19:01, hl 16.68 h; **0.9326583952** (08-20 11:00 `enter`); Δβ −0.039459 |
| σ₀ / μ₀ | **0.01450791 / −0.81006624** (entry print + the hybrid close point on β₁) | **0.01085687 / −5.42792565** (five entry-epoch prints; the hybrid point fits them to 3e-13) |
| independent check | live frame fitted from 3 priced records on β₁ gives (μ₁−μ₀)/σ₀ = **−0.61056** = logged | the five-point frame alone predicts the logged hybrid **+3.59701**; a five-point live frame gives (μ₁−μ₀)/σ₀ = **+6.44279** = logged |
| **true `z_in_entry_coords`** (on β₀) | **+0.133** | **−3.283** (as the record already says) |
| **σ₁/σ₀** | 0.947 | **0.599** |
| m_b (bridge ± sd) | 0.5916 ± 0.019 (2 AR prints; vol assumed) | 1.8100 ± 0.005 (8 ETC prints) |
| artefact / **same-beta shift** | −0.805 / **+0.195** (±2 sd: +0.14 … +0.25; at twice the vol +0.09 … +0.30) | +6.578 / **−0.136** (±2 sd: −0.17 … −0.10; at twice the vol −0.21 … −0.06) |
| direction | toward | toward |
| what the record and task 03 say | σ₀ 0.008432; entry-frame z −0.665, "the exit survives"; the reversion note was "a false alarm" | σ₁/σ₀ **2.047**, "σ doubled"; "μ moved away and tripled the raw deviation" |

**What can be concluded.**

**KAS/ETC.**

- 102% of the +6.44 is the beta-level artefact. On one beta the equilibrium moved −0.14σ₀, slightly toward the long position, and within noise (§5).
- The stop fired in the live frame because σ shrank to 0.60× at the refit, which inflated z by 1.67×. Decomposed at the stop:

```
z_live = (z_entry − same − Δβ·(ln p_b − m_b)/σ₀) · σ₀/σ₁
       = (−3.283 + 0.136 + 0.302) × 1.670
       = −4.752   (logged −4.752)
```

- The deviation from the live mean actually *shrank* from −3.28 to −2.85σ₀. The ruler did the rest.
- The 2.047 in the record comes from pairing the β₀ spread with the β₁ mean. That is the same mixing this task audits, made while correcting it. The paragraph retracted on 09-09 ("σ collapsed 40%, 0.599") was right about σ, though it reached that by checking logged fields against each other.

**FIL/AR.**

- On β₀ the spread was still +0.133σ₀ above the entry mean when the live frame exited at −0.058.
- The live exit happened because the same-beta mean rose +0.195σ₀ toward the spread (`(0.133 − 0.195 + 0.007) × 1.056 = −0.058`). That is a small instance of the "target came to us" pattern `entry_frame` was built to catch.
- So the reversion note's claim on this +6.03 winner was **correct**, and its number (−0.67) was not. The 09-09 retraction applied the new directional test to the wrong number.

**What cannot be determined.**

- Only m_b, the mean of ln AR (08-07 06:00 → 08-09 21:00) and of ln ETC (08-17 18:00 → 08-19 19:00).
- It is worth ±0.05σ₀ on FIL/AR (more if AR was much more volatile than assumed) and ±0.04σ₀ on KAS/ETC.
- **The hourly klines for those windows would determine both exactly.** Since 2026-09-29 the refit stores that quantity itself, `mu_entry_beta`, for every held pair.

---

## 5. The sample, restated

A genuine frame-drift event here means a **same-beta** shift. Both phases together have **10** closes whose hold spanned a refit: 8 in Phase II and 2 in Phase I. They are the only closes with a nonzero shift. Every other instrumented close has exactly 0.0 and no refit inside the hold.

| close | pair | side | same-beta shift | range | vs 0.10 | direction | 95% noise bound, φ from fitted hl | P(\|shift\| ≥ 0.10 \| no drift) | observed \|shift\| percentile under that null |
|---|---|---|---|---|---|---|---|---|---|
| 09-14 12:01 exit | 1000SHIB/DOGE | −1 | **+1.489** | +1.36 … +1.62 | ≥ 0.10 | toward | 2.65 | 0.94 | 0.73 |
| 09-15 20:00 stop | 1000SHIB/DOGE | +1 | −0.118 | −0.50 … +0.26 | **undetermined** | undetermined (central: toward) | 1.76 | 0.93 | 0.08 |
| 09-21 07:00 exit | 1000SHIB/DOGE | −1 | −0.015 | −0.05 … +0.02 | < 0.10 | ≈ 0 | 1.88 | 0.92 | 0.01 |
| 09-26 17:00 stop | 1000SHIB/DOGE | −1 | −0.145 | −0.50 … +0.21 | **undetermined** | undetermined (central: away) | 1.99 | 0.93 | 0.11 |
| 09-27 12:00 exit | ETH/BTC | −1 | +0.160 | −0.28 … +0.60 | **undetermined** | undetermined (central: toward) | 0.85 | 0.88 | 0.19 |
| 09-28 17:00 stop | 1000SHIB/DOGE | +1 | **+0.465** | +0.30 … +0.63 | ≥ 0.10 | **away** | 1.94 | 0.93 | 0.34 |
| 09-30 19:54 exit | 1000SHIB/DOGE | −1 | **+0.527** | exact (logged) | ≥ 0.10 | toward | 1.68 | 0.92 | 0.43 |
| 10-03 07:01 exit | 1000SHIB/DOGE | −1 | **+0.418** | exact (logged) | ≥ 0.10 | toward | 1.79 | 0.93 | 0.32 |
| 08-09 23:00 exit | FIL/AR | −1 | **+0.195** | +0.14 … +0.25 | ≥ 0.10 | toward | 1.28 | 0.91 | 0.17 |
| 08-20 02:00 stop | KAS/ETC | +1 | −0.136 | −0.17 … −0.10 | at the line | toward | 1.58 | 0.92 | 0.11 |

**Against 0.10:**

- 5 definite: 09-14, 09-28, 09-30, 10-03, FIL/AR.
- 1 at the line: KAS/ETC.
- 3 undetermined: 09-15, 09-26, ETH/BTC.
- 1 below: 09-21.
- Of the 6 with a determinable sign, **5 are toward and 1 is away.**

**Against the noise band: 0 of 10.**

- **The noise model.** The same-beta shift is (window mean at the in-hold refit − window mean at the entry refit) / (window sd at the entry refit), all on β₀.
  - I simulated it under no drift at all: a stationary AR(1) spread with φ = 2^(−1/hl).
  - Here hl is the agent's own fitted half-life at the entry refit; the windows and the gap between refits (23–48 h) are each case's actual values; 20,000 paths per case.
  - Under that null the median \|shift\| is 0.4–0.9σ₀. **The 0.10 flag fires 88–94% of the time with no drift.**
  - The observed shifts sit at the 1st–73rd percentile.
- **The fitted-hl null is probably too wide.** 9 of the 10 observed shifts fall below its median (one-sided binomial p ≈ 0.01).
  - The record's own hourly z autocorrelation suggests shorter memory: within-epoch half-life about 2–3 h (biased low on short epochs), five-minute `z_sample` about 9 h.
  - At hl 4 h the 95% band narrows to about 1.1σ₀ for these pairs; at hl 2 h, to about 0.8σ₀. Even then P(\|shift\| ≥ 0.10 \| no drift) is ≥ 0.79 for the 1000SHIB/DOGE cases and 0.57 for ETH/BTC.
  - **Under the shortest-memory reading, 09-14's +1.49 would be the only determinable event outside the band.** ETH/BTC's undetermined range also reaches past it at the top end. Under the agent's own fitted half-lives, none is.

**The "toward" lean is what conditioning on a close produces.** This set consists of positions that *closed*. A refit draw that pulls the mean toward an open spread makes the live exit fire. A draw that pushes it away does not, and that hold continues. Three of the four definite "toward" exits closed within two bars of the refit that produced the shift: 09-14 and 10-03 at the refit bar itself, FIL/AR two bars later. Before reading 5:1 as a direction, a symmetric-noise explanation has to be excluded, and with this selection it cannot be.

**Against task 03's bar.** Task 03 wanted double-digit drift events with a consistent direction, and wrote "2 of 9 closes drift at all; one toward, one away".

- The corrected sample is **10 refit-spanning closes, 5–6 above 0.10, 0 above the noise band.**
- The direction lean is explained by selection.
- Task 03's two Phase I events were both mis-measured: KAS/ETC's "away +6.44" is −0.14 toward, and FIL/AR's −0.61 is +0.20.
- **The bar is not reached, and it is further away than task 03 thought.** At 0.10 the count is mostly noise, and at the noise band it is zero.

---

## 6. Did the frame choice change any outcome?

For each of the 10 refit-spanning holds I computed entry-frame z at every agent bar from entry onward. Each bar's live z comes from `ai_spread_assessment`, which is logged every bar for every active pair. Each epoch's frame is the one reconstructed above, or fitted from that epoch's priced records. The transform is exact:

```
z_entry = (z_live·σ_k + μ_k + (β_k − β₀)·ln p_b(t) − μ₀) / σ₀
```

It is approximate only through ln p_b(t), which is bridge-interpolated between prints (±2 sd shown), and through β_k where only 3 dp exist. Rules: exit at `exit_z` 0 (directional), stop at 3.5, and max-hold at 3 × the live half-life, unchanged. Where the entry frame had not fired by the actual close, I continued the position past it.

**Sanity check.** Applying the live rule to the same bar series reproduces every actual close at its actual bar.

| # | close | actual (live frame) | entry-frame z at that bar | entry frame would have fired at | entry-frame z there | bars later (+) / earlier (−) | how exact is the transform | spread move between the two closes, σ₀ (signed for the position) | ≈ USDT (estimate) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 1000SHIB/DOGE 2026-09-14 12:01 | reverted at 09-14 12:01 | +1.393 | max_hold at 09-14 21:00 (no entry-frame exit or stop in the observable bars) | +2.463 | +9 | β₁ exact; ln p_b interpolated between prints; 24 bars in an epoch whose frame is unknown | -1.07 | -4.2 |
| 2 | 1000SHIB/DOGE 2026-09-15 20:00 | stop at 09-15 20:00 | -3.991 | stop at 09-15 20:00 (an exit at 13:00 only at the joint extreme of both uncertainties — see notes) | -3.991 | +0 | β₁ 3 dp + ln p_b interpolated | +0.00 | +0.0 |
| 3 | 1000SHIB/DOGE 2026-09-21 07:00 | reverted at 09-21 07:00 | -0.213 | exit at 09-21 07:00 | -0.213 | +0 | β₁ exact; ln p_b interpolated between prints | -0.00 | -0.0 |
| 4 | 1000SHIB/DOGE 2026-09-26 17:00 | stop at 09-26 17:00 | +7.333 | stop at 09-26 15:00 at the central β₁ (16:00 if β₁ ≥ 0.84231; an exit at 09:01 if β₁ ≥ 0.84247 — see notes) | +3.608 | -2 | β₁ 3 dp + ln p_b interpolated | +3.73 | +5.0 |
| 5 | ETH/BTC 2026-09-27 12:00 | reverted at 09-27 12:00 | +0.019 | exit at 09-27 14:00 | -0.296 | +2 | β₁ exact; ln p_b interpolated between prints | +0.32 | +0.8 |
| 6 | 1000SHIB/DOGE 2026-09-28 17:00 | stop at 09-28 17:00 | -1.903 | exit at 09-29 12:00 | +0.154 | +19 | β₁ 3 dp + ln p_b interpolated | +2.06 | +5.9 |
| 7 | 1000SHIB/DOGE 2026-09-30 19:54 | reverted at 09-30 19:54 | +0.448 | exit at 10-01 02:00 | -0.073 | +7 | exact (refit records / priced fits) | +0.52 | +1.6 |
| 8 | 1000SHIB/DOGE 2026-10-03 07:01 | reverted at 10-03 07:01 | +0.117 | exit at 10-03 08:00 | -0.261 | +1 | exact (refit records / priced fits) | +0.38 | +1.0 |
| 9 | FIL/AR 2026-08-09 23:00 | reverted at 08-09 23:00 | +0.133 | exit at 08-10 06:00 | -0.113 | +8 | β₁ exact; ln p_b interpolated between prints | +0.25 | +1.5 |
| 10 | KAS/ETC 2026-08-20 02:00 | stop at 08-20 02:00 | -3.283 | exit at 08-20 11:00 | +1.447 | +9 | β₁ exact; ln p_b interpolated between prints | +4.73 | +22.5 |

**Notes on the rows:**

- **#1 (09-14).** The first in-hold refit (09-13 12:00) started an epoch with **no priced record**, so 24 bars of the entry-frame path are unknown. The bars on either side are +1.12 (09-13 11:00) and +1.39 (the close), and the live z in between stayed 0.36–0.91. In the exact 09-14 frame after the close, the entry frame never reaches 0 or 3.5 before max-hold fires at 21:00. **"Later" holds unless the entry frame exited during those 24 unobservable bars.**
- **#2 (09-15).** At 13:00 the entry-frame z is −0.33. The β rounding range (−0.62 to −0.05) and the interpolation range (−0.49 to −0.17) each stay below 0; only their joint extreme reaches +0.11. Central reading: same bar.
- **#4 (09-26). The rounded beta decides the outcome.**
  - For 81% of the rounding interval (β₁ < 0.84231, including the central 0.842), the entry frame stops at **15:00**, at 3.43–3.79.
  - For the next 16% (0.84231 ≤ β₁ < 0.84247) it stops at 16:00.
  - For the top ~3% (β₁ ≥ 0.84247) it would instead have **exited at 09:01**, near the entry level, at −0.02 to +0.63.
  - This agrees with the week 8 note ("1–2 hours earlier, 3.45–3.79 at 15:00").
  - Here σ *widened* at the refit (σ₁/σ₀ 1.33–1.46), which **delayed** the live stop. It is the one case where the trailing frame fired later.
- **#6 (09-28).** The entry frame's worst bar is −3.06 (09-29 06:00; range −3.15 to −2.97 over rounding and interpolation), so it never stops. It exits at 09-29 12:00, in the next epoch, whose frame is exact (β from the 09-29 10:00 `enter`, fitted to 119 priced records with residuals of 6e-14). **A refit one hour into the hold cut σ to 0.61–0.70×; the stop was the ruler.**
- **#7 (09-30).** The close is the off-schedule restart bar at 19:54. The entry frame had not reverted (+0.45); it does so at 10-01 02:00. Both frames are exact (refit records and `z_sample` prices).
- **#9 (FIL/AR).** +8 agent bars is 7 hours; one of them is an off-schedule bar at 23:28.

**What moved z at the close.** This is the exact identity from §4, so each row closes to the logged live z:

| close | z_entry (exact) | − same-beta shift | − β term Δβ·(ln p_b − m_b)/σ₀ | = deviation on the live mean, in σ₀ | × σ₀/σ₁ | = z_live (logged) | what moved z |
|---|---|---|---|---|---|---|---|
| 09-14 12:01 1000SHIB/DOGE exit | +1.393 | -1.489 | +0.030 | -0.065 | 2.444 | -0.160 (-0.160) | mean |
| 09-15 20:00 1000SHIB/DOGE stop | -3.991 | +0.118 | +0.189 | -3.684 | 0.961 | -3.541 (-3.541) | beta |
| 09-21 07:00 1000SHIB/DOGE exit | -0.213 | +0.015 | -0.058 | -0.255 | 0.980 | -0.250 (-0.250) | beta |
| 09-26 17:00 1000SHIB/DOGE stop | +7.333 | +0.145 | -0.004 | +7.475 | 0.719 | +5.375 (+5.375) | sigma |
| 09-27 12:00 ETH/BTC exit | +0.019 | -0.160 | +0.077 | -0.064 | 1.236 | -0.079 (-0.079) | mean |
| 09-28 17:00 1000SHIB/DOGE stop | -1.903 | -0.465 | +0.009 | -2.360 | 1.528 | -3.605 (-3.605) | sigma |
| 09-30 19:54 1000SHIB/DOGE exit | +0.448 | -0.527 | +0.000 | -0.078 | 0.765 | -0.060 (-0.060) | mean |
| 10-03 07:01 1000SHIB/DOGE exit | +0.117 | -0.418 | +0.039 | -0.262 | 1.120 | -0.293 (-0.293) | mean |
| 08-09 23:00 FIL/AR exit | +0.133 | -0.195 | +0.007 | -0.055 | 1.056 | -0.058 (-0.058) | mean |
| 08-20 02:00 KAS/ETC stop | -3.283 | +0.136 | +0.302 | -2.846 | 1.670 | -4.752 (-4.752) | sigma |


**What moved z, by case:**

- **Mean:** the five exits that fired early in the live frame (09-14, ETH/BTC, 09-30, 10-03, FIL/AR). The same-beta mean came toward the spread, and z crossed 0 in the live frame before it did in the entry frame.
- **σ:** all three large stop disagreements.
  - 09-28 and KAS/ETC: σ shrank and the live frame stopped where the entry frame would not have.
  - 09-26: σ widened and the live frame stopped later.
- **β term:** two cases (09-15, 09-21), where it is small.

**The tally:**

| outcome in the entry frame | n | closes |
|---|---|---|
| same bar | 2 | 09-15 stop (central reading), 09-21 exit |
| **earlier** | 1 | 09-26 stop — 15:00 instead of 17:00 at the central β₁; 16:00, or an exit at 09:01, at the top of the rounding interval |
| **later**: an exit that fires later | 5 | 09-14 (+9 bars, by max-hold; conditional on 24 unobservable bars), ETH/BTC (+2), 09-30 (+7), 10-03 (+1), FIL/AR (+7 h) |
| **later**: a stop that becomes an exit | 2 | 09-28 (+19 bars), KAS/ETC (+9 bars) |

**In 8 of 10 refit-spanning holds the frame choice changed the closing bar.** In 2 of 10 it changed the kind of close: a stop became an exit. In a third (09-26) the stop came two bars earlier, and at the top of the rounding interval it too would have been an exit.

The σ₀ and USDT columns show the direction of each counterfactual. **They must not be summed:**

- Each one continues a position the agent actually closed, and ignores what the agent did instead. It re-entered after several of these closes: 09-14 13:00, 09-27 15:00, 10-03 08:00.
- The USDT figure is g·σ₀·Δz on the entry legs, with no fees.
- The sample contains only holds that spanned a refit.
- The frozen frame's own failure mode, riding a genuine break with no stop, does not occur in these 10. They cannot show how often it would. The one case where the trailing frame did better is 09-14: a +9-bar max-hold exit at −1.07σ₀.

This is task 03's frozen-versus-trailing axis, tallied as asked. I make no recommendation on it.

---

## 7. What the records cannot tell you

1. **m_b, the window mean of ln p_b, is never logged before 2026-09-29.**
   - Every pre-fix same-beta figure uses a bridge estimate of it. That estimate assumes a random walk for ln p_b, with hourly vol estimated from the record's own prints. Two of those vols are weak: **BTC** comes from only 5 increments, so I used the 95% upper bound; **AR**'s is assumed outright, because its 3 increments give an implausible 0.12%/h.
   - The bridge's two ground-truth misses were within 1 sd.
   - The windows are assumed to be contiguous hourly bars ending at the refit hour. A one-bar misalignment moves m_b by at most one hourly move.
2. **Three rounded betas: 09-15, 09-26, 09-28.**
   - **The rounding decides a sign for 09-15 and 09-26.** Their same-beta shifts span zero.
   - **The rounding decides an outcome for 09-26.** Depending on where β₁ sits inside ±0.0005, the entry frame stops at 15:00 or 16:00, or exits at 09:01.
   - For 09-28 the rounding moves the magnitude by ±0.16 but not the sign or the verdict.
   - No ledger record narrows any of the three: each stop is the only priced record in its epoch.
3. **The 09-13 12:00 epoch of the 09-14 hold has no priced record.** Its frame is unknown, so 24 bars of that hold's entry-frame path are unobservable.
4. **The transform at assessment bars** interpolates ln p_b between prints. That is approximate between decision prints before 09-29, and near-exact after, when five-minute samples exist. The ±2 sd ranges are shown wherever they matter. None changes a firing bar except the joint extreme on 09-15 at 13:00.
5. **The noise band is model-based**: a stationary AR(1) using the agent's fitted half-lives. The observed shifts sit low in it, so it is probably too wide. The conclusion about 0.10 holds under every φ tried. The count against the band ranges from 0 (fitted φ) to at most 1: 09-14, and only if the true half-life is ≤ ~6–7 h, against the fitted 18.7–33.8 h.
6. **Closes excluded, and why:**
   - **19 Phase II exits/stops with `mu_shift_sigma` exactly 0.0.** No refit fitted the pair inside any of those holds; I checked each.
   - **2 `refit_drop` closes** (09-21 10:01, 10-04 07:01). By design they carry no frame fields, and the close is the refit's universe decision, not a frame rule.
   - **7 instrumented Phase I closes at 0.0**, and **18 Phase I closes before 2026-08-06**, which have no frame fields at all.
   - **The 10-07 13:45 intra-bar stop**, which had no refit in the hold (`mu_shift_sigma` 0.0 on the entry beta).
7. **The §6 counterfactuals** say when the entry frame would have fired. They say nothing about the trades the agent made instead.
8. **The 0.527 and 0.418 are exact as logged**, but they are measurements of window-mean noise as much as of anything else. The live code's numbers are correct. What has no basis in this evidence is the threshold that reads them (0.10).

---

## Bottom line

**`mu_shift_sigma` as logged before 2026-09-29 is an artefact, almost entirely.**

- In every pre-fix case, 64–132% of the logged value is the beta-level term Δβ·m_b/σ₀. The rest is a same-beta shift. Where the beta is exact (five of the eight pre-fix cases across both phases), I recover it to ±0.04–0.13σ₀; ETH/BTC is the exception at ±0.44, with one BTC print in a 104-bar window. Where only a 3-dp beta exists, the bound is ±0.16–0.38σ₀.
- The two Phase I values were also mis-corrected on 2026-09-09. KAS/ETC's σ shrank to 0.60× rather than doubling, and its mean moved −0.14σ₀ toward the position, not +6.44σ₀ away. FIL/AR's entry-frame z was +0.133, so its "false alarm" was a true, small "target moved" exit.

**After the fix it measures something real, but the thing it measures is mostly noise.**

- The same-beta shift is the difference between two window means a refit apart. On spreads this autocorrelated, that difference wanders by 0.4–0.9σ₀ in a typical refit with no drift at all.
- None of the ten events, in either phase, clears the noise band implied by the agent's own fitted half-lives.
- The 0.10 flag fires on about 90% of driftless refits.
- The 5:1 "toward" lean is what conditioning on closed positions produces.

**So "frame drift", as an equilibrium that moves under open positions, has no evidence behind it in this record. What remains is the frame *disagreement* itself.** At a refit, β, μ and especially σ are re-estimated. In 8 of the 10 holds that spanned one, that changed the bar the position closed on: mostly later in the entry frame, once earlier. In two cases (09-28, and KAS/ETC on 08-20) the stop belonged to the live frame alone, because σ shrank at the refit. That is a ruler effect, task 05's territory, not a moving equilibrium. Whether to judge open positions in a frozen frame is still a human decision, and ten selected cases with no observed break are not enough to make it on.

---

## Statements in the record this contradicts

I modified none of these files.

| where | says | primary records give |
|---|---|---|
| `WEEKLY_REVIEW.md` week 8 table; `LTP_STRATEGY.md` 2026-09-27 addendum table | ETH/BTC same-beta ~+0.7; 09-21 ~−0.1; 09-15 ~−0.3; 09-26 ~−0.1 | +0.16 (−0.28…+0.60); ≈0; −0.12 (−0.50…+0.26), unsignable; −0.15 (−0.50…+0.21), unsignable |
| same places, and the Open commitments row "FIX `mu_shift_sigma`" | "every nonzero Phase II shift is ≥90% this artefact"; "the five pre-fix ones" | 88% (09-14), 64% (09-28 stop); six pre-fix closes |
| `WEEKLY_REVIEW.md` 2026-09-09 (later), "The KAS/ETC frame corruption"; `LTP_STRATEGY.md` 2026-09-09 addendum | σ_live/σ₀ = 2.047, "σ roughly doubled"; "μ moved away and tripled the raw deviation" | **σ₁/σ₀ = 0.599**; same-beta shift −0.14σ₀ (toward); deviation from the live mean shrank −3.28 → −2.85σ₀ |
| `LTP_STRATEGY.md` 2026-09-09 addendum, "a second retraction" | the FIL/AR drift note was "a false alarm attached to a +6.03 winner" | true entry-frame z +0.133: the exit would **not** have fired in its own frame; the note's claim was right, its number (−0.67) wrong |
| `out/03-frame-drift-cost.md` (task 03, my own answer) | §0 and §2b σ ratio 2.047; FIL/AR σ₀ 0.008432 and entry-frame z −0.665; §3 "zero exits change label"; §2a toward/away labels | 0.599; 0.014508 and +0.133; one exit changes label (FIL/AR); labels void (cross-beta) |
| `tests/test_ltp_entry_frame.py::_kas_pair` | fixture `sigma: KAS_SIG0 * 2.047` | 0.599 × σ₀. The fixture value is not asserted, so nothing fails. |
| `tests/test_ltp_entry_frame.py::test_the_2026_09_26_stop_shift_was_the_beta_change` | asserts \|same\| < 0.3 at the central 3-dp beta | true at the centre; the rounding range reaches −0.50 |
| this task's brief | Phase I close records carry no leg prices | all 27 Phase I `exit`/`stop` records carry `price_a`/`price_b` |

Two record statements are confirmed rather than contradicted. Week 8's "entry-frame z ~3.45–3.79 at 15:00, the stop fires 1–2 h earlier" for 09-26: I get 3.43–3.79. The 10-01 note "09-28: a refit one hour into the hold cut sigma by ~⅓": I get σ₁/σ₀ 0.61–0.70.

---

## Provenance

- **Measured** (arithmetic on logged values only):
  - every σ₀ and μ₀;
  - every cross-beta reproduction;
  - exact β₁ for 09-14, 09-21, ETH/BTC, 09-30, 10-03, FIL/AR and KAS/ETC;
  - the live frames fitted from priced records, and every σ₁/σ₀ where β₁ is exact;
  - the true Phase I entry-frame z;
  - the post-fix m_b and the method's measured errors;
  - the bar-by-bar live z series and the rule reproductions.
- **Estimated:**
  - every pre-fix same-beta shift, through the m_b bridge, with ranges stated;
  - σ₁/σ₀ where β₁ is 3-dp;
  - entry-frame z at assessment bars between prints;
  - the USDT column in §6;
  - the empirical autocorrelation cross-checks.
- **Assumed:**
  - a random walk for ln p_b inside windows;
  - AR's hourly vol;
  - contiguous hourly windows ending at the refit hour;
  - a stationary AR(1) null for the noise band.
- **Sources:**
  - `track_record/ltp_ledger_phase2.jsonl` (working tree = `origin/live/track-record` `e7dff87`);
  - `track_record/ltp_state_history.jsonl` (same);
  - `track_record/phase1_submission/reasoning.jsonl`;
  - `deploy/ltp_agent.py` at `2a006c2` (`refit`, `entry_frame`, `live_mu_on_entry_beta`, `window_mean_on_beta`, `trade_step`), and the pre-09-09 `entry_frame` at `da7aadb^`;
  - `deploy/research_queue/out/03-frame-drift-cost.md`, `deploy/WEEKLY_REVIEW.md` and `deploy/LTP_STRATEGY.md` at `2a006c2`, read for the claims under test only.
