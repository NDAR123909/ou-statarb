# 06 — How much frame drift is there, measured on one beta?

**Blocks:** nothing formally. But it decides whether task 03's sample means what
it says, and whether the frozen-vs-trailing frame question (task 03 §6) has any
evidence behind it at all.

## Why this exists

At the week 8 review (2026-09-27) the stop record of 2026-09-26 carried
`mu_shift_sigma = 1.12` and `equilibrium_reestimated: true`. Reading **how that
field is computed** showed it compares two different coordinate systems:

```python
# deploy/ltp_agent.py, entry_frame()
spread        = log_a - beta0 * log_b            # rebuilt on the ENTRY beta (the 09-09 fix)
z_entry_frame = (spread - mu0) / sig0            # consistent
mu_shift      = (live_mu - mu0) / sig0           # live_mu was fitted on the LIVE beta
```

When a refit moves beta during a hold, `live_mu` shifts by roughly
Δβ · mean(log price_b) purely because the spread is now a different linear
combination — not because the equilibrium moved. Divided by a small `sig0`,
that is large: the week 8 review estimated **~91σ** on a 09-27 ETH/BTC exit
(ln BTC ≈ 11.35) and **~13.5σ** on the 09-15 stop that the record had called
"the largest frame drift on record".

That review's decomposition is **one session's arithmetic on rounded inputs**.
This task is the independent check, and the extension to everything.

---

## PROMPT

