# Research queue

Ready-to-dispatch tasks for the research lane (Claude Cowork). One file per
task, each self-contained: the question, where the data is, the known traps,
and what a finished answer looks like.

## Why this exists as files rather than as a conversation

The Phase I diagnosis was that operational work crowds out research. Five
weekly reviews ran and the universe question — the agenda's own stated highest
priority — was never touched. Nothing was forgotten; the agenda survived
intact. It simply never got dispatched, because dispatching it required a
session with someone who had time.

A queue that lives in a chat window has the same problem: it needs whoever
wrote it to be present. A queue that lives in the repo does not.

## When to run one

**Wednesdays, ~20 minutes. Take the lowest-numbered open task. If the queue is
empty, skip it — there is no make-work here.**

Wednesday because it sits midway between Sunday reviews and leaves the result
committed with days to spare, so Sunday can *act* on a finding rather than
commission one. One task a week also matches the rate the queue refills at:
reviews generate roughly one or two research questions, not ten.

The exception is a task marked **GATE**. Those block a decision the next review
is meant to make, so run them as soon as the queue has one rather than waiting
for Wednesday.

Of your ~20 minutes, maybe five are yours: branch, paste the prompt, commit
what comes back. The rest is the tool working.

## How to run one

**The operator dispatches. Nobody needs to be asked** — and nobody should have
to ask what the commands are. **This section is the whole procedure.** If it is
ever re-derived in a chat window instead of read from here, that is precisely
the failure this queue was built to prevent.

**Everything below uses ONE variable: the task file's stem.** Set it once and
the rest is literal. The branch name derives from it deliberately, so there is
no second thing to remember.

### 0. Refresh the Phase II data — droplet, ~1 min

Skip only if the task is Phase-I-only. The published slice is a periodic export
and goes stale; a brief pointing at it gets whatever was last pushed.

```bash
ssh root@68.183.209.2
cd /root/ou-statarb
.venv/bin/python deploy/export_phase_ledger.py
git add track_record/ltp_ledger_phase2.jsonl
git commit -m "track: refresh phase II ledger slice"
git push origin live/track-record
exit
```

**Read the `last record:` line before moving on.** The tool prints its age in
hours and, past three, says plainly that a quiet ledger is ambiguous: an empty
universe silences the sentinel (`ltp_agent.py`, `if assets:`), so "idle and
healthy" and "stopped" look identical from the file. `deploy/status.py` is what
settles it. **Do not dispatch against a slice you have not looked at.**

Defaults: cut at the Phase II open (2026-09-08T16:00 UTC = 00:00 GMT+8 on
09-09), `ai_deep_review` excluded. `--since`, `--out` and `--include-reviews`
override. The write is atomic, so an interrupted run leaves the previous
published file intact rather than a truncated one that looks complete.

**One-time, if the droplet has not got the script yet:**

```bash
git fetch origin claude/offline-competition-deploy-nuk5tz
git checkout origin/claude/offline-competition-deploy-nuk5tz -- deploy/export_phase_ledger.py
```


### 1. Branch — laptop

```powershell
cd $HOME\repos\ou-statarb
$T = "05-sigma-window-and-stops"        # <- the ONLY thing you change
git checkout claude/offline-competition-deploy-nuk5tz
git pull
git checkout -b research/$T
git fetch origin live/track-record
git checkout origin/live/track-record -- track_record/ltp_ledger_phase2.jsonl track_record/ltp_state_history.jsonl
```

**The last two lines are not optional.** The published Phase II data lives on
`live/track-record`, the droplet's branch — **not on this one.** Without them
the research branch carries Phase I only, and every brief that says "both phases
are in the repo" is false for the tool reading it. That is exactly the
2026-09-16 task 02 failure, and it was found on 2026-09-23, the night before
task 05 would have repeated it.

They only *read* from `live/track-record`; nothing in this runbook pushes to it
(standing rule). And the data is pulled here rather than kept on the working
branch on purpose: a copy there would be a second home for a fact that changes
daily and would go stale the way the coverage note below did twice. Pulled right
after step 0 refreshed it, it is fresh by construction.

### 2. Dispatch — Claude Desktop → Cowork, pointed at the repo folder

One line. Cowork reads the task file itself, so the prompt is never copied:

> Read `deploy/research_queue/05-sigma-window-and-stops.md` and carry out the
> task in its PROMPT block exactly as written.

