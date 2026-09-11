"""
deploy/universe_discover.py — find out what we are actually allowed to trade.

**There is no listing endpoint.** All 53 RapidX capabilities were dumped on
2026-09-10 and every market action takes a symbol as *input* — `klines`,
`ticker`, `orderbook`, `symbol-info`, `funding-rate`, `open-interest`,
`mark-price`. Nothing returns a list, and neither does anything under
`portfolio`. So the universe cannot be enumerated; it can only be **probed**.

That matters more than it sounds. For eight weeks this agent has traded a
hardcoded `CANDIDATES` list, seeded in July from the Phase I top-50 Binance
whitelist, and every statement we have made about "the universe" — pass rates,
breadth, the 0-of-55 regime finding — was measured against a set we inherited
rather than chose. The organizer confirmed on 2026-09-09 that **any instrument
orderable under the RapidX perp portfolio is eligible, crypto or not**, and
`OKX_PERP_CL_USDT` (WTI crude) came back `live` the next day. Nobody had asked.

`get-symbol-info` is the oracle. Three response classes were separated on
2026-09-10 using a deliberate control probe, and they are the whole basis of
this tool:

    RCLI12001  "Invalid RapidX symbol"     malformed -- never reached the venue
    RCLI22001  upstream 401011             well-formed, not supported
    PASS       + real_tool_call            live

Without the control (`BINANCE_PERP_FAKE_USDT`) the first two are
indistinguishable, and `CL-USDT-SWAP` — OKX's own name for the contract, which
RapidX rejects locally — looks exactly like "not available" when it is only
"wrong spelling". RapidX normalises to `OKX_PERP_<BASE>_USDT` and reports the
venue's name back in `originalSymbol`.

Read-only. It places no orders, touches no agent state, and decides nothing --
it writes a manifest for `universe_scan.py` to consume.

    python deploy/universe_discover.py
    python deploy/universe_discover.py --venues OKX --bases CL,BTC,ETH
    python deploy/universe_discover.py --out deploy/universe_manifest.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.ltp_agent import CANDIDATES                      # noqa: E402
from deploy.ltp_broker import RapidXBroker, RapidXError      # noqa: E402

DEFAULT_OUT = Path(__file__).resolve().parent / "universe_manifest.json"

# Error codes, from the 2026-09-10 probe. Classified rather than lumped
# together because "you spelled it wrong" and "the venue does not have it" lead
# to opposite next actions, and they are trivially confusable.
MALFORMED = "RCLI12001"
UNSUPPORTED = "RCLI22001"

VENUES = ("BINANCE", "OKX")

# Everything the live book already trades, so the manifest always covers the
# current universe and a diff against it is meaningful.
CRYPTO_BASES = sorted({s.split("_")[2] for pair in CANDIDATES for s in pair})

# Candidates beyond the live book. The crypto names are the sector groups from
# `universe_scan.py`; the rest are the interesting part.
#
# **The non-crypto list is the weak link and it is deliberately short.** We
# have no listing endpoint, so these are names to TEST, not names we know
# exist, and guessing a long list of plausible tickers would dress speculation
# up as discovery. `CL` is the only one confirmed live (2026-09-10). The proper
# source is OKX's own public instruments endpoint, which returns every
# `*-USDT-SWAP` and maps mechanically onto `OKX_PERP_<BASE>_USDT`; until
# somebody pulls that list, extend this with `--bases`.
EXTRA_BASES = [
    # crypto sectors already scanned
    "DASH", "ATOM", "SUI", "APT", "VET", "TIA", "INJ", "FET", "WLD",
    "1000PEPE", "WIF", "COMP", "MKR", "CRV", "SUSHI", "LDO", "RPL",
    "BAND", "PYTH", "ARB", "OP", "STRK", "BNB", "OKB",
    # non-crypto: CL is confirmed, the others are hypotheses
    "CL",
]


def probe(broker: RapidXBroker, symbol: str) -> dict:
    """One symbol -> {'state': live|unsupported|malformed|error, ...spec}.

    Never caches a failure and never raises: a discovery sweep that dies on
    the first bad name would report the venue as empty, which is exactly the
    wrong conclusion to draw from a typo.
    """
    try:
        info = broker.symbol_info(symbol)
    except RapidXError as exc:
        code = getattr(exc.result, "code", "")
        state = ("malformed" if code == MALFORMED else
                 "unsupported" if code == UNSUPPORTED else "error")
        return {"symbol": symbol, "state": state, "code": code,
                "message": getattr(exc.result, "message", "")[:160]}
    except Exception as exc:                                 # noqa: BLE001
        return {"symbol": symbol, "state": "error", "code": "",
                "message": str(exc)[:160]}
    if not info:
        return {"symbol": symbol, "state": "error", "code": "",
                "message": "empty symbol-info payload"}
    return {"symbol": symbol, "state": "live",
            "original": info.get("originalSymbol"),
            "venue_state": info.get("state"),
            "contract_size": info.get("contractSize"),
            "min_size": info.get("minSize"),
            "min_notional": info.get("minNotional"),
            "tick_size": info.get("tickSize"),
            "default_leverage": info.get("defaultLeverage"),
            "safe_leverage": info.get("safeLeverage")}


def sweep(broker: RapidXBroker, venues, bases) -> list[dict]:
    out = []
    total = len(venues) * len(bases)
    for i, venue in enumerate(venues):
        for j, base in enumerate(bases):
            symbol = f"{venue}_PERP_{base}_USDT"
            row = probe(broker, symbol)
            row["venue"], row["base"] = venue, base
            out.append(row)
            n = i * len(bases) + j + 1
            print(f"  [{n:>3}/{total}] {symbol:<28} {row['state']}"
                  f"{'' if row['state'] == 'live' else '  ' + row.get('code', '')}",
                  flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="probe which symbols are live")
    ap.add_argument("--venues", default=",".join(VENUES),
                    help="comma-separated, e.g. BINANCE,OKX")
    ap.add_argument("--bases", default=None,
                    help="comma-separated base assets; default is the live "
                         "book plus the candidate list in this file")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    venues = [v.strip().upper() for v in args.venues.split(",") if v.strip()]
    bases = ([b.strip().upper() for b in args.bases.split(",") if b.strip()]
             if args.bases else sorted(set(CRYPTO_BASES) | set(EXTRA_BASES)))

    print(f"probing {len(venues) * len(bases)} symbols "
          f"({len(venues)} venues x {len(bases)} bases); "
          f"rate-limited by the broker ...")
    rows = sweep(RapidXBroker(), venues, bases)

    live = [r for r in rows if r["state"] == "live"]
    by_state: dict[str, int] = {}
    for r in rows:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1

    args.out.write_text(json.dumps(
        {"probed": len(rows), "by_state": by_state, "symbols": rows},
        indent=1), encoding="utf-8")

    print(f"\n{'-' * 60}")
    for state, n in sorted(by_state.items(), key=lambda kv: -kv[1]):
        print(f"  {state:<14}{n:>4}")
    print(f"\nLIVE by venue:")
    for venue in venues:
        got = sorted(r["base"] for r in live if r["venue"] == venue)
        print(f"  {venue:<9}{len(got):>4}  {', '.join(got)}")
    # A base on one venue and not the other is the interesting row: it is
    # breadth we cannot reach without moving, and the venue choice is made once.
    only = {v: {r["base"] for r in live if r["venue"] == v} for v in venues}
    if len(venues) == 2:
        a, b = venues
        print(f"\n  only on {a}: {sorted(only[a] - only[b])}")
        print(f"  only on {b}: {sorted(only[b] - only[a])}")
    print(f"\nmanifest -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
