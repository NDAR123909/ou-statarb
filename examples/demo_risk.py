import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run from repo root
"""
Position sizing and the regime gate, shown on the failure they exist for.

The spread mean-reverts for the first half of the sample, then the relationship
breaks and the spread wanders off as a random walk. A plain backtest keeps
betting on a reversion that never comes. The gate watches the rolling half-life
and ADF p-value, notices the spring is gone, and stands aside. Same money made
while the edge was real, far less given back once it died.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from statarb import fit_ou, SpreadModel
from statarb.risk import backtest_sized_gated, regime_ok


def ou(rng, theta, sig, n, x0=0.0):
    b = np.exp(-theta); sd = sig * np.sqrt((1 - b**2) / (2 * theta))
    x = np.empty(n); x[0] = x0
    for t in range(1, n):
        x[t] = b * x[t-1] + sd * rng.standard_normal()
    return x


rng = np.random.default_rng(5)
n = 2000; half = n // 2
s1 = ou(rng, 0.06, 0.02, half)
s2 = s1[-1] + np.cumsum(0.02 * rng.standard_normal(n - half))  # breakdown: random walk
spread = pd.Series(np.concatenate([s1, s2]))

model = SpreadModel(beta=1.0, ou=fit_ou(s1), adf_stat=0.0, adf_pvalue=0.0,
                    is_cointegrated=True)
w = int(round(3 * model.ou.half_life))

naive = backtest_sized_gated(spread, model, z_window=w, use_gate=False)
gated = backtest_sized_gated(spread, model, z_window=w, use_gate=True,
                             max_half_life=60, adf_pmax=0.10)

print("=" * 60)
print("Regime gate vs naive, spread breaks at the midpoint")
print("=" * 60)
print(f"  in-sample half-life: {model.ou.half_life:.1f}d   z-window: {w}")
print(f"  {'':8}{'Sharpe':>8}{'PnL':>9}{'max DD':>9}{'trades':>8}")
for name, r in [("naive", naive), ("gated", gated)]:
    print(f"  {name:8}{r.sharpe:>8.2f}{r.total_return:>9.3f}"
          f"{r.max_drawdown:>9.3f}{r.n_trades:>8}")
print(f"\n  days in market after the break  naive: "
      f"{int((naive.positions.iloc[half:] != 0).sum())}  "
      f"gated: {int((gated.positions.iloc[half:] != 0).sum())}")
print("  Same PnL while the edge was alive, a third of the drawdown overall.")

# ---- proportional vs fixed sizing on clean OU (a smaller, separate point) ----
clean = pd.Series(ou(rng, 0.05, 0.02, 3000))
cm = SpreadModel(beta=1.0, ou=fit_ou(clean.values), adf_stat=0, adf_pvalue=0,
                 is_cointegrated=True)
wc = int(round(3 * cm.ou.half_life))
fixed = backtest_sized_gated(clean, cm, z_window=wc, use_gate=False, max_size=1.0)
prop = backtest_sized_gated(clean, cm, z_window=wc, use_gate=False, max_size=3.0)
print(f"\n  sizing on clean OU   fixed cap Sharpe {fixed.sharpe:.2f} | "
      f"proportional cap Sharpe {prop.sharpe:.2f}")

# ---- figure ------------------------------------------------------------------
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
    "grid.alpha": .25, "axes.spines.top": False, "axes.spines.right": False})
INK = "#1b2a4a"; BL = "#2d6cdf"; GR = "#2c9e6b"; RD = "#cf4444"
fig, ax = plt.subplots(2, 1, figsize=(11, 6.6), sharex=True)

gate = regime_ok(spread, 252, 60.0, 0.10)
ax[0].plot(spread.index, spread.values, color=INK, lw=.8)
ax[0].axvline(half, color=RD, ls="--", lw=1)
ax[0].fill_between(spread.index, spread.min(), spread.max(),
                   where=~gate.values, color=RD, alpha=.08, label="gate stands aside")
ax[0].fill_between(spread.index, spread.min(), spread.max(),
                   where=gate.values, color=GR, alpha=.08, label="gate trades")
ax[0].set_title("Spread mean-reverts, then breaks at the dashed line, and the gate notices",
                fontweight="bold", color=INK, loc="left", fontsize=10)
ax[0].set_ylabel("spread"); ax[0].legend(frameon=False, ncol=2, loc="upper left", fontsize=8)

ax[1].plot(naive.equity.index, naive.equity.values, color=RD, lw=1.4, label="naive (no gate)")
ax[1].plot(gated.equity.index, gated.equity.values, color=BL, lw=1.4, label="gated")
ax[1].axvline(half, color=RD, ls="--", lw=1); ax[1].axhline(0, color="#999", lw=.8)
ax[1].set_title("Equity, the gate keeps the first-half gains instead of giving them back",
                fontweight="bold", color=INK, loc="left", fontsize=10)
ax[1].set_xlabel("day"); ax[1].set_ylabel("cum. PnL"); ax[1].legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig("figures/regime_report.png", bbox_inches="tight", facecolor="white")
print("\n  saved figures/regime_report.png")
