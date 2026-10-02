"""Counterfactual daily equity series per lever (close-to-close, 23:50 rows).
Overshoots are the mid-beta values from stops.py. A proxy for the scorer, whose
own daily window (00:00 -> 23:00) we cannot yet reproduce."""
import json, math, statistics as st, sys
data = sys.argv[1]
rows = [json.loads(l) for l in open(data + "/state.jsonl")]
rows = [r for r in rows if r["date"] >= "2026-09-08"]
dates, eq = [r["date"] for r in rows], [r["equity"] for r in rows]
over = {"2026-09-15": 0.08, "2026-09-16": 1.63, "2026-09-17": 2.89,
        "2026-09-26": 3.65, "2026-09-28": 0.20, "2026-09-29": 0.06}
def stats(e):
    r = [e[i] / e[i - 1] - 1 for i in range(1, len(e))]
    mu, sd = st.mean(r), st.stdev(r); pk, mdd = e[0], 0
    for x in e: pk = max(pk, x); mdd = max(mdd, 1 - x / pk)
    return 100 * (e[-1] / e[0] - 1), mu / sd * math.sqrt(365), 100 * mu, 100 * sd, 100 * mdd
def series(delta, k=1.0):
    out = [eq[0]]
    for i in range(1, len(eq)):
        out.append(out[-1] + (eq[i] - eq[i - 1]) * k + delta.get(dates[i], 0) * k)
    return out
for name, s in (("actual", series({})), ("perfect intra-bar 3.5", series(over)),
                ("sizing x2", series({}, 2)), ("perfect 3.5 + sizing x2", series(over, 2))):
    ret, sh, mu, sd, mdd = stats(s)
    print(f"{name:26} return {ret:+.2f}%  Sharpe {sh:+.2f}  mu {mu:+.3f}%  sd {sd:.3f}%  MDD {mdd:.2f}%")
ret, sh, mu, sd, mdd = stats(eq); n = len(eq) - 1; left = 57 - n
need = (3 / math.sqrt(365) * sd * 57 - mu * n) / left
print(f"Sharpe 3 over 57 days at sd {sd:.3f}% needs {need:+.3f}%/day for the last {left} days "
      f"(~{need * 10:.2f} USDT/day) vs {mu * 10:+.3f} so far")
