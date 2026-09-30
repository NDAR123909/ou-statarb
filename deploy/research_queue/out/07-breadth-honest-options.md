# 07 — Is there honest breadth, in time to matter?

## The answer first: no.

**No honest breadth is available in time to matter.** Of the three pre-declared
sets, **B adds nothing** (0 of 22 non-crypto pairs pass) and **C adds at most two
new crypto pairs, of which one shares a leg with the pair we already trade** —
so at most **one** additional relationship that could plausibly be independent.
And even that one cannot move the score: Phase II's per-trade edge is
**t = +0.46**, a diversification multiplier of at most √2 applied to an edge
indistinguishable from zero is still indistinguishable from zero, and four weeks
cannot produce anywhere near the ~411 trades it would take to tell.

A top-3 finish therefore does not depend on our universe. It depends on loss
control — the four stop days are −3.32% against a +0.21% total — and on the
field. That is the thing to know early, and it is what the operator asked for.

Three things about the scan itself also need saying before its numbers are
used, because each changes how it reads (§0b): **its VERDICT double-counts**,
**its headline tests the wrong orientation**, and **it runs on a panel roughly
half the length of the live one.**

Audit date 2026-09-30. No figure is taken from prose, including this task
file's. This is evidence for a human decision. It recommends no loosening, no
FDR stratification, and no selection of pairs by their results.

---

## 0. Coverage — both required files are present

| file | state |
|---|---|
| `track_record/universe_scan_task07.txt` | present, 166 lines, **ends on a `VERDICT:` line** |
| `track_record/ltp_ledger_phase2.jsonl` | present, 1,287 records, 2026-09-09 15:00 → **2026-09-30 19:10** |
| `track_record/phase1_submission/reasoning.jsonl` | 35 refits |
| `track_record/ltp_state_history.jsonl` | 22 Phase II rows, 2026-09-08 → 2026-09-29 |

**When the scan ran, and whether anything failed.** The output carries no
timestamp — `universe_scan.py` prints none by design, so its absence is not a
truncation. It was committed as `eb6ed0c` on `live/track-record` at
**2026-09-30 19:21:59 UTC**, so it ran shortly before that, eleven hours after
the 08:01 refit and clear of it as the dispatch note asked. Its first line is
the first thing the source prints once a manifest is found. Nothing failed:

- `available: 112/112`, `dropped (no data): []`;
- no `EXCLUDED for missing data` line, so all 15 live candidates were scored;
- no `no manifest found` note, so the probe manifests were present on the
  droplet;
- it closes on `VERDICT:`, not an error.

**`candidates` coverage.** Only **1 of 22** Phase II refits carries the new
`candidates` field — **2026-09-30 08:01**, the first after it shipped. That one
record is what makes Set A's FDR arithmetic exact (§1); every earlier refit
carries survivors only.

---

## 0b. Three things the scan gets wrong or does not say

**1. The VERDICT double-counts.** It reads *"6 genuine pairs pass the unchanged
gates vs 1"*. `_report()` (`universe_scan.py:199`) counts **passing rows**, and
the scan forms every sector pair **once per venue** (`:394–398`). So DOGE/WIF
passes twice — once on Binance, once on OKX — and so does AAVE/COMP. The stratified
diagnostic confirms it (`memes@OKX 1/1 DOGE/WIF`, `defi_lending@OKX 1/1
AAVE/COMP`). **Six rows are four distinct underlying pairs.** Trading the same
pair on two venues is one bet sized twice, not breadth.

**2. The headline tests the wrong orientation.** The live agent orients every
pair by the **vol-rule** — the more volatile series is the dependent variable
(`ltp_agent.py:292`). The scan's CURRENT section tests `CANDIDATES` in its
literal tuple order, and its EXPANDED headline tests pairs alphabetically. Of the
15 live pairs, **12 are flipped** by the vol-rule relative to their `CANDIDATES`
tuples — the traded pair is tested live as **1000SHIB/DOGE** (β 0.854) but in the
scan's CURRENT section as DOGE/1000SHIB (β 1.10), a different regression. The
scan does run the vol-rule policy, in its orientation-sensitivity section, and
**that** is the row that answers "what would the live agent admit": **5 rows, 3
distinct pairs** — not 6 and 4. 1000SHIB/WIF passes only in the alphabetical
orientation the agent does not use.

