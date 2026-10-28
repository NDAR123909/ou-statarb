# Phase II post-mortem — LTP Liquidity Arena 2026, Track A

> **DRAFT, written 2026-10-25 with ten days of the phase left.** Every number is
> as of the 2026-10-25 ledger export (`live/track-record` `864ddf4`) unless
> marked otherwise. Sections marked **[final after 11-04]** are completed when
> the phase closes. Nothing here is back-edited after the fact: corrections are
> added beside what they correct, as everywhere else in this repo.

This is the document the project was built to produce: what a statistically
honest pairs strategy did with live capital, what we expected it to do, where
the two differed, and every mistake we made along the way. It is written for a
reader who wants to check it, not to be impressed by it.

---

## 1. The result

| | Phase I (sandbox, 07-20 → 08-21) | Phase II (live capital, 09-09 → 11-04) |
|---|---|---|
| Finish | **6th of 30**, advanced | **[final after 11-04]** — outside the public top 10 at 10-25 (11th at best; model score ~2 below 10th place) |
| Return | +3.8% | −0.7% (equity 992.56 on 10-25) |
| Sharpe (scorer's) | **4.86 — highest of all 30 teams** | ~~~0 (our estimate; last published 0.23 on 10-13)~~ **−0.82 on the 10-27 board**, lowest in the visible top 10. Reproduced from our hourly NAV: −1.22 under the scorer's definition over 09-30 → 10-24. The "~0" was too generous (corrected 10-27) |
| Max drawdown | 3.7% | ≥ 4.02% (our hourly series; the scorer's is ≥ this) |
| Round trips | 140 trades (board count) | 50 closed (to 10-24) |

**One-line verdict, as of 10-25: the strategy's live edge measured
indistinguishable from zero** — 50 Phase II round trips, mean −0.10 USDT, sd
4.86, **t = −0.15**. Phase I's leading Sharpe came from consistent small daily
returns, not from efficient conversion of risk into return: its return per unit
of drawdown was the worst of the top four.

## 2. Backtest versus live

| | expectation | live, Phase II |
|---|---|---|
| Edge | reference backtest: **net Sharpe 0.36 OOS**, 31 DJIA names, 2006-2017, daily bars (`IMPROVEMENTS.md`; corrected from a published 0.44) | per-trip mean −0.10, t −0.15 |
| Fees | 2 bps/side assumed in band design | **~1.6 bps/side measured** |
| Slippage | sandbox 0.57–0.91 bps | **~0.5 bps mean** on live fills |
| Cost share | "costs ~8% of the entry band" (band diagnostics) | **fees 14.53 against gross +9.39** — costs exceeded the gross edge |
| Breadth | multi-pair portfolio, up to 4 pairs | **one pair most of the time**: 1000SHIB/DOGE 39 of 50 trips |

**Where the money went (50 trips):** 32 reversion exits **+83.71**; 15 stops
**−92.13**; 3 refit drops +3.27. The reversion engine worked; the stops took it
back. By pair: **1000SHIB/DOGE +35.83 over 39 trips; every other pair −41 over 11**
(ALGO/HBAR −9.32, KAS/ETC −13.56, NEAR/ICP −8.72, DOGE/1000SHIB −8.61, PAXG/XAUT
−1.08, ETH/BTC +0.33). Five of six newly selected pairs lost money on their first
trades — a small sample, recorded without a conclusion.

**The gap, in one sentence:** a modest daily-equity edge did not survive hourly
crypto spreads net of costs, and a gate honest enough to reject ~97% of
candidates left too few independent bets for the score's Sharpe term, which
stop days decided.

## 3. Every Phase II stop

| when (UTC) | pair | side | entry z | stop z | trigger |
|---|---|---|---|---|---|
| 09-15 20:00 | 1000SHIB/DOGE | long | −0.96 | −3.54 | hourly bar |
| 09-16 10:00 | NEAR/ICP | short | +2.37 | +3.76 | hourly bar |
| 09-17 17:00 | 1000SHIB/DOGE | short | +1.24 | +4.13 | hourly bar |
| 09-26 17:00 | 1000SHIB/DOGE | short | +0.61 | **+5.38** | hourly bar |
| 09-28 17:00 | 1000SHIB/DOGE | long | −1.31 | −3.61 | hourly bar |
| 09-29 08:00 | ETH/BTC | short | +1.11 | +3.56 | hourly bar |
| 10-07 13:45 | 1000SHIB/DOGE | long | −1.83 | −3.80 | intra-bar |
| 10-08 07:20 | ALGO/HBAR | short | +0.74 | +3.60 | intra-bar |
| 10-13 11:20 | DOGE/1000SHIB | short | +1.92 | +3.62 | intra-bar |
| 10-15 14:40 | KAS/ETC | long | −0.95 | −3.53 | intra-bar |
| 10-16 00:10 | 1000SHIB/DOGE | short | **+3.39** | +3.70 | intra-bar |
| 10-21 08:05 | 1000SHIB/DOGE | short | +1.30 | +3.71 | intra-bar |
| 10-23 12:45 | 1000SHIB/DOGE | short | +1.16 | +3.56 | intra-bar |
| 10-23 14:45 | PAXG/XAUT | short | +2.26 | +3.91 | intra-bar |
| 10-24 16:10 | PAXG/XAUT | long | **−3.26** | −3.64 | intra-bar |
| 10-25 18:55 | PAXG/XAUT | short | +2.27 | +3.97 | intra-bar |

**[final after 11-04: any stops 10-26 → 11-04.]** The six hourly-bar stops
overshot 3.5 by ≈ 8.5 USDT in all (upper bound, `deploy/review_prep/2026-10-04/`),
which is what motivated the intra-bar stop.

## 4. The intra-bar stop (deployed 2026-10-05)

The hourly stop's own rule, checked on every five-minute sample. **Ten firings to
10-25, audited against what the hourly stop alone would have done:**

- **Net ≈ +8 USDT saved**, almost all on one firing (10-08 ALGO/HBAR: stopped at
  +3.60, the next bar read +5.98 and the spread reached 12.49; ≈ 7.6 saved).
- **Two false alarms, both PAXG/XAUT** (10-23, 10-24): the hourly stop would never
  have fired and the positions would have reverted; ≈ 2.3 cost. PAXG/XAUT is the
  fastest pair traded (half-life 7.7h) and the noisiest at five-minute scale.
- One firing (10-25) at a worse level than the next bar (≈ −0.3σ).
- Savings are estimated linear in z on each entry's frame; approximate where a
  refit fell inside the hold.

**Not tested, and why:** a two-reading confirmation rule might have avoided both
false alarms, but its cost on the true stops is unmeasurable — sampling ends the
moment a position closes. Not changed with ten days left.

**Near-stop entries:** the only two entries within ~0.25 of the stop since the
intra-bar stop went live (10-15 at +3.39, 10-24 at −3.26) were both stopped. Task
04's finding that deep entries pay was measured under hourly stops. Two cases;
open question for a next version.

## 5. Position size ×1.5 (2026-10-12 → 11-04)

**What:** `risk_per_pair` 0.002 → 0.003 and `per_leg_cap_mult` 0.5 → 0.75, fixed
through the close; kill switch, gross cap, stop and leverage unchanged. A clamp
keeps both order ceilings under the session's 1000 per-order cap.

**Why, as stated before the outcome:** a variance choice for a top-3 objective,
**not a claim of edge** (t = 0.22 on 31 trips at the time). The score formula was
reproduced from the leaderboard (z-composite, components clipped at ±1.5; R²
0.994 across 25 teams) and our daily returns bootstrapped: ×1.5 moved the
simulated top-3 chance ~20% → ~27% and 12th-or-worse ~29% → ~35%, median
unchanged. An automatic revert rule was tested in the same simulation and
rejected.

**Outcome so far:** trips before ×1.5: 31, **+6.60**, mean +0.21. Trips at ×1.5
(to 10-24): 19, **−11.74**, mean −0.62 (≈ −0.41 at the old size). The added
variance went against us in its first week and with us in its second. Simulated
top-3 chance from the position on each review date: 10-18 ~2–5%, 10-25 ~6–7%.
**[final after 11-04: the decision judged against its stated premise, not its
outcome.]**

## 6. Every control that acted

| control | Phase II record |
|---|---|
| Kill switch (12% off peak) | never fired; minimum headroom ~81 |
| Hourly z-stop / intra-bar stop | 6 / 10 firings (§3, §4) |
| One-sided re-entry block | ~150 `side_blocked` skips |
| Gross cap | ~10 `gross_cap` skips, mostly the one-pair-at-a-time cost of ×1.5 |
| AI anomaly veto | **2** (10-20, 10-23) — first blocking AI decisions of the phase |
| News sentinel size reduction | 1 (09-28, halved the entry that then stopped); **a second on 10-27**, details at the final review |
| Reconcile | 1 (10-03: closed a naked leg left by a refused hedge order) |
| Entry unwind / budget skip (10-05 fix) | built after 10-03; not triggered since |
| Maintenance-window guard | six windows, never armed — none contained an hourly tick |

## 7. Mistakes, and how each was caught

| found | what was wrong | caught by |
|---|---|---|
| 09-09 | `entry_frame` measured positions on the live beta, not the entry beta | an audit that went to price prints |
| 09-15 | the AI review prompt said the phase was over; it recommended halting on day 6 | reading the prompt's rendered text |
| 09-21 | that fix sat in git for six days, never deployed | the deploy-key work, by accident |
| 09-27 | `mu_shift_sigma` compared means on two betas (≈91σ "drift" that was arithmetic) | reconstructing one stop from the ledger |
| 09-30 | the universe scan truncated every pair when the symbol list widened | task 07's numbers disagreeing with the live refit |
| 10-03 | the automation budget was cumulative, not a cap on exposure → one naked leg for an hour | the cold start's count of entries vs closes |
| 10-07 | the 09-09 "σ doubled (2.047)" correction was itself the beta-mixing error | task 06, verified from logged fields |
| 10-07 | the week 8 decomposition used rounded betas where exact ones existed | task 06 |
| 10-12 | ×1.5 would have breached the per-order cap on high-β hedge legs | building the change |
| 10-13 | a session container started on a stale branch ref | a failed edit, checked against GitHub before any push |
| throughout | the 2026-09-13 decision to drop the intra-bar monitor (≈ 6.5 USDT of overshoot before it was reversed) | the overshoot table |

**The pattern worth keeping:** most of these were corrections that inherited the
error they corrected, found only by going back to primary records and to the
code that produced a field. Self-consistent logged numbers proved nothing.

## 8. What a next version would test — not claims

1. **Breadth before anything else.** The single largest gap: one pair cannot carry
   a Sharpe-weighted score. Task 07 found no honest breadth in time; a next
   version starts there.
2. **Intra-bar confirmation** on fast pairs, with sampling continued after a stop
   so the cost on true stops is measurable.
3. **An entry margin below the stop** now that the stop is checked five-minutely.
4. **Frame choice at refits** — task 06 found no evidence of equilibrium drift;
   what changed outcomes was σ re-estimated at the refit.
5. **Costs.** Fees exceeded gross P&L over the phase; the band design assumed
   costs were ~8% of the band.

## 9. Sources and reproduction

- Ledger slice: `git show origin/live/track-record:track_record/ltp_ledger_phase2.jsonl`
- Daily state: `track_record/ltp_state_history.jsonl` on `live/track-record`
- Round trips: `deploy/review_prep/2026-10-04/trips.py` over the published fills
- Decisions, in order: `deploy/WEEKLY_REVIEW.md`; behaviour changes: `deploy/LTP_STRATEGY.md`
- Research answers: `deploy/research_queue/out/01`–`07`
