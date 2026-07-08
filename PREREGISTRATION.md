# Preregistration — ou-statarb live paper-trading experiment

**Registered:** 2026-07-07 (first live run committed the same day).
**Author:** repository owner, via the `ou-statarb` framework.
**Status:** ACTIVE. Frozen for the duration of the experiment.

This document is a *preregistration*: it states, in advance and in a
git-timestamped commit, exactly what strategy is being run and under what rules,
so that the live track record cannot later be reinterpreted, cherry-picked, or
quietly retuned into looking better than it was. It exists for one reason — the
project's non-negotiable principle is **honesty over performance**, and the only
way a paper track record proves anything is if the hypothesis and every
parameter were fixed *before* the data arrived.

The git history of this file is the evidence. If any parameter below changes,
the change is a new commit with a dated rationale, and it is (per the amendment
rules) either a bug fix or the start of a *new* experiment — never a silent edit
to this one.

---

## 1. Hypothesis

A disciplined, cost-aware Ornstein-Uhlenbeck pairs strategy on a small,
sector-restricted universe of large-cap US equities produces a **positive net
Sharpe ratio out-of-sample, after realistic costs**, over a six-month live
paper-trading window.

Stated honestly up front: the real-data backtest that motivates this work
netted **Sharpe ≈ 0.44 OOS** on a 31-name universe (2006–2017, see
`IMPROVEMENTS.md`). That is a weak-but-real edge. The live experiment is **not**
expected to beat it; the expected outcome is a live Sharpe *at or below* the
backtest, and the scientifically valuable result is the size and direction of
the **backtest-vs-live gap**, not the raw number. A negative or zero live
Sharpe is a publishable, honest result and will be reported as such.

## 2. Universe (frozen)

Eight hand-chosen, same-sector candidate pairs (`deploy/run_strategy.py::CANDIDATES`,
mirroring `quantconnect/main.py`). The economic restriction to same-sector pairs
*is* the primary multiple-testing control:

| Pair      | Sector              |
| :-------- | :------------------ |
| V / MA    | payment networks    |
| KO / PEP  | beverages           |
| XOM / CVX | oil majors          |
| HD / LOW  | home improvement    |
| UPS / FDX | parcels             |
| GS / MS   | investment banks    |
| UNP / CSX | rails               |
| MCD / YUM | restaurants         |

No symbol appears in two pairs (the per-pair position ledger depends on this).
Data is Alpaca's own split- and dividend-**adjusted** daily bars. The universe
is fixed for the experiment; expanding it starts a new experiment.

## 3. Strategy parameters (frozen)

All values are the defaults in `deploy/run_strategy.py::StrategyConfig`,
`statarb/selection.py::SelectionConfig`, and `statarb/costs.py::CostModel` as of
the registration commit. They are reproduced here so the record is
self-contained; the code is the source of truth and the two must agree.

### Sizing & risk
| Parameter                    | Value            | Meaning                                           |
| :--------------------------- | :--------------- | :------------------------------------------------ |
| `risk_per_pair_bps`          | **10 bps of NAV**| target daily PnL volatility budget per pair       |
| `max_gross_leverage`         | 3.0×             | portfolio gross exposure cap (incl. resting orders)|
| `max_pair_gross_frac`        | 0.5× NAV         | one pair's gross may not exceed half of NAV        |
| account                      | Alpaca **paper**, ~$100k start | vol-targeted against live account equity |

Position sizing is vol-targeted: dollars-per-unit-of-spread `g` is set so each
pair contributes ≈ `risk_per_pair_bps` of equity in daily spread vol, fixed at
entry, capped by `max_pair_gross_frac`.

### Entry / exit / stop
| Parameter        | Value                    | Meaning                                                        |
| :--------------- | :----------------------- | :------------------------------------------------------------- |
| entry / exit `z` | **cost-aware optimal bands** | per-pair `optimal_bands()`; pairs whose costs exceed the edge are dropped |
| **`stop_z`**     | **3.5**                  | structural-break stop; position cut if \|z\| blows past this   |
| re-entry block   | one-sided                | after a stop, that side stays blocked until z heals inside the entry band |
| `max_hold_mult`  | 3.0                      | max holding = 3 × fitted half-life, then flatten               |
| `z_window_mult`  | 3.0                      | rolling z lookback = 3 × half-life (clamped [15, lookback/2])  |