**3. The scan's panel is not the live panel — and neither would be the
agent's, under B or C.** `fetch_panel` ends in `pd.DataFrame(frames).dropna()`
(`ltp_agent.py:239`): an **inner join on timestamps across every symbol
fetched**. The live refit fetches 30 crypto symbols; the scan fetches 112,
including equity, index and commodity perps and OKX listings. The one pair
printed from both panels on the same day:

| 1000SHIB/DOGE, vol-rule | live refit 08:01 | scan ~19:00 |
|---|---|---|
| mean crossings (a raw count over the panel) | **80** | **38** |
| ADF p-value | **7.7 × 10⁻⁵** | **0.0158** |
| half-life | 14.87h | 13h |
| beta | 0.854 | 0.87 |

Same pair, same orientation, near-identical fit — **half the crossings and a
p-value 200× weaker.** Eleven hours of window drift cannot do that; a panel
roughly **half as long** (~460–500 of 960 bars) can. That is also where
`fetch_panel`'s inclusion floor sits (≥ 480 bars), so the likeliest mechanism is
that the youngest or gappiest of the 112 symbols sets the length for everyone.
**Inferred, not measured** — the scan does not print its panel length (§7).

This is not a quirk of the scan. **It is what the live agent would do under B or
C**, because `refit()` fetches every `CANDIDATES` symbol through the same
function. Widening the list to include market-hours or newly-listed instruments
would truncate the panel for **every pair in the book**, including the one that
currently passes. That is a cost of breadth on top of the FDR price, and it is
recorded nowhere in the project.

---

## Summary

| set | m | distinct passers | new vs A | lost vs A | independent new pairs |
|---|---|---|---|---|---|
| **A** status quo | 15 | 1 — 1000SHIB/DOGE | — | — | — |
| **B** + non-crypto drivers | 37 | 1 *or* 0 (§2) | **0** | 0, *or* the traded pair | **0** |
| **C** full scan (live orientation) | 166 | 3 | 2 — DOGE/WIF, AAVE/COMP | 0 | **≤ 1** — AAVE/COMP |
| C, scan's alphabetical headline | 166 | 4 | 3 (+ 1000SHIB/WIF) | 0 | ≤ 1 |

---

## Method

**FDR is reproduced, not trusted.** `select_pairs` applies step-up
Benjamini-Hochberg at q = 0.10 over **every** test, including those rejected by
another gate, then keeps a pair only if it passes both (`selection.py:44–57`,
and the tail of `select_pairs`). I reimplemented it and checked it against the
09-30 08:01 refit's own labels: it reproduces them exactly — 1000SHIB/DOGE
passes; ETH/BTC clears every non-FDR gate and fails BH, which is precisely what
the ledger's `reason` field says.

**Where a set's p-values come from.**

- **A** — the 09-30 08:01 refit's `candidates`: all 15, live orientation, live
  panel. Exact.
- **B** — A's 15 plus the 22 within-venue non-crypto rows the scan prints. Two
  panel scenarios, because §0b-3 makes the panel itself uncertain.
- **C** — the scan's own printed results at m = 166. The scan prints p-values for
  35 of its 166 tests (6 passing rows + 29 non-crypto); for the rest I compute
  what BH **requires** of them rather than guessing them.

**Distinct pairs** count an underlying pair once regardless of venue or
orientation.

---

## 1. What passes under each set, pooled FDR

### Set A — status quo, m = 15 (live panel, live orientation, 09-30 08:01)

