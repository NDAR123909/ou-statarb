"""Tests for OU estimation, cointegration detection, and the backtester."""
import numpy as np
import pandas as pd
import pytest

from statarb import (
    fit_ou, fit_spread_model, backtest, BacktestConfig, SpreadModel,
)


def simulate_ou(rng, theta, mu, sigma, n):
    b = np.exp(-theta); sd = sigma * np.sqrt((1 - b**2) / (2 * theta))
    x = np.empty(n); x[0] = mu
    for t in range(1, n):
        x[t] = mu + b * (x[t-1] - mu) + sd * rng.standard_normal()
    return x


def test_ou_recovers_known_parameters():
    """Estimator must back out parameters it was given (within tolerance)."""
    rng = np.random.default_rng(0)
    true_theta, true_mu, true_sigma = 0.10, 0.0, 0.02
    x = simulate_ou(rng, true_theta, true_mu, true_sigma, 6000)
    fit = fit_ou(x)
    assert fit.theta == pytest.approx(true_theta, rel=0.15)
    assert fit.half_life == pytest.approx(np.log(2) / true_theta, rel=0.15)
    assert fit.sigma == pytest.approx(true_sigma, rel=0.15)


def test_cointegration_detected_for_real_pair():
    """A genuinely cointegrated pair should pass the ADF test."""
    rng = np.random.default_rng(1)
    common = np.cumsum(0.01 * rng.standard_normal(1500))
    lp2 = 3.0 + common
    lp1 = 1.2 * lp2 + simulate_ou(rng, 0.05, 0.0, 0.02, 1500)
    model = fit_spread_model(lp1, lp2)
    assert model.is_cointegrated
    assert model.beta == pytest.approx(1.2, abs=0.15)


def test_independent_random_walks_not_cointegrated():
    """Two unrelated random walks must NOT be flagged cointegrated."""
    rng = np.random.default_rng(2)
    lp1 = np.cumsum(0.01 * rng.standard_normal(1500))
    lp2 = np.cumsum(0.01 * rng.standard_normal(1500))
    model = fit_spread_model(lp1, lp2)
    assert not model.is_cointegrated


def test_backtest_profitable_on_pure_ou_before_costs():
    """
    Regression test for a real bug we hit: a correct mean-reversion rule MUST
    be profitable on a pure OU process with zero costs. If this fails, the
    position/flip logic is broken.
    """
    rng = np.random.default_rng(3)
    s = pd.Series(simulate_ou(rng, 0.05, 0.0, 0.022, 5000))
    p = fit_ou(s.values)
    model = SpreadModel(beta=1.0, ou=p, adf_stat=0.0, adf_pvalue=0.0,
                        is_cointegrated=True)
    res = backtest(s, model, BacktestConfig(cost_bps=0.0, z_window=None))
    assert res.sharpe > 0.5
    assert res.total_return > 0


def test_costs_reduce_pnl():
    """Adding costs must never increase PnL."""
    rng = np.random.default_rng(4)
    s = pd.Series(simulate_ou(rng, 0.05, 0.0, 0.022, 4000))
    p = fit_ou(s.values)
    m = SpreadModel(beta=1.0, ou=p, adf_stat=0.0, adf_pvalue=0.0,
                    is_cointegrated=True)
    free = backtest(s, m, BacktestConfig(cost_bps=0.0)).total_return
    costly = backtest(s, m, BacktestConfig(cost_bps=10.0)).total_return
    assert costly <= free
