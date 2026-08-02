"""
deploy/fills_report.py — what the venue actually did, against what we intended.

The ledger records the decision and the order we sent. This reconstructs what
came back: filled price versus the price the decision was taken at (slippage),
the fee the venue actually charged (versus the 5 bps per leg the cost model
assumes), realised P&L per round trip, hold time, and why each position closed.

It exists because `optimal_bands` refuses any pair whose edge cannot pay the
round-trip toll, and that toll is currently a guess. A cost model built on an
assumed fee is a backtest wearing a live-trading costume. `portfolio
user-fee-rate` would give the quoted tier but fails on the contest's simulated
portfolio (upstream 2002), so the fee has to be measured from fills — which is
the better number regardless, since it includes whatever the venue actually
did rather than what it advertises.

Two halves, deliberately separable:

  * Everything computable from `deploy/ltp_ledger.jsonl` alone — round trips,
    gross P&L from executed prices, hold times, exit reasons, slippage against
    the decision-time price. Pure functions, no network, tested offline.
  * Fees and funding, which need read-only calls to RapidX (`transaction
    executions`, `portfolio statement`). Skipped entirely with --no-api.

    set -a; source /root/ltp.env; set +a
    python deploy/fills_report.py                # full report
    python deploy/fills_report.py --no-api       # ledger only, no network
    python deploy/fills_report.py --json out.json

Read-only throughout: it opens no automation session and places no orders.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LEDGER = Path(__file__).resolve().parent / "ltp_ledger.jsonl"

# Decisions that open or close a position. `refit_drop` is included ahead of
# the event existing so this report keeps working the moment it ships; until
# then those closes arrive tagged "close" and land in UNMATCHED_CLOSE below.
OPEN_EVENTS = ("enter",)
CLOSE_EVENTS = ("exit", "stop", "refit_drop", "news_derisk", "kill_switch")
# Operations follow their decision within seconds (5.5s minimum spacing between
# the two legs, plus preview -> submit -> readback). 180s is generous enough to
# survive a slow venue and far short of the one-hour bar that separates
# consecutive decisions on the same pair.
OP_WINDOW_S = 180.0


def _ts(row: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(row["ts"])
    except (KeyError, TypeError, ValueError):
        return None


def _f(v) -> float | None:
    """Numbers arrive as floats from the agent and strings from the venue's
    readback; neither is wrong, so accept both and refuse to guess at junk."""
    if v in (None, "", "null"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def base_asset(symbol: str) -> str:
    """BINANCE_PERP_AVAX_USDT -> AVAX; pass anything else through unharmed."""
    parts = (symbol or "").split("_")
    return parts[2] if len(parts) > 2 else (symbol or "")


# ------------------------------------------------------------------ model --
@dataclass
class Leg:
    symbol: str
    base: str
    side: str                      # BUY / SELL as sent at entry
    qty: float
    entry_price: float | None = None
    exit_price: float | None = None
    intended_entry: float | None = None   # decision-time price, for slippage
    intended_exit: float | None = None
    entry_order_id: str | None = None
    exit_order_id: str | None = None
    # When the operation was recorded. Closing operations carry no order id, so
    # this is the only handle on which of a symbol's fills belong to them.
    entry_ts: datetime | None = None
    exit_ts: datetime | None = None
    fee: float | None = None       # summed over fills, once the API is queried
    venue_rpnl: float | None = None   # the venue's own realised P&L on the exit

    @property
    def pnl(self) -> float | None:
        if self.entry_price is None or self.exit_price is None:
            return None
        direction = 1.0 if self.side == "BUY" else -1.0
        return self.qty * (self.exit_price - self.entry_price) * direction


@dataclass
class RoundTrip:
    pair: str
    entry: dict
    close: dict | None = None
    legs: dict[str, Leg] = field(default_factory=dict)

    @property
    def opened(self) -> bool:
        """An `enter` decision whose orders never filled did not open a
        position. Day one produced four of these: every order was rejected
        with RCLI26005 because the automation cap sat below the order size,
        and counting them as trades would overstate the trade count and
        understate the win rate."""
        return any(l.entry_price is not None for l in self.legs.values())

    @property
    def closed(self) -> bool:
        return self.close is not None and any(
            l.exit_price is not None for l in self.legs.values())

    @property
    def reason(self) -> str:
        if self.close is None:
            return "open"
        if self.close.get("event") == "exit":
            return self.close.get("reason") or "exit"
        return self.close.get("event", "?")

    @property
    def hold_hours(self) -> float | None:
        a, b = _ts(self.entry), _ts(self.close) if self.close else None
        return (b - a).total_seconds() / 3600.0 if a and b else None

    @property
    def gross_pnl(self) -> float | None:
        vals = [l.pnl for l in self.legs.values() if l.pnl is not None]
        return sum(vals) if vals else None

    @property
    def venue_pnl(self) -> float | None:
        """The venue's own realised P&L on the closing fills. An independent
        check on `gross_pnl`, which is reconstructed from prices and sizes --
        if the two disagree the reconstruction is wrong, and a report nobody
        can falsify is not evidence."""
        vals = [l.venue_rpnl for l in self.legs.values()
                if l.venue_rpnl is not None]
        return sum(vals) if vals else None

    @property
    def fees(self) -> float | None:
        vals = [l.fee for l in self.legs.values() if l.fee is not None]
        return sum(vals) if vals else None

    @property
    def net_pnl(self) -> float | None:
        g, f = self.gross_pnl, self.fees
        return None if g is None else (g - f if f is not None else None)

    @property
    def notional(self) -> float:
        """Gross notional at entry, both legs — the base for a fee rate."""
        return sum(l.qty * l.entry_price for l in self.legs.values()
                   if l.entry_price is not None)


# ------------------------------------------------------- ledger -> trades --
def load_ledger(path: Path = LEDGER) -> list[dict]:
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass          # one malformed line must not lose the history
    return rows


def attach_operations(rows: list[dict]) -> list[dict]:
    """Give every decision the operations it caused.

    Operations carry `decision` (the reason tag) and `pair` but no unique id
    linking them to the exact decision row, so the join is (same pair, within
    OP_WINDOW_S after the decision). That is unambiguous because two decisions
    on one pair are at least a bar apart.
    """
    ops = [r for r in rows if r.get("event") == "operation"]
    decisions = [r for r in rows
                 if r.get("event") in OPEN_EVENTS + CLOSE_EVENTS]
    for d in decisions:
        t0 = _ts(d)
        d["_ops"] = [] if t0 is None else [
            o for o in ops
            if o.get("pair") == d.get("pair") and _ts(o) is not None
            and 0 <= (_ts(o) - t0).total_seconds() <= OP_WINDOW_S]
    return decisions


def round_trips(rows: list[dict]) -> list[RoundTrip]:
    """Walk decisions in time order, pairing each open with its close."""
    decisions = sorted(attach_operations(rows), key=lambda r: r.get("ts", ""))
    live: dict[str, RoundTrip] = {}
    trips: list[RoundTrip] = []

    for d in decisions:
        pair = d.get("pair") or "?"
        if d["event"] in OPEN_EVENTS:
            trip = RoundTrip(pair=pair, entry=d)
            _fill_entry(trip, d)
            trips.append(trip)
            if trip.opened:
                # A rejected entry never opened, so it must not occupy the slot
                # and swallow the next real close.
                live[pair] = trip
        else:
            trip = live.pop(pair, None)
            if trip is None:
                # A close with no open we know about: the week-1 orphan closed
                # by hand, or a refit-drop whose decision was never logged.
                trip = RoundTrip(pair=pair, entry={"ts": d.get("ts")})
                trips.append(trip)
            trip.close = d
            _fill_exit(trip, d)
    return trips


def _leg_key(pair: str, symbol: str) -> str:
    """Which side of "AVAX/SOL" this symbol is. Falls back to the client order
    id suffix (`...-a` / `...-b`) only if the base asset does not match."""
    names = [n.strip().upper() for n in (pair or "").split("/")]
    base = base_asset(symbol).upper()
    if base in names:
        return "a" if names.index(base) == 0 else "b"
    return base or symbol


def _fill_entry(trip: RoundTrip, d: dict) -> None:
    for op in d.get("_ops", []):
        sym = op.get("symbol") or ""
        key = _leg_key(trip.pair, sym)
        leg = trip.legs.get(key)
        if leg is None:
            leg = Leg(symbol=sym, base=base_asset(sym),
                      side=op.get("side") or "",
                      qty=abs(_f(op.get("executed_qty"))
                              or _f(op.get("quantity")) or 0.0))
            trip.legs[key] = leg
        leg.entry_price = _f(op.get("executed_price"))
        leg.entry_order_id = op.get("order_id")
        leg.entry_ts = _ts(op)
        leg.intended_entry = _f(d.get(f"price_{key}"))


def _fill_exit(trip: RoundTrip, d: dict) -> None:
    for op in d.get("_ops", []):
        sym = op.get("symbol") or ""
        key = _leg_key(trip.pair, sym)
        leg = trip.legs.get(key)
        if leg is None:
            leg = Leg(symbol=sym, base=base_asset(sym), side="", qty=0.0)
            trip.legs[key] = leg
        leg.exit_price = _f(op.get("executed_price"))
        leg.exit_order_id = op.get("order_id")
        leg.exit_ts = _ts(op)
        leg.intended_exit = _f(d.get(f"price_{key}"))


# ------------------------------------------------------------- slippage ---
def slippage_bps(intended: float | None, executed: float | None,
                 side: str) -> float | None:
    """Signed so POSITIVE always means adverse — we paid up on a buy or sold
    down on a sell. Averaging unsigned slippage hides exactly the asymmetry
    worth knowing about."""
    if not intended or executed is None or intended <= 0:
        return None
    direction = 1.0 if (side or "").upper() == "BUY" else -1.0
    return direction * (executed - intended) / intended * 1e4


def trip_slippage(trip: RoundTrip) -> list[float]:
    out = []
    for leg in trip.legs.values():
        entry = slippage_bps(leg.intended_entry, leg.entry_price, leg.side)
        # The closing order is the opposite side of the opening one.
        opposite = "SELL" if (leg.side or "").upper() == "BUY" else "BUY"
        exit_ = slippage_bps(leg.intended_exit, leg.exit_price, opposite)
        out += [v for v in (entry, exit_) if v is not None]
    return out


# -------------------------------------------------------------- summary ---
def summarise(trips: list[RoundTrip]) -> dict:
    done = [t for t in trips if t.opened and t.closed
            and t.gross_pnl is not None]
    pnl = [t.gross_pnl for t in done]
    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p <= 0]
    holds = [t.hold_hours for t in done if t.hold_hours is not None]
    slips = [s for t in trips for s in trip_slippage(t)]
    fees = [t.fees for t in done if t.fees is not None]
    notion = [t.notional for t in done if t.notional]

    reasons: dict[str, int] = {}
    for t in done:
        reasons[t.reason] = reasons.get(t.reason, 0) + 1

    # Self-diagnosis. A close decision that picked up no operations means the
    # join failed, and every downstream number is then silently missing that
    # trade rather than visibly wrong. Report it instead of absorbing it.
    closes = [t.close for t in trips if t.close is not None]
    orphan_closes = sum(1 for c in closes if not c.get("_ops"))

    out = {
        "round_trips": len(done),
        "never_opened": sum(1 for t in trips if not t.opened and t.entry),
        "still_open": sum(1 for t in trips if t.opened and not t.closed),
        "gross_pnl": round(sum(pnl), 4) if pnl else None,
        "win_rate": round(len(wins) / len(pnl), 4) if pnl else None,
        "mean_win": round(statistics.fmean(wins), 4) if wins else None,
        "mean_loss": round(statistics.fmean(losses), 4) if losses else None,
        "worst": round(min(pnl), 4) if pnl else None,
        "expectancy": round(statistics.fmean(pnl), 4) if pnl else None,
        "median_hold_h": round(statistics.median(holds), 2) if holds else None,
        "max_hold_h": round(max(holds), 2) if holds else None,
        "exit_reasons": reasons,
        "close_decisions": len(closes),
        "closes_with_no_operations": orphan_closes,
        "venue_gross_pnl": (round(sum(v), 4) if (v := [t.venue_pnl for t in done
                                                      if t.venue_pnl is not None])
                            else None),
        "slippage_bps_mean": round(statistics.fmean(slips), 2) if slips else None,
        "slippage_bps_median": (round(statistics.median(slips), 2)
                                if slips else None),
        "slippage_legs": len(slips),
    }
    if fees:
        out["fees_paid"] = round(sum(fees), 4)
        out["net_pnl"] = round(sum(pnl) - sum(fees), 4)
        out["fee_share_of_gross"] = (round(sum(fees) / sum(pnl), 4)
                                     if sum(pnl) else None)
        if notion:
            # Round-trip notional is entry + exit, hence the 2x.
            out["measured_fee_bps_per_side"] = round(
                sum(fees) / (2 * sum(notion)) * 1e4, 3)
            out["assumed_fee_bps_per_side"] = 5.0
    return out


# ------------------------------------------------------------------- I/O ---
# The venue's field names are not documented in the schema, and the CSV export
# that would have shown them comes back header-only. Accept the plausible
# spellings and say so loudly when none of them match, rather than returning a
# tidy zero that reads as "this cost nothing".
FEE_FIELDS = ("fee", "commission", "feeAmount", "feeCost", "tradeFee")
PRICE_FIELDS = ("filledPrice", "execPrice", "executedPrice", "price",
                "avgPrice", "tradePrice", "fillPrice")
QTY_FIELDS = ("filledQuantity", "execQty", "executedQty", "quantity", "qty",
              "filledQty", "size", "tradeQty")


def _pick(row: dict, names: tuple[str, ...]) -> float | None:
    for n in names:
        v = _f(row.get(n))
        if v is not None:
            return v
    return None


def _vwap(fills: list[dict]) -> float | None:
    """Volume-weighted average fill price, or the plain mean when the venue
    does not give a per-fill quantity. An order that filled in one print --
    which is all of ours so far -- makes the distinction moot, but a partial
    fill priced by simple mean would silently misstate the entry."""
    pairs = [(_pick(f, PRICE_FIELDS), _pick(f, QTY_FIELDS)) for f in fills]
    pairs = [(p, q) for p, q in pairs if p is not None]
    if not pairs:
        return None
    if all(q for _, q in pairs):
        num = sum(p * abs(q) for p, q in pairs)
        den = sum(abs(q) for _, q in pairs)
        return num / den if den else None
    return sum(p for p, _ in pairs) / len(pairs)


# A fill lands before the operation record that reports it: the agent writes
# the operation after preview -> submit -> readback, which is several
# rate-limited calls. Generous behind, tight ahead. Entries and exits on one
# symbol are at least a bar apart, so this cannot straddle two of ours.
FILL_WINDOW_BEFORE_S = 300.0
FILL_WINDOW_AFTER_S = 60.0


def fetch_symbol_fills(broker, symbols: list[str], stat: dict) -> dict:
    out: dict[str, list[dict]] = {}
    for sym in symbols:
        try:
            rows = broker.executions(symbol=sym)
        except Exception as exc:                       # noqa: BLE001
            print(f"  execution fetch failed for {sym}: {exc}", file=sys.stderr)
            stat["symbols_failed"] += 1
            rows = []
        if rows and stat["sample_fill_keys"] is None:
            stat["sample_fill_keys"] = sorted(rows[0])
        out[sym] = sorted(rows, key=lambda f: _f(f.get("createAt")) or 0.0)
        stat["fills_fetched"] += len(rows)
    return out


def attach_executions(trips: list[RoundTrip], broker) -> dict:
    """Match every leg to the venue's own fills, by symbol and time.

    Not by order id, which is the obvious way and does not work: `close_position`
    records `order_id: null` because the venue's close response carries no
    orderId, and it emits no `executed_price` either -- unlike `place_market`,
    which emits both. So the ledger alone cannot say what ANY exit was done at,
    and looking one up by order is impossible. Pulling each symbol's fills and
    assigning them by time is the only route, and it has the side benefit of
    working retroactively over history recorded before the agent is fixed.

    Fills are consumed as they are claimed, so two round trips on one symbol
    cannot both bank the same fill. Legs are processed in time order for the
    same reason.
    """
    stat = {"legs_priced": 0, "entry_prices": 0, "exit_prices": 0,
            "fills_fetched": 0, "fills_matched": 0, "legs_unmatched": 0,
            "symbols_failed": 0, "sample_fill_keys": None}

    symbols = sorted({l.symbol for t in trips for l in t.legs.values()
                      if l.symbol})
    pools = fetch_symbol_fills(broker, symbols, stat)

    events: list[tuple[datetime, Leg, str]] = []
    for trip in trips:
        for leg in trip.legs.values():
            if leg.entry_ts:
                events.append((leg.entry_ts, leg, "entry"))
            if leg.exit_ts:
                events.append((leg.exit_ts, leg, "exit"))
    events.sort(key=lambda e: e[0])

    claimed: set = set()
    for op_ts, leg, which in events:
        hits = []
        for f in pools.get(leg.symbol, []):
            key = f.get("transactionId") or id(f)
            if key in claimed:
                continue
            created = _f(f.get("createAt"))
            if created is None:
                continue
            lag = op_ts.timestamp() - created / 1000.0
            if -FILL_WINDOW_AFTER_S <= lag <= FILL_WINDOW_BEFORE_S:
                hits.append((key, f))
        if not hits:
            stat["legs_unmatched"] += 1
            continue
        for key, _ in hits:
            claimed.add(key)
        fills = [f for _, f in hits]
        stat["fills_matched"] += len(fills)

        fee = sum(abs(_pick(f, FEE_FIELDS) or 0.0) for f in fills)
        if fee:
            leg.fee = (leg.fee or 0.0) + fee
            stat["legs_priced"] += 1
        px = _vwap(fills)
        if which == "entry":
            if leg.entry_price is None and px is not None:
                leg.entry_price = px
                stat["entry_prices"] += 1
        else:
            if leg.exit_price is None and px is not None:
                leg.exit_price = px
                stat["exit_prices"] += 1
            rpnl = [_f(f.get("rpnl")) for f in fills]
            rpnl = [v for v in rpnl if v is not None]
            if rpnl:
                leg.venue_rpnl = sum(rpnl)
            if not leg.qty:
                leg.qty = sum(abs(_pick(f, QTY_FIELDS) or 0.0)
                              for f in fills) or leg.qty
    return stat


def funding_summary(broker, coin: str = "USDT") -> dict:
    """Group statement lines by type and total them.

    The venue's vocabulary for statement types is undocumented in the schema,
    so this fetches unfiltered and reports what actually came back rather than
    guessing at a magic string and silently returning zero — a zero that would
    read as "funding costs nothing" when it really means "we asked wrong".
    """
    try:
        rows = broker.statement(coin=coin)
    except Exception as exc:                            # noqa: BLE001
        return {"error": str(exc)[:300]}
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    parsed = 0
    for r in rows:
        kind = str(r.get("statementType") or r.get("type")
                   or r.get("bizType") or "unknown")
        # deltaAmount is what RapidX actually calls it, confirmed against the
        # row's own beforeAvailable/afterAvailable on 2026-08-02. The rest stay
        # as fallbacks in case a different statement type spells it otherwise.
        amt = _pick(r, ("deltaAmount", "delta", "amount", "change", "income",
                        "value", "realizedPnl", "cashFlow"))
        if amt is not None:
            parsed += 1
        totals[kind] = round(totals.get(kind, 0.0) + (amt or 0.0), 8)
        counts[kind] = counts.get(kind, 0) + 1
    out = {"lines": len(rows), "totals_by_type": totals, "counts": counts,
           "amounts_parsed": parsed}
    if rows and (parsed == 0 or not any(totals.values())):
        # Zero funding and an unreadable amount field look identical in a
        # total. Show the raw shape so the difference is decidable instead of
        # assumed -- "funding is free" is a claim that needs evidence.
        out["sample_row"] = {k: rows[0][k] for k in sorted(rows[0])}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", default=str(LEDGER))
    ap.add_argument("--no-api", action="store_true",
                    help="ledger only: skip fee and funding lookups")
    ap.add_argument("--json", metavar="PATH",
                    help="also write the full per-trade detail as JSON")
    args = ap.parse_args()

    rows = load_ledger(Path(args.ledger))
    trips = round_trips(rows)

    funding = None
    if not args.no_api:
        from deploy.ltp_broker import RapidXBroker      # noqa: PLC0415
        broker = RapidXBroker()
        stat = attach_executions(trips, broker)
        print("venue executions: " + "  ".join(f"{k}={v}" for k, v in stat.items()
                                               if k != "sample_fill_keys"))
        if stat["sample_fill_keys"]:
            print(f"  fill fields seen: {stat['sample_fill_keys']}")
        funding = funding_summary(broker)

    s = summarise(trips)
    print("=" * 62)
    print("fills report")
    print("=" * 62)
    for k, v in s.items():
        print(f"  {k:26s} {v}")
    if funding:
        print("\n  funding / statement")
        for k, v in funding.items():
            print(f"    {k:24s} {v}")

    print("\n  per round trip")
    for t in trips:
        if not (t.opened and t.closed):
            continue
        g = t.gross_pnl
        print(f"    {t.entry.get('ts', '?')[:16]}  {t.pair:10s} "
              f"{t.reason:10s} hold={t.hold_hours or 0:5.1f}h "
              f"gross={g if g is None else round(g, 2):>7} "
              f"fees={t.fees if t.fees is None else round(t.fees, 3)}")

    if args.json:
        Path(args.json).write_text(json.dumps({
            "summary": s,
            "funding": funding,
            "trips": [{
                "pair": t.pair, "entry_ts": t.entry.get("ts"),
                "close_ts": (t.close or {}).get("ts"), "reason": t.reason,
                "hold_hours": t.hold_hours, "gross_pnl": t.gross_pnl,
                "fees": t.fees, "net_pnl": t.net_pnl,
                "entry_z": t.entry.get("z"), "close_z": (t.close or {}).get("z"),
                "notional": t.notional,
                "slippage_bps": trip_slippage(t),
                "legs": {k: vars(l) for k, l in t.legs.items()},
            } for t in trips],
        }, indent=2, default=float))
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
