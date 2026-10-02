# Top-3 strategy review — prep for Sun 2026-10-04

Prepared 2026-10-01 from `live/track-record` at `68ad618` (ledger export to
2026-10-01 14:00). Every figure below is produced by the scripts in this
directory — see `README.md` to reproduce. Estimates are labelled as estimates.

## Bottom line

**Top 3 is unlikely, and no lever available to us changes that by itself.**
Finishing at Sharpe ~3 — the top three run 3.0–4.6 — needs about **+1.23
USDT/day** for the remaining 35 days at today's volatility; Phase II has made
**+0.21/day**. That is ~6× the realised edge, sustained for five weeks.

**One lever is real: stopping exactly at 3.5 instead of at the next hourly
bar.** It is the only one that moves the 40% Sharpe term — an upper bound of
**+0.75 → +2.41** (close-to-close) — because it shrinks the tail days that
decide our Sharpe. Everything else either does nothing for Sharpe (sizing),
fails out of sample (a tighter stop), is unavailable in time (breadth, task 07),
or cannot be measured (macro gating).

**Realistic target with good loss control: top 5–7.** Top 3 additionally needs
a better edge than the record shows, or the field to stumble.

---

## (a) What the stops cost

**All 23 Phase II round trips** (fills reports, merged so no trip loses its
P&L):

| exit | trips | net |
|---|---|---|
| reverted (profit-take) | 16 | **+44.17** |
| stop | 6 | **−41.67** |
| refit drop | 1 | +2.22 |
| total | 23 | **+4.72** |

**The six stops gave back 94% of what the sixteen winners made.** Per stop —
loss at the actual stop versus the loss had it closed exactly at live z = 3.5,
with frame changes rebuilt from each close record (`stops.py`; live beta from
3-dp state rows, so a range where a refit fell inside the hold):

| stop | side | entry z | last hourly z | stop z (live) | entry-frame z | gross | loss at 3.5 | **overshoot** |
|---|---|---|---|---|---|---|---|---|
| 09-15 1000SHIB/DOGE | long | −0.96 | −2.42 | −3.54 | −3.99 | −5.39 | −5.31 | **0.08** |
| 09-16 NEAR/ICP | short | +2.37 | +3.34 | +3.76 | +3.76 | −8.59 | −6.96 | **1.63** |
| 09-17 1000SHIB/DOGE | short | +1.24 | +2.82 | +4.13 | +4.13 | −13.32 | −10.43 | **2.89** |
| 09-26 1000SHIB/DOGE | short | +0.61 | +2.90 | +5.38 | +7.33 | −9.41 | −5.59…−5.93 | **3.48–3.82** |
| 09-28 1000SHIB/DOGE | long | −1.31 | −2.78 | −3.61 | **−1.90** | −1.77 | −1.56 | **0.19–0.22** |
| 09-29 ETH/BTC | short | +1.11 | +2.79 | +3.56 | +3.56 | −2.14 | −2.08 | **0.06** |
| **total** | | | | | | **−40.62** | | **≈ 8.5** |

- **A perfect intra-bar stop at 3.5 recovers at most ~8.5 of 41.67** — an
  upper bound, assuming z passed continuously through 3.5. Two stops carry most
  of it (09-26, 09-17).
- **09-28 is a different animal:** it fired at live −3.61 when the spread, in
  the frame it was entered in, was only at **−1.90**. A refit one hour into the
  hold cut sigma by about a third. The ruler moved, not the spread — and the
  loss was small (−1.77). It is one event on task 03's frozen-versus-trailing
  axis; task 06 (Wed 10-07) is the place to weigh it.

## (b) Loss-control levers, scored on all 23 trips — winners included

A lever that saves stops but also cuts winners must show both. `levers.py`
applies each to every trip's hourly z path. **A tighter stop also blocks entries
beyond it** (the entry rule is `entry_z < |z| < stop_z`) — the first pass of
this analysis missed that and overstated it by the best winner of the phase.

| lever | Phase II (in-sample) | Phase I, live-regime era, n=25 (out of sample) | Phase I, all, n=31 |
|---|---|---|---|
| hourly stop at **3.0** | **−8.32** | **−4.75** | −14.32 |
| hourly stop at **2.5** | **+4.58** | **+2.61** | −6.96 |
| intra-bar stop at **3.5** (upper bound) | **+8.51** | — | task 01: ceiling ≈ +6.30 on 8 stops |

**A tighter stop is not a lever. Do not change `stop_z`.** The in-sample gain
at 2.5 shrinks out of sample and turns negative across all of Phase I. The
mechanism is task 04's finding: a tighter stop forbids deep entries, and deep
entries stopped *less* often — KAS/ETC entered deep for +13.5, TAO/RENDER gave
three winners. Whether 2.5 "helps" depends on which deep winners happened to
occur. That is noise, not an edge. (`oos.py` holds trips with a refit inside the
hold at their actual P&L rather than estimating them; its first version did not,
and turned the 08-05 "reverted" −4.12 into a phantom +13.23.)

**The intra-bar stop at 3.5 is different in kind**: it fires at the *same*
threshold, only sooner, so it forbids no entries. Its two unknowns:

1. **Gaps.** If z jumps straight through 3.5 between samples, a monitor saves
   less than the overshoot. 09-26 went 2.90 → 5.38 inside one hour; whether
   that was a slide or a gap is exactly what the record cannot say.
