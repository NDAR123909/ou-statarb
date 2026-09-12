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
**NDAR**. Phase I (Sandbox Elimination) **Jul 20 – Aug 21 2026** — CLOSED, we
finished **#6 of 30 and advanced**.

**Phase II (Mainnet Duel Finals) runs 2026-09-09 → 2026-11-04.** ~~Sep 7 –
Oct 31~~ — **both** dates were wrong in this file since July; corrected from
the organizer's advancement announcement (start) and the Phase II welcome email
(end). The build window is **19 days**, not the 17 the agenda was written for.

**Phase II rules, from the organizer's welcome email 2026-08-27:**
- Scoring **unchanged**: ROI 20% + PnL 25% + Sharpe 40% + MDD 15%.
- Elimination **unchanged**: equity < 800 USDT / NAV < 0.8.
- **Maximum leverage 5× (was 2×). Violating it is DISQUALIFICATION.**
- **AI spend of at least USD 1 per day is now a formal written rule**, not an
  emailed warning. The daily pass built in August is exactly what this needs.
- **An AI agent is mandatory** and must be incorporated into *"data processing,
  algorithm training, or trading inference and decision-making."*
- **Choose Binance OR OKX perpetuals.** New — Phase I was Binance only.
- **One primary account.** No sub-accounts; ranking is that account alone.
- No deposits or withdrawals. AI tokens distributed "gradually starting this
  week", so new keys are imminent.

**DECISION: leave every symbol at 2× leverage despite the 5× allowance.**
Sharpe is scale-invariant, so leverage does nothing for the 40% term; it scales
PnL, ROI and MDD together. Phase I's lesson was **not** that we were
under-levered — it was that our **return per unit of drawdown was the worst of
the top four** (1.03 against 3.18 / 2.37 / 2.03). Levering a thin edge
amplifies both sides of it; at 2× sizing Phase I would have finished with
X-Explore's drawdown and half their return. Staying at 2× is also a hard rail
against an accidental DQ on live capital, for headroom we never used — peak
gross was ~1.06×. **If the platform resets symbol leverage for Phase II,
re-run `set_leverage.py` at 2×, not 5×.**

**Phase II is LIVE CAPITAL IN LIVE MARKETS**, not a sandbox: *"1,000 USDT in
live trading capital from LTP … live markets under institutional-scale
execution."* All scores reset to zero. This is not a continuation of Phase I
with a bigger prize; it is a different risk regime, and every Phase I
measurement taken in the sandbox is now a **prior, not a fact**:
- slippage measured at 0.57–0.91 bps was a sandbox number. Expect worse.
- funding and borrow become real costs rather than a rounding error.
- **the intra-bar monitor's value rises**, because the losses it prevents are
  now actual money — which raises the stakes on re-checking the −10.67
  overshoot figure *before* building it.
- risk appetite should go **down** on the first live days, not up.

**Phase I scoring stops at 23:59 GMT+8 on 2026-08-21 = 15:59 UTC** (organizer,
Telegram 2026-08-16). Converted here once so nobody re-derives it under time
pressure: that is **08:59 America/Denver**, i.e. Friday *morning* local, not
Friday evening. Consequences: the 23:50 and 23:55 UTC crons on 08-21 both run
**after** the bell, so their rows are post-phase readings and must be labelled
as such; and the last budget period overlapping scoring is 16:00 UTC 08-20 →
15:59 UTC 08-21, cleared by the 16:30 UTC 08-20 pass.

