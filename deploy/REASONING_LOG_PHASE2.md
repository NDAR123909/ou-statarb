# Reasoning Log — Team NDAR

**LTP Liquidity Arena 2026, Track A "Logic Frontier" · Phase II (Mainnet Duel Finals)**
Live capital, 1,000 USDT seed · 00:00 GMT+8 2026-09-09 → 23:59 GMT+8 2026-11-04
(16:00 UTC 09-08 → 15:59 UTC 11-04) · Binance USDT perpetuals via RapidX

This document explains how to read the accompanying records. The machine-
readable log is `reasoning.jsonl`. `MANIFEST.txt` carries row counts, an event
tally, the records left outside the phase's window, and a SHA-256 for every
file, so nothing here has to be taken on trust.

**The agent is the one described in our Phase I Reasoning Log (submitted
2026-08-21).** This document states what changed since, what Phase II's records
contain, and what went wrong. For Phase II records, where the two documents
differ, this one governs.

Source code, including every component named below, the weekly review log
with every decision and correction, and the strategy pre-registration are
public at `github.com/NDAR123909/ou-statarb`.

---

## 1. What the agent is

A systematic Ornstein-Uhlenbeck pairs-trading agent. It trades mean reversion
of cointegrated spreads between crypto perpetuals, market-neutral by
construction. Every position is two legs: long one asset, short a hedge-ratio
multiple of another.

**The mathematics decides every trade. The language model can only refuse or
shrink one.** A decision's narrative is assembled from the same quantitative
inputs that produced the decision, at the moment it is taken. There is no
separate step where a model is asked what it thinks and the answer is written
down as justification.

The pipeline is the same as in Phase I:

1. **Selection** (`statarb/selection.py`) over 15 candidate pairs (30 symbols).
   It uses Engle-Granger cointegration with a Benjamini-Hochberg FDR
   correction across every test run, split-half stability of the
   cointegration and the hedge ratio, a 6h–168h half-life band, mean-crossing
   density, and a Hurst cap. Refitted daily.
2. **Band optimisation** (`statarb/thresholds.py`): entry and exit thresholds
   from exact OU first-passage times, net of a two-leg cost model.
3. **Sizing:** volatility-targeted at a fraction of NAV per pair, under a
   per-leg cap and a gross-exposure cap of 2× NAV. Leverage is set at 2× on
   every symbol, against the 5× Phase II allows.
4. **Risk:**
   - a z-stop at 3.5σ with a one-sided re-entry block;
   - a maximum hold of 3× the fitted half-life;
   - a kill switch at 12% below the phase's peak equity;
   - a maintenance-window guard;
   - reconciliation of the venue's positions against the agent's state at
     every bar.

### What changed during Phase II

Every change is disclosed, with its reasoning, in `deploy/LTP_STRATEGY.md`
under the date shown.

| live from (UTC) | change | where it shows in the records |
|---|---|---|
| 2026-09-08 cutover | Production host, live capital. Kill switch re-anchored on Phase II's own peak; the Phase I high-water mark was deleted deliberately, with the book flat | `nav` and kill-switch figures from 09-09 |
| 2026-09-09 (`da7aadb`) | `entry_beta` snapshotted at entry; the entry-frame z is rebuilt on it. Live before the first Phase II entry (09-12), so **every Phase II close is measured in its own entry frame** | `z_in_entry_coords` on every `exit` / `stop` |
| 2026-09-29 21:15 | `mu_shift_sigma` re-expressed on the entry beta (see §7). New logging: `z_sample` (z every five minutes while a position is open), `nav` (hourly equity, peak, drawdown), `z_fixed`, and per-candidate `candidates` / `rejects` / `band_side` on every `refit` | `mu_shift_basis` on every later close |
| 2026-09-30 19:54 | Each pair is tested on its own two legs' overlapping history, not on the overlap of all 30 symbols | `panel` on every `refit` |
| 2026-10-05 03:20 | **Intra-bar stop:** the same 3.5σ rule, checked on every five-minute `z_sample`. **Two legs or none:** a failed second leg unwinds the first. An automation-budget check before entry | `stop.trigger` = `bar` / `intrabar`; `entry_failed`, `entry_unwound`; `skip reason=automation_budget` |
| 2026-10-12 01:13 | **Position size ×1.5**, fixed to the end of the phase: `risk_per_pair` 0.002 → 0.003, per-leg cap 0.5 → 0.75 × NAV. Each leg is clamped to fit the venue's 1,000 USDT per-order cap | `g` on every `enter` |

