"""
statarb: Ornstein-Uhlenbeck statistical arbitrage with a Kalman-filtered hedge
ratio.

A research framework for cointegration-based pairs trading. The goal is to be
defensible rather than to print money: it checks for the economic mechanism
(cointegration), validates its estimators against known truth, keeps in-sample
and out-of-sample strictly apart, charges realistic costs, and reports
distributions instead of one lucky backtest.
"""

from .ou import (
    OUParams, SpreadModel, BacktestConfig, BacktestResult,
    fit_ou, build_spread, fit_spread_model, backtest,
)
from .kalman import (
    KalmanFit, KalmanBacktestConfig, KalmanBacktestResult, KalmanState,
    kalman_hedge, kalman_backtest, kalman_state,
)
from .walkforward import WalkForwardResult, walk_forward
from .johansen import (
    JohansenResult, BasketModel,
    johansen_test, leading_weights, basket_spread, fit_basket,
)
from .risk import (
    proportional_size, rolling_half_life, regime_ok, backtest_sized_gated,
)
from .broker import (
    Fill, Broker, MockBroker, AlpacaPaperBroker, run_pairs_session,
)
from .thresholds import OptimalBands, optimal_bands, ou_expected_passage_time
from .costs import CostModel, apply_costs
from .selection import (
    SelectionConfig, select_pairs, benjamini_hochberg, hurst_exponent,
    mean_crossings,
)
from .portfolio import PortfolioConfig, PortfolioResult, walk_forward_portfolio

__all__ = [
    "OUParams", "SpreadModel", "BacktestConfig", "BacktestResult",
    "fit_ou", "build_spread", "fit_spread_model", "backtest",
    "KalmanFit", "KalmanBacktestConfig", "KalmanBacktestResult", "KalmanState",
    "kalman_hedge", "kalman_backtest", "kalman_state",
    "WalkForwardResult", "walk_forward",
    "JohansenResult", "BasketModel",
    "johansen_test", "leading_weights", "basket_spread", "fit_basket",
    "proportional_size", "rolling_half_life", "regime_ok", "backtest_sized_gated",
    "Fill", "Broker", "MockBroker", "AlpacaPaperBroker", "run_pairs_session",
    "OptimalBands", "optimal_bands", "ou_expected_passage_time",
    "CostModel", "apply_costs",
    "SelectionConfig", "select_pairs", "benjamini_hochberg", "hurst_exponent",
    "mean_crossings",
    "PortfolioConfig", "PortfolioResult", "walk_forward_portfolio",
]

__version__ = "0.2.0"
