import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run from repo root
"""
Run the OU pipeline on real data.

Needs internet and `pip install yfinance`, so run it on your own machine. It
downloads daily closes for a list of tickers, scans every pair, keeps the ones
that pass the cointegration test in-sample, fits the OU model and freezes it,
then backtests out-of-sample with costs and ranks the survivors by Sharpe.

The best candidates are economically related names (same sector, or close
substitutes), because that is where a real mean-reverting spring should exist:

    refiners      : VLO, MPC, PSX
    majors        : XOM, CVX
    gold miners   : GLD, GDX, NEM, GOLD
    payments      : V, MA
    cola          : KO, PEP
    semis vs etf  : NVDA, AMD, SMH
"""
from itertools import combinations

import numpy as np
import pandas as pd

from statarb import fit_spread_model, backtest, BacktestConfig

CANDIDATES = ["VLO", "MPC", "PSX", "XOM", "CVX", "KO", "PEP", "V", "MA"]
START, END = "2015-01-01", "2024-12-31"
IS_FRACTION = 0.6
COST_BPS = 5.0


def load_prices(tickers, start, end):
    import yfinance as yf
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True,
                      progress=False)["Close"]
    return raw.dropna(how="any")


def scan(prices):
    n = len(prices)
    split = int(n * IS_FRACTION)
    rows = []
    for t1, t2 in combinations(prices.columns, 2):
        lp1, lp2 = np.log(prices[t1].values), np.log(prices[t2].values)
        model = fit_spread_model(lp1[:split], lp2[:split])
        if not model.is_cointegrated:
            continue
        oos_spread = pd.Series(
            lp1[split:] - model.beta * lp2[split:], index=prices.index[split:])
        window = int(round(3 * model.ou.half_life))
        res = backtest(oos_spread, model,
                       BacktestConfig(cost_bps=COST_BPS, z_window=window))
        rows.append({
            "pair": f"{t1}/{t2}", "beta": round(model.beta, 3),
            "half_life": round(model.ou.half_life, 1),
            "adf_p": float(f"{model.adf_pvalue:.1e}"),
            "oos_sharpe": round(res.sharpe, 2),
            "oos_pnl": round(res.total_return, 3),
            "max_dd": round(res.max_drawdown, 3),
            "trades": res.n_trades,
        })
    return pd.DataFrame(rows).sort_values("oos_sharpe", ascending=False)


if __name__ == "__main__":
    try:
        prices = load_prices(CANDIDATES, START, END)
    except ImportError:
        raise SystemExit("Install yfinance first:  pip install yfinance")
    print(f"loaded {prices.shape[1]} tickers, {len(prices)} days\n")
    table = scan(prices)
    if table.empty:
        print("No cointegrated pairs found -> no spring -> nothing to trade.")
    else:
        print("Cointegrated pairs, ranked by OUT-OF-SAMPLE Sharpe:\n")
        print(table.to_string(index=False))
        print("\nReminder: in-sample cointegration does NOT guarantee it holds "
              "live. Paper-trade survivors before risking capital.")
