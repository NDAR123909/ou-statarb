"""Tests for the Kalman dynamic-hedge-ratio filter."""
import numpy as np
import pandas as pd

from statarb import kalman_hedge, kalman_backtest, KalmanBacktestConfig


def simulate_ou(rng, theta, mu, sigma, n):
    b = np.exp(-theta); sd = sigma * np.sqrt((1 - b**2) / (2 * theta))
    x = np.empty(n); x[0] = mu
    for t in range(1, n):
        x[t] = mu + b * (x[t-1] - mu) + sd * rng.standard_normal()
    return x


def _drifting_pair(rng, n=2000, drift=0.5):
    xlp = 3.0 + np.cumsum(0.0003 + 0.012 * rng.standard_normal(n))
    beta_true = 1.0 + drift * (np.arange(n) / n)
    ylp = beta_true * xlp + simulate_ou(rng, 0.05, 0.0, 0.02, n)
    return ylp, xlp, beta_true


def test_kalman_tracks_drifting_beta_better_than_ols():
    """The whole point: on a drifting hedge ratio, the filter must beat a
    single static OLS estimate by a wide margin."""
    rng = np.random.default_rng(3)
    ylp, xlp, beta_true = _drifting_pair(rng)
    fit = kalman_hedge(ylp, xlp, delta=1e-6, R=1e-3)
    beta_ols = np.polyfit(xlp[:1200], ylp[:1200], 1)[0]

    burn = 300
    err_kalman = np.mean(np.abs(fit.beta[burn:] - beta_true[burn:]))
    err_ols = np.mean(np.abs(beta_ols - beta_true[burn:]))
    assert err_kalman < err_ols / 2          # at least 2x better tracking


def test_kalman_zscore_is_roughly_standardized():
    """A well-tuned innovation z-score should have std on the order of 1."""
    rng = np.random.default_rng(5)
    ylp, xlp, _ = _drifting_pair(rng)
    fit = kalman_hedge(ylp, xlp, delta=1e-6, R=1e-3)
    z = fit.zscore[300:]
    assert 0.3 < np.std(z) < 3.0


def test_large_delta_absorbs_signal():
    """Documented failure mode: too-large delta lets beta eat the signal, so
    the innovation rarely exceeds the entry band."""
    rng = np.random.default_rng(6)
    ylp, xlp, _ = _drifting_pair(rng)
    slow = kalman_hedge(ylp, xlp, delta=1e-6, R=1e-3)
    fast = kalman_hedge(ylp, xlp, delta=1e-2, R=1e-3)
    frac_slow = np.mean(np.abs(slow.zscore[300:]) > 1.0)
    frac_fast = np.mean(np.abs(fast.zscore[300:]) > 1.0)
    assert frac_fast < frac_slow            # fast filter has less tradeable signal
