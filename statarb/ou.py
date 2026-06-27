r"""
OU pairs-trading engine.

The model
---------
Ornstein and Uhlenbeck wrote this process down in 1930 for the velocity of a
Brownian particle stuck in a harmonic potential. It is a random walk with a
restoring force, a spring being kicked by noise:

        dX_t = theta * (mu - X_t) dt + sigma dW_t
               \________________/   \__________/
               restoring force        thermal noise
               (a spring, stiffness theta)

Here X_t is the spread between two cointegrated assets, and the restoring force
is the arbitrage that keeps related prices in line. When that force is missing,
i.e. the pair is not cointegrated, there is no spring and nothing to trade, so
the code checks for it first.

Why OLS is enough to fit it
---------------------------
The OU equation has an exact discrete solution, no Euler approximation needed.
Over a step dt it is just an AR(1):

        X_{t+1} = mu*(1 - b) + b * X_t + eps,   b = exp(-theta*dt)
        eps ~ N(0, sigma^2 * (1 - b^2) / (2*theta))

Regress X_{t+1} on X_t and read the parameters back off the slope, intercept,
and residual variance: theta = -ln(b)/dt, mu = a/(1-b), and sigma from the
residual. Two quantities I lean on later:

    half_life = ln(2)/theta          (the radioactive-decay formula)
    sigma_eq  = sigma/sqrt(2*theta)  (the spread's resting width)

How it avoids fooling itself
----------------------------
Parameters are fit on an in-sample window and then frozen for the out-of-sample
backtest, so there is no look-ahead. Cointegration is tested with an ADF check
before trading. Costs and slippage are charged on every position change. And the
reported metrics are the ones that can hurt: out-of-sample Sharpe, max drawdown,
turnover, and trade count.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller


# --------------------------------------------------------------------------- #
#  OU parameter estimation                                                    #
# --------------------------------------------------------------------------- #
@dataclass
class OUParams:
    """Fitted OU parameters and the physics quantities derived from them."""
    theta: float        # mean-reversion speed (1/time), i.e. spring stiffness
    mu: float           # long-run mean of the spread
    sigma: float        # instantaneous volatility of the driving noise
    half_life: float    # ln(2)/theta, time to decay halfway back to mu
    sigma_eq: float     # sigma/sqrt(2 theta), the stationary std (z-score scale)

    def describe(self) -> str:
        return (
            f"  theta (reversion speed) : {self.theta:.4f} /day\n"
            f"  mu (equilibrium)        : {self.mu:.5f}\n"
            f"  sigma (noise vol)       : {self.sigma:.5f}\n"
            f"  half-life               : {self.half_life:.2f} days\n"
            f"  sigma_eq (z scale)      : {self.sigma_eq:.5f}"
        )


def fit_ou(series: np.ndarray, dt: float = 1.0) -> OUParams:
    """
    Fit an OU process by exploiting its exact AR(1) representation.

    We regress X_{t+1} on X_t via OLS:  X_{t+1} = a + b X_t + eps.
    Then invert the mapping to recover (theta, mu, sigma).
    """
    x = np.asarray(series, dtype=float)
    x_t, x_next = x[:-1], x[1:]

    # OLS slope/intercept via closed form (cheap, transparent, no deps).
    b, a = np.polyfit(x_t, x_next, 1)        # slope b, intercept a
    resid = x_next - (a + b * x_t)
    var_eps = resid.var(ddof=2)

    # Guard: if b >= 1 the series is not mean-reverting (no spring).
    if b <= 0 or b >= 1:
        theta = np.nan
        mu = np.nan
        sigma = np.nan
        half_life = np.inf
        sigma_eq = np.nan
    else:
        theta = -np.log(b) / dt
        mu = a / (1.0 - b)
        sigma = np.sqrt(var_eps * 2.0 * theta / (1.0 - b ** 2))
        half_life = np.log(2.0) / theta
        sigma_eq = sigma / np.sqrt(2.0 * theta)

    return OUParams(theta, mu, sigma, half_life, sigma_eq)


# --------------------------------------------------------------------------- #
#  Cointegration / spread construction                                        #
# --------------------------------------------------------------------------- #
@dataclass
class SpreadModel:
    beta: float            # hedge ratio: spread = log P1 - beta * log P2
    ou: OUParams
    adf_stat: float        # ADF test statistic on the in-sample spread
    adf_pvalue: float      # p-value: small => spread is stationary => tradeable
    is_cointegrated: bool


def build_spread(log_p1: np.ndarray, log_p2: np.ndarray) -> tuple[np.ndarray, float]:
    """
    Estimate the hedge ratio beta by OLS of log_p1 on log_p2 (Engle-Granger
    step 1) and return the spread log_p1 - beta*log_p2.
    """
    beta, intercept = np.polyfit(log_p2, log_p1, 1)
    spread = log_p1 - beta * log_p2
    return spread, beta


def fit_spread_model(
    log_p1: np.ndarray,
    log_p2: np.ndarray,
    adf_threshold: float = 0.05,
) -> SpreadModel:
    """Build spread, run ADF stationarity test, fit OU. All IN-SAMPLE only."""
    spread, beta = build_spread(log_p1, log_p2)
    adf_stat, adf_p, *_ = adfuller(spread, autolag="AIC")
    ou = fit_ou(spread)
    return SpreadModel(
        beta=beta,
        ou=ou,
        adf_stat=adf_stat,
        adf_pvalue=adf_p,
        is_cointegrated=(adf_p < adf_threshold) and np.isfinite(ou.half_life),
    )


# --------------------------------------------------------------------------- #
#  Backtest                                                                    #
# --------------------------------------------------------------------------- #
@dataclass
class BacktestConfig:
    entry_z: float = 2.0       # enter when |z| exceeds this
    exit_z: float = 0.5        # exit when |z| falls back inside this
    cost_bps: float = 5.0      # per-side cost (commission+slippage), basis points
    max_hold: int = 30         # force-exit after this many days (stale trade guard)
    z_window: int | None = None  # trailing window for z-score; None = frozen IS mu.
    #                              Set to ~k*half_life to let the equilibrium drift
    #                              (handles hedge-ratio error & slow regime change).


@dataclass
class BacktestResult:
    equity: pd.Series          # cumulative PnL (log-spread units)
    positions: pd.Series       # -1 / 0 / +1
    zscore: pd.Series
    daily_pnl: pd.Series
    n_trades: int
    sharpe: float              # annualized, OOS
    max_drawdown: float
    total_return: float
    hit_rate: float
    avg_hold: float


def _zscore(spread: np.ndarray, mu: float, sigma_eq: float) -> np.ndarray:
    return (spread - mu) / sigma_eq


def backtest(
    spread: pd.Series,
    model: SpreadModel,
    cfg: BacktestConfig = BacktestConfig(),
    periods_per_year: int = 252,
) -> BacktestResult:
    """
    Event-driven backtest on a spread series using FROZEN in-sample parameters.

    Position convention (long the spread = +1):
        spread is below equilibrium (z < -entry) -> it's "cheap" -> go long (+1)
        spread is above equilibrium (z > +entry) -> it's "rich"  -> go short(-1)
    PnL of holding the spread for a day = position * change-in-spread.
    Costs are charged on |change in position| (turnover).
    """
    # z-score: either frozen in-sample equilibrium, or a trailing window that
    # lets the equilibrium drift. The window uses ONLY past data (no look-ahead).
    if cfg.z_window is None:
        z = _zscore(spread.values, model.ou.mu, model.ou.sigma_eq)
    else:
        roll_mu = spread.rolling(cfg.z_window).mean()
        roll_sd = spread.rolling(cfg.z_window).std(ddof=1)
        z = ((spread - roll_mu) / roll_sd).values
    n = len(spread)
    pos = np.zeros(n)
    hold = 0

    for t in range(1, n):
        if not np.isfinite(z[t]):          # warm-up period for the rolling window
            pos[t] = 0.0
            continue
        prev = pos[t - 1]
        if prev == 0:
            # flat -> look for entry. Spread rich (z high) => short (-1);
            # spread cheap (z low) => long (+1).
            if z[t] > cfg.entry_z:
                pos[t] = -1.0
                hold = 0
            elif z[t] < -cfg.entry_z:
                pos[t] = +1.0
                hold = 0
            else:
                pos[t] = 0.0
        else:
            hold += 1
            # NOTE: position sign is OPPOSITE the z sign (long when z<0).
            # Exit when the spread reverts into the mean band, or it blows
            # through to the opposite extreme (genuine flip), or it goes stale.
            reverted = abs(z[t]) < cfg.exit_z
            flip_to_short = prev > 0 and z[t] > cfg.entry_z   # was long, now rich
            flip_to_long = prev < 0 and z[t] < -cfg.entry_z   # was short, now cheap
            stale = hold >= cfg.max_hold
            if reverted or stale:
                pos[t] = 0.0
            elif flip_to_short:
                pos[t] = -1.0
                hold = 0
            elif flip_to_long:
                pos[t] = +1.0
                hold = 0
            else:
                pos[t] = prev

    pos = pd.Series(pos, index=spread.index)
    dspread = spread.diff().fillna(0.0)

    # PnL: yesterday's position earns today's spread change.
    gross_pnl = pos.shift(1).fillna(0.0) * dspread
    turnover = pos.diff().abs().fillna(abs(pos.iloc[0]))
    cost = turnover * (cfg.cost_bps / 1e4)
    net_pnl = gross_pnl - cost

    equity = net_pnl.cumsum()

    # Metrics
    daily = net_pnl
    sharpe = (
        np.sqrt(periods_per_year) * daily.mean() / daily.std(ddof=1)
        if daily.std(ddof=1) > 0 else 0.0
    )
    running_max = equity.cummax()
    drawdown = equity - running_max
    max_dd = drawdown.min()

    # Trade-level stats
    trade_changes = pos.diff().fillna(pos.iloc[0])
    entries = trade_changes[(pos != 0) & (pos.shift(1).fillna(0) == 0)]
    n_trades = int((entries != 0).sum())

    # hit rate: fraction of days-in-market that were profitable
    in_mkt = daily[pos.shift(1).fillna(0) != 0]
    hit_rate = float((in_mkt > 0).mean()) if len(in_mkt) else 0.0
    avg_hold = float((pos != 0).sum() / n_trades) if n_trades else 0.0

    return BacktestResult(
        equity=equity,
        positions=pos,
        zscore=pd.Series(z, index=spread.index),
        daily_pnl=daily,
        n_trades=n_trades,
        sharpe=float(sharpe),
        max_drawdown=float(max_dd),
        total_return=float(equity.iloc[-1]),
        hit_rate=hit_rate,
        avg_hold=avg_hold,
    )
