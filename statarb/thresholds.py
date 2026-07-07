r"""
Cost-aware optimal entry/exit bands for an OU spread.

The problem with 2.0 / 0.5
--------------------------
The classic entry_z=2.0, exit_z=0.5 rule is folklore, not optimization. For a
given reversion speed theta, noise sigma, and round-trip cost c, there is a band
choice that maximizes expected profit per unit of time, and it is usually NOT
(2.0, 0.5). Fast-reverting spreads want tighter bands (trade the small wiggles
often); slow spreads with high costs want wider bands (only take the big
dislocations). Getting this wrong is a silent tax on every trade.

The math (Bertram-style, but computed numerically)
--------------------------------------------------
Trade cycle on a zero-mean OU process dX = -theta X dt + sigma dW:

    enter long at  -a*sigma_eq,  exit at  -b*sigma_eq   (and mirrored short side)

Profit per completed round trip (in spread units) = (a - b) * sigma_eq - cost.
Expected cycle duration = E[tau(-a -> -b)] + E[tau(-b -> -a)], the expected
first-passage times of the OU process between those levels. Choose (a, b) to
maximize profit / duration.

Rather than trusting a remembered closed form, the passage times are computed
from the exact diffusion formula (scale/speed densities):

    E[tau(x0 -> b)] = 2 * int_{x0}^{b} s'(y) [ int_{-inf}^{y} m(z) dz ] dy
    s'(y) = exp(theta y^2 / sigma^2),   m(z) = exp(-theta z^2 / sigma^2)/sigma^2

for x0 < b (mirror for the other direction). A Monte Carlo test pins the
implementation to simulated truth.

What falls out of it
--------------------
optimal_bands() returns (entry_z, exit_z, expected_profit_rate). If the optimal
profit rate is <= 0 -- costs eat the whole reversion -- the pair is not worth
trading at all, which is itself the most valuable output: it converts "the
spread mean-reverts" into "the spread mean-reverts *enough to pay the toll*".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import integrate

from .ou import OUParams


# --------------------------------------------------------------------------- #
#  Expected first-passage time of an OU process (exact, numerical)            #
# --------------------------------------------------------------------------- #
def ou_expected_passage_time(x0: float, target: float, theta: float,
                             sigma: float) -> float:
    """
    E[time for dX = -theta X dt + sigma dW to first hit `target` from `x0`].

    Uses the scale/speed-density formula for one-dimensional diffusions.
    Symmetric in sign, so only the upward crossing is implemented and the
    downward case is mirrored.
    """
    if x0 == target:
        return 0.0
    if x0 > target:                       # mirror: OU is symmetric about 0
        return ou_expected_passage_time(-x0, -target, theta, sigma)

    k = theta / sigma ** 2

    def inner(y: float) -> float:
        # int_{-inf}^{y} exp(-k z^2) dz / sigma^2, via the error function
        from scipy.special import erf
        return (np.sqrt(np.pi / k) / 2.0) * (1.0 + erf(np.sqrt(k) * y)) / sigma ** 2

    def integrand(y: float) -> float:
        return np.exp(k * y ** 2) * inner(y)

    val, _ = integrate.quad(integrand, x0, target, limit=200)
    return 2.0 * val


# --------------------------------------------------------------------------- #
#  Optimal bands                                                              #
# --------------------------------------------------------------------------- #
@dataclass
class OptimalBands:
    entry_z: float           # enter when |z| exceeds this
    exit_z: float            # exit when |z| falls back inside this
    profit_rate: float       # expected spread-units of profit per day at optimum
    profit_per_trade: float  # net profit per round trip, spread units
    cycle_days: float        # expected days per round trip
    tradeable: bool          # False if costs eat the whole edge


def optimal_bands(ou: OUParams, roundtrip_cost: float,
                  a_grid: np.ndarray | None = None,
                  b_grid: np.ndarray | None = None) -> OptimalBands:
    """
    Grid-search the (entry, exit) bands that maximize expected profit per day.

    roundtrip_cost is the total cost of one open+close of the full spread
    position, in the same units as the spread (e.g. for a two-leg trade at
    cost_bps per side per leg: 4 legs * cost_bps/1e4 * gross-per-unit).

    Bands are expressed as multiples of sigma_eq (i.e. z-score units).
    """
    if not np.isfinite(ou.half_life) or ou.sigma_eq <= 0:
        return OptimalBands(np.nan, np.nan, -np.inf, -np.inf, np.inf, False)

    a_grid = a_grid if a_grid is not None else np.arange(0.4, 3.01, 0.2)
    b_grid = b_grid if b_grid is not None else np.arange(0.0, 1.51, 0.25)

    # Work on the standardized spread: theta as fitted, sigma_eq = 1
    # (rescale sigma so the stationary std is 1: sigma_std = sqrt(2*theta)).
    theta = ou.theta
    sigma_std = np.sqrt(2.0 * theta)
    cost_z = roundtrip_cost / ou.sigma_eq          # cost in z-units

    best = OptimalBands(2.0, 0.5, -np.inf, -np.inf, np.inf, False)
    # Cache passage times: cycle = tau(-a -> -b) + tau(-b -> -a)
    for a in a_grid:
        for b in b_grid:
            if b >= a - 0.1:
                continue
            profit = (a - b) - cost_z              # per round trip, z-units
            if profit <= 0:
                continue
            t_up = ou_expected_passage_time(-a, -b, theta, sigma_std)
            t_dn = ou_expected_passage_time(-b, -a, theta, sigma_std)
            cycle = t_up + t_dn
            if cycle <= 0:
                continue
            rate = profit / cycle
            if rate > best.profit_rate:
                best = OptimalBands(
                    entry_z=float(a), exit_z=float(b),
                    profit_rate=float(rate * ou.sigma_eq),
                    profit_per_trade=float(profit * ou.sigma_eq),
                    cycle_days=float(cycle),
                    tradeable=True,
                )
    return best
