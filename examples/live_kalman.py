import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run from repo root
"""
Run the Kalman pairs pipeline on real data.

Needs internet and `pip install yfinance`, so run it on your own machine. The
filter is walk-forward by construction (each day uses only past data), so there
is no in-sample/out-of-sample split. It just warms up over `burn_in` days and
then trades.

The knob to watch is `delta`. A small value (around 1e-6) lets beta drift slowly
and keeps the mean-reversion signal tradeable. A large value lets beta absorb
that signal and the edge disappears (see demo_kalman.py). Tune it per pair
instead of copying a number.
"""
from itertools import combinations

import numpy as np
import pandas as pd

from statarb import kalman_hedge, kalman_backtest, KalmanBacktestConfig

CANDIDATES = ["VLO", "MPC", "PSX", "XOM", "CVX", "KO", "PEP", "V", "MA"]
START, END = "2015-01-01", "2024-12-31"
DELTA, R = 1e-6, 1e-3


def load_prices(tickers, start, end):
    import yfinance as yf
    px = yf.download(tickers, start=start, end=end, auto_adjust=True,
                     progress=False)["Close"]
    return px.dropna(how="any")


def scan(prices, delta=DELTA, R=R):
    rows = []
    for t1, t2 in combinations(prices.columns, 2):
        y = np.log(prices[t1]); x = np.log(prices[t2])
        fit = kalman_hedge(y.values, x.values, delta=delta, R=R)
        res = kalman_backtest(y, x, fit,
                              KalmanBacktestConfig(entry_z=1.5, cost_bps=5.0))
        # half-life of the innovation as a sanity/strength check
        e = pd.Series(fit.innov)
        b = np.polyfit(e[:-1], e.diff().dropna(), 1)[0]
        hl = -np.log(2) / np.log(1 + b) if -1 < b < 0 else np.inf
        rows.append({
            "pair": f"{t1}/{t2}",
            "beta_end": round(float(fit.beta[-1]), 3),
            "innov_half_life": round(hl, 1) if np.isfinite(hl) else np.inf,
            "sharpe": round(res.sharpe, 2),
            "pnl": round(res.total_return, 3),
            "max_dd": round(res.max_drawdown, 3),
            "trades": res.n_trades,
        })
    return pd.DataFrame(rows).sort_values("sharpe", ascending=False)


if __name__ == "__main__":
    try:
        prices = load_prices(CANDIDATES, START, END)
    except ImportError:
        raise SystemExit("Install yfinance first:  pip install yfinance")
    print(f"loaded {prices.shape[1]} tickers, {len(prices)} days\n")
    table = scan(prices)
    print("Pairs ranked by Kalman walk-forward Sharpe (after costs):\n")
    print(table.to_string(index=False))
    print("\nSanity checks before trusting any row:")
    print(" - innov_half_life should be small & finite (real mean reversion)")
    print(" - re-run with delta in [1e-7, 1e-5]; a robust edge survives the sweep")
    print(" - paper-trade before risking capital. Backtest Sharpe >> live Sharpe.")
