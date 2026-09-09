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
| 01 | `01-overshoot-recheck.md` — **GATE** on the intra-bar monitor decision | open · run before Sunday 2026-09-13 |
| 02 | `02-side-blocked-earned-its-keep.md` — nothing waits on it | open · next Wednesday |
