"""
Live open/close verification for the LTP RapidX broker.

Exercises the exact path the agent uses in production — start automation,
place one small MARKET order, then close it through the FIXED
`close_position` — and asserts the position actually goes flat. Its reason
to exist: the v0.x close built the reduceOnly close from the strategy's
intended side, which a one-way (NET) account rejects with NO_POSITION, so a
close that never closed reported success. This script is how we prove that
can't happen anymore, and how we re-verify after a key rotation or reboot.

It trades REAL (small) size on whatever portfolio LTP_PORTFOLIO_ID points at,
so keep that pointed at the funded UAT test portfolio. One leg, opened and
immediately closed; notional is sized to just clear the symbol's minNotional.

    source /root/ltp.env
    python deploy/verify_close.py                 # ETCUSDT, live
    python deploy/verify_close.py --symbol KASUSDT
    python deploy/verify_close.py --dry-run        # sizing only, no orders

Requires LTP_AUTOMATION_CONSENT_TEXT (the human-authored consent), same as
the agent — the broker will not open an automation session without it.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.ltp_broker import RapidXBroker, RapidXError          # noqa: E402


def _op_printer(rec: dict) -> None:
    print(f"    [operation] {rec}")


def _size_to_min_notional(broker: RapidXBroker, symbol: str,
                          price: float) -> float:
    """Smallest lot-aligned qty whose notional clears minNotional (+2%)."""
    info = broker.symbol_info(symbol)
    min_notional = float(info.get("minNotional") or 0.0)
    lot = float(info.get("lotSize") or info.get("stepSize") or 0.0)
    raw = (min_notional / price) * 1.02 if price > 0 else 0.0
    if lot > 0:
        qty = math.ceil(raw / lot) * lot
        decimals = max(0, -int(math.floor(math.log10(lot) + 1e-9)))
        qty = round(qty, decimals)
    else:
        qty = round(raw, 6)
    return qty


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbol", default="ETCUSDT",
                    help="whitelist symbol to open and close (default ETCUSDT)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show self-check, equity and sizing; place no orders")
    args = ap.parse_args()

    symbol = args.symbol.upper()
    broker = RapidXBroker(on_operation=_op_printer)

    print(f"== verify_close: {symbol} "
          f"({'DRY-RUN' if args.dry_run else 'LIVE'}) ==")
    print(f"   portfolio: {broker.portfolio_id or '(CLI default)'}")

    # 1. self-check must pass before we touch anything.
    sc = broker.self_check()
    verdict = (sc.status or sc.data.get("status") if isinstance(sc.data, dict)
               else sc.status)
    print(f"1. self-check: ok={sc.ok} status={sc.status} "
          f"code={sc.code} {sc.message}")
    if not sc.ok:
        print("   ABORT: self-check failed (source /root/ltp.env?).")
        return 2

    # 2. equity readback.
    equity_before = broker.equity_usdt()
    print(f"2. equity before: {equity_before:.2f} USDT")

    # 3. price + sizing.
    price = broker.mark_price(symbol)
    qty = _size_to_min_notional(broker, symbol, price)
    notional = qty * price
    info = broker.symbol_info(symbol)
    print(f"3. mark={price:.6f}  qty={qty}  ~notional={notional:.2f} USDT  "
          f"(minNotional={info.get('minNotional')}, "
          f"lot={info.get('lotSize') or info.get('stepSize')})")
    if qty <= 0:
        print("   ABORT: computed qty is zero; check symbol_info.")
        return 2

    if args.dry_run:
        print("DRY-RUN: sizing only, no orders placed. OK.")
        return 0

    consent = os.environ.get("LTP_AUTOMATION_CONSENT_TEXT", "").strip()
    if not consent:
        print("   ABORT: LTP_AUTOMATION_CONSENT_TEXT is not set. The human "
              "operator must author the automation consent (README_ltp.md).")
        return 2

    # 4. automation session (small caps for a single test leg).
    sid = broker.start_automation(
        symbols=[symbol], max_per_order="200", max_total="400",
        expires_s=3600, consent_text=consent)
    print(f"4. automation session: {sid}")

    coid = f"verify-{int(time.time())}"
    broker.op_context = {"decision": "verify_open", "pair": symbol}

    # 5. OPEN: long one leg.
    print(f"5. placing MARKET BUY {qty} {symbol} (LONG) coid={coid} ...")
    placed = broker.place_market(
        symbol=symbol, side="BUY", position_side="LONG", qty=qty,
        max_notional=notional * 1.05, client_order_id=coid)
    state = placed.get("orderState") or placed.get("status")
    print(f"   placed: state={state} "
          f"execQty={placed.get('executedQty')} "
          f"execPx={placed.get('executedAvgPrice')}")

    # 6. confirm the position is actually open before we test the close.
    live = broker._live_position(symbol)
    if live is None:
        print("   NOTE: no live position yet — order may be resting "
              "(post-close market orders fill at next open). The close test "
              "needs an open position; re-run during market hours.")
        broker.op_context = {}
        return 3
    print(f"6. live position: side={live.get('positionSide')} "
          f"qty={broker._position_qty(live)}")

    # 7. CLOSE via the FIXED path, then read back.
    broker.op_context = {"decision": "verify_close", "pair": symbol}
    print("7. closing via close_position() ...")
    broker.close_position(symbol, "LONG", max_notional=notional * 2)
    broker.op_context = {}

    after = broker._live_position(symbol)
    equity_after = broker.equity_usdt()
    print(f"8. live position after: "
          f"{'FLAT' if after is None else after}")
    print(f"   equity after: {equity_after:.2f} USDT")

    if after is None:
        print("\nPASS: opened and closed cleanly; symbol is FLAT.")
        return 0
    resid = broker._position_qty(after)
    if abs(resid) > 0:
        print(f"\nFAIL: position still open (residual qty {resid}). The close "
              "did not flatten — do NOT trust the agent's kill switch until "
              "this is understood.")
        return 1
    print("\nPASS (resting): close submitted; residual shows zero qty.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RapidXError as exc:
        print(f"\nFAIL: RapidX error — {exc}")
        sys.exit(1)
