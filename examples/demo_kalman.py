import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run from repo root
"""
Show the Kalman edge where it should exist (a drifting hedge ratio), and be
honest about where it doesn't (a constant one).
"""
import numpy as np, pandas as pd
from statarb import kalman_hedge, kalman_backtest, KalmanBacktestConfig
from statarb import fit_spread_model, backtest, BacktestConfig


def ou(rng, theta, mu, sig, n):
    b = np.exp(-theta); sd = sig*np.sqrt((1-b**2)/(2*theta))
    x = np.empty(n); x[0] = mu
    for t in range(1, n): x[t] = mu + b*(x[t-1]-mu) + sd*rng.standard_normal()
    return x


def make_pair(rng, n=2000, drift=0.5, ctrend=0.012, theta=0.05, sig=0.02):
    """drift = how much the TRUE hedge ratio moves over the whole sample."""
    xlp = 3.0 + np.cumsum(0.0003 + ctrend*rng.standard_normal(n))
    beta_true = 1.0 + drift*(np.arange(n)/n)
    spread = ou(rng, theta, 0.0, sig, n)
    ylp = beta_true*xlp + spread
    idx = pd.bdate_range("2016-01-01", periods=n)
    return pd.Series(ylp, index=idx), pd.Series(xlp, index=idx)


def run_static(y, x, split):
    m = fit_spread_model(y.values[:split], x.values[:split])
    sp = pd.Series(y.values - m.beta*x.values, index=y.index)
    w = int(round(3*m.ou.half_life)) if np.isfinite(m.ou.half_life) else 40
    r = backtest(sp.iloc[split:], m, BacktestConfig(z_window=w))
    return r.sharpe


def run_kalman(y, x):
    fit = kalman_hedge(y.values, x.values, delta=1e-6, R=1e-3)
    r = kalman_backtest(y, x, fit, KalmanBacktestConfig(entry_z=1.5))
    return r.sharpe, r, fit


print("="*64)
print("A. DRIFTING beta (true beta 1.0 -> 1.5): Kalman should win")
print("="*64)
sk, ss = [], []
for seed in range(300, 400):
    y, x = make_pair(np.random.default_rng(seed), drift=0.5)
    ss.append(run_static(y, x, int(len(y)*0.6)))
    sk.append(run_kalman(y, x)[0])
sk, ss = np.array(sk), np.array(ss)
print(f"  static-beta OOS Sharpe : mean {ss.mean():+.2f}  P(>0) {np.mean(ss>0):.0%}")
print(f"  Kalman      OOS Sharpe : mean {sk.mean():+.2f}  P(>0) {np.mean(sk>0):.0%}")

print("\n" + "="*64)
print("B. CONSTANT beta (drift=0): Kalman should NOT help (honesty check)")
print("="*64)
sk0, ss0 = [], []
for seed in range(300, 400):
    y, x = make_pair(np.random.default_rng(seed), drift=0.0)
    ss0.append(run_static(y, x, int(len(y)*0.6)))
    sk0.append(run_kalman(y, x)[0])
sk0, ss0 = np.array(sk0), np.array(ss0)
print(f"  static-beta OOS Sharpe : mean {ss0.mean():+.2f}  P(>0) {np.mean(ss0>0):.0%}")
print(f"  Kalman      OOS Sharpe : mean {sk0.mean():+.2f}  P(>0) {np.mean(sk0>0):.0%}")

# showcase one drifting pair for plotting
y, x = make_pair(np.random.default_rng(311), drift=0.5)
sh, res, fit = run_kalman(y, x)
print("\n" + "="*64)
print(f"Showcase drifting pair: Kalman OOS Sharpe {sh:.2f}, "
      f"trades {res.n_trades}, maxDD {res.max_drawdown:.3f}")
print("="*64)
beta_true = 1.0 + 0.5*(np.arange(len(y))/len(y))
pd.DataFrame({"beta_true": beta_true, "beta_kal": fit.beta,
              "zscore": fit.zscore, "position": res.positions,
              "equity": res.equity}, index=y.index).to_csv("figures/kal_results.csv")
np.savez("figures/kal_mc.npz", sk=sk, ss=ss, sk0=sk0, ss0=ss0)
print("saved kal_results.csv, kal_mc.npz")