**What did not change:** the gates, the cost model, the stop level, the kill
switch rule, and the leverage. No gate was loosened to manufacture a trade.

**The agent was stopped at the bell, 15:59 UTC on 2026-11-04.**
**[FINAL AFTER THE BELL: the exact stop time, and any position open at the
bell.]** Per the organizer, positions still open at the cutoff are closed by
the Organizing Committee after the competition. **Those closes are not agent
operations.** No decision record precedes them, and none should.

---

## 2. The audit chain

Every record carries `ts` (UTC) and `event`. The chain is:

```
decision  →  reasoning  →  operations  →  execution
 (enter)     (in-record)   (operation)    (fills/)
```

- An **`enter`** record carries:
  - the pair, side, and z at decision;
  - the fitted `mu` / `sigma` / `beta` / `half_life` and the entry-frame
    snapshot;
  - the entry and stop bands;
  - the computed size `g` and any `size_mult` a risk control applied;
  - `reasoning`: prose generated from exactly those numbers.
- **`screening_provenance`** fields on the same record state which gates
  actually screened it: `screened`, `news_status`, `news_severity` per leg,
  `news_age_h`, `regime`, `regime_confidence`.
- Two **`operation`** records follow, one per leg. Every order goes through a
  RapidX automation session:
  - it is previewed under the session, whose consent text, per-order cap and
    session notional budget are set at startup;
  - it is then submitted, and read back from the venue rather than inferred
    from the submit response;
  - placements carry `client_order_id`, `order_id`, `max_notional`,
    `order_state`, `executed_qty` and `executed_price`.
- The realised outcome is in `fills/`, reconciled against the venue's own
  execution records (§5).

Exits work the same way. The decision event is `exit`, `stop` (with
`trigger`, from 2026-10-05) or `refit_drop`. Every close also carries:
- `z_in_entry_coords`, `mu_shift_sigma` and `equilibrium_reestimated`, which
  say where the spread stood in the frame the position was opened in;
- from 2026-09-29, `mu_shift_basis` (§7) and `z_fixed`, a counterfactual z on
  a fixed 72-bar sigma window.

---

## 3. Decisions not to trade are logged too

Every path that *refuses* or *shrinks* a trade writes a record:

| event | meaning |
|---|---|
| `skip` `reason=side_blocked` | the one-sided re-entry block after a stop |
| `skip` `reason=news_veto` | the news sentinel rated a leg critical |
| `skip` `reason=anomaly_veto` | the spread assessment rated the regime broken |
| `skip` `reason=gross_cap` | the entry would breach 2× NAV gross |
| `skip` `reason=min_notional` | vol-targeted size below the venue minimum |
| `skip` `reason=automation_budget` | the automation session's remaining budget could not cover both legs |
| `size_reduced` | a control halved the position rather than refusing it |
| `entry_failed` / `entry_unwound` | an order was refused; the pair was left flat |
| `refit_drop` | a held pair failed re-selection and was closed |
| `reconcile` | the venue held something the agent's state did not; it was closed |

**In Phase I exactly one of these ever fired. In Phase II several did:**
- the re-entry block, many times;
- the gross cap, mostly from 2026-10-12, when ×1.5 made one pair's gross
  ~1.4–1.5× NAV, so a second pair's signal could not fit;
- **the anomaly veto, twice** (2026-10-20 and 10-23), the first blocking AI
  decisions of the competition;
- **the news sentinel's size reduction, twice** (2026-09-28 and 10-27);
- one `reconcile` (§6).

`MANIFEST.txt` gives the count for every path, including the ones at zero.
"A control exists" and "a control fired" are different claims, and an audit
deserves the second.

**The most important restraint is still the selection gate.** Most refits
passed one pair or none. Each `refit` record names every candidate with its
pass or fail, the reason, and its fitted half-life. Long stretches with no
position are the pipeline working, not the agent idling.

---

## 4. Where the language model is used

All AI calls go exclusively through the organizer's gateway
(`LTP_COMPETITION_MODE=1` hard-refuses any self-provided key).

| layer | event | role |
|---|---|---|
| Spread assessment | `ai_spread_assessment` | hourly, per active pair: reads the z path, half-life and band, and rates the regime `normal` / `stressed` / `broken`; `broken` vetoes an entry |
| News sentinel | `news_assessment` | hourly: per-asset event severity; `critical` vetoes an entry, `watch` halves its size |
| Refit review | `ai_refit_review` | per refit: what the rejection pattern implies about the regime |
| **Deep review** | `ai_deep_review` | **advisory only — see below** |

