# 05 — Does the shrinking sigma window explain the stops?

**Blocks:** nothing formally. But it is the only *mechanical* account anyone has
offered for the Phase II stop cluster, and every other explanation on the table
("regime", "memecoins") is unfalsifiable by comparison.

## The hypothesis

`ltp_agent.py:291-293` estimates the frame from windows tied to the fitted
half-life:

```python
"mu":    float(np.mean(spread[-int(3 * m.ou.half_life):])),
"sigma": float(np.std(spread[-int(max(3 * m.ou.half_life, 24)):], ddof=1)),
```

So **as the fitted half-life compresses, the window that estimates sigma shrinks
with it.** Over week 7 it did, steadily:

```
                     half-life   sigma window
NEAR/ICP    09-15      26.6h        79 bars
1000SHIB/DOGE 09-15    18.7h        56 bars
              09-17    14.5h        43 bars
              09-19    12.5h        37 bars
```

56 → 37 bars is a **34% cut in one week**. A smaller window estimates sigma on
less data, so it is both noisier and more responsive to a recent quiet patch.
Since `z = (spread − mu) / sigma`, **a smaller sigma inflates z for the same raw
move** — and the stop fires on z, not on the raw move.

If that is what happened, the three Phase II stops were not the spread breaking.
They were the ruler shrinking.

## What is already known, and what it is worth

Two stops carry `mu_shift_sigma = 0.0`, meaning the frame was provably stable
during the hold, so `dspread / dz` **is** sigma:

```
NEAR/ICP 09-15>16     hl 26.58h  window 79  sigma_eq 0.038992  raw move 0.0543 over 1.393 z
1000SHIB/DOGE 09-17   hl 14.46h  window 43  sigma_eq 0.011710  raw move 0.0337 over 2.881 z
```

Both stops **overshot** — 3.76 and 4.13 against a 3.5 band — on **small raw
moves**, 1.4% and 3.4% of log spread.

**That is suggestive and it is not evidence.** Two points, two different pairs,
whose sigmas are not comparable to each other. The hypothesis survives because
nothing has tested it, which is not the same as support.

---

## PROMPT

