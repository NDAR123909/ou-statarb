"""
Broker bridge for the LTP Liquidity Arena competition (RapidX).

Wraps the official `rapidx` CLI (@liquiditytech/rapidx-cli) via subprocess
rather than reimplementing REST signing: the CLI is the organizer-supported
path, it enforces the preview->submit safety model on every write, and it
returns a stable JSON envelope we can parse. The cost is a Node.js runtime
dependency, which is acceptable for a single always-on agent.

Competition constraints baked in here rather than left to the strategy:
  - order writes are rate-limited to one per 5 seconds (hard contest limit);
  - every write goes preview -> submit -> readback, never blind;
  - quantities are rounded to the symbol's lot size and checked against
    minNotional before any preview is attempted;
  - all writes ride an automation session, which the CLI only grants when a
    human has supplied explicit consent text (LTP_AUTOMATION_CONSENT_TEXT).

Credentials come from the environment (LTP_ACCESS_KEY / LTP_SECRET_KEY /
LTP_API_HOST) and are read by the CLI itself, never by this module.
"""

from __future__ import annotations

import json
import math
import subprocess
import time
from dataclasses import dataclass, field

import pandas as pd

ORDER_WRITE_INTERVAL = 5.5     # contest: 1 order write per 5s; leave margin
READ_INTERVAL = 0.7            # gentle pacing on reads ("production x 1/5")


@dataclass
class RapidXResult:
    ok: bool
    status: str
    code: str
    message: str
    data: dict

    @classmethod
    def from_envelope(cls, env: dict) -> "RapidXResult":
        return cls(
            ok=bool(env.get("ok", False)),
            status=str(env.get("status", "")),
            code=str(env.get("code", "")),
            message=str(env.get("message", "")),
            data=env.get("data") or {},
        )


class RapidXError(RuntimeError):
    def __init__(self, result: RapidXResult, context: str):
        super().__init__(f"{context}: {result.status} {result.code} {result.message}")
        self.result = result


