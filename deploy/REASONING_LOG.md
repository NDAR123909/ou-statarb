# Reasoning Log — Team NDAR

**LTP Liquidity Arena 2026, Track A "Logic Frontier" · Phase I**
Portfolio 2188959816060766 · live 2026-07-20 → 2026-08-21 · 1,000 USDT seed

This document explains how to read the accompanying records. The machine-
readable log is `reasoning.jsonl`; `MANIFEST.txt` carries row counts, an event
tally and a SHA-256 for every file, so nothing here has to be taken on trust.

Source code, including every component named below, is public at
`github.com/NDAR123909/ou-statarb`.

---

## 1. What the agent is

A systematic Ornstein-Uhlenbeck pairs-trading agent. It trades mean reversion
of cointegrated spreads between crypto perpetuals, market-neutral by
construction — every position is two legs, long one asset and short a
hedge-ratio multiple of another.

**The mathematics decides every trade. The language model can only refuse or
shrink one.** That division is deliberate and it is the reason this log can
claim internal consistency: a decision's narrative is assembled from the same
quantitative inputs that produced the decision, at the moment it is taken.
There is no separate step where a model is asked what it thinks and the answer
is written down as justification.

The pipeline, per pair, per refit:

1. **Selection** (`statarb/selection.py`) — Engle-Granger cointegration with a
   Benjamini-Hochberg FDR correction applied across *every* test run, plus
   split-half cointegration and hedge-ratio stability, a 6h–168h half-life
   band, mean-crossing density, and a Hurst cap.
2. **Band optimisation** (`statarb/thresholds.py`) — entry and exit thresholds
   from exact OU first-passage times, net of a two-leg cost model. Pairs whose
   edge cannot pay the toll are refused.
3. **Sizing** — volatility-targeted at a fixed fraction of NAV per pair, under
   a gross-exposure cap and the venue's 2× leverage limit.
4. **Risk** — a structural-break z-stop at 3.5σ with a one-sided re-entry
   block, a maximum hold of 3× the fitted half-life, a drawdown kill switch,
   and a maintenance-window guard.

---

## 2. The audit chain

Every record carries `ts` and `event`. The chain is:

```
decision  →  reasoning  →  operations  →  execution
 (enter)     (in-record)   (operation)    (fills/)
```

A worked example, an entry:

- an **`enter`** record carries the pair, side, z at decision, the fitted
  `mu` / `sigma` / `beta` / `half_life`, the entry and stop bands, the
  computed size and any `size_mult` applied by a risk control, plus
  `reasoning` — prose generated from exactly those numbers;
- **`screening_provenance`** fields on the same record state which gates
  actually screened it: `screened`, `news_status`, `news_severity` per leg,
  `news_age_h`, `regime`, `regime_confidence`;
- two **`operation`** records follow, one per leg, carrying the venue's
  response;
- the realised outcome appears in `fills/`, reconciled against the venue's own
  execution records.

Exits work the same way, with `exit`, `stop` or `refit_drop` as the decision
event. Exits additionally carry `z_in_entry_coords`, `mu_shift_sigma` and
`equilibrium_reestimated` — see §5.

---

## 3. Decisions not to trade are logged too

We assume an audit cares as much about restraint as activity, so every path
that *refuses* a trade writes a record:

| event | meaning |
|---|---|
| `skip` `reason=side_blocked` | the one-sided re-entry block after a stop |
| `skip` `reason=news_veto` | the news sentinel rated a leg critical |
| `skip` `reason=anomaly_veto` | the analyst rated the regime broken |
| `skip` `reason=gross_cap` | the entry would breach gross exposure |
| `skip` `reason=min_notional` | vol-targeted size below the venue minimum |
| `size_reduced` | a control halved the position rather than refusing it |
| `refit_drop` | a held pair failed re-selection and was closed |

**Of those, exactly one has ever fired.** `MANIFEST.txt` reports the count for
every path, including the ones that sat at zero, because "five refusal paths
exist" and "one of them has ever triggered" are very different claims and an
audit deserves the second. The one that fires is the **one-sided re-entry
block** — after a z-stop, that side stays shut until the spread heals back
inside the entry band. It has refused entries in double digits, which on a book
this selective is a material fraction of the signals ever generated, and
whether it protected us or cost us is an open question we are carrying into
Phase II rather than one we claim to have answered.

The news and anomaly vetoes have never triggered in live trading. We say so
plainly rather than presenting an unexercised control as a working one.

**The most important restraint is not a skip at all.** Across 22 scored refits
the selection gate passed a mean of **0.91 pairs out of 15 candidates**, one
pair 59% of the time and **zero 27% of the time**, and only **5 of the 15
candidates ever passed at all**. Each refit writes a `refit` record and an
`ai_refit_review` record naming the rejection reason per candidate. Long
stretches with no position are the pipeline working, not the agent idling, and
the log shows the reasoning bar by bar throughout.

No gate was ever loosened to manufacture a trade, including during a
three-day stretch with zero tradeable pairs while our score was falling.

---

## 4. Where the language model is used

All AI calls go exclusively through the organizer's gateway
(`LTP_COMPETITION_MODE=1` hard-refuses any self-provided key).

| layer | event | role |
|---|---|---|
| Spread assessment | `ai_spread_assessment` | hourly, per open pair: reads the z path, half-life and band, and rates the regime `normal`/`stressed`/`broken` |
| News sentinel | `news_assessment` | hourly: per-asset event severity; `critical` vetoes an entry, `watch` halves size |
| Refit review | `ai_refit_review` | per refit: what the rejection pattern implies about the regime |
| **Deep review** | `ai_deep_review` | **advisory only — see below** |

