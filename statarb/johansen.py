r"""
Basket stat-arb via the Johansen test.

Pairs are the n=2 case of a more general idea. With three or more related assets
there can be a linear combination of them that is stationary even though no two
of them are cointegrated on their own. The Johansen test finds those
combinations directly, and it hands you the weights as eigenvectors.

The picture
-----------
Stack the log prices of n assets into a vector and write a vector
error-correction model. The test asks how many independent stationary
combinations exist (the cointegration rank r) and returns, for each, the weight
vector that produces it. The eigenvalue attached to a vector measures how
strongly that combination reverts, so the leading eigenvector is the
fastest-reverting basket, which is the one worth trading.

Once you have the weights w, the basket spread is just w . log_prices, a single
stationary series. From there it is the same OU machinery as the pairs case: fit
theta and the half-life, build a z-score, trade the mean reversion.

A caveat the pairs case hides
-----------------------------
Johansen weights are estimated, and with n assets there are more of them to get
wrong. Trading costs also scale with sum(|w|), since every leg turns over, so a
basket with large opposing weights can look great on paper and bleed in
practice. The demo charges costs per unit of gross weight to keep that honest.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen

from .ou import fit_ou, OUParams


@dataclass
class JohansenResult:
    eigenvalues: np.ndarray      # reversion strength of each cointegrating vector
    eigenvectors: np.ndarray     # columns are the cointegrating vectors
    trace_stat: np.ndarray       # trace statistic for r <= 0, 1, ...
    trace_crit_95: np.ndarray    # matching 95% critical values
    rank: int                    # number of stationary combinations detected
    columns: list[str]           # asset names, in weight order

    def describe(self) -> str:
        lines = [f"  cointegration rank (95%): {self.rank}"]
        for i, (t, c) in enumerate(zip(self.trace_stat, self.trace_crit_95)):
            mark = "reject" if t > c else "keep"
            lines.append(f"    r<={i}: trace {t:7.2f} vs crit {c:6.2f}  -> {mark}")
        return "\n".join(lines)


def johansen_test(prices: pd.DataFrame, det_order: int = 0,
                  k_ar_diff: int = 1) -> JohansenResult:
    """
    Run the Johansen trace test on a panel of prices (one column per asset).

    Works on log prices internally. det_order=0 allows a nonzero mean in the
    cointegrating relation; k_ar_diff is the number of lagged differences.
    """
    logp = np.log(prices.values)
    res = coint_johansen(logp, det_order, k_ar_diff)
    trace, crit95 = res.lr1, res.cvt[:, 1]
    rank = 0
    for t, c in zip(trace, crit95):
        if t > c:
            rank += 1
        else:
            break
    return JohansenResult(
        eigenvalues=res.eig, eigenvectors=res.evec,
        trace_stat=trace, trace_crit_95=crit95, rank=rank,
        columns=list(prices.columns),
    )


def leading_weights(result: JohansenResult, normalize: str = "first") -> pd.Series:
    """
    The fastest-reverting cointegrating vector, as portfolio weights.

    normalize='first' scales so the first asset has weight 1 (easy to read as a
    hedge of the other legs against it); 'unit' scales to sum(|w|)=1.
    """
    w = result.eigenvectors[:, 0].astype(float)
    if normalize == "first":
        w = w / w[0]
    elif normalize == "unit":
        w = w / np.sum(np.abs(w))
    return pd.Series(w, index=result.columns)


def basket_spread(prices: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Form the stationary basket: w . log_prices."""
    logp = np.log(prices[weights.index])
    return logp.mul(weights, axis=1).sum(axis=1).rename("basket")


@dataclass
class BasketModel:
    weights: pd.Series
    ou: OUParams
    johansen: JohansenResult


def fit_basket(prices: pd.DataFrame, normalize: str = "first") -> BasketModel:
    """Test, pick the leading vector, build the spread, fit OU. One call."""
    jres = johansen_test(prices)
    w = leading_weights(jres, normalize)
    spread = basket_spread(prices, w)
    ou = fit_ou(spread.values)
    return BasketModel(weights=w, ou=ou, johansen=jres)
