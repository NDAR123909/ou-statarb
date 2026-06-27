r"""
Position sizing and a regime gate.

Two pieces of risk control that the plain backtest skips.

Sizing. The base strategy bets a fixed +/-1 whenever the z-score clears the entry
band. That throws away information: a spread three standard deviations from fair
value is a better bet than one barely past the band. Proportional sizing scales
the position with the z-score (bet more when the edge is larger), capped so a
single outlier can't take the whole book. It is a poor man's Kelly: size with the
edge, but bound it.

Regime gate. Mean reversion has one catastrophic failure, the relationship
breaking for good (a merger, a spinoff, a business that quietly became something
else). The naive backtest keeps leaning into a spread that is now a runaway
random walk. The gate watches two live signals, the rolling half-life and the
rolling ADF p-value, and forces the book flat when the spring weakens: when the
half-life blows up (theta heading to zero) or the spread stops looking
stationary. It trades less and sleeps better.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from .ou import SpreadModel, BacktestResult


def proportional_size(z: float, entry: float, scale: float, max_size: float) -> float:
    """
    Map a z-score to a signed position. Zero inside the entry band, then linear
    in |z| beyond it, capped at max_size. Sign is opposite z (short when rich).
    """
    if abs(z) < entry:
        return 0.0
    raw = (abs(z) - entry) / scale
    return -np.sign(z) * min(raw, max_size)


def rolling_half_life(spread: pd.Series, window: int) -> pd.Series:
    """Trailing OU half-life from an AR(1) slope on each window. inf if no reversion."""
    def hl(x):
        x = np.asarray(x)
        b = np.polyfit(x[:-1], x[1:], 1)[0]
        return np.log(2) / -np.log(b) if 0 < b < 1 else np.inf
    return spread.rolling(window).apply(hl, raw=True)


def rolling_adf_pvalue(spread: pd.Series, window: int, step: int = 5) -> pd.Series:
    """Trailing ADF p-value, computed every `step` days and forward-filled (ADF is slow)."""
    p = pd.Series(np.nan, index=spread.index)
    for i in range(window, len(spread), step):
        seg = spread.iloc[i - window:i].values
        try:
            p.iloc[i] = adfuller(seg, autolag="AIC")[1]
        except Exception:
            p.iloc[i] = 1.0
    return p.ffill()


def regime_ok(spread: pd.Series, window: int = 252, max_half_life: float = 60.0,
              adf_pmax: float = 0.10) -> pd.Series:
    """
    Boolean series: True when mean reversion still looks alive. Trade only then.
    Requires a finite, short-enough rolling half-life and a stationary-enough
    rolling ADF p-value.
    """
    hl = rolling_half_life(spread, window)
    p = rolling_adf_pvalue(spread, window)
    ok = (hl < max_half_life) & (p < adf_pmax)
    return ok.fillna(False)


def backtest_sized_gated(
    spread: pd.Series,
    model: SpreadModel,
    entry: float = 2.0,
    exit: float = 0.5,
    scale: float = 1.0,
    max_size: float = 3.0,
    cost_bps: float = 5.0,
    z_window: int = 40,
    use_gate: bool = True,
    gate_window: int = 252,
    max_half_life: float = 60.0,
    adf_pmax: float = 0.10,
    periods_per_year: int = 252,
) -> BacktestResult:
    """
    Backtest with proportional sizing and an optional regime gate.

    The z-score uses a trailing window. Position is the proportional size unless
    the gate says the regime is dead, in which case the book goes flat. Costs are
    charged on the change in (continuous) position.
    """
    roll_mu = spread.rolling(z_window).mean()
    roll_sd = spread.rolling(z_window).std(ddof=1)
    z = (spread - roll_mu) / roll_sd

    gate = regime_ok(spread, gate_window, max_half_life, adf_pmax) if use_gate \
        else pd.Series(True, index=spread.index)

    n = len(spread)
    pos = np.zeros(n)
    zv = z.values
    gv = gate.values
    for t in range(1, n):
        if not np.isfinite(zv[t]) or not gv[t]:
            pos[t] = 0.0
            continue
        target = proportional_size(zv[t], entry, scale, max_size)
        prev = pos[t - 1]
        if prev == 0.0:
            pos[t] = target
        elif abs(zv[t]) < exit:
            pos[t] = 0.0
        elif np.sign(target) == np.sign(prev) or target == 0.0:
            pos[t] = target if target != 0.0 else prev
        else:
            pos[t] = target  # flipped sides

    pos = pd.Series(pos, index=spread.index)
    dspread = spread.diff().fillna(0.0)
    gross = pos.shift(1).fillna(0.0) * dspread
    cost = pos.diff().abs().fillna(pos.abs().iloc[0]) * (cost_bps / 1e4)
    net = gross - cost
    equity = net.cumsum()

    sharpe = (np.sqrt(periods_per_year) * net.mean() / net.std(ddof=1)
              if net.std(ddof=1) > 0 else 0.0)
    max_dd = (equity - equity.cummax()).min()
    entries = int(((pos != 0) & (pos.shift(1).fillna(0) == 0)).sum())
    in_mkt = net[pos.shift(1).fillna(0) != 0]
    hit = float((in_mkt > 0).mean()) if len(in_mkt) else 0.0

    return BacktestResult(
        equity=equity, positions=pos, zscore=z, daily_pnl=net,
        n_trades=entries, sharpe=float(sharpe), max_drawdown=float(max_dd),
        total_return=float(equity.iloc[-1]), hit_rate=hit,
        avg_hold=float((pos != 0).sum() / entries) if entries else 0.0,
    )
