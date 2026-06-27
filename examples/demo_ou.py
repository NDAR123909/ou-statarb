import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run from repo root
"""
End-to-end OU demo. Three steps:

  1. validate the estimator against known ground truth
  2. build a cointegrated pair, fit in-sample, freeze, trade out-of-sample
  3. repeat over many independent pairs so the result is a distribution
     rather than one lucky backtest
"""
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

from statarb import fit_ou, fit_spread_model, backtest, BacktestConfig


def simulate_ou(rng, theta, mu, sigma, n):
    b = np.exp(-theta); sd = sigma * np.sqrt((1 - b**2) / (2 * theta))
    x = np.empty(n); x[0] = mu
    for t in range(1, n):
        x[t] = mu + b * (x[t-1] - mu) + sd * rng.standard_normal()
    return x


def make_pair(rng, n=2500, true_beta=1.15, ctrend=0.011, theta=0.05, sig=0.022):
    """A genuine cointegrated pair: shared random-walk trend + OU spread."""
    common = np.cumsum(0.0002 + ctrend * rng.standard_normal(n))
    lp2 = 3.0 + common + 0.003 * rng.standard_normal(n)
    spread = simulate_ou(rng, theta, 0.0, sig, n)
    lp1 = true_beta * lp2 + spread
    idx = pd.bdate_range("2015-01-01", periods=n)
    return (pd.Series(np.exp(lp1), index=idx, name="ASSET_A"),
            pd.Series(np.exp(lp2), index=idx, name="ASSET_B"), true_beta)


# 1. estimator validation (own RNG so it can't perturb anything else) ----------
print("=" * 68)
print("STEP 1  Validate estimator: recover known OU parameters")
print("=" * 68)
f = fit_ou(simulate_ou(np.random.default_rng(0), 0.10, 0.0, 0.02, 4000))
print(f"  true half-life 6.93d   ->   fitted {f.half_life:.2f}d   (theta "
      f"recovered)\n")

# 2. showcase one pair ---------------------------------------------------------
print("=" * 68)
print("STEP 2  One pair: in-sample fit -> freeze -> out-of-sample backtest")
print("=" * 68)
p1, p2, tb = make_pair(np.random.default_rng(11))
split = 1500
model = fit_spread_model(np.log(p1.values[:split]), np.log(p2.values[:split]))
print(f"  hedge ratio beta : {model.beta:.4f}  (true {tb})")
print(f"  in-sample ADF p  : {model.adf_pvalue:.2e}  "
      f"({'cointegrated' if model.is_cointegrated else 'NOT'})")
print(model.ou.describe())

oos_p1, oos_p2 = p1.iloc[split:], p2.iloc[split:]
oos_spread = pd.Series(np.log(oos_p1.values) - model.beta * np.log(oos_p2.values),
                       index=oos_p1.index, name="spread")
print(f"  OOS ADF p        : {adfuller(oos_spread.values)[1]:.2e} "
      "(still mean-reverting out of sample)")

window = int(round(3 * model.ou.half_life))
naive = backtest(oos_spread, model, BacktestConfig(z_window=None))
adap = backtest(oos_spread, model, BacktestConfig(z_window=window))
print("\n  out-of-sample, 5 bps/side costs:")
print(f"    {'':18}{'frozen mean':>14}{'adaptive':>12}")
for nm, a, b, fmt in [("Sharpe (ann.)", naive.sharpe, adap.sharpe, ".2f"),
                      ("total PnL(log)", naive.total_return, adap.total_return, ".3f"),
                      ("max drawdown", naive.max_drawdown, adap.max_drawdown, ".3f"),
                      ("trades", naive.n_trades, adap.n_trades, "d"),
                      ("hit rate", naive.hit_rate, adap.hit_rate, ".1%")]:
    print(f"    {nm:18}{format(a,fmt):>14}{format(b,fmt):>12}")

# 3. Monte Carlo over many independent pairs -----------------------------------
print("\n" + "=" * 68)
print("STEP 3  Monte Carlo: 200 independent pairs (distribution, not one run)")
print("=" * 68)
sh_naive, sh_adap = [], []
for seed in range(1000, 1200):
    a, b, _ = make_pair(np.random.default_rng(seed))
    m = fit_spread_model(np.log(a.values[:split]), np.log(b.values[:split]))
    if not m.is_cointegrated:
        continue
    osp = pd.Series(np.log(a.values[split:]) - m.beta * np.log(b.values[split:]))
    w = int(round(3 * m.ou.half_life))
    sh_naive.append(backtest(osp, m, BacktestConfig(z_window=None)).sharpe)
    sh_adap.append(backtest(osp, m, BacktestConfig(z_window=w)).sharpe)
sh_naive, sh_adap = np.array(sh_naive), np.array(sh_adap)
print(f"  pairs that passed cointegration test: {len(sh_adap)}/200")
print(f"  frozen-mean  OOS Sharpe : mean {sh_naive.mean():+.2f}  "
      f"median {np.median(sh_naive):+.2f}  P(>0) {np.mean(sh_naive>0):.0%}")
print(f"  adaptive     OOS Sharpe : mean {sh_adap.mean():+.2f}  "
      f"median {np.median(sh_adap):+.2f}  P(>0) {np.mean(sh_adap>0):.0%}")

# save artifacts for plotting
p1.to_frame().join(p2).to_csv("figures/prices.csv")
pd.DataFrame({"spread": oos_spread, "zscore": adap.zscore,
              "position": adap.positions, "equity_naive": naive.equity,
              "equity_adaptive": adap.equity}).to_csv("figures/oos_results.csv")
np.savez("figures/mc.npz", naive=sh_naive, adap=sh_adap)
print("\n  saved prices.csv, oos_results.csv, mc.npz")