> You are testing whether a documented implementation detail explains a run of
> losses, or whether that is a story that merely fits. Work from primary
> records; do not accept any figure stated in prose anywhere in this repo,
> including the ones in this task file.
>
> **Background.** The agent trades mean reversion of a spread measured in z,
> where `z = (spread − mu) / sigma`. Both `mu` and `sigma` are re-estimated at
> every refit over trailing windows **tied to the fitted OU half-life**: `mu`
> over `3 * half_life` bars, `sigma` over `max(3 * half_life, 24)` bars. It
> enters when |z| exceeds a cost-aware band and stops out at |z| = 3.5.
>
> The question: **when the fitted half-life compresses, does the resulting
> smaller sigma window inflate z and cause stops that the raw spread movement
> does not justify?**
>
> **Read the coverage note before you start — it changed on 2026-09-21.**
>
> **Both phases are now in the repo**, and they play different roles:
>
> - `track_record/phase1_submission/reasoning.jsonl` — **Phase I**, ending
>   2026-08-21T16:00:23Z. **8 stops, 39 entries, many refits. This is your
>   primary test bed**, because it is the only sample large enough to compute a
>   stop rate conditioned on window size with a denominator worth the name.
> - `track_record/ltp_ledger_phase2.jsonl` — **Phase II**, from
>   2026-09-08T16:00 (the phase open). Trading records only: `enter`, `exit`,
>   `stop`, `refit`, `operation`, `skip`, `news_assessment`,
>   `ai_spread_assessment`. **`ai_deep_review` records are deliberately
>   excluded** — they are advisory, they are ~99% of the raw ledger by volume,
>   and that window is independently known to be contaminated.
>
> **Phase II is small but unusually clean for this question.** It holds the
> three stops that prompted the task, and **two of them carry
> `mu_shift_sigma = 0.0`** — a provably stationary frame during the hold, which
> is exactly the condition under which `dspread / dz` *is* sigma. Those are the
> cleanest available cases for separating the ruler from the move (question 3).
> Three stops cannot carry a rate; they can carry a worked example.
>
> So: **compute on Phase I, corroborate on Phase II**, and keep the two clearly
> labelled. If they disagree, that is a finding, not a problem to average away.
>
> The Phase II file is a periodic export and **may lag the live agent by a day
> or two** — check its last timestamp and say what it is rather than assuming it
> runs to today.
>
> **Answer these, in order:**
>
> 1. **Reconstruct the sigma window per refit.** `refit` records carry each
>    pair's `half_life`. Compute `max(3 * half_life, 24)` for every pair at
>    every refit and describe how it moves over the phase — per pair, and in
>    aggregate. Is compression common, rare, or specific to a few pairs?
>
> 2. **Does the window predict the stop?** For every stop, what was the sigma
>    window in force at the time, and how does that compare to the window
>    distribution across all refits where a pair was held and did NOT stop?
>    **The denominator is the whole question** — a window size at a stop means
>    nothing without the windows at non-stops.
>
> 3. **Separate the ruler from the move.** For each closed position where the
>    records allow it, recover the **raw** spread displacement (in log units,
>    on a single consistent beta) and the z displacement. If the hypothesis is
>    right, stops in short-window regimes should show **large z on small raw
>    moves** relative to stops in long-window regimes. Report raw-move
>    distributions by window size, not just z.
>
> 4. **Is half-life compression itself real, or an artefact?** A shrinking
>    fitted half-life could mean the spread genuinely reverts faster, or it
>    could be the estimator responding to a quiet patch. Check whether
>    compression persists across refits or oscillates, and whether it coincides
>    with realised volatility falling.
>
> 5. **The obvious confound, stated up front.** A short half-life means a fast
>    pair, and fast pairs may simply be worse to trade for reasons unrelated to
>    the window. **Try to separate "short window" from "fast pair."** If you
>    cannot with this sample, say so — that is a legitimate answer and more
>    useful than a confident one.
>
> 6. **Say whether the sample supports a conclusion.** Eight stops across one
>    phase and one regime. **"Not enough data" is a good answer.** If it is
>    yours, say precisely what measurement would settle it — including
>    measurements that require instrumentation we do not yet have.
>
> 7. **State what the records cannot tell you**, including anything you
>    interpolated and every place the Phase I / Phase II boundary bit.
>
> **Then give a bottom line in one paragraph:** is the sigma window a cause, a
> correlate, or a coincidence?
>
> Write your answer to
> `deploy/research_queue/out/05-sigma-window-and-stops.md` with your per-refit
> and per-stop working tables, so the arithmetic can be checked without
> re-running you.
>
> **Scope — do not deviate:**
> - Work only inside this repo folder.
> - Create only the output file named above. Modify nothing else.
> - **Never modify `deploy/WEEKLY_REVIEW.md` or `deploy/LTP_STRATEGY.md`** —
>   they are append-only project records.
> - State your method and say plainly where a figure is sampled, estimated or
>   assumed rather than measured.
> - This is evidence for a human decision, not a recommendation to act. The
>   windows are documented, intentional behaviour; a negative finding is an
>   input to a decision, not authority to change a live strategy.

---

## What a finished answer looks like

A per-refit table of sigma windows, a stop rate conditioned on window size
**with its denominator**, raw-move distributions separated from z, an honest
attempt at the fast-pair confound, and a clear read on whether eight stops can
carry any of it.

**If the window is a cause**, the fix is not obvious and should not be assumed:
decoupling sigma's window from the half-life trades one bias for another, since
a fixed long window would be slow to notice a genuine volatility regime change.
That is a design decision for the operator, informed by this.

**If it is a coincidence, say so plainly** — and the stop cluster goes back to
being unexplained, which is a more honest place to stand than a mechanism that
merely fits.
