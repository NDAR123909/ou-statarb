# region imports
from AlgorithmImports import *
import numpy as np
from collections import deque
from statsmodels.tsa.stattools import adfuller
# endregion


class PairState:
    """Per-pair trading state carried between bars."""
    __slots__ = ("beta", "window", "half_life", "entry_z", "exit_z",
                 "hold", "blocked", "active")

    def __init__(self):
        self.beta = None
        self.window = None          # deque of recent spread values
        self.half_life = np.inf
        self.entry_z = 2.0
        self.exit_z = 0.5
        self.hold = 0
        self.blocked = 0            # +1 longs blocked post-stop, -1 shorts
        self.active = False


class OUPairsPortfolio(QCAlgorithm):
    """
    Multi-pair OU statistical arbitrage. The portfolio version of ou-statarb.

    What changed vs the single-pair template, and why each change matters live:

      PORTFOLIO of sector-restricted pairs. A single pair is concentration
      risk wearing a lab coat. Breadth is where pairs trading gets whatever
      Sharpe it has. Candidates are hand-restricted to same-sector pairs,
      which is the multiple-testing correction that carries economic meaning.

      Z-STOP with one-sided re-entry block. Mean reversion's fatal mode is
      adding into a relationship that broke for good. If |z| blows past
      stop_z the position is cut and that side stays blocked until the
      spread heals back inside the entry band.

      MAX-HOLD tied to the fitted half-life. If a trade has been on for 3x
      the half-life, the model was wrong about the spring; stop paying
      borrow to find out how wrong.

      VOL-TARGETED sizing. Each pair gets an equal daily-risk budget rather
      than an equal notional, so one sleepy spread can't be levered into the
      book's biggest bet while a wild one dominates risk.

      WEEKLY re-fit with a strict gate: ADF p, half-life band, and a
      split-half beta-stability check. Pairs that fail go flat immediately.
    """

    # sector-restricted candidate pairs (edit to taste; keep it restricted)
    CANDIDATES = [
        ("V", "MA"),        # payment networks
        ("KO", "PEP"),      # beverages
        ("XOM", "CVX"),     # oil majors
        ("HD", "LOW"),      # home improvement
        ("UPS", "FDX"),     # parcels
        ("GS", "MS"),       # investment banks
        ("UNP", "CSX"),     # rails
        ("MCD", "YUM"),     # restaurants
    ]

    def initialize(self):
        # No end date: the backtest runs to the present, and once published to
        # the Strategies hub QuantConnect re-runs it daily so everything after
        # the publication date is verifiable out-of-sample. Default brokerage
        # model kept as-is — Strategies submissions must not override models.
        self.set_start_date(2019, 1, 1)
        self.set_cash(1_000_000)
        self.set_benchmark("SPY")

        tickers = sorted({t for p in self.CANDIDATES for t in p})
        self.syms = {t: self.add_equity(t, Resolution.DAILY).symbol
                     for t in tickers}

        # Idle cash earns nothing in a LEAN backtest while a real brokerage
        # sweeps it into interest, which makes any low-vol market-neutral
        # book look like Sharpe -3 against the risk-free hurdle. Park spare
        # cash in 1-3 month T-bills (BIL) so the curve shows what a live
        # account would actually earn. Disclosed in the published version
        # notes: the equity curve is T-bill yield plus the pairs overlay.
        self.bil = self.add_equity("BIL", Resolution.DAILY).symbol
        self.cash_target = 0.85

        # parameters
        self.lookback = 378          # ~18m fit window
        self.adf_pmax = 0.05
        self.hl_min, self.hl_max = 3.0, 40.0
        self.stop_z = 3.5
        self.max_hold_mult = 3.0
        self.max_beta_drift = 0.30
        self.risk_per_pair = 0.0025  # 25 bps of NAV daily risk per pair
        self.max_pairs = 6
        self.max_gross = 1.0         # pairs-only gross cap (BIL excluded);
                                     # 0.85 BIL + 1.0 pairs stays inside 2x
                                     # equity buying power with room to spare

        self.pairs = {p: PairState() for p in self.CANDIDATES}

        self.recalibrate()
        self.schedule.on(
            self.date_rules.week_start(self.syms[tickers[0]]),
            self.time_rules.after_market_open(self.syms[tickers[0]], 30),
            self.recalibrate,
        )

    # ------------------------------------------------------------------ fit --
    def _fit_pair(self, a, b):
        """Return (beta, half_life, spread) if the pair passes the gate."""
        hist = self.history([self.syms[a], self.syms[b]],
                            self.lookback, Resolution.DAILY)
        if hist.empty or "close" not in hist.columns:
            return None
        closes = hist["close"].unstack(level=0).dropna()
        if len(closes) < self.lookback // 2:
            return None
        la = np.log(closes[self.syms[a]].values)
        lb = np.log(closes[self.syms[b]].values)

        beta = float(np.polyfit(lb, la, 1)[0])
        if not (0.3 <= abs(beta) <= 3.0):
            return None
        spread = la - beta * lb

        # split-half beta stability: a real linkage doesn't move much
        h = len(la) // 2
        b1 = float(np.polyfit(lb[:h], la[:h], 1)[0])
        b2 = float(np.polyfit(lb[h:], la[h:], 1)[0])
        if abs(b1 - b2) > self.max_beta_drift * max(abs(beta), 1e-9):
            return None

        # adfuller raises on degenerate input; a flat spread is the only way
        # real price history gets there, so gate on variance instead of
        # try/except (the Strategies hub rejects code containing try/except).
        if np.std(spread) < 1e-12:
            return None
        adf_p = adfuller(spread, autolag="AIC")[1]
        if adf_p >= self.adf_pmax:
            return None

        phi = float(np.polyfit(spread[:-1], np.diff(spread), 1)[0])
        half_life = -np.log(2) / phi if phi < 0 else np.inf
        if not (self.hl_min <= half_life <= self.hl_max):
            return None
        return beta, half_life, spread

    def recalibrate(self):
        scored = []
        for pair in self.pairs:
            fit = self._fit_pair(*pair)
            st = self.pairs[pair]
            if fit is None:
                if st.active:
                    self._flatten(pair)
                st.active = False
                continue
            beta, hl, spread = fit
            win = int(max(20, min(3 * hl, self.lookback // 2)))
            st.beta, st.half_life = beta, hl
            st.window = deque(spread[-win:], maxlen=win)
            scored.append((hl, pair))

        # keep the fastest-reverting max_pairs; flatten the rest
        scored.sort()
        keep = {p for _, p in scored[: self.max_pairs]}
        for pair, st in self.pairs.items():
            was = st.active
            st.active = pair in keep
            if was and not st.active:
                self._flatten(pair)
        self.log(f"recalibrate: {len(keep)} pairs active "
                 f"{sorted(f'{a}/{b}' for a, b in keep)}")

    # --------------------------------------------------------------- trading --
    def _flatten(self, pair):
        a, b = pair
        self.liquidate(self.syms[a])
        self.liquidate(self.syms[b])
        self.pairs[pair].hold = 0

    def _invested(self, pair):
        a, b = pair
        return (self.portfolio[self.syms[a]].invested
                or self.portfolio[self.syms[b]].invested)

    def _gross_leverage(self):
        # BIL is cash parking, not a bet; counting it would eat the pairs cap
        nav = self.portfolio.total_portfolio_value
        gross = sum(abs(h.holdings_value) for h in self.portfolio.values()
                    if h.symbol != self.bil)
        return gross / nav if nav > 0 else 0.0

    def _park_cash(self, data):
        """Keep idle cash swept into BIL, rebalancing only on meaningful
        drift so the parking position doesn't generate order churn."""
        if not data.contains_key(self.bil):
            return
        nav = self.portfolio.total_portfolio_value
        if nav <= 0:
            return
        w = self.portfolio[self.bil].holdings_value / nav
        if abs(w - self.cash_target) > 0.02:
            self.set_holdings(self.bil, self.cash_target)

    def on_data(self, data):
        nav = self.portfolio.total_portfolio_value
        self._park_cash(data)
        for pair, st in self.pairs.items():
            if not st.active or st.beta is None:
                continue
            a, b = pair
            sa, sb = self.syms[a], self.syms[b]
            if not (data.contains_key(sa) and data.contains_key(sb)):
                continue
            ba, bb = data[sa], data[sb]
            if ba is None or bb is None or ba.close <= 0 or bb.close <= 0:
                continue

            spread = np.log(ba.close) - st.beta * np.log(bb.close)
            st.window.append(spread)
            if len(st.window) < st.window.maxlen:
                continue
            arr = np.asarray(st.window)
            sd = arr.std(ddof=1)
            if sd == 0:
                continue
            z = (spread - arr.mean()) / sd

            # heal the post-stop block once z is back inside the band
            if st.blocked == +1 and z > -st.entry_z:
                st.blocked = 0
            elif st.blocked == -1 and z < st.entry_z:
                st.blocked = 0

            invested = self._invested(pair)
            if not invested:
                side = 0
                if z > st.entry_z and st.blocked != -1:
                    side = -1
                elif z < -st.entry_z and st.blocked != +1:
                    side = +1
                if side != 0 and self._gross_leverage() < self.max_gross:
                    # vol-target: daily spread vol in return terms
                    dvol = np.std(np.diff(arr), ddof=1)
                    if dvol <= 0:
                        continue
                    g = self.risk_per_pair * nav / dvol   # $ per unit spread
                    g = min(g, 0.25 * nav)                # single-pair cap
                    self.set_holdings(sa, side * g / nav)
                    self.set_holdings(sb, -side * st.beta * g / nav)
                    st.hold = 0
            else:
                st.hold += 1
                long_spread = self.portfolio[sa].is_long
                stopped = (long_spread and z < -self.stop_z) or \
                          (not long_spread and z > self.stop_z)
                stale = st.hold >= self.max_hold_mult * st.half_life
                reverted = abs(z) < st.exit_z
                if stopped:
                    self._flatten(pair)
                    st.blocked = +1 if long_spread else -1
                elif reverted or stale:
                    self._flatten(pair)
