# 05 — Does the shrinking sigma window explain the stops?

**No. On the evidence it is a coincidence, and three independent tests point the
same way.** The window does not predict stops (25% either side of a 50-bar cut,
Fisher p = 1.0000, identical medians). Stops arrive on raw moves **2.19× larger**
than non-stops, not smaller. And in the one pair that actually compressed, the
implied sigma **doubled** as the window shrank — the opposite of the mechanism.

A fourth point makes the first three almost redundant: over the observed range
the sigma window is an **exact linear function of the half-life**
(r = +0.9996), so "short window" and "fast pair" are not two variables. The
hypothesis is not merely unsupported here — it is **unidentifiable** from
observational records, and I say below exactly what would identify it.

Audit date 2026-09-23. Recomputed from the two ledgers and from
`deploy/ltp_agent.py:287–296`. No figure is taken from prose, **including this
task file's own** — two of its numbers do not survive the check (§0b). This is
evidence for a human decision, not a recommendation to act; the windows are
documented, intentional behaviour.

---

## 0. Coverage

`track_record/ltp_ledger_phase2.jsonl` **is present**, so this proceeds on both
phases as instructed.

| | records | span | refits | closes | stops |
|---|---|---|---|---|---|
| Phase I `phase1_submission/reasoning.jsonl` | 1,271 | 2026-07-19 20:07 → **2026-08-21 16:00** | 35 | 31 | **8** |
| Phase II `ltp_ledger_phase2.jsonl` | 593 | 2026-09-09 15:00 → **2026-09-23 10:01** | 15 | 13 | **3** |

The Phase II export's last record is **2026-09-23T10:01**, which is this
morning's refit — it lags the live agent by hours, not days. Combined test bed:
**44 closed positions with a sigma window in force, 11 of them stops.**

Phase I is the primary bed as instructed; Phase II is corroboration and is kept
separately labelled throughout. **They agree**, which is the least interesting
of the possible outcomes and the one that happened.

### 0b. Two figures in this task file do not reproduce

Stated because the brief says not to accept its own numbers on trust.

**1. NEAR/ICP's raw move was not small — it is the largest in the record.** The
brief reports the two clean stops as being on *"small raw moves, 1.4% and 3.4%
of log spread"*. Recomputing from the enter and stop prints on the entry beta
(1.48902408):

```
log-spread  -0.53519976  ->  -0.48088678      d = +0.05431298
                                              = 5.43% of log spread
dz = 3.7643 - 2.3714 = +1.3929
implied sigma = d/dz = 0.03899214      mu_shift_sigma = 0.0
```

**5.43%, not 1.4%.** The "1.4" appears to be the z displacement of 1.393 read as
a percentage. The 3.4% figure for 1000SHIB/DOGE is correct (0.033737). This
matters: the brief's headline framing — *both stops overshot on small raw moves*
— rests on it, and one of the two is in fact the **biggest raw move in either
phase**, on the **second-longest window** in Phase II.

**2. The `max(3 × half_life, 24)` floor has never bound.** The smallest fitted
half-life anywhere in either ledger is 12.48h, so `3 × hl = 37.4 > 24` always.
The floor is inert, and the window is simply `int(3 × half_life)` in practice.

(A third, immaterial: the brief's table dates 1000SHIB/DOGE's 18.7h/56-bar fit
to 09-15; that fit is the **09-14** refit. The 09-15 refit fitted 15.23h → 45
bars. The "56 → 37 in one week" arithmetic is right.)

---

## Summary of answers

| Question | Answer |
|---|---|
| 1. Window per refit | Phase I: oscillates, **no trend** (r = +0.100 over 36 fits). Phase II: falls, but that is **one pair**. |
| 2. Does it predict the stop? | **No.** <50 bars: 3/12 = 25%. ≥50: 8/32 = 25%. **Fisher p = 1.0000.** Median window identical at 55. |
| 3. Ruler vs move | **Backwards.** Stops come on raw moves **2.19× larger** than non-stops; the 4 largest raw moves in the record are all stops. |
| 4. Compression real? | Partly — and it came with **rising**, not falling, realised volatility. Not a quiet patch. |
| 4b. Which end of the band? | **The ledger cannot say.** Rejection half-lives are not recorded. Survivors sit at 12.5–33.8 against a [6, 168] band, near neither bound. |
| 5. Fast pair vs short window | **The same variable**, r = +0.9996. Not separable from these records at all. |
| 6. Enough data? | **No** — but the negative is robust because it does not depend on the rate. |

