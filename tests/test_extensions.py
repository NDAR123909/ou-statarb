"""Tests for the extensions: Johansen baskets, risk controls, broker bridge."""
import numpy as np
import pandas as pd

from statarb import (
    fit_basket, johansen_test, regime_ok, proportional_size,
    MockBroker, run_pairs_session, kalman_state, kalman_hedge,
)


def simulate_ou(rng, theta, sigma, n):
    b = np.exp(-theta); sd = sigma * np.sqrt((1 - b**2) / (2 * theta))
    x = np.empty(n); x[0] = 0.0
    for t in range(1, n):
        x[t] = b * x[t-1] + sd * rng.standard_normal()
    return x


# ---- Johansen ---------------------------------------------------------------
def test_johansen_finds_rank_one_basket():
    rng = np.random.default_rng(2); n = 1800
    r2 = np.cumsum(0.012 * rng.standard_normal(n))
    r3 = np.cumsum(0.012 * rng.standard_normal(n))
    lp1 = 0.5 * (3 + r2) + 0.3 * (3 + r3) + simulate_ou(rng, 0.05, 0.02, n)
    P = pd.DataFrame({"A": np.exp(lp1), "B": np.exp(3 + r2), "C": np.exp(3 + r3)})
    m = fit_basket(P)
    assert m.johansen.rank == 1
    assert np.isfinite(m.ou.half_life)        # the basket actually mean-reverts


def test_johansen_independent_walks_no_cointegration():
    rng = np.random.default_rng(3); n = 1500
    P = pd.DataFrame({c: np.exp(3 + np.cumsum(0.01 * rng.standard_normal(n)))
                      for c in "ABC"})
    assert johansen_test(P).rank == 0


# ---- risk controls ----------------------------------------------------------
def test_proportional_size_band_cap_and_sign():
    assert proportional_size(1.0, 2.0, 1.0, 3.0) == 0.0       # inside band -> flat
    assert proportional_size(5.0, 2.0, 1.0, 3.0) == -3.0      # rich, capped, short
    assert proportional_size(-5.0, 2.0, 1.0, 3.0) == 3.0      # cheap, capped, long


def test_regime_gate_distinguishes_ou_from_random_walk():
    rng = np.random.default_rng(4)
    ou = pd.Series(simulate_ou(rng, 0.06, 0.02, 1500))
    rw = pd.Series(np.cumsum(0.02 * rng.standard_normal(1500)))
    assert regime_ok(ou, 252).iloc[252:].mean() > 0.6        # mostly on for OU
    assert regime_ok(rw, 252).iloc[252:].mean() < 0.2        # mostly off for a walk


# ---- broker bridge ----------------------------------------------------------
def test_mock_broker_tracks_cash_and_positions():
    prices = pd.DataFrame({"X": [100.0, 101.0, 102.0]})
    b = MockBroker(prices, cash=10_000.0, commission_bps=0.0, slippage_bps=0.0)
    b.submit("X", 10)                       # buy 10 @ 100
    assert b.position("X") == 10
    assert b.equity() == 10_000.0           # no cost, no move yet
    b.advance()                             # price -> 101
    assert b.equity() == 10_010.0           # 10 shares * +1


def test_incremental_kalman_matches_batch():
    """KalmanState.step run in a loop must equal kalman_hedge on the array."""
    rng = np.random.default_rng(7); n = 400
    x = np.cumsum(0.01 * rng.standard_normal(n)) + 3
    y = 1.2 * x + simulate_ou(rng, 0.05, 0.02, n)
    batch = kalman_hedge(y, x, delta=1e-4, R=1e-3)
    st = kalman_state(delta=1e-4, R=1e-3)
    betas = [st.step(y[t], x[t])[2] for t in range(n)]
    assert np.allclose(betas, batch.beta, atol=1e-10)


def test_pairs_session_runs_end_to_end():
    rng = np.random.default_rng(8); n = 600
    x = np.cumsum(0.01 * rng.standard_normal(n)) + 3
    y = 1.1 * x + simulate_ou(rng, 0.05, 0.02, n)
    prices = pd.DataFrame({"A": np.exp(y), "B": np.exp(x)})
    broker = MockBroker(prices, cash=100_000.0)
    log, equity = run_pairs_session(broker, "A", "B", burn_in=200)
    assert len(equity) > 0
    assert len(log) > 0
    assert np.isfinite(broker.equity())