| pair | adf_p | half-life | beta | crossings | hurst | cost_z | result |
|---|---|---|---|---|---|---|---|
| **1000SHIB/DOGE** | 7.67 × 10⁻⁵ | 14.87h | 0.854 | 80 | 0.354 | 0.056 † | **pass** |
| ETH/BTC | 0.0521 | 42.28h | 1.089 | 59 | 0.358 | — | every gate but FDR |

† `cost_z` is not in the refit record; 0.056 is the scan's figure for this pair
on its own panel.

The BH ladder, ranks 1–6 of 15: thresholds 0.0067, 0.0133, 0.0200, 0.0267,
0.0333, 0.0400. 1000SHIB/DOGE (rank 1) and AVAX/SOL (rank 2, p 0.0051) clear;
AVAX/SOL then fails Hurst. **ETH/BTC is rank 6 at p 0.0521 against 0.0400** —
the one pair on the list genuinely held back by m, which makes it the pair most
sensitive to any widening. Rejects that day: split-half 5, too few mean crossings
5, Hurst 3, FDR 1. Every candidate's half-life was **inside** the 6–168h band
(`band_side: "in"` for all 15).

### Set B — A + non-crypto drivers, m = 37

B adds every within-venue pair the scan forms in `energy`, `megacap_equity` and
`index_vs_member`. All nine non-crypto bases are live on both venues (the only
non-crypto absence is ZS, which forms no pair), and `megacap_equity`'s six pairs
are subsumed by `index_vs_member`'s ten, so each venue contributes 1 + 6 + 4 =
**11** pairs — **22** across both, which matches the scan's 22 non-cross-venue
non-crypto rows exactly.

**All 22 fail a non-FDR gate**, with p from 0.2743 to 0.7725:

| rejected by | pairs (each on both venues) |
|---|---|
| beta out of range | AAPL/SPX, MSFT/SPX, AAPL/NVDA, MSFT/TSLA, NVDA/TSLA, NVDA/SPX |
| too few mean crossings | AAPL/MSFT, MSFT/NVDA, AAPL/TSLA |
| hurst too high | SPX/TSLA |
| fails split-half cointegration | **BZ/CL** |

**No non-crypto pair failed on the half-life band at either end.** BZ/CL — the
WTI–Brent pair the scan calls its strongest economic prior — has a half-life of
31–32h, comfortably inside the band, and fails split-half cointegration. The
brief's concern that `max_half_life` rejects slow commodity spreads for being
slow does not arise in this snapshot; the only band failures anywhere in the
non-crypto set are the **same-asset** cross-venue pairs, which fail for being too
**fast** (0.7–3.8h).

**So B's passers are A's passers or fewer.** Which, depends on the panel:

- **(i) If adding these symbols does not truncate the panel**, A's live p-values
  apply. At m = 37, 1000SHIB/DOGE sits at rank 1 against a threshold of 0.0027
  and clears it by 35× — it would survive as rank 1 up to **m ≈ 1,303**. **Kept.**
- **(ii) If it does truncate, as §0b-3 indicates**, 1000SHIB/DOGE carries the
  scan-panel p of 0.0158. At m = 37 it then needs rank ≥ 6 — at least **six** of
  the fifteen A-set p-values at or below 0.0162. On the *live* panel, which has
  more history and therefore more power, only **two** are. The scan does not
  print the other fourteen on its own panel. **Probably ejected; not
  determinable from the output.**

### Set C — the scan's full expanded universe, m = 166

**In the live (vol-rule) orientation — 5 rows, 3 distinct pairs:**

| pair | venue | adf_p | hurst | half-life | beta | crossings | cost_z |
|---|---|---|---|---|---|---|---|
| WIF/DOGE | Binance | 0.0003 | 0.18 | 8h | +1.64 | 54 | n/p ‡ |
| WIF/DOGE | OKX | 0.0003 | 0.18 | 8h | +1.64 | 54 | n/p ‡ |
| AAVE/COMP | one venue each | 0.0020 | 0.33 | 14h | +0.98 | 52 | 0.027 |
| AAVE/COMP | one venue each | 0.0021 | 0.33 | 14h | +0.98 | 50 | 0.027 |
| **1000SHIB/DOGE** | Binance | 0.0158 | 0.34 | 13h | +0.87 | 38 | 0.056 |

