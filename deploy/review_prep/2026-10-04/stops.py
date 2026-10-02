"""Top-3 prep: per-stop cost and loss-control levers on every Phase II trip.

P&L of a position is linear (to first order) in the spread rebuilt on its ENTRY
beta, s0 = ln a - beta0 ln b, because the legs were sized on beta0. So P&L at any
hour = gross_total * (z_e(h) - z0) / (z_e_close - z0), with z_e the entry-frame z.
Before the first in-hold refit, live z IS entry-frame z. After it, z_e is an
affine map of live z: z_e = ratio*z + c, recovered from the close record
(z, z_in_entry_coords, mu_shift_sigma) and the live beta (3-dp state rows).
"""
import json, math, sys
S = sys.argv[1]
L = math.log
R = [json.loads(l) for l in open(S + "/p2.jsonl")]
trips = json.load(open(S + "/trips.json"))
state = [json.loads(l) for l in open(S + "/state.jsonl")]

refits = sorted(r["ts"] for r in R if r.get("event") == "refit")
def beta_on(date, pair):
    for r in state:
        if r["date"] == date:
            for p in r["pairs"]:
                if p["pair"] == pair:
                    return p["beta"]
    return None

def enter_rec(pair, ts):
    c = [r for r in R if r.get("event") == "enter" and r["pair"] == pair and r["ts"][:16] <= ts[:16]]
    return c[-1]
def close_rec(pair, ts):
    c = [r for r in R if r.get("event") in ("exit", "stop", "refit_drop") and r["pair"] == pair and r["ts"][:16] == ts[:16]]
    return c[0] if c else None
def path(pair, t0, t1):
    return [(r["ts"], r["z"]) for r in R if r.get("event") == "ai_spread_assessment"
            and r["pair"] == pair and t0[:16] < r["ts"][:16] <= t1[:16]]

out = []
for t in sorted(trips, key=lambda t: t["close_ts"]):
    e = enter_rec(t["pair"], t["entry_ts"]); c = close_rec(t["pair"], t["close_ts"])
    side, z0 = e["side"], e["z"]
    in_hold = [x for x in refits if t["entry_ts"][:16] < x[:16] <= t["close_ts"][:16]]
    zc = c["z"]
    ze_c = c.get("z_in_entry_coords")
    ms = c.get("mu_shift_sigma")
    maps = {}   # beta1 -> (ratio, c)
    note = ""
    if ze_c is None or not in_hold:
        ze_c = zc if ze_c is None else ze_c
        maps = {None: (1.0, 0.0)}
    elif abs(ze_c - zc) < 1e-9 and (ms or 0) == 0:
        maps = {None: (1.0, 0.0)}
    else:
        b0 = e["beta"]
        s0e = L(e["price_a"]) - b0 * L(e["price_b"])
        s0c = L(c["price_a"]) - b0 * L(c["price_b"])
        sig0 = (s0c - s0e) / (ze_c - z0)
        mu0 = s0e - z0 * sig0
        mu1 = mu0 + ms * sig0
        bmid = beta_on(in_hold[-1][:10], t["pair"])
        for b1 in (bmid - 0.0005, bmid, bmid + 0.0005):
            s1c = L(c["price_a"]) - b1 * L(c["price_b"])
            sig1 = (s1c - mu1) / zc
            ratio = sig1 / sig0
            maps[round(b1, 4)] = (ratio, ze_c - ratio * zc)
        if len(in_hold) > 1:
            note = f"{len(in_hold)} refits in hold: hours before the last one are mapped only approximately"
    hp = path(t["pair"], t["entry_ts"], t["close_ts"])
    last_refit = in_hold[-1] if in_hold else None
    def ze_of(ts, z, m):
        ratio, cc = m
        if last_refit is None or ts[:16] < last_refit[:16]:
            return z if not in_hold or len(in_hold) == 1 or ts[:16] < in_hold[0][:16] else ratio * z + cc
        return ratio * z + cc
    out.append(dict(pair=t["pair"], entry=t["entry_ts"][:16], close=t["close_ts"][:16], reason=t["reason"],
                    side=side, z0=z0, zc=zc, ze_c=ze_c, gross=t["gross_pnl"], fees=t["fees"], net=t["net_pnl"],
                    in_hold=in_hold, maps=maps, hp=hp, note=note))

def pnl_at(tr, ze, m):
    return tr["gross"] * (ze - tr["z0"]) / (tr["ze_c"] - tr["z0"])

# ---------------- per-stop table ----------------
print("PER-STOP")
for tr in out:
    if tr["reason"] != "stop":
        continue
    side = tr["side"]; thr = -3.5 if side > 0 else 3.5
    rows = []
    for b, m in tr["maps"].items():
        ratio, cc = m
        ze_at = ratio * thr + cc                     # entry-frame z where LIVE z = 3.5
        loss35 = pnl_at(tr, ze_at, m)
        prev = [(ts, z) for ts, z in tr["hp"] if ts[:16] < tr["close"]]
        zprev = prev[-1][1] if prev else None
        # frozen frame: first hour where entry-frame z is past 3.5
        froz = None
        for ts, z in tr["hp"]:
            ze = (z if (not tr["in_hold"] or ts[:16] < tr["in_hold"][-1][:16]) else ratio * z + cc)
            if (side > 0 and ze <= -3.5) or (side < 0 and ze >= 3.5):
                froz = (ts[5:16], round(ze, 2), round(pnl_at(tr, ze, m), 2)); break
        rows.append((b, round(ratio, 3), round(loss35, 2), round(tr["gross"] - loss35, 2), froz, zprev))
    print(f'{tr["pair"]:14} {tr["entry"][5:]}->{tr["close"][5:]} side {tr["side"]:+d} z0 {tr["z0"]:+.2f} '
          f'z_stop {tr["zc"]:+.2f} z_e_stop {tr["ze_c"]:+.2f} gross {tr["gross"]:+.2f} net {tr["net"]:+.2f} refits_in_hold {len(tr["in_hold"])}')
    for b, ratio, l35, ov, froz, zprev in rows:
        print(f'     beta1 {b}: ratio {ratio}  loss@3.5 {l35:+.2f}  overshoot {ov:+.2f}  last hourly z before stop {zprev:+.2f}  frozen-frame stop {froz}')
json.dump([{k: v for k, v in tr.items() if k != "maps"} | {"maps": {str(k): v for k, v in tr["maps"].items()}} for tr in out],
          open(S + "/trips_mapped.json", "w"))