Substitute your own `$T`. The scope rules live inside each PROMPT block, so a
task dispatched this way carries them whether or not anyone remembers to repeat
them.

### 3. Check, commit, push — laptop

```powershell
git status --short
```

**Expect exactly three lines** — the two inputs you staged in step 1, and the one
file the tool created:

```
A  track_record/ltp_ledger_phase2.jsonl
A  track_record/ltp_state_history.jsonl
?? deploy/research_queue/out/<your $T>.md
```

**Anything else is a scope violation — including `AM` on either input, which
means the tool edited its own data.** All four dispatches so far have been clean
— that is the rules working rather than luck, and it is worth verifying each
time rather than assuming.

```powershell
git add deploy\research_queue\out\$T.md
git commit -m "research: $T"
git push -u origin research/$T
```

The commit carries the two inputs as well as the answer. That is deliberate: the
research branch then records **exactly which slice the answer was computed on**,
which is otherwise lost the next time step 0 overwrites it. Step 4 lands only the
answer, and switching back to the working branch removes the inputs from your
checkout.

### 4. Land it — part of the job, not an afterthought

Pushing the throwaway branch is **not** finishing. On 2026-09-14 all three
completed outputs turned out to exist *only* on their research branches, while
this README and `WEEKLY_REVIEW.md` cited `out/` paths that did not resolve on
the working branch. The decisions survived in prose; the per-entry working
tables that back the arithmetic did not.

```powershell
git checkout claude/offline-competition-deploy-nuk5tz
git checkout origin/research/$T -- deploy/research_queue/out/$T.md
git mv deploy/research_queue/$T.md deploy/research_queue/done/
git add -A deploy/research_queue
git commit -m "research: land $T, move to done/"
git push
```

Then update the **Open** and **Done** tables below, and tell Claude the result so
it reaches `WEEKLY_REVIEW.md`. **An output nobody reads back is a file, not a
finding.**

Tasks are numbered by dispatch order, not importance. A task marked **GATE**
blocks a decision — run those first.

## Standing scope rules for every Cowork task

These are repeated in each task file because a rule that lives only here will
eventually be dispatched without being read.

- Work only inside the repo folder. Never grant a broader directory.
- Always on a throwaway branch, never on `claude/offline-competition-deploy-*`.
- **Never modify `deploy/WEEKLY_REVIEW.md` or `deploy/LTP_STRATEGY.md`.** They
  are append-only project records and rewriting them destroys the memory this
  project runs on.
- Output is **evidence, not orders.** Nothing a research task concludes reaches
  live trading without going through the normal describe-then-go with the
  operator. This is the same standing position taken toward the deep-review
  corpus, and it exists because that corpus turned out to contain a confident,
  widely-repeated claim that was fabricated by our own prompt.

## What the research lane can and cannot see — CHECK THIS BEFORE WRITING A BRIEF

**Both phases reach a research branch, by two different routes, and they are not
equivalent.**

- `track_record/phase1_submission/reasoning.jsonl` is **Phase I**, ending
  2026-08-21T16:00:23Z — the larger sample, and usually the primary test bed.
  It is **on this branch**, so every research branch inherits it.
- `track_record/ltp_ledger_phase2.jsonl` is **Phase II** from 2026-09-08T16:00,
  **trading records only**: `ai_deep_review` is excluded (advisory, ~99% of the
  raw ledger by volume, and that window is independently known to be
  contaminated). It and `track_record/ltp_state_history.jsonl` live **only on
  `live/track-record`**, and reach a research branch **because step 1 checks
  them out onto it.** Skip that and they are absent.

The raw `deploy/ltp_ledger.jsonl` is gitignored and stays on the droplet.
`tests/test_research_queue.py` fails if an open brief names a `track_record/`
file that is neither on this branch nor pulled by step 1.

**The Phase II file is a periodic export and lags** — step 0 of the dispatch
refreshes it, and every brief should tell its reader to check the last
timestamp rather than assume it runs to today.

> **This paragraph was itself wrong for a day.** It said "the repo carries
> Phase I only" from 2026-09-16 until 2026-09-21, and stayed wrong for a day
> after the slice landed — the same stale claim was fixed in task 05's brief
> and missed here. **A coverage note is a fact about the repo, and facts about
> the repo change.** Re-check it when writing any brief.
>
> **And then it was wrong the other way, 2026-09-21 → 09-23.** The correction
> said "both phases are in the repo", which was true of the *repository* and
> false of the *branch the tool is handed* — the slice was only ever on
> `live/track-record`. Found on the cold start the night before task 05's
> dispatch. "In the repo" is not specific enough: say **which branch**.