**In the scan's alphabetical headline — 6 rows, 4 distinct:** the same, with
DOGE/WIF (β +0.58, 60 crossings, `cost_z` 0.043) in place of WIF/DOGE, plus
**1000SHIB/WIF** (p 0.0059, hurst 0.35, 16h, β +0.50, 50 crossings, `cost_z`
0.033), which the live orientation does not admit.

‡ `cost_z` is printed only for the alphabetical rows. Every printed `cost_z` for
a passer is between 0.027 and 0.056, far below the ~1 at which fees consume the
edge, so **cost does not bind for any C passer.** The scan prints no venue label
on duplicate rows; which row is which venue is not recoverable from the text.

**Two of the four distinct pairs sit near a band edge worth naming.** WIF/DOGE's
7–8h half-life is 1–2 bars above `min_half_life = 6.0`, so a modest speed-up
fails it outright.

---

## 2. The FDR price: gains and losses against A

| | gains vs A | loses vs A |
|---|---|---|
| **B** | **0** | **0** in scenario (i); **the traded pair, probably**, in scenario (ii) |
| **C** (live orientation) | **2** — WIF/DOGE, AAVE/COMP | **0** |
| C (alphabetical) | 3 — adds 1000SHIB/WIF | 0 |

**B is breadth in name only.** It raises m from 15 to 37, admits nothing, and can
only make the correction stricter for the pair we trade. Under the panel
truncation §0b-3 points to, it likely ejects it.

**C keeps the traded pair — but look at how.** On the scan's panel
1000SHIB/DOGE has p = 0.0158, so passing BH at m = 166 requires rank ≥ 27: at
least **27 tests at or below 0.0163**. The scan prints only **11** such (live
orientation; 12 alphabetical), and **6** of those 11 are same-asset cross-venue
pairs. So its survival in C **depends on at least 15–16 tests the scan never
prints.**

| C passer | needs rank ≥ | printed tests at/below threshold | …excl. same-asset | unprinted tests required |
|---|---|---|---|---|
| WIF/DOGE | 1 | 6 | 2 | **0** |
| AAVE/COMP | 4 | 8 | 4 | **0** |
| 1000SHIB/WIF (alpha only) | 10 | 9 | 5 | **1** |
| **1000SHIB/DOGE** | **27** | **11** | **5** | **16** |

The obvious source of those unprinted low p-values is the **44 same-asset crypto
pairs** — one coin priced on two venues, which the scan's own comment calls "the
purest cointegration here" (`universe_scan.py:403`). But the scan prints none of
them, and some of the 87 unprinted within-venue crypto rejects could contribute
too, so I cannot say how the 16 divide.

What I can say: **C's family includes 51 same-asset tests, every one of them
untradeable** (`cost_z` 1.15–5.16 wherever printed, and two-venue execution
unmodelled), and near-certain discoveries of that kind raise the BH cut-off for
every other test in the family. This is compliant with invariant 3 — they are
tests that were run — but it means **the correction's apparent strictness at
m = 166 is relaxed by hypotheses the agent could never trade**, and the traded
pair's survival in C rests on that relaxation. WIF/DOGE and AAVE/COMP do not: both
pass on printed values alone, even with every same-asset test removed from the
count.

---

## 3. Is one snapshot evidence?

**Not for adding a pair.** Persistence across refits, from the ledgers:

| pair | Phase I (35 refits) | Phase II (22 refits) |
|---|---|---|
| **1000SHIB/DOGE** | 0 | **15 (68%)** |
| ETH/BTC | 0 | **3 (14%)** — 09-26, 27, 28; gone 09-29 |
| NEAR/ICP | 0 | 1 (5%) |
| AVAX/SOL | 11 (31%) | 0 |
| **refits passing nothing** | 8 (23%) | **7 (32%)** |