---

## Method

**The window.** `ltp_agent.py:291–293` fits `mu` over `int(3 × half_life)` bars
and `sigma` over `int(max(3 × half_life, 24))` bars, hourly (`interval = "1h"`).
I recompute the window from each `refit` record's per-pair `bands.half_life`,
and attribute to every closed position the window from the **latest refit
carrying that pair before the close**.

**Pair identity** is normalised — `KAS/ETC` and `ETC/KAS` are one underlying
pair traded in reversed orientation, and both appear.

**Raw displacement.** For each closed position, `d(log-spread) =
[log(pa₁) − β·log(pb₁)] − [log(pa₀) − β·log(pb₀)]` on the **entry record's own
beta**, so both ends are in one consistent frame. Where
`mu_shift_sigma = 0.0` the frame is provably stationary across the hold, and
then `d(log-spread) / dz` **is** sigma — which is what makes the ruler separable
from the move at all. 30 of the 44 closes qualify.

**One selection effect checked and cleared.** `refit()` keeps the
**fastest-reverting** `max_pairs` fits (`:299`), which would bias survivor
half-lives downward. `max_pairs = 4` and no refit in either phase passed more
than 3, so **the cap never bound** and this is not a confound here.

---

## 1. The sigma window, per refit

Survivors only — the ledger records no half-life for a rejected candidate (§4b).

**Phase I — 35 refits, 36 pair-fits. No compression.**

Half-lives run 15.63h to 29.31h, windows **46 to 87 bars**, oscillating.
First fit 18.59h, last 15.63h, median 19.30h, and the correlation between refit
order and fitted half-life is **r = +0.100** — no trend over a month. Selected
rows:

| refit | pass/test | survivor half-lives (h) | windows |
|---|---|---|---|
| 07-19 20:07 | 2/14 | ETC/KAS 18.43, TAO/RENDER 18.59 | 55, 55 |
| 07-26 22:07 | 3/15 | AVAX/SOL 25.41, FIL/AR 23.21, RENDER/TAO 17.03 | 76, 69, 51 |
| 08-01 01:00 | 2/15 | AVAX/SOL 17.48, FIL/AR 25.08 | 52, 75 |
| 08-10 20:00 | 1/15 | XLM/XRP 28.62 | **85** |
| 08-12 20:00 | 1/15 | XLM/XRP 29.31 | **87** |
| 08-19 19:01 | 1/15 | KAS/ETC 16.68 | 50 |
| 08-20 19:00 | 1/15 | ETC/KAS 15.63 | **46** |

**Phase II — 15 refits, 10 pair-fits, and the compression is one pair.**

| refit | pass/test | survivor | half-life | window |
|---|---|---|---|---|
| 09-09 → 09-11 | 0/15 ×3 | — | — | — |
| 09-12 12:00 | 1/15 | 1000SHIB/DOGE | 33.75 | **101** |
| 09-13 12:00 | 1/15 | 1000SHIB/DOGE | 23.57 | 70 |
| 09-14 12:00 | 1/15 | 1000SHIB/DOGE | 18.67 | 56 |
| 09-15 12:00 | 2/15 | 1000SHIB/DOGE / NEAR/ICP | 15.23 / 26.58 | 45 / **79** |
| 09-16 12:00 | 1/15 | 1000SHIB/DOGE | 15.35 | 46 |
| 09-17 10:00 | 1/15 | 1000SHIB/DOGE | 14.46 | 43 |
| 09-18 10:00 | 0/15 | — | — | — |
| 09-19 10:00 | 1/15 | 1000SHIB/DOGE | 12.48 | **37** |
| 09-20 10:00 | 1/15 | 1000SHIB/DOGE | 13.98 | 41 |
| 09-21 10:00 | 0/15 | — | — | — |
| 09-22 10:01 | 1/15 | 1000SHIB/DOGE | 14.39 | 43 |
| 09-23 10:00 | 0/15 | — | — | — |

**Nine of the ten Phase II fits are the same pair.** Its half-life fell 33.75 →
12.48 over seven refits, then **rebounded to 13.98 and 14.39**. So: a sharp
decline from first appearance to about 14h, then oscillation around that level —
not sustained compression.

