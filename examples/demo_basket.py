import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run from repo root
"""
Basket stat-arb with the Johansen test.

First a controlled check: build three assets where exactly one stationary
combination exists, and confirm the test finds the rank and the weights. Then
the honest part on real data, where baskets turn out to be a double-edged tool.
They can capture structure that pairs miss, but scanning every triple is far
more prone to overfitting than scanning pairs (more combinations, more weights),
and the weights often demand heavy gross leverage that quietly eats returns.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from itertools import combinations

from statarb import (fit_basket, basket_spread, backtest, BacktestConfig,
                     SpreadModel)
from examples.real_data_djia import load_panel


def ou(rng, theta, sig, n):
    b = np.exp(-theta); sd = sig * np.sqrt((1 - b**2) / (2 * theta))
    x = np.empty(n); x[0] = 0.0
    for t in range(1, n):
        x[t] = b * x[t-1] + sd * rng.standard_normal()
    return x


def basket_backtest(prices, model, split):
    """OOS backtest of a basket with frozen weights; costs scale with gross weight."""
    spread_oos = basket_spread(prices.iloc[split:], model.weights)
    sm = SpreadModel(beta=np.nan, ou=model.ou, adf_stat=0.0, adf_pvalue=0.0,
                     is_cointegrated=True)
    win = int(round(3 * model.ou.half_life)) if np.isfinite(model.ou.half_life) else 40
    gross = float(model.weights.abs().sum())
    return backtest(spread_oos, sm,
                    BacktestConfig(z_window=win, cost_bps=5.0 * gross)), gross


# ---- 1. synthetic validation -------------------------------------------------
print("=" * 64)
print("1. Synthetic check: one true stationary combination of three assets")
print("=" * 64)
rng = np.random.default_rng(2); n = 1800
r2 = np.cumsum(0.012 * rng.standard_normal(n)); r3 = np.cumsum(0.012 * rng.standard_normal(n))
lp2 = 3.0 + r2; lp3 = 3.0 + r3
lp1 = 0.5 * lp2 + 0.3 * lp3 + ou(rng, 0.05, 0.02, n)
P = pd.DataFrame({"A": np.exp(lp1), "B": np.exp(lp2), "C": np.exp(lp3)})
m = fit_basket(P)
print(m.johansen.describe())
print(f"  weights (A=1): {{'A':1.0, 'B':{m.weights['B']:.2f}, 'C':{m.weights['C']:.2f}}}"
      f"   true B=-0.5, C=-0.3")
print(f"  basket half-life: {m.ou.half_life:.1f} days  (the combination mean-reverts)")

# ---- 2. real DJIA: every triple, honestly -----------------------------------
print("\n" + "=" * 64)
print("2. Real DJIA: scan triples (and watch the overfitting)")
print("=" * 64)
wide = load_panel(); split = int(len(wide) * 0.6)
cands = ["JPM", "GS", "AXP", "MMM", "UTX", "CAT", "BA", "HD", "MCD", "KO",
         "PG", "XOM", "CVX", "IBM", "MSFT", "INTC", "CSCO", "DIS", "JNJ", "PFE"]
rows = []
for trio in combinations(cands, 3):
    sub = wide[list(trio)].iloc[:split]
    try:
        bm = fit_basket(sub)
    except Exception:
        continue
    if bm.johansen.rank < 1 or not np.isfinite(bm.ou.half_life):
        continue
    if not (5 < bm.ou.half_life < 90):
        continue
    res, gross = basket_backtest(wide[list(trio)], bm, split)
    rows.append({"triple": "/".join(trio), "sharpe": round(res.sharpe, 2),
                 "half_life": round(bm.ou.half_life, 1), "gross_weight": round(gross, 1)})
scan = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
n_trip = len(list(combinations(cands, 3)))
print(f"  triples tested: {n_trip} | cointegrated & sane half-life: {len(scan)}")
print(f"  median OOS Sharpe: {scan.sharpe.median():.2f} | "
      f"profitable: {(scan.sharpe > 0).mean():.0%}")
print(f"  median gross weight: {scan.gross_weight.median():.1f} "
      "(every unit is leverage and turnover)")
print("\n  top 5 by Sharpe (note the gross weight, and the lack of a clean story):")
print(scan.head(5).to_string(index=False))
print("\n  Scanning 1140 triples manufactures winners. The high-Sharpe baskets")
print("  lean on big offsetting weights, which means leverage and cost the")
print("  backtest barely feels. Pairs were already easy to overfit; baskets")
print("  are worse. Use Johansen when you have a prior, not as a search engine.")

scan.to_csv("figures/basket_scan.csv", index=False)

# ---- figure ------------------------------------------------------------------
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
    "grid.alpha": .25, "axes.spines.top": False, "axes.spines.right": False})
INK = "#1b2a4a"; BL = "#2d6cdf"; GR = "#2c9e6b"; RD = "#cf4444"
fig, ax = plt.subplots(1, 2, figsize=(12, 4.4))

sp = basket_spread(P, m.weights)
ax[0].plot(sp.index, sp.values, color=INK, lw=.8)
ax[0].axhline(sp.mean(), color=GR, lw=1.2, ls="--")
ax[0].set_title("Synthetic basket spread w·log(prices) is stationary",
                fontweight="bold", color=INK, loc="left", fontsize=10)
ax[0].set_xlabel("day"); ax[0].set_ylabel("basket spread")

ax[1].scatter(scan.gross_weight, scan.sharpe, s=18, color=BL, alpha=.6, edgecolor="white")
ax[1].axhline(0, color="#999", lw=.8)
ax[1].set_xlim(0, 15)   # a handful of near-collinear baskets have absurd weights
ax[1].set_title("Real triples, the best Sharpes ride on the biggest gross weight",
                fontweight="bold", color=INK, loc="left", fontsize=10)
ax[1].set_xlabel("gross weight  sum|w|  (clipped at 15, some run into the thousands)")
ax[1].set_ylabel("OOS Sharpe")
fig.tight_layout()
fig.savefig("figures/basket_report.png", bbox_inches="tight", facecolor="white")
print("\n  saved figures/basket_report.png")
