"""
deploy/status.py — read-only health & position snapshot for the LTP agent.

One command, one picture: service uptime, live equity vs the drawdown peak
and the kill-switch level, the active pairs and where their spreads sit
relative to the entry/exit/stop bands, live positions, and the last few
decisions from the ledger. Meant to be run any time you SSH in — or pasted
to a collaborator — to answer "is it alive, is it safe, what is it doing?"
without reading raw logs.

Deliberately inert: it opens NO automation session and calls only read
endpoints (portfolio overview, positions, marks). It never previews, places,
cancels, or closes anything, and it makes no AI calls — so running it can
neither move the book nor touch the organizer-AI budget. That keeps it clear
of the Track A trading/AI rules: it is an operator's dashboard, not a trader.

    source /root/ltp.env
    python deploy/status.py                 # full snapshot
    python deploy/status.py --ledger 15     # more decision history
    python deploy/status.py --no-marks      # skip live z (no mark calls)
    python deploy/status.py --json          # machine-readable
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.ltp_broker import RapidXBroker, RapidXError          # noqa: E402
from deploy.ltp_agent import AgentConfig, _LEDGER_PATH, load_state  # noqa: E402

ELIMINATION_FLOOR = 800.0     # contest: equity < 800 USDT (NAV<0.8) = out
# Sentinel states in which the news gate is DOWN rather than merely quiet.
DEGRADED_GATE = ("no_client", "quota", "api_error", "parse_error")
# Mirrors ltp_agent.NEWS_STALE_H: the sentinel refreshes hourly, so a
# verdict older than this did not screen the bar it is shown against.
from deploy.ltp_agent import NEWS_STALE_H                        # noqa: E402


def _systemd(unit: str = "ltp-agent") -> dict | None:
    """Best-effort service state; None if systemd isn't reachable."""
    try:
        out = subprocess.run(
            ["systemctl", "show", unit, "-p", "ActiveState", "-p", "SubState",
             "-p", "ActiveEnterTimestamp", "-p", "NRestarts", "-p", "MainPID"],
            capture_output=True, text=True, timeout=5)
        if out.returncode != 0:
            return None
        return dict(l.split("=", 1) for l in out.stdout.splitlines() if "=" in l)
    except Exception:
        return None


def bars_to_refit(bar: int, every: int) -> int:
    """Bars until the next refit. 0 means "on the very next bar".

    The agent checks `state["bar"] % refit_every_bars == 0` at the TOP of an
    iteration and increments `bar` at the bottom, so the persisted value is the
    one the next iteration will test. At an exact multiple the refit is
    therefore imminent, not a full cycle away.

    This used to render `nxt or every`, which turned that 0 into `24` and told
    the operator to wait a day when the answer was "next bar". It cost a round
    of debugging on 2026-08-14 after a restart landed on bar 432, which is
    where a cosmetic bug stops being cosmetic.
    """
    return 0 if every <= 0 else (every - bar % every) % every


def _age_hours(stamp: str | None, now: datetime | None = None) -> float | None:
    """Hours since an ISO timestamp, or None if absent/unparseable."""
    try:
        t = datetime.fromisoformat(str(stamp))
    except (TypeError, ValueError):
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return ((now or datetime.now(timezone.utc)).timestamp() - t.timestamp()) / 3600.0


def _ai_spend() -> dict:
    """Current-period AI spend against the organizer's floor.

    The budget has two ends and we only ever watched one. On 2026-08-12 the
    organizer threatened disqualification for spend below USD 1 in a period,
    and the daily glance showed nothing about it -- the same shape of blind
    spot as the news gate before it got a line here. Imported lazily so a
    broken gateway degrades this line rather than the whole report.
    """
    try:
        from deploy.ai_deep_review import (AI_SPEND_FLOOR, FLOOR_GRACE_H,
                                           floor_state, key_info,
                                           period_age_hours)
    except Exception as exc:                                 # noqa: BLE001
        return {"spend": None, "floor": 1.0, "state": "unknown",
                "error": str(exc)[:120]}
    info = key_info() or {}
    spend = info.get("spend")
    spend = None if spend is None else float(spend)
    return {"spend": spend, "floor": AI_SPEND_FLOOR,
            "state": floor_state(spend, info),
            "period_age_h": period_age_hours(info),
            "grace_h": FLOOR_GRACE_H}