**Answer to Q1: compression is neither common nor universe-wide in these
records. It is one pair, in one phase, over one week, and it stopped.**

---

## 2. Does the window predict the stop?

The denominator is the whole question, so here it is.

| window (bars) | n | stops | stop rate | 95% CI (Wilson) |
|---|---|---|---|---|
| < 45 | 8 | 1 | **12.5%** | [2%, 47%] |
| 45–54 | 13 | 4 | 30.8% | [13%, 58%] |
| 55–64 | 20 | 4 | 20.0% | [8%, 42%] |
| 65+ | 3 | 2 | **66.7%** | [21%, 94%] |

Split at 50 bars:

```
short window (< 50 bars):  3 stops / 12   = 25.0%
long  window (>= 50 bars): 8 stops / 32   = 25.0%
Fisher exact two-sided p = 1.0000
```

**Identical rates, and the p-value is exactly 1.** The medians agree too:
**55 bars at a stop, 55 bars at a non-stop.**

If anything the sign runs against the hypothesis. The windows at the eleven
stops were `[43, 45, 46, 50, 52, 55, 55, 56, 58, 79, 85]` — the **two longest
windows in the record both produced stops**. And the seven shortest-window
closes anywhere:

| window | pair | outcome | closed |
|---|---|---|---|
| **37** | 1000SHIB/DOGE | reverted | 09-19 17:00 |
| **37** | 1000SHIB/DOGE | reverted | 09-20 03:00 |
| 41 | 1000SHIB/DOGE | reverted | 09-21 07:00 |
| 41 | 1000SHIB/DOGE | refit_drop | 09-21 10:01 |
| 43 | 1000SHIB/DOGE | **stop** | 09-17 17:00 |
| 43 | 1000SHIB/DOGE | reverted | 09-22 12:00 |
| 43 | 1000SHIB/DOGE | reverted | 09-23 00:00 |

The shortest windows the agent has ever run — 37 bars, a 34% cut from the
56-bar fit a week earlier — produced **reverted exits**. Phase I and Phase II
agree: neither shows a window effect.

---

## 3. Separating the ruler from the move

The hypothesis makes a sharp prediction: at short windows, stops should show
**large z on small raw moves**. The records show the reverse.

**Raw displacement, stops versus non-stops:**

| | n | median \|d(log-spread)\| | max |
|---|---|---|---|
| stops | 11 | **0.019746** | 0.054313 |
| non-stops | 33 | **0.008998** | 0.030761 |

**Stops arrive on raw moves 2.19× larger than non-stops.** The spread really did
move. And the largest raw moves in either phase are almost all stops:

| \|d(log-spread)\| | pair | window | outcome | \|dz\| |
|---|---|---|---|---|
| **0.054313** | NEAR/ICP | **79** | stop | 1.393 |
| 0.041618 | ETC/KAS | 46 | stop | 2.909 |
| 0.033737 | 1000SHIB/DOGE | 43 | stop | 2.881 |
| 0.031400 | AVAX/SOL | 52 | stop | 8.859 |
| 0.030761 | KAS/ETC | 50 | reverted | 4.731 |

By window bucket, median raw move shows no pattern of small moves at short
windows: `<45` → 0.011170, `45–54` → 0.016756, `55–64` → 0.008415, `65+` →
0.014190.

### The within-pair test, which is the only valid one

Sigma is not comparable across pairs — NEAR/ICP's is 0.039, 1000SHIB/DOGE's is
0.004, a ninefold difference that says nothing about windows. So the mechanism
must be tested **within** a pair, on closes where the frame was provably
stationary. The hypothesis needs a **positive** correlation: smaller window →
smaller sigma.

| pair | n | r(window, implied sigma) | verdict |
|---|---|---|---|
| AVAX/SOL | 11 | **+0.828** | consistent |
| KAS/ETC | 6 | +0.560 | consistent |
| TAO/RENDER | 5 | −0.117 | nothing |
| **1000SHIB/DOGE** | 9 | **−0.392** | **contradicts** |
| ETC/KAS | 3 | −1.000 | contradicts (n=3) |

**Mixed — and the pair that actually compressed goes the wrong way.**
1000SHIB/DOGE in full:

