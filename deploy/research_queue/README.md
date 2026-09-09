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

## How to use it

**The operator dispatches. Nobody needs to be asked.** When Cowork is idle and
this directory is non-empty, take the lowest-numbered open task and run it.

1. `git checkout -b research/<task-name>` in the local clone.
2. Point Cowork at the repo folder and paste the task file's **PROMPT** block
   verbatim. It is written to be pasted, not paraphrased.
3. When it finishes: `git status`, confirm it created only what the task names,
   commit and push the branch.
4. Move the task file to `done/` in the same commit and note the output path.

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

## Open

| # | task | status |
|---|---|---|
| 01 | `01-overshoot-recheck.md` — **GATE** on the intra-bar monitor decision | open |
| 02 | `02-side-blocked-earned-its-keep.md` | not yet written |
