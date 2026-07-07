"""
The daily trading step of the live paper track record.

This is quantconnect/main.py rebuilt on the statarb package itself, run once
per day after the close by the live workflow. Signals are computed on today's
close; market DAY orders are submitted after hours and fill at the NEXT open.
That gap is not a bug — it is the honest execution model for a daily strategy,
and the intended-vs-filled gap it creates is exactly what the Phase 3
post-mortem wants measured, so every order is logged with the close that
generated it, the reference price at submission, and the order id to join
against actual fills later.

Pipeline, mirroring the walk-forward portfolio engine so live and backtest
disagreements mean something:

  weekly    select_pairs (FDR + stability gates) on an adjusted daily panel,
  refit     frozen beta + OU fit per survivor, cost-aware optimal_bands;
            pairs whose costs eat the edge are skipped, pairs that lose
            their model while holding a position are flattened.
  daily     rolling z with the frozen beta (past-only window, same as
            portfolio.py), entries vol-targeted to risk_per_pair_bps of live
            account equity, z-stop at 3.5 with the one-sided re-entry block,
            exits on reversion or 3x half-life staleness, portfolio gross
            capped.

State (models, open positions, blocks, last run/refit dates) lives in
track_record/state.json so the committed history shows every decision input.
Re-running on a day that already ran is a no-op: workflow retries must not
double-trade.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from statarb import (
    CostModel, SelectionConfig, select_pairs, fit_spread_model, optimal_bands,
)

# Same sector-restricted universe as quantconnect/main.py. No symbol appears
# in two pairs — the per-pair position ledger relies on that.
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


@dataclass
class StrategyConfig:
    candidates: list = field(default_factory=lambda: list(CANDIDATES))
    lookback: int = 378              # ~18m fit window, as in the QC algorithm
    refit_days: int = 7              # recalibrate weekly (calendar days)
    max_pairs: int = 6
    risk_per_pair_bps: float = 10.0  # daily risk budget per pair, bps of equity
    max_gross_leverage: float = 3.0
    max_pair_gross_frac: float = 0.5 # one pair's gross may not exceed this * NAV
    stop_z: float = 3.5
    max_hold_mult: float = 3.0
    z_window_mult: float = 3.0
    selection: SelectionConfig = field(default_factory=SelectionConfig)
    costs: CostModel = field(default_factory=CostModel)


# --------------------------------------------------------------------------- #
#  State                                                                      #
# --------------------------------------------------------------------------- #
def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"last_run": None, "last_refit": None, "models": {},
            "positions": {}, "blocked": {}}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
#  Weekly refit                                                               #
# --------------------------------------------------------------------------- #
def refit_models(logp: pd.DataFrame, cfg: StrategyConfig) -> dict:
    """
    select_pairs + fit_spread_model + optimal_bands on the training panel.
    Returns {"A/B": model-dict} for pairs that pass every gate AND clear their
    own costs. Frozen numbers only — nothing here updates between refits.
    """
    sel = select_pairs(logp, cfg.candidates, cfg.selection)
    chosen = sel[sel.passed].head(cfg.max_pairs)
    models = {}
    for _, row in chosen.iterrows():
        a, b = row.a, row.b
        model = fit_spread_model(logp[a].values, logp[b].values)
        hl = model.ou.half_life
        rt_cost = 2.0 * (1.0 + abs(model.beta)) * cfg.costs.per_leg_bps / 1e4
        bands = optimal_bands(model.ou, rt_cost)
        if not bands.tradeable:
            continue                     # costs eat the edge: not a trade
        models[f"{a}/{b}"] = {
            "a": a, "b": b, "beta": float(model.beta),
            "half_life": float(hl),
            "adf_pvalue": float(model.adf_pvalue),
            "entry_z": float(bands.entry_z), "exit_z": float(bands.exit_z),
            "z_window": int(np.clip(round(cfg.z_window_mult * hl), 15,
                                    cfg.lookback // 2)),
            "max_hold": int(np.clip(round(cfg.max_hold_mult * hl), 5, 120)),
        }
    return models


# --------------------------------------------------------------------------- #
#  Daily signals                                                              #
# --------------------------------------------------------------------------- #
def pair_signal(logp: pd.DataFrame, m: dict) -> tuple[float, float] | None:
    """(z, daily spread vol) from the frozen beta, past-only rolling window."""
    spread = logp[m["a"]] - m["beta"] * logp[m["b"]]
    w = spread.tail(m["z_window"])
    if len(w) < m["z_window"]:
        return None
    sd = w.std(ddof=1)
    dvol = w.diff().std(ddof=1)
    if not np.isfinite(sd) or sd <= 0 or not np.isfinite(dvol) or dvol <= 0:
        return None
    z = (w.iloc[-1] - w.mean()) / sd
    return float(z), float(dvol)


def run_daily(broker, state: dict, bars: pd.DataFrame,
              cfg: StrategyConfig, today: str) -> list[dict]:
    """
    One post-close decision pass. Mutates `state`, submits orders through
    `broker`, returns the order log (one dict per submitted order).

    `bars` is the adjusted daily close panel INCLUDING today's close.
    """
    orders: list[dict] = []
    logp = np.log(bars)
    equity = broker.account_snapshot()["equity"]
    # gross already on the book; entries submitted below rest until the next
    # open, so their notional is tracked here or the cap leaks for one night
    gross = sum(abs(p["market_value"] or 0.0) for p in broker.all_positions())

    # ---- reconcile: the broker's book is the truth ------------------------ #
    # Yesterday's after-hours orders normally fill at the open; if one didn't
    # (rejected, expired), our per-pair ledger is wrong. Adopt the broker's
    # quantities and say so in the log rather than trading on fiction.
    for pair, p in list(state["positions"].items()):
        m = state["models"].get(pair)
        a, b = pair.split("/")
        qa, qb = broker.position(a), broker.position(b)
        if qa != p["qty_a"] or qb != p["qty_b"]:
            orders.append({"date": today, "pair": pair, "action": "reconcile",
                           "note": f"state ({p['qty_a']},{p['qty_b']}) vs "
                                   f"broker ({qa},{qb}); adopting broker"})
            if qa == 0.0 and qb == 0.0:
                del state["positions"][pair]
                continue
            p["qty_a"], p["qty_b"] = qa, qb
        if m is None:
            # model was dropped at refit while position was open: flatten
            _close(broker, state, orders, pair, p, today, z=None,
                   action="exit_model_dropped")

    # ---- per-pair decisions ------------------------------------------------ #
    for pair, m in state["models"].items():
        sig = pair_signal(logp, m)
        if sig is None:
            continue
        z, dvol = sig
        blocked = state["blocked"].get(pair, 0)

        # heal the post-stop block once z is back inside the entry band
        if blocked == +1 and z > -m["entry_z"]:
            blocked = 0
        elif blocked == -1 and z < m["entry_z"]:
            blocked = 0
        state["blocked"][pair] = blocked

        pos = state["positions"].get(pair)
        if pos is None:
            side = 0
            if z > m["entry_z"] and blocked != -1:
                side = -1
            elif z < -m["entry_z"] and blocked != +1:
                side = +1
            if side == 0:
                continue
            if equity <= 0 or gross / equity >= cfg.max_gross_leverage:
                orders.append({"date": today, "pair": pair, "action": "skip_entry",
                               "note": "gross leverage cap", "z": z})
                continue
            gross += _open(broker, state, orders, pair, m, side, z, dvol,
                           equity, cfg, bars, today)
        else:
            pos["hold"] += 1
            side = 1 if pos["qty_a"] > 0 else -1
            stopped = (side > 0 and z < -cfg.stop_z) or \
                      (side < 0 and z > cfg.stop_z)
            reverted = abs(z) < m["exit_z"]
            stale = pos["hold"] >= m["max_hold"]
            if stopped:
                _close(broker, state, orders, pair, pos, today, z, "stop")
                state["blocked"][pair] = +1 if side > 0 else -1
            elif reverted:
                _close(broker, state, orders, pair, pos, today, z, "exit_reverted")
            elif stale:
                _close(broker, state, orders, pair, pos, today, z, "exit_stale")

    return orders


def _submit(broker, orders, today, pair, action, z, symbol, qty, intended_px):
    fill = broker.submit(symbol, qty)
    orders.append({
        "date": today, "pair": pair, "action": action, "z": z,
        "symbol": symbol, "qty": fill.qty if fill.qty else qty,
        "intended_price": intended_px,          # today's close, the signal price
        "reference_price": fill.price,          # latest trade at submission
        "filled": fill.filled, "fill_price": fill.price if fill.filled else None,
        "order_id": fill.order_id, "status": fill.status,
    })
    return fill


def _open(broker, state, orders, pair, m, side, z, dvol, equity, cfg,
          bars, today) -> float:
    """Submit both entry legs. Returns the gross notional added (dollars)."""
    a, b = m["a"], m["b"]
    px_a, px_b = float(bars[a].iloc[-1]), float(bars[b].iloc[-1])

    # dollars per unit of spread so the pair contributes risk_per_pair_bps of
    # equity in daily vol; dvol is in log-spread units, so g is ~$ per unit
    g = (cfg.risk_per_pair_bps / 1e4) * equity / dvol
    g = min(g, cfg.max_pair_gross_frac * equity / (1.0 + abs(m["beta"])))
    wa = side * g
    wb = -side * g * m["beta"]
    qty_a = int(round(wa / px_a))
    qty_b = int(round(wb / px_b))
    if qty_a == 0 or qty_b == 0:
        orders.append({"date": today, "pair": pair, "action": "skip_entry",
                       "note": "size rounds to zero shares", "z": z})
        return 0.0

    fa = _submit(broker, orders, today, pair, "entry", z, a, qty_a, px_a)
    fb = _submit(broker, orders, today, pair, "entry", z, b, qty_b, px_b)
    state["positions"][pair] = {
        "qty_a": fa.qty, "qty_b": fb.qty, "g": g, "side": side,
        "entered": today, "entry_z": z, "hold": 0,
    }
    return abs(qty_a) * px_a + abs(qty_b) * px_b


def _close(broker, state, orders, pair, pos, today, z, action):
    # The reconcile pass at the top of run_daily has already made the ledger
    # match the broker, so closing the ledger quantity is closing the real
    # position. Zero legs are skipped — never invent an order for them.
    a, b = pair.split("/")
    for sym, qty in ((a, pos["qty_a"]), (b, pos["qty_b"])):
        if qty:
            _submit(broker, orders, today, pair, action, z, sym, -qty, None)
    state["positions"].pop(pair, None)


# --------------------------------------------------------------------------- #
#  Entry point                                                                #
# --------------------------------------------------------------------------- #
def main() -> int:
    from statarb.broker import AlpacaPaperBroker

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("track_record")
    state_path = root / "state.json"
    orders_dir = root / "orders"
    orders_dir.mkdir(parents=True, exist_ok=True)

    cfg = StrategyConfig()
    broker = AlpacaPaperBroker()            # fails loudly on bad keys
    today = str(broker.trading_date())

    if not broker.is_trading_day():
        print(f"{today}: not a trading day, nothing to do")
        return 0

    state = load_state(state_path)
    if state["last_run"] == today:
        print(f"{today}: already ran today, refusing to double-trade")
        return 0

    tickers = sorted({t for p in cfg.candidates for t in p})
    bars = broker.daily_bars(tickers, cfg.lookback)
    print(f"bars: {bars.shape[0]} days x {bars.shape[1]} symbols "
          f"(feed={broker.last_feed_used}, last={bars.index[-1]})")
    if bars.shape[1] != len(tickers):
        missing = set(tickers) - set(bars.columns)
        raise RuntimeError(f"missing bars for {sorted(missing)}")
    if len(bars) < cfg.lookback // 2:
        raise RuntimeError(f"panel too short: {len(bars)} rows "
                           f"(one symbol's history truncates the whole panel)")

    # weekly refit
    last_refit = state.get("last_refit")
    if last_refit is None or (date.fromisoformat(today) -
                              date.fromisoformat(last_refit)
                              >= timedelta(days=cfg.refit_days)):
        state["models"] = refit_models(np.log(bars), cfg)
        state["last_refit"] = today
        print(f"refit: {len(state['models'])} tradeable pairs "
              f"{sorted(state['models'])}")

    orders = run_daily(broker, state, bars, cfg, today)
    state["last_run"] = today
    save_state(state_path, state)

    tmp = orders_dir / f"{today}.json.tmp"
    tmp.write_text(json.dumps(orders, indent=2, default=str))
    os.replace(tmp, orders_dir / f"{today}.json")

    print(f"{today}: {len(orders)} order-log entries, "
          f"{len(state['positions'])} open pairs, "
          f"models={sorted(state['models'])}")
    for o in orders:
        print(" ", o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