| window | half-life | implied sigma | \|raw move\| | \|dz\| | outcome |
|---|---|---|---|---|---|
| 37 | 12.48 | 0.005816 | 0.006717 | 1.155 | reverted |
| 37 | 12.48 | 0.005816 | 0.008998 | 1.547 | reverted |
| 41 | 13.98 | 0.005936 | 0.005854 | 0.986 | refit_drop |
| **43** | **14.46** | **0.011710** | **0.033737** | **2.881** | **stop** |
| 43 | 14.39 | 0.008942 | 0.013341 | 1.492 | reverted |
| 43 | 14.39 | 0.008942 | 0.015317 | 1.713 | reverted |
| 43 | 14.39 | 0.008942 | 0.013975 | 1.563 | reverted |
| 56 | 18.67 | 0.004294 | 0.004117 | 0.959 | reverted |
| 56 | 18.67 | 0.004294 | 0.003228 | 0.752 | reverted |

Read the window column downward: as it fell from 56 to 43, **sigma roughly
doubled**, 0.004294 → 0.008942. The ruler did not shrink. It grew.

And the stop in that series is the row with the **largest raw move by a factor
of 2.2** over the pair's next-largest. It stopped because the spread moved,
measured against a sigma that was *larger* than the one in force a week before.

**The AVAX/SOL r = +0.828 needs its caveat**, and it is the same one as §5:
within a pair, "window" and "half-life" are the same number rescaled. A positive
correlation there says sigma and half-life move together on that spread — a
property of the price series, not evidence that the window is doing the work.

---

## 4. Is the compression real, or the estimator responding to quiet?

**It is real in the sense that the fit moved, and it is not a quiet patch.**

For 1000SHIB/DOGE, over the closes with a stationary frame, the half-life fell
23% (18.67 → 14.39) while the implied sigma went **0.004294 → 0.008942 — it
slightly more than doubled**. The raw moves rose with it, from 0.0041/0.0032 at
the 56-bar window to 0.0133/0.0153/0.0140 at the 43-bar window.

A window shrinking onto a quiet patch is the mechanism the hypothesis needs, and
it would show **falling** sigma. What the record shows is a spread that became
both **faster and noisier** at the same time — which is what an OU fit does when
mean reversion genuinely speeds up. On this pair the two effects partly cancel
in z: a shorter window, but a bigger sigma.

**And it does not persist.** The series is 33.75 → 23.57 → 18.67 → 15.23 →
15.35 → 14.46 → 12.48 → **13.98 → 14.39**. A decline from first appearance to
roughly 14h, then oscillation. The Phase I series across a whole month has no
trend at all (r = +0.100).

---

## 4b. Universe-wide, or only the pairs we hold? — and which end of the band?

**The ledger cannot answer this, and I am not going to infer it from
survivors.**

The `refit` record carries `passed`, `tested`, `active` and per-pair `bands` for
**pairs that passed**. A candidate rejected at `half-life out of band` leaves no
half-life anywhere in this repo — that breakdown exists only in the droplet's
systemd journal, which is not here and which rotates. Survivors are a sample
selected on the very quantity in question, so their distribution cannot stand in
for the universe's.

**What I can say, and its weight:**

- Survivor half-lives span **12.48h to 33.75h** against a band of **[6.0,
  168.0]**. They sit near **neither** bound — the closest approach to
  `min_half_life` is 12.48h, still 2× the floor, and nothing has come within a
  factor of 5 of `max_half_life`.
- Phase I survivor median **19.30h**, Phase II **15.29h**. Modestly faster, on
  10 Phase II fits of which 9 are one pair.
- **This is consistent with either reading and settles neither.** If the
  universe were compressing toward the 6h floor, survivors near the floor should
  be appearing; none are. If it were lengthening toward 168h, survivors should
  drift up; the one tracked pair went down. Both observations are dominated by
  the selection.

**An empty gate is not new, which weakens the "one story" framing:**

| | refits | 0-pass | share | dates |
|---|---|---|---|---|
| Phase I | 35 | 8 | 23% | 07-22, 08-05, 08-06, 08-11, **08-13 → 08-16** |
| Phase II | 15 | 6 | 40% | 09-09, 09-10, 09-11, 09-18, 09-21, 09-23 |

