"""Out-of-sample: the stop thresholds suggested by Phase II, tested on Phase I.
Decision-time gross P&L from the ledger's own prices and quantities (as in
stop_analysis._decision_pnl); P&L at an earlier hour by linear scaling in z,
which is exact only with no refit inside the hold. Trips with a refit inside the
hold are NOT estimated: they are held at their actual P&L and listed. The first
version of this script scaled them anyway and turned the 2026-08-05 "reverted"
loss (-4.12, the mean moving while the spread ran the other way) into a +13.23
gain -- the frame-drift sign flip, reproduced by accident."""
import json, collections
R = [json.loads(l) for l in open("track_record/phase1_submission/reasoning.jsonl")]
refits = sorted(r["ts"] for r in R if r["event"] == "refit")
trips, open_ = [], {}
for r in sorted(R, key=lambda r: r["ts"]):
    ev, p = r["event"], r.get("pair")
    if ev == "enter":
        open_[p] = r
    elif ev in ("exit", "stop", "refit_drop") and p in open_:
        e = open_.pop(p)
        if r.get("price_a") is None: continue
        s = 1.0 if e["side"] > 0 else -1.0
        gross = s * e["qa"] * (r["price_a"] - e["price_a"]) - s * e["qb"] * (r["price_b"] - e["price_b"])
        hp = [(a["ts"], a["z"]) for a in R if a["event"] == "ai_spread_assessment"
              and a.get("pair") == p and e["ts"][:16] < a["ts"][:16] <= r["ts"][:16]]
        rf = [x for x in refits if e["ts"][:16] < x[:16] <= r["ts"][:16]]
        trips.append(dict(pair=p, entry=e["ts"][:16], reason=ev if ev != "exit" else r.get("reason", "exit"),
                          side=e["side"], z0=e["z"], zc=r["z"], band=e["entry_z"], gross=gross, hp=hp, refit=bool(rf)))

def run(sub, thr):
    base = sum(t["gross"] for t in sub); new = 0.0; lost, cut, unk = [], [], []
    for t in sub:
        if abs(t["z0"]) >= thr:                      # could not have been entered
            lost.append((t["pair"], t["entry"][5:], t["reason"], round(t["gross"], 2))); continue
        g = t["gross"]
        for ts, z in t["hp"]:
            if (t["side"] > 0 and z <= -thr) or (t["side"] < 0 and z >= thr):
                if ts[:16] != t["hp"][-1][0][:16] or t["reason"] != "stop":
                    if t["refit"]:
                        unk.append((t["pair"], t["entry"][5:], t["reason"], round(t["gross"], 2)))
                    else:
                        g = t["gross"] * (z - t["z0"]) / (t["zc"] - t["z0"])
                        cut.append((t["pair"], t["entry"][5:], t["reason"], round(t["gross"], 2), round(g, 2)))
                break
        new += g
    return base, new, lost, cut, unk

print("Phase I trips with prices:", len(trips), collections.Counter(t["reason"] for t in trips))
for label, sub in (("ALL Phase I", trips), ("band < 1.0 era (live regime)", [t for t in trips if t["band"] < 1.0])):
    print(f"\n== {label}: n={len(sub)} ==")
    for thr in (3.0, 2.5):
        base, new, lost, cut, unk = run(sub, thr)
        print(f"  stop {thr}: {base:+.2f} -> {new:+.2f} (change {new - base:+.2f})")
        print(f"     unenterable at this stop: {lost}")
        print(f"     refit in hold, NOT estimated: {unk}")
        for c in cut: print("     exit moved earlier:", c)
