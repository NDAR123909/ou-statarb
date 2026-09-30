# 07 — Is there honest breadth, in time to matter? · GATE

**Blocks:** the Sun 2026-10-04 review, which the operator has made a **top-3
strategy review**. Runs ahead of task 06 for that reason.

## Why this exists

On 2026-09-29 the operator stated that a top-3 finish in Phase II is a must.
Position that day: **9th, score 61.3**; third place 90.0; ~36 days left. The
score is 40% Sharpe, and Phase II's daily returns explain ours: 9 up days
+4.19%, 6 down −3.69%, 5 flat, with the four big stop days ≈ −3.3% on their own.
The reversion engine makes small gains on almost every non-stop day; a handful
of stops cancels them.

Of the levers available, **breadth** — more simultaneous, *independent* pairs —
is the only one large enough to move Sharpe materially, because diversified
daily returns are smoother ones. It is also the slowest, and it has a known
price: `CLAUDE.md` invariant 3 applies Benjamini-Hochberg across every test run,
so **widening the candidate list tightens the gate for every pair on it**,
including the ones we trade now. The 2026-09-13 review found expanding
`CANDIDATES` to the 60-symbol universe would make the live gate *stricter*.

This task asks whether honest breadth exists, what it costs, and whether it can
arrive before the phase ends. **"No" is a useful answer** — it would mean a top-3
finish depends on loss control and on the field, not on our universe.

## Dispatch note — this task needs ONE extra file

**Step 0, on the droplet — replaces the README's step 0 for this task.** Run it
between :10 and :50 past the hour, not near the ~08:00 UTC refit. The scan only
reads market data (klines), places nothing, and takes a few minutes.

```bash
cd /root/ou-statarb
.venv/bin/python deploy/export_phase_ledger.py
( set -a; source /root/ltp.env; set +a; .venv/bin/python deploy/universe_scan.py ) 2>&1 | tee track_record/universe_scan_task07.txt
git add track_record/ltp_ledger_phase2.jsonl track_record/universe_scan_task07.txt
git commit -m "track: phase II slice and universe scan for task 07"
git push origin live/track-record
exit
```

Look at the end of the scan output before exiting: it should close with a
`VERDICT:` line. If it ends in an error instead, stop and bring it back — a
truncated scan is worse than none.

**Step 1 needs one extra line** after the usual two pulls:

```powershell
git checkout origin/live/track-record -- track_record/universe_scan_task07.txt
```

**Step 3 expects four lines** — three `A` inputs and the `??` answer.

---

## PROMPT

