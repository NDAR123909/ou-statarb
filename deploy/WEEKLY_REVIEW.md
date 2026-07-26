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
- "AI Engagement" and "AI-Adjusted PnL" are **display only, not scored**.

**Hard rules.**
- **AI API**: must use the organizer gateway *exclusively*; any self-provided or
  third-party LLM is immediate disqualification. USD 10/day of tokens, no
  rollover. They verify by correlating AI decision logs with executed orders,
  and warn that trading with zero/non-strategy AI usage may be read as "not an
  AI-driven process". Enforced in code by `LTP_COMPETITION_MODE=1`.
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

### Known-unexplained / watch
- **50% stop rate** (3 of 6 round-trips). Entry band is model-derived (~3.0)
  but `stop_z` is a hardcoded 3.5 — only 0.5z of room. Possible mis-calibration,
  **but n=6 is far too small to re-tune on.**
- **Anomaly-veto rate**: the new LLM veto could over-block entries and suppress
  the very Sharpe we want to lift. Unmeasured — first data arrives this week.
- **Funding carry is not modelled** and settlement went live Jul 20. Both legs
  pay/receive; unquantified.

---

## Week 2 agenda — review due Sun 2026-08-02

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
2. **Anomaly-veto rate**: `grep -c anomaly_veto deploy/ltp_ledger.jsonl` and read
   the rationales. If it is blocking entries that would have been profitable,
   tighten the prompt; the veto must stay rare and evidence-based.
3. **AI token spend**: `GET https://ai.ltp-contest.com/key/info` → `spend`.
   Confirm the depth layer sits comfortably under USD 10/day (expected ~72
   spread assessments + 24 news + 1 refit review per day). Also confirm the
   `ai_refit_review` / `ai_spread_assessment` records look substantive, since
   the audit judges *logical depth*, not volume.
4. **Entry/stop geometry — ONLY if (1) supports it.** The question is whether a
   fixed `stop_z=3.5` against a model-derived entry (~3.0) is too tight, e.g.
   making the stop relative to the entry band. A wider stop means fewer
   stop-outs but larger individual losses, and MDD is permanent — so this needs
   real evidence, not six trades and a hunch. **Default action is no change.**
5. **Self-ranking endpoint into `status.py`** (small, deferred from week 1):
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
