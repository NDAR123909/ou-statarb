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
]

__version__ = "0.1.0"