The veto reads an enum-validated `regime` field, so prose alone cannot move
the book. `news_assessment` is written on every refresh, including when there
is no relevant news, because "we looked and found nothing" is itself evidence
of cadence.

### `ai_deep_review` is not in the decision path

It ships separately, as `ai_deep_review.jsonl.gz`. **In Phase II it is too
large to attach to an email, so it is delivered by link.** Its SHA-256 is in
`MANIFEST.txt`, so the copy received can be checked against the one we
built. It is a daily, per-candidate adversarial review in which the model is
told to attack our reasoning rather than agree with it.

**It never touched a trade.** Nothing imports it, the agent never reads the
ledger, and they are separate processes. Asserted by source inspection in
`tests/test_ai_deep_review.py::test_it_places_no_orders_and_touches_no_agent_state`.

Its volume has a cause worth stating plainly: two scheduled passes a day keep
spend above the USD 1 floor. The analysis is real, but the cadence is
compliance, and every repeated pass is stamped `pass_index`.

**One window of it is contaminated, and we say so.** From the opening of
Phase II until 2026-09-21, the prompt that briefs each deep review on our risk
budget still carried Phase I constants. It said **"0 days remain" in the
phase**, gave Phase I's kill-switch level, and said our advancement was
assured. On 2026-09-15 a reviewer, reasoning correctly from what it was told,
recommended halting all trading on day 6 of 57. The recommendation went
nowhere, because deep review is advisory. The fix was written on 09-15 and
reached the droplet on 09-21. **Any reading of deep reviews from 09-09 → 09-21
must discount every answer conditioned on the risk briefing.** The records are
left as written, because the ledger records what the agent was told at the
time. Disclosed in `LTP_STRATEGY.md`, 2026-09-15.

---

## 5. Where to find the final result of each operation

Every `operation` record carries its outcome: `filled` or `closed`.
Placements also carry `executed_price`, `executed_qty` and the venue
`order_id`.

**Closes still do not carry an execution price, exactly as disclosed in
Phase I.** The venue's close response nests its fill data below the level our
probe reads. Every close record stores the response's own key names
(`response_keys`), which show the nesting. The probe was not rewritten, for
the reason given in Phase I: `close_position` is the path that flattens
positions, and an exception there means a position that will not close.

**So the execution price of every close is in `fills/`.** Each nightly
snapshot (`fills_report.py`, 23:55 UTC) reconciles the ledger's round trips
against the venue's own `transaction executions` for roughly the week before
it, and records fees, funding and the venue's realised P&L beside ours.
Snapshots therefore overlap: the first ones reach back before the phase, and
the last (2026-11-04) may include the Committee's post-bell closes. **Match
fills to decisions by symbol and timestamp.** `MANIFEST.txt` names any day of
the phase without a snapshot.

```
reasoning.jsonl   decision (why)  ->  operation (what, and that it closed)
fills/*.json      execution (at what price, what fee, against venue rpnl)
```

---

## 6. The one incident with money at risk: a naked leg, 2026-10-03

At **15:00 UTC on 2026-10-03**:
- the first leg of an entry, a ~509 USDT 1000SHIB short, filled;
- the second leg was refused: `RCLI26005 automation maxTotalNotional exceeded`.

We had read the automation session's budget as a cap on exposure. **It is a
cumulative total of the opening orders' ceilings over the session**, and it
had run out. The exception unwound the whole bar before the agent's state
recorded the fill. So the agent believed it was flat, while the venue held a
naked memecoin short.

**The next bar's reconciliation found it and closed it** (the `reconcile`
record at 16:00). It cost nothing that hour. A 5% move would have cost more
than any stop of the phase to that date.

**Fixed 2026-10-05:**
- an entry is now **two legs or none**;
- a refused second leg unwinds the first, logged as `entry_unwound`;
- the remaining session budget is checked before the first leg is sent
  (`skip reason=automation_budget`);
- the session budget was raised from 4,000 to 12,000 USDT
  (`LTP_AUTOMATION_MAX_TOTAL`).

---

## 7. Known gaps

Stated because an audit is entitled to them.

1. **Close prices are in `fills/`, not in the ledger** (§5).
2. **Before 2026-10-05 the stop was checked only on the hourly bar**, so a
   spread that crossed 3.5σ between bars was stopped at the next bar, beyond
   the threshold. Those stops carry no `trigger` field. From 10-05 the same
   rule is checked every five minutes. We audited every intra-bar firing
   against what the hourly stop alone would have done. Net, they saved money,
   almost all of it on one firing. They also produced false alarms, all on
   PAXG/XAUT, the fastest and noisiest pair we traded. **[FINAL AFTER THE
   BELL: firings, false alarms and net effect, through the close.]**
