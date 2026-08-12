# Liquidity Arena 2026 — weekly review log

**READ THIS FILE FIRST at the start of every weekly review**, before answering
anything or proposing changes. It is the durable record: chat context is
compacted or lost between sessions, this file is not. It carries the standing
facts, what each week actually did and why, and the agenda the next review is
expected to pick up.

Companion documents: `deploy/LTP_STRATEGY.md` (the pre-registration and every
disclosed strategy change), `deploy/README_ltp.md` (how the deployment works).
Every behavioural change to the strategy must be disclosed in LTP_STRATEGY.md;
this file is the operating log, not a substitute for that.

**Cold start (context reset).** The operator's trigger phrase is *"Cold start —
read the record and tell me where we are."* The full read order and the required
summary-back are specified in `CLAUDE.md` § "Cold start"; this file is step 2 of
it. Read the standing context, then the newest entry, then Open commitments,
then the current agenda — and report any place the sources disagree rather than
choosing the tidiest one.

---

## Standing context (verify before relying on it — the organizer amends rules)

**Competition.** LTP Liquidity Arena 2026, **Track A "Logic Frontier"**. Team
**NDAR**. Phase I (Sandbox Elimination) **Jul 20 – Aug 21 2026**; Phase II
(Live Finals) Sep 7 – Oct 31. **Top 30 teams advance.**

**Scoring.** `Score = 0.40×Z(Sharpe) + 0.25×Z(PnL) + 0.20×Z(ROI) + 0.15×Z(MDD)`
Hard exit: **equity < 800 USDT** → forced liquidation and elimination.

- **Sharpe** = mean(daily returns) / stdev(daily returns) × √365, risk-free 0,
  where `daily_return[d] = NAV[UTC 23:00] / NAV[UTC 00:00] − 1`. Only completed
  days count; needs ≥2 days. **Zero-return (idle) days and any loss day drag the
  mean down**, so inactivity directly suppresses 40% of the score.
- **MDD** = max over hourly NAV snapshots of `(running_peak − nav)/running_peak`.
  **Monotonically non-decreasing** — once a drawdown is recorded it never
  recovers, so a bad day is permanent and protecting MDD is protecting a
  banked asset.
- "AI Engagement" and "AI-Adjusted PnL" are **display only, not scored**, and
  the engagement figure is a **rolling window, not a cumulative total** — it
  fell 72k → 61k across 2026-08-02 with no change in behaviour. A drop there is
  not a fault.
- **Sharpe at this sample size is noise, in both directions.** With ~14
  completed days, one −0.8% day moved ours from 9.30 to 5.66 (2026-08-02) —
  pure arithmetic, since a single outlier hits the mean and the deviation at
  once. The reference backtest is 0.36 net Sharpe OOS. **Never read a live
  Sharpe move as evidence about the strategy**, and never let one motivate a
  parameter change.

**Hard rules.**
- **AI API**: must use the organizer gateway *exclusively*; any self-provided or
  third-party LLM is immediate disqualification. USD 10/day of tokens, no
  rollover. They verify by correlating AI decision logs with executed orders,
  and warn that trading with zero/non-strategy AI usage may be read as "not an
  AI-driven process". Enforced in code by `LTP_COMPETITION_MODE=1`.
- **AI spend is a BAND, not a cap: minimum USD 1, maximum USD 10/day.** The
  floor is enforced by disqualification and it nearly ended our competition on
  2026-08-12 (see that addendum). Week 2 measured spend at 0.021/day and called
  the quota machinery "three orders of magnitude from binding" — true of the
  ceiling, blind to the floor. **Check `spend` against BOTH ends at every
  review**: `GET https://ai.ltp-contest.com/key/info`. A frugal agent is not
  automatically a compliant one.
- **Leverage**: max 2× opening leverage. All 28 whitelist symbols were set to
  2× on 2026-07-20 via `deploy/set_leverage.py` (re-run it if symbols reset).
- **Never place manual orders through the LTP web UI** — an unlogged order
  breaks the reasoning audit.
- Data partners (SoSoValue, AIVIX) are *market data*, not AI models, so they are
  compliant — but we deliberately do **not** use them (see Deferred).

**Useful endpoints.**
- Self ranking: `GET https://api.ltp-contest.com/api/v1/tracka/ranking/self?phase=PHASE_I`
  (V2 signature: `X-MBX-APIKEY`, `nonce`, `signature`; portfolioId derives from
  the key). Error 30016 = wrong key or T+1 data not ready.
- AI spend: `GET https://ai.ltp-contest.com/key/info` → `spend` field.

**Deployment.** DigitalOcean droplet `68.183.209.2`, systemd unit `ltp-agent`,
repo at `~/ou-statarb`, venv `.venv`, env `/root/ltp.env` (shell-format, so
manual commands need `set -a; source /root/ltp.env; set +a`; the service wrapper
does this itself). Branch **`claude/offline-competition-deploy-nuk5tz`**, which
is what the droplet pulls. Competition portfolio **2188959816060766**, **NET**
position mode, funded 1000 USDT.

**Working protocol with the operator.**
- The operator turns on "Ultracode" and gives an explicit **go** before any code
  is written. Describe the intended change first, then wait.
- Never `rm deploy/ltp_state.json` without first checking for open positions
  (this caused the week-1 orphaned-position incident). Reconciliation now
  cleans up after it, but check anyway.
- Honesty over performance: never loosen a statistical gate to manufacture
  trades or flatter numbers, and say plainly when a result is unflattering.

**Daily glance (operator's routine).** `.venv/bin/python deploy/status.py`.
Escalate immediately on: `halted YES`; service not `active/running` or restarts
climbing; equity down >~5% in a day or headroom-to-kill under ~40; `equity
UNAVAILABLE` / `bad_read` / repeated errors; a position open for days; any
organizer message. Normal and ignorable: stop-outs, pairs cycling flat↔open,
small drawdowns, `reconcile` lines, `ai_spread_assessment` volume.

---

## Week 1 — 2026-07-19 → 2026-07-26 (reviewed Sun 2026-07-26)

### Position at review
Rank **#9 of 29**, score 70.5 · ROI **+0.7%** · PnL **+6.78** · Sharpe **1.15**
· MDD **0.9%** · 25 trades · AI engagement 24k|3k|28k (lowest in top 10).
Equity 1006.42, peak 1009.85, kill switch 888.67. Three active pairs
(RENDER/TAO, FIL/AR, AVAX/SOL), all flat.

Trade record: **6 real round-trips — 3 reverted exits, 3 z-stops** (plus 4
day-one `enter` records that never opened; see the maxNotional bug). Net
positive, so winners outweighed losers, but a 50% stop rate is unexplained and
n is far too small to tune on.

**Why we rank where we do:** MDD 0.9% is second-lowest in the top 10 (teams
above us carry 1.7%–13.6%, permanently). Our weakness is **Sharpe, 9th of 10**,
depressed by day-1's loss plus several idle zero-return days.

### What shipped this week
| # | change | why it mattered |
|---|---|---|
| 1 | Launch on funded competition portfolio (Jul 19) | live before the Jul 20 open |
| 2 | Automation `maxNotionalPerOrder` 500 → 1000 | **every entry was silently blocked** with `RCLI26005`; the book sat flat for ~9h on day 1 |
| 3 | 2× leverage compliance (`set_leverage.py`, all 28 symbols) | 24-hour DQ deadline from the Jul 20 rule change |
| 4 | **nav-guard**: implausible equity read (≤0 or <50% of peak) skips the bar | a defunded/failed read computed a 100% drawdown and fired the kill switch hourly. **This would have self-eliminated us** on any API hiccup |
| 5 | `cancel_all` preview→submit; halt latches before flatten | `RCLI20002`; and a failed flatten left the halt unlatched, re-firing every hour |
| 6 | Durable drawdown high-water mark (`ltp_hwm.json`) | clearing state re-anchored the kill switch downward; now monotonic and state-wipe-proof |
| 7 | AR/FIL added after `universe_scan.py` breadth diagnostic | one genuine storage-sector pair we were blind to; the honest finding was "mostly regime, not too-small universe" |
| 8 | **AI reasoning-depth layer** (`ltp_analyst.py`) | audit exposure: our logs covered only sentiment, not the promised anomaly detection or strategy adaptation |
| 9 | **vol-rule canonical orientation** | Engle-Granger is asymmetric, so the order a pair was *typed in* decided whether it was found (SOL/AVAX fails, AVAX/SOL passes). 2 → 3 pairs at zero statistical cost |
| 10 | **Degeneracy guard** in `select_pairs` + catch-all bar handler | a halted symbol's flat series makes `adfuller` raise; that propagated out of `refit()` and **would have crashed the agent into a systemd restart loop** |
| 11 | **Position reconciliation** (`reconcile_positions`) | see incident below; also catches a crash between an entry's two legs, which leaves a **naked directional leg** |
| 12 | CI fix: `requests` import made optional | first test importing `deploy/` turned `main` red |

Items 4, 10, 11 were latent failures found by diagnostics *before* they cost
money. Item 2 and the incident below were found the hard way.

### Incident — orphaned position (2026-07-26)
`rm deploy/ltp_state.json` was run to force a refit **while a TAO/RENDER pair
was open**. The agent restarted believing it was flat while the exchange held
~1,193 USDT gross: no exit, no stop, outside the gross-exposure budget — and
because the pair read as flat, the next signal would have opened a **second
position in the same direction**. Caught in-session, both legs closed manually
(~+0.30 unrealised, ~0.6 in fees). Root cause was operator/agent process, but
the same state-vs-reality gap occurs with no human error if the process dies
between the two legs of an entry. Fixed structurally by item 11.

### Decisions taken, with reasoning (so they are not silently revisited)
- **Adopted vol-rule orientation, rejected "test both directions".** Measured
  on the same panel: hardcoded 2 pairs, alphabetical 3, vol-rule 3, both-
  directions 3. Both-directions found *nothing extra* while doubling the tests,
  and the two orientations of one pair are strongly correlated tests, which
  weakens Benjamini-Hochberg. The vol-rule never inspects a p-value, so it adds
  no multiple testing.
- **Unaccounted positions are flattened, not adopted.** Adopting means guessing
  the entry price, hold clock and hedge ratio the legs were sized under; a
  mis-adopted pair is a directional bet in a market-neutral costume.
- **Did not act on the Jul 21 mandatory-AI notice beyond deepening logs.** The
  operator holds prior written confirmation (Gigi Deng) that this systematic
  architecture satisfies the Reasoning Audit, and the notice was a group
  broadcast, not addressed to us. Trip-wires that would change this: a rule
  explicitly requiring the LLM to *generate* buy/sell decisions; any message
  addressed to us specifically; our AI usage reading zero.
- **Did not chase the leaderboard.** Ranking pressure is not a reason to loosen
  gates; doing so would forfeit the low-MDD advantage that is our banked
  strength.

### Post-review addition (same day) — news-gate failure visibility
The operator flagged that the depth layer's step up in token use (~32k -> a few
hundred k/day) raises a real risk: the USD 10/day allocation does not roll
over, and if it is exhausted mid-day the *sentiment gate* goes quiet. An audit
confirmed the concern was worse than suspected — `_classify` had six silent
`return {}` paths including a bare `except Exception`, `note()` conflated "no
news" with "LLM unavailable", the sentinel had no budget awareness at all, and
`status.py` showed nothing about it. A quota outage would have stopped entries
being vetoed and `watch` ratings being halved, while the daily glance showed a
perfectly healthy agent.