The best-behaved pair in Phase II passed on two refits in three. ETH/BTC — which
the brief names as "currently traded" — passed three days running and left. The
scan's docstring says ETH/BTC passed "six of the eight refits" before 09-09; those
refits predate this ledger and I could not check it.

**For every expansion candidate there is exactly one observation, and it is on a
panel the live agent does not use.** WIF and COMP appear nowhere in the project's
record — not in `WEEKLY_REVIEW.md`, not in `LTP_STRATEGY.md`, not in any ledger.

**What a decision would need.** A persistence rate distinguishable from ETH/BTC's
14% needs roughly 10 daily readings at minimum; with 0.68 against 0.14 a
difference shows at around 8–10 refits per pair. Daily scans from 10-01 would
supply ten by ~10-11, leaving **about three weeks** — and each scan must be run on
the **B/C panel** the agent would then use, since §0b-3 shows the statistics
change with the fetch set.

---

## 4. Would it actually be breadth?

**This cannot be measured here** — the repo holds no price panel for WIF, COMP or
any non-crypto symbol, so no correlation between spread returns can be computed.
What the economic grouping implies:

- **WIF/DOGE shares DOGE with 1000SHIB/DOGE.** In the live orientation both have
  DOGE as the regressor with positive beta (1.64 and 0.87), so a DOGE move pushes
  both spreads the same way. **Holding both is concentration in DOGE, not
  diversification.** The same holds for 1000SHIB/WIF.
- **Three of the four distinct C passers are memecoins**, and the fourth is DeFi.
  All four are crypto. The scan's own comment names what that means: *"A breadth
  result driven entirely by crypto is the 09-09 finding again, and should not be
  read as a new one."* **Zero of 29 non-crypto pairs passed** — the non-crypto
  hope that motivated building the scan produced nothing in this snapshot.
- **The rejection mix points to trending.** The only refit carrying `rejects`
  (09-30) shows too few mean crossings 5, split-half 5, Hurst 3; the record
  reports crossings leading 5–6 of 15 daily since 09-27 from the journal, which
  I could not verify beyond that one refit. Hedged crypto spreads can still fail
  together when the sector trends.

**So the honest breadth count under C is one**: AAVE/COMP, from a different
sector, correlation unmeasured.

---

## 5. Operational blockers, per passer

| passer | set | blockers |
|---|---|---|
| **1000SHIB/DOGE** (Binance) | A, B, C | none new under A. **Under B or C: panel truncation** (`ltp_agent.py:239`) cuts its evidence from p 7.7 × 10⁻⁵ to 0.0158 |
| **WIF/DOGE** (Binance) | C | shares DOGE with the traded pair (§4); half-life 7–8h against a 6h floor; WIF never traded or reviewed (no mention anywhere in the record) |
| WIF/DOGE (OKX) | C | a duplicate of the above; **OKX orderability unverified** — trigger-only commitment, run `order place-preview` the day an OKX pair is proposed (`WEEKLY_REVIEW.md:1811`); **OKX is actively delisting perps** — 72 contracts cut 09-28 (`WEEKLY_REVIEW.md:5965`, `:1812`); `grep` finds no OKX symbol in `ltp_agent.py`, so the agent has never traded there |
| **AAVE/COMP** (Binance) | C | COMP never traded or reviewed; none structural |
| AAVE/COMP (OKX) | C | a duplicate; the OKX blockers above |
| 1000SHIB/WIF (Binance) | C, alphabetical only | **not admitted in the live orientation**; shares 1000SHIB with the traded pair |

**Blockers that apply to the sets rather than to a passer:**

- **Panel truncation (B and C).** Any `CANDIDATES` list that includes market-hours
  or newly-listed instruments shortens the live panel for every pair
  (`ltp_agent.py:239`). New finding; not in any Open commitment.
- **Two-venue execution is unmodelled** (`WEEKLY_REVIEW.md:1809`). Applies to C's
  51 same-asset tests. None pass, so it binds nothing today.
