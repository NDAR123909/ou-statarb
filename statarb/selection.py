r"""
Pair selection that survives its own search.

The single biggest reason pairs backtests fail live is the scan itself. Test 465
pairs at p<0.05 and ~23 false positives sail through by luck; rank by in-sample
Sharpe and you have hand-picked the luckiest noise. The old real_data_djia.py
demonstrated the trap; this module actually closes it.

Filters, in order:

  1. Benjamini-Hochberg FDR across ALL tested pairs. The question changes from
     "is this pair's p-value small?" to "given I ran N tests, which discoveries
     can I keep so that at most q of them are expected to be false?"
  2. Split-half stability: cointegration must hold on BOTH halves of the
     training window independently, and the two hedge ratios must agree. A real
     economic linkage is stable; a lucky sample is not.
  3. Half-life band: too fast (< ~3 days) is usually microstructure noise you
     cannot capture at daily bars; too slow (> ~40 days) barely trades and eats
     borrow while it waits.
  4. Mean-crossing count: the spread must actually cross its mean many times in
     the sample. Cheap, brutal, and catches "stationary" spreads that made one
     slow round trip.
  5. Hurst exponent < 0.5 on the spread (variance-ratio estimate): a direct
     check for anti-persistence, independent of the ADF machinery.

None of these creates an edge. Together they stop you from mistaking the search
process for one, which is the precondition for any real income.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd

from .ou import fit_spread_model, build_spread, fit_ou


# --------------------------------------------------------------------------- #
#  Small statistics helpers                                                   #
# --------------------------------------------------------------------------- #
def benjamini_hochberg(pvalues: np.ndarray, q: float = 0.10) -> np.ndarray:
    """Boolean mask of discoveries at FDR level q."""
    p = np.asarray(pvalues, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    thresh = q * (np.arange(1, n + 1) / n)
    below = ranked <= thresh
    keep = np.zeros(n, dtype=bool)
    if below.any():
        k = np.max(np.where(below)[0])
        keep[order[: k + 1]] = True
    return keep


def hurst_exponent(x: np.ndarray, max_lag: int = 60) -> float:
    """
    Variance-of-differences Hurst estimate. H < 0.5 => anti-persistent
    (mean-reverting), H ~ 0.5 => random walk, H > 0.5 => trending.
    """
    x = np.asarray(x, dtype=float)
    lags = np.arange(2, min(max_lag, len(x) // 4))
    tau = [np.std(x[lag:] - x[:-lag]) for lag in lags]
    tau = np.maximum(tau, 1e-12)
    h = np.polyfit(np.log(lags), np.log(tau), 1)[0]
    return float(h)


def mean_crossings(x: np.ndarray) -> int:
    """How many times the series crosses its own mean."""
    c = np.asarray(x) - np.mean(x)
    return int(np.sum(np.sign(c[1:]) != np.sign(c[:-1])))


# --------------------------------------------------------------------------- #
#  The selector                                                               #
# --------------------------------------------------------------------------- #
@dataclass
class PairCandidate:
    a: str
    b: str
    beta: float
    half_life: float
    adf_pvalue: float
    hurst: float
    crossings: int
    beta_first_half: float
    beta_second_half: float
    passed: bool
    reject_reason: str


@dataclass
class SelectionConfig:
    fdr_q: float = 0.10             # false-discovery rate across the whole scan
    min_half_life: float = 3.0      # days
    max_half_life: float = 50.0     # days
    min_crossings_per_year: float = 8.0
    max_hurst: float = 0.47
    max_beta_drift: float = 0.30    # |beta_h1 - beta_h2| / |beta| tolerance
    min_abs_beta: float = 0.25      # degenerate hedge ratios out
    max_abs_beta: float = 4.0
    split_adf_pmax: float = 0.15    # looser threshold for the HALF-window ADF:
    #                                 the primary gate is the full-window test
    #                                 (via FDR); half-window ADF has low power,
    #                                 so demanding p<0.05 there mostly rejects
    #                                 genuine pairs for lack of sample, not for
    #                                 lack of cointegration.
    periods_per_year: int = 252


def select_pairs(
    log_prices: pd.DataFrame,
    candidates: list[tuple[str, str]] | None = None,
    cfg: SelectionConfig = SelectionConfig(),
) -> pd.DataFrame:
    """
    Screen candidate pairs on a training panel of LOG prices.

    `candidates` defaults to all combinations, but you should pass an
    economically restricted list (same sector / same underlying exposure).
    Restricting the search space is itself a multiple-testing correction, and
    it is the one that carries economic information.

    Returns a DataFrame of all candidates with pass/fail and reasons; the
    tradeable set is rows with passed == True.
    """
    cols = list(log_prices.columns)
    cands = candidates or list(combinations(cols, 2))
    n_days = len(log_prices)
    half = n_days // 2

    rows: list[PairCandidate] = []
    for a, b in cands:
        la, lb = log_prices[a].values, log_prices[b].values
        m = fit_spread_model(la, lb)
        spread, _ = build_spread(la, lb)

        # split-half refits
        m1 = fit_spread_model(la[:half], lb[:half])
        m2 = fit_spread_model(la[half:], lb[half:])

        h = hurst_exponent(spread)
        cr = mean_crossings(spread)
        cr_per_year = cr / (n_days / cfg.periods_per_year)

        reason = ""
        ok = True
        if not (cfg.min_abs_beta <= abs(m.beta) <= cfg.max_abs_beta):
            ok, reason = False, "beta out of range"
        elif not np.isfinite(m.ou.half_life) or not (
                cfg.min_half_life <= m.ou.half_life <= cfg.max_half_life):
            ok, reason = False, "half-life out of band"
        elif cr_per_year < cfg.min_crossings_per_year:
            ok, reason = False, "too few mean crossings"
        elif h > cfg.max_hurst:
            ok, reason = False, "hurst too high (not anti-persistent)"
        elif not (m1.adf_pvalue < cfg.split_adf_pmax
                  and m2.adf_pvalue < cfg.split_adf_pmax
                  and np.isfinite(m1.ou.half_life)
                  and np.isfinite(m2.ou.half_life)):
            ok, reason = False, "fails split-half cointegration"
        elif abs(m1.beta - m2.beta) > cfg.max_beta_drift * max(abs(m.beta), 1e-9):
            ok, reason = False, "hedge ratio unstable across halves"

        rows.append(PairCandidate(
            a=a, b=b, beta=m.beta, half_life=m.ou.half_life,
            adf_pvalue=m.adf_pvalue, hurst=h, crossings=cr,
            beta_first_half=m1.beta, beta_second_half=m2.beta,
            passed=ok, reject_reason=reason,
        ))

    df = pd.DataFrame([r.__dict__ for r in rows])

    # FDR across the WHOLE scan (including pairs that failed other filters --
    # they were still tests you ran).
    if len(df):
        fdr_keep = benjamini_hochberg(df["adf_pvalue"].values, cfg.fdr_q)
        newly_rejected = df["passed"] & ~fdr_keep
        df.loc[newly_rejected, "reject_reason"] = "fails FDR correction"
        df["passed"] = df["passed"] & fdr_keep

    return df.sort_values(["passed", "adf_pvalue"], ascending=[False, True]) \
             .reset_index(drop=True)
