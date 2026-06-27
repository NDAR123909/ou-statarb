# region imports
from AlgorithmImports import *
import numpy as np
from collections import deque
from statsmodels.tsa.stattools import adfuller
# endregion


class OUPairsTrading(QCAlgorithm):
    """
    Ornstein-Uhlenbeck pairs trading on a cointegrated pair.

    A LEAN port of the ou-statarb research project. The methodology is the same
    one I validated offline, adapted to run on QuantConnect's engine:

      - re-estimate the hedge ratio every week on a rolling window (this is the
        walk-forward idea: parameters are never fit on data they trade)
      - an ADF cointegration gate, so the algorithm only trades a pair while its
        spread is actually stationary
      - the OU half-life sets the z-score lookback window
      - a z-score entry/exit rule, with dollar-neutral legs

    Transaction costs and slippage are handled by LEAN's brokerage model, so the
    backtest is honest about fills without me hand-rolling a cost model.

    This is a starting template, not a tuned winner. Backtest it, look at the
    out-of-sample stretch, and swap the pair for one with an economic story you
    can defend.
    """

    def initialize(self):
        # 5 years of history, $1M, SPY benchmark, institutional cost model.
        self.set_start_date(2019, 1, 1)
        self.set_end_date(2024, 1, 1)
        self.set_cash(1_000_000)
        self.set_benchmark("SPY")
        self.set_brokerage_model(BrokerageName.ALPHA_STREAMS)

        # The pair. V/MA (payments duopoly) is a defensible, commonly cointegrated
        # choice. Other reasonable starts: KO/PEP, GLD/IAU (tighter), EWA/EWC.
        self.tickers = ["V", "MA"]
        self.symbols = [self.add_equity(t, Resolution.DAILY).symbol
                        for t in self.tickers]

        # Strategy parameters.
        self.lookback = 252          # days per re-estimation of beta and OU
        self.entry_z = 2.0
        self.exit_z = 0.5
        self.adf_pmax = 0.05         # cointegration gate
        self.max_half_life = 60      # regime gate: skip pairs that revert too slowly

        # State carried between bars.
        self.beta = None
        self.spread_window = None
        self.trading_ok = False

        # First fit now, then re-fit at the start of every week.
        self.recalibrate()
        self.schedule.on(
            self.date_rules.week_start(self.symbols[0]),
            self.time_rules.after_market_open(self.symbols[0], 30),
            self.recalibrate,
        )

    def recalibrate(self):
        """Re-estimate hedge ratio, test cointegration, fit the OU half-life."""
        history = self.history(self.symbols, self.lookback, Resolution.DAILY)
        if history.empty or "close" not in history.columns:
            self.trading_ok = False
            return
        try:
            closes = history["close"].unstack(level=0).dropna()
            a = np.log(closes[self.symbols[0]].values)
            b = np.log(closes[self.symbols[1]].values)
        except Exception:
            self.trading_ok = False
            return
        if len(a) < self.lookback // 2:
            self.trading_ok = False
            return

        # Hedge ratio (OLS) and the spread.
        beta = float(np.polyfit(b, a, 1)[0])
        spread = a - beta * b

        # Cointegration gate: ADF on the in-sample spread.
        try:
            adf_p = adfuller(spread, autolag="AIC")[1]
        except Exception:
            adf_p = 1.0

        # OU half-life from an AR(1) slope on the spread.
        ds = np.diff(spread)
        phi = float(np.polyfit(spread[:-1], ds, 1)[0])
        half_life = -np.log(2) / phi if phi < 0 else np.inf

        if adf_p < self.adf_pmax and np.isfinite(half_life) \
                and half_life < self.max_half_life:
            self.beta = beta
            window = int(max(20, min(3 * half_life, self.lookback // 2)))
            # Seed the z-score window with the tail of the in-sample spread so it
            # is warm immediately (past data only, no look-ahead).
            self.spread_window = deque(spread[-window:], maxlen=window)
            self.trading_ok = True
            self.log(f"recalibrate ok: beta={beta:.3f} adf_p={adf_p:.3g} "
                     f"half_life={half_life:.1f} window={window}")
        else:
            self.trading_ok = False
            self.liquidate()  # relationship looks dead; stand aside
            self.log(f"recalibrate skip: adf_p={adf_p:.3g} half_life={half_life:.1f}")

    def on_data(self, data):
        if not self.trading_ok or self.beta is None:
            return
        s0, s1 = self.symbols
        if not (data.contains_key(s0) and data.contains_key(s1)):
            return
        bar0, bar1 = data[s0], data[s1]
        if bar0 is None or bar1 is None:
            return

        pa, pb = bar0.close, bar1.close
        if pa <= 0 or pb <= 0:
            return

        spread = np.log(pa) - self.beta * np.log(pb)
        self.spread_window.append(spread)
        if len(self.spread_window) < self.spread_window.maxlen:
            return

        arr = np.asarray(self.spread_window)
        mu, sd = arr.mean(), arr.std(ddof=1)
        if sd == 0:
            return
        z = (spread - mu) / sd

        invested = self.portfolio[s0].invested or self.portfolio[s1].invested
        denom = 1.0 + abs(self.beta)   # keeps gross exposure near 1

        if not invested:
            spread_pos = 0
            if z > self.entry_z:
                spread_pos = -1            # spread rich -> short it
            elif z < -self.entry_z:
                spread_pos = +1            # spread cheap -> long it
            if spread_pos != 0:
                # long spread = long A, short beta units of B (signs flip for short)
                self.set_holdings(s0, spread_pos / denom)
                self.set_holdings(s1, -spread_pos * self.beta / denom)
        else:
            if abs(z) < self.exit_z:
                self.liquidate()