# Advisory events that flood the tail without being decisions. The review
# layer writes ~380 rows in one nightly pass, which buried enter/exit/stop
# entirely -- the glance showed 20 of 20 rows as `ai_deep_review` and the
# operator could no longer see what the agent had actually done. Hidden from
# the tail, still counted in the tally.
GLANCE_HIDE = ("ai_deep_review",)


def _tail_ledger(path: str, n: int,
                 hide: tuple[str, ...] = GLANCE_HIDE) -> tuple[list[dict], dict]:
    """Last n DECISION records, plus a whole-file tally over everything."""
    p = Path(path)
    if not p.exists():
        return [], {}
    recs = []
    for line in p.read_text().splitlines():
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    tally: dict = {}
    for r in recs:
        ev = r.get("event", "?")
        tally[ev] = tally.get(ev, 0) + 1
    shown = [r for r in recs if r.get("event") not in hide]
    return shown[-n:], tally


def _z_for_pair(broker: RapidXBroker, pair: dict, marks: dict) -> float | None:
    """Live spread z-score from the pair's fitted model, or None on any gap."""
    a, b = pair.get("a"), pair.get("b")
    try:
        pa = marks.get(a) or broker.mark_price(a)
        pb = marks.get(b) or broker.mark_price(b)
        marks[a], marks[b] = pa, pb
        sigma = float(pair["sigma"])
        if sigma <= 0:
            return None
        spread = math.log(pa) - float(pair["beta"]) * math.log(pb)
        return (spread - float(pair["mu"])) / sigma
    except (RapidXError, KeyError, ValueError, ZeroDivisionError):
        return None


def build_report(cfg: AgentConfig, use_marks: bool, ledger_n: int) -> dict:
    state = load_state(cfg.state_path)
    broker = RapidXBroker()               # no automation session, reads only

    rep: dict = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}

    # --- account / kill switch ---
    try:
        equity = broker.equity_usdt()
        rep["equity"] = round(equity, 2)
    except RapidXError as exc:
        rep["equity"] = None
        rep["equity_error"] = str(exc)
        equity = None

    peak = float(state.get("peak_equity") or 0.0)
    rep["peak_equity"] = round(peak, 2) if peak > 0 else None
    rep["halted"] = bool(state.get("halted"))
    rep["bar"] = state.get("bar", 0)
    rep["refit_every_bars"] = cfg.refit_every_bars
    if peak > 0:
        kill_level = peak * (1.0 - cfg.dd_halt)
        rep["kill_level"] = round(kill_level, 2)
        if equity is not None:
            rep["drawdown_pct"] = round((1.0 - equity / peak) * 100.0, 2)
            rep["headroom_to_kill"] = round(equity - kill_level, 2)
            rep["headroom_to_floor"] = round(equity - ELIMINATION_FLOOR, 2)

    # --- positions (live) ---
    try:
        positions = [p for p in broker.positions()
                     if abs(broker._position_qty(p)) > 0]
    except RapidXError as exc:
        positions = []
        rep["positions_error"] = str(exc)
    rep["open_positions"] = [
        {"sym": p.get("sym") or p.get("symbol"),
         "side": p.get("positionSide"),
         "qty": broker._position_qty(p),
         "value": p.get("positionValue"),
         "uPnL": p.get("unrealizedPNL")}
        for p in positions]

    # --- active pairs ---
    marks: dict = {}
    pairs_out = []
    for key, pair in state.get("pairs", {}).items():
        a, b = pair.get("a", ""), pair.get("b", "")
        name = f"{a.split('_')[2]}/{b.split('_')[2]}" if "_" in a else key
        side = pair.get("side", 0)
        z = _z_for_pair(broker, pair, marks) if use_marks else None
        entry_z = float(pair.get("entry_z", 0) or 0)
        exit_z = float(pair.get("exit_z", 0) or 0)
        flag = ""
        if z is not None:
            if side == 0:
                blocked = pair.get("blocked", 0)
                if entry_z < abs(z) < cfg.stop_z and \
                        not (blocked == +1 and z < 0) and \
                        not (blocked == -1 and z > 0):
                    flag = "ENTRY-READY"
            else:
                if abs(z) < exit_z:
                    flag = "AT/NEAR EXIT"
                elif (side > 0 and z < -cfg.stop_z) or \
                     (side < 0 and z > cfg.stop_z):
                    flag = "AT STOP"
        pairs_out.append({
            "pair": name,
            "side": {0: "FLAT", 1: "LONG-SPREAD", -1: "SHORT-SPREAD"}.get(side, side),
            "hold_bars": pair.get("hold", 0),
            "z": None if z is None else round(z, 2),
            "entry_z": round(entry_z, 2), "exit_z": round(exit_z, 2),
            "stop_z": cfg.stop_z,
            "half_life_h": round(float(pair.get("half_life", 0) or 0), 1),
            "beta": round(float(pair.get("beta", 0) or 0), 3),
            "blocked": pair.get("blocked", 0),
            "flag": flag,
        })
    rep["pairs"] = pairs_out

    gate_ts = (state.get("news_gate") or {}).get("ts")
    rep["news_gate_age_h"] = _age_hours(gate_ts)

    rep["ai_spend"] = _ai_spend()

    # --- ledger ---
    recent, tally = _tail_ledger(_LEDGER_PATH, ledger_n)
    rep["ledger_tally"] = tally
    rep["recent"] = recent

    # News-gate health. The sentinel fails open, so a dead gate does not stop
    # trading — which is exactly why it has to be visible here.
    rep["news_gate"] = state.get("news_gate") or {}

    rep["service"] = _systemd()
    return rep


