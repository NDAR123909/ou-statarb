"""Merge every fills report into one Phase II round-trip list.

Each daily report re-lists trips from earlier days, but venue retention is ~7
days, so a later report can carry a trip WITHOUT its fills (P&L None). A record
that has P&L is therefore never replaced by one that does not -- the first
version of this merge got that backwards and showed 13 of 23 trips with no P&L.
"""
import glob, json, sys
data = sys.argv[1]
trips = {}
for f in sorted(glob.glob(data + "/fills/*.json")):
    for t in json.load(open(f))["trips"]:
        if t["entry_ts"] >= "2026-09-08" and t["close_ts"]:
            k, old = (t["pair"], t["entry_ts"]), trips.get((t["pair"], t["entry_ts"]))
            if old is not None and old["net_pnl"] is not None and t["net_pnl"] is None:
                continue
            trips[k] = t
json.dump(list(trips.values()), open(data + "/trips.json", "w"), default=str)
print(f"{len(trips)} Phase II round trips -> {data}/trips.json")