### Selection gate (all tests FDR-corrected across the whole scan)
| Parameter                | Value      |
| :----------------------- | :--------- |
| `fdr_q` (Benjamini-Hochberg) | 0.10   |
| half-life band           | 3.0 – 50.0 days |
| `min_crossings_per_year` | 8.0        |
| `max_hurst`              | 0.47       |
| `max_beta_drift` (split-half) | 0.30  |
| beta magnitude band      | 0.25 – 4.0 |
| `split_adf_pmax`         | 0.15       |
| `max_pairs` kept         | 6 (fastest-reverting survivors) |
| fit `lookback`           | 378 trading days (~18 months) |

### Costs charged (paper-modeled; a known approximation)
| Parameter          | Value        |
| :----------------- | :----------- |
| commission         | 0.5 bps / leg |
| half-spread        | 1.5 bps / leg |
| borrow             | 50 bps/yr flat, accrued daily on short notional |

Borrow is modeled flat; real per-name locate rates differ and this is logged as
a gap, not corrected mid-experiment.

## 4. Schedule (frozen)

- **Weekly refit.** Pair selection + OU fit + optimal bands recompute every
  **7 calendar days** (`refit_days = 7`). Between refits, betas, bands, half-lives,
  and z-windows are **frozen** — daily decisions use only past data through the
  frozen model. Pairs that fail the gate at a refit are flattened immediately.
- **Daily decision step.** Runs once per US trading day after the close
  (`.github/workflows/live.yml`, ~21:35 UTC, DST slop accepted). Signals are
  computed on that day's close; market orders rest and fill at the **next open**.
  This lag is part of the design and is measured, not hidden.
- **Daily snapshot.** Account equity, positions, and fills are appended to
  `track_record/` and committed. The git history is the timestamp.

## 5. Commitment window (frozen)

**Six months of live paper trading**, from the registration date **2026-07-07**
through approximately **2027-01-07** (~126 US trading days).

Interpretation rules fixed in advance:
- Live Sharpe is **statistical noise until ~60+ trading days** have accumulated
  and will be explicitly labeled as such in all interim reporting.
- The experiment is not stopped early for good *or* bad results. Early stopping
  conditioned on performance is exactly the bias this preregistration exists to
  prevent. The only early-termination causes are external: broker/account
  failure, data-feed loss, or a corporate action that structurally breaks a pair
  (each logged with cause).
- The primary reported metric is **net (after-cost) OOS Sharpe** over the full
  window, accompanied by the backtest-vs-live gap, max drawdown, average gross
  leverage, and turnover.

## 6. Amendment rules — what may and may not change during the experiment

This is the core commitment. During the six-month window:

**ALLOWED — bug fixes only.** A change qualifies as a bug fix if it makes the
running system do what *this document already says it does*. Examples:
correcting a broker API response-shape error, fixing a look-ahead leak, fixing
an idempotency or reconciliation defect, fixing an off-by-one in a rolling
window, repairing the workflow so it runs. Every such fix is committed with a
clear message identifying it as a bug fix and what incorrect behavior it
corrected.

**NOT ALLOWED — parameter tuning of any kind.** During the experiment we will
**not** change: `stop_z`, `risk_per_pair_bps`, leverage caps, the entry/exit
band methodology, `max_hold_mult`, `z_window_mult`, any selection-gate threshold
(`fdr_q`, half-life band, crossings, Hurst, beta drift/magnitude, ADF), the fit
`lookback`, the refit cadence, the cost assumptions, or the universe. We will
not add, remove, or substitute pairs. We will not "improve" the strategy in
response to a drawdown, a stopped-out pair, or a disappointing interim Sharpe.
Any temptation to do so is the precise failure mode — fitting to the live sample
— that invalidates a track record.

If a parameter genuinely should change, that is a **new experiment**: it starts
a new preregistration and a new track-record segment with its own start date.
The existing live record is never retroactively relabeled or spliced.

**Distinguishing the two, operationally.** The test for any proposed change is a
single question: *"Would this change the strategy's decisions on data it has
already seen, in a way that depends on how those decisions turned out?"* If yes,
it is tuning and is forbidden until the window closes. If it only corrects a
mechanism to match this spec, it is a bug fix and is allowed.

---

*Verification: this file's introduction into git history predates all but the
first day of live data. A stranger can confirm the parameters above match the
code at the registration commit, and that no forbidden parameter changed during
the window, by reading the commit history of `deploy/run_strategy.py`,
`statarb/selection.py`, `statarb/costs.py`, and this file.*
