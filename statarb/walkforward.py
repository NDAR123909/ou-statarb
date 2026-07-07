r"""
Walk-forward analysis: the honest way to test a strategy you have to re-fit.

A single in-sample/out-of-sample split tells you how the strategy did in one
particular future. Walk-forward rolls the whole procedure forward instead:

    |--- train ---|--- test ---|
            |--- train ---|--- test ---|
                    |--- train ---|--- test ---|
                            ...

At each step it re-estimates the hedge ratio and OU parameters on the training
window, then trades the next, unseen test window with those frozen parameters.
Stitch the test windows together and you get one continuous out-of-sample equity
curve made entirely of genuine forecasts.

It also answers the question that really separates a live edge from an overfit
backtest: how fast does the edge decay after each refit? If performance is strong
on day one and gone by day twenty, the parameters go stale fast and the "edge" is
mostly curve-fitting. A real edge fades slowly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .ou import fit_spread_model, backtest, BacktestConfig


@dataclass
class WalkForwardResult:
    stitched_pnl: pd.Series           # continuous OOS daily PnL (all folds)
    equity: pd.Series                 # cumulative
    fold_table: pd.DataFrame          # per-fold metrics
    decay: pd.DataFrame               # mean PnL & cumulative edge vs days-since-refit
    sharpe: float                     # overall walk-forward Sharpe
    n_folds: int


def walk_forward(
    price_a: pd.Series,
    price_b: pd.Series,
    train: int = 504,                 # ~2y training
    test: int = 126,                  # ~6m out-of-sample per fold
    step: int | None = None,          # roll distance; defaults to `test` (no overlap)
    cfg: BacktestConfig | None = None,
    periods_per_year: int = 252,
) -> WalkForwardResult:
    """
    Roll a (train -> test) window across the data, re-fitting each fold.

    The z-score uses a trailing window (set to ~3x the fold's OU half-life), and
    each test segment is seeded with the tail of its training window so the
    rolling statistics are warm from day one of the test period (no NaN gap, no
    look-ahead).
    """
    step = step or test
    la, lb = np.log(price_a.values), np.log(price_b.values)
    n = len(price_a)
    idx = price_a.index

    fold_rows = []
    pnl_pieces = []
    decay_accum: dict[int, list[float]] = {}

    start = 0
    fold = 0
    while start + train + test <= n:
        tr = slice(start, start + train)
        te = slice(start + train, start + train + test)

        model = fit_spread_model(la[tr], lb[tr])
        # window from the physics; fall back to 40 if half-life is degenerate
        win = int(round(3 * model.ou.half_life)) if np.isfinite(model.ou.half_life) else 40
        win = max(20, min(win, train // 2))

        if not model.is_cointegrated:
            fold_rows.append({"fold": fold, "start": str(idx[start].date()),
                              "cointegrated": False, "beta": np.nan,
                              "half_life": np.nan, "sharpe": np.nan,
                              "pnl": 0.0, "trades": 0})
            start += step; fold += 1
            continue

        c = cfg or BacktestConfig(z_window=win)
        if cfg is not None and cfg.z_window is None:
            c = BacktestConfig(entry_z=cfg.entry_z, exit_z=cfg.exit_z,
                               cost_bps=cfg.cost_bps, max_hold=cfg.max_hold,
                               z_window=win)

        # seed with `win` days of training tail so rolling z is warm immediately
        seed0 = start + train - win
        seg = slice(seed0, start + train + test)
        spread_seg = pd.Series(la[seg] - model.beta * lb[seg], index=idx[seg])
        res = backtest(spread_seg, model, c, periods_per_year)

        # keep only the genuine test portion (drop the seed days)
        test_pnl = res.daily_pnl.iloc[win:]
        pnl_pieces.append(test_pnl)

        # edge-decay bookkeeping: PnL by day-offset since refit
        for offset, val in enumerate(test_pnl.values):
            decay_accum.setdefault(offset, []).append(val)

        f_sharpe = (np.sqrt(periods_per_year) * test_pnl.mean() / test_pnl.std(ddof=1)
                    if test_pnl.std(ddof=1) > 0 else 0.0)
        fold_rows.append({"fold": fold, "start": str(idx[start].date()),
                          "cointegrated": True, "beta": round(model.beta, 3),
                          "half_life": round(model.ou.half_life, 1),
                          "sharpe": round(float(f_sharpe), 2),
                          "pnl": round(float(test_pnl.sum()), 3),
                          "trades": int(res.n_trades)})
        start += step; fold += 1

    stitched = pd.concat(pnl_pieces) if pnl_pieces else pd.Series(dtype=float)
    equity = stitched.cumsum()
    overall_sharpe = (np.sqrt(periods_per_year) * stitched.mean() / stitched.std(ddof=1)
                      if len(stitched) and stitched.std(ddof=1) > 0 else 0.0)

    decay = pd.DataFrame({
        "days_since_refit": sorted(decay_accum),
        "mean_pnl": [np.mean(decay_accum[k]) for k in sorted(decay_accum)],
        "n_obs": [len(decay_accum[k]) for k in sorted(decay_accum)],
    })
    decay["cumulative_edge"] = decay["mean_pnl"].cumsum()

    return WalkForwardResult(
        stitched_pnl=stitched, equity=equity,
        fold_table=pd.DataFrame(fold_rows), decay=decay,
        sharpe=float(overall_sharpe), n_folds=fold,
    )