**Two properties matter for the audit.** First, the veto reads an
enum-validated `regime` field, so prose alone cannot move the book — a model
answering in free text cannot change trading. Second, `news_assessment` is
written on every refresh *including when there is no relevant news*, because
"we looked and found nothing" is itself evidence of cadence.

### `ai_deep_review` is not in the decision path

It ships in a separate file, `ai_deep_review.jsonl.gz`. It is a per-candidate
and per-conclusion adversarial review, run daily, in which the model is
instructed to attack our reasoning rather than agree with it.

It dominates the raw log: **it is the majority of records and the large
majority of bytes** — `MANIFEST.txt` carries the exact counts and sizes for
this build, and they are the figures to quote rather than anything stated here.

**It never touched a trade.** Nothing imports it; the agent never reads the
ledger (append-only from its side); they are separate processes. This is
asserted by source inspection in
`tests/test_ai_deep_review.py::test_it_places_no_orders_and_touches_no_agent_state`.

It is separated rather than merged because mixing it in would drown the
decisions that actually drove trades in analysis that drove none of them.
Its volume also has a cause worth stating plainly: on 2026-08-12 the
organizer warned that AI spend below USD 1 is disqualifying, and this layer was
built and scheduled in response. The analysis is real and was already on our
review agenda, and roughly two-thirds of each run is per-candidate analysis on
freshly fitted numbers — but the *cadence* is compliance, not a research
decision, and every repeated pass is stamped `pass_index` so a reader can tell
which is which.

---

## 5. Where to find the final result of each operation

The requirement asks for the **final result of every operation**. Every
`operation` record carries its outcome — `result: "filled"` or
`result: "closed"` — and placements additionally carry `executed_price`,
`executed_qty` and the venue `order_id`.

**Close operations are the exception, and the cause is the venue's API rather
than our logging.** Its close response carries no `orderId` and no price at the
top level. Every close record therefore also stores the response's own key
names (`response_keys`), and those show the payload is **nested** — the probe
was reading the wrong depth, not guessing the wrong field names. The fix was
deliberately not shipped during the competition: `close_position` is the path
that flattens live positions, and an exception there means a position that will
not close.

**So the execution price of every close is in `fills/`**, reconciled against
the venue's own `transaction executions` endpoint and matched by symbol and
timestamp. The chain completes across two files rather than inside one record:

```
reasoning.jsonl   decision (why)  ->  operation (what, and that it closed)
fills/*.json      execution (at what price, what fee, against venue rpnl)
```

Each dated snapshot also carries the venue's own realised P&L beside ours, an
independent check that agreed to within 0.11 USDT across the first eleven round
trips.

## 6. Known gaps

Stated because an audit is entitled to them, and because a log that hides its
limits is worth less than one that names them.

1. **The ledger cannot say what any exit was executed at.** `close_position`
   records `executed_price: null` — the venue's close response nests the
   fill data below the level our probe inspects. The `response_keys` field
   records the response's own key names so this was diagnosable from the log
   rather than by re-probing. **Realised exit prices therefore come from
   `fills/`**, matched by symbol and timestamp against the venue's execution
   records, and every P&L figure we report depends on that reconciliation.
2. **Week 1 executions are unrecoverable.** `transaction executions` serves
   roughly seven days and then refuses — this is retention, not a query limit
   (a six-day window over Jul 20–26 was rejected while later windows of equal
   width succeeded). Snapshots have been taken daily since 2026-08-02; before
   that date only decisions survive, not fills.
3. **The news sentinel does not refresh when no pair is active**, because it
   refreshes for the assets of already-selected pairs. A pair selected out of a
   drought can therefore be entered against verdicts that never covered its
   legs. Since 2026-08-14 provenance reports this honestly as
   `news_status: stale` or `missing_legs` with `screened: false`, rather than
   claiming a screening that did not occur. The behavioural fix was deferred
   rather than shipped into the final days of the phase.
4. **Corporate actions and token events are not modelled.** The z-stop limits
   the damage; an event filter before entry is wanted.
5. **Funding was measured, not modelled** — net +0.34 to +0.39 USDT received
   across ~96 settlements, about 0.04% of NAV.
6. Four logging gaps were found and closed on 2026-08-02 (`refit_drop` events,
   `size_reduced` events, close prices, close order IDs) and a fifth on
   2026-08-08 (`side_blocked`). Decisions taken *before* those dates are less
   completely instrumented than later ones. The dates are in the log.

---

## 7. Honest performance framing

The reference backtest for this framework is **0.36 net Sharpe out-of-sample**
on a 31-name equity universe (2006–2017), corrected down from a previously
published 0.44 after a bug was found that flattered it. That correction is in
the repository's `IMPROVEMENTS.md`.

Live Phase I ran a **single pair at a time out of 15 candidates**, not the
multi-pair portfolio the engine was written for. That is the largest gap
between backtest and deployment in this record, and it was not visible until
the pass-rate distribution was measured on 2026-08-15.

A headline live Sharpe above 9 was recorded in early August. **It was never
real** — it reflected a short low-variance streak on ~14 daily returns, and one
−0.8% day moved it to 5.66 by arithmetic alone. We say so in our own review log
on the day it happened.

---

## 8. Verifying this

- **`MANIFEST.txt`** lists SHA-256 and byte size for every file.
- **`reasoning.jsonl`** is one JSON object per line, chronological.
  `pandas.read_json(..., lines=True)` loads it directly.
- **`fills/`** holds dated reconciliations against the venue's own execution
  records, including the venue's `rpnl` as an independent check on our
  computed P&L.
- The full source, the weekly review log with every decision and every
  correction, and the strategy pre-registration are public at
  `github.com/NDAR123909/ou-statarb` under `deploy/`.