> You are auditing a logged quantity that may have been measuring an artefact,
> and the claims built on it. Work from primary records; do not accept any
> figure stated in prose anywhere in this repo — **including the decomposition
> table in this brief and in `deploy/WEEKLY_REVIEW.md`'s week 8 entry, which is
> the claim under test.**
>
> **Background.** The agent trades a spread `log_a − β·log_b` in z units,
> `z = (spread − mu) / sigma`, with `beta`, `mu` and `sigma` re-fitted at every
> daily refit (`deploy/ltp_agent.py:refit`, `mu` over the last
> `int(3 × half_life)` bars, `sigma` over `int(max(3 × half_life, 24))`). When a
> position opens, the agent snapshots `entry_mu`, `entry_sigma` and
> `entry_beta`. At every close it logs, via `entry_frame()`:
> `z_in_entry_coords` (spread rebuilt on `entry_beta`, measured against
> `entry_mu`/`entry_sigma`) and `mu_shift_sigma = (live_mu − entry_mu) /
> entry_sigma`, where **`live_mu` is fitted on the live beta**.
> `equilibrium_reestimated` is `|mu_shift_sigma| ≥ 0.10`. Before 2026-09-09
> `z_in_entry_coords` was itself computed on the live beta (a known, fixed bug —
> see the `entry_frame` docstring).
>
> **The data, and where it is.**
>
> - `track_record/ltp_ledger_phase2.jsonl` — Phase II, 2026-09-08T16:00 on,
>   trading records only. `enter` records carry the **exact** `beta` in force
>   and both leg prices; `exit`/`stop`/`refit_drop` carry `z`,
>   `z_in_entry_coords`, `mu_shift_sigma` and both leg prices. **This is your
>   primary data.** Check its last timestamp and say what it is.
> - `track_record/ltp_state_history.jsonl` — one row per day at 23:50 UTC,
>   including each active pair's `beta` **rounded to 3 decimals**.
> - `track_record/phase1_submission/reasoning.jsonl` — Phase I. Its close
>   records carry **no leg prices**, so Phase I cannot be reconstructed the same
>   way. Two Phase I closes carry a nonzero `mu_shift_sigma` (2026-08-09 FIL/AR,
>   2026-08-20 KAS/ETC).
> - `deploy/research_queue/out/03-frame-drift-cost.md` — task 03's answer,
>   which reconstructed the KAS/ETC entry frame from in-epoch price prints.
>
> **If `track_record/ltp_ledger_phase2.jsonl` is not in your folder, stop and
> say so** — do not proceed on Phase I alone. Its absence means a dispatch step
> was skipped, which the operator can fix in a minute.
>
> **Answer these, in order:**
>
> 1. **Reproduce or refute the decomposition.** For every Phase II close with a
>    nonzero `mu_shift_sigma`: find its entry record, reconstruct `sig0` and
>    `mu0` from the two entry-frame points available (the entry print, where
>    live frame = entry frame, and the close's `z_in_entry_coords` with its
>    prices on `entry_beta`), and split the reported shift into (a) the part
>    explained by the beta change alone and (b) the **same-beta** shift — the
>    live equilibrium re-expressed on `entry_beta`. Say plainly whether the
>    week 8 table survives.
>
> 2. **The live beta is the weak input — find the best source for each case.**
>    The in-hold refit's beta is not in the `refit` record. An `enter` record
>    for the same pair after that refit and before the next one carries it
>    exactly; otherwise only the 3-dp state row does. For each case, state
>    which source you used and propagate the rounding into a range. Where the
>    range spans "material" and "not material", say so rather than choosing.
>
> 3. **`mu` is a window mean, not a point.** Re-expressing `live_mu` on
>    `entry_beta` needs `mean(log price_b)` over the refit's mu window, which
>    the ledger does not carry. State what you substitute (e.g. the close's
>    `log price_b`) and bound the error it introduces, using the price prints
>    you do have inside each window.
>
> 4. **Phase I's two events.** Using task 03's reconstruction where it exists,
>    and the Phase I `enter` betas, say what can and cannot be concluded about
>    FIL/AR (−0.61) and KAS/ETC (6.44). Remember `z_in_entry_coords` was
>    computed on the wrong beta before 2026-09-09, so the Phase I field is
>    compromised twice over. "Cannot be determined from these records" is an
>    acceptable answer; say what record would determine it.
>
> 5. **Restate the sample.** How many **genuine** frame-drift events — same-beta
>    `|shift| ≥ 0.10` — exist across both phases? Their direction relative to
>    each position (toward or away), and their size. Task 03 said *"2 of 9
>    closes drift at all; one toward, one away"* and set its bar for acting at
>    *double-digit events with consistent direction*. Where does the corrected
>    sample stand against that bar?
>
>    **Be careful with the 0.10 threshold itself.** A same-beta shift is the
>    difference of two window means taken a refit apart, and on an
>    autocorrelated spread those means wander by more than one window-sd between
>    refits, because the sd of ~39 autocorrelated bars understates the process
>    variance. Building the logging fix on 2026-09-27, a synthetic stationary
>    spread with AR(1) φ = 0.95 gave correct same-beta shifts of 0.3–4.1σ₀
>    across seeds. So "≥ 0.10" may count ordinary refit noise as drift. Estimate
>    what these spreads' own autocorrelation implies for the noise band, and
>    report the count against that as well as against 0.10.
>
> 6. **Did the frame choice change any outcome?** Separately from the
>    artefact: when beta and sigma change at a refit, the entry frame and the
>    live frame genuinely disagree about z. For each close whose hold spanned a
>    refit, would the exit or stop have fired **at a different hourly bar** in
>    the entry frame? Use `ai_spread_assessment` z readings (live frame, hourly,
>    no prices) and the reconstructed transform between frames; say where the
>    transform is only approximate. This is task 03's frozen-vs-trailing axis —
>    tally it, do not recommend on it.
>
> 7. **Say what the records cannot tell you**, including every interpolation,
>    every place a rounded beta decided a sign, and every close excluded and
>    why.
>
> **Then a one-paragraph bottom line:** is `mu_shift_sigma` as logged an
> artefact, a signal, or a mixture — and what, if anything, is left of
> "frame drift" as a phenomenon in this record?
>
> Write your answer to `deploy/research_queue/out/06-frame-drift-single-beta.md`
> with per-close working tables (inputs, reconstructed `sig0`/`mu0`, beta source
> and range, artefact, same-beta shift), so the arithmetic can be checked
> without re-running you.
>
> **Scope — do not deviate:**
> - Work only inside this repo folder.
> - Create only the output file named above. Modify nothing else.
> - **Never modify `deploy/WEEKLY_REVIEW.md` or `deploy/LTP_STRATEGY.md`** —
>   they are append-only project records.
> - State your method and say plainly where a figure is sampled, estimated or
>   assumed rather than measured.
> - This is evidence for a human decision, not a recommendation to act. A fix
>   to the logging is already proposed; nothing here should be read as
>   authority to change a live strategy.

---

## What a finished answer looks like

A per-close table that either reproduces the week 8 decomposition or shows
where it is wrong, a beta source and error range for every case, a restated
drift sample with direction, and a tally of closes whose timing depended on the
frame.

**If the week 8 table is wrong, say so first.** It was produced in one sitting
from 3-dp betas and one price print per window, and it has already been used to
correct three places in the record. An error there propagates into all of them.
