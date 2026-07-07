import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run from repo root
"""
Paper-trading the Kalman pairs strategy through the broker bridge.

This replays real JPM/GS prices through a MockBroker, which fills orders with
slippage and commission and tracks cash and positions. It runs the exact same
loop that would talk to Alpaca, so it tests the plumbing end to end and prints a
simulated track record. Swap MockBroker for AlpacaPaperBroker (with paper keys)
and the same code trades paper in real time.

This is the honest path to "does it work": a live, zero-capital record, not
another in-sample backtest.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from statarb import MockBroker, run_pairs_session
from examples.real_data_djia import load_panel

wide = load_panel()
pair = wide[["JPM", "GS"]].copy()

broker = MockBroker(pair, cash=100_000.0, commission_bps=1.0, slippage_bps=2.0)
log, equity = run_pairs_session(broker, "JPM", "GS", notional=10_000.0,
                                entry_z=1.5, exit_z=0.0, burn_in=250,
                                delta=1e-6, R=1e-3)

eq = pd.Series(equity, index=pair.index[1:len(equity) + 1])
ret = eq.pct_change().dropna()
start_after_burn = eq.iloc[250:]
total_ret = start_after_burn.iloc[-1] / start_after_burn.iloc[0] - 1
ann_sharpe = np.sqrt(252) * ret.iloc[250:].mean() / ret.iloc[250:].std()
dd = (eq - eq.cummax())
max_dd_pct = (dd / eq.cummax()).min()

print("=" * 58)
print("Paper-trade replay: JPM/GS via MockBroker (Kalman pairs)")
print("=" * 58)
print(f"  bars traded         : {len(log)}")
print(f"  fills               : {len(broker.fills)}")
print(f"  starting equity     : $100,000")
print(f"  ending equity       : ${eq.iloc[-1]:,.0f}")
print(f"  return after burn-in: {total_ret:+.1%}")
print(f"  annualized Sharpe   : {ann_sharpe:.2f}")
print(f"  max drawdown        : {max_dd_pct:.1%}")
print("\n  This is a simulated fill log, not a live result. Point the same")
print("  runner at AlpacaPaperBroker with paper keys for a real-time record.")

# ---- figure ------------------------------------------------------------------
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
    "grid.alpha": .25, "axes.spines.top": False, "axes.spines.right": False})
INK = "#1b2a4a"; BL = "#2d6cdf"; GR = "#2c9e6b"
fig, ax = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True,
                       gridspec_kw={"height_ratios": [2, 1]})
ax[0].plot(eq.index, eq.values, color=BL, lw=1.4)
ax[0].axhline(100_000, color="#999", lw=.8)
ax[0].set_title("Simulated paper-trading equity, JPM/GS through the broker bridge",
                fontweight="bold", color=INK, loc="left", fontsize=10)
ax[0].set_ylabel("account equity ($)")

logi = log.copy()
logi.index = pair.index[logi["step"].values - 1]
ax[1].plot(logi.index, logi["z"], color=INK, lw=.6)
for lvl in (1.5, -1.5):
    ax[1].axhline(lvl, color=BL, ls=":", lw=1)
ax[1].axhline(0, color="#999", lw=.8)
ax[1].set_title("Kalman innovation z-score driving the orders",
                fontweight="bold", color=INK, loc="left", fontsize=10)
ax[1].set_xlabel("date"); ax[1].set_ylabel("z")
fig.tight_layout()
fig.savefig("figures/paper_trade_report.png", bbox_inches="tight", facecolor="white")
print("\n  saved figures/paper_trade_report.png")