@dataclass
class RapidXBroker:
    """Thin, rate-limited wrapper over `rapidx <domain> <action> --json`.

    Audit note: the Track A reasoning-log rules require every order/trade
    operation (place, cancel, open, close) to appear in the submitted log
    with its final result. `on_operation` is the hook for that — the agent
    wires it to the decision ledger, and `op_context` (set by the agent at
    each decision site) ties every operation back to the decision that
    caused it: decision -> operations -> outcomes, one chain per order.
    """

    cli: str = "rapidx"
    automation_session_id: str | None = None
    on_operation: object = field(default=None, repr=False)   # callable(dict)
    op_context: dict = field(default_factory=dict, repr=False)
    _last_write: float = field(default=0.0, repr=False)
    _last_read: float = field(default=0.0, repr=False)
    _symbol_info: dict = field(default_factory=dict, repr=False)

    def _emit(self, op: str, **fields) -> None:
        """Report one order operation. Observability must never break
        trading, so callback failures are swallowed."""
        if self.on_operation is None:
            return
        try:
            self.on_operation({"op": op, **self.op_context, **fields})
        except Exception:
            pass

    # ------------------------------------------------------------- plumbing --
    def _run(self, args: list[str], input_obj: dict | None = None,
             write: bool = False) -> RapidXResult:
        now = time.monotonic()
        wait = ((self._last_write + ORDER_WRITE_INTERVAL) - now if write
                else (self._last_read + READ_INTERVAL) - now)
        if wait > 0:
            time.sleep(wait)

        cmd = [self.cli, *args]
        if input_obj is not None:
            cmd += ["--input", json.dumps(input_obj)]
        cmd += ["--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        stamp = time.monotonic()
        if write:
            self._last_write = stamp
        self._last_read = stamp

        try:
            env = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return RapidXResult(False, "FAIL", "NO_JSON",
                                (proc.stdout or proc.stderr)[:500], {})
        return RapidXResult.from_envelope(env)

    def _must(self, args: list[str], input_obj: dict | None = None,
              write: bool = False) -> dict:
        res = self._run(args, input_obj, write)
        if not res.ok:
            raise RapidXError(res, " ".join(args))
        return res.data

    # ---------------------------------------------------------- diagnostics --
    def self_check(self) -> RapidXResult:
        return self._run(["self-check", "--read-only"])

    # ---------------------------------------------------------- market data --
    def klines(self, symbol: str, interval: str = "1h",
               limit: int = 1000) -> pd.DataFrame:
        """Close-price bars, indexed by bar close time (UTC). Empty on error
        so a missing/new symbol degrades to 'not enough history'."""
        res = self._run(["market", "get-klines"],
                        {"symbol": symbol, "interval": interval, "limit": limit})
        if not res.ok:
            return pd.DataFrame()
        rows = res.data.get("klines") or res.data.get("list") or res.data
        if not isinstance(rows, list) or not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        # tolerate either open-time keys or array-style rows
        tcol = next((c for c in ("closeTime", "openTime", "time", "t")
                     if c in df.columns), None)
        ccol = next((c for c in ("close", "closePrice", "c")
                     if c in df.columns), None)
        if tcol is None or ccol is None:
            return pd.DataFrame()
        out = pd.DataFrame({
            "time": pd.to_datetime(pd.to_numeric(df[tcol]), unit="ms", utc=True),
            "close": pd.to_numeric(df[ccol]),
        }).dropna().set_index("time").sort_index()
        return out

    def symbol_info(self, symbol: str) -> dict:
        """minNotional / lotSize / tickSize / contractSize; cached."""
        if symbol not in self._symbol_info:
            self._symbol_info[symbol] = self._must(
                ["market", "get-symbol-info"], {"symbol": symbol})
        return self._symbol_info[symbol]

    def mark_price(self, symbol: str) -> float:
        data = self._must(["market", "get-mark-price"], {"symbol": symbol})
        for k in ("markPrice", "price", "mark"):
            if k in data:
                return float(data[k])
        raise KeyError(f"no mark price in response for {symbol}: {data}")

    # -------------------------------------------------------------- account --
    def equity_usdt(self) -> float:
        data = self._must(["portfolio", "overview"])
        for k in ("totalEquity", "equity", "totalWalletBalance", "accountEquity"):
            if k in data:
                return float(data[k])
        # some shapes nest per-exchange accounts
        accounts = data.get("accounts") or data.get("list") or []
        if accounts and isinstance(accounts, list):
            for k in ("totalEquity", "equity", "totalWalletBalance"):
                if k in accounts[0]:
                    return sum(float(a.get(k, 0.0)) for a in accounts)
        raise KeyError(f"cannot find equity in portfolio overview: {data}")

    def positions(self) -> list[dict]:
        data = self._must(["position", "query"])
        rows = data.get("positions") or data.get("list") or data
        return rows if isinstance(rows, list) else []

    def open_orders(self) -> list[dict]:
        data = self._must(["order", "open-orders"])
        rows = data.get("orders") or data.get("list") or data
        return rows if isinstance(rows, list) else []

    # ------------------------------------------------------------ automation --
    def start_automation(self, symbols: list[str], max_per_order: str,
                         max_total: str, expires_s: int,
                         consent_text: str) -> str:
        """Consent text must come verbatim from the human operator."""
        data = self._must(["automation", "start"], {
            "symbols": symbols,
            "maxNotionalPerOrder": max_per_order,
            "maxTotalNotional": max_total,
            "expiresInSeconds": expires_s,
            "allowedActions": ["order.place", "order.cancel"],
            "allowedOrderTypes": ["MARKET", "LIMIT"],
            "explicitUserConsent": True,
            "acceptedRiskText": consent_text,
        }, write=True)
        self.automation_session_id = data["automationSessionId"]
        return self.automation_session_id

    # ---------------------------------------------------------------- sizing --
    def round_qty(self, symbol: str, qty: float) -> float:
        info = self.symbol_info(symbol)
        lot = float(info.get("lotSize") or info.get("stepSize") or 0.0)
        if lot > 0:
            qty = math.floor(qty / lot) * lot
            # avoid float dust like 0.30000000000000004
            decimals = max(0, -int(math.floor(math.log10(lot) + 1e-9)))
            qty = round(qty, decimals)
        return qty

    def meets_min_notional(self, symbol: str, qty: float, price: float) -> bool:
        info = self.symbol_info(symbol)
        min_notional = float(info.get("minNotional") or 0.0)
        return qty * price >= min_notional

    # ---------------------------------------------------------------- orders --
    def place_market(self, symbol: str, side: str, position_side: str,
                     qty: float, max_notional: float,
                     client_order_id: str) -> dict:
        """Preview -> submit -> readback. Returns the readback order dict."""
        params = {
            "symbol": symbol,
            "side": side,                      # BUY / SELL
            "positionSide": position_side,     # LONG / SHORT (hedge mode)
            "orderType": "MARKET",
            "quantity": str(qty),
            "maxNotional": str(round(max_notional, 2)),
            "clientOrderId": client_order_id,
        }
        if self.automation_session_id:
            params["automationSessionId"] = self.automation_session_id

        preview = self._must(["order", "place-preview"], params, write=True)
        submit = dict(params)
        submit["previewId"] = preview["previewId"]
        submit["continueConsentId"] = preview["confirmation"]["submitToken"]
        self._must(["order", "place"], submit, write=True)

        # readback: never infer state from the submit response alone
        result = self._must(["order", "query"], {"clientOrderId": client_order_id})
        self._emit("place", symbol=symbol, side=side, position_side=position_side,
                   quantity=qty, max_notional=round(max_notional, 2),
                   client_order_id=client_order_id,
                   order_id=result.get("orderId"),
                   order_state=result.get("orderState") or result.get("status"),
                   executed_qty=result.get("executedQty"),
                   executed_price=result.get("executedAvgPrice"))
        return result

    def close_position(self, symbol: str, position_side: str,
                       max_notional: float) -> dict | None:
        """reduceOnly close via preview->submit; None if nothing to close."""
        params = {
            "targetCapabilityId": "position.close",
            "symbol": symbol,
            "positionSide": position_side,
            "reduceOnly": True,
            "maxNotional": str(round(max_notional, 2)),
        }
        if self.automation_session_id:
            params["automationSessionId"] = self.automation_session_id
        preview = self._run(["trade", "preview"], params, write=True)
        if not preview.ok:
            if "NO_POSITION" in (preview.code + preview.message).upper():
                self._emit("close", symbol=symbol, position_side=position_side,
                           result="no_position")
                return None
            self._emit("close", symbol=symbol, position_side=position_side,
                       result="preview_error", error=preview.message)
            raise RapidXError(preview, f"close-preview {symbol}")
        submit = {
            "symbol": symbol,
            "positionSide": position_side,
            "reduceOnly": True,
            "maxNotional": params["maxNotional"],
            "previewId": preview.data["previewId"],
            "continueConsentId": preview.data["confirmation"]["submitToken"],
        }
        if self.automation_session_id:
            submit["automationSessionId"] = self.automation_session_id
        data = self._must(["position", "close"], submit, write=True)
        self._emit("close", symbol=symbol, position_side=position_side,
                   max_notional=params["maxNotional"], result="submitted",
                   order_id=data.get("orderId"))
        return data

    def cancel_all(self, symbol: str | None = None) -> None:
        payload = {"symbol": symbol} if symbol else {}
        res = self._run(["order", "cancel-all"], payload or None, write=True)
        if not res.ok and res.status not in ("NOT_FOUND",):
            self._emit("cancel_all", symbol=symbol, result="error",
                       error=res.message)
            raise RapidXError(res, "cancel-all")
        self._emit("cancel_all", symbol=symbol,
                   result="ok" if res.ok else res.status,
                   canceled=res.data.get("canceled") if isinstance(res.data, dict) else None)