Fixed: typed sentinel status (`ok`/`no_news`/`no_client`/**`quota`**/
`api_error`/`parse_error`) with quota detected specifically (HTTP 429 or
quota/credit/balance/exceeded in the text); `sentinel_degraded` /
`sentinel_restored` ledger events logged **on transition** so an outage is one
loud event and the audit can see exactly which decisions were unscreened; a
`note()` that states plainly "entry NOT screened for event risk"; a `news gate:`
line in `status.py` (and a non-zero exit code) so the daily glance catches it;
and the analyst's spend meter cached (5 min) so the guard stops costing ~73
HTTP calls/day. Pinned by `tests/test_ltp_news_gate.py`.

**Decision taken: fail-open, but loud.** When the gate is dark the agent keeps
trading at full size rather than halving it, because the news veto is a
secondary guard — the z-stop, vol-targeted sizing and gross cap are unaffected —
and halting or shrinking on an operational outage would cost return for a
non-market reason. Operator concurred. Revisit if the veto ever proves it earns
its keep (see below).

### Post-review addition (2026-07-27) — audit-log gaps found by operator review
The operator audited the ledger's actual contents (not just its existence) and
found three gaps. Verified against source before acting:

1. **`anomaly` is free text — but it never drives behaviour.** The veto reads
   `regime`, which IS enum-validated (`ltp_analyst.py`: anything outside
   `normal|stressed|broken` returns `{}`). So a model answering "no anomalies
   detected" in prose cannot change trading. Concern was well-reasoned; the
   design already separated description from control.
2. **The hourly news verdicts were never persisted** — CONFIRMED and the
   important one. Severities lived in memory and were flattened into one prose
   sentence inside an entry's `reasoning`; with no trade that bar, the
   sentiment call left **no trace at all**. An auditor pulling a quiet stretch
   would have seen no evidence that sentiment analysis ran — the audit theme we
   have claimed longest and described to the organizer.
3. **Screened vs unscreened entries were distinguishable only in prose**, not
   in structured fields, defeating the programmatic correlation the organizer
   says it will run.

Fixed (logging only — no behavioural change, no extra AI spend):
`news_assessment` ledger event on every refresh with per-asset severity and
rationale (logged on `no_news` too: "we looked, nothing relevant" is itself
evidence of cadence); `screening_provenance()` attaches `screened`,
`news_status`, `news_severity{leg}`, `regime`, `regime_confidence` to every
`enter` and `skip`; and the analyst gained the sentinel's typed status so a
missing assessment emits `ai_assessment_unavailable` instead of silence — the
same blind spot, one file over. Pinned by `tests/test_ltp_news_gate.py`.

**Method note for future checks:** `grep '"severity":"..."'` returns nothing
even when the field is present — `json.dumps` writes `"severity": "none"` WITH
a space. Count event types instead; the event tally is the reliable probe.

### Known-unexplained / watch
- **50% stop rate** (3 of 6 round-trips). Entry band is model-derived (~3.0)
  but `stop_z` is a hardcoded 3.5 — only 0.5z of room. Possible mis-calibration,
  **but n=6 is far too small to re-tune on.**
- **Anomaly-veto rate**: the new LLM veto could over-block entries and suppress
  the very Sharpe we want to lift. Unmeasured — first data arrives this week.
- **Funding carry is not modelled** and settlement went live Jul 20. Both legs
  pay/receive; unquantified.

---

## Mid-week — 2026-07-28 → 2026-07-30 (not a scheduled review)

Recorded out of cycle because three days of consequential change would
otherwise have reached Sunday only as chat context, which does not survive.

### Position now
Rank **#4 of 29** (was #9), equity **1019.76 at a new high** (was 1006.42),
drawdown **none since the day-1 event**, peak 1019.64, kill switch 897.28.
Live pair AVAX/SOL, entry ±0.6 / exit ±0.0 / stop ±3.5.

### What changed, and why it was the biggest find of the competition
- **`optimal_bands` had a unit-mismatch bug** (full account in LTP_STRATEGY.md,
  2026-07-28). It compared a raw `profit/cycle` rate against an incumbent
  stored as `rate * sigma_eq`, deflating the bar ~30x, so the greedy search
  walked to the grid corner instead of the optimum. Every live pair reported
  entry 3.0 / exit 1.5 with expected round trips of **83 days to 3.7 years**.
  That — not thin crypto cointegration — was why the book sat idle.
- **Fixing it exposed a second bug within the hour**: the corrected optimiser
  chose `exit_z = 0.0`, and the exit test was `abs(z) < exit_z`, never true at
  zero, so the first position had no reachable profit exit. Exit is now
  directional. Both pinned by tests.
- **Corrected bands validated live**: entry at z=-0.68 (a level the old bands
  could never trade) → exit on reversion at z=+0.37, **2-hour round trip**.
- **Estimation-error floor** added (`ou_mean_standard_error`, `min_entry_se`).
  Honest result: it did NOT rescue the Sharpe, which was the hypothesis. Kept
  at 1.0 as a safety rail only — inert on the reference data, binding on
  slow-reverting crypto pairs the reference data has no examples of.
- **`IMPROVEMENTS.md` corrected 0.44 → 0.36** net Sharpe. The old figure came
  from the bug barely trading (0.02x gross leverage), which flattered Sharpe
  while forgoing most of the return.
- **Maintenance-window guard** (`LTP_MAINTENANCE_WINDOWS`): flatten before,
  trade nothing during an announced order-API blackout. The 2026-07-30 06:00
  UTC window passed with no damage, but only because the book happened to be
  flat — that was luck, and is now handled.

### The decision that governs this phase
`risk_per_pair` **halved 0.004 → 0.002** and the corrected bands deployed live,
deliberately spending drawdown budget to buy evidence. Justification: Track A
Phase I advances the **top 30 of a 29-team field** and Track B does not compete
in Phase I, so advancement is assured above the 800 floor and **Phase I rank is
worth nothing** — but Phase II ranking and the prize are real, and we would
otherwise enter it with no crypto evidence for the corrected bands. Stated in
LTP_STRATEGY.md so the post-mortem can hold us to it: *if advancement turns out
not to be assured, the decision was wrong.*

### Pattern worth remembering
A long-lived bug had been holding a second, dependent bug harmless. Fixing the
first made the second live immediately, in production, on a real position. The
lesson is not "fix fewer bugs" — it is that **the first trade after a change to
core maths deserves to be watched, not assumed.**

---

## Continuity work — 2026-07-30 (not a scheduled review)

The subject of this entry is the record itself, so it belongs in the record.

### Position at time of writing
Equity **1020.15**, peak 1019.64, drawdown **0.08%**, kill switch 897.28,
halted **no**. Live pair **AVAX/SOL**. Rank **#4 of 29** as last observed on
2026-07-29 — *not re-checked since*, so treat the rank as the stale figure it
is until the self-ranking call is run. This supersedes the 1019.76 in the
mid-week entry above, which was correct when written.

### What shipped
| # | change | why |
|---|---|---|
| 1 | `tests/test_review_log.py` | documentation rots silently; tests fail loudly. Asserts the log's newest entry is ≤10 days old, that **Open commitments** exists, that `CLAUDE.md` still points here, and that `LTP_STRATEGY.md` still discloses `optimal_bands` / `exit_z` / `sandbox` / `min_entry_se`. It caught a real gap on its first run — the strategy doc described the estimation floor without naming `min_entry_se`, so a future session could not have grepped for it |
| 2 | **Open commitments** table (above) | four "I'll look at that Sunday" promises were lost in one session on 2026-07-28/30 |
| 3 | **Session close-out** protocol in `CLAUDE.md` | four numbered obligations before any session that changed something ends |
| 4 | `deploy/record_state.py` + droplet cron at 23:50 UTC | the review log records what we *decided*; this records what was *true*. One JSON line per day to `track_record/ltp_state_history.jsonl`, idempotent per day. Generated state cannot drift; remembered state does |
| 5 | **Cold-start protocol** in `CLAUDE.md`, trigger phrase *"Cold start — read the record and tell me where we are"* | the freshness test keeps the record accurate but nothing made anyone **read** it. A reset session does not feel reset; it answers a narrow question confidently from a stale premise. The protocol fixes a read order and requires a summary-back — including any disagreement between sources — before any other work |

### Gap found by running the cold-start protocol on itself
`track_record/ltp_state_history.jsonl` **is not in the repository.** The cron
writes it on the droplet, and nothing ever `git add`s it, so step 4 of the read
order returns nothing in a fresh clone — and the "tamper-evident, publicly
verifiable" framing does not yet apply to it. `git push` from the droplet was
proven working on 2026-07-30 (`--dry-run` reached the remote and reported
*Everything up-to-date*), but it prompted for a username and password: the
remote is HTTPS with **no stored credential**, and cron has no TTY to answer a
prompt. Extending the cron to commit and push therefore needs a deploy key or a
stored PAT on the droplet **first** — see Open commitments. Until that is done,
the state history is a local file on one machine, and should be described that
way and no better.

The same pass found that commit `aa2ab6c` had shipped items 1–4 above without a
line in this log. That is precisely the drift the protocol exists to catch, and
it is why the read order includes `git log`.

---

## Week 2 — 2026-07-27 → 2026-08-02 (reviewed Sun 2026-08-02)

### Position at review
Rank **#2 of 29**, score 94.4 · Sharpe **9.30** · MDD **1.3%** · PnL **+27.32**
· ROI **+2.7%** · 77 trades · turnover 28.83× · AI engagement 63k|9k|72k.
Equity 1027.39, peak 1041.19, drawdown 1.33%, kill switch 916.25. One active
pair, AVAX/SOL, short-spread and open at z=+3.31 against a 3.5 stop.

