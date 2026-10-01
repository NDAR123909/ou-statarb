"""Loss-control levers scored on EVERY Phase II round trip, winners included."""
import json, sys
S = sys.argv[1]
T = json.load(open(S + "/trips_mapped.json"))

def mid_map(tr):
    ks = list(tr["maps"].keys())
    return tr["maps"][ks[len(ks) // 2]]

def ze(tr, ts, z, m):
    ratio, c = m
    if not tr["in_hold"] or ts[:16] < tr["in_hold"][-1][:16]:
        return z
    return ratio * z + c

def pnl(tr, zev):
    return tr["gross"] * (zev - tr["z0"]) / (tr["ze_c"] - tr["z0"])

def hourly_stop(tr, thr):
    """First hourly LIVE reading past `thr` against the position -> exit there."""
    m = mid_map(tr); side = tr["side"]
    for ts, z in tr["hp"]:
        if (side > 0 and z <= -thr) or (side < 0 and z >= thr):
            return ts, z, pnl(tr, ze(tr, ts, z, m))
    return None

base = sum(t["net"] for t in T)
print(f"actual: 23 trips, net {base:+.2f}")
print("\nMax adverse hourly live z on the 17 non-stop trips:")
for tr in T:
    if tr["reason"] == "stop": continue
    adv = [(-z if tr["side"] > 0 else z) for _, z in tr["hp"]] or [0]
    print(f'   {tr["pair"]:14} {tr["entry"][5:]} {tr["reason"]:10} worst adverse z {max(adv):+.2f}  net {tr["net"]:+.2f}')

for thr in (3.0, 2.5):
    delta, changed = 0.0, []
    for tr in T:
        if abs(tr["z0"]) >= thr:
            # The entry rule is entry_z < |z| < stop_z, so with the stop at
            # `thr` this trade could never have opened. Missed in the first
            # pass, which overstated a tighter stop by the best winner of the
            # phase (09-12, entered at z +3.41, +7.71).
            delta -= tr["net"]
            changed.append((tr["pair"], tr["entry"][5:], tr["reason"], "never entered",
                            round(tr["z0"], 2), round(tr["net"], 2), 0.0))
            continue
        hit = hourly_stop(tr, thr)
        if hit is None: continue
        ts, z, g = hit
        new_net = g - tr["fees"]
        if ts[:16] == tr["close"] and tr["reason"] == "stop":
            # crossed thr and 3.5 in the same hourly bar: same exit, same price
            continue
        delta += new_net - tr["net"]
        changed.append((tr["pair"], tr["entry"][5:], tr["reason"], ts[5:16], round(z, 2), round(tr["net"], 2), round(new_net, 2)))
    print(f"\nHOURLY STOP AT {thr} (live frame): net change {delta:+.2f} -> total {base + delta:+.2f}")
    for c in changed: print("   ", c)

ov = 0.0
for tr in T:
    if tr["reason"] != "stop": continue
    ratio, c = mid_map(tr); thr = -3.5 if tr["side"] > 0 else 3.5
    ov += tr["gross"] - pnl(tr, ratio * thr + c)
print(f"\nPERFECT INTRA-BAR STOP AT 3.5 (upper bound, continuous path): recovers {-ov:+.2f} -> total {base - ov:+.2f}")