**Phase I scores do NOT carry into Phase II** — every team resets to 1,000 USDT
(organizer, 2026-08-13). Phase I is worth advancement and evidence, nothing
else. **Eliminated teams leave the Z-score normalization pool**, so our score
moves when other teams die; check whether the pool changed before reading a
score move as signal.

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
- **AI usage is a GATE, not a score term.** No AI term appears in the scoring
  formula, so **more spend never buys score**. But usage is an eligibility
  condition enforced by elimination at both ends: zero usage removes a team
  (organizer, Telegram 2026-08-12: teams at zero *"have already been eliminated
  in previous reviews"*, with more reviews at their discretion), and spend
  below USD 1 disqualifies. Pass/fail at the bottom, no reward above it.
- **Do not lean any argument on the "AI Engagement" column.** On 2026-08-13 it
  showed the #1 team at `0 | 0 | 0` — either a display bug or a team pending
  elimination — and an argument built on that row had to be retracted the same
  day.
- "AI Engagement" and "AI-Adjusted PnL" are **display only, not scored**, and
  the engagement figure is a **rolling window, not a cumulative total** — it
  fell 72k → 61k across 2026-08-02 with no change in behaviour. A drop there is
  not a fault.
- **A Sharpe of ±13.51 on the Phase II leaderboard is NOT a measurement — it
  is `sqrt(365/2)`.** Established 2026-09-10, day 2 of the phase, when six of
  the visible top ten showed exactly ±13.51. That value is what two completed
  daily returns produce **when one of them is flat**, and it is *independent of
  the size of the move*: +2.6% and +50% both give 13.51. Derivation, with
  r = [x, 0]: mean = x/2, stdev(ddof=1) = |x|/√2, so mean/stdev = sign(x)/√2
  and × √365 gives sign(x)·13.509 for any x whatsoever.

  The proof was sitting at rank 4: **Poetikrule, −0.0% return, −0.16 PnL,
  ranked fourth** on a Sharpe that is a constant. Only four values on that
  board carried information (X-Explore 3.78, NeuPortal −10.28, btcol −13.74,
  Quantech −32.61); the rest were arithmetic. **Before reading any early
  leaderboard, check how many teams share an identical Sharpe** — and note
  that a two-day artifact collapses the moment a third distinguishable day
  lands, exactly as ours went 9.30 → 5.66 on one −0.8% day.
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
- **Leverage**: Phase II permits **5×**; we run **2×** by the standing decision
  above, which is *ours*, not the venue's cap. Re-applied to **30** symbols at
  the 2026-09-08 cutover via `deploy/set_leverage.py`, 0 failed. (The whitelist
  was 28 on 2026-07-20 and has grown since — trust the script's count over any
  number written here.)
- **Never place manual orders through the LTP web UI** — an unlogged order
  breaks the reasoning audit.
- Data partners (SoSoValue, AIVIX) are *market data*, not AI models, so they are
  compliant — but we deliberately do **not** use them (see Deferred).

**Useful endpoints. THE TRADING HOST CHANGED AT THE PHASE II CUTOVER.**
- **Trading / account: `https://api.liquiditytech.com`** (production), set as
  `LTP_API_HOST`. Phase I ran on `https://api.ltp-contest.com`, which is the
  **sandbox/contest** domain and answers a production key with
  `100018 API not exist`.
- **AI gateway: `https://ai.ltp-contest.com` — did NOT move**, and still
  authenticates. The two domains have **diverged**; do not "tidy" one to match
  the other.
- Self ranking: `GET {LTP_API_HOST}/api/v1/tracka/ranking/self?phase=PHASE_II`
  (V2 signature: `X-MBX-APIKEY`, `nonce`, `signature`; portfolioId derives from
  the key). Error 30016 = wrong key or T+1 data not ready.
- AI spend: `GET https://ai.ltp-contest.com/key/info` → `spend` field. The
  budget period rolls at **00:00 GMT+8 = 16:00 UTC** — the competition day, not
  the UTC day. Confirmed by direct observation across the boundary 2026-09-08.

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

### Deployed, verified, and one more hardcoded number removed

Crons installed and confirmed by `crontab -l`: two `ai_deep_review` entries, no
duplicates. `--floor 1.05` correctly refused to spend at $1.20925, and the new
`ai spend` line reads *"$1.2093 — clears the $1.00 floor"*. First live pass
2026-08-13 16:30 UTC.

Two defects found by looking at the real crontab rather than remembering it:
the cron block I wrote **used `\` line continuations, which cron does not
honour** — every entry would have truncated at the backslash, installed
cleanly, listed cleanly, and done nothing. And my lines wrote `ltp_ai.log`
**into the repo**, where nothing ignored it and one `git add -A` would have
committed a growing log of raw AI output into the track record. Both fixed;
`*.log` is now in `.gitignore`, and the README block is transcribed from the
installed crontab rather than written from memory (it had the fills job's flags
wrong too).

**Live reading at 2026-08-13 00:40 UTC — supersedes the week 3 numbers:**
equity **1016.66** (was 1024.78), peak 1041.19, drawdown **2.36%** (was 1.58%),
headroom 100.41 to the kill switch and 216.66 to the 800 floor, one pair
active, service up since 08-09 with `NRestarts=0`. Under the 3.7% banked MDD,
so nothing here is actionable — but −8.12 in four days is real and the record
should not keep quoting the older figure.

That drift also exposed **the same rot I had fixed one line above and left in
place**: `EQUITY_AT_REVIEW = 1024.78` was hardcoded into the reviewer's
constraint prompt, so the daily pass would have claimed 224.78 of headroom
against a real 216.66 — small next to this morning's 2× error, but growing
daily. Equity is now read live (`live_equity()`), the constant survives only as
a **labelled** fallback that tells the reviewer its own date when the meter is
unreadable, and `followups()` substitutes it via a named `CONSTRAINT_INDEX`
rather than a bare index that would silently point at the wrong prompt if a
question were inserted above it. 185 tests.

### Incident 2026-08-13 — a command I supplied deleted the whole crontab

**All four cron jobs were wiped.** The fix I handed over was
`crontab -l | sed … | crontab -`. The paste broke across a newline, sed died
with *"unterminated `s' command"* and produced no output, and **`crontab -`
installed that empty output** — which deletes every job. `crontab -l` came back
silent.

Cost: nothing, by luck. The wipe fell around 16:35 UTC and the next scheduled
job was 20:30, so no run was missed and the pass already running (pid 41532)
was unaffected — a running job holds no reference to the crontab. Had it landed
after 23:00 it would have taken the 23:55 `fills_report` with it, and that
evidence expires in ~7 days and cannot be re-fetched.

Restoring exposed a second failure: **`/root/cron.bak` was captured before the
2026-08-12 `&&`/log-path fix**, so the restore silently rolled that fix back.
Caught by reading the output, not by anything automatic.

**Two rules now in `README_ltp.md`:**
1. **Never install a crontab through a pipeline.** Write to a file, `cat` it,
   install, verify. A pipeline into `crontab -` has a failure mode of total
   loss and a success mode that saves four keystrokes.
2. **Refresh `cron.bak` after every verified change**, or the backup becomes a
   time machine to a bug you already fixed.

The generalisable form, and it is not "paste more carefully": *a recovery
command must not have a destructive failure mode.* I optimised a one-liner for
brevity in a situation where brevity was worth nothing.

Also shipped from the same run: **`-u` on both review cron lines.** The log was
empty while the process was demonstrably alive — Python block-buffers stdout
when redirected to a file, so nothing appears until a 4–8KB flush and
everything is lost if the process dies. A log that is invisible exactly when
you need it is not a log.

**And the false-alarm window is closed.** The 16:28 UTC glance read
`** $0.0007 — BELOW the $1.00 floor **`, which was correct, useful once, and
would have been correct-and-useless every morning between the 16:00 reset and
whenever the pass finished. A warning that fires daily on schedule teaches the
operator to scroll past it — the same way the news-gate blind spot would have
returned. `floor_state()` now reads `budget_reset_at` and `budget_duration` and
reports `clear` / `pending` / `short` / `unknown`; `status.py` only alarms and
only exits non-zero on the last two. `pending` covers the first 5 hours, which
outlasts both scheduled passes (+0:30 and +4:30). **A period whose age cannot
be established reads `short`, not `pending`** — suppressing an alarm on
ignorance is the exact failure the guard exists to prevent. 188 tests.

**Repo note:** PR #27 merged while this work was in flight, and the local
checkout was moved onto main's tip, so a session's edits were briefly being
written against a version six commits stale. Nothing was lost — the remote
branch held everything — and main was merged into the branch rather than
rebased onto it, because the droplet is live on this branch and the week 3
force-push cost a `git reset --hard` there.

### 2026-08-13, first full daily pass: 67% analysis, 33% labelled volume

The pass ran to target and the log pins the split exactly:

```
line 258:  -- 36 distinct topics exhausted below target; repeating as pass 2.
target $1.15 reached at $1.15357
calls: 376   spend: $0.00075 -> $1.15357  (+$1.15282, $0.00307/call)
```

**36 distinct topics** — 15 pairs × 2 angles, 2 ledger topics, 4 strategy —
× 7 rounds = **252 calls of material that did not exist yesterday**. Reaching
the target took **124 more** over the same ground.

| | calls | cost | share |
|---|---|---|---|
| distinct material | **252** | ~$0.77 | **67%** |
| labelled repetition | **124** | ~$0.38 | **33%** |

So two-thirds of the daily dollar is genuine and one-third is compliance
volume, and the third is stamped `pass_index=2` in the ledger and announced in
the log. **This is a measurement, not an estimate**, and it is the number to
quote if anyone asks what the spend bought. Also worth noting:
`ledger_prompts()` returned 2 topics, so the quiet-day fallback did not fire —
there was real activity to review.

**Decision: do not close the 33%.** Reaching $1.15 on distinct material alone
needs ~18 more topics, and there is a legitimate candidate (a third angle on
cross-pair redundancy — whether the 15 candidates are 15 independent bets or
four bets in fifteen costumes, which we have genuinely never checked and which
bears on breadth, our binding constraint). It was declined on priority, not on
merit: **8 days remain and the week 4 agenda carries two items with measured
payoffs.** Broadening a compliance script ahead of those would be choosing the
tidier problem over the valuable one. Revisit for Phase II, where the daily
floor will run for two months rather than a week.

### The AI-spend-hurts-our-score worry, closed — but not for the reason I first gave

The operator asked whether the jump to ~$1.15/day had cost us score. It has
not. My first answer leaned hardest on an argument that does not survive, and
the retraction is recorded before the conclusion.

> **RETRACTED, same day.** I wrote: *"T.Anh sits at #1 with AI Engagement
> `0 | 0 | 0`. If engagement were scored, a team with none of it could not
> lead."* The operator then supplied a 2026-08-12 organizer exchange on
> Telegram:
>
> > **Mark Cooper:** When do the zero ai use teams get removed from the LB?
> > **Liquidity Arena:** Teams with zero total AI usage have already been
> > eliminated in previous reviews. We'll conduct another review today, and if
> > any teams are still at zero AI usage, they will be eliminated accordingly.
>
> So T.Anh is either a **display bug** or a team **pending elimination**.
> Either way the row proves nothing about scoring, and it cuts the opposite way
> from how I used it: zero AI usage is an **elimination criterion**, which is
> precisely the kind of AI-linked rule I was asserting did not exist.
>
> **Also withdrawn on the same grounds:** the *"our `AI-Adj PnL` haircut is the
> smallest in the top ten (0.02 vs T.Anh's 0.85)"* argument. It compares against
> a row I have just said is untrustworthy.

**The reframe, which is the right model: AI usage is a GATE, not a score term.**
Zero usage → elimination. Below USD 1 → elimination. Pass/fail, with no points
for exceeding it. That reconciles both facts without contradiction — the
scoring formula genuinely has four terms and none is AI, *and* the organizers
genuinely eliminate teams on AI usage. Add it to the standing rules: **more
spend never buys score; too little ends the competition.**

What the conclusion actually rests on, after the retraction:

- **The published formula has four terms** — Sharpe, PnL, ROI, MDD — none of
  them AI. Rule text, not an inference from one leaderboard row.
- **The timing is wrong by a week.** Score was 94.4 (#2) on 08-02 and #6 by
  08-04; the spend increase was 08-12/13.
- **MDD accounts for the whole decline on its own** — see the next section.
- The one mechanism that could have bitten — the review pass throttling the
  agent's own hourly assessments through the shared gateway — was checked
  rather than argued: `sentinel_degraded` **0**, `ai_assessment_unavailable`
  **0**, across 376 calls in three hours.

Two operational consequences from that exchange, both worth more than the
retracted argument was:

1. **The reviews recur and their timing is the organizer's discretion**
   (*"we'll conduct another review today"*). That is a better justification for
   clearing the floor every period than the one given on 08-12, which reasoned
   from the meter's shape alone.
2. They say *"zero **total** AI usage"* — so whether they read a lifetime total
   or a per-period figure is **still unresolved**. Clearing USD 1 every period
   satisfies both readings, so the current arrangement is safe under either;
   but this sharpens the open commitment to just ask them.

**Method note, and it is the third of its kind this week.** 08-04: compared two
runs of a tool whose column labels I had changed between them. 08-12: conflated
our kill switch with the elimination floor. Now: took a leaderboard cell at
face value without asking whether that row was valid. Same shape every time —
**reaching for the tidiest available data point before checking whether the
instrument means what it says.** The conclusions have survived; the supporting
arguments keep not surviving. The fix is not more careful retracting, it is
asking "what would make this number wrong?" before it goes into the record.
**Do not lean any future argument on the AI Engagement column.**

### Leaderboard 2026-08-13 — and MDD is what actually moved

**#4 of the field, score 86.9** · Sharpe **3.16** · MDD **3.7%** · PnL
**+20.30** · ROI **+2.0%** · 105 trades · ann. return +28.5%. (An earlier
reading the same day showed 86.5 / 2.94 / +19.65; **the metrics rose across
the window the first daily AI pass ran in**, which is one more thing the
spend-hurts-score story has to explain away.)

| | T.Anh #1 | btcol #2 | Supes #3 | **NDAR #4** |
|---|---|---|---|---|
| Score | 95.2 | 92.0 | 88.4 | **86.9** |
| Sharpe (40%) | 4.00 | 4.57 | 2.43 | **3.16** |
| MDD (15%) | 3.8% | 1.3% | 2.6% | **3.7%** |
| PnL (25%) | +58.71 | +26.53 | +24.91 | **+20.30** |
| ROI (20%) | +5.9% | +2.7% | +2.5% | **+2.0%** |

**#3 is 1.5 points away and #5 is 1.8 behind** — Krosus at 85.1 with MDD 1.0%.
This is a tight band, not a settled position.

**We out-Sharpe third place and rank below them anyway.** The gap is size and
MDD — and MDD is the one that used to be ours. It read **1.3%, best in the top
10, on 2026-08-02**; it reads **3.7% now, second-worst**, while btcol holds
1.3%, Krosus 1.0% and PSJeevaa 0.9%. Two stop-outs in early August spent it,
and because MDD is monotonically non-decreasing **that 15% of the score cannot
be earned back this phase.**

This is the single most consequential fact on the board and it should open the
Sunday review. It also sharpens week 4 item 1: the intra-bar monitor's entire
case is that roughly a third of losses came from stops firing late, and late
stops are exactly what banked this number. The counter-argument — that with
3.7% already banked, further drawdown *below* that level costs nothing in the
scored metric — is now load-bearing rather than academic, because we are past
the point where MDD protection buys anything back.

### The refit-cadence premise has inverted — and it was load-bearing

Prompted by the operator asking whether the review layer could be suppressing
entries (it cannot — see below), the fills report was re-run. **Five round
trips, 2026-08-07 → 08-12:**

| date | pair | exit | hold | gross |
|---|---|---|---|---|
| 08-07 | KAS/ETC | refit_drop | 24.0h | −2.49 |
| 08-08 | FIL/AR | **reverted** | 26.0h | **+6.29** |
| 08-10 | FIL/AR | refit_drop | 10.0h | +2.46 |
| 08-10 | XLM/XRP | **stop** | 11.0h | **−5.61** |
| 08-12 | XLM/XRP | refit_drop | 23.0h | −0.24 |

Gross **+0.41**, fees **1.52**, **net −1.10**. Fees are **366% of gross** — the
book is currently paying more to trade than the trades earn. The single stop
carries 67% of losses. Funding **+0.337** received; slippage 0.91 bps (was
0.57).

**Two numbers that a week-3 decision rested on have both inverted.** The
operator's proposal to lengthen the refit interval was declined on this exact
reasoning, quoted from the week 3 entry: *"Median hold **2.0h** against a 24h
interval; refit-drops are **~10%** of closes."*

- **median hold is now 23.02h** — essentially the 24h refit interval itself
- **`refit_drop` is 3 of 5 exits, 60%** — not 10%

Positions are no longer reverting and closing on their own; they survive to the
next refit and are dropped by it. **Four of five exits are plumbing** (stop,
refit cadence, band geometry) against one that was the edge — and that one was
the only clean winner.

**No change made, and lengthening the interval is not obviously the fix**:
one of the three refit_drops was a **winner** (+2.46) closed early, and n=5 in
the low-cointegration stretch. But the decision was made on a premise that no
longer holds, so it is re-opened rather than inherited. **Week 4 agenda item
0b.**

### The review layer is advisory — verified, not asserted

The operator asked whether `ai_deep_review` could suppress entries, noting that
if it could, we would have a layer recommending "stop trading" on the basis of
a portfolio we do not hold and a risk budget I had described wrongly for a
whole pass. Checked three ways:

1. **Nothing imports it** except `status.py`, which reads the spend meter for
   display. `ltp_agent.py` contains no reference to it.
2. **The agent never reads the ledger.** `_LEDGER_PATH` appears exactly twice
   in `ltp_agent.py`: the constant, and `open(_LEDGER_PATH, "a")`. Its only
   file reads are `ltp_state.json` and `ltp_hwm.json`.
3. **Separate processes** — systemd pid 715 versus a cron-spawned process that
   exits. No IPC. Pinned by `test_it_places_no_orders_and_touches_no_agent_state`.

Worth recording because it is counter-intuitive: the one indirect channel
**fails open, not closed.** If the review pass exhausted the gateway the news
gate goes dark, and the week-1 decision was fail-open — the agent keeps trading
at full size, unscreened. Gateway contention cannot produce "stop trading"; it
produces the opposite.

**Shipped from the same question — `SPEND_CEILING = 8.00`.** The only bound was
`--target`, so a future raised target could have eaten the agent's allocation.
The ceiling is enforced independently of `--target`, reserving ≥2.00/day
against measured agent burn of ~0.04–0.08/day, and
`DAILY_TARGET < SPEND_CEILING < 10.0` is pinned so nobody can raise the target
past the reserve without CI going red. **An unreadable meter does not stop the
run** — missing the floor is disqualification while overspending only darkens a
fail-open gate, and `--max-calls` (600, ~1.80 USD) is the backstop that makes
blind running safe.

### A third hardcoded-number rot, in the reviewer's own briefing

`strategy_prompts()` was telling the model *"13 round trips… median hold 2.0h…
ZERO trades have ever hit the max-hold clock"* — a week after the median hold
became 23h and refit-drops became the majority exit. **The reviewer was being
briefed on a strategy that had stopped behaving that way**, which devalues
every answer it gave about hold times and band geometry. Same failure as
`days_left()` and `EQUITY_AT_REVIEW`, third instance.

`record_facts()` now derives the block from the newest `track_record/fills_*.json`
snapshot — round trips, exit mix, gross/fees/net, win rate, median hold,
measured fee, slippage, funding — and states outright when fees exceeded gross,
which is the sort of thing a reviewer derives late or not at all. When no
snapshot is readable it falls back to the 2026-08-09 figures **and labels them
dated**, the same contract as the equity read. 191 tests.

### 2026-08-14 — the news gate goes silent when the book is idle

The 17:58 UTC glance read `news gate ok — 2 assets rated @ 2026-08-13T20:01`.
**Twenty-two hours old, rendered as `ok`.** The ledger tallies prove it was not
a display artefact:

| | 08-13 16:28 | 08-14 17:58 | Δ |
|---|---|---|---|
| bar | 405 | 430 | **+25** |
| `news_assessment` | 340 | 344 | **+4** |
| `ai_spread_assessment` | 458 | 462 | **+4** |

Twenty-five bars, four assessments — and the four line up exactly with the
hours XLM/XRP was alive before the 21:00 refit dropped it. Cause is one line in
the bar loop (`ltp_agent.py`): `assets = active_assets()` then
`if assets: sentinel.refresh(assets)`. **Zero active pairs → no refresh.**

Three consequences, in order of weight:

1. **A pair selected out of a drought is entered on verdicts that never covered
   it.** `active_assets()` is computed *before* `trade_step`, and `trade_step`
   runs the refit that adds pairs. So on the bar a new pair is selected and
   entered, the sentinel holds the old asset list — or nothing — and
   `screening_provenance` stamped that entry `news_status: ok`. Same defect
   class as the four logging gaps: **a control that appears to have acted and
   did not.** No money lost — the news veto has never fired — but it is audit
   exposure of exactly the kind Track A correlates.
2. **During a drought our own AI usage falls to ~zero**, and the organizers
   eliminate teams at zero usage (Telegram, 08-12). Droughts here have run 3+
   days. **Without the daily review pass a long idle stretch could have walked
   us into the zero-usage elimination with the glance showing a healthy agent.**
   That is a materially stronger justification for the daily pass than the one
   written on 08-12: it does not top up a floor the agent nearly reaches, it
   **carries the floor entirely whenever we are flat.**
3. **The review layer buried the daily glance.** 968 `ai_deep_review` rows
   against 29 `enter`; `--ledger 20` returned 20 of 20 advisory rows. The
   operator's decision-history view was unusable. My regression, from 08-13.

**Shipped (logging and display only — `screened` and `news_status` are
write-only, confirmed by grep, so nothing here can reach trading):**
`NEWS_STALE_H = 2.0` and `verdict_age_hours()`; provenance now reports
`stale` / `missing_legs` with `news_age_h`, `news_refreshed_at` and
`news_unrated_legs`, and sets `screened: False` for both — **with degraded
status taking precedence**, so a quota outage still reports `quota` rather than
losing the cause behind a symptom (an existing test caught that and was right).
`status.py` prints the gate's age, renders `STALE` past the threshold, and says
whether the cause is an idle book or a genuine failure to refresh with pairs
active. `GLANCE_HIDE` keeps advisory rows out of the tail while the tally still
counts them. 194 tests.

**NOT shipped, and it is week 4 item 0c:** refreshing the sentinel for a newly
selected pair *before* screening its first entry. That is the actual fix and it
touches the entry path with a week left, so it goes to Sunday with the other
behavioural decisions rather than being shipped on a Friday evening.

### A cosmetic bug that stopped being cosmetic

The 18:11 restart landed on **bar 432**, an exact multiple of the 24-bar refit
interval, and the glance read *"next in 24 bars"* while `refit:28` said none had
run. That looked like a restart had skipped a refit and left us idle a full
extra day in the middle of a drought.

It had not. `ltp_agent.py:1143` tests `state["bar"] % refit_every_bars == 0` at
the **top** of an iteration and increments at the bottom, so the persisted bar
is the one the next iteration checks. At 432 the refit was one bar away, not
twenty-four. The display was computing `(every - bar % every) % every` and then
rendering the resulting 0 through `nxt or every` — a fallback meant for "just
refitted" that at the boundary says exactly the opposite of the truth.

Fixed as `bars_to_refit()` with the boundary rendered as **"refit runs NEXT
bar"**, pinned by a test. Filed here because the lesson is not the one-line fix:
**a display that is wrong only at a boundary is wrong exactly when someone is
looking hard at it.** This one cost a debugging round on the day a restart
happened to land there. 195 tests.

### 2026-08-15 — this has been a single-pair strategy for its entire life

The operator pulled every `ai_refit_review` record and read the `passed` column
across the competition. It is the most important thing measured this week, and
no daily glance could have shown it.

**22 scored refits, 2026-07-26 → 2026-08-15:**

| pairs passed | refits | share |
|---|---|---|
| 3 | 1 (Jul 26, day one) | 5% |
| 2 | 2 (Jul 27, Aug 1) | 9% |
| **1** | **13** | **59%** |
| 0 | 6 | **27%** |

- **Mean 0.91 pairs per refit.** Modal outcome is exactly one.
- **`tested` is 15 on every refit but one** (14 on Aug 5). The universe never
  shrank, so the zeros are cointegration genuinely failing, not candidates
  going missing. That closes the refit review's own stated caveat.
- **Overall pass rate 20 / 329 ≈ 6%.**
- **Only 5 of the 15 candidates have EVER passed**: AVAX/SOL, FIL/AR,
  TAO/RENDER, KAS/ETC, XLM/XRP. **Ten have never once cleared the gate in
  three weeks.**
- **AVAX/SOL appeared in all 11 refits from Jul 26 to Aug 4 and was the sole
  survivor on 8 of them** — then never passed again after Aug 4.
- Zero-pair refits are **not unusual**: six of 22. The current run of three
  consecutive is the longest, but the prior record was two (Aug 5–6), broken
  the next day.

**The reframing, and it is harsher than the "unfavourable regime" reading the
AI refit review gave:** the current dry spell is not a departure from a healthy
state. **The gate has been passing 0–1 pairs out of 15 for three weeks.** The
recorded Sharpe came from one position at a time with fourteen candidates idle.
Every diversification claim in the design is aspirational rather than realised
— disclosed in LTP_STRATEGY.md, because the pre-registration names *"breadth
across 14 sector-restricted pairs"* as the profitability mechanism and that is
now falsified by measurement.

**Decision for Phase I: change nothing.** The universe is stable, the gate is
not miscalibrated, the refit review says adjust nothing, and this pass rate is
normal for this setup rather than degraded. With six days left, loosening a
screen would spend a 3.7% MDD we cannot recover chasing a pair the pipeline
says is not there. **But keep the two questions separate:** "do not loosen the
gate" and "do not widen the universe" are different decisions. Widening adds
hypotheses, which BH-FDR correctly penalises — it is not cheating. It also
cannot produce judgeable evidence in six days. So it is **Phase II design
work**, where a single-pair book running eight weeks is a structural fragility
rather than an observation.

### Method note — substring-grepping the ledger is now unsafe

The same pull turned up four `ai_refit_review`-matching rows with `tested:
None`, which looked like refits that had failed to record a result — invisible
zeros that would have corrupted the distribution above.

They were not. The operator's filter was `if 'ai_refit_review' in line`, and
**the ledger now contains long AI prose that names our own event types**: an
`ai_deep_review` response discussing the schema matches that filter. The
arithmetic gave it away before any command did — the grep returned 26 rows,
`status.py` counts `ai_refit_review: 22`, and all four extras resolve to
`ai_deep_review` at timestamps inside daily review passes.

This is the 2026-07-27 `severity` trap on a new surface, and worse now that
~1,500 review rows carry paragraphs of text. **Parse each line and match on
`d["event"]`; never `in line`.** The event tally in `status.py` remains the
reliable probe.

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
| **Rotate credentials — now four, not two.** (1) the July LTP + AI keys pasted in chat; (2) **the Phase II production key AND secret**, pasted in chat at the 2026-09-08 cutover — the same mistake, made again, by the session that was reading the rule; (3) the GitHub PAT, expired 2026-08-27. Mitigated but not fixed by the IP allowlist (`68.183.209.2`) and by Withdraw/Transfer being OFF on the production key | 2026-07-20, re-opened 2026-09-08 | **the "before Phase II" trigger has passed.** Next window the operator is at the droplet with time; the trading key is the urgent one because it can trade |
| **Give the droplet a non-interactive git credential** (deploy key or stored PAT), then extend the 23:50 UTC cron to `git add track_record/ && git commit && git push` | 2026-07-30 | next time the operator is at the droplet terminal — until then `ltp_state_history.jsonl` exists only on that machine |
| ~~Re-check rank~~ **DONE 2026-08-02**: #2 of 29, score 94.4 | 2026-07-30 | closed |
| ~~Restore `risk_per_pair` 0.002 → 0.004~~ **APPROVED 2026-08-02, HELD the same evening, and DECIDED AGAINST at the 2026-08-09 review** | 2026-07-30 | **closed.** Sizing is scale-invariant in Sharpe, so a restore buys the 45% of the score made of PnL and ROI while doing nothing for the 40% made of Sharpe, and roughly doubles the MDD we still lead on. The organizer's 2026-08-04 Quant Tip reaches the same place from the scoring side. Re-opening this needs a new argument, not the old one |
| **Report the header-only CSV exports to the organizers** — order, transaction and position history all export zero rows | 2026-08-02 | next organizer contact; a broken data export in a competition judged on auditability is worth raising |
| **Decide on the sub-hourly risk check** (read-only pass that may only close or stop, never open). ~~Measured cost of not having it: −10.67 across five stops, ~a third of all losses~~ **AUDITED 2026-09-09 — see that entry.** −10.67 reproduces but was frozen at five stops on 08-02; the full record is **−18.71 across eight**, and −10.67 is **16%** of all losses, not a third. Four of eight stops never reached 4.0σ, so the ceiling on a perfect monitor is **−6.30**, 69% of it one event, and the recoverable fraction is unmeasurable from hourly data — **[0, −6.30] at every cadence**. The tool's own verdict flips on the complete record to *"the stop is doing its job; leave it alone"* | 2026-08-02 | **decide at the Sun 2026-09-13 review.** Recommendation on record: **drop the monitor, ship sub-hourly z logging on open positions instead** (~90 min) — bounded benefit against an entirely unmeasured false-positive cost, in a new code path that closes live positions |
| ~~Schedule `fills_report.py`~~ **DONE 2026-08-02**, daily at 23:55. Without it this week's loss attribution would not exist — retention had already eaten the live window | 2026-08-02 | closed |
| ~~Restart for `taker_fee`~~ **DONE 2026-08-02 20:54** | 2026-08-02 | closed |
| ~~Restart for `side_blocked` logging~~ **DONE 2026-08-09 23:28** — live now, dormant until a block actually declines a signal | 2026-08-08 | closed |
| ~~`dist-upgrade` + reboot~~ **DONE 2026-08-09 23:28** — kernel 6.8.0-136 → 137, zero updates pending, banner cleared. Second clean reboot: NRestarts=0, peak 1041.19 and the bar counter both survived | 2026-08-06 | closed |
| **Re-merge the fills snapshots weekly** for the loss attribution — the live report only reaches back ~7 days | 2026-08-09 | each review, before writing the numbers down |
| **Synthesise the 399 deep reviews** — where they converge, where they contradict each other, which claims survive contact with the others. Discount the round-5 layer, which reasoned from the understated headroom | 2026-08-12 | Sun 2026-08-16 review. Until it exists, no claim from that run has been acted on |
| ~~Reply to LTP with the BSC USDT deposit address~~ **SENT 2026-09-02, ~5 hours late.** Deadline was 19:00 GMT+8 = 11:00 UTC = 04:00 local; sent ~16:00 UTC. Low consequence — it was administrative batching for account setup, not an eligibility condition like the Reasoning Log, and Phase II does not open until 09-09. **UI note for next time: the button is "Top up", not "Deposit"** (Asset Center → Funds account → Top up → USDT → BSC/BEP20); generating the address sends nothing | 2026-08-27 | closed |
| **Surface dated commitments in `status.py`** — this deadline was written down, with the local-time conversion done in advance precisely so it could not be misread, **and it was still missed, because the record is passive and never alerts.** Show any commitment falling due inside 72h in the daily glance the operator already runs | 2026-09-02 | build window, before 09-09. It would have caught this one |
| **Check AI `spend` against BOTH ends of the band** (min USD 1, max 10/day) at every review — the floor is what nearly disqualified us on 2026-08-12 | 2026-08-12 | every review, and before Phase II opens. Now also automated: `status.py` exits 1 below the floor |
| ~~**Verify the two spend crons actually fired** and that the second no-ops rather than double-spending~~ **CLOSED 2026-09-08.** Both fired; spend landed at **$1.1553** against `DAILY_TARGET` 1.15, so the 20:30 pass (invoked `--floor 1.05`) did nothing. A double-spend would read ≈$2.30. Log is `/var/log/ltp_ai.log` | 2026-08-12 | closed — see the Day 1 close-out |
| **Ask the organizers whether the USD 1 floor is daily or was one-off enforcement, and whether they read a lifetime total or the per-period meter** — their 2026-08-12 Telegram reply says "zero **total** AI usage", which does not settle it. Clearing 1.00 every period is safe under either reading, but that is an assumption. Rides along with the header-only CSV report we already owe them | 2026-08-12 | next organizer contact; draft is written when the operator wants it |
| **`ltp_stream.py:31` hardcodes `wss://feeds.ltp-contest.com`** — the contest domain, which the cutover moved *away* from everywhere else. No env change reaches it; if that domain is retired now production is live, `NewsStream` goes silent and only a code edit fixes it. Proposed change: an env lookup mirroring `ltp_news.py:50` | 2026-09-08 | needs the operator's go. Wait for one live news-gate reading first — if the gate is healthy, this is precautionary rather than urgent |
| **Verify `ltp_news.py`'s `FEEDS_BASE` against the production host** — it follows `LTP_API_HOST` so it moved with the cutover, but nothing has confirmed `api.liquiditytech.com` serves the feeds path at all | 2026-09-08 | first hourly tick after 2026-09-08 15:37 UTC. `status.py`'s news-gate line answers it |
| **`deploy/README_ltp.md:20` still documents `LTP_API_HOST=https://api.ltp-contest.com`** — the sandbox host. A future session following the setup block would rebuild the exact failure we just spent a day diagnosing | 2026-09-08 | next doc pass; trivial, but it is a trap laid for a cold reader |
| **Re-run `universe_scan.py`** now that ETH/BTC is actually fetched. The 2026-09-09 run's CURRENT line (`0/14`) excluded the pair carrying the book and cannot be quoted until this is done | 2026-09-09 | next droplet session, avoiding ~15:38 UTC (refit) |
| **Rule out a data cause for the 0/54**, before "regime" is written down as fact. ETH\|BTC passed 09-07, then 0/15 and 0/54 within 36h — coinciding exactly with the host change. Compare klines from `api.liquiditytech.com` against a known 09-07 fit | 2026-09-09 | before any decision rests on the regime verdict |
| ~~**Enumerate the orderable instrument set**~~ **PROBED 2026-09-10.** No listing action exists in any of the 53 capabilities — enumeration is a name-by-name probing exercise with `get-symbol-info` as the oracle. `OKX_PERP_CL_USDT` (WTI crude) is **live and reachable** | 2026-09-10 | closed as a question; the blocker below replaces it |
| ~~**Chase `market.klines` for the OKX adapter**~~ **RESOLVED 2026-09-10** — we were on CLI **1.0.41**, three versions stale. `npm install -g @liquiditytech/rapidx-cli@latest` → 1.0.44, OKX klines return data. Binance path verified unchanged before restart | 2026-09-10 | closed |
| **DECIDE: stratified FDR, or keep one pooled family.** CL/BZ (WTI/Brent) passes every economic and statistical gate — hurst 0.35, hl 23.9h, beta +0.95, 54 crossings, adf p=0.026 — and is rejected **only** by Benjamini-Hochberg at m=66. Correcting within pre-declared economic strata is standard where hypotheses are not exchangeable, and the driver groups predate these p-values. **But we would be restructuring the family because a result we liked got rejected** | 2026-09-11 | **Sun 2026-09-13 review.** Pre-committed test: run both ways on the same panel and compare what ELSE passes, not just whether CL/BZ does. One pair clearing a looser correction is not evidence. Invariant 3 stands until a written decision says otherwise |
| **Check whether the SPX contract tracks its underlying.** Four non-crypto pairs died on `beta out of range`, all SPX, including MSFT/SPX at adf p=0.0133 — the best p-value of the eleven — with beta +0.03. An index against its largest constituents should not have a hedge ratio of 0.03, and the fit is on log prices so raw scale is not the cause | 2026-09-11 | before anything is built on SPX. One correlation check against AAPL/MSFT/NVDA returns |
| ~~**Ask whether the portfolio may trade BOTH venues**~~ **ANSWERED 2026-09-11: both, one portfolio, perpetuals only.** No venue decision to make; take the union, 62 bases. NG joins energy (1 pair -> 3) and ~52 same-underlying cross-venue pairs become formable | 2026-09-11 | closed |
| **Two-venue execution is unmodelled.** A cross-venue pair has legs on two venues; a fill on one without the other leaves a naked directional position, and the maintenance-window guard reasons about one venue's blackout. The scan can now find such pairs before the agent can trade them safely | 2026-09-11 | **before any cross-venue pair reaches `CANDIDATES`.** Not urgent while cost_z likely refuses them anyway |
| **Chase the OKX 300-bar klines cap.** Binance returns 1000 on an identical request; OKX returns 300 for symbols with years of history. `KlinesInput` is `additionalProperties: false` with only symbol/interval/limit, so pagination cannot be expressed, and `limit` carries no documented maximum — a bug, not a feature request. Raised 2026-09-10 | 2026-09-10 | **still blocks the universe scan.** 300 bars = 12.5 days, which silently narrows the effective half-life band to ~6–48h. **Do not scan OKX at 300 bars and report the result as a regime measurement.** Re-test on each RapidX release |
| **Verify OKX instruments are actually ORDERABLE**, not merely readable. `symbol-info` succeeding is not proof; the organizer's test is "any instrument you are able to place orders on". The check is `order place-preview`, classed **TRADE_WRITE** — decide it deliberately at a review, not casually against live capital | 2026-09-10 | Sun 2026-09-13 review |
| **Scan the full Phase II universe, grouped by DRIVER not venue.** The top-50 whitelist is gone and the organizer confirmed (2026-09-09) that **any orderable instrument counts, crypto or not** — commodity and tokenised-equity perps score identically. The 0/55 result is a **one-factor** problem: every crypto perp shares BTC beta, so widening within crypto cannot fix it. Non-crypto breaks the factor | 2026-09-09, reshaped 2026-09-10 | highest-priority research item. Hedges recorded in the 09-10 entry: liquidity, weekend gaps in the underlying, corporate actions, FDR, 960-bar data depth |
| **Resolve the taker-fee discrepancy** — API reports `level=1`, taker 3.5 bps; this record has it *measured* at 1.75 bps/side. VIP 5 is "being applied" per LTP. Re-measure once it lands; `optimal_bands` consumes it, so it decides which passing pairs are tradeable | 2026-09-09 | when LTP confirms VIP 5, and at the next review regardless |
| ~~**Synthesise the ~3,400 deep reviews**~~ **DONE 2026-09-09** via Claude Cowork — `deploy/DEEP_REVIEW_SYNTHESIS.md` on branch `research/deep-review-synthesis`. Found the corpus's most convergent claim to be a prompt artefact of our own making; that bug is now fixed and pinned | 2026-08-12 | closed — but the surviving claims still need reading before Sunday |
| ~~**Watch `bad_read`**~~ **CLOSED 2026-09-08** — frozen at 307 across seven hours on the production host. The guard fired every bar through the dead-credential window and has not fired since | 2026-09-08 | closed |
| **`status.py` prints times with no date** in the `recent` list, so five refits on five different days render as five identical `19:00 refit` lines. This misled the 2026-09-08 session into chasing a discrepancy that did not exist — the **fifth** cosmetic defect in this file to cost a real inference. Show the date, or a relative age | 2026-09-08 | build window. The glance is the instrument we steer by |
| **Probe the news/feeds path against `api.liquiditytech.com`** with a hardcoded asset list, so `ltp_news.py`'s `FEEDS_BASE` and `ltp_stream.py`'s hardcoded `wss://feeds.ltp-contest.com` are tested **before** a live entry is the first thing to depend on them. With zero active pairs the sentinel is silent by design, so waiting does not answer it | 2026-09-08 | before the next pair passes the gate. Needs the operator's go |
| ~~**Decide on the pending reboot**~~ **DONE 2026-09-09 16:22 UTC** — kernel 6.8.0-137 → 139, 0 updates pending, banner cleared, ~5 min downtime on a flat book. `NRestarts=0`; equity, peak, `bad_read` and **the bar counter** all survived, so the refit clock did not move. The "it re-phases the clock" note in this row was wrong and is corrected in the day-1 entry | 2026-09-08 | closed |
| **Ask the organizers whether the Binance-vs-OKX venue choice is still open** now that Phase II has started, and whether the primary account is provisioned as a **Sub Portfolio** (if so the key can read but not trade it — `Edit API` fixes it in one click), and whether their side needs an IP whitelisted. The last two were asked of @LTP_Tracey on 2026-09-07 and **never answered** | 2026-09-07 / 2026-09-08 | next organizer contact — bundle with the CSV-export and AI-floor questions already owed |

> **Table hygiene, 2026-08-12.** Three rows above this line had been stranded
> *below* the closing horizontal rule since 2026-08-09 — outside the table, where
> the next review would likely not have read them, and one of them was open.
> Merged back in. If rows appear below a `---` again, that is the bug, not a
> section break.

---

## Week 4 — 2026-08-10 → 2026-08-16 (reviewed Sun 2026-08-16)

**The last review inside Phase I.** It ends 2026-08-21.

### Position at review
Reading **2026-08-17 01:19 UTC**. Equity **1020.30**, peak 1041.19, drawdown
**2.01%**, **MDD 3.7% banked**, kill switch 916.25 with 104.05 headroom.
**Flat, zero pairs, fourth consecutive day.** Service up since 08-14 with
`NRestarts=0`; AI floor cleared at $1.1534; 195 tests.

**Rank #5 of the 30 displayed, score 84.9.** Krosus passed us.

| | T.Anh #1 | btcol #2 | Supes #3 | Krosus #4 | **NDAR #5** |
|---|---|---|---|---|---|
| Score | 93.9 | 91.8 | 86.3 | 85.9 | **84.9** |
| Sharpe (40%) | 3.79 | 4.90 | 2.31 | 3.72 | **2.99** |
| MDD (15%) | 3.8% | 1.3% | 2.6% | **1.0%** | 3.7% |
| PnL (25%) | +58.71 | +30.37 | +24.91 | +15.09 | **+20.30** |
| ROI (20%) | +5.9% | +3.0% | +2.5% | +1.5% | **+2.0%** |

**Sharpe is decaying ~0.06/day while idle** — 3.16 (08-13) → 3.10 → 2.99. Every
other metric is frozen because we hold nothing. Straight-lined to 08-21 that is
~2.7 Sharpe and ~83 score, roughly 6th. **Krosus beats us on both quality
metrics** (Sharpe 3.72, MDD 1.0%); we lead them only on PnL.

### The organizer clarification settles four things
Posted 2026-08-13 in reply to another team; no message was addressed to us and
there were no announcements this week.

1. **Phase 1 scores do NOT carry over. Every team resets to 1,000 USDT in
   Phase 2.** We had assumed this since 2026-07-28; it is now confirmed in
   writing. **The entire remaining value of Phase I is advancement plus
   evidence** — the score itself is worthless after the 21st.
2. **Advancement is the top 30 by overall ranking.** We are **5th**, and the
   displayed #30 scores 49.9 — a **35-point cushion**. Sixteen of the thirty
   shown carry negative PnL. **Advancement is not in doubt**, and four more
   idle days cannot threaten it. This closes the field-size question raised
   2026-08-14: it no longer matters that the board hides everyone below 30.
3. **Eliminated teams leave the normalization pool.** Z-scores are computed
   against the eligible pool only, so **our score moves when other teams die,
   with no action from us.** Do not read a score move as signal without
   checking whether the pool changed.
4. **Advancement also requires "continuously run automated trading strategies
   throughout the competition period."** We have held no position for four
   days. The defence is strong and should be ready rather than improvised: the
   agent runs continuously and logs refits, AI reviews and hourly assessments;
   **the absence of positions is the strategy's output, not its absence**, and
   the ledger proves it bar by bar. Recorded as a watch item, not an incident.

### The decision that governs this week: ship nothing, and why
**There is a 17-day dead window between Phase I closing (08-21) and Phase II
opening (09-07).** That reframes every ship-or-drop question on the agenda. It
was never "ship now or never" — it is **"ship into five days of live risk, or
into seventeen days with time to test and no position at stake."**

Stated that way all three answered themselves, and **no behavioural change
shipped this week. That is a decision, not an idle week:**

- **Sub-hourly monitor — DROPPED for Phase I.** The measured payoff is real
  (roughly a third of losses came from stops firing late) but MDD is already
  spent, we are flat so it would very likely never fire, and Phase I scores
  evaporate on the 21st. A new loop that can close positions, inside a process
  whose job is to stay up, buying nothing that survives the phase.
- **Refit cadence — no change.** The premise genuinely inverted (median hold
  2.0h → 23.0h, refit_drop 10% → 60%) but n=5, one refit_drop was a *winner*
  closed early, and with zero pairs it cannot bind.
- **News-gate refresh — no change.** The logging now tells the truth, which was
  the audit-critical half; the behavioural half touches the entry path.

### Week 4 agenda outcomes
| # | item | outcome |
|---|---|---|
| 0a | single-pair finding | **the frame for everything else** — 0.91 pairs/refit, only 5 of 15 candidates have ever passed |
| 0 | MDD reading | 3.7%, spent. We now out-Sharpe nobody in the top 4 |
| 0b | refit cadence | **no change**, reasons above |
| 0c | gate refresh | **no change**, reasons above |
| 1 | sub-hourly monitor | **DROPPED for Phase I**, scheduled for the gap window |
| 2 | band/`mu` simulation | **not done, deprioritised** — it tunes a book holding at most one position |
| 3 | verify logging | `refit_drop` ✓ live · `size_reduced` never exercised · **close price still null — now diagnosed, see below** |
| 4 | self-ranking in `status.py` | **DELETED** after four carries. The board shows only the top 30, so the endpoint would not have answered the question we actually had |
| 5 | synthesis of ~1,900 reviews | **still owed** |
| 6 | close-out prep | now the main event — week 5 item 1 |

### The close-price gap is diagnosed, and it is nesting
The last close (08-13 20:01, XLM/XRP) recorded `executed_price: null`,
`executed_qty: null`, `order_id: null` — and the fallback did its job:

```
"response_keys": ["closePosition", "readbackNote", "reduceOnlyRequested",
                  "request", "response", "sourceCapability"]
```

**The venue's close response is nested.** The probe checks top-level keys only,
so all three lookups failed on depth rather than spelling. That converted "we
need another live probing session" into a diagnosis read from the ledger, which
is exactly what the mechanism was built for — **but only one level.** It records
key names, not nested contents, so what sits under `response` is still unknown.
A limit of the design worth writing down rather than a triumph.

**Not fixed now**: `close_position` is trading-critical, and an exception there
means a position that will not close — materially worse than the gap it repairs.
Gap window, with the probe extended to recurse and to record nested keys.

**Consequence for the post-mortem: the ledger still cannot say what any exit was
done at.** `fills_report.py`'s symbol-plus-timestamp matching is the only
source, and the entire loss attribution rests on it.

---

## Post-review addendum — 2026-08-20: only one risk control has ever fired

Building the Reasoning Log package surfaced two facts no glance had shown.

**`skip` is 10, and all ten are `side_blocked`.** So across the entire
competition: the **news veto has never fired, the anomaly veto has never fired,
gross-cap and min-notional have never fired.** The one-sided re-entry block is
the only refusal path that has ever triggered, and it has declined **ten**
entry signals.

That reframes the week 2 finding. On 2026-08-02 we recorded *"there are no
`skip` events of any kind"* and concluded the news gate's protective value was
unproven; the `side_blocked` logging then shipped on 08-08 and was described as
*"dormant until a block actually declines a signal."* It was not dormant — it
fired five times within a day of shipping and five more since. **The
last unverified item from the 08-02 logging work is closed, and it is the only
control with a live track record.**

**Why this matters and is not just bookkeeping:** the gate passes 0.91 pairs
per refit, so entry signals are scarce. A control that refused ten of them is
declining a material fraction of everything the strategy ever wanted to do.
The block exists to stop re-entering a side that just broke — but on a spread
that has genuinely re-anchored it refuses the *best* entries, which is exactly
the objection the AI review raised against it. **Ten data points now exist to
settle it**: measure z after each block and ask whether the refused entry would
have paid. That is Phase II work and it is added to the build list.

**Also open: enters (34) exceed closes (27) by seven.** Four are the known
day-one `maxNotional` failures that never opened, and one is likely the
manually-closed orphaned TAO/RENDER position from the week-1 incident. **That
leaves two unexplained**, and the post-mortem must not claim a complete audit
chain until they are.

Both are recorded in the submission: `MANIFEST.txt` now prints a
**RISK CONTROLS THAT ACTUALLY FIRED** block listing every path including the
ones at zero, and `REASONING_LOG.md` states plainly that four of the five
refusal paths have never triggered. Presenting an unexercised control as a
working one is the kind of overclaim this project exists to avoid, and a
submission document is the worst place to start.

---

## Organizer answers on the Reasoning Log — 2026-08-20

Asked in the Q&A channel; answered the same day. Recorded because two of the
three are still open and one sharpened a requirement.

1. **Format: ANSWERED — JSONL plus a written architecture document is
   acceptable.** But the official wording is more specific than the
   announcement: the log must cover *"every order/trading operation … including
   order placement, **cancellation**, opening, and closing — and attach the
   Agent's complete reasoning process, decision basis, and **final result for
   each operation**."* Two consequences: **cancellations must be present** if
   any occurred (the `cancel_all` path exists for the kill switch and flatten
   routine — verify before submitting), and **"final result for each
   operation"** is precisely the close-price gap. `REASONING_LOG.md` §5 now
   answers it head-on: closes carry `result: "closed"` but no price, because
   the venue's response nests it; the execution price for every close lives in
   `fills/`, reconciled by symbol and timestamp. **The chain completes across
   two files rather than inside one record, and the document says so** rather
   than leaving an auditor to find a null.
2. **Delivery: NOT ANSWERED.** *"The specific submission format and submission
   window will be announced later."* So the mechanism may still change. **Watch
   for the announcement**; prepare both an archive (currently ~8.5 MB, well
   inside email limits) and a repo link, and email by the stated 08-24 deadline
   regardless.
3. **Coverage: not specified, but safe.** Non-trading decisions are not
   required, and *"including additional non-trading decision records will not
   interfere with that correlation check."* So include everything. Also
   confirmed: **the compliance review correlates AI decision logs against
   executed orders**, which makes the `operation` records and their order IDs
   the join key.

---

## 2026-08-20 — first place, an expired key, and a bug of mine

Three things happened inside eight hours on the second-to-last day. Recorded
now rather than at the bell, so tomorrow's capture is numbers on a finished
narrative instead of the whole story at once.

### The drought broke, and it broke well
After **seven flat days**, KAS/ETC passed the gate and traded twice:

```
09:00  skip  KAS/ETC  side_blocked        10:00  skip  KAS/ETC  side_blocked
11:00  enter KAS/ETC                      16:00  exit  KAS/ETC  reverted   ~+28.5
17:00  enter KAS/ETC  (still open at 18:42, uPnL +2.66)
```

**Equity 1020.30 → 1051.44, a new all-time high** (old peak 1041.19). PnL
**+20.30 → +50.42**, ROI to **+5.0%**.

Note the two `side_blocked` refusals at 09:00 and 10:00, **immediately before
the most profitable trade of the competition.** The block delayed entry by two
hours on a spread that then reverted hard. That is the sharpest evidence yet
that this control may cost more than it saves, and it makes the Phase II
question concrete rather than theoretical: **ten blocks are now on record, and
one of them sat directly in front of our best trade.**

### #1 of 30 — and the Sharpe move is noise in our favour
| | **NDAR #1** | X-Explore #2 | Little J #3 | T.Anh #4 | btcol #5 |
|---|---|---|---|---|---|
| Score | **86.1** | 85.8 | 85.6 | 85.4 | 82.1 |
| Sharpe | **4.93** | 2.30 | 1.65 | 3.61 | 4.58 |
| MDD | **3.7%** | 7.5% | 7.2% | 3.8% | 1.3% |
| PnL | +50.42 | +97.19 | +141.33 | +58.71 | +31.33 |

**Sharpe went 2.99 → 4.93 in a day.** That is the 9.30 → 5.66 collapse of
2026-08-02 running in reverse — at ~30 completed days one +3% outlier lifts the
mean far more than it inflates the deviation. **The standing rule holds in both
directions: never read a live Sharpe move as evidence about the strategy.** It
was worth stating when it hurt and it is worth stating now.

What is real: we lead on risk-adjusted terms while carrying less risk than
everyone near us. The three teams within 0.7 points made their PnL with MDD of
7.5%, 7.2% and 15.5%.

**Decision: no intervention before the bell.** The decisive argument is not
about variance — it is that **Phase I scores do not carry over and advancement
was already secure at #5.** The practical difference between finishing 1st and
4th is a nicer sentence in the post-mortem. Flattening early to protect a
position would spend real discretionary risk for nothing, which is the reflex
this project exists to refuse. The new peak also raises the bar for a *new*
maximum drawdown to roughly **1012.5** — a fall of ~39 rather than the ~18 it
was on Sunday.

### Incident — the organizer's AI key expired a day early
```
401 Authentication Error - Expired Key.
Key Expiry time 2026-08-20 16:00:00+00:00
```
A hard expiry at **16:00 UTC on 08-20 = 00:00 GMT+8 on 08-21**, a full day
before scoring ends at 23:59 GMT+8. Not something we did. `sentinel_degraded`
fired once on transition at 16:00:08 and every assessment since is logged
`ai_assessment_unavailable` — the week-1 machinery working exactly as designed.

Consequences, in order:
1. **The AI spend floor cannot be met for the final scored period**
   (16:00 UTC 08-20 → 15:59 UTC 08-21) because we cannot authenticate at all.
   Raised with the organizers in writing with the timestamp evidence, which is
   the whole defence. We had cleared it every period since 08-13.
2. **The news gate is dark and fails open** — the 17:00 entry was made
   unscreened and **logged as such**, which is the honest-logging work from
   last week doing its job on the last day. Practically this costs little: the
   sentinel has never vetoed an entry in a month and is asset-specific, so it
   would rate tomorrow's PMI release `none` regardless. The z-stop, gross cap
   and kill switch are unaffected.
3. The reasoning log will show the gap. Better disclosed than explained.

### The bug that expiry exposed was mine
The run that hit the dead key made **600 consecutive failing calls and lapped
its material nineteen times.** The guard I wrote for exactly this case —
*"a whole pass produced nothing, so stop"* — counted **failed** calls as
progress: `calls += 1` runs before the failure check, so `calls != before`
stayed true forever and it ran to the cap. The top-up cron would have repeated
it two hours later.

Fixed: `ok_calls` gates the per-pass guard, and `MAX_CONSECUTIVE_FAILURES = 5`
ends the whole run with a message naming the likely cause. The script runs
fresh from cron, so it took effect on the next firing with no restart.

**The lesson is not the off-by-one.** I wrote a guard specifically for "the
gateway is failing", shipped it, and never exercised it. It ran for the first
time today and did the opposite of its purpose. Hundreds of rejected auth
attempts against someone else's infrastructure is bad behaviour quite apart
from the waste — **a safety valve that has never been opened is an assumption,
not a valve.**

---

## PHASE I CLOSE-OUT — 2026-08-21 15:59 UTC

Thirty-two days. 1,000 USDT seed. The bell rang at 15:59 UTC and we were flat.

### Final
| | |
|---|---|
| equity | **1037.96** (peak 1057.48) |
| PnL / ROI | **+37.96 / +3.8%** (ann. +42.0%) |
| Sharpe | **4.86** |
| MDD | **3.7%**, banked 2026-08-02, never recovered |
| trades | 140 |
| **rank** | **#6 of 30 — ADVANCEMENT SECURED** |

**We finished flat by design, not by luck.** The last active pair read
`ETC/KAS FLAT z=+3.19 blocked=-1`: the spread was stretched into the short zone
and the one-sided re-entry block refused it because that side had stopped out
earlier. The last control standing did exactly what it was built to do on the
final bar.

### The scoreboard, read honestly
**We had the highest Sharpe on the visible board** — 4.86, just above btcol's
4.84 and clear of the three teams above us. We built for the 40% Sharpe term
and won it outright.

We lost the 45% made of PnL and ROI, decisively:

| | ROI | MDD | ROI ÷ MDD |
|---|---|---|---|
| Little J #1 | +22.9% | 7.2% | 3.18 |
| X-Explore #2 | +17.8% | 7.5% | 2.37 |
| Quantech #3 | +31.4% | 15.5% | 2.03 |
| **NDAR #6** | **+3.8%** | **3.7%** | **1.03** |

**Do not tell the flattering version of this.** "We won risk-adjusted and lost
on raw return" is the story that suggests itself, and the last column refutes
it: on return per unit of drawdown we are **last of those four.** Our Sharpe is
highest because our *daily* returns were consistent, not because we converted
risk into return efficiently. We spent the drawdown early on two August stops
and made the return in the final 48 hours — the worst possible ordering for
that ratio.

The accurate summary is narrower and less comfortable: **most consistent daily
returns on the board, mid-pack on everything else, comfortably advancing.**

### Backtest versus live — the gap that matters
The reference run is **0.36 net Sharpe OOS**, on a 31-name universe, through a
multi-pair portfolio engine, on US equities 2006–2017.

The live Sharpe was 4.86 and **that comparison is meaningless**: n≈30 daily
returns, and this record contains a Sharpe that went 9.30 → 5.66 → 2.99 → 4.93
→ 4.86 without the strategy changing once. The standing rule holds in both
directions.

**The real gap is breadth, and it is the largest thing in this record:**

> A framework built and validated as a **multi-pair portfolio engine over 31
> names** was deployed as a **single-pair book over 15 candidates.** Across 22
> scored refits the gate passed a mean of **0.91 pairs**, one pair 59% of the
> time, **zero 27% of the time**, and **only 5 of the 15 candidates ever passed
> at all.** Ten never cleared it once in a month.

That was invisible until 2026-08-15, when the operator queried the `passed`
column across every refit. No daily glance could have shown it. It is a bigger
divergence than fees, slippage or funding — those were assumptions that turned
out benign; this one falsifies a mechanism named in the pre-registration, and
`LTP_STRATEGY.md` now retracts the breadth claim rather than letting the
post-mortem call it a strength.

### What was assumption at launch and is measurement now
| | assumed | measured |
|---|---|---|
| taker fee | 5.0 bps/side | **1.75** — and irrelevant: `cost_z` 0.01–0.08 |
| funding | unmodelled, feared material | **+0.385 received** over 66 settlements |
| slippage | unknown | 0.57 → 0.91 bps mean |
| pairs per refit | "breadth across 14 pairs" | **0.91** |
| stop overshoot | assumed tight | median **0.2σ**, fat tail to 6.75σ |
| refusal paths | five, all live | **one has ever fired** (`side_blocked`, ×10) |

### What actually went wrong, and what caught it
The single largest find was a **unit mismatch in `optimal_bands`** that made
every pair report entry 3.0 / exit 1.5 with expected round trips of 83 days to
3.7 years. The book was idle for a week because of arithmetic, not markets.
Fixing it produced a 2-hour round trip on a level the old bands could never
have traded — and exposed a second bug within the hour, because
`exit_z = 0.0` was unreachable under `abs(z) < exit_z`.

Latent failures caught by diagnostics *before* they cost money: the **nav-guard**
(a failed equity read computed a 100% drawdown and would have self-eliminated
us on any API hiccup), the **degeneracy guard** (a halted symbol's flat series
crashed `adfuller` out of `refit` and into a systemd restart loop), and
**position reconciliation**. Found the hard way: `maxNotionalPerOrder` silently
blocking every entry on day one, and the orphaned position after a state wipe.

### The honesty record
Fifteen corrections were issued and recorded rather than quietly fixed. The
instructive ones share a shape: **reaching for the tidiest available data point
before checking whether the instrument still means what it says.**

- `IMPROVEMENTS.md` **0.44 → 0.36** — the old figure came from the band bug
  barely trading, which flattered Sharpe while forgoing the return.
- The **knife-edge** story, retracted twice, because a sweep's column labels
  were computed from a config value changed between runs.
- **"~22 tokens per call"** — a rolling-window count divided by a lifetime count.
- **"the news veto never fired"** — it had halved the worst trade of the month.
- **Headroom "~100 USDT"** in an AI prompt — that was the distance to our own
  kill switch, not the elimination floor, and it biased 19 answers per pass.
- **"T.Anh at 0|0|0 proves engagement is unscored"** — that row was a display
  artefact or a team pending elimination, and it was never evidence.

And one that is still open: two independent review topics called our
**−10.67 overshoot figure "mechanically inconsistent."** That number is the
entire basis for *"roughly a third of losses came from stops firing late"* and
therefore for the intra-bar monitor. **Check it before building the monitor.**

### The last week, in one line
Seven flat days with zero tradeable pairs, then the gate reopened and KAS/ETC
made **+28.5 in five hours** — the most profitable trade of the competition,
immediately preceded by two `side_blocked` refusals that delayed the entry by
two hours. No gate was ever loosened to manufacture a trade, including through
a three-day drought while the score was falling. That rule was tested and it
held.

### Loose ends carried into the post-mortem
- **Enters (38) exceed closes (31) by seven.** Four are the day-one
  `maxNotional` failures that never opened and one is the manually-closed
  orphan. **Two remain unexplained** and the audit chain is not complete until
  they are.
- **The ledger still cannot say what any exit was done at.** `close_position`
  logs `executed_price: null`; the `response_keys` fallback diagnosed why — the
  venue's response is nested — but the fix waited for the gap window because an
  exception there means a position that will not close. `fills_report.py`'s
  timestamp matching is the sole source for realised exits.
- **The organizer's gateway key expires daily at 16:00 UTC.** It fired on
  08-20 (excused as platform-side) and again on 08-21 after the bell. It will
  recur; raise it before Phase II opens.

---

## PHASE II CUTOVER RUNBOOK — written 2026-09-07, **EXECUTED 2026-09-08 15:37 UTC**

> **This section is now history.** It is kept unedited, in its original future
> tense, because what it predicted correctly and what it got wrong are both
> worth having. The outcome is the section immediately below it. Two of its
> open questions are now answered: the production host, and the gateway key's
> daily expiry.

**GO-LIVE: 2026-09-09 00:00 GMT+8 = 2026-09-08 16:00 UTC = 2026-09-08 09:00
America/Denver.** Converted here once. This is the **third** time this
competition has hidden a day in a timezone: it is *Tuesday morning* local, not
Wednesday. Read that twice before planning around it.

### Where we are starting from (droplet, 2026-09-07 17:44 UTC)
The agent has been failing every bar since the Phase I settlement:

```
equity UNAVAILABLE — RapidX upstream business error 100018: API not exist
news gate DEGRADED (api_error) — 401 Authentication Error
ai spend UNREADABLE (no meter)
bar 1007, pid 51261, up since 2026-08-14, NRestarts=0
```

**Both Phase I credentials are dead**, and this is universal — NeuPortal, SUPES
K and Stream4AI reported the identical `100018` in #TechnicalSupport, and Elaine
confirmed new keys for everyone. **No funds have been distributed to any team
yet.** Nothing here is our fault and nothing needed chasing.

Note what still works: **refits run normally** (2026-09-06 19:00 passed 1/15,
`ADA|DOT`). Market data is unauthenticated or separately authed; only account
endpoints are dead. So a key swap should restore everything.

### The thing most likely to break day one
**`ltp_hwm.json` carries `peak_equity: 1057.48` and the kill switch sits at
930.58.** Phase II starts at **1,000 USDT**. Booted unchanged, the agent
believes it is **already 5.4% in drawdown**, with its kill switch only **7%
below the opening equity** — one ordinary early loss halts us on day one of a
56-day phase.

It will not self-correct. `reconcile_peak` takes
`max(state, hwm file, live)` and **`ltp_hwm.json` was deliberately built to
survive a state wipe** — that was the week-1 fix for the kill switch
re-anchoring downward after `rm ltp_state.json`. It does exactly its job here,
in the wrong direction. **Both files must be deleted explicitly.**

### The second thing: the API host is contest infrastructure
```
LTP_API_HOST=https://api.ltp-contest.com
LTP_AI_BASE_URL=https://ai.ltp-contest.com
```
The Phase II production key was created on **`liquiditytech.com`** — a
different domain. The organizers warned twice, in two separate messages, to
create keys *"in the production environment, rather than the UAT
environment."* Phase I was the **Sandbox** tournament. **A production key very
likely will not authenticate against `api.ltp-contest.com`**, and nobody in the
Telegram thread has raised it. Asked of @LTP_Tracey; answer pending.

### The key we created (2026-09-07 10:55, `NDAR-PhaseII`)
Read on all accounts · **Trade on RapidX Main Portfolio only** · **Transfer OFF
· Withdraw OFF** · IP-bound to `68.183.209.2`. Withdraw is the only
irreversible permission and it is off; sharing a *trading* key with the
platform operator is required and normal. Two follow-ups pending with Tracey:
whether their setup needs an IP whitelisted, and **whether the competition
account is provisioned as a Sub Portfolio** — if so the key can read but not
trade it, and `Edit API` fixes that in one click.

### Cutover, in order
```bash
systemctl stop ltp-agent
cp deploy/ltp_state.json /root/phase1_state.bak
cp deploy/ltp_hwm.json  /root/phase1_hwm.bak
rm deploy/ltp_state.json deploy/ltp_hwm.json
# edit /root/ltp.env:
#   LTP_ACCESS_KEY   = new production key
#   LTP_SECRET_KEY   = new production secret
#   LTP_API_HOST     = PRODUCTION host (ask Tracey; NOT api.ltp-contest.com)
#   LTP_AI_API_KEY   = new gateway key
#   LTP_AI_BASE_URL  = confirm with Tracey
#   LTP_PORTFOLIO_ID = leave UNSET (broker defaults to the CLI's portfolio)
#   LTP_COMPETITION_MODE = 1  (unchanged)
set -a; source /root/ltp.env; set +a
.venv/bin/python deploy/set_leverage.py     # 2x — see the standing decision
systemctl start ltp-agent
.venv/bin/python deploy/status.py
```

**Success criteria:** `equity 1000.00` · `peak 1000.00` · `dd 0.00%` ·
**kill switch 880.00** · news gate live · spend meter readable.

**Diagnostic split if it fails:** `100018 API not exist` after a key swap means
the **host** is wrong, not the key. `401` on the AI side means the gateway key
or base URL.

**Do NOT reboot before go-live.** 21 updates and a restart banner are pending;
they wait until the book is flat and the phase is running.

**Check the new AI key's expiry.** The Phase I gateway key expired at 16:00 UTC
on 08-20 *and again* at the same boundary on 08-21. If Phase II keys carry the
same daily expiry it will take the news gate dark on day one — raise it with
the organizers the moment the key arrives, not after.

---

## PHASE II CUTOVER — EXECUTED 2026-09-08

Ran at **15:37 UTC**, ~22 minutes before the bell. Sequence as written in the
runbook above: stop, back up `/root/ltp.env` + `ltp_state.json` + `ltp_hwm.json`
to `/root/*.bak`, delete both state files, three `sed` edits to the env (host,
access key, secret), source, `set_leverage.py`, start.

### Result, against the runbook's success criteria

| criterion | outcome |
|---|---|
| `equity 1000.00` | ✅ |
| peak reset | ✅ `peak not set yet` — the 1057.48 carry-over is gone |
| `dd 0.00%` | ✅ |
| kill switch 880.00 | **not yet observable** — it anchors on the first peak reading, not at boot. The runbook expected it at boot and was wrong about that |
| news gate live | **unverified** — see the open question below |
| spend meter readable | ✅ |
| service | ✅ active/running, pid 487387, **NRestarts 0**, since 15:37:50 UTC |
| leverage | ✅ 30 symbols → 2×, 0 failed |

Capture at 15:38 UTC: **flat, 0 active pairs, 0 open positions, bar 0**, refit
due next bar.

### The hwm reset was the whole point, and it worked

The runbook called this "the thing most likely to break day one" and it was
right. Booted unchanged, `reconcile_peak`'s `max(state, hwm file, live)` would
have carried `peak_equity: 1057.48` into a 1,000 USDT phase — **5.4% in
drawdown before the first trade, with the kill switch at 930.58, i.e. seven
percent below opening equity.** One ordinary early loss halts us on day one of
56. Deleting *both* files was necessary precisely because `ltp_hwm.json` was
built in week 1 to survive a state wipe; it did its job here in the wrong
direction. It did not self-correct and it would not have.

### The production host — found by testing, not by being told

**`https://api.liquiditytech.com`.** The runbook flagged that a production key
"very likely will not authenticate against `api.ltp-contest.com`" and asked
@LTP_Tracey. **Tracey never replied.** The host was found by trying it, and the
runbook's own diagnostic split is what made that cheap: `100018 API not exist`
after a key swap means the host is wrong, `401` means the AI side. That split
was written the day before and is the reason this took minutes rather than the
afternoon.

Three other teams — NeuPortal, SUPES K, Stream4AI — reported the identical
`100018` in #TechnicalSupport with nobody answering. **We posted the host
there** on 2026-09-08.

**Phase I was the sandbox tournament in a more literal sense than we read it at
the time.** `ltp-contest.com` is the contest/UAT domain; `liquiditytech.com` is
production. The organizers warned twice, in two separate messages, to create
keys "in the production environment rather than the UAT environment" — and
nobody, us included, connected that to the *API host* rather than just the key.

### The gateway key resurrected without being touched — and the daily expiry is gone

`LTP_AI_API_KEY` was **not** among the three values changed. The same string
that returned `401 Authentication Error - Expired Key` before the cutover
returned `200` after it. The organizers evidently re-provisioned it server-side
when Phase II credentials went out, and told nobody.

**The daily expiry did not recur.** Checked deliberately either side of the
16:00 UTC boundary — the exact boundary at which the key died on 08-20 *and
again* on 08-21:

```
15:5x UTC  spend 0.00181176   reset_at 2026-09-09T00:00+08:00
16:05 UTC  spend 0.0          reset_at 2026-09-10T00:00+08:00   ← 200, not 401
```

So Phase II agenda item 9's third clause — "left alone it will take the news
gate dark on day one" — was a correct worry, now answered by observation rather
than by an organizer reply. **Closed.** Note the method: `key/info` has never
reported an expiry field, so the only way to learn this was to call across the
boundary and see what came back.

That reading also pins the budget period to the **competition day** (00:00
GMT+8 = 16:00 UTC), which means our two spend crons at 16:30 and 20:30 UTC sit
at hours 0.5 and 4.5 of the window. That is luck, not design — they were set in
August against a boundary we had not confirmed — but it leaves ~19 hours of
retry room after a failed pass instead of minutes. **Do not move them later
without re-deriving this.**

### The open question the cutover created: three host paths, one of them hardcoded

The cutover changed one environment variable. **Three code paths resolve a host,
and they do not agree:**

| path | how it resolves | state after cutover |
|---|---|---|
| `deploy/ltp_broker.py` (rapidx CLI) | `LTP_API_HOST` | ✅ moved, confirmed working — equity read succeeded |
| `deploy/ltp_news.py:50` `FEEDS_BASE` | `LTP_API_HOST`, default `api.ltp-contest.com` | ⚠️ **moved, unverified** — does the production host serve the feeds path at all? |
| `deploy/ltp_stream.py:31` `FEEDS_WS` | **hardcoded** `wss://feeds.ltp-contest.com/feeds/v2/public` | ⚠️ **could not have moved.** No env change reaches it |

Both `NewsSentinel` and `NewsStream` are imported by `ltp_agent.py`, so both are
in the live path. If the contest domain is decommissioned now that production is
live, the stream stops delivering and **no configuration change fixes it** —
it needs a code edit. This was found by grep during a cold start, not by a
failure, which is the good version of finding it.

`deploy/README_ltp.md:20` also still documents the old host in its setup block.

**Nothing here has been changed.** The fix is a one-line env lookup for
`FEEDS_WS` and a README correction, and it waits for the operator's go and for
evidence from a live news-gate reading.

### What was unverifiable at write time

The 15:38 capture read `news gate unknown (no reading yet)` — expected at bar 0,
not a fault, but it means **the news path has not been exercised against the new
host at all.** The first hourly tick settles it. Until then, treat the news gate
as unproven rather than working.

Also carried forward: **`bad_read: 307`** in the ledger totals, the NAV guard
firing every bar through the dead-credential window. It did the right thing —
refused to act on an unreadable account. It should now be frozen; if it climbs
on the new host, the trading key is less healthy than one successful equity read
suggests.

### Day 1 is running unattended

The operator is in class until **19:00 UTC**. The 16:30 pass fires with nobody
watching. This is fine and was chosen deliberately over a hand-run at 16:05: a
manual pass would likely still have been in flight when the cron fired, and two
concurrent passes is the exact double-spend the 08-12 commitment exists to rule
out. With the period running to 16:00 UTC on 09-09 there are ~21 hours left at
19:00 — ample to recover by hand if the cron did nothing.

**The current period is Phase II day 1 and it is the first one under the
formal written ≥USD 1/day rule.** It opened at $0.00.

---

## PHASE II DAY 1 — closed 2026-09-08

Reading at **22:26 UTC**, ~7 hours after the cutover restart.

```
service      active/running (pid 487387, restarts 0) since 15:37:50 UTC
equity       1000.00 USDT   peak 1000.00, dd 0.00%
kill switch  880.00  |  headroom 120.00 to kill, 200.00 to the 800 floor
halted       no
news gate    unknown (no reading yet)
ai spend     $1.1553 — clears the $1.00 floor
bar          8   (refit every 24; next in 16 bars)
active pairs 0 · open positions 0 (flat)
bad_read     307
```

**Day 1 closed flat.** Zero pairs, zero positions, zero trades. That is a
zero-return day, which drags the Sharpe mean — and the standing rule applies at
full force: at n=1 this says nothing about the strategy.

### CLOSED: the spend crons work, and the second one no-ops

Open since 2026-08-12 and never once confirmed. Settled tonight **by arithmetic
rather than by the log**, which is the more durable evidence anyway.

`crontab -l` confirms two entries, and note the second one's flag:

```
30 16 * * *  ... ai_deep_review.py --daily              >> /var/log/ltp_ai.log
30 20 * * *  ... ai_deep_review.py --daily --floor 1.05 >> /var/log/ltp_ai.log
```

`DAILY_TARGET` is 1.15; the 20:30 pass is invoked with an explicit floor of
1.05. Both had fired by the 22:26 reading and spend stands at **$1.1553** — one
pass to target and no more. A double-spend would read ≈$2.30. **The second pass
found spend above its floor and did nothing, exactly as designed.**
`ai_deep_review` moved ~3400 → 3796, one pass's worth. Commitment struck.

Log path for the record: **`/var/log/ltp_ai.log`**, not `/root/ltp_ai.log`.
`README_ltp.md`'s cron block was already correct; the wrong path came from this
session's memory, and cost one wasted check.

### CONFIRMED: `bad_read` frozen at 307

Unchanged across seven hours on the production host. The NAV guard fired every
bar through the dead-credential window and has not fired since. The new host is
healthy, not merely lucky on one equity read.

### CONFIRMED: the kill switch anchored at 880.00

Peak set to 1000.00 on the first live reading and the switch followed. The
runbook expected this at boot and was wrong about the timing, not the value.

### A display defect that misled this session

`status.py`'s `recent` list showed five lines reading `19:00  refit`, against a
`refit` total that had moved by only one. I raised it as a discrepancy. **There
was no discrepancy.** The list prints **time-of-day with no date**, so five
refits on five *different days* render as five identical lines:

```
2026-09-01T19:01  passed 1/15   ETH|BTC
2026-09-02T19:00  passed 2/15   ETH|BTC, PAXG|XAUT
2026-09-03T19:00  passed 2/15   ETH|BTC, PAXG|XAUT
2026-09-04T19:00  passed 3/15   ADA|DOT, ETH|BTC, PAXG|XAUT
2026-09-05T19:00  passed 2/15   ADA|DOT, ETH|BTC
2026-09-06T19:00  passed 1/15   ADA|DOT
2026-09-07T19:00  passed 1/15   ETH|BTC
2026-09-08T15:38  passed 0/15   (none)
```

The `refit` count of 54 was right all along: exactly one refit since the
cutover. This is the **fifth** display defect in `status.py` to briefly mislead
a reading, after the refit countdown, the news-gate age, the spend states and
the `nxt or every` zero. Every one of them was cosmetic and every one of them
cost a real inference. The glance is the instrument we actually steer by; it
deserves the same standard as the trading path.

### The state wipe re-phased the refit clock — an unplanned side effect

`ltp_agent.py:94` sets `refit_every_bars = 24` and line 1143 gates on
`state["bar"] % 24 == 0`. **Refit cadence is driven by the bar counter, not by
the clock.** Deleting `ltp_state.json` reset `bar` to 0, which forced a refit at
15:38 and re-anchored every future refit to that offset.

Consequence, visible in the table above: refits ran at **19:00 UTC daily from
09-01 to 09-07**, and there was **no 19:00 refit on 09-08**. The next one falls
at ~15:38 on 09-09. The daily refit has permanently moved from 19:00 to 15:38.

Nothing is broken and no gate changed. But it is worth knowing for two reasons.
A normal restart preserves the counter — Phase I proved that twice across clean
reboots — so this re-phasing is specific to **wiping state**, and any future
wipe will move the refit clock again to whenever it happens. And because the
15:38 refit passed **0 of 15**, the book is **guaranteed flat until ~15:38 on
09-09**: day 1's zero-return day was locked in by the cutover's timing, not by
the market.

### Refit pass rates improved in the gap window — read carefully

Over the eight refits above: **mean 1.5 pairs passed of 15**, against the
**0.91** measured across Phase I's 22 scored refits. Same 15-candidate universe,
same gates, same sandbox host.

That is 65% better and it is **not** a reason to relax about agenda item 2. A
mean of 1.5 out of 15 is still a ~10% pass rate, n=8 is small, and the
concentration is unchanged — three names carry all of it (ETH|BTC in six of
eight, PAXG|XAUT and ADA|DOT in three each).

One of those deserves a caveat we should not let ourselves forget:
**PAXG|XAUT is two gold-backed tokens.** Cointegration there is close to
mechanical — it is a redundant-asset pair, the crypto equivalent of two share
classes of one company, not a statistical discovery. Counting it as evidence of
*breadth* would be flattering ourselves. The universe question stands exactly
where the Phase I close-out left it.

### Still unresolved: the news gate cannot be verified yet

`news gate unknown` at bar 8, and `news_assessment` stands at **577 — the same
count as before the cutover.** Zero refreshes in seven hours.

**This is the known defect, not a new one.** The sentinel refreshes for the
assets of already-selected pairs, and `if assets: sentinel.refresh(assets)`
never fires with zero pairs (Reasoning Log gap #3). With no pair active it is
supposed to be silent.

Which means **we still cannot distinguish** "the feeds path works fine on
`api.liquiditytech.com`, nothing has asked it to run" from "it would fail if it
ran." Both look identical from here. `ltp_news.py`'s `FEEDS_BASE` and
`ltp_stream.py`'s hardcoded `wss://feeds.ltp-contest.com` are **both** untested
against Phase II, and they will stay untested until a pair passes the gate — at
which point the first thing to depend on them will be a live entry.

That ordering is bad and it is worth fixing before it bites: a one-off manual
probe against the production host with a hardcoded asset list would settle it
without touching the agent.

### The reboot window is open now

`*** System restart required ***`, 21 updates pending, 3 more under ESM. The
runbook deferred this past go-live; we are past it, **the book is completely
flat, and the next refit is not until ~15:38 on 09-09.** This is the widest
safe window a 56-day phase is likely to offer. Precedent from Phase I is good —
two clean reboots, `NRestarts=0` both times.

~~One caveat now that did not apply then: a reboot resets nothing we care about
*provided `ltp_state.json` is left alone*, but it will restart the agent and
therefore re-phase the refit clock again to the restart time.~~

**WRONG, corrected 2026-09-09 by doing it.** A reboot does **not** re-phase the
refit clock. `state["bar"]` persists in `ltp_state.json`, so the counter
continues across a restart — it read 26 before the reboot and 27 after, with
the next refit still at bar 48. The 09-08 re-phasing was caused by **deleting**
that file at the cutover, not by the process restarting, and the Phase I record
already said the bar counter survived two reboots. The caveat was reasoning
from the wrong cause. **A reboot on a flat book costs a few minutes of uptime
and nothing else.**

**Executed 2026-09-09 16:22–16:28 UTC.** Kernel 6.8.0-137 → 6.8.0-139, 23
packages, 0 updates pending afterwards, banner cleared. Third clean reboot,
`NRestarts=0` every time; equity 1000.00, peak 1000.00 and `bad_read` 307 all
survived. ~5 minutes of downtime on a flat book.

---

## 2026-09-09 — the breadth question, answered and then re-opened

Three things landed on one day and they interact. Read all three before acting
on any of them.

### 1. The universe scan ran for the first time since 2026-08-09

```
EXPANDED universe (54 sector pairs, FDR across all):  0/54 pass
CURRENT  universe (14 pairs):                         0/14 pass
orientation: alpha 0 · vol-rule 0 · both directions (108 tests) 0
VERDICT: regime
```

Rejects on the expanded set: **20 "too few mean crossings" + 19 "fails
split-half cointegration" = 72%**, then Hurst 6, unstable beta 4, half-life 2,
degenerate series 2, beta range 1.

**The EXPANDED result stands.** The verdict fires on that number alone
(`n_expanded <= 1`) and the failure profile is regime-shaped, not
breadth-shaped: widening *within sectors* found nothing, and it found nothing
in a way that says the market is trending rather than that our net is small.

**The CURRENT result does not stand, and the reason is a bug in the scan.**
`BTC` and `ETH` were in `CANDIDATES` and absent from `SECTOR_GROUPS`, so they
were never fetched, so **ETH/BTC was silently excluded** — the pair that passed
the gate on **six of the eight refits** from 09-01 to 09-07. That is why the
header read `14 pairs` against a live book of 15, and nothing said why. So
"0/14" means fourteen of fifteen failed with the load-bearing pair untested. It
is not evidence that today's book is dead.

**Fixed, and fixed twice over so it cannot rot again** (`deploy/universe_scan.py`):
a `majors` sector group so ETH/BTC is scored, *and* the fetch set is now the
**union** of `SECTOR_GROUPS` and `CANDIDATES`, so a symbol the book trades is
always fetched whether or not anyone remembers to list it. Any candidate pair
still excluded for missing data is now **named in the output** rather than
subtracted from a count. Pinned by `tests/test_universe_scan.py`.

**The scan needs re-running before its verdict is quoted anywhere.**

### 2. Two hypotheses the scan cannot yet separate

**The discontinuity is suspicious.** 09-07 19:00: ETH|BTC passes. 09-08 15:38:
0 of 15. 09-09 03:10: 0 of 54 across the whole sector universe. That is a very
sharp transition in ~36 hours and **it coincides exactly with the host change
to `api.liquiditytech.com`**. `degenerate price series: 2` among the rejects is
a data smell. Before "the market changed" is written down as fact, confirm the
production host serves the same klines the sandbox host did — otherwise we are
reading a data artefact as a regime.

### 3. The deep-review corpus contained a fabrication, and it was ours

The synthesis pass (run in Claude Cowork, the first use of it on this project)
found that the corpus's **most convergent claim was a prompt artefact**, and
the finding verifies:

> `ai_deep_review.py` asserted to every reviewer that the agent *"holds a
> median of 2.0 hours against fitted half-lives of 17-26 hours"* and asked what
> the mismatch meant.

Against the 19 fills snapshots in the repo:

| | |
|---|---|
| lowest median hold ever recorded | **2.5h** |
| the **2026-08-09** snapshot the briefing named as its source | **25.98h** |
| 2026-08-20, the last | **8.0h** |

**No snapshot has ever reported 2.0h**, and the one explicitly cited says
thirteen times that. The likely mechanism is transposition: the realised hold
was genuinely 17–26h that week, so the *hold* was relabelled as the
*half-life* and 2.0h invented as the hold. Reviewers were handed a
contradiction that did not exist and asked to explain it; per the synthesis,
~45% of strategy reviews did, and three widely-repeated downstream claims
collapse with it.

**Four instances of the same rot, in one function.** The comment at
`RECORD_FALLBACK` already said this was the *third* case after `days_left()`
and `EQUITY_AT_REVIEW` — and the fix had been applied to the derived path while
leaving three more untouched:

1. `RECORD_FALLBACK` — the false 2.0h, misquoting its own cited snapshot;
2. `_record_block` — interpolated a *measured* hold into a **hardcoded**
   "against fitted half-lives of 17-26h", so even the live path shipped a
   frozen range;
3. `ANGLES[1]` — a hardcoded "sharp sell-off around 2026-07-31/08-01", six
   weeks stale and about to fall out of the 40-day window entirely;
4. `candidate_prompts` — "At the 2026-08-09 refit only 1 of 15 candidates
   passed", a month stale, and false for two days by then.

**All four now derive.** `hold_clause()` builds the question from the measured
median, `last_refit()` reads the newest ledger refit, the estimation window
comes from `cfg.lookback_bars`. `ANGLES` are templates; nothing dated is typed
into them.

**And `RECORD_FALLBACK` no longer quotes any figure at all.** A plausible
stand-in is indistinguishable downstream from a measurement — which is exactly
how a fabricated 2.0h survived a month of daily runs — so the unreadable case
says so and reasons from the fitted numbers instead. This also removes the
1.75 bps fee from the fallback, which matters: see the VIP 5 item below.

**Two tests were holding the fabrication in place.**
`test_prompts_carry_the_real_measured_numbers` asserted `"median hold 2.0h" in
p`, and the angles test asserted `"median of 2.0 hours" in a2`. A test that
pins a number nobody measured is worse than no test, because it makes the
fiction look load-bearing. Both rewritten to pin the *source* of a figure
rather than its value. Suite 203 → **216**.

**On Cowork.** It stated its method, disclosed that its prevalence percentages
were regex-derived and indicative, checked the corpus against ground truth
instead of summarising it, and corrected the round-5 quarantine *upward* —
noting that rounds 6–7 inherit context and quarantining 114 further records
nobody had thought of. Working corpus 2,824 of 3,424. It earned the role.
`deploy/DEEP_REVIEW_SYNTHESIS.md` is on branch `research/deep-review-synthesis`.

### 4. Three organizer items from #TechnicalSupport (2026-09-08)

**a. Phase II permits ALL perpetuals on Binance or OKX.** Phase I was
*"strictly limited to the top 50 Binance USDT-margined perpetuals"* — a fixed
whitelist. That constraint is gone. Our scan tested a hand-built **52-symbol**
sector list; the permitted universe is now in the **hundreds**. The breadth
lever is far larger than the agenda assumed. Temper it: under FDR more tests
raise the bar for everyone, and crossings/split-half failures are regime
symptoms that more symbols do not cure.

**b. `mds.ltp-contest.com` is live and documented**, endpoint
`wss://mds.ltp-contest.com/marketdata/v2/public`. So **`ltp-contest.com` is not
being decommissioned** — which materially downgrades the 09-08 worry about
`ltp_stream.py`'s hardcoded host. Note ours is a *news* socket
(`feeds.ltp-contest.com/feeds/v2/public`), a different service from the market
data one, and still untested.

**c. VIP 5 fee rates are pending.** The account currently reads `level=1`,
taker `0.00035` = **3.5 bps** — but this record has taker *measured* at
**1.75 bps/side**. That 2× gap is unresolved. Important: **fees do not affect
the scan.** `select_pairs` is pure statistics; costs enter later at
`optimal_bands`. Cheaper fees make more *passing* pairs tradeable; they cannot
turn 0/54 into anything.

### Shipped

`deploy/universe_scan.py` (majors group, union fetch, loud exclusions),
`deploy/ai_deep_review.py` (`hold_clause()`, `last_refit()`, templated
`ANGLES`, figure-free fallback), `tests/test_universe_scan.py` (new),
`tests/test_ai_deep_review.py` (+8). **216 tests pass.** No trading behaviour
changed: both files are diagnostics and the advisory layer, neither in the
decision path.

---

## 2026-09-09 (evening) — the −10.67 audited, and the briefing that outlived its phase

Research task 01 ran in Cowork. Output at
`deploy/research_queue/out/01-overshoot-recheck.md` on branch
`research/overshoot-recheck`, 431 lines with a per-stop working table.

### The number is right, and stale, and mis-framed

**−10.67 reproduces to the cent.** `stop_analysis.py` was run unmodified
against the archived ledger and the arithmetic independently reimplemented.
The five-vs-eight doubt has a dull answer: **all eight stops are live**
(`dry: false`), nothing was excluded, and the five are simply the stops that
existed on **2026-08-02**, the day the claim was written. It was then carried
through the 08-09 and 08-16 reviews without recomputation while three more
accumulated. Full-phase cost is **−18.71**.

**"Roughly a third of all losses" is wrong as stated.** Against the full-phase
loss base of −64.69 across 31 closed trades, **−10.67 is 16%.** It is −18.71
that is 29%. Quoted together — "−10.67 ≈ a third of all losses" — the claim is
wrong at both ends: numerator 75% understated, denominator doubled. That
phrasing sat in the commitments table and in the review prompts.

### The 6.75σ exit is genuine — the synthesis's doubt is answered against it

Four independent checks agree. Decision-price P&L −6.19 matches the fills gross
−6.20 **and the venue's own per-leg `rpnl`** (−8.832 + 2.632 = −6.20); slippage
across the four legs was 0.87 / 0.0 / −2.74 / 1.73 bps; z decayed slowly
afterwards (−10.245 → −9.547 → −8.911) rather than snapping back, which is what
a broken relationship looks like and a spike does not.

**And the σ scale is what made it look impossible.** σ_eq for that pair is
**35.4 bps**, so 6.75σ of overshoot is a **2.7% relative price move** between
AVAX and SOL, on 2026-08-01, inside the referenced sell-off. Unremarkable. The
sample is **n=8, not n=3**.

### The KAS/ETC frame corruption — resolved from source, not left open

The audit found the 2026-08-20 KAS/ETC stop reading **3.597σ in entry
coordinates against 4.752σ refitted**, `mu_shift_sigma` 6.443, and reported the
`z_in_entry_coords` convention as undocumented with an inconsistent sign.

> ### ⚠ THE PARAGRAPH THAT WAS HERE WAS WRONG. Corrected 2026-09-09 (later).
>
> It read: *"Fully consistent. σ collapsed 40% during the hold ... σ_live/σ₀ =
> 0.599."* **Task 03 falsified it and the correction is verified below.** The
> error was method, not arithmetic: I checked three logged fields against *each
> other*, found them self-consistent, and called it solved. Self-consistency
> among fields produced by one computation says nothing about whether that
> computation was right. Task 03 went to the price prints. Worse, I wrote the
> bad derivation into task 03's brief under the heading *"do not re-derive
> these"* — Cowork re-derived it anyway, which is the only reason it was
> caught.

**The convention is real** — `ltp_agent.py` defines
`z_entry_frame = (spread − mu₀)/σ₀`, unadjusted for side. **The logged value
is not.**

Reconstructing the frame from the five in-epoch price prints between the 08-18
and 08-19 refits: **all ten point-pairs return σ₀ = 0.01085687 and
μ₀ = −5.42792565 to eight decimals**, and those reproduce all five logged z
readings to six. At the stop the log-spread is −5.46357, *below* μ₀, so
`z_in_entry_coords` must be **negative**:

```
true  z_in_entry_coords = −3.2833
logged                  = +3.5970      ← wrong in sign AND magnitude
σ₀ implied by +3.597    = −0.0099      ← negative. impossible.
σ_live/σ₀               =  2.047       ← σ roughly DOUBLED; it did not collapse
```

So the mechanism runs the **opposite** way to what I published: μ moved *away*,
tripling the raw deviation, and σ doubling damped it back — net ~1.45×
inflation, not a 40% collapse.

**The operational conclusion is unchanged.** −3.28 is inside ±3.5, so the stop
does not fire in the entry frame either way, the entry-frame overshoot is 0.097σ
only under the bad number and simply *does not overshoot* under the right one,
and task 01's row 7 remains an upper bound with a floor near zero.

### Root cause, found afterwards: a beta mismatch

Neither analysis had this. `entry_frame(pair, spread)` was handed a spread
computed with the **live** beta and divided it into `entry_mu`/`entry_sigma`,
which were fitted on the **entry** beta. A hybrid coordinate belonging to no
series — μ₀ and σ₀ only mean anything for the spread they were fitted on, and
the refit changes β. Verified exactly:

```
entry beta   0.97212 → spread −5.46357 → z = −3.2833   ← the truth
refitted beta 0.93266 → spread −5.38887 → z = +3.5970   ← what was logged
```

Reproduces to four decimals. `entry_beta` was never snapshotted at open and
never carried across the refit, so the correct spread could not be rebuilt.
That is why **7 of 9** instrumented closes look fine: the bug only bites when β
moves across a refit *during* a hold.

**It does not touch the −10.67.** Zero refits fired during any of those five
holds, checked against all 35 `refit` events.

### What actually decides the monitor

**−10.67 was never the prize.** Four of the eight stops never reached 4.0σ at
all, so a 4.0–4.5σ monitor cannot touch their −3.04 at any cadence, however
fast. The ceiling on a **perfect zero-latency** monitor is **−6.30 of the
−10.67 (59%)**, or −9.07 of −18.71 — and **69% of that ceiling sits in the one
AVAX/SOL event** the operator's own contemporaneous note calls discontinuous.

**The cadence question cannot be answered from these records.** For every one
of the eight stops the last logged z before the stop bar was inside the band
(−3.31, −3.02, +3.08, −2.70, +3.03, +3.11, −3.18, +2.79); every crossing
happened inside a single unobserved interval. Of 607 z readings essentially all
are stamped at minute :00. **N = 5, 15 and 30 all return the same answer:
unknown, bounded by [0, −6.30].** A linear-in-time sensitivity — labelled an
assumption, and the one most favourable to the monitor — spans only 56% → 41%
across a 6× change in cadence. The value depends far more on whether the move
was continuous than on polling rate.

**Two findings settle it for me.**

1. **The tool's own verdict flips on its complete record.** Five stops:
   *"stops fire LATE → the sampling interval is the defect."* Eight:
   ***"stops fire at the band and the spread does NOT always revert → the stop
   is doing its job; leave it alone."*** Same code, same threshold, three more
   observations.
2. **Bounded benefit, unmeasured cost.** Four of eight stops fired below 4.0σ
   and reverted; XLM/XRP kept running to 4.40σ *after* its stop. A 4.0σ tier
   would also close positions the hourly rule lets breathe, and **no
   false-positive cost is estimated anywhere or derivable from these records.**
   Against that we would be adding a new code path that **closes live
   positions** — the same class of path we deliberately refused to touch
   mid-competition.

**Recommendation into Sunday: drop the monitor, ship the instrumentation.**
Sub-hourly z capture on open positions, estimated at ~90 minutes of work, would
answer at the next stop what a month of re-reading this ledger cannot.

### Three gaps the audit names, worth carrying

- **Three of the five stops in the claim have no venue-verified P&L at all.**
  Retention ate them; their decision-price P&L is corroborated only by NAV
  deltas (agreeing to within 0.2).
- **The largest single loss of the phase, −18.52**, closed after the last
  snapshot and rests on the ledger plus a NAV delta, never a reconciled fill.
- **P&L linearity in z is untested at −10.25σ**, and it sets the largest number
  in the table.

### The briefing had outlived its phase

Fixing the −10.67 exposed that `strategy_prompts` was still opening every
review with **Phase I's position**: `peak 1041.19`, `max drawdown 3.7%`,
`5 lifetime stops`, `−10.67`, `~29 teams`, `~20 daily returns`. Phase II reset
the book to 1,000 and deleted the high-water mark. **Every review generated
since the phase opened was briefed on a position that no longer existed**, at
$1.15/day.

Now derived: `live_peak()` from `ltp_state.json`, `stop_facts()` delegating to
`stop_analysis.py` itself so the briefing and the analysis cannot drift apart,
`phase_days()` from `PHASE_II_START`. The stop_geometry prompt now carries the
audit's findings so the reviewer attacks the live question instead of
re-deriving a settled one. Current drawdown is labelled as **not** the scored
MDD — it is a lower bound on the venue's running maximum, and conflating them
overstates how much room is spent.

Two more contract tests had to be rewritten because they pinned the frozen
figures (`"4 of 5 stops were followed"`, `"already banked at 3.7%"`). Suite
216 → **225**.

### And one error of mine

The task file said −8.31 came from *a single trade*. It comes from two — the
stops at 1.08σ and 6.75σ past the band (−3.5863 + −4.7153 = −8.3016).
`WEEKLY_REVIEW.md:821` and the prompt both said two; the "one trade" was
invented while writing a task whose whole purpose was checking someone else's
numbers. Corrected in place with a visible note rather than edited away.

---

## 2026-09-10 — the universe is not crypto-only, and that may be the whole game

**Organizer clarification, Telegram, 2026-09-09 23:38 (Ella Zhang), answering
another team:**

> *"Any instrument you are able to place orders on under your RapidX perp
> portfolio is eligible for Phase II. Whether the underlying is crypto or not
> makes no difference, so commodity and tokenised-equity contracts such as
> **CL-USDT-SWAP** are treated exactly the same as any other perpetual."*

Both follow-ups answered explicitly: they **count toward the Track A composite
score on the same basis**, with no separate or adjusted treatment, and there is
**nothing different about adding one to an automation session whitelist**.

### Why this is potentially the most important message of Phase II

The 2026-09-09 scan returned **0 of 55**, with **40 of the 55 rejections** being
"too few mean crossings" or "fails split-half cointegration". That is a
trending market — and it trends *everywhere at once* because **every crypto
perp is driven by one factor.** BTC beta is why our sector pairs fail together:
when the whole complex trends there is no such thing as a diversifying crypto
pair, and no amount of widening *within* crypto fixes it. That is exactly what
the scan measured.

Non-crypto perpetuals break the single factor. Crude, metals and tokenised
equities have **different macro drivers**, so the probability that *something*
is mean-reverting at any moment rises substantially. That attacks the precise
bind we are in: flat days earn no PnL (25%), no return (20%), and **actively
suppress Sharpe** (40%, and it scales as √(n/(n+k)) in idle days). We have been
flat since the phase opened.

Two specifics:

- **`CL-USDT-SWAP` is WTI crude.** If Brent is also listed, **WTI/Brent is
  arguably the most reliably cointegrated pair in finance** — a physical
  arbitrage relationship with decades of evidence behind it, not a narrative
  grouping like "two L1 blockchains". Our gates would finally be testing a
  relationship that is known to exist.
- **This framework was written for equities.** `examples/real_data_portfolio.py`
  is 31 DJIA names, 2006–2017. Tokenised equity perps would let it run on the
  asset class it was validated on — with the honest caveat that the validated
  figure is **net Sharpe 0.36 OOS**, modest, and nothing like Phase I's noisy
  4.86.

And it is the purest available form of the agenda's own standing instruction:
**widen the universe, do not weaken the screen.** Nothing here touches a gate.

### Where to hedge, before anyone gets excited

- **Liquidity.** These contracts are likely thin. On a 1,000 USDT book
  `minNotional` may exceed what vol-targeted sizing wants, and `costs.py`'s
  sqrt-impact term stops being decorative.
- **Trading hours.** The perp trades 24/7; the underlying does not. Weekend and
  overnight gaps in the underlying become **jumps** in the spread — and a jump
  is exactly what the z-stop handles worst. The hourly OU model assumes
  continuous trading.
- **Corporate actions become live**, not hypothetical. Already a documented
  unhandled gap; on tokenised equities it means dividends and splits.
- **FDR.** More candidates, stricter correction. The usual tax.
- **Data depth.** We need 960 hourly bars per symbol. Newly listed contracts
  may not have them, and `fetch_panel` drops a symbol with no data silently —
  which is how ETC/KAS's absence went unnoticed for a day.

### The binding unknown, and it is empirical

The operative phrase is *"any instrument you are able to place orders on."* So
the question is not interpretive but factual: **what is actually orderable from
our portfolio?**

**We have never asked.** `ltp_broker.py` implements `market get-klines`,
`market get-symbol-info` and `market get-mark-price` — and **no listing action
at all**. Every symbol this agent has ever traded came from the hardcoded
`CANDIDATES` list in `ltp_agent.py`, seeded from the Phase I top-50 Binance
whitelist. We have been reasoning about "the universe" for eight weeks without
once enumerating it.

`rapidx --help` shows the domains but not the actions; `rapidx market --help`
or `rapidx schema --json` is the next call. Until that list exists, both the
venue question and this one are unanswerable.

### PROBED THE SAME DAY — WTI crude is live and reachable

```
rapidx market get-symbol-info --symbol OKX_PERP_CL_USDT --json
  → PASS, real_tool_call
    originalSymbol  CL-USDT-SWAP        state  live
    contractSize    0.1   minSize 1     minNotional 0
    tickSize        0.01  pricePrecision 2   qtyPrecision 0
    defaultLeverage 5     safeLeverage  10   liquidationFee 0.020
```

`OKX_PERP_BTC_USDT` also live, so the whole OKX namespace is reachable.

**The naming convention, recorded because it cost us a false negative.**
RapidX normalises to **`OKX_PERP_<BASE>_USDT`** and reports the venue's own
name in `originalSymbol`. The organizer quoted OKX's native `CL-USDT-SWAP`,
which RapidX **rejects outright** — so the first probe looked like "not
available" when it was only "wrong spelling".

**Three failure modes, now separated — this is the existence oracle.** A
control probe (`BINANCE_PERP_FAKE_USDT`) was run precisely to make the others
interpretable:

| result | meaning |
|---|---|
| `RCLI12001` "Invalid RapidX symbol" | **malformed name**, never reached the venue |
| `RCLI22001` / upstream `401011` "sym is not supported" | **well-formed, not supported** |
| `PASS` + `real_tool_call` | live |

**CLI quirk worth knowing.** The `FAKE` probe returns
`evidence.source: "local_check"` *while also* carrying
`details.upstreamCode: 401011`. **The `source` field does not reliably
distinguish a local pattern check from an upstream round-trip** — read the
error code and `details` instead. Taken at face value it would have told us
the venue was never contacted, which is false.

**One hedge from the entry above is now weaker.** I flagged thin liquidity
against `minNotional` on a 1,000 USDT book. For CL, `minSize 1` at
`contractSize 0.1` is a **tenth of a barrel** — single-digit dollars of
notional — with `minNotional: 0`. Comfortably inside what vol-targeted sizing
wants. That caution was unfounded here; it may still bite on thinner contracts.

### Two things this does NOT establish

1. **`symbol-info` succeeding is not proof of orderability.** The organizer's
   test is *"any instrument you are able to place orders on."* Data access and
   order access can differ. The definitive check is `order place-preview` — but
   that is classed **TRADE_WRITE**, so it does not get run casually against a
   live-capital account. Decide it deliberately at the review.
2. **Data depth is unverified.** Selection needs `lookback_bars = 960` hourly
   bars. `fetch_panel` drops a symbol with no data **silently**, which is
   exactly how ETC/KAS's absence went unnoticed for a day, so a shallow history
   would quietly shrink the universe rather than announce itself.

### BLOCKED, and precisely: `market.klines` is the one OKX adapter method missing

```
rapidx market get-klines --input '{"symbol":"OKX_PERP_CL_USDT","interval":"1h","limit":1000}'
  → {"ok":false,"code":"RCLI30002",
     "message":"OKX adapter not registered for market.klines"}
```

A coverage probe against `OKX_PERP_BTC_USDT` puts the gap at exactly one method
of seven:

| action | OKX |
|---|---|
| `symbol-info`, `ticker`, `mark-price` | ✅ live |
| `funding-rate`, `open-interest`, `orderbook` | ✅ live |
| **`klines`** | ❌ `RCLI30002` |

**This is a CLI gap, not a data gap, and it is not ours to fix.** Everything
needed to *trade* OKX works today — live price, mark price, book, funding. Only
the historical fit is blocked, and it blocks it for **every team**, so nobody
can build a statistical strategy on OKX instruments in this state. We are not
behind; the tooling is not ready. Reported to #TechnicalSupport 2026-09-10 with
the error code, the coverage table and the naming convention.

**FIXED SAME DAY — by upgrading our own CLI.** Zach's reply: run
`npm install -g @liquiditytech/rapidx-cli@latest`. **We were on 1.0.41**, three
versions behind, while this log had recorded "CLI 1.0.44" since another team
quoted it on 09-08 — we assumed we were current and were not. Upgraded 20:20
UTC with the agent stopped and the book flat; Binance klines verified unchanged
before restarting, since `ltp_broker.klines()` reads rows **by position** inside
a bare `except` and a shape change would have silently returned zero pairs.
Agent back at 20:23, pid 14890, restarts 0.

**Two response-shape differences, and we survive them by accident:**

| | Binance | OKX |
|---|---|---|
| timestamp | `1789056000000` int | `"1789070400000"` **string** |
| row order | ascending | **descending**, newest first |
| fields | 12 | 9 |

`int()` happens to accept numeric strings, the trailing `.sort_index()` happens
to fix the reversal, and we only index positions 0 and 4, which happen to
align. **Remove any one of those and OKX breaks silently.** Pinned by a unit
test against both literal shapes.

### THE REAL BLOCKER: OKX klines cap at 300 rows

```
BINANCE_PERP_BTC_USDT   limit 1000 → count 1000
OKX_PERP_BTC_USDT       limit 1000 → count  300     ← years of history exist
OKX_PERP_CL_USDT        limit 1000 → count  300
```

BTC on OKX has traded for years, so this is an **adapter cap, not data
availability**. And it cannot be paged around: `KlinesInput` declares only
`symbol` / `interval` / `limit`, with **`additionalProperties: false`**, so no
start, end or cursor can be passed. `limit` carries **no documented maximum**,
which makes this a bug report rather than a feature request. Raised with LTP
2026-09-10.

**Why 300 is disqualifying rather than merely awkward.** It is **12.5 days**
against `lookback_bars = 960`:

- the half-life band is 6–168h, and a 168h pair shows **1.8 half-lives** in
  12.5 days — an OU decay rate cannot be fitted on that;
- the crossing gate needs ~9.5 crossings in 300 bars, and a 24h half-life
  spread produces roughly 8. Marginal at the *fast* end;
- split-half would run on 150 bars per half.

So the cap **silently narrows the effective half-life band to roughly 6–48h**
and rejects everything slower for lack of evidence rather than lack of
cointegration. That would read as a market finding when it is a data artifact —
the same failure shape as ETC/KAS vanishing from the scan. **Do not run a scan
over OKX instruments at 300 bars and report the result as a regime measurement.**

**A note on where the naming convention was.** `KlinesInput`'s own description
documents `OKX_PERP_<BASE>_<QUOTE>` and that `OKX_SWAP_<BASE>_<QUOTE>` is an
accepted alias. The answer that cost us a false negative this morning was in
`rapidx schema --json` the whole time, under `inputSchemas`, which we had not
read. Worth remembering before the next round of probing: **read the schema
first.**

**The fallback, if the cap stays.** Selection data and execution data
need not come from the same place. OKX's public REST serves klines
unauthenticated — market data, compliant under the same reasoning that covers
SoSoValue and AIVIX — so we could fit on OKX's own history and trade through
RapidX, since `mark-price` and `ticker` both work for the live z. It is uglier,
it introduces a data-source seam that would have to be disclosed in
`LTP_STRATEGY.md`, and it should not be built while a one-line fix on their
side is plausible. Recorded so the option is not rediscovered from scratch.

### There is no listing action, and that reshapes the work

All 53 capabilities were dumped. **Every market action takes a symbol as
input** — `klines`, `ticker`, `orderbook`, `symbol-info`, `funding-rate`,
`open-interest`, `mark-price`. Nothing returns a list. Neither does anything
under `portfolio`.

So enumerating the universe is **not a call, it is a probing exercise**:
generate candidate names from outside, then use `get-symbol-info` as the
oracle. OKX's public instrument endpoint gives the candidate list, and
`originalSymbol` proves the mapping is mechanical
(`<BASE>-USDT-SWAP` ↔ `OKX_PERP_<BASE>_USDT`). Public market data is
compliant under the same reasoning that covers SoSoValue and AIVIX — it is
market data, not a model.

### What it does to Sunday

Agenda item 3 changes shape. It was *"pull both crypto symbol lists and
compare."* It is now:

1. **Enumerate the orderable instrument set.** Everything else waits on this.
2. **Group by economic driver, not by venue** — crypto majors, crypto sectors,
   energy, metals, equity sectors. The grouping *is* the multiple-testing
   correction and it is the one that carries meaning.
3. **Scan across drivers**, unchanged gates, FDR over every test run.
4. **Then** decide the venue, if the choice is even forced — the organizer's
   phrasing suggests it is about what the portfolio can order, not a
   declaration we make.

### The leaderboard appeared, and it is measuring nothing yet

Top ten visible on day 2. **We are not in it, and that fact carries no
information** — see the `sqrt(365/2)` entry in Standing context. Six of the ten
shared an identical Sharpe of ±13.51, which is the constant two days produce
when one is flat.

State of the field: best PnL on the board is **+25.57 on a 1,000 USDT book**,
2.6% after two days. Nobody has done anything. The only top-three team whose
number means something is **X-Explore** — 558 trades, Sharpe 3.78, MDD 1.7% —
which is a real strategy running at high frequency. Krosus (93.0) and TDB
(83.1) are two-day artifacts.

**Poetikrule shows `0 | 0 | 0` AI engagement at rank 4.** The record already
says both that this column is unreliable (the 2026-08-13 display bug) and that
zero-AI teams have been eliminated in prior reviews. Watch it; do not build an
argument on it — that mistake was made and retracted once already.

**What flat actually costs us, stated plainly.** PnL 0, Return 0, and a Sharpe
that is zero or undefined. Our Phase I edge was the 40% Sharpe term and
**Sharpe needs returns** — there is nothing to be sharp about in an empty book.
That is worse than Phase I, where advancement was the only bar and ten teams
cleared it with negative returns; Phase II is scored on rank.

**And it is still not a reason to loosen a gate.** The 09-09 scan returned 0 of
55 with 40 rejections on crossings and split-half — a trending market. Forcing
entries into that is how Quantech reached −460% annualised and 4.7% MDD on day
two. The legitimate lever is the universe question, and it is blocked on LTP's
300-bar cap rather than on our judgement. Nothing to do but wait and build.

---

## 2026-09-11 — WTI/Brent is cointegrated, and our own correction rejected it

The universe opened, the scan ran across economic drivers for the first time,
and it returned **0 of 66**. The headline is not the zero. It is one row:

```
BZ/CL   adf_p=0.0257  hurst=0.35  hl=23.9h  beta=+0.95  cross=54
        rejected: fails FDR correction
```

**That pair passes every economic and statistical gate we have.** Hurst 0.35 is
strongly anti-persistent. A 23.9h half-life sits comfortably inside the 6–168h
band. Beta +0.95 is what two grades of the same crude should give. 54 crossings.
ADF p = 0.026, significant at 5%. It was rejected by the **multiple-testing
correction and nothing else.**

### Why, and the tension it exposes

Benjamini-Hochberg's threshold scales with the size of the test family. At
m = 66 and q = 0.10 a pair needs p ≤ 0.0015 to clear at rank 1 and ≤ 0.015 at
rank 10; at p = 0.026 CL/BZ needs roughly 17 pairs below it, and **only 2 pairs
in the whole run reached the FDR stage at all.** Tested alone — or within its
own energy group — p = 0.026 passes trivially.

**It failed for the company it was keeping.** Fifty-five crypto pairs we have
strong prior reason to believe are junk right now were in the same family.

So: **breadth and per-pair significance trade off directly.** Every symbol added
to the scan makes it harder for any individual pair to clear. *Widening the
universe hurt the best pair in it.* That is the multiple-testing tax working as
designed, and `CLAUDE.md` invariant 3 exists precisely to stop us dodging it.

### The option, and why it is NOT being taken today

Stratified FDR — correcting **within** pre-declared economic strata instead of
pooling hypotheses with wildly different priors — is standard practice where
families are not exchangeable, and a physical arbitrage relationship and a
meme-coin pair are not exchangeable hypotheses. Our driver groups were defined
on the morning of 09-11, before any of these p-values existed.

**It is still not being changed now, and the reason is the one this project
keeps writing down: we would be restructuring the test family because a result
we liked got rejected.** That is the garden of forking paths, and "what did
this fit to?" is the first question the repo demands of any change that
improves a number.

**Decision deferred to the Sun 2026-09-13 review, with a pre-committed test:**
if we stratify, does junk also get through? Run it both ways on the same panel
and compare what *else* passes, not just whether CL/BZ does. One pair passing
under a looser correction is not evidence; it is the thing we are trying not
to fool ourselves with.

### A second finding, possibly a defect in an instrument

Four of eleven non-crypto pairs died on **`beta out of range`** — all involving
SPX, including the lowest p-value in the entire non-crypto set:

```
MSFT/SPX   adf_p=0.0133  beta=+0.03    <- best p-value of all 11
NVDA/SPX   adf_p=0.0269  beta=+0.03
AAPL/SPX   adf_p=0.2673  beta=+0.06
```

A hedge ratio of 0.03 between an index and its largest constituents is
economically implausible; they should move close to together. The spread is
fitted on **log** prices, so raw scale (SPX quotes at 0.5017 against AAPL's
334) should not cause it. Either the SPX contract tracks its underlying poorly
or something about that instrument is off. **One correlation check before
anything is built on SPX.**

### What survives untouched

**The crypto regime finding.** 49 of the 66 rejections were split-half or
crossings — before FDR entered into it at all. That conclusion is independent
of everything above, and **the flat book remains correct.**

### Data depth, and a prediction I got wrong

`ZS` (soybeans) was excluded with **224 bars** against the 960 required, and
named in the output rather than silently dropped — the fix from 09-09 doing its
job on its first real test. `OKB` is not live on Binance and forms no pair.

And for the record: I predicted CL/BZ would fail on **half-life out of band or
too few mean crossings**, reasoning that the Brent-WTI differential reverts on
a scale of weeks and our band was tuned for hourly crypto. Wrong on both. Its
half-life is 23.9h and it crossed 54 times. The band is fine; the *family* was
the problem. Recorded because the wrong hypothesis was plausible enough that a
future session might reach for it again.

---

## 2026-09-11 (late) — both venues, and a new kind of pair

**Organizer, Telegram:** *"You can place orders on both Binance and OKX for a
single RapidX portfolio but only on perpetuals for Phase II."*

**There is no venue decision.** The `VENUE = "BINANCE"` choice recorded earlier
the same day is superseded — we take the union, 62 unique bases. OKX
contributes exactly two things Binance lacks and one of them matters:

- **`NG` joins energy**, taking the group from one pair to three: CL/BZ, CL/NG,
  BZ/NG. Crude against natural gas is a weaker prior than crude against crude,
  but it triples the group that produced our best row.
- `OKB`, which pairs with nothing.

### The same underlying, priced twice

~52 bases are live on both venues, so `BINANCE_PERP_BTC_USDT` against
`OKX_PERP_BTC_USDT` is now formable. **That is the purest cointegration
available anywhere in this universe** — not two grades of crude, not two tech
stocks, one asset with a spread that is nothing but venue basis.

**And that purity is exactly why it probably will not trade.** Basis between
major venues on a liquid perp runs a few bps; our round trip is two legs each
way at the measured taker fee, call it 7–14 bps. `cost_z = roundtrip / sigma_eq`
will be large and `optimal_bands` is entitled to refuse. The scan now prints
`cost_z` per interesting pair, because **"cointegrates" and "is tradeable" are
different claims and this scan conflated them until today.**

### This makes the FDR problem worse, not better

Adding cross-venue pairs takes the family from 66 to past 120. At m=120, q=0.10,
rank 10 needs p ≤ 0.008 — **CL/BZ at p=0.026 moves further from passing.** Every
expansion of breadth penalises the individual pairs we most believe in.

That strengthens the stratification case from an independent direction: a
universe containing a physical-arbitrage pair, a venue-basis spread and a
meme-coin pair is not an exchangeable family in any defensible sense. **It is
still not a change made today.** Noticing that an argument improved is not a
licence to act on it mid-week, and the improvement does not touch the forking
path: we would still be re-cutting the family after seeing which result it
killed.

**What was built instead is the evidence.** `_stratified_diagnostic()` runs FDR
within each stratum and prints what each would pass, alongside the pooled
result, labelled `NOT the live gate`. That is precisely the pre-committed test
Sunday was promised — *"run both ways on the same panel and compare what ELSE
passes"* — and producing a comparison is not making a decision. The live gate
is untouched; invariant 3 stands. The output frames extra passes as **the
price, not the prize**: every one is a hypothesis the pooled correction was
refusing.

### An execution gap, before any of this reaches the agent

A cross-venue pair has **legs on two venues**. A fill on one without the other
leaves a naked directional position, and `parse_maintenance_windows` reasons
about a single venue's order-API blackout. The scan finding such a pair is not
the same as being able to trade it, and nothing in `ltp_agent.py` currently
models two-venue execution. Recorded now so it is a known gap rather than a
discovery made with money on the table.

---

## PHASE II agenda — opens **2026-09-09**, everything resets to 1,000 USDT

> **STATUS 2026-09-08, read this before the list.** The build window closed and
> **items 2 through 10 did not ship.** Item 1 (the Reasoning Log) is done and
> receipt-confirmed; item 9's expiry clause is closed; everything else is
> untouched. Phase II is therefore live on **Phase I's code, unchanged**, with
> the single-pair fragility unaddressed, the −10.67 overshoot figure still
> unverified, and — the one with a hard edge — **the Binance-vs-OKX venue
> choice apparently defaulted to Binance without the comparison this list calls
> "the thing most likely to decide Phase II."** Whether that choice is still
> open is itself unknown and worth asking the organizers.
>
> Stating it plainly rather than letting a future session infer it from an
> unstruck list: nineteen days were available and the build did not happen.

### Advancement confirmed 2026-08-27
The organizer published the 30 advancing teams. **Team NDAR #6, score 78.4,
ann. return +42.0%, Sharpe 4.86 — the highest Sharpe of all thirty.** btcol is
second at 4.84, Krosus third at 4.52; the five teams *above* us on score ran
3.20–3.76.

**Ten of the thirty advanced with negative returns.** So advancement was never
genuinely at risk, and the anxiety during the three-day drought — when the
score was falling and we were flat — was unwarranted on the evidence available
at the time. Worth remembering the next time a rank move feels urgent: the
binding constraint was the 800 floor and the top-30 cut, and we were never near
either.

The Reasoning Log was emailed to `events@liquiditytech.com` and **receipt was
confirmed by the organizers.** That eligibility item is closed.

**The 19-day gap (08-21 → 09-09) is the build window.** Nothing was shipped in
the final week deliberately: a change that cannot be exercised before the
measurement period ends is pure risk. That constraint is now lifted, and there
is no live position at stake.

1. **Submit the Reasoning Log** by **2026-08-24 15:59 UTC** — built, committed
   at `track_record/phase1_submission/`, archive 9.48 MB. **Eligibility depends
   on it.**
2. **The universe question — highest priority.** Re-run `universe_scan.py` with
   22 refits of evidence rather than week 1's three. A single-pair book running
   eight weeks is the central fragility, and the evidence cannot yet separate
   "the gate is correctly rigorous and crypto rarely cointegrates" from "15
   names is too thin for a multi-test pipeline." Both imply the same action:
   **widen the universe, do not weaken the screen.**

   **New lever, from the Phase II rules: we may trade Binance OR OKX perps.**
   Phase I was Binance only. If OKX's whitelist is larger or differently
   composed, that is breadth at zero statistical cost — the one way to get more
   opportunities without touching a gate. **Pull both symbol lists and compare
   before committing to a venue**, because the choice is made once and the
   universe question is the thing most likely to decide Phase II.

2b. **Make the AI's role in decisions demonstrable** (added 2026-08-27). The
   rules now require an AI agent *"incorporated into data processing, algorithm
   training, or trading inference and decision-making."* We satisfy this
   architecturally — the sentinel can veto or halve an entry and the regime
   gate is enum-validated — but **empirically the AI has changed a trading
   decision exactly once in five weeks**: the `size_mult` halving on
   2026-08-01. News veto: never. Anomaly veto: never. The only refusal path
   that ever fired was `side_blocked`, which is pure arithmetic with no model
   in it.

   That is disclosed honestly in the Reasoning Log and it is defensible. But if
   Phase II audits whether the AI is *actually* in the decision path, one
   halved position is thin evidence. **The design question is how to make the
   role more demonstrable without making it more discretionary** — the whole
   architecture rests on the maths deciding and the model only refusing, and
   that must not be traded away for a better-looking audit trail.
3. **Check the −10.67 overshoot arithmetic** before anything else touches the
   stop. If it is wrong, the intra-bar monitor's case largely evaporates.
4. **Then the intra-bar monitor**, two-tier at 4.0–4.5σ, read-only, may close
   or stop but never open — *if* item 3 survives.
5. **`side_blocked` earned-its-keep analysis.** Ten refusals on record, one of
   them directly in front of the best trade of the phase. Measure z after each
   block and ask whether the refused entry would have paid.
6. **The nested close-price probe**, so the ledger can state its own exits.
7. **The news-gate refresh** before a newly selected pair's first entry.
8. **The synthesis pass** over ~3,400 advisory reviews.
9. **Credential housekeeping, all three in one sitting before 09-09:**
   rotate the **LTP and AI keys** (pasted in chat back in July — that is why
   this item exists); **regenerate the GitHub PAT**, which expired 2026-08-27
   and is used only for manual pushes from the droplet, so nothing depends on
   it today; and **raise the gateway key's daily expiry with the organizers**.
   That last one is not a one-off: the key died at 16:00 UTC on 08-20, was
   restored, and **expired again at the same boundary on 08-21**. Left alone it
   will take the news gate dark on day one of live trading.
   **Do not paste any new credential into chat** — the first two items on this
   list exist precisely because that happened once.

   **STATUS 2026-09-08.** The daily-expiry clause is **CLOSED** — verified by
   calling `key/info` either side of the 16:00 UTC boundary; the key survived,
   so the expiry did not carry into Phase II and there is nothing to raise.
   The rotation clause is **worse than when it was written**: the Phase II
   production key *and secret* went through chat during the cutover, so the
   instruction one line above was broken again by the very work this item was
   meant to precede. The PAT is still expired. Nothing was rotated before 09-09
   and the deadline in this item's own heading has passed.
10. **Refit cadence**, only if the band/`mu` simulation supports it.

---

## Week 5 agenda — Phase I closes Fri 2026-08-21 (COMPLETED — see the close-out)

Five days. **No behavioural change ships in them** unless something breaks.

1. **Write the Phase I post-mortem.** The deliverable that makes this record
   mean something. It must state: backtest **0.36 net Sharpe OOS** on a 31-name
   multi-pair engine versus a live deployment that ran **one pair at a time out
   of 15 candidates** — the largest backtest-vs-live gap in the whole record,
   and invisible until 2026-08-15; that the headline live Sharpe of 9.30 was
   never real; that fees ran **366% of gross** in the final reconciled window;
   that MDD was spent by two stops and never recovered; and that **the ledger
   cannot say what any exit was done at.**
2. **Final capture at the bell: 15:59 UTC Fri 2026-08-21 (08:59 local).**
   `status.py`, the leaderboard, and confirmation the last fills snapshot
   wrote — taken in the ~15 minutes *before* the cutoff, not "sometime Friday".
   Then a **second leaderboard grab a day later**, because scored figures have
   settled T+1 before and the number at the bell may not be final.
   Fills snapshots at ~7-day retention remain the binding archival constraint;
   whatever the post-mortem needs must exist on disk by then.

   **No intervention in the closing days.** Refits run ~19:00 UTC, so 08-20's
   is the last that could open a position with room to work; if it does, let it
   run — an open position at the bell is simply marked to market, since MDD is
   computed on hourly NAV including unrealised. The banked metric is not
   fragile either: **MDD 3.7% against the 1041.19 peak puts the recorded trough
   at ~1002.67, so equity must fall 17.63 from 1020.30 before a new maximum is
   set** — roughly three stops at recent sizing. Deliberately halting to
   protect the score would be the discretionary intervention this project
   refuses, and it would buy nothing.
3. **The synthesis pass** over ~1,900 reviews — convergence, contradiction,
   which claims survive. Discount the round-5 layer, which reasoned from an
   understated headroom figure.
4. **Phase II build list for the 17-day gap**, in priority order:
   **(a) the universe question** — `universe_scan.py` re-run with 22 refits of
   evidence rather than week 1's three; a single-pair book running eight weeks
   is the central fragility. **(b)** the intra-bar monitor, two-tier at
   4.0–4.5σ. **(c)** the news-gate refresh before a new pair's first entry.
   **(d)** the nested close-price probe. **(e)** the refit cadence, if the
   band/`mu` simulation supports it.

### Standing items carried
- **Rotate LTP + AI keys** before Phase II opens.
- **Give the droplet a non-interactive git credential** — `ltp_state_history.jsonl`
  still exists on one machine only.
- **Report the header-only CSV exports** and ask whether the USD 1 floor is
  daily or was one-off enforcement.
- **Re-merge the fills snapshots** at each review.
- **Check AI `spend` against both ends of the band** at each review.

---

## Week 4 agenda — review due Sun 2026-08-16 (COMPLETED — see the week 4 entry)

**Phase I ends 2026-08-21.** The review on 08-16 is the last one inside the
phase. (This line read "12 days" when written on 08-09; countdowns rot, so the
date is what is stated. It was 9 days out on 2026-08-12.)

0. **Open on the MDD reading** (added 2026-08-13). We are **#4, score 86.5**,
   out-Sharping third place (2.94 vs 2.48) and ranking below them on size and
   drawdown. **MDD went 1.3% best-in-field → 3.7% second-worst and cannot
   recover** — 15% of the score is spent. Every other item on this list should
   be argued against that fact rather than against the week 2 position where we
   led MDD, because it inverts one standing argument: with 3.7% banked, further
   drawdown below that level costs nothing scored, which is the strongest case
   *against* item 1.

0a. **Open on the pass-rate distribution, not on the drought** (added
   2026-08-15). Across 22 scored refits the gate passed **0.91 pairs on
   average**, one pair 59% of the time and **zero 27% of the time**, and only
   **5 of 15 candidates have ever passed at all**. This has been a single-pair
   strategy since day one; the current three-day dry spell is the low end of a
   distribution that was always this tight, not a break from health. It
   reframes every other item — a monitor, a band or a refit cadence all tune a
   book that holds at most one position. **Phase I answer is still "change
   nothing".** The real question is Phase II: eight weeks on one pair at a time
   is a fragility, and `universe_scan.py` should be re-run as design work with
   22 refits of evidence rather than week 1's three.

0b. **Re-decide the refit cadence — its premise is gone** (added 2026-08-13).
   Week 3 declined lengthening the interval because *"median hold 2.0h against
   a 24h interval; refit-drops are ~10% of closes."* Both have inverted:
   **median hold 23.02h, refit_drop 60% of exits.** Four of five recent exits
   are plumbing rather than edge, and fees ran 366% of gross. **Do not simply
   reverse it** — one refit_drop was a winner closed early, n=5, and this is
   the low-cointegration stretch. Decide it on the numbers, and note this is
   the same machinery as item 2: a hold-time simulation answers both.

0c. **Refresh the news gate for a newly selected pair before its first entry**
   (added 2026-08-14). `assets = active_assets()` is computed before the refit
   that adds pairs, so a pair coming out of a drought is entered on verdicts
   that never covered its legs. The logging now says so (`missing_legs` /
   `stale`, `screened: False`); the behaviour is unchanged. Smallest of the
   behavioural items and the least contentious — but it is the entry path, so
   it gets decided here rather than shipped ad hoc.

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
  **Re-declined 2026-08-27**, when AIVIX emailed a fresh API key to advancing
  teams. The evidence trigger below is unchanged and has still never fired —
  but a *new and more tempting* argument now exists and is recorded so it can
  be recognised when it resurfaces: the Phase II rules require the AI agent be
  incorporated into *"**data processing**, algorithm training, or trading
  inference and decision-making"*, and agenda item 2b concedes our
  decision-path evidence is thin. Piping an alternative-data feed through the
  sentinel would appear to satisfy both at once.
  **That is precisely why to refuse it.** It would mean adding an unvalidated
  third-party dependency, weeks before live capital, to improve how an audit
  reads rather than how the strategy trades — and this project does not add
  code to flatter a metric. It also does not touch the real constraint: only
  **5 of 15 candidates have ever cointegrated**, and community sentiment does
  not make pairs cointegrate. The levers are a wider symbol universe and the
  Binance/OKX choice.
  (The key arrived in plaintext to a group and was pasted into chat. Treat it
  as compromised by default; it must not go into `/root/ltp.env`.)
  The trigger to reconsider is evidence-based and specific: a pair stops out on
  a structural event that the news sentinel rated `none`, *and* their data
  flagged it earlier. Until that pattern appears in the ledger, leave it alone.
- `get_leverage` readback parses a dict but the API returns a list, so
  `set_leverage.py` prints `Nonex` (cosmetic only — the sets succeeded).
- Droplet has pending Ubuntu security updates; safe to apply and reboot (the
  service auto-starts and state survives).
- `deploy/ltp_state.test.json` / `ltp_ledger.test.jsonl` are archived
  pre-competition shakeout data, kept for the post-mortem.