2. **False positives** — z touching 3.5 inside the hour and reverting before the
   bar. The 09-14 trade read **3.23 at an hourly bar** and still closed +0.97;
   inside the hour it may have touched 3.5. A monitor would have cut it at
   roughly −3 to −4.

**Rate limits are not a constraint** (organizer, 10-02: 20 requests/s per portfolio,
both venues): a firing is two close orders; sampling is ~4 reads per 5 minutes.

**`z_sample` (live since 09-29) measures both, but only while a position is
held near its stop** — which is rare, so the evidence may not arrive before
11-04.

## (c) Score scenarios

`scenarios.py`, daily 23:50 rows — a close-to-close proxy. The scorer's own
Sharpe for us was −0.10 on 09-29 against this proxy's +0.75, so read the
**changes**, not the levels:

| scenario | return | Sharpe (proxy) | daily MDD |
|---|---|---|---|
| actual | +0.43% | +0.75 | 2.71% |
| perfect intra-bar 3.5 | +1.28% | **+2.41** | 2.26% |
| sizing ×2 | +0.86% | +0.79 | 5.38% |
| perfect 3.5 + sizing ×2 | +2.56% | +2.44 | 4.48% |

**Leaderboard neighbourhood (09-29 board)** — not a model, just where profiles
like these sat:

| rank | team | score | return | Sharpe | MDD |
|---|---|---|---|---|---|
| 1 | Imnzzz | 93.9 | +6.1% | 4.60 | 3.8% |
| 2 | Stream4AI | 91.6 | +6.6% | 3.00 | 4.1% |
| 3 | Quantech | 90.0 | +11.1% | 3.23 | 8.7% |
| 4 | Gamma Reasoning | 81.3 | +1.8% | 3.02 | 2.7% |
| 6 | X-Explore | 72.1 | +2.2% | 1.95 | 14.3% |
| 7 | T.Anh | 70.7 | +0.1% | 1.98 | 0.2% |
| 9 | **NDAR** | 61.3 | +0.1% | −0.10 | 3.1% |

Gamma (4th) against Stream4AI (2nd): the same Sharpe, 1.8% against 6.6% return,
81 against 92. **The top three need Sharpe ~3 AND return ~6%+.** A Sharpe around
2 at near-zero return sits at 6th–7th (T.Anh). Sizing doubles return and MDD and
leaves Sharpe where it is; it cannot buy rank on a zero edge.

## (d) The odds, restated

- **Top 3: unlikely.** It needs ~6× the realised daily edge at today's
  volatility for 35 days, or a field collapse. Not impossible — ranks moved
  15th → 9th in twelve days — but no decision on the table produces it.
- **Top 5–7: realistic** if loss control works and the edge holds at its
  measured level. Being 4th would need Gamma-like Sharpe (~3), which even the
  upper-bound monitor scenario does not reach in the proxy.
- **Honesty check on the evidence:** Phase II's per-trade edge is t = +0.46
  over 22 trips (task 07). Every projection above assumes the past pace
  persists, and that pace is statistically indistinguishable from zero.

## (e) Macro-event exposure

The organizer's 09-30 Market Watch names U.S. PCE as the key catalyst; the
sentinel rates assets individually, so market-wide releases read `none`. The
2026-07-28 macro-awareness row has never been decided.

**What the record can say:** the stops fell on Tue 09-15 20:00, Wed 09-16 10:00,
Thu 09-17 17:00, **Sat 09-26 17:00**, Mon 09-28 17:00 and Tue 09-29 08:00 UTC.
**The largest overshoot was on a Saturday**, when no U.S. macro data is
released, so a scheduled-release gate would not have touched it. The 09-15→17
cluster may coincide with a mid-September FOMC meeting — **unverified here; the
repo holds no event calendar**, so check the dates against one before reading
anything into it.

**What it cannot say:** whether gating entries around releases helps. Six stops,
no calendar, no counterfactual. Selective size reduction *would* move Sharpe
(unlike uniform sizing), so it is not a dead lever — just an unmeasured one.

---

## Decisions for Sunday

| # | decision | recommendation | why |
|---|---|---|---|
| 1 | change `stop_z` | **no** | in-sample gain does not survive out of sample; forbids profitable deep entries |
| 2 | **intra-bar stop at 3.5, acting on the 5-minute samples** | **build it, disclosed, with the caveats stated** | the only lever that moves Sharpe; it fires at the same threshold, only sooner, and forbids no entries; downside per false positive is bounded (one early exit at 3.5); and the wait-for-evidence path cannot conclude before 11-04. It reverses the 09-13 decision to drop it, on two changed facts — the goal, and samples that let every firing be audited afterwards |
| 3 | sizing | **no** | no Sharpe effect; doubles MDD |
| 4 | breadth | **no** | task 07 |
| 5 | macro gating | **leave open** | unmeasured; largest overshoot was on a Saturday |
| 6 | frozen-frame stop | **no change** | one event each way (09-26 earlier and cheaper; 09-28 would not have stopped at all); task 06 informs |

**If decision 2 is yes**, the build is a new trading path that closes
positions, and gets the full treatment: disclosure in `LTP_STRATEGY.md`, the
same blocking logic as the hourly stop, a test that it fires only past
`stop_z` and only on a held side, and a `z_sample`-based audit of every firing
against what the hourly bar would have done.