This was learned the expensive way on 2026-09-16. Task 02's brief had been
updated twice with Phase II material — the live `blocked=1`, the 09-15 churn
cluster, the −3.54 stop — all of it quoted from droplet output pasted into a
chat window, and **none of it reachable by the tool being asked to analyse it.**
The dispatch still produced a good answer, because Cowork opened by saying the
data was missing and scoped its work to Phase I. It should not have had to.

**So: every figure a brief asks about must be in the repo, or the brief must
say plainly that it is not and what to do instead.** If a question genuinely
needs Phase II data, the honest options are to ask the operator to paste the
relevant ledger lines into the repo on the task branch first, or to defer the
question until the droplet ledger is committed (a standing open commitment).

**These held.** Audited 2026-09-14 across all three completed dispatches: each
branch contains exactly one new file, its own `out/` answer, and nothing else —
no edits to the records, no stray files, no changes to agent code. The rules
travelling inside each PROMPT block is what did that, so keep copying them.

## Open

| # | task | status |
|---|---|---|
| — | *(empty since 2026-09-23 — skip Wednesday unless a review adds a task)* | |

The queue emptied on 2026-09-16, refilled at the 09-20 review, and emptied
again on 09-23. That is the cadence the top of this file predicts: reviews
generate roughly one or two research questions, not ten.

## Done

Task file in `done/`, answer in `out/`. **Both are on this branch** — read them
here, not on the research branches.

| # | task | answer | decision |
|---|---|---|---|
| 01 | `done/01-overshoot-recheck.md` | `out/01-overshoot-recheck.md` | **2026-09-09.** −10.67 reproduces but is stale and an upper bound; recoverable fraction unmeasurable. Intra-bar monitor **DROPPED** 09-13 |
| 03 | `done/03-frame-drift-cost.md` | `out/03-frame-drift-cost.md` | **2026-09-11.** Mislabelling cost nothing, drift cost one stop; n=9 closes, not enough to act on. **Falsified its own brief's anchor case**, which found the `entry_beta` bug |
| 04 | `done/04-entry-depth-vs-stops.md` | `out/04-entry-depth-vs-stops.md` | **2026-09-13.** Depth does not predict stop-outs (Fisher p=1.00); damage is in the middle bucket. **DO NOTHING** |
| 02 | `done/02-side-blocked-earned-its-keep.md` | `out/02-side-blocked-earned-its-keep.md` | **2026-09-16. The block EARNS ITS KEEP on drawdown.** The "ten refusals" are **two episodes** (entry fires only when `side == 0`). Net −3.5 (~0.34% NAV), but MDD **2.273% → 1.779%** — a 28% relative cut in permanent drawdown. Also found: `blocked` does **not** survive pair eviction (`ltp_agent.py:302–306`), an undocumented third exit from the block |
| 05 | `done/05-sigma-window-and-stops.md` | `out/05-sigma-window-and-stops.md` | **2026-09-23. COINCIDENCE.** Stop rate 25% vs 25% (Fisher p = 1.00); stops come on raw moves 2.19× **larger**; sigma **grew** as the window shrank. Window = `int(3 × half_life)` everywhere observed (r = +0.9996), so it is **unidentifiable** without a counterfactual fixed-window sigma. **Falsified its own brief's key figure** (NEAR/ICP 5.43%, not 1.4%). Declined 4b: rejected half-lives are not logged. First dispatch with the Phase II inputs pulled onto the research branch |

Run order was **01 → 04 → 03 → 02 → 05**, not numeric. 04 jumped to the front on
2026-09-13: it gates a live sizing decision, and the agent had just entered at
0.09 sigma from its own stop. 03 came before 02 because two independent analyses
landed on the same mechanism within a day of each other without either looking
for it, and it touches the accuracy of the record rather than only performance.

> **Paths in older `WEEKLY_REVIEW.md` entries.** Entries written before
> 2026-09-14 refer to these task files at their original
> `deploy/research_queue/NN-*.md` location, because that log is append-only and
> is not rewritten to match later moves. If a path from an old entry does not
> resolve, look in `done/`.
