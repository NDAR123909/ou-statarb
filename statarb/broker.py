r"""
A thin bridge for running a pairs strategy against a broker, live or simulated.

The point of this module is to get a real, zero-capital track record instead of
another backtest. It defines a small Broker interface, two implementations, and a
runner that drives the Kalman pairs strategy one bar at a time.

  MockBroker          replays a historical price feed and fills at the current
                      bar with slippage and commission. Lets you exercise the
                      entire live loop offline and check the plumbing.
  AlpacaPaperBroker   the same interface against Alpaca's paper endpoint. Needs
                      `pip install alpaca-py` and paper keys. The import is
                      guarded so the module loads fine without it.

The runner is deliberately boring. Each step it reads prices, updates the filter,
turns the signal into target share quantities for both legs, and trades the
difference. Boring is the goal: the same code path that runs the simulation is
the one that would trade paper.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .kalman import kalman_state


@dataclass
class Fill:
    step: int
    symbol: str
    qty: float          # signed: + buy, - sell
    price: float
    cost: float


@dataclass
class Broker:
    """Interface. Concrete brokers implement price, submit, positions, equity."""
    def price(self, symbol: str) -> float: raise NotImplementedError
    def submit(self, symbol: str, qty: float) -> Fill: raise NotImplementedError
    def position(self, symbol: str) -> float: raise NotImplementedError
    def equity(self) -> float: raise NotImplementedError


class MockBroker(Broker):
    """Replays a price panel (index = time, columns = symbols). Call advance()."""

    def __init__(self, prices: pd.DataFrame, cash: float = 100_000.0,
                 commission_bps: float = 1.0, slippage_bps: float = 2.0):
        self.prices = prices
        self.cash = cash
        self.commission_bps = commission_bps
        self.slippage_bps = slippage_bps
        self.t = 0
        self.shares: dict[str, float] = {s: 0.0 for s in prices.columns}
        self.fills: list[Fill] = []
        self.equity_curve: list[float] = []

    def advance(self) -> bool:
        """Move to the next bar. Returns False at the end of the feed."""
        self.t += 1
        if self.t >= len(self.prices):
            return False
        self.equity_curve.append(self.equity())
        return True

    def price(self, symbol: str) -> float:
        idx = min(self.t, len(self.prices) - 1)
        return float(self.prices[symbol].iloc[idx])

    def submit(self, symbol: str, qty: float) -> Fill:
        if qty == 0.0:
            return Fill(self.t, symbol, 0.0, self.price(symbol), 0.0)
        px = self.price(symbol)
        fill_px = px * (1 + np.sign(qty) * self.slippage_bps / 1e4)  # pay the spread
        notional = abs(qty) * fill_px
        commission = notional * self.commission_bps / 1e4
        self.cash -= qty * fill_px + commission
        self.shares[symbol] += qty
        f = Fill(self.t, symbol, qty, fill_px, commission)
        self.fills.append(f)
        return f

    def position(self, symbol: str) -> float:
        return self.shares[symbol]

    def equity(self) -> float:
        mtm = sum(self.shares[s] * self.price(s) for s in self.prices.columns)
        return self.cash + mtm


class AlpacaPaperBroker(Broker):
    """
    Same interface against Alpaca's paper trading endpoint. Untested here because
    it needs network and keys; run it on your machine.

        broker = AlpacaPaperBroker(key, secret)   # paper=True by default

    Requires `pip install alpaca-py`.
    """

    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import StockHistoricalDataClient
        except ImportError as e:
            raise ImportError("pip install alpaca-py to use AlpacaPaperBroker") from e
        from alpaca.data.requests import StockLatestTradeRequest
        self._TradingClient = TradingClient
        self._data = StockHistoricalDataClient(api_key, api_secret)
        self._trade = TradingClient(api_key, api_secret, paper=paper)
        self._latest_req = StockLatestTradeRequest

    def price(self, symbol: str) -> float:
        req = self._latest_req(symbol_or_symbols=symbol)
        return float(self._data.get_stock_latest_trade(req)[symbol].price)

    def submit(self, symbol: str, qty: float) -> Fill:
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce
        if qty == 0.0:
            return Fill(0, symbol, 0.0, self.price(symbol), 0.0)
        side = OrderSide.BUY if qty > 0 else OrderSide.SELL
        order = MarketOrderRequest(symbol=symbol, qty=abs(qty), side=side,
                                   time_in_force=TimeInForce.DAY)
        self._trade.submit_order(order)
        return Fill(0, symbol, qty, self.price(symbol), 0.0)

    def position(self, symbol: str) -> float:
        try:
            return float(self._trade.get_open_position(symbol).qty)
        except Exception:
            return 0.0

    def equity(self) -> float:
        return float(self._trade.get_account().equity)


def run_pairs_session(
    broker: MockBroker,
    sym_a: str,
    sym_b: str,
    notional: float = 10_000.0,
    entry_z: float = 1.5,
    exit_z: float = 0.0,
    burn_in: int = 250,
    delta: float = 1e-6,
    R: float = 1e-3,
    rebalance_band: float = 0.2,
):
    """
    Drive a Kalman pairs strategy bar by bar through a MockBroker.

    Each step: feed the new prices to the incremental filter (only past data),
    read the normalized innovation, pick a target spread position (-1/0/+1), and
    move both legs to the target share counts. The hedge ratio is the filter's
    current beta, so the B leg is sized as -beta * notional.

    Returns the broker's equity curve and the trade log.
    """
    state = kalman_state(delta=delta, R=R)
    target = 0.0
    last_traded = 0.0
    t = 0
    log = []

    while True:
        pa, pb = broker.price(sym_a), broker.price(sym_b)
        e, s, beta = state.step(np.log(pa), np.log(pb))
        z = e / s
        t += 1

        if t > burn_in:
            if target == 0.0:
                if z > entry_z: target = -1.0
                elif z < -entry_z: target = +1.0
            elif abs(z) < exit_z or (target > 0 and z > entry_z) or \
                    (target < 0 and z < -entry_z):
                target = 0.0 if abs(z) < exit_z else -target

            # Trade on a signal change, and while in a position re-hedge a leg
            # only when its share count has drifted past `rebalance_band`. This
            # keeps the hedge current without bleeding slippage every bar.
            tgt_a = target * notional / pa
            tgt_b = -target * beta * notional / pb
            for sym, tgt in ((sym_a, tgt_a), (sym_b, tgt_b)):
                held = broker.position(sym)
                signal_changed = target != last_traded
                drifted = abs(tgt - held) > rebalance_band * max(abs(tgt), 1e-9)
                if signal_changed or (target != 0.0 and drifted):
                    broker.submit(sym, tgt - held)
            last_traded = target
            log.append({"step": t, "z": float(z), "beta": float(beta),
                        "target": target, "equity": broker.equity()})

        if not broker.advance():
            break

    return pd.DataFrame(log), broker.equity_curve
