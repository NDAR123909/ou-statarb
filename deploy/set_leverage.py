"""
deploy/set_leverage.py — set every whitelist symbol's leverage to a target
(default 2x) to comply with the competition's max-2x-opening-leverage rule.

RapidX defaults symbols to 5x and the agent never changed it, so a fresh open
would use 5x — a violation. This sets all CANDIDATES symbols to <=2x up front,
so any pair the selector later picks is already compliant. Idempotent, so it's
safe to re-run (e.g., if the venue ever resets a symbol's leverage).

    set -a; source /root/ltp.env; set +a
    python deploy/set_leverage.py                 # 2x on all whitelist symbols
    python deploy/set_leverage.py --dry-run       # report current leverage only
    python deploy/set_leverage.py --leverage 2

position.set-leverage is a preview->submit write; the preview returns the
consent token that authorizes the submit, so a human-run one-off needs no
automation session. If the account requires one, the FIRST symbol's error will
say so and it aborts immediately (rather than hammering all 28) so we adjust.

At the contest's 1-write-per-5s limit this takes a few minutes for 28 symbols
(two writes each). Let it run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.ltp_broker import RapidXBroker, RapidXError          # noqa: E402
from deploy.ltp_agent import CANDIDATES                          # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="set whitelist leverage")
    ap.add_argument("--leverage", type=int, default=2,
                    help="target leverage (default 2, the contest max)")
    ap.add_argument("--dry-run", action="store_true",
                    help="report each symbol's current leverage; set nothing")
    args = ap.parse_args()

    broker = RapidXBroker()
    symbols = sorted({t for p in CANDIDATES for t in p})
    print(f"== set-leverage: {len(symbols)} whitelist symbols -> "
          f"{args.leverage}x ({'DRY-RUN' if args.dry_run else 'LIVE'}) ==")

    ok: list[str] = []
    failed: list[str] = []
    for i, sym in enumerate(symbols):
        try:
            before = broker.get_leverage(sym)
        except RapidXError as exc:
            before = f"?({exc})"

        if args.dry_run:
            print(f"  {sym}: current = {before}x")
            continue

        try:
            broker.set_leverage(sym, args.leverage)
            after = broker.get_leverage(sym)
            print(f"  {sym}: {before}x -> {after}x  OK")
            ok.append(sym)
        except RapidXError as exc:
            print(f"  {sym}: SET FAILED — {exc}")
            failed.append(sym)
            if i == 0:
                print("\nABORT: the first symbol failed, so stopping before "
                      "hammering the rest. Paste this — the error tells us "
                      "whether it needs an automation session or something "
                      "else, and we adjust.")
                return 2

    if args.dry_run:
        return 0
    print(f"\ndone: {len(ok)} set to {args.leverage}x, {len(failed)} failed"
          + (f" — {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RapidXError as exc:
        print(f"\nFAIL: {exc}")
        sys.exit(1)
