r"""
The portfolio layer: where a pairs strategy becomes (or fails to become) viable.

Three things separate a live-able strategy from the single-pair research code:

  Diversification. One pair is a coin with a slight bias; its Sharpe is low and
  its worst month can erase a year. Fifteen pairs with modest correlation is the
  same edge multiplied by sqrt(breadth). Every real statistical-arbitrage book
  is a portfolio; this module makes the framework one too.

  Dollars, not log-units. The research backtests report PnL in "spread units",
  which cannot be compared to costs, borrow, or a salary. Here every position is
  sized in dollars against a NAV, targeting a fixed daily risk contribution per
  pair, with a portfolio-level gross-leverage cap.

  A way out. Mean reversion's catastrophic mode is the relationship breaking
  while the model doubles down. Every position here carries a z-stop
  (structural-break exit), a max-hold, and a one-sided re-entry block after a
  stop so the book cannot instantly re-enter the same losing trade.

Mechanics
---------
walk_forward_portfolio() rolls a (train -> test) window. Each refit it:
  1. runs the disciplined selector (FDR + stability filters) on the train panel,
  2. keeps the top pairs, fits frozen betas and OU params,
  3. computes cost-aware optimal bands per pair (or uses fixed ones),
  4. trades the test window with dollar sizing:
        gross_per_unit = (risk_bps/1e4 * NAV) / daily_spread_vol
     so each pair contributes roughly the same daily risk,
  5. charges commission + half-spread on every dollar of turnover on BOTH legs
     (including the initial entry), and borrow on the short leg every day.

Everything reported is out-of-sample by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .ou import fit_spread_model, SpreadModel
from .costs import CostModel
from .selection import SelectionConfig, select_pairs
from .thresholds import optimal_bands


# --------------------------------------------------------------------------- #
#  Config / results                                                           #
# --------------------------------------------------------------------------- #
@dataclass
class PortfolioConfig:
    train: int = 504                  # ~2y training window
    test: int = 63                    # ~3m per fold, then refit
    max_pairs: int = 12
    nav: float = 1_000_000.0
    risk_per_pair_bps: float = 10.0   # target daily PnL vol per pair, bps of NAV
    max_gross_leverage: float = 4.0   # portfolio gross / NAV cap
    use_optimal_bands: bool = True
    entry_z: float = 2.0              # fallback bands if not using optimal
    exit_z: float = 0.5
    stop_z: float = 3.5               # structural-break stop
    max_hold_mult: float = 3.0        # max holding = mult * half-life
    z_window_mult: float = 3.0        # z lookback = mult * half-life
    selection: SelectionConfig = field(default_factory=SelectionConfig)
    costs: CostModel = field(default_factory=CostModel)
    periods_per_year: int = 252


@dataclass
class PortfolioResult:
    daily_pnl: pd.Series          # dollars, portfolio level, OOS only
    returns: pd.Series            # daily_pnl / NAV
    equity: pd.Series             # cumulative dollars
    sharpe: float
    annual_return_pct: float      # on NAV
    max_drawdown_pct: float       # on NAV
    avg_gross_leverage: float
    total_costs: float            # dollars paid in commissions/spread/borrow
    total_gross_pnl: float
    pair_history: pd.DataFrame    # which pairs traded in which fold
    n_folds: int


# --------------------------------------------------------------------------- #
#  Single-pair dollar engine (frozen params, one test window)                 #
# --------------------------------------------------------------------------- #
def _trade_pair_dollars(
    la: np.ndarray, lb: np.ndarray, index: pd.Index,
    model: SpreadModel, entry: float, exit_: float, stop: float,
    z_window: int, max_hold: int, risk_dollars: float,
    cm: CostModel,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, int]:
    """
    Trade one pair over a window whose first `z_window` bars are warm-up seed
    (training tail). Returns (net_pnl$, gross_exposure$, turnover$, cost$,
    n_trades) for the NON-seed portion.

    Position sizing: a unit of spread = $g long A, $g*beta short B (signs flip
    when short the spread). g is fixed at entry so the position is not churned
    by vol drift; risk is re-targeted at the next entry.
    """
    spread = la - model.beta * lb
    n = len(spread)
    beta = model.beta

    # rolling z (past-only: window ends at t)
    s = pd.Series(spread)
    mu = s.rolling(z_window).mean().values
    sd = s.rolling(z_window).std(ddof=1).values
    # realized daily spread vol for sizing (same trailing window)
    dvol = s.diff().rolling(z_window).std(ddof=1).values

    pos = np.zeros(n)                 # in units of spread
    g = np.zeros(n)                   # dollars per unit, fixed while in a trade
    blocked = 0                       # +1: longs blocked, -1: shorts blocked (post-stop)
    hold = 0
    n_trades = 0

    for t in range(1, n):
        if not np.isfinite(sd[t]) or sd[t] <= 0 or not np.isfinite(dvol[t]):
            continue
        z = (spread[t] - mu[t]) / sd[t]
        prev = pos[t - 1]
        g[t] = g[t - 1]

        # clear the re-entry block once the spread has healed back inside the band
        if blocked == +1 and z > -entry:
            blocked = 0
        if blocked == -1 and z < entry:
            blocked = 0

        if prev == 0.0:
            if z > entry and blocked != -1:
                pos[t] = -1.0
            elif z < -entry and blocked != +1:
                pos[t] = +1.0
            if pos[t] != 0.0:
                hold = 0
                n_trades += 1
                unit_vol = dvol[t] if dvol[t] > 0 else np.nan
                g[t] = (risk_dollars / unit_vol) if np.isfinite(unit_vol) else 0.0
        else:
            hold += 1
            stopped = (prev > 0 and z < -stop) or (prev < 0 and z > stop)
            reverted = abs(z) < exit_
            stale = hold >= max_hold
            if stopped:
                pos[t] = 0.0
                blocked = +1 if prev > 0 else -1   # don't re-enter the losing side
            elif reverted or stale:
                pos[t] = 0.0
            else:
                pos[t] = prev

    # --- dollars ---
    pos_s = pd.Series(pos, index=index)
    g_s = pd.Series(g, index=index)
    dspread = pd.Series(spread, index=index).diff().fillna(0.0)

    # PnL: yesterday's units * yesterday's $/unit * today's spread change
    gross_pnl = pos_s.shift(1).fillna(0.0) * g_s.shift(1).fillna(0.0) * dspread

    # leg notionals
    wA = pos_s * g_s
    wB = -pos_s * g_s * beta
    gross_exp = wA.abs() + wB.abs()
    turnover = wA.diff().abs().fillna(wA.abs()) + wB.diff().abs().fillna(wB.abs())
    short_notional = (-wA).clip(lower=0.0) + (-wB).clip(lower=0.0)

    trade_cost = cm.trading_cost(turnover)
    borrow = cm.borrow_cost(short_notional.shift(1).fillna(0.0))
    cost = trade_cost + borrow
    net = gross_pnl - cost

    sl = slice(z_window, None)        # drop the seed portion
    return (net.iloc[sl], gross_exp.iloc[sl], turnover.iloc[sl],
            cost.iloc[sl], n_trades)


# --------------------------------------------------------------------------- #
#  The walk-forward portfolio                                                 #
# --------------------------------------------------------------------------- #
def walk_forward_portfolio(
    prices: pd.DataFrame,
    candidates: list[tuple[str, str]] | None = None,
    cfg: PortfolioConfig = PortfolioConfig(),
) -> PortfolioResult:
    """
    Run the full pipeline on a price panel (index=dates, columns=tickers).

    `candidates` should be an economically restricted list of (a, b) tickers
    (same sector / same exposure). Passing None scans all pairs, which the FDR
    correction will punish appropriately -- expect few or no survivors, and
    treat that as information.
    """
    logp = np.log(prices)
    idx = prices.index
    n = len(prices)

    pnl_total = pd.Series(0.0, index=idx)
    gross_total = pd.Series(0.0, index=idx)
    cost_total = pd.Series(0.0, index=idx)
    traded_mask = pd.Series(False, index=idx)
    pair_rows = []

    start, fold = 0, 0
    while start + cfg.train + cfg.test <= n:
        tr = slice(start, start + cfg.train)
        te_lo, te_hi = start + cfg.train, start + cfg.train + cfg.test

        sel = select_pairs(logp.iloc[tr], candidates, cfg.selection)
        chosen = sel[sel.passed].head(cfg.max_pairs)

        for _, row in chosen.iterrows():
            a, b = row.a, row.b
            la_tr, lb_tr = logp[a].values[tr], logp[b].values[tr]
            model = fit_spread_model(la_tr, lb_tr)
            hl = model.ou.half_life
            z_win = int(np.clip(round(cfg.z_window_mult * hl), 15, cfg.train // 2))
            max_hold = int(np.clip(round(cfg.max_hold_mult * hl), 5, 120))

            # bands: cost-aware optimum, or fixed fallback
            if cfg.use_optimal_bands:
                # round-trip cost in spread units: 4 leg-trades at per_leg_bps
                # on gross (1+|beta|)/unit... expressed per unit of spread:
                rt_cost = 2.0 * (1.0 + abs(model.beta)) * cfg.costs.per_leg_bps / 1e4
                bands = optimal_bands(model.ou, rt_cost)
                if not bands.tradeable:
                    pair_rows.append({"fold": fold, "pair": f"{a}/{b}",
                                      "skipped": "costs exceed edge"})
                    continue
                entry, exit_ = bands.entry_z, bands.exit_z
            else:
                entry, exit_ = cfg.entry_z, cfg.exit_z

            # window = training tail seed + test slice
            seg = slice(te_lo - z_win, te_hi)
            la, lb = logp[a].values[seg], logp[b].values[seg]
            risk_dollars = cfg.nav * cfg.risk_per_pair_bps / 1e4

            net, gross_exp, turn, cost, ntr = _trade_pair_dollars(
                la, lb, idx[seg], model, entry, exit_, cfg.stop_z,
                z_win, max_hold, risk_dollars, cfg.costs)

            pnl_total.loc[net.index] += net
            gross_total.loc[gross_exp.index] += gross_exp
            cost_total.loc[cost.index] += cost
            traded_mask.loc[net.index] = True
            pair_rows.append({"fold": fold, "pair": f"{a}/{b}",
                              "beta": round(model.beta, 3),
                              "half_life": round(hl, 1),
                              "entry_z": round(entry, 2), "exit_z": round(exit_, 2),
                              "trades": ntr, "pnl": round(float(net.sum()), 0),
                              "skipped": ""})
        start += cfg.test
        fold += 1

    # ---- leverage cap: scale down days where gross exceeded the cap --------
    cap = cfg.max_gross_leverage * cfg.nav
    over = gross_total > cap
    if over.any():
        scale = (cap / gross_total[over]).clip(upper=1.0)
        pnl_total[over] = pnl_total[over] * scale
        gross_total[over] = cap

    oos = pnl_total[traded_mask]
    rets = oos / cfg.nav
    equity = oos.cumsum()
    sd = rets.std(ddof=1)
    sharpe = float(np.sqrt(cfg.periods_per_year) * rets.mean() / sd) if sd > 0 else 0.0
    ann_ret = float(rets.mean() * cfg.periods_per_year * 100.0)
    dd = float(((equity - equity.cummax()).min() / cfg.nav) * 100.0) if len(equity) else 0.0
    avg_lev = float((gross_total[traded_mask] / cfg.nav).mean()) if traded_mask.any() else 0.0

    return PortfolioResult(
        daily_pnl=oos, returns=rets, equity=equity, sharpe=sharpe,
        annual_return_pct=ann_ret, max_drawdown_pct=dd,
        avg_gross_leverage=avg_lev,
        total_costs=float(cost_total.sum()),
        total_gross_pnl=float(oos.sum() + cost_total[traded_mask].sum()),
        pair_history=pd.DataFrame(pair_rows), n_folds=fold,
    )
