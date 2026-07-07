# CLAUDE.md — project context for Claude Code

## What this project is

`ou-statarb` is an Ornstein-Uhlenbeck pairs-trading framework, upgraded in v0.2
from single-pair research code to a multi-pair portfolio engine with production
risk controls. The owner's goal is NOT to maximize backtest numbers — it is to
build a **verifiable live paper-trading track record** that proves the work is
real. Read `IMPROVEMENTS.md` for the full v0.2 changelog and the honest
real-data results (net Sharpe 0.44 OOS on a 31-name universe, 2006-2017).

Guiding principle, non-negotiable: **honesty over performance.** This repo's
credibility comes from being upfront about what doesn't work. Never add code or
docs that overclaim. When a change improves a backtest, the first question is
"what did this fit to?" — not "how do we ship it?"

## Architecture map

```
statarb/
├── ou.py           OU fitting (exact AR(1) form), Engle-Granger spread, core
│                   backtester. v0.2 added stop_z (structural-break stop with
│                   one-sided re-entry block) and legs_cost_mult.
├── kalman.py       dynamic hedge ratio (2-state DLM), incremental KalmanState
│                   for live use, two-leg cost-aware backtest.
├── selection.py    v0.2. FDR (Benjamini-Hochberg) across the whole scan,
│                   split-half cointegration + beta stability, half-life band,
│                   mean-crossings, Hurst. Rejects ~97% of real candidates.
├── thresholds.py   v0.2. Cost-aware optimal entry/exit bands from exact OU
│                   first-passage times (numerical scale/speed-density
│                   integrals, Monte-Carlo-verified in tests). Flags pairs
│                   where costs exceed the edge as untradeable.
├── costs.py        v0.2. Two-leg commission+half-spread, DAILY borrow accrual
│                   on short notional, sqrt-impact capacity estimate.
├── portfolio.py    v0.2. walk_forward_portfolio(): dollar-based multi-pair
│                   walk-forward with vol-targeted sizing (risk_per_pair_bps of
│                   NAV), z-stops, gross-leverage cap. All results OOS.
├── walkforward.py  single-pair rolling refit + edge-decay diagnostic.
├── risk.py         proportional sizing, rolling ADF/half-life regime gate.
├── johansen.py     3+ asset baskets.
└── broker.py       Broker interface, MockBroker (replay), AlpacaPaperBroker
                    (untested against live API — this is the deployment TODO).

quantconnect/main.py   deployable multi-pair LEAN algorithm (sector-restricted
                       candidates, weekly refit gate, vol targeting, z-stops).
examples/real_data_portfolio.py   the real-data validation run; treat its
                                  printed numbers as the reference baseline.
tests/                 27 tests. test_viability.py pins the v0.2 math
                       (passage times vs Monte Carlo, stop caps losses, FDR).
```

## Invariants — do not break these

1. **No look-ahead, anywhere.** Every signal at time t uses data ≤ t. Rolling
   windows are seeded from training tails, never future data. If you touch the
   backtest loop, re-run the full test suite and think twice.
2. **Costs are charged on both legs** plus daily borrow. Any new trading path
   must go through `CostModel`.
3. **Selection changes must keep the FDR correction applied to ALL tests run**,
   including candidates rejected by other filters (they were still tests).
4. **The z-stop's one-sided re-entry block** must survive any refactor: after a
   stop, that side stays blocked until z heals inside the entry band.
5. Old tests are behavioral contracts. `BacktestConfig` defaults must keep
   v0.1 behavior (stop_z=None, legs_cost_mult=1.0).

## Commands

```bash
pip install -e . && pip install statsmodels pytest
pytest                                   # 27 tests, ~20s
python examples/real_data_portfolio.py  # real-data reference run (~5-10 min,
                                         # downloads DJIA csv from GitHub)
```

## The deployment mission (what Claude Code is here to build)

Goal: a tamper-evident, publicly verifiable paper-trading track record.

### Phase 1 — daily snapshot harness (build this first)
- `deploy/snapshot.py`: connects to Alpaca **paper** API, pulls account equity,
  positions, and the day's fills; appends one row to `track_record/equity.csv`
  and writes `track_record/positions/YYYY-MM-DD.json`. Idempotent (safe to
  re-run same day). Fail loudly on auth errors; never write partial rows.
- `deploy/run_strategy.py`: the daily trading step. Reuse `statarb` directly:
  weekly refit via `select_pairs` + `fit_spread_model` + `optimal_bands`
  (mirror the logic in `quantconnect/main.py`), daily z-score check, orders
  via `AlpacaPaperBroker` (which needs finishing/testing — it has never hit
  the real API). Vol-target sizing, stop_z=3.5, max_hold = 3×half-life.
- `.github/workflows/live.yml`: scheduled run at market close (~21:30 UTC,
  handle DST or accept the slop), executes strategy then snapshot, commits and
  pushes `track_record/`. Alpaca keys via GitHub Actions secrets
  (`ALPACA_KEY_ID`, `ALPACA_SECRET_KEY`). The git history IS the timestamp —
  never rewrite history on `track_record/`.
- Universe: start with the liquid sector pairs in
  `quantconnect/main.py::CANDIDATES`; expand later.

Acceptance: workflow runs green on a market day, produces a commit containing
equity + positions, and re-running produces no duplicate rows.

### Phase 2 — verifiability & reporting
- `deploy/report.py`: regenerate a `track_record/README.md` each run — equity
  chart, live Sharpe (mark clearly as noise until ~60+ trading days), gross
  leverage, and **backtest-vs-live gap notes**.
- A `VERIFY.md` explaining how a stranger can audit the record (git timestamps,
  Alpaca account activity export cross-check).

### Phase 3 — the post-mortem inputs
Log everything needed for the "backtest vs live" writeup: intended vs filled
price per order (slippage), pairs the selector approved that later stopped out,
borrow availability issues. Structure logs so the analysis is a pandas one-liner
later.

## Known gaps / gotchas

- `AlpacaPaperBroker` in `broker.py` is unexercised against the real API —
  expect signature/response-shape fixes on first contact.
- Corporate actions (mergers, spinoffs) are unhandled; the z-stop limits damage
  but an event filter before entry is a wanted improvement.
- Borrow is modeled flat at 50 bps/yr; real locate rates are per-name. Fine for
  paper; note it in the gap analysis.
- The DJIA csv used by examples is UNADJUSTED prices — fine for the reference
  run's honesty framing, wrong for anything live. Live code must use adjusted
  data (Alpaca's own bars are fine).
- pandas 3.x / numpy 2.x are what the suite currently passes on.

## Style

Match the existing voice: plain prose docstrings that explain WHY (the physics
analogy, the failure mode being prevented), dataclasses for configs/results,
no heavy dependencies, every non-obvious numerical claim pinned by a test.
