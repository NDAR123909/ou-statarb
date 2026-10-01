# Reproducing the 2026-10-04 top-3 prep

Data: the `live/track-record` branch as of `68ad618` (2026-10-01 14:00 export).

```bash
DATA=/some/scratch/dir; mkdir -p $DATA/fills
git show origin/live/track-record:track_record/ltp_ledger_phase2.jsonl > $DATA/p2.jsonl
git show origin/live/track-record:track_record/ltp_state_history.jsonl > $DATA/state.jsonl
for f in $(git ls-tree --name-only origin/live/track-record track_record/ | grep fills_2026-); do
  git show origin/live/track-record:$f > $DATA/fills/$(basename $f); done
python deploy/review_prep/2026-10-04/trips.py $DATA       # merge round trips
python deploy/review_prep/2026-10-04/stops.py $DATA       # per-stop cost, frames rebuilt
python deploy/review_prep/2026-10-04/levers.py $DATA      # levers on all 23 trips
python deploy/review_prep/2026-10-04/oos.py               # Phase I out-of-sample (repo data)
python deploy/review_prep/2026-10-04/scenarios.py $DATA   # score scenarios
```

Analysis code, not agent code: nothing here is imported by the live agent.