- **The SPX hedge ratio is unexplained** (`WEEKLY_REVIEW.md:1807`). In this
  snapshot all four SPX pairs on each venue fail, three on `beta out of range`
  with β between −0.15 and +0.06 — the same anomaly, still open.
- **Weekend gaps** in equity and commodity underlyings while the perps trade 24/7.
  The scan argues a within-driver spread is largely insulated because both legs
  gap together (`universe_scan.py:94–100`). Untested, and moot while no
  non-crypto pair passes.
- **`max_half_life` and slow commodities** (`universe_scan.py:476–481`) — does not
  bind in this snapshot (§1, Set B).

---

## 6. Timeline

A change decided 2026-10-04 deploys ~10-06, leaving **29 days** to the 11-04
close. Calibrated on Phase II's own cadence — **22 closed round trips over ~19
in-universe pair-days = 1.16 per pair per day** (median hold 9.5h against a
`max_hold_mult` of 3 × half-life, which for these half-lives caps a hold at
21–48h) — and bracketed by the two persistence rates actually observed:

| set | new pairs | round trips in 29 days (at 68% / 14% persistence) |
|---|---|---|
| **A** | 0 | ~23 / — |
| **B** | 0 | ~23 — or ~0 if the traded pair is ejected |
| **C** | 2 | ~23 + **46 / 9** = **~69 / ~32** |

**What it would take to register.** Phase II's measured per-trade P&L is mean
**+0.519, sd 5.26, t = +0.46**. To detect an edge that size at two standard errors
takes **(2 × 5.26 / 0.519)² ≈ 411 trades.** Phase II's 22 plus the most optimistic
C total of 69 comes to 91 — **about a fifth of what is needed.**

**And breadth multiplies edge; it does not create it.** k independent pairs scale
a book's Sharpe by roughly √k. C offers one independent addition at best, so √2 ≈
1.41 on a measured daily Sharpe of **+0.019** — **+0.51 annualised**, against a top
three running 3.0–4.6. To reach 3.0 with two independent pairs, each would need a
daily Sharpe of about **0.11 — six times** what the book has produced.

**The score's Sharpe is also mostly noise at this horizon.** On Phase II's 21 daily
returns the book's annualised Sharpe is **+0.37 ± 4.17** (1 SE; ×√365). At the
close it will rest on ~57 days, where one SE is still **~2.5**. The top three's
3.0–4.6 sit about 1–2 SE from zero. Worth weighing on Sunday alongside the gap to
third: part of it is signal, and part is not.

(The leaderboard reports our Sharpe as −0.10; my figure from
`ltp_state_history.jsonl` is +0.37. The organizer's sampling and annualisation
are not documented, and I have not reconciled the two.)

---

## 7. What the records cannot tell you

1. **The scan's panel length.** Not printed. The ~half-length inference rests on
   one pair seen on both panels (§0b-3).
2. **p-values for 131 of C's 166 tests** — including all 44 same-asset crypto
   pairs whose padding the traded pair's survival in C depends on (§2).
3. **A's 14 non-passing p-values on the scan's panel**, which decide scenario (ii)
   for Set B.
4. **Venue labels** on duplicate passer rows.
5. **`cost_z` in the live orientation** for WIF/DOGE; printed only alphabetically.
6. **Any correlation between spread returns** for expansion candidates (§4).
7. **Persistence for any expansion candidate** — one observation each (§3).
8. **Orderability** of anything on OKX, and whether WIF and COMP perps have the
   depth to fill the agent's size without slippage beyond the cost model.
9. **The rejection mix since 09-27**, except on the one refit that records it.
10. **ETH/BTC's pre-Phase-II pass history**, which predates the ledger.

---

## For a future pre-registration — a recommendation, not a result

Three choices would have made this set definition sharper. None loosens a gate;
each makes the correction **stricter**, not looser.

