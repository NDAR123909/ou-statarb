"""Tests for the viability layer: optimal bands, costs, selection, stops, portfolio."""
import numpy as np
import pandas as pd
import pytest

from statarb import (
    fit_ou, fit_spread_model, backtest, BacktestConfig, SpreadModel,
    ou_expected_passage_time, optimal_bands,
    CostModel, benjamini_hochberg, hurst_exponent, mean_crossings,
    SelectionConfig, select_pairs,
    PortfolioConfig, walk_forward_portfolio,
)


def simulate_ou(rng, theta, mu, sigma, n):
    b = np.exp(-theta); sd = sigma * np.sqrt((1 - b**2) / (2 * theta))
    x = np.empty(n); x[0] = mu
    for t in range(1, n):
        x[t] = mu + b * (x[t-1] - mu) + sd * rng.standard_normal()
    return x


# ---- optimal thresholds ------------------------------------------------------
def test_passage_time_matches_monte_carlo():
    """The analytic E[first passage] must agree with brute-force simulation."""
    theta, sigma = 0.10, np.sqrt(2 * 0.10)   # stationary std = 1
    analytic = ou_expected_passage_time(-2.0, -0.5, theta, sigma)

    rng = np.random.default_rng(7)
    dt = 0.05
    b = np.exp(-theta * dt)
    sd = sigma * np.sqrt((1 - b**2) / (2 * theta))
    times = []
    for _ in range(3000):
        x, t = -2.0, 0.0
        while x < -0.5 and t < 2000:
            x = b * x + sd * rng.standard_normal()
            t += dt
        times.append(t)
    mc = float(np.mean(times))
    assert analytic == pytest.approx(mc, rel=0.10)


def test_optimal_bands_widen_with_cost():
    """Higher costs must push the optimal entry band wider (or kill the trade)."""
    ou = fit_ou(simulate_ou(np.random.default_rng(0), 0.08, 0.0, 0.02, 6000))
    cheap = optimal_bands(ou, roundtrip_cost=0.0005)
    dear = optimal_bands(ou, roundtrip_cost=0.01)
    assert cheap.tradeable
    if dear.tradeable:
        assert dear.entry_z >= cheap.entry_z
        assert dear.profit_rate < cheap.profit_rate


def test_optimal_bands_untradeable_when_costs_dominate():
    """A weak spring with huge costs must be flagged untradeable, not traded."""
    ou = fit_ou(simulate_ou(np.random.default_rng(1), 0.01, 0.0, 0.005, 6000))
    res = optimal_bands(ou, roundtrip_cost=1.0)
    assert not res.tradeable


# ---- costs -------------------------------------------------------------------
def test_borrow_cost_accrues_daily():
    cm = CostModel(borrow_bps_annual=252.0)   # 1 bp/day for easy math
    assert cm.borrow_cost(1_000_000.0) == pytest.approx(100.0)


def test_capacity_shrinks_with_impact_budget():
    cm = CostModel()
    loose = cm.capacity_notional(50e6, max_impact_bps=5.0)
    tight = cm.capacity_notional(50e6, max_impact_bps=0.5)
    assert tight < loose


# ---- selection ---------------------------------------------------------------
def test_benjamini_hochberg_controls_discoveries():
    rng = np.random.default_rng(3)
    nulls = rng.uniform(0, 1, 95)             # true nulls
    signals = np.full(5, 1e-6)                # genuine effects
    keep = benjamini_hochberg(np.concatenate([nulls, signals]), q=0.10)
    assert keep[-5:].all()                    # real ones kept
    assert keep[:95].sum() <= 5               # few false discoveries slip through


def test_hurst_separates_reverting_from_trending():
    rng = np.random.default_rng(4)
    rev = simulate_ou(rng, 0.10, 0.0, 0.02, 3000)
    walk = np.cumsum(0.01 * rng.standard_normal(3000))
    assert hurst_exponent(rev) < 0.5 < hurst_exponent(walk) + 0.1
    assert mean_crossings(rev) > mean_crossings(walk)


def test_selector_keeps_real_pair_rejects_fake():
    """A genuine cointegrated pair passes; unrelated walks do not."""
    rng = np.random.default_rng(5)
    n = 2000
    common = np.cumsum(0.012 * rng.standard_normal(n))
    lp_b = 3.0 + common
    lp_a = 1.1 * lp_b + simulate_ou(rng, 0.08, 0.0, 0.015, n)
    lp_c = np.cumsum(0.012 * rng.standard_normal(n)) + 3.0
    lp_d = np.cumsum(0.012 * rng.standard_normal(n)) + 3.0
    panel = pd.DataFrame({"A": lp_a, "B": lp_b, "C": lp_c, "D": lp_d})
    res = select_pairs(panel)
    ab = res[(res.a == "A") & (res.b == "B")].iloc[0]
    assert ab.passed
    others = res[~((res.a == "A") & (res.b == "B"))]
    assert not others.passed.any()


