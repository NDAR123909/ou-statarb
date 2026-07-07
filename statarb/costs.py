r"""
A cost model that tries to hurt the way real markets hurt.

The old backtests charged a flat 5 bps per side on ONE leg of the spread. Real
pairs trades pay four ways:

  1. commission on both legs
  2. half the bid-ask spread on both legs, every time either leg trades --
     including the drip of hedge rebalancing as beta drifts
  3. borrow fee on the short leg, accrued every single day the position is on.
     For large liquid names this is ~25-50 bps/year ("general collateral");
     for crowded or small names it can be 1-10%/year and it is exactly the
     crowded names that show up at the top of naive pair scans
  4. market impact, which caps how much capital the strategy can absorb

This module prices 1-3 explicitly and treats 4 as a capacity constraint (a
square-root impact sanity check) rather than pretending to model it precisely.

The point is not precision, it is sign and order of magnitude: a daily-frequency
pairs strategy typically nets 10-40 bps per round trip before costs, and the
all-in toll below is commonly 8-20 bps. Any framework that hides that ratio is
lying to you about viability.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class CostModel:
    commission_bps: float = 0.5      # per leg, per trade (IBKR-tier for liquid US equities)
    half_spread_bps: float = 1.5     # effective half-spread paid per leg (liquid large caps)
    borrow_bps_annual: float = 50.0  # short-leg borrow fee, annualized (GC-ish)
    impact_coeff: float = 0.1        # sqrt-impact coefficient (fraction of daily vol)
    periods_per_year: int = 252

    @property
    def per_leg_bps(self) -> float:
        return self.commission_bps + self.half_spread_bps

    def trading_cost(self, dollar_turnover: float | pd.Series):
        """Cost of trading `dollar_turnover` of notional (both legs summed)."""
        return dollar_turnover * self.per_leg_bps / 1e4

    def borrow_cost(self, short_notional: float | pd.Series):
        """One day of borrow on the given short-side notional."""
        return short_notional * (self.borrow_bps_annual / 1e4) / self.periods_per_year

    def capacity_notional(self, adv_dollars: float, max_participation: float = 0.01,
                          max_impact_bps: float = 2.0, daily_vol_bps: float = 150.0
                          ) -> float:
        """
        A blunt capacity estimate: the largest per-trade notional such that
        (a) you stay under max_participation of average daily volume, and
        (b) square-root impact  impact_coeff * daily_vol * sqrt(participation)
            stays under max_impact_bps.
        Pairs strategies die by capacity long before they die by signal; this
        number is the honest ceiling on "income".
        """
        cap_a = max_participation * adv_dollars
        # impact_bps = impact_coeff * daily_vol_bps * sqrt(notional/adv)
        part = (max_impact_bps / (self.impact_coeff * daily_vol_bps)) ** 2
        cap_b = part * adv_dollars
        return float(min(cap_a, cap_b))


def apply_costs(
    gross_pnl: pd.Series,
    dollar_turnover: pd.Series,
    short_notional: pd.Series,
    cm: CostModel,
) -> pd.Series:
    """Net PnL = gross - trading costs - daily borrow accrual."""
    return gross_pnl - cm.trading_cost(dollar_turnover) - cm.borrow_cost(short_notional)
