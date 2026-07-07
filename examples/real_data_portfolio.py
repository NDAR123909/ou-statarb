import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
"""
The improved pipeline on real market data: sector-restricted candidates, FDR
selection, cost-aware optimal bands, dollar sizing with borrow, z-stops, and a
multi-pair walk-forward portfolio. Prints the numbers you would actually be
paid (or not).
"""
import numpy as np
import pandas as pd

from statarb import (
    PortfolioConfig, walk_forward_portfolio, SelectionConfig, CostModel,
)

DATA_URL = ("https://raw.githubusercontent.com/szrlee/Stock-Time-Series-Analysis/"
            "master/data/all_stocks_2006-01-01_to_2018-01-01.csv")

# Economically restricted candidates: ALL pairs WITHIN a sector, no pairs
# across sectors. The sector restriction is the multiple-testing correction
# that carries economic meaning; the FDR correction handles the count.
from itertools import combinations

SECTORS = {
    "financials": ["JPM", "GS", "AXP", "TRV"],
    "energy":     ["XOM", "CVX"],
    "staples":    ["KO", "PG", "WMT", "MCD"],
    "tech":       ["INTC", "CSCO", "MSFT", "IBM", "AAPL"],
    "industrial": ["MMM", "CAT", "BA", "UTX", "GE"],
    "pharma":     ["PFE", "MRK", "JNJ", "UNH"],
    "cons_disc":  ["DIS", "HD", "NKE"],
}
SECTOR_CANDIDATES = [p for group in SECTORS.values()
                     for p in combinations(group, 2)]


def load_panel(url=DATA_URL):
    df = pd.read_csv(url, parse_dates=["Date"])
    return df.pivot(index="Date", columns="Name", values="Close").dropna(how="any")


if __name__ == "__main__":
    wide = load_panel()
    tickers = set(wide.columns)
    cands = [(a, b) for a, b in SECTOR_CANDIDATES if a in tickers and b in tickers]
    print(f"panel: {wide.shape[0]} days x {wide.shape[1]} names, "
          f"{len(cands)} sector-restricted candidates\n")

    cfg = PortfolioConfig(
        train=504, test=126, max_pairs=8,
        nav=1_000_000, risk_per_pair_bps=10.0,
        use_optimal_bands=True, stop_z=3.5,
        selection=SelectionConfig(fdr_q=0.10),
        costs=CostModel(commission_bps=0.5, half_spread_bps=1.5,
                        borrow_bps_annual=50.0),
    )
    res = walk_forward_portfolio(wide, cands, cfg)

    print("=" * 62)
    print("WALK-FORWARD PORTFOLIO, REAL DATA, FULL COSTS  (all OOS)")
    print("=" * 62)
    print(f"  folds                  : {res.n_folds}")
    print(f"  OOS days traded        : {len(res.daily_pnl)}")
    print(f"  Sharpe (net)           : {res.sharpe:.2f}")
    print(f"  annual return on NAV   : {res.annual_return_pct:.2f}%")
    print(f"  max drawdown on NAV    : {res.max_drawdown_pct:.2f}%")
    print(f"  avg gross leverage     : {res.avg_gross_leverage:.2f}x")
    print(f"  gross PnL              : ${res.total_gross_pnl:,.0f}")
    print(f"  total costs paid       : ${res.total_costs:,.0f}")
    if res.total_gross_pnl > 0:
        print(f"  costs / gross PnL      : {res.total_costs / res.total_gross_pnl:.0%}")

    ph = res.pair_history
    if len(ph):
        traded = ph[ph["skipped"] == ""] if "skipped" in ph else ph
        print(f"\n  pair-folds traded      : {len(traded)}")
        if len(traded):
            by_pair = traded.groupby("pair")["pnl"].agg(["count", "sum"]) \
                            .sort_values("sum", ascending=False)
            print("\n  PnL by pair ($, all folds):")
            print(by_pair.to_string())
        skipped = ph[ph.get("skipped", "") == "costs exceed edge"]
        if len(skipped):
            print(f"\n  pair-folds skipped because costs exceeded the modeled "
                  f"edge: {len(skipped)}")