# ---- structural-break stop ---------------------------------------------------
def test_stop_z_caps_loss_when_relationship_breaks():
    """
    Build a spread that mean-reverts, then breaks into a runaway trend.
    Without a stop the strategy rides the divergence; with a stop it bails and
    stays out. The stopped version must lose meaningfully less.
    """
    rng = np.random.default_rng(6)
    good = simulate_ou(rng, 0.08, 0.0, 0.02, 1500)
    # regime break: strong downward drift, no more spring
    broken = good[-1] + np.cumsum(-0.004 + 0.02 * rng.standard_normal(500))
    s = pd.Series(np.concatenate([good, broken]))
    p = fit_ou(good)
    m = SpreadModel(beta=1.0, ou=p, adf_stat=0.0, adf_pvalue=0.0,
                    is_cointegrated=True)
    # frozen in-sample z: the realistic failure case, where the model is
    # anchored to a stale equilibrium while the spread runs away. (A rolling
    # z-window partially self-heals by chasing the trend, which is exactly why
    # the naive version feels safe until it isn't.)
    base = BacktestConfig(cost_bps=0.0, z_window=None, max_hold=10_000)
    with_stop = BacktestConfig(cost_bps=0.0, z_window=None, max_hold=10_000,
                               stop_z=3.5)
    r_no = backtest(s, m, base)
    r_yes = backtest(s, m, with_stop)
    # loss during the break period must be smaller with the stop
    tail_no = r_no.daily_pnl.iloc[1500:].sum()
    tail_yes = r_yes.daily_pnl.iloc[1500:].sum()
    assert tail_yes > tail_no


def test_two_leg_costs_charge_more():
    rng = np.random.default_rng(8)
    s = pd.Series(simulate_ou(rng, 0.05, 0.0, 0.02, 3000))
    p = fit_ou(s.values)
    m = SpreadModel(beta=1.5, ou=p, adf_stat=0.0, adf_pvalue=0.0,
                    is_cointegrated=True)
    one = backtest(s, m, BacktestConfig(cost_bps=5.0)).total_return
    two = backtest(s, m, BacktestConfig(cost_bps=5.0,
                                        legs_cost_mult=2.5)).total_return
    assert two < one


# ---- portfolio ---------------------------------------------------------------
def _synthetic_panel(rng, n=1600, n_pairs=4):
    """Several genuinely cointegrated pairs plus decoys, as PRICES."""
    cols = {}
    cands = []
    for i in range(n_pairs):
        common = np.cumsum(0.012 * rng.standard_normal(n))
        lb = 3.5 + common
        la = 1.0 * lb + simulate_ou(rng, 0.07, 0.0, 0.015, n)
        cols[f"A{i}"] = np.exp(la); cols[f"B{i}"] = np.exp(lb)
        cands.append((f"A{i}", f"B{i}"))
    for i in range(3):   # decoys
        cols[f"X{i}"] = np.exp(3.5 + np.cumsum(0.012 * rng.standard_normal(n)))
        cands.append((f"X{i}", f"A{i}"))
    idx = pd.bdate_range("2015-01-01", periods=n)
    return pd.DataFrame(cols, index=idx), cands


def test_portfolio_end_to_end_profitable_on_synthetic():
    rng = np.random.default_rng(9)
    prices, cands = _synthetic_panel(rng)
    cfg = PortfolioConfig(train=504, test=126, max_pairs=6,
                          risk_per_pair_bps=10.0)
    res = walk_forward_portfolio(prices, cands, cfg)
    assert res.n_folds >= 3
    assert len(res.daily_pnl) > 200
    assert res.sharpe > 0.5            # real cointegration should survive costs
    assert res.total_costs > 0         # and costs were actually charged
    assert res.avg_gross_leverage <= cfg.max_gross_leverage + 1e-9


def test_portfolio_rejects_pure_noise_universe():
    """On unrelated random walks the selector should barely trade at all."""
    rng = np.random.default_rng(10)
    n = 1600
    cols = {f"N{i}": np.exp(3.5 + np.cumsum(0.012 * rng.standard_normal(n)))
            for i in range(8)}
    prices = pd.DataFrame(cols, index=pd.bdate_range("2015-01-01", periods=n))
    res = walk_forward_portfolio(prices, None, PortfolioConfig(train=504, test=126))
    traded = res.pair_history
    real_rows = traded[traded.get("skipped", "") == ""] if len(traded) else traded
    assert len(real_rows) <= 3         # a false discovery or two at most