> You are assessing whether a statistical trading strategy can honestly widen the
> set of pairs it trades, under a fixed multiple-testing correction, in time to
> matter. Work from primary records; do not accept any figure stated in prose
> anywhere in this repo, including this task file.
>
> **Background.** The agent trades mean reversion in cointegrated pairs of
> perpetual futures. At every daily refit it tests a fixed candidate list
> (`CANDIDATES` in `deploy/ltp_agent.py`, 15 crypto pairs, all Binance) through
> the gates in `statarb/selection.py`: Engle-Granger cointegration, split-half
> stability of both cointegration and the hedge ratio, a half-life band
> (`min_half_life` 6h, `max_half_life` 168h), mean crossings, Hurst, a beta
> range, and **Benjamini-Hochberg FDR at q = 0.10 across every pair tested,
> including those rejected by other gates.** That last rule is a project
> invariant (`CLAUDE.md`, invariant 3) and is not up for relaxation here.
> Typically 0–2 of the 15 pass.
>
> **The data.**
>
> - `track_record/universe_scan_task07.txt` — the printed output of
>   `deploy/universe_scan.py`, run on the live venue data shortly before this
>   task was dispatched. It applies the **exact live gates** to a wider
>   universe grouped by economic driver (crypto sectors, plus energy, mega-cap
>   equities, an index against its members), across Binance and OKX, and
>   prints: the expanded result under **pooled** FDR (the live standard), the
>   current 15 on the same panel, orientation sensitivity, every non-crypto pair
>   with the gate that rejected it, `cost_z` (round-trip cost in units of the
>   spread's own sigma — above ~1 there is no edge left after fees), a
>   **stratified** FDR diagnostic that is explicitly *not* the live gate, and a
>   verdict line. Read the scan's source to understand each section. **Check the
>   file's first lines and say when it was run and whether anything failed.**
> - `track_record/ltp_ledger_phase2.jsonl` — Phase II trading records.
>   `refit` records carry `passed`, `tested`, `active` and per-pair `bands`;
>   **from 2026-09-30 they also carry `candidates`** — every tested pair with
>   its half-life, reason and which end of the half-life band it failed at. Use
>   what exists; say how many refits carry it.
> - `track_record/phase1_submission/reasoning.jsonl` — Phase I, 35 refits.
> - `track_record/ltp_state_history.jsonl` — daily equity.
> - `deploy/universe_manifest.json`, `deploy/universe_manifest_nc.json` are
>   **not** on your branch; the scan output names any symbol that failed to
>   fetch, which is what you need.
>
> **If `track_record/universe_scan_task07.txt` or
> `track_record/ltp_ledger_phase2.jsonl` is not in your folder, stop and say
> so.** Without the scan this task has no subject.
>
> **Pre-declared expansion sets — evaluate ONLY these three.** Choosing which
> pairs to add by looking at which ones passed is itself a multiple-testing
> error, and the one this project exists to avoid. These were fixed on
> 2026-09-29, before the scan was run:
>
> - **A — status quo:** the 15 `CANDIDATES` pairs.
> - **B — status quo + non-crypto drivers:** A plus every within-venue pair the
>   scan forms in its `energy`, `megacap_equity` and `index_vs_member` groups.
>   Rationale: different economic drivers from crypto's single BTC factor.
> - **C — the scan's full expanded universe**, as the scan defines it.
>
> Do not construct a fourth set from the results. If you believe a different
> set should have been pre-declared, say so and why — as a recommendation for
> a future pre-registration, not as a result.
>
> **Answer these, in order:**
>
> 1. **What passes under each set, under pooled FDR?** For A, B and C: the
>    number of tests (m), what passes, each passer's half-life, beta, crossings
>    and `cost_z` where printed. Where the scan does not print a quantity you
>    need for B specifically, say how you derived it or that you could not.
>    Treat any pair with `cost_z` near or above 1 as not tradeable.
>
> 2. **The FDR price.** Do the pairs that pass under A — the ones currently
>    traded, e.g. 1000SHIB/DOGE and ETH/BTC — still pass at the m of B and of C?
>    State plainly how many passes each set **gains** and how many it **loses**
>    relative to A. A wider set that admits one new pair and ejects the one we
>    trade is not breadth.
>
> 3. **Is one snapshot evidence at all?** The scan is a single day. Using the
>    refit history, how often has each currently-traded pair passed across
>    Phase I and Phase II refits? For expansion candidates only the one snapshot
>    exists — say what persistence evidence a decision would need (for example,
>    how many further daily scans) and whether that can exist before the phase
>    ends on 2026-11-04.
>
> 4. **Would it actually be breadth?** More pairs only smooth daily returns if
>    their spread returns are not correlated with each other. The repo has no
>    price panel for the expansion candidates, so this cannot be measured here —
>    say so, and say what the economic grouping does and does not imply about it
>    (e.g. crypto spreads may fail together in a trending regime even when
>    hedged; the rejection mix since 2026-09-27 has been led by "too few mean
>    crossings", which is what trending produces).
>
> 5. **What blocks each candidate operationally, independent of statistics?**
>    From the record: pairs spanning two venues have unmodelled execution risk;
>    the SPX contract's hedge ratio against its own constituents is unexplained;
>    OKX delisted 72 perps on 2026-09-28, dense with equity and index contracts;
>    underlyings with market hours gap on weekends while perps trade 24/7;
>    `max_half_life` (168h) was set for hourly crypto and may reject slow
>    commodity spreads for being slow rather than for failing to revert. Tag each
>    passer in B and C with every such blocker that applies, citing where in the
>    repo you found it.
>
> 6. **Timeline.** A change decided on 2026-10-04 deploys at the earliest around
>    2026-10-06, leaving about four weeks. For each set, roughly how many
>    additional round trips could that produce, given the passers' half-lives
>    and the agent's hold rules (`max_hold_mult` 3 × half-life)? **Do not
>    assume an edge per trade** — Phase II's measured edge is indistinguishable
>    from zero. State what the trade count would need to be for the effect on
>    Sharpe to be distinguishable from noise, and whether four weeks can supply
>    it.
>
> 7. **State what the records cannot tell you**, including anything the scan
>    output omits that a decision would need.
>
> **Then a one-paragraph bottom line:** is honest breadth available under the
> invariant, in time to matter — **yes, no, or not knowable from this** — and
> what the operator should look at on Sunday to decide.
>
> Write your answer to
> `deploy/research_queue/out/07-breadth-honest-options.md`, with the per-set
> tables (m, passers, their statistics, blockers) so the reasoning can be checked
> without re-running you.
>
> **Scope — do not deviate:**
> - Work only inside this repo folder.
> - Create only the output file named above. Modify nothing else.
> - **Never modify `deploy/WEEKLY_REVIEW.md` or `deploy/LTP_STRATEGY.md`** —
>   they are append-only project records.
> - State your method and say plainly where a figure is sampled, estimated or
>   assumed rather than measured.
> - This is evidence for a human decision, not a recommendation to act. It must
>   not recommend loosening any gate, stratifying the FDR family (rejected
>   2026-09-12 on its own pre-committed test), or selecting pairs by their
>   results. A finding that honest breadth is unavailable is as valuable as the
>   opposite.

---

## What a finished answer looks like

Three tables — one per pre-declared set — with m, passers, statistics, `cost_z`
and operational blockers; a clear gains-versus-losses line against the status
quo; an honest statement of what a single snapshot can and cannot support; and a
yes / no / not-knowable bottom line the Sunday review can act on.

**If the answer is "no honest breadth in time", say it first and plainly.** The
operator asked for top 3 and deserves to know early which levers are real.