3. **Maintenance windows blind the five-minute check.** During the venue's
   announced maintenance windows, the sampler's price reads fail and are
   skipped. A held position is then protected only by the hourly bar. The
   maintenance guard (`LTP_MAINTENANCE_WINDOWS`) was never armed in Phase II:
   every announced window fell between two hourly decision ticks, and arming
   it would only have closed positions early for no protection.
4. **`mu_shift_sigma` was wrong on Phase II closes before 2026-09-29 21:15.**
   It compared means fitted on two different hedge ratios, so any refit that
   moved beta produced a large, meaningless "equilibrium shift". Two published
   exit reasonings state false magnitudes from it: 2026-09-14 1000SHIB/DOGE
   ("re-estimated by +12.55 sigma") and 2026-09-27 ETH/BTC ("+91.96 sigma").
   Their entry-frame z values are correct; the sigma figures are not.
   Trading was unaffected: exits and stops are computed on the live z.
   **Not back-edited.** Every later close carries `mu_shift_basis`, so the
   two kinds are distinguishable.
5. **Restarts.** Each deploy or reboot restarts the agent. Its first bar runs
   at once, off the hourly cadence, and can act: on 2026-09-30 a deploy's
   startup bar exited an open position mid-hour. Each restart also moves the
   daily refit one hour earlier. Every restart, with its time and reason, is
   in `deploy/WEEKLY_REVIEW.md`.
6. **News screening can be stale.** As in Phase I, an entry whose legs were not
   freshly rated says `news_status: stale` or `missing_legs` with
   `screened: false`. Such an entry was not screened, and the record says so.
7. **The organizer's AI gateway failed from 2026-10-30 ~16:00 UTC** for us and
   other teams: every call returned HTTP 402,
   `insufficient_balance_error (1008)`, from the upstream model provider. The
   agent behaved as in Phase I's key expiry: fail-open and loud.
   - one `sentinel_degraded` record on the transition;
   - an `ai_assessment_unavailable` record on every bar while it lasted;
   - every entry in that window marked `screened: false`.

   For us it lasted from 16:00 UTC 10-30 to 01:00 UTC 10-31: **nine hourly
   bars without AI assessment.** The USD 1/day floor for that budget period
   was still met inside the period: a manual deep-review pass, run once the
   gateway was back, reached $1.15 at ~04:33 UTC 10-31. **[FINAL AFTER THE
   BELL: how many entries ran unscreened in that window.]**
8. **Funding was measured, not modelled.** It is in `fills/`.
9. **Corporate and token events are not modelled.** The z-stop limits the
   damage. Every delisting notice we received was checked against the symbols
   we trade; none named one.

---

## 8. Honest performance framing

The reference backtest for this framework is **0.36 net Sharpe out-of-sample**
on a 31-name equity universe (2006–2017), corrected down from a previously
published 0.44 after a bug was found that flattered it.

In Phase I we finished 6th of 30 with the highest Sharpe of the field. But
our return per unit of drawdown was the worst of the top four, and we said so
at the time.

**In Phase II the strategy's live edge measured indistinguishable from zero.**
Over the first 50 round trips (to 2026-10-24), the mean was −0.10 USDT per
trip (t = −0.15), and fees (14.53 USDT) exceeded gross trading profit (9.39).
The selection gate
rejected most candidates, so the book held one pair most of the time, not the
portfolio the engine was written for. That is the largest gap between
backtest and deployment in this record. **[FINAL AFTER THE BELL: final equity,
return, Sharpe, MDD and rank; the edge over every Phase II round trip.]**

**The ×1.5 size increase on 2026-10-12 was a choice of variance, not a claim of
edge.** It was made and written down as such before its outcome was known.
Size scales return and drawdown together and leaves Sharpe unchanged.

---

## 9. Verifying this

- **`MANIFEST.txt`** lists SHA-256 and byte size for every file, including
  `ai_deep_review.jsonl.gz`, which is delivered separately.
- It also states the window, `2026-09-08T16:00Z <= ts < 2026-11-04T16:00Z`,
  and how many ledger records fell outside it. Those were left out, not lost.
- **`reasoning.jsonl`** is one JSON object per line, chronological.
  `pandas.read_json(..., lines=True)` loads it directly.
- **`fills/`** holds the nightly reconciliations against the venue's own
  execution records, including the venue's `rpnl`.
- The droplet publishes its daily state, a Phase II ledger slice and every
  fills snapshot to the public branch `live/track-record` each night, so git's
  own timestamps show when each record existed.
