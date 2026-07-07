import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run from repo root
"""
Roll the OU strategy forward across about ten years, re-fitting every six
months, and measure how fast the edge fades after each refit.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from statarb import walk_forward, BacktestConfig


def ou(rng, theta, mu, sig, n):
    b = np.exp(-theta); sd = sig * np.sqrt((1 - b**2) / (2 * theta))
    x = np.empty(n); x[0] = mu
    for t in range(1, n):
        x[t] = mu + b * (x[t-1] - mu) + sd * rng.standard_normal()
    return x


def make_pair(rng, n=3000, true_beta=1.15):
    common = np.cumsum(0.0002 + 0.011 * rng.standard_normal(n))
    lp2 = 3.0 + common + 0.003 * rng.standard_normal(n)
    spread = ou(rng, 0.05, 0.0, 0.022, n)
    lp1 = true_beta * lp2 + spread
    idx = pd.bdate_range("2013-01-01", periods=n)
    return pd.Series(np.exp(lp1), index=idx), pd.Series(np.exp(lp2), index=idx)


a, b = make_pair(np.random.default_rng(21))
wf = walk_forward(a, b, train=504, test=126,
                  cfg=BacktestConfig(cost_bps=5.0, z_window=None))

print(f"walk-forward folds        : {wf.n_folds}")
print(f"overall walk-forward Sharpe: {wf.sharpe:.2f}")
print("\nper-fold (each is genuine out-of-sample):")
print(wf.fold_table.to_string(index=False))

# edge half-life: how many days until cumulative edge reaches half its final value
final = wf.decay["cumulative_edge"].iloc[-1]
half_day = int(np.searchsorted(wf.decay["cumulative_edge"].values, final / 2)) \
    if final > 0 else -1
print(f"\nedge accrues steadily; half of the per-fold edge is captured by "
      f"day {half_day} of each 126-day test window"
      if half_day > 0 else "\n(edge not positive on this sample)")

# plots
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), dpi=130)
for s in ("top", "right"):
    ax[0].spines[s].set_visible(False); ax[1].spines[s].set_visible(False)

ax[0].plot(wf.equity.index, wf.equity.values, color="#2d6cdf", lw=1.4)
ax[0].axhline(0, color="#999", lw=.8); ax[0].grid(alpha=.25)
ax[0].set_title("Stitched walk-forward equity (re-fit every 6 months)",
                fontweight="bold", color="#1b2a4a", loc="left")
ax[0].set_ylabel("cumulative log-PnL")

ax[1].plot(wf.decay["days_since_refit"], wf.decay["mean_pnl"].rolling(5).mean(),
           color="#2c9e6b", lw=1.4)
ax[1].axhline(0, color="#999", lw=.8); ax[1].grid(alpha=.25)
ax[1].set_title("Edge decay, mean daily PnL vs days since last refit",
                fontweight="bold", color="#1b2a4a", loc="left")
ax[1].set_xlabel("days since refit"); ax[1].set_ylabel("mean daily PnL (5d smooth)")

fig.tight_layout()
fig.savefig("figures/walkforward_report.png", bbox_inches="tight", facecolor="white")
print("\nsaved figures/walkforward_report.png")