def _print_human(rep: dict) -> None:
    def line(label, val):
        print(f"  {label:<16}{val}")

    print("=" * 62)
    print(f"LTP agent status  —  {rep['ts']}")
    print("=" * 62)

    svc = rep.get("service")
    if svc:
        since = svc.get("ActiveEnterTimestamp", "").strip()
        line("service", f"{svc.get('ActiveState')}/{svc.get('SubState')} "
                        f"(pid {svc.get('MainPID')}, restarts "
                        f"{svc.get('NRestarts')}) since {since}")

    eq = rep.get("equity")
    if eq is None:
        line("equity", f"UNAVAILABLE — {rep.get('equity_error', 'read failed')}")
    else:
        peak = rep.get("peak_equity")
        dd = rep.get("drawdown_pct")
        line("equity", f"{eq:.2f} USDT" + (
            f"   peak {peak:.2f}, dd {dd:.2f}%" if peak else "   (peak not set yet)"))
    if rep.get("kill_level"):
        line("kill switch", f"fires at {rep['kill_level']:.2f} USDT (12% off peak)"
             + (f"  |  headroom {rep['headroom_to_kill']:.2f} to kill, "
                f"{rep['headroom_to_floor']:.2f} to the 800 floor"
                if "headroom_to_kill" in rep else ""))
    line("halted", "YES — trading stopped" if rep["halted"] else "no")

    gate = rep.get("news_gate") or {}
    gstatus = gate.get("status", "unknown")
    age = rep.get("news_gate_age_h")
    aged = "" if age is None else f", {age:.1f}h old"
    if gstatus in DEGRADED_GATE:
        line("news gate", f"** DEGRADED ({gstatus}) — entries are NOT being "
                          f"screened for event risk ** {gate.get('error', '')[:80]}")
    elif age is not None and age > NEWS_STALE_H:
        # The sentinel only refreshes for assets of already-active pairs, so an
        # idle book freezes it. Rendering that as "ok" is how a 22-hour-old
        # verdict read as healthy on 2026-08-14.
        line("news gate", f"STALE — last rated {age:.1f}h ago "
                          f"@ {gate.get('ts', '?')}"
                          + ("  (no active pairs: nothing to screen, and "
                             "nothing refreshing)" if not rep["pairs"] else
                             "  ** pairs are active and the gate is not "
                             "refreshing **"))
    elif gstatus == "ok":
        line("news gate", f"ok — {gate.get('rated', 0)} assets rated "
                          f"@ {gate.get('ts', '?')}{aged}")
    elif gstatus == "no_news":
        line("news gate", f"ok — no relevant news in window "
                          f"@ {gate.get('ts', '?')}{aged}")
    else:
        line("news gate", f"{gstatus} (no reading yet)")
    ai = rep.get("ai_spend") or {}
    spend, floor = ai.get("spend"), ai.get("floor", 1.0)
    state, age = ai.get("state", "unknown"), ai.get("period_age_h")
    if state == "clear":
        line("ai spend", f"${spend:.4f} — clears the ${floor:.2f} floor "
                         f"(budget $10/day, resets 16:00 UTC)")
    elif state == "pending":
        # Expected every morning between the reset and the scheduled passes.
        # Deliberately NOT an alarm: a warning that fires daily on schedule is
        # one the operator learns to ignore.
        line("ai spend", f"${spend:.4f} — under the ${floor:.2f} floor but "
                         f"only {age:.1f}h into the period; the daily pass "
                         f"runs at +0:30 and the top-up at +4:30")
    elif state == "short":
        line("ai spend", f"** ${spend:.4f} — BELOW the ${floor:.2f} floor with "
                         f"both passes past due ({age:.1f}h in). "
                         f"Disqualification risk THIS PERIOD; run "
                         f"ai_deep_review.py --daily **")
    else:
        line("ai spend", f"** UNREADABLE ({ai.get('error', 'no meter')[:50]}) — "
                         f"floor ${floor:.2f}/period, check /key/info by hand **")
    nxt = bars_to_refit(rep["bar"], rep["refit_every_bars"])
    line("bar", f"{rep['bar']}   (refit every {rep['refit_every_bars']}; "
                + ("refit runs NEXT bar)" if nxt == 0
                   else f"next in {nxt} bars)"))

    print(f"\n  active pairs ({len(rep['pairs'])})")
    if not rep["pairs"]:
        print("    (none — no pair currently passes the gate)")
    for p in rep["pairs"]:
        z = "n/a" if p["z"] is None else f"{p['z']:+.2f}"
        blk = f" blocked={p['blocked']}" if p["blocked"] else ""
        flag = f"   << {p['flag']}" if p["flag"] else ""
        print(f"    {p['pair']:<11} {p['side']:<12} z={z:<7} "
              f"entry±{p['entry_z']} exit±{p['exit_z']} stop±{p['stop_z']}  "
              f"hl={p['half_life_h']}h beta={p['beta']} hold={p['hold_bars']}b"
              f"{blk}{flag}")

    print(f"\n  open positions ({len(rep['open_positions'])})")
    if rep.get("positions_error"):
        print(f"    UNAVAILABLE — {rep['positions_error']}")
    for p in rep["open_positions"]:
        print(f"    {str(p['sym']):<24} {str(p['side']):<6} qty={p['qty']} "
              f"value={p['value']} uPnL={p['uPnL']}")
    if not rep["open_positions"] and not rep.get("positions_error"):
        print("    (flat)")

    if rep["ledger_tally"]:
        tally = ", ".join(f"{k}:{v}" for k, v in sorted(rep["ledger_tally"].items()))
        print(f"\n  ledger totals   {tally}")
    print(f"  recent ({len(rep['recent'])})")
    for r in rep["recent"]:
        t = r.get("ts", "")[11:16]
        ev = r.get("event", "?")
        pair = r.get("pair", r.get("op", ""))
        extra = ""
        if "z" in r:
            extra += f" z={r['z']:+.2f}" if isinstance(r["z"], (int, float)) else ""
        if r.get("reason"):
            extra += f" ({r['reason']})"
        if r.get("result"):
            extra += f" -> {r['result']}"
        print(f"    {t}  {ev:<10} {str(pair):<12}{extra}")
    print("=" * 62)


def main() -> int:
    ap = argparse.ArgumentParser(description="read-only LTP agent snapshot")
    ap.add_argument("--ledger", type=int, default=8,
                    help="how many recent ledger records to show (default 8)")
    ap.add_argument("--no-marks", action="store_true",
                    help="skip live z-score (avoids per-pair mark-price reads)")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    rep = build_report(AgentConfig(), use_marks=not args.no_marks,
                       ledger_n=args.ledger)
    if args.json:
        print(json.dumps(rep, indent=2, default=float))
    else:
        _print_human(rep)
    # exit non-zero on the two states worth alarming on
    if rep.get("halted") or rep.get("equity") is None:
        return 1
    if (rep.get("news_gate") or {}).get("status") in DEGRADED_GATE:
        return 1                      # risk gate dark: worth alarming on
    # `pending` is the expected state right after a budget reset and must not
    # alarm; `short` and `unknown` both mean nobody is coming to fix it.
    if (rep.get("ai_spend") or {}).get("state") in ("short", "unknown"):
        return 1                      # below the organizer floor: DQ risk
    return 0


if __name__ == "__main__":
    sys.exit(main())