Phase I ran **four consecutive 0/15 refits, 08-13 to 08-16**, and no sigma-window
story was needed to explain it. The Phase II rate is higher on a fifth of the
sample; on 15 refits that difference is not distinguishable from noise.

**So the unifying story fails at its first step**: the compression it needs is
visible on exactly one held pair, it reversed, and the universe half-lives that
would test the other half are not recorded. **To settle it, log the per-gate
rejection counts and the fitted half-life of every candidate at every refit** —
the small instrumentation fix already in Open commitments. Until then the
direction question stays open, and the rally reading (longer half-lives failing
`max_half_life`) is no worse supported than the compression reading.

---

## 5. Short window versus fast pair — not a confound, an identification failure

The brief asks me to try to separate them. They cannot be separated, and the
reason is arithmetic rather than statistical.

```
window = int(max(3 * half_life, 24))
smallest half-life observed anywhere = 12.48h  ->  3 * hl = 37.4 > 24
```

The floor never binds, so over the entire observed range the window is a
deterministic **linear** function of the half-life. Measured across all 44
closes:

```
Pearson r(window, half-life) = +0.999604
```

**They are one variable.** Any correlation between window and outcome is
identically a correlation between half-life and outcome, and no amount of this
data can attribute it to the window rather than to the pair being fast. The
r = +0.828 on AVAX/SOL is exactly this: it is r(half-life, sigma), relabelled.

This is the deepest reason the hypothesis cannot be confirmed here — **not that
the evidence is against it, but that the design of the estimator makes the
question unanswerable observationally.** The answer has to be counterfactual:

> take the stored 960-bar price panel for each pair at each refit, recompute
> sigma with a **fixed** window (say 72 bars) alongside the live one, and compare
> the two z paths bar by bar. Every stop then has a counterfactual z, and the
> question "would this stop have fired under a fixed window?" becomes a
> measurement instead of an inference.

That panel is not in this repo. It is a few hundred kilobytes per refit and the
agent already fetches it — persisting it, or just logging both sigmas per bar,
would make this a one-afternoon question.

---

## 6. Does the sample support a conclusion?

**For the negative, largely yes — and that is the unusual part.**

The negative does not rest on the stop rate, which with 11 stops across four
buckets has CIs spanning [2%, 47%] and [21%, 94%] and could not detect a
moderate effect. It rests on three things that are not rate-limited:

1. **Direction.** Stops come on raw moves **2.19× larger** than non-stops. The
   hypothesis requires smaller. A sample this size can get a direction wrong,
   but the four largest raw moves in 44 closes being stops is not subtle.
2. **A within-pair mechanism check that fails on its own best case.** In the
   only pair that compressed, sigma doubled while the window fell 23%. The
   mechanism requires the opposite, on the very case that motivated the task.
3. **The identification failure in §5**, which is a property of the code, not of
   the sample. More data will not fix it.

**For any positive claim, no.** 11 stops, two regimes, and 9 of 10 Phase II fits
are one pair.

**What would settle it:** the fixed-window recomputation in §5 — it turns
44 observational closes into 44 paired counterfactuals and removes the
collinearity entirely. Failing that, sub-refit logging of `sigma` alongside the
half-life, so the two can at least be seen to move independently when the
`max()` floor does bind on a genuinely fast pair (half-life below 8h, which has
never occurred).

---

## 7. What the records cannot tell you

1. **Rejected candidates' half-lives** — nowhere in this repo, which is what
   makes 4b unanswerable rather than merely uncertain (§4b).
2. **The per-gate rejection mix** — journal only, rotating. The 09-20/09-21
   mixes quoted in the brief could not be verified here.
3. **Intra-refit sigma.** Sigma is recomputed only at a refit, so between refits
   the window is fixed; I could not observe sigma moving within a reign, only
   infer it from closes.
4. **Sigma at all, for 14 of 44 closes** — `d(log-spread)/dz` is only sigma when
   `mu_shift_sigma = 0.0`. Where the frame moved (five closes carry shifts of
   5.92, 6.44, 12.55, 13.24) the implied ratio mixes two frames and I excluded
   it from every sigma test rather than interpolating.
5. **Phase I carries no frame fields before 2026-08-09**, so 22 Phase I closes
   cannot be confirmed stationary. They are in the rate test (§2), which does
   not need sigma, and out of the mechanism test (§3), which does.