> **Same-day amendment (2026-08-02 18:00 UTC).** That position **stopped at
> z=+3.63** — 0.13 past the band, so the hourly check behaved correctly here and
> yesterday's −10.25 overshoot is the anomaly rather than the norm. **Both sides
> of AVAX/SOL have now stopped within 31 hours** (long at −10.25 on Aug 1,
> short at +3.63 on Aug 2). Lifetime stops go 4 → 5.
>
> **Numbers after the stop (20:54 UTC, supersedes the table above):** equity
> **1025.28**, peak 1041.19, drawdown **1.53%**, kill switch 916.25, headroom
> 109.03. Flat, `blocked=-1`, z=+2.73. Entry NAV was 1035.18, so that round
> trip cost **−9.90 all-in**; with Aug 1's −6.20 that is **−16.10 against a
> peak-to-now drawdown of −15.91**. The two stops are the entire drawdown —
> nothing else is leaking, and the MDD tick is permanent.
>
> **`risk_per_pair` was NOT restored** — see the commitment below. The agent was
> restarted at 20:54 UTC so `taker_fee = 2e-4` is now live.
>
> **The head-to-head table above is now WRONG and must not be quoted.** At
> 21:00 UTC the leaderboard reads:
>
> | | T.Anh (#1) | NDAR (#2) |
> |---|---|---|
> | Score | 97.6 | **93.2** (was 94.4) |
> | Sharpe (40%) | 7.85 | **5.66** (was 9.30) |
> | MDD (15%) | 3.1% | **1.5%** |
> | PnL (25%) | +63.04 | +25.28 |
> | ROI (20%) | +6.3% | +2.5% |
>
> **We led on Sharpe this morning and now trail on it.** MDD is the only metric
> we still lead. See the Sharpe-sensitivity note below before drawing any
> conclusion from that.

### Sharpe is the score's dominant term and it is dominated by noise
One loss day of roughly −0.8% took our Sharpe from **9.30 to 5.66**, and Sharpe
is 40% of the score. That is not decay and nothing is broken — it is arithmetic
on a 14-day sample:

- `Sharpe = mean(daily) / stdev(daily) × √365`, over ~14 **completed** days.
- Before today: mean ≈ +0.19%/day against stdev ≈ 0.39%/day. That ratio, 0.49
  per day, is what a headline Sharpe of 9.3 actually means.
- A −0.8% day hits both terms at once: it drags the mean **and**, sitting ~2.5σ
  out, inflates the deviation. New mean ≈ 0.12%, new stdev ≈ 0.45% → Sharpe
  ≈ 5.1. Observed 5.66. The arithmetic accounts for all of it.

**A Sharpe of 9.3 was never real.** No strategy sustains that; it was a short
low-variance streak, and 5.66 is regression toward the truth rather than a
failure. The reference backtest is **0.36 net Sharpe OOS** (`IMPROVEMENTS.md`),
and this repo's own Phase 2 spec says to mark live Sharpe as noise until ~60+
trading days. Today is that principle collecting. **Do not read a Sharpe move
in either direction as evidence about the strategy at this sample size.**

Context: the whole field's Sharpe fell today — T.Anh 8.62 → 7.85, Supes
4.69 → 2.52 — so it was a hostile day generally. T.Anh's score still rose
because they made +4.47 on it. (Also: the AI-engagement column is a rolling
window, not cumulative — ours read 72k this morning and 61k tonight without us
doing anything differently. Do not treat a fall there as a problem.)

**The forward risk is idleness, not losses.** Zero-return days drag the mean
down exactly like small losses do, so an idle book suppresses 40% of the score.
We are flat, on one pair, short side blocked, with z at +2.73 against a long
entry that needs z < −0.6. Days of nothing are plausible. There is no
legitimate response — the answer is breadth, breadth is gated by statistics we
will not loosen, and manufacturing trades is the one thing this project refuses
to do. Wait, and say so plainly rather than dressing the wait up as strategy.

**We beat first place on the two metrics we optimised for** and lose on the two
that measure size:

| | T.Anh (#1) | NDAR (#2) |
|---|---|---|
| Sharpe (40%) | 8.62 | **9.30** |
| MDD (15%) | 3.1% | **1.3%** |
| PnL (25%) | +58.57 | +27.32 |
| ROI (20%) | +5.9% | +2.7% |

### Agenda item 1 — the fills analysis (the main event)
Built `deploy/fills_report.py`, which reconciles `ltp_ledger.jsonl` against the
venue's own executions. Window Jul 26 → Aug 1, **11 round trips**:

| | |
|---|---|
| gross P&L | **+23.25** (venue's own `rpnl`: +23.36 — an independent check that agrees) |
| net after fees | **+20.79** |
| win rate | **81.8%** · mean win +3.54 · mean loss −4.31 · worst −6.20 |
| expectancy | **+2.11 / round trip** |
| median / max hold | **2.0h** / 22.0h |
| exits | 9 reverted, 2 stops, **0 max-hold** |
| slippage | mean **0.57 bps**, median 0.0 |
| fees | 2.46, **10.6% of gross** |
| funding | **−0.024 USDT over 34 settlements** |

Fitted half-life is 18.5h and the median round trip is **2 hours**; before the
band fix, expected round trips were 83 days to 3.7 years. That correction is
now measured rather than argued.

### The three numbers that were assumptions and are now measurements
1. **Taker fee is 1.75 bps, not the 5.0 assumed** — exact to five significant
   figures across 22 fills, `fee == tradingFee`, zero rebate, `execType` TAKER
   throughout. **But it does not matter**, which is the more useful finding:
   `band_diagnostic.py` puts `cost_z` at 0.01–0.08 for every candidate, so
   costs are ~8% of the entry band. Correcting the fee moves AVAX/SOL's entry
   by at most one grid step (0.6 → 0.4), and the diagnostic's verdict on
   breadth is explicit: *"HALVING EXECUTION COST would newly admit: NOTHING."*
   Every candidate is already economically tradeable at any fee down to zero.
2. **Funding is −0.024 USDT over 13 days**, 0.002% of NAV. The
   "funding carry is not modelled" caveat carried since launch closes as a
   measured near-zero. (`MODIFY_ASSET +1000.0` matching our deposit is what
   confirms the parser reads the right field.)
3. **Slippage is 0.57 bps mean, 0.0 median.** Execution quality is not where
   the money goes.

**So cost is not what limits us.** The refit rejected 14 of 15 candidates on
*statistics* — split-half ×6, mean crossings ×3, Hurst ×2, beta range ×2,
unstable hedge ratio ×1 — and those gates stay untouched. The only remaining
PnL lever is size.

### Agenda items 2–5
- **2. Has the news veto ever fired? No — and the question was the wrong one.**
  There are no `skip` events of any kind in the ledger: zero news vetoes, zero
  anomaly vetoes, zero gross-cap or min-notional skips. **But `size_mult`
  halved the position on 2026-08-01 08:00**, on the single trade that lost. At
  full size that −6.20 would have been ≈−12.4. The venue's records corroborate
  it: that stop shows `fees=0.105` against ~0.217 everywhere else, and the
  closing fill shows `quantity: 32` against an entry of 63. The gate has never
  vetoed; it has acted. n=1 and post-hoc, but "unproven" was wrong.
- **3. Anomaly veto: zero**, confirmed.
- **4. AI spend is USD 0.021/day against a 10.00/day budget — 0.2%.** The
  quota-exhaustion machinery built in week 1 guards a constraint three orders
  of magnitude from binding. ~~Meanwhile output is **~22 tokens per call**
  across 404 calls, and the Reasoning Audit judges *logical depth*. This is the
  clearest gap on the board and it costs nothing to close.~~
  **WRONG — retracted 2026-08-04.** That divided a *rolling-window* output
  count by a *lifetime* call count; they do not divide. Measured from the
  ledger instead: `ai_spread_assessment` **n=300, median 54 words** (min 38,
  max 102), `news_assessment` median 39. `max_tokens` is 512 and was never
  binding. The rationales are substantive — a sample cites the exact z path,
  the fitted half-life and the band, and distinguishes monotonic trend from
  oscillation to land on `stressed` rather than `broken`. **There is nothing to
  fix here.** The spend figure stands; the depth complaint does not.
- **5. Entry/stop geometry: no change, now for a stated reason.** Zero
  max-hold timeouts in 16 lifetime round trips kills the "losers run too long"
  hypothesis. The geometry is asymmetric — winners capture ~0.6σ to an exit at
  zero, losers can run 2.9σ — but an 82% hit rate pays for it.
- **6. Self-ranking into `status.py`: not done**, carried to week 3.

### The stop fired at z = −10.25, not −3.5
The Aug 1 loss entered long-spread at z=−1.39 (08:00) and stopped at
**z=−10.25** (19:00) — an 8.9σ move in 11 hours on a pair fitted with an 18.5h
half-life. The stop did not fail; **nothing looked between 18:00 and 19:00.**
P&L is linear in Δz, so stopping at 3.5 rather than 10.25 would have cost
≈−1.5 instead of −6.20: **the hourly-only risk check cost ~4.7 USDT, ~0.45% of
NAV, permanently banked into MDD.** A stop is only as tight as its monitoring
interval. This is the case for a sub-hourly, read-only pass that may only close
or stop — see the agenda.

### A logging bug class, found four times in one session
Every path that opens a position is well instrumented. Almost nothing else is:

| path | what is missing |
|---|---|
| refit-drop close (`ltp_agent.py:705`) | no ledger event at all; operations tagged `decision="close"` with no decision behind them |
| `size_mult` (`ltp_news.py:336`) | risk halved, journal-only, no ledger record that a control acted |
| `close_position` (`ltp_broker.py:445`) | no `executed_price` / `executed_qty`, unlike `place_market` |
| `close_position` order id | `order_id: null` — the venue's close response has no `orderId`, so fills cannot be looked up by order at all |

The last two mean **the ledger cannot say what any exit was ever done at.**
`fills_report.py` works around it by matching each symbol's fills by timestamp,
which also makes the report work retroactively — but the audit chain
(decision → operations → outcomes) was missing its outcomes.

**All four fixed the same day** (`tests/test_ltp_logging_gaps.py` pins them as
behavioural contracts): a `refit_drop` decision event with reasoning, logged
*before* the close so a failed close still records the intent; a `size_reduced`
event plus a `size_mult` field on every `enter` row, so a halved position is
visible programmatically rather than only in prose; and `executed_price`,
`executed_qty` and a probed `order_id` on close operations — with the response's
own keys recorded when a field cannot be found, so the next gap is diagnosed by
reading the ledger instead of another live probing session. One principle, not
four fixes: *every path that moves money or changes risk records what it did
and what came back.*

### Operational
- **The Aug 1 06:24:58 restart was `unattended-upgrades`**, via `needrestart`,
  not a crash — `NRestarts=0`, and all 12 lifetime starts were deliberate
  stops. But a randomised timer restarting the trading agent could land between
  the two legs of an entry (naked leg) or inside an announced venue
  maintenance window. Blocked with
  `/etc/needrestart/conf.d/99-ltp-agent.conf`; OS updates still install, the
  restart is now ours to time.
- **`portfolio user-fee-rate` returns upstream 2002 "API Invalid
  Authorization"** — there is no real exchange account behind the simulated
  portfolio to have a fee tier. Our credentials are fine.
- **The platform's CSV exports return header-only files** (all three: order,
  transaction, position history). Worth reporting to the organizers.
- **`transaction executions` will not serve fills older than ~7 days, and this
  is not a span limit we can slice around.** The report now fetches in six-day
  windows; the Jul 20 → Jul 26 window failed on all 8 symbols with upstream
  400001 "Exceed dayTime limit" while the two *later* windows of identical
  width succeeded. It is retention, not width. **Week 1's fills are
  permanently unavailable**, which is why the table above starts 2026-07-26 and
  why the pre-band-fix era can never be compared against the post-fix era from
  this endpoint. The operational consequence outranks the lost data:
  **`fills_report.py` must run on a schedule or the evidence expires.**
  `position history` may have longer retention — untested, week 3.

### Decisions taken
- **`risk_per_pair` 0.002 → 0.004: APPROVED, execution gated** on the current
  position closing. The halving on 2026-07-28 bought evidence for the corrected
  bands; that evidence now exists (11 round trips, 82% win rate, +20.79 net,
  zero max-hold exits), so its justification has expired on its own terms. We
  are trading 15% of the score (MDD ~1.3% → ~2.6%, still under T.Anh's 3.1%)
  to compete for 45% of it. **Not executed today** because AVAX/SOL is our only
  pair, it just moved 8.9σ, and it sits at z=+3.31 against a 3.5 stop — the
  arithmetic is fine, the timing is not.
- **`taker_fee` 5e-4 → 2e-4**, a small margin over the measured 1.75 bps
  against a venue schedule change. Expected to be **inert**, which is exactly
  why it is safe; a wrong input is worth fixing even when it changes nothing
  today.
- **No band geometry change**, no loosening of any selection gate.
- **PAXG/XAUT is retired on evidence**: `cyc_h 2525` — 105 days per round trip.
  Nominally tradeable, practically useless. The pre-registered gold anchor is
  dead for a measured reason rather than an opinion.
  **[Over-claimed — corrected in the 2026-08-03 addendum below.]**

### Method note
I misdiagnosed the fills report's empty output **twice** by reasoning from
indirect evidence before reading a raw record, and separately back-solved σ_eq
from a stop print and got it ~5× wrong, which briefly made a bookkeeping fix
look like a PnL lever. The report now reports its own join quality
(`closes_with_no_operations`, `legs_unmatched`, `windows_failed`,
`symbols_truncated`) so the next failure announces itself instead of arriving
as a plausible-looking zero. **Look at the record before theorising about it.**

---

## Post-review addendum — 2026-08-03

> **RETRACTED later the same day — see the 2026-08-04 addendum.** The
> "constant fee" evidence below is wrong: `band_diagnostic.py`'s sweep columns
> are multipliers of `cfg.taker_fee` with hardcoded labels, so after the fee
> changed 5e-4 → 2e-4 the column reading "2.5bp" was really 1.0bp. The fee was
> never held constant. **The plain explanation was correct: the fee change
> tightened the band one grid step**, exactly as the 2026-08-02 sweep (0.6 at
> 2.5bp, 0.4 at 1.25bp) predicted. Left in place unedited because the reasoning
> error is more instructive than the conclusion.

### The entry band moved, and the cause is neither of the obvious two
The 23:00 UTC refit — the first under `taker_fee = 2e-4` — put AVAX/SOL at
**entry ±0.4**, down from ±0.6. The strategy doc had said the fee change was
"expected to be inert." It was not, and that is corrected there.

The cause is **not** the fee and **not** a regime shift. `band_diagnostic.py`
isolates it, because its 2.5bp column does not depend on `AgentConfig`:

| pair, at a constant 2.5 bps | 2026-08-02 | 2026-08-03 |
|---|---|---|
| ETH/BTC, AVAX/SOL, TAO/RENDER, FIL/AR | 0.6 | **0.4** |

Four pairs flipped overnight at an unchanged fee, so the fee cannot explain it.
But the fit barely moved either: `cost_z` scaled almost exactly by the fee ratio
(2.5×) across the whole panel — AVAX/SOL 0.08 → 0.03, ETH/BTC 0.14 → 0.05,
ZEC/XMR 0.02 → 0.01 — which it would not have done if `sigma_eq` had shifted
materially, and half-lives are near-identical (AVAX/SOL 17.8 → 17.7).

Both facts hold at once, and only one reading reconciles them: **the objective
is nearly flat between 0.4 and 0.6, so the argmax sits on a knife edge and a
~6% nudge to `cost_z` from either direction flips the grid cell.**

**Consequence: expect the band to oscillate 0.4 ↔ 0.6 refit to refit, and do
not read it as signal.** Entry-to-stop geometry swings 2.9σ ↔ 3.1σ with it.
Yesterday's 0.6 was never a settled value either. No action taken and none
warranted — but see Deferred for how to make this visible rather than
recurringly mysterious.

### Correction: PAXG/XAUT is not "dead"
Yesterday's entry retired the pre-registered gold anchor "on evidence" at
`cyc_h 2525` (105 days per round trip). Today it reads **219 (9 days)**, band
3.0 → 1.6. Still not tradeable inside a 19-day phase, so the operational
conclusion stands — but a number that moves 11× in a day on a knife-edge
optimiser does not support the word *dead*. Re-check it at each review rather
than treating it as settled.

### Operational verification
- **Both crons fired.** `fills_2026-08-02.json` carries a 23:55 mtime (not the
  14:13 of the manual run), and `ltp_record.log` shows the Aug 2 row appended.
- **The retention clock is visibly working**: last night's report starts
  2026-07-28 where the previous started 07-26. TAO/RENDER has already aged out.
- **`net_pnl` in that report will keep shrinking as winners age out** — it read
  20.79, then 13.72 overnight, with no money lost. Gross moved 23.25 → 15.97,
  exactly +2.41 (TAO/RENDER leaving) −9.69 (the Aug 2 stop arriving). **It is a
  rolling window, not performance.** The dated JSON files are the real record,
  which is the whole reason the cron exists.
- The Aug 2 stop reconciles at **−9.69 gross / −9.91 net** against the −9.90
  estimated from the equity delta.

### Method note, and it is about me rather than the agent
Four corrections were issued inside 24 hours: the news gate's value, the fee as
a PnL lever, "we beat first place on both metrics", and "expected to be inert".
Each correction was right, and that is not the useful observation. **The
pattern is confident forward-looking claims made on thin evidence and then
walked back.** The fix is not more diligent correcting; it is writing "the band
sits near a grid boundary and may move one step" the first time. A record that
needs correcting four times a day is also a record that becomes hard to read —
which is why this is a dated addendum rather than a fourth amendment layered
onto the week 2 entry.

---

## Post-review addendum — 2026-08-04

Context: short-spread AVAX/SOL open since 2026-08-03 ~14:00, z drifting adverse
(0.54 → 0.56 → 0.94 → 1.12), uPnL −5.66, equity 1019.61, **drawdown 2.07%**.
The position is unremarkable — 1.12 against a 3.5 stop, 11 bars against a
~53-bar max hold. Two findings came out of looking at it.

### Both live bands sit on the optimiser's grid floor
```python
a_grid = np.arange(0.4, 3.01, 0.2)    # entry: minimum 0.4
b_grid = np.arange(0.0, 1.51, 0.25)   # exit:  minimum 0.0
```
AVAX/SOL is at **entry 0.4 / exit 0.0 — both grid minima**, and every pair in
the 2026-08-03 diagnostic showed exit 0.00 at every fee level (60 of 60). The
estimation floor is not what is binding: `min_entry_se × ou_mean_standard_error`
is ≈0.24σ on this fit, *below* the grid minimum.

So `optimal_bands` did not choose 0.4; 0.4 is the smallest value it can return.
**We cannot currently distinguish "optimal" from "clamped."** This is the same
signature as the original band bug — a search pinned at a corner — except the
unit mismatch is fixed and the cause now would be that corrected costs are low
enough for the objective to want a tighter band than the grid allows.

**This partly retracts the 2026-08-03 knife-edge explanation**, which assumed an
interior optimum. At a boundary, "the objective is flat between 0.4 and 0.6" is
not established. Corrected in LTP_STRATEGY.md too.

> **Fully retracted, later on 2026-08-04.** The knife-edge story rested on
> "four pairs flipped at a constant fee." The fee was **not** constant:
> `band_diagnostic.py`'s sweep columns are multipliers of `cfg.taker_fee` with
> **hardcoded labels**, so once `taker_fee` went 5e-4 → 2e-4 the column reading
> "2.5bp" was actually 1.0bp. I compared 2.5bp against 1.0bp and called it a
> control.
>
> The plain explanation was right all along. The 2026-08-02 sweep read AVAX/SOL
> at **0.6 for 2.5bp and 0.4 for 1.25bp**; we set 2.0bp; it went to 0.4. **The
> fee moved the band, one grid step, as predicted.** No knife edge, no regime
> shift.
>
> Fixed at the source rather than only in prose: `fee_label()` derives every
> column heading from the live config so a label cannot go stale, and
> `tests/test_band_probe.py` pins it.
>
> **The grid-floor finding is unaffected** — `a_grid` still starts at 0.4 and
> `min_entry_se` still sits below it, so "optimal vs clamped" is still open.
> `band_diagnostic.py` section 3 now answers it directly: it prints the
> objective across a probe grid down to 0.05 and labels each pair `interior`,
> `at floor`, or `CLAMPED`.
>
> **The lesson is the one worth carrying**: I compared two runs of a tool whose
> column labels are computed from a config value I had changed between the
> runs. Six corrections in three days, and this one retracts a retraction. The
> failure is not carelessness about the record — it is reaching for an
> explanation before checking whether the instrument still means what it says.
> **When two runs disagree, suspect the instrument before inventing a
> mechanism.**

What would settle it: print the objective *value* at each candidate band (the
Deferred item), or widen `a_grid` in a **diagnostic-only** run and see where the
argmax lands. **Do not widen the live grid before that evidence exists** —
a tighter entry means more trades on a thinner edge with the stop unchanged,
and `optimal_bands` takes no stop parameter, so it cannot price that.

### A refit mid-position redefines the spread the position is managed against
`ltp_agent.py:295` preserves only `side`, `hold` and `blocked` across a refit.
Everything else — `beta`, `mu`, `sigma`, `entry_z`, `exit_z`, `half_life`,
`dvol` — is replaced by the new fit, **while the book keeps the hedge ratio it
was opened at.**

Observed 2026-08-03 23:00, with a position open: `beta` 0.488 → 0.504, book
still at 198.12/410.44 = 0.483. A ~4% hedge divergence, immaterial here, and
**not** the cause of the drawdown (AVAX rose ~1.4% while SOL was flat — a
genuine widening).

The latent risk is `mu`, not `beta`. `mu` is re-estimated over the last
3×half-life of spread, so a refit that shifts it materially would move the z of
an open position **with no market movement at all** — potentially into a stop
or an exit. Not observed, and the Aug 1 −10.25 stop is clean (no refit between
its entry at 08:00 and the stop at 19:00). Recorded as a watch item, not an
incident. If it ever fires, the tell is a large z jump on a bar that also
carries a `refit` event.

---

## Post-review addendum — 2026-08-04 (evening): the stop, measured

`deploy/stop_analysis.py` now reconciles every z-stop against the ledger. Five
stops, band ±3.50, 72h watch window:

| pair | when | entry z | stop z | over | pnl | @band | cost | best after | hrs |
|---|---|---|---|---|---|---|---|---|---|
| ETC/KAS | 07-20 07:00 | −3.31 | −4.58 | **1.08** | −4.22 | −0.63 | **−3.59** | — | — |
| TAO/RENDER | 07-21 01:00 | −3.02 | −3.70 | 0.20 | −3.89 | −2.72 | −1.16 | −0.74 | 18.0 |
| TAO/RENDER | 07-26 20:00 | 3.08 | 3.65 | 0.15 | −2.42 | −1.77 | −0.65 | 2.98 | 1.8 |
| AVAX/SOL | 08-01 19:00 | −1.39 | −10.25 | **6.75** | −6.19 | −1.48 | **−4.72** | 0.01 | 35.0 |
| AVAX/SOL | 08-02 18:00 | 1.74 | 3.63 | 0.13 | −8.18 | −7.62 | −0.55 | 0.01 | 12.0 |

**Median overshoot 0.2σ; three of five fired within 0.5σ of the band.** The
stop mechanism is accurate and has a fat tail: two events account for −8.31 of
the **−10.67 total cost of hourly sampling** (~1% of NAV, banked).

### It also solves week 1's unexplained 50% stop rate
The three July stops entered at z = **−3.31, −3.02, +3.08** against a 3.5 band —
**half a sigma of room.** That was the pre-fix entry band of ~3.0, so an
ordinary wiggle stopped them out. Week 1 flagged this as "unexplained, n far
too small to tune on" and deferred it. It is now explained, and it is a
*already-fixed* problem: at entry 0.4–0.6 the same stop sits ~3σ away.

### It sizes the intra-bar threshold, which is what it was built for
A 5.0σ trigger recovers ~3.7 of Aug 1's 4.72 but **misses ETC/KAS entirely**
(that stop fired at 4.58). A **4.0–4.5σ** trigger catches both and recovers
roughly 6 of the 8.31, while sitting far enough above the Aug 4 excursion
(hourly peak 3.38, never stopped, reverted) not to convert it into a loss.
That is a threshold from data rather than the 5.0 I guessed at this morning.

**Caveats that belong with it**: n=5, and 4 of 5 reverted within 72h — on both
AVAX/SOL stops the spread returned to z≈0.01, so holding would have recovered
essentially all of both losses. Hindsight-optimal holding is not a strategy,
and **ETC/KAS never came back inside the band** — that is the case the stop
exists for. The tool's verdict line reads *"stops fire at the band and the
spread does NOT always revert → the stop is doing its job; leave it alone."*
**`stop_z` stays at 3.5.** The defect is the sampling interval, not the level.

### The grid-floor question is closed: clamping costs ~1%
`band_diagnostic.py` section 3 probes to 0.05 and prints the objective, not
just the argmax. Six of fifteen pairs are `CLAMPED` — ZEC/XMR, BCH/LTC,
1000SHIB/DOGE and UNI/AAVE at 0.30, LINK/QNT 0.35, ADA/DOT 0.25 — but the rate
they forfeit to the 0.4 floor is **about one percent**:

```
ZEC/XMR   argmax 0.30    0.3:1.00  0.4:1.00
ADA/DOT   argmax 0.25    0.2:1.00  0.4:0.99
```

**The live grid stays as it is.** And **AVAX/SOL is `interior` at 0.45**, so our
live band was never clamped at all.

### The real result is the flatness, and it hands the band to the stop
```
AVAX/SOL   0.2:0.93  0.3:0.98  0.4:1.00  0.6:0.99  0.8:0.96  1.2:0.83  1.6:0.66
```
**Anything from 0.3 to 0.8 is within 4% of optimal.** (This vindicates the
*description* in the 2026-08-03 addendum — the objective really is nearly flat
there — while the evidence given for it was still invalid and the fee change
remains the correct explanation for the flip. Right description, broken
argument.)

So the entry band is nearly a free parameter as far as `optimal_bands` can see,
which means it should be set by the term `optimal_bands` structurally *cannot*
see — it takes no `stop_z` and prices profit-per-cycle assuming positions run to
reversion:

| entry | captures | risks to stop | ratio | rate cost |
|---|---|---|---|---|
| **0.4 (live)** | 0.4σ | 3.1σ | 7.75 : 1 | — |
| 0.6 | 0.6σ | 2.9σ | 4.83 : 1 | 1% |
| 0.8 | 0.8σ | 2.7σ | 3.38 : 1 | 4% |

**No change made, and the obvious move is not obviously right.** Rate is
profit ÷ cycle, so holding rate roughly constant while widening the band makes
trades ~2× larger and ~2× rarer — AVAX/SOL's cycle goes 28h → ~60h. For Sharpe
that cuts the wrong way: the same return per unit time delivered in chunkier
lumps means more zero-return days and larger jumps, i.e. a higher daily
deviation against an unchanged mean, on the metric worth 40%. Set against that,
a wider band produces fewer stop-outs, and stop-outs are the large negative
outliers. **Those two effects cannot be ranked by argument** — see the week 3
agenda for the measurement that settles it.

### Organizer corroboration on sizing (Quant Tip, 2026-08-04)
> *"Maximum leverage in Track A is 2x. With amplification limited, rankings
> separate on signal quality, position sizing, and drawdown control. It also
> fits how scoring works: Sharpe rewards steady returns, so adding volatility
> tends to weigh on your score rather than lift it."*

Independent confirmation of the `risk_per_pair` hold, reached from the scoring
side rather than ours. It is corroboration, not new information — we got there
from Sharpe's scale-invariance plus the MDD tail — but it further weakens the
case for restoring 0.004 and should be quoted at whoever revisits it.

The same day's Market Watch ("stabilisation rather than a turnaround… could
keep swinging both ways… make sure your risk controls hold up if volatility
picks up") is context, not signal. We do not trade direction, so it changes
nothing operationally. The risk-control half is what the −10.67 sampling
finding above is about.

---

## Post-review addendum — 2026-08-06

### Droplet rebooted cleanly (first time ever tested)
`is-enabled` was checked first — it returned `enabled`, which is the only way a
reboot could have gone wrong. 19 seconds down, on a flat book with zero active
pairs. Everything survived: `NRestarts=0`, **peak 1041.19 preserved** (the hwm
file), bar counter continued 218 → 219 rather than resetting, both cron lines
intact, `self-check PASS`, `news stream: live`. The "System restart required"
banner cleared. Kernel packages (`linux-image-virtual`) were **kept back** —
`apt-get upgrade` does not pull new kernels; that needs `dist-upgrade` and
another reboot, at the next flat window. Not urgent.

### The 2026-08-05 exit was the mean moving, not the spread returning
A short spread entered at z=+0.717, exited at z=−0.109 tagged `reverted`, and
lost 4.11. Both are true only if the reference point moved, and it did:

```
z       fell   -0.827   ← "reverted"
spread  ROSE   +0.0101  ← the thing that actually pays us
```

`−g × Δspread = −407.3 × 0.010094 = −4.11` against an observed −4.06. Two
refits fired during the 38-hour hold, and `mu` is the trailing mean of the last
3 half-lives, so **the equilibrium moved ~1.3σ while the spread rose 0.5σ** —
the target chased the price and overtook it. Full disclosure in
LTP_STRATEGY.md. Shipped: `entry_mu`/`entry_sigma` snapshotted at entry and
carried across refits, `z_in_entry_coords` / `mu_shift_sigma` /
`equilibrium_reestimated` on every exit and stop, and a reasoning line that
says the mean moved instead of claiming a completed cycle. **No behavioural
change**; freezing `mu` is a week 3 question on n=1.

Worth noting *against* over-reading this: every other reverted exit in the
fills record was profitable (+7.26, +2.93, +3.74, +1.85, +3.23, +5.90, +3.37,
+1.59, +1.99). The mechanism is confirmed; its frequency is not.

### Zero pairs pass the gate
```
refit: 0/14 candidates pass
rejects {split-half: 4, mean crossings: 4, hurst: 3, hedge ratio unstable: 2,
         half-life: 1}
```
The AI review called it correctly: *"A zero-pair refit is a strong regime
signal. The rejection pattern is broad and shallow rather than concentrated in
one gate."* Fourteen pairs failing across five different tests is a market-wide
loss of cointegration, not one broken relationship.

**We are idle until at least the next refit (~21h), and longer if it also comes
back empty.** Idle days drag the Sharpe mean exactly like small losses, so this
is the breadth problem at its most acute — and **there is nothing legitimate to
do about it.** Loosening a gate to manufacture trades is the one thing this
project refuses to do, and doing it now, after three losing trades with the
score falling, would be the textbook version of that mistake. We wait, and the
record says we waited rather than dressing it up.

---

## Week 3 — 2026-08-03 → 2026-08-09 (reviewed Sun 2026-08-09)

### Position at review
Final reading **2026-08-09 23:24 UTC**. Equity **1024.78**, peak 1041.19,
drawdown **1.58%**, **MDD 3.7% banked**, kill switch 916.25 with 108.53 of
headroom. **Flat.** 1 of 15 pairs passing (FIL/AR). Rank last observed **#6** on
2026-08-04 and not refreshed since — treat as stale, and note agenda item 4.

**The week ended on a win.** FIL/AR entered 08-08 21:01, exited 08-09 23:00 on a
reverted z=−0.06 after ~26h: **+3.56**, the first winner since Aug 1 and the
first outside AVAX/SOL in this stretch. Its entry band also read **±0.6**, back
up from ±0.4 — the oscillation the flat-objective finding predicts, and a
reminder not to read a band value as a decision.

**The week in one sentence:** three days with no tradeable pair, the gate
reopened unprompted, and the loss attribution finally exists.

### The loss attribution — the main event, and it changes the framing
Merged across the archived daily `fills_*.json` snapshots (the live report only
covers ~7 days; see retention below):

| reason | n | w/l | gross | share of losses |
|---|---|---|---|---|
| **stop** | 2 | 0/2 | −15.89 | **71%** |
| reverted | 10 | 9/1 | **+27.79** | 18% |
| refit_drop | 1 | 0/1 | −2.49 | 11% |

**Total +9.41 across 13 round trips.** The reversion book is 9 wins in 10.
**The edge is real; this is entirely a loss-control problem.** (FIL/AR's +3.56
is not yet in this table — it closed at 23:00, before the 23:55 cron snapshot.
Expect 14 trips and roughly +13 next week.)

But "stops carry the losses" is close to tautological — a stop *is* how a
losing trade ends. The number that survives scrutiny is narrower, from
`stop_analysis`:

```
stop losses, all 5 stops (decision prices):   -24.90
of which overshoot (fired LATE, not at all):  -10.67   → 43% of stop damage
```

Against all identified losses (−24.90 stops on decision prices, −4.07 the
mu-drift exit, −2.49 the refit-drop ≈ −31.46 — the bases are mixed, so treat
this as approximate): **roughly a third of every dollar lost came from the hourly sampling
interval, not from any decision the strategy made.** That is the one lever with
a measured payoff, and it is the whole case for the intra-bar monitor.

Missing from the merge and worth knowing: the Jul 26 TAO/RENDER stop (aged out
before the first cron snapshot overwrote the manual run) and week 1 entirely.

### The three-day drought, and a hypothesis that partly failed
```
Aug 5  0/14 pass   Aug 6  0/15 pass   Aug 7  1/15 pass  → KAS|ETC
```
Rejects were broad and shallow across six gates on both zero days — the AI
review called it correctly twice: *"not concentrated in any single failure
mode."* Equity was flat ~60 hours.

I hypothesised that the 960-bar (~40 day) lookback now contains the Jul 31–Aug 1
market-wide sell-off, breaking split-half stability across the board, with the
implication that it might not clear before Aug 21. **KAS/ETC passing on Aug 7
falsifies the alarming form of that** — a poisoned window would clear nothing.
The weak form survives (pairs whose legs moved together still pass) but that is
just the gate working. **The "we may not trade again this phase" fear is dead.**

**Idle is much cheaper than losing.** A zero-return day sits ~0.12% below our
daily mean; the Aug 2 loss day was ~0.8% below it, and variance punishes
distance quadratically. Three idle days cost roughly 10% of Sharpe against the
**44%** one loss day cost (9.30 → 5.66). Standing flat in a regime with no
dependable spread is the cheap outcome, and **no gate was loosened to
manufacture a trade** — recorded as a decision, not an oversight.

### `refit_drop` fired live for the first time
KAS/ETC was dropped by the 2026-08-08 21:01 refit at z=+1.97 and flattened,
with a proper decision record and reasoning. Before the 2026-08-02 fix that
close would have been two orphan `operation` rows tagged `decision="close"`
with nothing behind them. Cost −2.49 on a 24h hold.

Note the orientation: **`KAS|ETC`, the opposite of the `ETC/KAS` that stopped on
Jul 20.** The vol rule flipped it, so it is a different regression and a
different spread — not the same relationship returning.

### Week 2 agenda outcomes
| # | item | outcome |
|---|---|---|
| 1 | AI reasoning depth | **CLOSED, nothing built** — premise was a rolling-window count divided by a lifetime count. Median 54 words, n=300, `max_tokens` never binding |
| 2 | `risk_per_pair` re-decide | **HOLD at 0.002**, reaffirmed. Organizer's Quant Tip corroborates from the scoring side |
| 3 | Verify the logging fixes fire | **`refit_drop` confirmed live.** `size_reduced` and close-price not yet exercised — carried |
| 4 | Sub-hourly risk check | designed, threshold **measured at 4.0–4.5σ**, NOT shipped — carried |
| 5 | Entry-band / freeze-`mu` simulation | not done — carried, and it is now the gate on two open questions |
| 6 | Did the z-stop cut winners | **ANSWERED** — median overshoot 0.2σ, level is fine, interval is the defect |
| 7 | Self-ranking into `status.py` | not done — **carried a third time** |
| 8 | `fills_report` on a schedule | **DONE** — daily 23:55 since Aug 2, and it is the only reason the attribution above exists |

### The operator's throughput/geometry list — assessed 2026-08-08
Nine items proposed. **Two shipped, seven declined with evidence.** Recorded so
they are not re-proposed from scratch:

| proposal | verdict |
|---|---|
| Loss attribution before changing anything | **SHIPPED** — and it was the right first move |
| Log blocked entries | **SHIPPED** as `skip`/`side_blocked`; last known logging gap |
| Lengthen refit interval / exempt open positions | **No.** Median hold **2.0h** against a 24h interval; refit-drops are ~10% of closes. Exempting means holding pairs that just failed split-half — the failure mode the gate exists for |
| `exit_z` 0.0 → 0.15 | **No.** 13 of 13 exits were `reverted`, **zero** hit `max_hold`, so nothing hovers. And 0.25 was on the optimiser's grid and lost to 0.0 for all 15 pairs at all 4 fee levels |
| Pull `stop_z` in to 1.0–1.2 | **No.** Leaves 0.6σ between entry and stop. Week 1 ran **0.19–0.48σ** of room and produced a 50% stop rate — this rebuilds the failure the corrected bands fixed |
| Deduplicate block logic (`ltp_agent` vs `run_strategy`) | **Real, wrong timing.** Refactoring the live trading loop for zero behavioural benefit at 12 days out. Post-competition |
| Hedge drift on long holds | **No.** Measured 4% on a 2.0h median hold |
| Confirm the ±0.6 → ±0.4 band change | **Mine, and disclosed** — a consequence of `taker_fee` 5e-4 → 2e-4, reported 2026-08-03, cause corrected 2026-08-04, in LTP_STRATEGY.md |
| Restart-required banner | next flat window, with `dist-upgrade` |

### Smaller findings
- **Funding flipped positive: +0.385 across 66 settlements** (was −0.024 across
  34). We are net *receiving*. Still trivial at 0.04% of NAV, but the sign
  changed and the earlier figure is superseded.
- **Ignore `measured_fee_bps_per_side: 1.48`** from the short window — 12 legs
  against 70 unmatched means fees and notional cover different trades. **The
  1.75 bps from 22 complete fills stands.**
- The mu-drift exit prices out at **−4.07** against the −4.06 derived from the
  equity delta. That reconciliation closes.
- **Retention ate the executions window.** The live report now covers 3 round
  trips; everything older is only in the dated snapshots. The Aug 2 cron
  decision is what makes this week's headline number possible at all.

### Process incident — CI, and a rebase that reset the droplet
Three tests compared hardcoded 2026-08-02 fixtures against the wall clock. Once
those aged past the 6.5-day retention clamp they began failing — **tests that
expire on a calendar, failing loudly for the wrong reason.** Fixed by injecting
the clock (`attach_executions(..., now=)`).

PR #25 merged *before* the fix landed, so main went red on `26fc4b6`. The branch
was rebased onto main and force-pushed, which required
`git reset --hard origin/<branch>` on the droplet rather than a pull — the
force-push hazard flagged when #25 was opened. All untracked live state
(`ltp_state.json`, `ltp_ledger.jsonl`, `ltp_hwm.json`, the fills snapshots)
survived. PR #26 merged the fix.

Two corrections from this: **rebase onto main before pushing follow-up work
after a merge**, and — correcting a claim I made — **commits pushed by Actions
using `GITHUB_TOKEN` do not trigger other workflows**, so the daily
`track_record` pushes never re-ran CI. Main held one stale red result rather
than accumulating new ones.

One deliberate calendar-dependent test remains: `test_review_log_is_not_stale`.
If it goes red, **append to this log — never touch the date.**

### Decisions taken
- **`stop_z` stays at 3.5.** Median overshoot 0.2σ; three of five stops fired
  within 0.5σ of the band. The level is fine.
- **Entry band unchanged**, pending the simulation. The optimiser's objective is
  flat within 4% from 0.3 to 0.8, so the band is nearly free to it — but wider
  bands make returns chunkier and rarer, which hurts Sharpe. Cannot be ranked
  by argument.
- **`risk_per_pair` stays at 0.002.**
- **No gate loosened** through a three-day drought with the score falling. This
  was the week that tested that rule and it held.

---

## Post-review addendum — 2026-08-12: near-disqualification on AI spend

**We came within about thirteen hours of being thrown out of the competition,
for a reason nothing in this record had flagged as a risk.**

### What happened

The organizer emailed: Track A requires AI spend above **1 USD**, and teams
below it are **automatically disqualified** at 13:00 GMT+8 on 2026-08-13
(05:00 UTC). Our spend for the period was **USD 0.0036**.

The cause is a blind spot this log helped create. The week 2 entry measured
spend at USD 0.021/day against a 10.00/day budget and concluded the quota
machinery "guards a constraint three orders of magnitude from binding." True of
the ceiling. There is also a **floor**, and we were two orders of magnitude
*under* that one. The standing-context block above now states the band at both
ends, because the week 2 sentence would otherwise have gone on reassuring
future sessions about the wrong side of the constraint.

Nothing about the agent was wrong. It is frugal by design and the frugality was
never the problem — the problem is that a rule existed which we had modelled
only halfway, and no amount of care about the half we understood would have
caught it.

### How it was cleared

`deploy/ai_deep_review.py`, written and shipped the same day, run three times:

| pass | calls | spend after | per call |
|---|---|---|---|
| probe | 2 | $0.00359 → $0.00521 | $0.00131 |
| `--rounds 7 --max-tokens 4000` | 133 | **$0.39646** | $0.00257 |
| `--rounds 7 --max-tokens 8000` | 133 | **$0.79932** | $0.00300 |
| `--rounds 7 --max-tokens 8000` | 133 | **$1.20119** | $0.00299 |

**399 reviews, final spend $1.20119** — 20% clear of the requirement, banked
inside the current budget period (`budget_reset_at` 2026-08-13 16:00 UTC falls
*after* the 05:00 UTC deadline, so the reset cannot claw it back).

The design decision that makes this defensible rather than padding: the seven
follow-ups **escalate**, and each call carries the whole conversation, so cost
scales with depth rather than repetition. Re-asking one question 399 times
would have moved the meter identically and taught us nothing. The analysis
itself was already on the week 4 agenda — the fourteen candidates rejected at
each refit had never had individual review, and the model had never been asked
to argue against us. Read-only with respect to trading, pinned by source
inspection in `tests/test_ai_deep_review.py`. Full disclosure in
LTP_STRATEGY.md, including that the timing was forced.

### I put a wrong number in the prompt and it biased 19 answers per pass

The constraint follow-up read *"Roughly 100 USDT of drawdown headroom sits above
the elimination floor."* Elimination is at **800**; equity was **1024.78**;
headroom above the floor is **224.78**. The ~100 is the distance to **our own
kill switch at 916.25** — a self-imposed halt, not the competition's exit.

Every round-5 "highest-expected-value action" reasoned from it explicitly, and
a reviewer told it has half its real risk budget will counsel more caution than
it should. **That layer is contaminated in a known direction.** Two reviewers
attacked the figure from the inside without being able to check it — *"is the
headroom figure real?"* — which is the single most useful output of the run and
is a finding about my prompt, not about the market.

Fixed at the source, not just in prose: `ELIMINATION_FLOOR`, `KILL_SWITCH` and
`EQUITY_AT_REVIEW` are named constants; `constraint_prompt()` does the
arithmetic and says which floor is ours; `days_left()` derives the phase length
from `PHASE_I_END` rather than the hardcoded "nine days" that would have been
wrong the next morning. Two new tests, 177 total.

**The pattern is the one from 2026-08-04**: I reached for a framing before
checking whether the instrument said what I thought. There the sweep labels had
gone stale; here the headroom figure conflated two floors. Both times the fix
was to derive the number instead of typing it.

### What the reviewer found — hypotheses, not conclusions

One model arguing with itself 399 times, on no data we did not hand it. Volume
is not evidence. Three items clear that bar and go to the synthesis pass:

- **The split-half rejections may be shock artefact rather than
  de-cointegration** — raised unprompted across nearly every pair, and
  `AVAX/SOL` r1 argues the split-half statistics actively *defend* the pair. If
  right, the gate is rejecting on the market-wide 2026-07-31 dislocation now
  sitting inside the 960-bar lookback — which is precisely the hypothesis the
  week 3 entry raised and considered falsified by KAS/ETC passing on Aug 7.
  Worth a second look because it arrives from an independent direction.
- **Realised half-life per closed trade** as the measurement that should gate
  the intra-bar monitor, rather than the reasoning week 3 used. `stop_geometry`
  r1 grants the instinct is defensible and denies the evidence supports the
  mechanism claimed — which is a sharper objection than agreement would have been.
- **Whether the 3.5σ stop triggers correctly at all** (`ADA/DOT` r6) — mechanical,
  never checked in that form.

Discounted hardest: the size-reduction advice (`ETH/BTC` to one-third,
`LINK/QNT` by half), being the most direct consequence of the bad headroom.

**Nothing here has been acted on**, and week 4 item 1 is not pre-empted by it.

### Same day, evening: the floor is DAILY, and a standing job now clears it

`/key/info` returned `budget_duration: "1d"` with `spend` in the same block,
and the reading that started the emergency — **USD 0.00359946** — settles it: a
layer running since 07-20 at ~0.02/day is ~0.50 lifetime at minimum, so a
cumulative meter could not have shown 0.0036. **`spend` is a per-period counter
that zeroes at 16:00 UTC.** The floor recurs.

The organizer checks it **at a moment**, not at a boundary (the warning named
13:00 GMT+8, mid-period). We cannot predict the moment, so every period must
read ≥ 1.00. Natural burn is ~0.04–0.08/day, **at most 8% of the floor** — the
rest has to be deliberate.

**Shipped**: `ai_deep_review.py --daily` (`daily_work()`), targeting 1.15
against a 1.00 floor. Each candidate reviewed from **two angles** (`ANGLES` —
statistical validity, then execution, separated so a reviewer cannot answer the
easier one), rebuilt from a freshly re-fitted panel each run; plus
`ledger_prompts()`, built from the previous 24 hours of our own decisions,
which cannot be stale by construction. A quiet day gets **one** honest topic
about the quiet rather than four about nothing. Two crons: main pass 16:30 UTC
(30 min after reset), top-up 20:30 UTC that no-ops above 1.05. Both exit
non-zero below the floor. **`status.py` gained an `ai spend` line** and returns
1 when the period is short — the same blind spot the news gate had before it
got a line, fixed the same way. 183 tests.

**The part not to overclaim**: this takes the AI layer from ~0.05 to ~1.15
USD/day and *a rule is the reason*, not a result. The per-candidate reviews were
already on the week 4 agenda and are real; the daily cadence is not something
the analysis earned. Where the material runs out below target the pass repeats
it, stamps `pass_index` on every ledger row and prints "this is compliance
volume, not new analysis" — so nobody counting rows later mistakes a second lap
for twice the thinking.

**Still unconfirmed**: whether the floor is formally daily or was one-off
enforcement. Only the organizer can say, and that is the one answer that would
let us stop. See Open commitments.

Also corrected while here: `README_ltp.md` still said **"fees are assumed 5 bps
taker per leg"**, superseded by the 1.75 bps measurement on 2026-08-02. A live
doc asserting a number we disproved ten days ago is exactly the stale premise
the close-out protocol exists to catch.

### Record hygiene done in the same pass

Running the cold-start protocol surfaced four defects in this file, fixed now:
`be4fab2` and `66ac146` had shipped `ai_deep_review.py` with no log line (the
exact drift the read order exists to catch); three commitment rows had been
stranded *below* the table's closing rule, one of them open; and two rows
already decided at the week 3 review were still listed as pending. Also worth
knowing for anyone reading the repo as live truth: **`deploy/ltp_hwm.json` in
git says `peak_equity: 1000.0`** (live is 1041.19) and **`track_record/equity.csv`
is the Alpaca paper record**, flat at 100000 — neither is the competition
account.

---

## Open commitments (write these down WHEN PROMISED, not later)

Anything said in chat as "I'll look at that Sunday" belongs here immediately.
Four such promises were lost in a single session on 2026-07-28/30 before this
section existed; that is what it is for.

| promised | on | trigger / when |
|---|---|---|
| ~~Decide whether to **restore `risk_per_pair` 0.002 → 0.004**~~ **DECIDED 2026-08-09: HOLD at 0.002** | 2026-07-30 | closed — see the row below for the reasoning, and the week 3 "Decisions taken" |
| Decide whether the sentinel should gain **macro-event awareness** (Fed/CPI/GDP are market-wide; our prompt is asset-specific and would rate them `none`) | 2026-07-28 | Sunday review; design question is whether market-wide risk should shrink size across all pairs, or whether the hedge already handles it |
| ~~**Sample the AI rationales for genuine depth**~~ **CLOSED 2026-08-04, nothing to fix** — `ai_spread_assessment` n=300, median 54 words, `max_tokens` never binding; the sampled rationales cite the z path, half-life and band. The "~22 tokens per call" that raised this divided a rolling-window count by a lifetime count | 2026-07-27 | closed |
| ~~Reboot the droplet~~ **DONE 2026-08-06** — 19s down, hwm/bar counter/crontab all survived, first ever test. Kernel packages were kept back; `dist-upgrade` + the second reboot completed 2026-08-09 | 2026-07-28 | closed |
| **Rotate LTP + AI keys** (pasted in chat; mitigated by IP allowlist) | 2026-07-20 | when convenient before Phase II |
| **Give the droplet a non-interactive git credential** (deploy key or stored PAT), then extend the 23:50 UTC cron to `git add track_record/ && git commit && git push` | 2026-07-30 | next time the operator is at the droplet terminal — until then `ltp_state_history.jsonl` exists only on that machine |
| ~~Re-check rank~~ **DONE 2026-08-02**: #2 of 29, score 94.4 | 2026-07-30 | closed |
| ~~Restore `risk_per_pair` 0.002 → 0.004~~ **APPROVED 2026-08-02, HELD the same evening, and DECIDED AGAINST at the 2026-08-09 review** | 2026-07-30 | **closed.** Sizing is scale-invariant in Sharpe, so a restore buys the 45% of the score made of PnL and ROI while doing nothing for the 40% made of Sharpe, and roughly doubles the MDD we still lead on. The organizer's 2026-08-04 Quant Tip reaches the same place from the scoring side. Re-opening this needs a new argument, not the old one |
| **Report the header-only CSV exports to the organizers** — order, transaction and position history all export zero rows | 2026-08-02 | next organizer contact; a broken data export in a competition judged on auditability is worth raising |
| **Decide on the sub-hourly risk check** (read-only pass that may only close or stop, never open). Measured cost of not having it: −10.67 across five stops, ~a third of all losses | 2026-08-02 | **carried to the Sun 2026-08-16 review as agenda item 1 — ship it or drop it in writing.** Design is settled (two-tier, 4.0–4.5σ intra-bar); what is left is the judgement call, with Phase I ending 08-21 |
| ~~Schedule `fills_report.py`~~ **DONE 2026-08-02**, daily at 23:55. Without it this week's loss attribution would not exist — retention had already eaten the live window | 2026-08-02 | closed |
| ~~Restart for `taker_fee`~~ **DONE 2026-08-02 20:54** | 2026-08-02 | closed |
| ~~Restart for `side_blocked` logging~~ **DONE 2026-08-09 23:28** — live now, dormant until a block actually declines a signal | 2026-08-08 | closed |
| ~~`dist-upgrade` + reboot~~ **DONE 2026-08-09 23:28** — kernel 6.8.0-136 → 137, zero updates pending, banner cleared. Second clean reboot: NRestarts=0, peak 1041.19 and the bar counter both survived | 2026-08-06 | closed |
| **Re-merge the fills snapshots weekly** for the loss attribution — the live report only reaches back ~7 days | 2026-08-09 | each review, before writing the numbers down |
| **Synthesise the 399 deep reviews** — where they converge, where they contradict each other, which claims survive contact with the others. Discount the round-5 layer, which reasoned from the understated headroom | 2026-08-12 | Sun 2026-08-16 review. Until it exists, no claim from that run has been acted on |
| **Check AI `spend` against BOTH ends of the band** (min USD 1, max 10/day) at every review — the floor is what nearly disqualified us on 2026-08-12 | 2026-08-12 | every review, and before Phase II opens. Now also automated: `status.py` exits 1 below the floor |
| **Verify the two spend crons actually fired** — 16:30 and 20:30 UTC, first live run 2026-08-13. Check `ltp_ai.log` and that the top-up no-opped rather than double-spending | 2026-08-12 | first daily glance after 2026-08-13 17:00 UTC |
| **Ask the organizers whether the USD 1 floor is daily or was one-off enforcement** — it is the only answer that would let us stop spending ~1.15/day, and it rides along with the header-only CSV report we already owe them | 2026-08-12 | next organizer contact; draft is written when the operator wants it |

> **Table hygiene, 2026-08-12.** Three rows above this line had been stranded
> *below* the closing horizontal rule since 2026-08-09 — outside the table, where
> the next review would likely not have read them, and one of them was open.
> Merged back in. If rows appear below a `---` again, that is the bug, not a
> section break.

---

## Week 4 agenda — review due Sun 2026-08-16

**Phase I ends 2026-08-21.** The review on 08-16 is the last one inside the
phase. (This line read "12 days" when written on 08-09; countdowns rot, so the
date is what is stated. It was 9 days out on 2026-08-12.)

1. **Sub-hourly risk monitor — ship it or drop it, in writing.** The only change
   with a measured payoff: **roughly a third of every dollar lost** came from stops
   firing late. Design is settled — two-tier, the 3.5 band stays on the hourly close
   where it fires within 0.5σ three times in five, and a read-only intra-bar
   pass stops only past **4.0–4.5σ** (5.0 misses ETC/KAS at 4.58; 4.0 still
   clears the Aug 4 excursion that peaked at 3.38 and reverted). May only close
   or stop, never open. **It is also the riskiest thing left to ship** — a new
   loop that can close positions, into a process whose job is to stay up, with
   12 days on the clock. That tension is the decision; make it explicitly.
2. **Run the band/`mu` simulation.** Two questions, one piece of machinery:
   entry band 0.3/0.4/0.6/0.8 against `stop_z=3.5`, and trailing `mu` versus
   `mu` frozen at entry. Report **realised Sharpe, MDD and stop rate** — not the
   optimiser's rate, which is the term that cannot see either. Gates two open
   decisions that have each been argued four or more ways without numbers.
3. **Verify the remaining logging fires.** `refit_drop` is confirmed live.
   `size_reduced` needs a `watch` news rating; close price/qty needs any close
   after the next restart. If `close_position` still logs no price, read the
   `response_keys` it now records rather than probing live again.
4. **Self-ranking endpoint into `status.py`** — carried three times. **Do it or
   delete it from the agenda**; carrying it a fourth time is just noise.
5. **Synthesise the 399 deep reviews** (added 2026-08-12). Where they converge,
   where they contradict each other, and which claims survive contact with the
   others — discounting the round-5 layer, which reasoned from an understated
   headroom figure. Three candidates are already named in that addendum: the
   split-half-as-shock-artefact reading, realised half-life per closed trade as
   the gate on item 1, and whether the 3.5σ stop triggers correctly at all.
   **The output is a list of testable claims, not a list of changes.**
6. **Phase I close-out preparation.** Whatever the post-mortem needs must exist
   before Aug 21: the fills snapshots keep rolling, but decide now what else
   expires. Draft the honest write-up — backtest 0.36 net Sharpe OOS versus what
   actually happened, including that the headline live Sharpe was never real.

### Deferred (revisit only if they matter)
- `band_diagnostic`: print the objective value per candidate band. Convenience
  upgrade to a hand-run tool; the clamping question it was raised for is already
  answered (~1% cost).
- Deduplicate the block state machine across `ltp_agent.py` / `run_strategy.py`.
  Post-competition.
- Sentinel macro-event awareness (Fed/CPI are market-wide; our prompt is
  asset-specific and rates them `none`).
- Report the header-only CSV exports to the organizers.
- Key rotation before Phase II.

---

## Week 3 agenda — review due Sun 2026-08-09 (COMPLETED — see the week 3 entry)

Phase I ends **2026-08-21**. Two reviews left.

1. ~~**AI reasoning depth**~~ **CLOSED 2026-08-04, no action needed.** Measured
   from the ledger: `ai_spread_assessment` n=300, **median 54 words**, and the
   content is real reasoning — the 07:00 sample on 2026-08-04 cites the z path
   (+3.38 → +2.46), the 17.6h half-life and the ±0.40 band, and reasons from
   "not monotonically trending" to `stressed` rather than `broken`. `max_tokens`
   was 512 and never binding. The "~22 tokens per call" that made this the top
   priority was a rolling-window output count divided by a lifetime call count.
   **The layer is working; leave it alone.**
2. **Re-decide the `risk_per_pair` restore** per the commitment above — it was
   approved on 2026-08-02 and held the same evening when both sides of our only
   pair stopped within 31 hours. Two questions decide it: did selection produce
   a second pair, and has AVAX/SOL stopped whipsawing. If it goes ahead, watch
   the first trades at the new size the way the band fix was watched.

   **The case for it changed on the evening of 2026-08-02 and the change is not
   in its favour.** Sizing is scale-invariant in Sharpe — doubling positions
   doubles the mean daily return and the deviation together — so it buys the
   45% of the score made of PnL and ROI while doing **nothing** for the 40%
   made of Sharpe, which is precisely where we just lost our lead (9.30 → 5.66,
   now behind T.Anh's 7.85). It also roughly doubles MDD, the 15% we still lead
   on. So the honest framing is no longer "restore sizing to recover our
   position" — it is "concede the Sharpe race and compete on PnL instead."
   That may still be right, since Sharpe at n=14 is mostly noise and PnL is
   not. But it is a different argument from the one that was approved, and it
   deserves to be made explicitly rather than inherited.

   **The tail, added 2026-08-04 with a live number.** P&L is linear in z
   (`g × sigma × Δz`). The open position was losing ≈−9 to −11 USDT per unit z;
   run to the 3.5 stop that is roughly **−22 to −28 more, putting drawdown near
   4–5%** — worse than every team in the top three, permanently, on the one
   metric we still lead. At `risk_per_pair = 0.004` the same stop is −45 to −55
   and drawdown near **6–7%**. Historical stop rate is 5 of ~19 opens, ~26%, so
   this is a 1-in-4 branch and not a base case. It is the first version of this
   argument carrying a measured number rather than a framing.

   **Organizer corroboration, 2026-08-04 Quant Tip**: *"With amplification
   limited, rankings separate on signal quality, position sizing, and drawdown
   control… Sharpe rewards steady returns, so adding volatility tends to weigh
   on your score rather than lift it."* Reached from the scoring side, that is
   what we concluded from Sharpe's scale-invariance plus the MDD tail. Quote it
   at whoever revisits this.
   **Also ask the prior question**: three of the last four AVAX/SOL trades were
   stops. Is the pair's cointegration decaying, and should a pair that stops on
   *both* sides in quick succession be benched until a refit re-validates it?
   Today the one-sided block covers only the side that broke, by design. n=2 is
   thin evidence for a new rule and a bad week is not a reason to invent one —
   but the sequence is now in the record rather than in someone's memory.
3. **Verify the three logging fixes actually fired** — they shipped 2026-08-02
   but nothing has exercised them live yet. Confirm in the ledger that a
   `refit_drop` event appears at the next refit that drops a held pair, that
   `size_reduced` appears the next time the news gate rates a leg `watch`, and
   that close operations now carry `executed_price`. If `close_position` still
   logs no price, read the `response_keys` it now records and fix the field
   names from that rather than probing live again.
4. **Sub-hourly risk check** — now measured rather than argued. `stop_analysis`
   puts the cost of hourly sampling at **−10.67** across five stops, with
   −8.31 of it in two events. Design is **two-tier**: the 3.5 band keeps being
   evaluated on the hourly close, where it fires within 0.5σ three times in
   five and where the noise filter is doing useful work; a read-only intra-bar
   pass stops only past **4.0–4.5σ**. That threshold is from the data — 5.0
   (my guess) misses ETC/KAS at 4.58, and 4.0 still clears the 2026-08-04
   excursion that peaked at 3.38 and reverted. It may only close or stop, never
   open. **This is the riskiest change on the list to ship** — a new loop that
   can close positions, into a process whose job is to stay up.

5. **Simulate the entry band against the stop — the term the optimiser omits.**
   Section 3 shows the objective is flat within 4% from entry 0.3 to 0.8, so the
   band is nearly free to `optimal_bands`, which takes no `stop_z` and assumes
   positions run to reversion. Two effects then compete and cannot be ranked by
   argument: a wider band gives a better entry-to-stop ratio and fewer stop-outs
   (fewer large negative outliers), while also making returns chunkier and
   rarer, which raises daily deviation and hurts Sharpe. **Measure it**: run the
   fitted OU parameters through `statarb/`'s backtester at entry 0.3 / 0.4 / 0.6
   / 0.8 with `stop_z=3.5`, and report realised Sharpe, MDD and stop rate — not
   the optimiser's rate. Whatever it says, the change is a `min_entry_z` floor
   on top of the optimiser, disclosed as a behavioural change. **Default action
   remains no change.**

   **Second question, same machinery** (added 2026-08-06): should `mu` be
   frozen at entry for the life of a position? The trailing re-estimate closed
   a losing trade as `reverted` on 2026-08-05 by moving the target ~1.3σ. But
   freezing has its own failure mode — holding to a stale mean is exactly what
   the trailing window exists to prevent — and n=1, with every other reverted
   exit on record profitable. Run both settings through the same backtest and
   report realised Sharpe, MDD, and the rate of loss-making `reverted` exits.
   The new `equilibrium_reestimated` field makes that rate countable from the
   ledger going forward. **Default action remains no change.**
6. ~~**Did the z-stop cut two winners?**~~ **ANSWERED 2026-08-04 by
   `stop_analysis.py` — see the evening addendum.** Across all five stops the
   median overshoot is 0.2σ and three of five fire within 0.5σ of the band, so
   the level is being honoured; 4 of 5 reverted but **ETC/KAS never came back**,
   which is the case the stop exists for. **`stop_z` stays at 3.5 and the
   defect is the sampling interval** (item 4). The framing below was written
   from two observations and is superseded by five — kept because the reasoning
   error, generalising from the two most recent trades, is the instructive part.

   Original framing: Both August stops were followed by full
   reversion. Aug 1 stopped long at z=−10.25; z was −1.03 seven hours later and
   +3.31 by midday. Aug 2 stopped short at +3.63; z read 3.34 → 2.99 → 2.73 over
   the next three bars. In both, the "relationship broke" hypothesis the stop
   encodes was wrong, and holding would have recovered. Together they realised
   **−16.10, the entire drawdown from peak.**

   The sharper form of the question: **MDD is scored on hourly NAV including
   unrealised P&L**, so at the trough the stop protected nothing — NAV had
   already fallen. What it did was forfeit the recovery. On these two trades it
   cost P&L *and* bought no MDD protection.

   **Do not act on this without the counterfactual.** n=2; judging insurance by
   the times it paid out badly is textbook outcome bias; and the −10.25
   excursion was genuinely violent — that is the LTCM failure mode `stop_z`
   exists for, and one path where holding worked says nothing about the next.
   What would make this actionable: measuring how far the spread actually
   travelled past each stop before turning, across every stop in the record,
   against the loss the stop realised. If stops consistently fire near the
   turning point, the band is mis-calibrated to the post-break `sigma_eq`; if
   the −10.25 case is the only one where it mattered, the stop is doing exactly
   its job at a fair price. **Default action remains no change.**
7. **Self-ranking endpoint into `status.py`** — carried twice now. Either do it
   or delete it from the agenda.
8. ~~**Put `fills_report.py` on a schedule**~~ **DONE 2026-08-02** — daily at
   23:55 UTC rather than weekly, since weekly would sit exactly on the ~7-day
   retention edge and one failed run would lose a week permanently. Verified
   firing 2026-08-03 (`fills_2026-08-02.json`, 23:55 mtime). Still open, and
   smaller: test whether `position history` retains longer than executions — if
   it does, week 1's trades may be partly recoverable.

### Deferred from week 2
- **Make `band_diagnostic.py` print the objective VALUE at each candidate band,
  not just the argmax.** The band flipped 0.6 → 0.4 on 2026-08-03 and it took
  two sessions to establish that the optimum is simply flat there. Printing the
  profit rate at 0.4 / 0.6 / 0.8 would answer it in seconds and turn a
  recurring mystery into a number. Deliberately NOT a numbered agenda item —
  it is a convenience upgrade to a hand-run tool, and week 3's numbered list
  already carries items on a scored dimension (AI reasoning depth) that matter
  more.
- Sentinel macro-event awareness (Fed/CPI are market-wide; our prompt is
  asset-specific and rates them `none`). Still undecided — the design question
  is whether market-wide risk should shrink size across all pairs, or whether
  the hedge already handles it.
- Droplet reboot (kernel update pending). Safer now that `needrestart` will not
  bounce the agent.
- Key rotation before Phase II.

---

## Week 2 agenda — review due Sun 2026-08-02 (COMPLETED — see the week 2 entry above)

Carried from week 1. Do these in order; the analysis gates the tuning.

1. **Trade-by-trade analysis with REAL fills** (the main event; deferred from
   week 1 for sample size). Pull execution history from the exchange
   (`rapidx order history` / execution list — check `rapidx schema --json`
   `inputSchemas` for `OrderHistoryInput` / `ExecutionListInput`) and reconcile
   against `deploy/ltp_ledger.jsonl`. Produce:
   - per-round-trip realised P&L, hold time, exit reason (reverted / stop /
     max_hold), win rate and stop rate;
   - **slippage**: intended price at decision (`enter` record's `price_a`,
     `price_b`) vs actual `executed_price` on the `operation` records — this is
     the repo's Phase-3 post-mortem input;
   - **funding carry**: total paid/received per pair over the period, so the
     unmodelled gap is finally a number;
   - fee drag per round-trip vs the assumed 5 bps taker.
2. **Has the news veto EVER fired?** `grep -c news_veto deploy/ltp_ledger.jsonl`.
   If it has never fired in weeks, its practical protective value is unproven,
   which further supports the fail-open decision — and is worth stating
   honestly in the post-mortem rather than assuming the gate is earning its
   keep. Also check `sentinel_degraded` events for any dark windows.
3. **Anomaly-veto rate**: `grep -c anomaly_veto deploy/ltp_ledger.jsonl` and read
   the rationales. If it is blocking entries that would have been profitable,
   tighten the prompt; the veto must stay rare and evidence-based.
4. **AI token spend**: `GET https://ai.ltp-contest.com/key/info` → `spend`.
   Confirm the depth layer sits comfortably under USD 10/day (expected ~72
   spread assessments + 24 news + 1 refit review per day). Also confirm the
   `ai_refit_review` / `ai_spread_assessment` records look substantive, since
   the audit judges *logical depth*, not volume.
5. **Entry/stop geometry — ONLY if (1) supports it.** NOTE: the premise here
   changed on 2026-07-28. Entry is no longer ~3.0 — the corrected optimiser
   chooses ~0.6, so `stop_z=3.5` now sits ~3 sigma away rather than 0.5. The
   old worry (entry too close to the stop) is gone; the new question is the
   opposite — whether a stop that far out lets losers run too long, given the
   trade profile is now many small wins against rare large losses. Needs the
   fills analysis, not a hunch. **Default action is no change.**
6. **Self-ranking endpoint into `status.py`** (small, deferred from week 1):
   surfaces rank, composite score, per-metric percentiles and AI cost directly.

### Deferred / open items (not scheduled, revisit if they matter)
- **Key rotation.** LTP and AI keys were pasted in chat. Mitigated by IP
  allowlisting to the droplet; the platform blocked config actions at launch.
  Do it when convenient: rotate in the LTP dashboard → update `/root/ltp.env`
  → `systemctl restart ltp-agent`.
- **SoSoValue / AIVIX data**: access secured, deliberately **not integrated**.
  The trigger to reconsider is evidence-based and specific: a pair stops out on
  a structural event that the news sentinel rated `none`, *and* their data
  flagged it earlier. Until that pattern appears in the ledger, leave it alone.
- `get_leverage` readback parses a dict but the API returns a list, so
  `set_leverage.py` prints `Nonex` (cosmetic only — the sets succeeded).
- Droplet has pending Ubuntu security updates; safe to apply and reboot (the
  service auto-starts and state survives).
- `deploy/ltp_state.test.json` / `ltp_ledger.test.jsonl` are archived
  pre-competition shakeout data, kept for the post-mortem.
