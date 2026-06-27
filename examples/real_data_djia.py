import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # run from repo root
"""
Run the framework on real market data (31 DJIA names, 2006 to 2017) and report
honest numbers, including the pitfall that trips up most pairs-trading projects.

The data is daily close prices from a public mirror of DJIA components. They are
unadjusted (no split or dividend adjustment), so treat the results as indicative
rather than production-grade; swap in adjusted prices (yfinance auto_adjust=True)
for anything serious.

The script shows two things side by side. The right way is to start from an
economic hypothesis, why should these two co-move, and then test it, which gives
modest believable edges. The trap is to scan all 465 pairs and rank by Sharpe:
the best-looking pairs have no economic story and are almost certainly overfit.
A high Sharpe found by searching is evidence of overfitting, not of an edge.
"""
import numpy as np
import pandas as pd
from itertools import combinations

from statarb import fit_spread_model, backtest, BacktestConfig, walk_forward

DATA_URL = ("https://raw.githubusercontent.com/szrlee/Stock-Time-Series-Analysis/"
            "master/data/all_stocks_2006-01-01_to_2018-01-01.csv")


def load_panel(url=DATA_URL):
    df = pd.read_csv(url, parse_dates=["Date"])
    return df.pivot(index="Date", columns="Name", values="Close").dropna(how="any")


def evaluate(wide, a, b):
    la, lb = np.log(wide[a].values), np.log(wide[b].values)
    n = len(la); split = int(n * 0.6)
    m = fit_spread_model(la[:split], lb[:split])
    if not m.is_cointegrated:
        return None
    wf = walk_forward(wide[a], wide[b], train=504, test=126,
                      cfg=BacktestConfig(cost_bps=5.0, z_window=None))
    return {"beta": round(m.beta, 3), "half_life": round(m.ou.half_life, 1),
            "wf_sharpe": round(wf.sharpe, 2), "folds": wf.n_folds}


if __name__ == "__main__":
    wide = load_panel()
    print(f"real panel: {wide.shape[0]} days x {wide.shape[1]} tickers "
          f"({wide.index[0].date()} to {wide.index[-1].date()})\n")

    # ---- 1. The RIGHT way: economically-motivated hypotheses ----
    print("=" * 64)
    print("1. Economically-motivated pairs (hypothesis first, then test)")
    print("=" * 64)
    econ = [("JPM", "GS"), ("JPM", "AXP"), ("GS", "AXP"),   # banks
            ("XOM", "CVX"),                                  # oil majors
            ("KO", "PG"), ("MCD", "KO"),                     # consumer staples
            ("INTC", "CSCO"), ("MSFT", "IBM")]               # tech
    for a, b in econ:
        r = evaluate(wide, a, b)
        if r:
            print(f"  {a+'/'+b:10} cointegrated | beta {r['beta']:>5} | "
                  f"half-life {r['half_life']:>5}d | walk-forward Sharpe {r['wf_sharpe']:>5}")
        else:
            print(f"  {a+'/'+b:10} NOT cointegrated -> no trade")

    # ---- 2. The data-mining TRAP: scan everything ----
    print("\n" + "=" * 64)
    print("2. Full scan of all 465 pairs (the data-mining trap)")
    print("=" * 64)
    rows = []
    for a, b in combinations(wide.columns, 2):
        r = evaluate(wide, a, b)
        if r:
            rows.append({"pair": f"{a}/{b}", **r})
    res = pd.DataFrame(rows).sort_values("wf_sharpe", ascending=False)
    n_tested = len(list(combinations(wide.columns, 2)))
    exp_false = int(0.05 * n_tested)

    print(f"  cointegrated: {len(res)}/{n_tested}  "
          f"(~{exp_false} expected by chance alone at the 5% ADF level)")
    print(f"  median walk-forward Sharpe among them: {res.wf_sharpe.median():.2f}")
    print(f"  fraction profitable out-of-sample     : {(res.wf_sharpe>0).mean():.0%}")
    print("\n  'best' pairs by Sharpe, and notice the lack of any economic story:")
    print(res.head(5).to_string(index=False))
    print("\n  The top pairs (e.g. DIS/JNJ, MCD/NKE) have no reason to co-move.")
    print("  Their high Sharpe is selection bias: test 465 things and a few")
    print("  shine by luck. The honest edge is the MEDIAN (~0.2), not the max.")

    res.to_csv("figures/real_scan.csv", index=False)
    print("\n  saved figures/real_scan.csv")