6. **The Phase I / Phase II boundary bit in three places**: the entry band
   differs (0.60 in late Phase I, 0.40 for NEAR/ICP in Phase II), leverage and
   capital reset, and the pairs do not overlap at all — so no pair can be
   tracked across the boundary and the two samples are joined only at the level
   of rates.
7. **`max_pairs` never bound** (passed ≤ 3 < 4), so the fastest-pairs selection
   is cleared as a confound *in this sample* — it would bite in any future
   period where more than four candidates pass.
8. **Nothing here was interpolated.** Where a value was unavailable the row is
   excluded and counted.

---

## Bottom line

**Coincidence.** The sigma window does not predict stops — 25.0% against 25.0%
either side of a 50-bar cut, Fisher p = 1.0000, medians identical at 55 bars,
with the two longest windows in the record both stopping and the two shortest
ever run (37 bars) both reverting. The mechanism's own signature is absent and
inverted: stops arrive on raw spread moves **2.19× larger** than non-stops, the
four biggest raw moves in 44 closes are all stops, and in the single pair that
actually compressed the implied sigma **doubled** (0.0043 → 0.0089) while the
window fell 23% — so the ruler grew rather than shrank, because the spread got
faster *and* noisier together, which is what a genuine speed-up looks like. The
two Phase II cases that made the hypothesis attractive do not survive
recomputation: NEAR/ICP's stop came on a **5.43%** raw move, the largest in
either phase, on the second-**longest** window — the brief's "1.4%" is its z
displacement of 1.393 misread as a percentage — and 1000SHIB/DOGE's 09-17 stop
came on that pair's largest raw move by a factor of 2.2. Underneath all of this
sits a harder problem: the window is `int(3 × half_life)` over the entire
observed range (the 24-bar floor has never bound), so window and half-life
correlate at **r = +0.9996** and are one variable — "short window" and "fast
pair" cannot be separated by any observational test on these records, which
means the hypothesis could not have been confirmed here even had the signs come
out its way. **The stop cluster goes back to being unexplained**, which is the
more honest place to stand; and question 4b's unifying story fails at its first
step, because the compression it needs is one pair over one week that then
reversed, while an empty gate is not new at all — Phase I ran four consecutive
0/15 refits in August without anyone reaching for this mechanism. Two cheap
instrumentation fixes would close both questions properly: **log every
candidate's fitted half-life and per-gate rejection reason at each refit** (which
side of the band, the thing 4b actually asks), and **recompute sigma on a fixed
window alongside the live one** so every stop carries a counterfactual z. Neither
is a strategy change, and together they convert this from an argument into a
measurement.

---

## Provenance

- `track_record/phase1_submission/reasoning.jsonl` — 35 refits (36 survivor
  fits), 31 closes, 8 stops; span 2026-07-19 20:07 → 2026-08-21 16:00.
- `track_record/ltp_ledger_phase2.jsonl` — 15 refits (10 survivor fits), 13
  closes, 3 stops; span 2026-09-09 15:00 → **2026-09-23 10:01** (hours behind
  live, not days).
- Window formula and selection read from `deploy/ltp_agent.py:287–296`
  (`mu`/`sigma` windows), `:299` (`keep` sorts ascending by half-life),
  `:91` (`interval = "1h"`), `:95–96` (`min/max_half_life`), `:115`
  (`stop_z = 3.5`), `:128` (`max_pairs = 4`).
- Context read first per `CLAUDE.md`: `deploy/WEEKLY_REVIEW.md` standing
  context, the 2026-09-22 entries on the 0/15 refit and the rally, and Open
  commitments. Used for framing and for the journal-only caveat in §4b; **no
  figure in this file comes from it.**
- **Measured** — every window, half-life, stop rate, Wilson interval, Fisher
  p-value, correlation, raw displacement, implied sigma, and both pass-count
  tallies.
- **Excluded, with reason** — closes where `mu_shift_sigma ≠ 0` (frame moved, so
  `d(spread)/dz` is not sigma) from the §3 mechanism tests only; Phase I closes
  before 2026-08-09 from the same tests, for lack of frame fields.
- **Assumed** — nothing. Statistics computed directly (Wilson score interval,
  hypergeometric two-sided Fisher exact); no external libraries used.

*Created: this file only. No other file was modified.*
