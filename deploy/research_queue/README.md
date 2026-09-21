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

**The operator dispatches. Nobody needs to be asked.**

Nothing here is automated. There is no timer and no scheduled job — the day is
a reminder so the lane does not drift, exactly like the daily `status.py`
glance. The procedure is five minutes of typing.

1. Sync the local clone and branch:
   ```powershell
   cd $HOME\repos\ou-statarb
   git checkout claude/offline-competition-deploy-nuk5tz
   git pull
   git checkout -b research/<task-name>
   ```
2. Open Claude Desktop → Cowork, point it at the repo folder, and give it
   **one line** — Cowork can read the task file itself, so the prompt never
   needs copying:
   > Read `deploy/research_queue/05-sigma-window-and-stops.md` and carry
   > out the task in its PROMPT block exactly as written.
3. When it finishes: `git status`, confirm it created only the output file the
   task names, then commit and push the branch.
4. **Land the output on the working branch and move the task file to `done/`.**
   Pushing the throwaway branch is not finishing — on 2026-09-14 all three
   completed outputs turned out to exist *only* on their research branches,
   while this README and `WEEKLY_REVIEW.md` cited `out/` paths that did not
   resolve on `claude/offline-competition-deploy-*`. The decisions survived in
   prose; the per-entry working tables that back the arithmetic did not. Three
   commands do it:
   ```powershell
   git checkout claude/offline-competition-deploy-nuk5tz
   git checkout origin/research/<task-name> -- deploy/research_queue/out/<file>.md
   git mv deploy/research_queue/<task>.md deploy/research_queue/done/
   ```
   then update the tables below and commit.

The scope rules live inside each PROMPT block, so a task dispatched this way
carries them whether or not anyone remembers to repeat them.

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

**The repo carries Phase I only.** `track_record/phase1_submission/reasoning.jsonl`
ends **2026-08-21T16:00:23Z**, and there is no `deploy/*.jsonl` in the repo at
all. The live Phase II ledger exists **only on the droplet**, which Cowork
cannot reach.

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
| 05 | `05-sigma-window-and-stops.md` — does the shrinking sigma window explain the stops? | **open · run next** (Wed 2026-09-23) |

The queue emptied on 2026-09-16 and refilled at the 09-20 review, which is the
cadence the top of this file predicts: reviews generate roughly one or two
research questions, not ten.

## Done

Task file in `done/`, answer in `out/`. **Both are on this branch** — read them
here, not on the research branches.

| # | task | answer | decision |
|---|---|---|---|
| 01 | `done/01-overshoot-recheck.md` | `out/01-overshoot-recheck.md` | **2026-09-09.** −10.67 reproduces but is stale and an upper bound; recoverable fraction unmeasurable. Intra-bar monitor **DROPPED** 09-13 |
| 03 | `done/03-frame-drift-cost.md` | `out/03-frame-drift-cost.md` | **2026-09-11.** Mislabelling cost nothing, drift cost one stop; n=9 closes, not enough to act on. **Falsified its own brief's anchor case**, which found the `entry_beta` bug |
| 04 | `done/04-entry-depth-vs-stops.md` | `out/04-entry-depth-vs-stops.md` | **2026-09-13.** Depth does not predict stop-outs (Fisher p=1.00); damage is in the middle bucket. **DO NOTHING** |
| 02 | `done/02-side-blocked-earned-its-keep.md` | `out/02-side-blocked-earned-its-keep.md` | **2026-09-16. The block EARNS ITS KEEP on drawdown.** The "ten refusals" are **two episodes** (entry fires only when `side == 0`). Net −3.5 (~0.34% NAV), but MDD **2.273% → 1.779%** — a 28% relative cut in permanent drawdown. Also found: `blocked` does **not** survive pair eviction (`ltp_agent.py:302–306`), an undocumented third exit from the block |

Run order was **01 → 04 → 03 → 02**, not numeric. 04 jumped to the front on
2026-09-13: it gates a live sizing decision, and the agent had just entered at
0.09 sigma from its own stop. 03 came before 02 because two independent analyses
landed on the same mechanism within a day of each other without either looking
for it, and it touches the accuracy of the record rather than only performance.

> **Paths in older `WEEKLY_REVIEW.md` entries.** Entries written before
> 2026-09-14 refer to these task files at their original
> `deploy/research_queue/NN-*.md` location, because that log is append-only and
> is not rewritten to match later moves. If a path from an old entry does not
> resolve, look in `done/`.