- **Declare the orientation.** The sets should be evaluated in the **vol-rule**
  orientation the live agent uses. The scan's alphabetical headline admits a pair
  (1000SHIB/WIF) the agent would not.
- **Do not form tests the agent cannot trade.** Same-asset cross-venue pairs are
  untradeable here and near-certain discoveries; forming them pads the BH
  cut-off for everything else. Invariant 3 covers tests that are *run*, so not
  forming them (`--no-cross-venue`) is compliant — and would make the correction
  bite harder on the marginal pair, very possibly including the one we trade.
- **Count distinct underlying pairs**, and pre-declare which venue's instance
  would be traded.

---

## Bottom line

**No — honest breadth is not available under the invariant in time to matter,
and the part of the question that is not knowable does not change that.** Set B
admits nothing: all 22 non-crypto pairs fail a non-FDR gate — BZ/CL on split-half
cointegration, not on the half-life band — and B can only tighten the correction
on the pair we trade, which it likely ejects once the wider fetch truncates the
live panel. Set C, in the orientation the agent actually uses, admits **two** new
pairs, not the five the scan's VERDICT implies once its venue duplicates and
alphabetical orientation are stripped out — and one of the two, WIF/DOGE, shares
DOGE with 1000SHIB/DOGE, so the honest independent gain is **one** pair,
AAVE/COMP, seen exactly once, on a panel half the live one's length. C keeps the
traded pair only because at least sixteen unprinted tests — most plausibly the
same-asset cross-venue pairs nobody could trade — relax the BH cut-off. Even if
AAVE/COMP were real and persistent, √2 times an edge of t = +0.46 is still no
measurable edge, four weeks yields perhaps 70 trades against the ~411 needed to
see one, and the score's Sharpe carries a standard error of ~2.5 at the close
regardless. **So top 3 rests on loss control and on the field, not on the
universe.** On Sunday the operator should look at: (1) the four stop days,
−3.32% of a +0.21% total, which remain the only lever with a measured payoff;
(2) whether to authorise **daily B/C scans on the live fetch set from 10-01** —
the only way to learn, by ~10-11, whether AAVE/COMP persists, with three weeks
left if it does; and (3) the panel-truncation finding, which should be settled
before **any** `CANDIDATES` change, because widening the list silently weakens
the evidence for every pair already on it.

---

## Provenance

- `track_record/universe_scan_task07.txt` — `eb6ed0c`, 2026-09-30 19:21:59 UTC;
  source read in full: `deploy/universe_scan.py` (grouping `:77–145`, pair
  formation `:394–413`, `_report` counting rows `:199`, orientation policies
  `:300–340`, verdict `:483–495`).
- `track_record/ltp_ledger_phase2.jsonl` — 22 refits, one carrying `candidates`
  and `rejects` (09-30 08:01); 22 closed round trips.
- `track_record/phase1_submission/reasoning.jsonl` — 35 refits, 31 closed trips.
- `track_record/ltp_state_history.jsonl` — 22 Phase II daily equity rows.
- Code read: `ltp_agent.py:70` (`CANDIDATES`), `:95–96` (half-life band), `:116`
  (`max_hold_mult`), `:239` (`dropna`), `:292` (vol-rule orientation);
  `statarb/selection.py:44–57` (BH) and `select_pairs`.
- Record read first, per `CLAUDE.md`: `WEEKLY_REVIEW.md` 2026-09-29 entries, the
  2026-09-24 OKX entry, Open commitments `:1807–1812`. Used for context and
  citations only; **no figure here comes from them.**
- **Measured** — every BH ladder and threshold, set sizes, persistence counts,
  per-trade mean/sd/t, round-trip cadence, daily returns and Sharpe SE.
- **Inferred, labelled** — the scan panel's ~half length (§0b-3); the unprinted
  tests required by BH in C (§2), which are logical requirements, not estimates.
- **Assumed, labelled** — trade cadence and persistence for untraded pairs (§6),
  bracketed by the two rates observed.

*Created: this file only. No other file was modified.*
