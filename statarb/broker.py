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
    # Live-broker extras (defaults keep MockBroker and old callers unchanged).
    order_id: str = ""
    filled: bool = True     # False when the order is resting (e.g. submitted
    #                         after hours; it will fill at the next open)
    status: str = ""


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
    Same interface against Alpaca's paper trading endpoint, plus the extras the
    deployment harness needs (account snapshot, daily bars, today's fills).

        broker = AlpacaPaperBroker()              # keys from the environment
        broker = AlpacaPaperBroker(key, secret)   # or passed explicitly

    Keys come from ALPACA_KEY_ID / ALPACA_SECRET_KEY (the names used in the
    GitHub Actions secrets) with Alpaca's own APCA_API_KEY_ID /
    APCA_API_SECRET_KEY as fallbacks. Auth is validated in the constructor by
    fetching the account, so a bad key fails loudly at startup instead of
    halfway through a trading run.

    Two realities of the live API this class absorbs so callers don't have to:

      * Market orders submitted after hours REST until the next open. The
        daily workflow runs after the close, so this is the normal path, not
        an error: submit() returns a Fill with filled=False and the current
        reference price, and the order_id so the fill can be reconciled the
        next day.
      * Free data plans reject SIP quotes/bars newer than 15 minutes. Every
        data call tries SIP first and falls back to the IEX feed, recording
        which feed answered in `last_feed_used`.

    Requires `pip install alpaca-py`.
    """

    def __init__(self, api_key: str | None = None, api_secret: str | None = None,
                 paper: bool = True, fill_timeout: float = 90.0,
                 poll_interval: float = 2.0):
        try:
            from alpaca.trading.client import TradingClient
            from alpaca.data.historical import StockHistoricalDataClient
        except ImportError as e:
            raise ImportError("pip install alpaca-py to use AlpacaPaperBroker") from e

        import os
        api_key = api_key or os.environ.get("ALPACA_KEY_ID") \
            or os.environ.get("APCA_API_KEY_ID")
        api_secret = api_secret or os.environ.get("ALPACA_SECRET_KEY") \
            or os.environ.get("APCA_API_SECRET_KEY")
        if not api_key or not api_secret:
            raise RuntimeError(
                "Alpaca keys missing: set ALPACA_KEY_ID and ALPACA_SECRET_KEY "
                "(or APCA_API_KEY_ID / APCA_API_SECRET_KEY)")

        self._data = StockHistoricalDataClient(api_key, api_secret)
        self._trade = TradingClient(api_key, api_secret, paper=paper)
        self.fill_timeout = fill_timeout
        self.poll_interval = poll_interval
        self.last_feed_used: str | None = None

        # Fail loudly, now, if the keys are wrong.
        acct = self._trade.get_account()
        if str(acct.status) not in ("AccountStatus.ACTIVE", "ACTIVE"):
            raise RuntimeError(f"Alpaca account not active: {acct.status}")

    # ------------------------------------------------------------- data side --
    def _with_feed_fallback(self, call):
        """Run `call(feed)` with SIP, falling back to IEX on subscription errors."""
        from alpaca.common.exceptions import APIError
        from alpaca.data.enums import DataFeed
        try:
            out = call(DataFeed.SIP)
            self.last_feed_used = "sip"
            return out
        except APIError as e:
            if "subscription" not in str(e).lower():
                raise
            out = call(DataFeed.IEX)
            self.last_feed_used = "iex"
            return out

    def price(self, symbol: str) -> float:
        return self.prices([symbol])[symbol]

    def prices(self, symbols: list[str]) -> dict[str, float]:
        """Latest trade price for each symbol."""
        from alpaca.data.requests import StockLatestTradeRequest

        def call(feed):
            req = StockLatestTradeRequest(symbol_or_symbols=symbols, feed=feed)
            return self._data.get_stock_latest_trade(req)

        trades = self._with_feed_fallback(call)
        return {s: float(trades[s].price) for s in symbols}

    def daily_bars(self, symbols: list[str], lookback_days: int) -> pd.DataFrame:
        """
        Split+dividend adjusted daily closes, one column per symbol. This is
        the panel the strategy fits on — adjusted, unlike the DJIA example csv.
        """
        from datetime import datetime, timedelta, timezone
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        from alpaca.data.enums import Adjustment

        # calendar-day cushion over trading days; end 16 min back so the free
        # plan's "no SIP data newer than 15 minutes" rule can't bite
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=int(lookback_days * 1.7) + 10)
        end = now - timedelta(minutes=16)

        def call(feed):
            req = StockBarsRequest(
                symbol_or_symbols=symbols, timeframe=TimeFrame.Day,
                start=start, end=end, adjustment=Adjustment.ALL, feed=feed)
            return self._data.get_stock_bars(req)

        bars = self._with_feed_fallback(call)
        df = bars.df  # MultiIndex (symbol, timestamp)
        closes = df["close"].unstack(level=0)
        closes.index = pd.to_datetime(closes.index).tz_convert("America/New_York").date
        return closes.dropna().tail(lookback_days)

    # ---------------------------------------------------------- trading side --
    def market_open(self) -> bool:
        return bool(self._trade.get_clock().is_open)

    def trading_date(self):
        """Current date in the exchange's timezone (America/New_York)."""
        return self._trade.get_clock().timestamp.date()

    def is_trading_day(self) -> bool:
        """True if the exchange holds (or held) a session today. Holidays gate
        the daily workflow: no session, no strategy run, no snapshot row."""
        from alpaca.trading.requests import GetCalendarRequest
        today = self.trading_date()
        cal = self._trade.get_calendar(GetCalendarRequest(start=today, end=today))
        return any(c.date == today for c in cal)

    def submit(self, symbol: str, qty: float) -> Fill:
        """
        Submit a market DAY order for whole shares and wait for the fill.

        If the market is closed the order rests until the next open; we return
        immediately with filled=False and the latest trade as a reference
        price. Rejected/canceled orders raise — a silently dropped order is
        exactly the kind of gap that makes a track record unverifiable.
        """
        import time
        from alpaca.trading.requests import MarketOrderRequest
        from alpaca.trading.enums import OrderSide, TimeInForce

        qty = float(int(round(qty)))    # whole shares: shorts can't be fractional
        if qty == 0.0:
            return Fill(0, symbol, 0.0, self.price(symbol), 0.0, status="noop")

        side = OrderSide.BUY if qty > 0 else OrderSide.SELL
        req = MarketOrderRequest(symbol=symbol, qty=abs(qty), side=side,
                                 time_in_force=TimeInForce.DAY)
        order = self._trade.submit_order(req)
        oid = str(order.id)

        if not self.market_open():
            return Fill(0, symbol, qty, self.price(symbol), 0.0,
                        order_id=oid, filled=False, status=str(order.status))

        deadline = time.time() + self.fill_timeout
        while time.time() < deadline:
            order = self._trade.get_order_by_id(oid)
            status = str(order.status).split(".")[-1].lower()
            if status == "filled":
                px = float(order.filled_avg_price)
                signed = float(order.filled_qty) * (1 if qty > 0 else -1)
                return Fill(0, symbol, signed, px, 0.0,
                            order_id=oid, filled=True, status=status)
            if status in ("canceled", "expired", "rejected", "suspended"):
                raise RuntimeError(f"order {oid} {symbol} qty={qty} ended {status}")
            time.sleep(self.poll_interval)

        raise RuntimeError(f"order {oid} {symbol} qty={qty} unfilled after "
                           f"{self.fill_timeout}s with market open")

    def cancel(self, order_id: str) -> None:
        self._trade.cancel_order_by_id(order_id)

    def position(self, symbol: str) -> float:
        from alpaca.common.exceptions import APIError
        try:
            return float(self._trade.get_open_position(symbol).qty)
        except APIError as e:
            if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                return 0.0
            raise

    def all_positions(self) -> list[dict]:
        """Every open position as a plain dict (JSON-serializable)."""
        out = []
        for p in self._trade.get_all_positions():
            out.append({
                "symbol": p.symbol,
                "qty": float(p.qty),
                "avg_entry_price": float(p.avg_entry_price),
                "current_price": float(p.current_price) if p.current_price else None,
                "market_value": float(p.market_value) if p.market_value else None,
                "unrealized_pl": float(p.unrealized_pl) if p.unrealized_pl else None,
                "side": str(p.side).split(".")[-1].lower(),
            })
        return out

    def equity(self) -> float:
        return float(self._trade.get_account().equity)

    def account_snapshot(self) -> dict:
        """The numbers the daily equity row is built from."""
        a = self._trade.get_account()
        return {
            "equity": float(a.equity),
            "cash": float(a.cash),
            "long_market_value": float(a.long_market_value),
            "short_market_value": float(a.short_market_value),
            "buying_power": float(a.buying_power),
            "last_equity": float(a.last_equity),
        }

    def todays_fills(self) -> list[dict]:
        """
        Every (partially) filled order whose fill happened on the current
        exchange-local trading date. Queried from closed orders, which the
        Trading API exposes without Broker-API permissions.
        """
        from datetime import datetime, time as dtime
        from zoneinfo import ZoneInfo
        from alpaca.trading.requests import GetOrdersRequest
        from alpaca.trading.enums import QueryOrderStatus

        tz = ZoneInfo("America/New_York")
        today = self.trading_date()
        midnight = datetime.combine(today, dtime.min, tzinfo=tz)
        req = GetOrdersRequest(status=QueryOrderStatus.CLOSED, after=midnight,
                               limit=500)
        fills = []
        for o in self._trade.get_orders(req):
            if not o.filled_at or float(o.filled_qty or 0) == 0:
                continue
            if o.filled_at.astimezone(tz).date() != today:
                continue
            sign = 1 if str(o.side).split(".")[-1].lower() == "buy" else -1
            fills.append({
                "order_id": str(o.id),
                "symbol": o.symbol,
                "qty": sign * float(o.filled_qty),
                "price": float(o.filled_avg_price),
                "submitted_at": o.submitted_at.isoformat() if o.submitted_at else None,
                "filled_at": o.filled_at.isoformat(),
                "status": str(o.status).split(".")[-1].lower(),
            })
        return fills


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
