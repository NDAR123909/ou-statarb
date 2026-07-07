r"""
Pairs trading with a Kalman filter for a drifting hedge ratio.

The problem with a frozen beta
------------------------------
The OU engine fits one hedge ratio in-sample and freezes it. But the real
relationship moves over time: capital structures change and betas wander. Once
the frozen beta is even slightly off, the shared trend leaks back into the
"spread" and the edge quietly dies. This filter instead treats the hedge ratio
as a hidden state that drifts, and re-estimates it every day from past data.

The model (a dynamic linear regression)
---------------------------------------
Observation:   y_t = beta_t * x_t + alpha_t + eps_t,     eps_t ~ N(0, R)
Hidden state:  theta_t = [beta_t, alpha_t]^T
State drift:   theta_t = theta_{t-1} + w_t,              w_t ~ N(0, Q)

y_t and x_t are the log prices of the two legs. The state follows a random walk,
so the transition matrix is the identity: the hedge ratio is roughly constant
but free to wander. Q sets how fast it can wander and R is the measurement noise.
Their ratio is the filter's bandwidth, which is the one knob that really matters.

It is the same recursive Bayesian filter you would use to track a particle from
noisy position readings. theta_t is a Gaussian belief, and each new price updates
the posterior through predict, innovate, correct.

Where the trading signal comes from
-----------------------------------
The one-step-ahead forecast error, the innovation,

        e_t = y_t - H_t theta_{t-1},   H_t = [x_t, 1]

uses only past data by construction. Divide it by its own predicted standard
deviation sqrt(S_t) and you have an online z-score. A large positive value means
asset 1 is rich against the filter's fair value, so you short the spread. There
is no separate in-sample/out-of-sample split to worry about, because the filter
is walk-forward by nature.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- #
#  The Kalman filter (2-state dynamic regression)                             #
# --------------------------------------------------------------------------- #
@dataclass
class KalmanFit:
    beta: np.ndarray     # filtered hedge ratio over time
    alpha: np.ndarray    # filtered intercept over time
    innov: np.ndarray    # e_t, one-step forecast error (the raw signal)
    innov_std: np.ndarray  # sqrt(S_t), predicted std of the innovation
    zscore: np.ndarray   # e_t / sqrt(S_t)


def kalman_hedge(
    y: np.ndarray,
    x: np.ndarray,
    delta: float = 1e-4,
    R: float = 1e-3,
    beta0: float = 1.0,
    P0: float = 1.0,
) -> KalmanFit:
    """
    Run the dynamic-regression Kalman filter.

    delta : process-noise level. Q = delta/(1-delta) * I. Larger delta lets the
            hedge ratio adapt faster (responsive but noisier). This is the knob.
    R     : observation-noise variance.
    """
    n = len(y)
    Q = (delta / (1.0 - delta)) * np.eye(2)
    theta = np.array([beta0, 0.0])      # [beta, alpha]
    P = np.eye(2) * P0

    beta = np.empty(n); alpha = np.empty(n)
    innov = np.empty(n); innov_std = np.empty(n); z = np.empty(n)

    for t in range(n):
        H = np.array([x[t], 1.0])        # 1x2 observation row

        # --- predict (state transition is identity, so only covariance grows)
        P = P + Q

        # --- innovate: forecast error using prior state (past data only)
        y_hat = H @ theta
        e = y[t] - y_hat
        S = H @ P @ H + R                # scalar innovation variance

        # --- correct
        K = (P @ H) / S                  # Kalman gain (2,)
        theta = theta + K * e
        P = P - np.outer(K, H) @ P       # (I - K H) P

        beta[t], alpha[t] = theta[0], theta[1]
        innov[t] = e
        innov_std[t] = np.sqrt(S)
        z[t] = e / np.sqrt(S)

    return KalmanFit(beta, alpha, innov, innov_std, z)


@dataclass
class KalmanState:
    """
    Incremental single-bar Kalman update, for live trading where prices arrive
    one at a time. Holds the state between bars instead of refitting history.
    `kalman_hedge` is just this run in a loop.
    """
    theta: np.ndarray     # [beta, alpha]
    P: np.ndarray         # state covariance
    Q: np.ndarray         # process noise
    R: float              # observation noise

    def step(self, y: float, x: float) -> tuple[float, float, float]:
        """One predict/innovate/correct. Returns (innovation, innov_std, beta)."""
        H = np.array([x, 1.0])
        self.P = self.P + self.Q
        e = y - H @ self.theta
        S = H @ self.P @ H + self.R
        K = (self.P @ H) / S
        self.theta = self.theta + K * e
        self.P = self.P - np.outer(K, H) @ self.P
        return float(e), float(np.sqrt(S)), float(self.theta[0])


def kalman_state(delta: float = 1e-4, R: float = 1e-3,
                 beta0: float = 1.0, P0: float = 1.0) -> KalmanState:
    """Fresh filter state for incremental use."""
    Q = (delta / (1.0 - delta)) * np.eye(2)
    return KalmanState(np.array([beta0, 0.0]), np.eye(2) * P0, Q, R)


# --------------------------------------------------------------------------- #
#  Backtest using the Kalman signal                                           #
# --------------------------------------------------------------------------- #
@dataclass
class KalmanBacktestConfig:
    entry_z: float = 1.0      # Kalman z-scores are smaller; ~1 is the usual entry
    exit_z: float = 0.0       # exit when the innovation crosses back through 0
    cost_bps: float = 5.0     # per-side cost, both legs charged
    burn_in: int = 250        # let the filter converge before trading
    max_hold: int = 60


@dataclass
class KalmanBacktestResult:
    equity: pd.Series
    positions: pd.Series
    zscore: pd.Series
    beta: pd.Series
    daily_pnl: pd.Series
    n_trades: int
    sharpe: float
    max_drawdown: float
    total_return: float
    hit_rate: float


def kalman_backtest(
    y: pd.Series,
    x: pd.Series,
    fit: KalmanFit,
    cfg: KalmanBacktestConfig = KalmanBacktestConfig(),
    periods_per_year: int = 252,
) -> KalmanBacktestResult:
    """
    Trade the normalised innovation. PnL accounts for the TIME-VARYING hedge
    ratio: holding 1 unit of spread = long 1 of asset A, short beta_t of asset B,
    so the per-unit spread return is d(log A) - beta_t * d(log B). Costs are
    charged on both legs, including the small daily rebalancing of the B leg as
    beta drifts.
    """
    yv, xv = y.values, x.values
    z = fit.zscore
    n = len(yv)
    pos = np.zeros(n)
    hold = 0

    for t in range(1, n):
        if t < cfg.burn_in or not np.isfinite(z[t]):
            pos[t] = 0.0
            continue
        prev = pos[t - 1]
        if prev == 0:
            if z[t] > cfg.entry_z:
                pos[t] = -1.0; hold = 0
            elif z[t] < -cfg.entry_z:
                pos[t] = +1.0; hold = 0
            else:
                pos[t] = 0.0
        else:
            hold += 1
            crossed = (prev > 0 and z[t] >= -cfg.exit_z) or \
                      (prev < 0 and z[t] <= cfg.exit_z)
            flip_short = prev > 0 and z[t] > cfg.entry_z
            flip_long = prev < 0 and z[t] < -cfg.entry_z
            if hold >= cfg.max_hold or crossed:
                pos[t] = 0.0
            elif flip_short:
                pos[t] = -1.0; hold = 0
            elif flip_long:
                pos[t] = +1.0; hold = 0
            else:
                pos[t] = prev

    pos = pd.Series(pos, index=y.index)
    beta = pd.Series(fit.beta, index=y.index)

    # per-unit spread return using the hedge ratio you held (beta_{t-1})
    dy = pd.Series(yv, index=y.index).diff()
    dx = pd.Series(xv, index=y.index).diff()
    spread_ret = dy - beta.shift(1) * dx
    gross = pos.shift(1).fillna(0.0) * spread_ret.fillna(0.0)

    # two-leg turnover: asset A weight = pos, asset B weight = -pos*beta
    wA = pos
    wB = -(pos * beta)
    turnover = wA.diff().abs().fillna(wA.abs().iloc[0] if len(wA) else 0.0) \
        + wB.diff().abs().fillna(0.0)
    cost = turnover * (cfg.cost_bps / 1e4)
    net = gross - cost
    equity = net.cumsum()

    traded = net.iloc[cfg.burn_in:]
    sharpe = (np.sqrt(periods_per_year) * traded.mean() / traded.std(ddof=1)
              if traded.std(ddof=1) > 0 else 0.0)
    running_max = equity.cummax()
    max_dd = (equity - running_max).min()
    entries = ((pos != 0) & (pos.shift(1).fillna(0) == 0)).sum()
    in_mkt = net[pos.shift(1).fillna(0) != 0]
    hit = float((in_mkt > 0).mean()) if len(in_mkt) else 0.0

    return KalmanBacktestResult(
        equity=equity, positions=pos, zscore=pd.Series(z, index=y.index),
        beta=beta, daily_pnl=net, n_trades=int(entries), sharpe=float(sharpe),
        max_drawdown=float(max_dd), total_return=float(equity.iloc[-1]),
        hit_rate=hit,
    )
