# Liquidity Arena 2026 — competition strategy notes

This documents what we learned about how agents win and lose competitions of
this shape, and exactly how this agent intends to be different. It is written
BEFORE Phase 1 begins (starts 2026-07-20), in the spirit of PREREGISTRATION.md:
stating the plan up front so the post-mortem can't quietly rewrite it.

## The evidence base, rated honestly

Liquidity Arena 2026 is the first edition — there are no past winners of this
competition to study. The closest predecessor is **Alpha Arena Season 1**
(nof1.ai, Oct–Nov 2025): six frontier LLMs autonomously trading crypto
perpetuals live with $10k each. Same asset class, same agent format as
Track A. Results:

| agent | outcome | behavior |
|---|---|---|
| Qwen3 Max | +22%, won | rule-like execution: technical signals, strict stops/targets, mechanical entries and exits |
| DeepSeek V3.1 | +4–5%, best Sharpe (~0.36) | few high-conviction trades, ~35h holds, moderate leverage, diversified |
| GPT-5, Gemini 2.5 Pro | −60% or worse | overtrading, high leverage, flip-flopping on news noise |
| Claude Sonnet 4.5, Grok 4 | heavy losses | same failure modes |

The consistent finding across every published analysis: **discipline and risk
control beat prediction**. The two survivors behaved like systematic
strategies; the four casualties behaved like impulsive discretionary traders.
The best Sharpe in the entire field was ~0.36. Academic work on LLM trading
agents points the same way — multi-agent designs with a dedicated risk
supervisor beat monolithic LLM traders, and the risk layer does most of the
work.

**Evidence quality: weak.** n=6 agents, 17 days, one market regime, and heavy
media narrative on top. Treat it as directional, not proof. What it is good
evidence for — because it doesn't depend on sample size — is the failure
mode: an LLM given discretionary trading authority overtrades and over-levers
unless something mechanical stops it.

## The field prediction

Track A explicitly recruits LLM developers and mandates AI-agent
participation, so the field will be dominated by LLM-decides-every-trade
designs. The competition is an elimination tournament: **NAV < 0.8 is
automatic disqualification** (Phase 1 has the same 20% max-drawdown rule).
If the Alpha Arena base rate holds even loosely, a large fraction of the
field eliminates itself inside a month. Phase 1 advances the top 30 teams
on profitability + risk management + system robustness.

Prediction, stated so we can check it later: **surviving with a modest
positive Sharpe and near-100% uptime clears the top-30 bar.** Placing top-3
requires more, which is what the differentiators below are for.

## Our design, mapped to their scoring

The agent is the thing that won Alpha Arena, institutionalized. The math
(OU pairs on cointegrated perps, FDR-corrected selection, cost-aware bands)
decides every trade; the LLM can only refuse or shrink one.

| their criterion | our mechanism |
|---|---|
| elimination at equity < 800 USDT (NAV < 0.8) | kill switch flattens everything at 12% off peak (fires at >= 880, always above the floor) and halts; process stays alive to keep de-risking |
| risk management | vol-targeted sizing, per-leg caps, gross cap, z-stop 3.5 with one-sided re-entry block, no entries beyond the stop |
| profitability | breadth across 14 sector-restricted pairs; the toll-gate: pairs whose edge can't pay fees are refused at refit |
| system robustness (uptime rule removed — see addendum) | single long-running process; per-bar error capture and retry; fail-open sentinel |
| reasoning log audit ("logic consistency") | every decision carries a narrative generated FROM its quantitative inputs — consistent by construction, contradiction-free across days, correlated 1:1 with orders |
| macro sentiment capture | news sentinel: LLM rates event severity per asset; critical vetoes entries, watch halves size — sentiment as a falsifiable risk rule |
| speed on unstructured data | (planned) WebSocket news listener for sub-minute de-risking; see below |
| AI API compliance | organizer-gateway-only wiring; LTP_COMPETITION_MODE hard-refuses self-provided keys (a disqualification offense) |

## The three differentiators for top-3

1. **Speed on news — their stated core task.** The rules score "AI's speed
   in interpreting unstructured data and converting it into trading
   signals." The hourly sentinel becomes a streaming one: LTP's news feed
   has a public WebSocket; a listener fires the LLM assessment the moment a
   critical-looking item lands and de-risks affected positions within
   seconds instead of at the next bar. Still risk-reducing only, still
   auditable. Status: planned, buildable before credentials arrive.

2. **The gold anchor.** XAUT/PAXG — two tokenized claims on vault gold — is
   the strongest cointegration on the 50-symbol whitelist, and exactly the
   pair momentum-chasing LLM agents won't touch. A slow, low-vol
   mean-reversion book on it anchors the Sharpe while selective bets run
   elsewhere. That risk profile is what topped Alpha Arena.

3. **Deterministic reasoning logs.** The audit checks logic consistency.
   Discretionary-LLM logs drift and contradict themselves across days; ours
   cannot, because the narrative is assembled from the decision's inputs
   (z vs band, half-life, gate provenance, news verdicts) at decision time.
   Most teams cannot retrofit this.

Supporting discipline: the $10/day AI-token budget rewards low-frequency,
small-prompt LLM use (hourly classification fits trivially; agents burning
tokens on per-trade chain-of-thought will hit the ceiling), and the 1-order-
per-5s rate limit punishes high-frequency designs — both structurally favor
this architecture.

## What would make us wrong

Stated now so the post-mortem is honest:

- **Our crypto edge is unvalidated.** The pipeline's OOS record is US
  equities (small, positive, decayed). Crypto pairs may cointegrate worse,
  or funding carry (unmodeled — both legs pay/receive funding) may eat the
  edge. The dry-run and Phase 1 are the test, not a formality.
- **The field may be better than the base rate.** If most teams also ship
  disciplined agents, survival alone won't rank and profitability carries
  the weight. Nothing in our design conjures edge that isn't there.
- **Scoring discretion.** The organizer weighs criteria however it wants
  (including "innovation" and "explainability"); a deterministic strategy
  may read as less impressive to judges who wanted LLM theatrics, even if
  it outperforms. The reasoning-log quality is our counterargument.

## Addendum — rule changes since writing (2026-07-17)

Recorded here rather than silently rewritten, since this document is a
pre-registration:

- **The ≥90% uptime elimination rule was removed** from the official rules.
  The only elimination condition left is equity < 800 USDT (NAV < 0.8) with
  automatic forced liquidation. This *strengthens* the survival thesis: the
  field's main guillotine is now purely drawdown, which is the dimension this
  agent is most conservative on (kill switch at 12% off peak, firing at
  >= 880 USDT — always before the 800 floor). Our design keeps the always-on
  process anyway: a down agent can't de-risk on breaking news.
- **The scoring emphasis was reiterated by the organizers** ("reasoning
  consistency… drawdown control and position stability are being watched
  too"), consistent with this document's original bet.
- **Exchange-side TP/SL became available** on the API. Deliberately not
  adopted: per-leg price stops can fire on one leg alone and leave the other
  naked — a directional position a pairs book must never hold. The software
  z-stop closes both legs together at spread level, which is structurally
  correct for mean reversion. Every stop is in the reasoning ledger anyway.

## Addendum — first live-data selection result (2026-07-18)

The first selection run on real RapidX data (960 hourly bars, 28 symbols)
passed **0 of 14** candidate pairs. This is disclosed here, not smoothed
over, because it is partly the crypto-edge risk this document named first
("crypto pairs may cointegrate worse") showing up on live data — exactly
the thing a pre-registration exists to hold us to.

Reading the per-pair reject reasons, most rejections were correct and left
alone: three pairs were trending (Hurst > 0.47), three reverted too slowly
(half-life 108–164h, too few crossings), and the strongest full-window
pair (TAO/RENDER, ADF p=0.001) failed the split-half stability check
because one 20-day half genuinely did not hold. The gold pair (XAUT/PAXG)
oscillates tightly (Hurst 0.26) but with too little amplitude to clear
costs (ADF p=0.12) — the cost-aware gate doing its job.

**One parameter was changed**, transparently: the hedge-ratio band, from
the equity default 0.25–4.0 to **0.20–5.0**, in the crypto agent only
(`selection.py` defaults and the equity backtest are untouched). Rationale:
crypto pairs have far wider volatility ratios than paired equities, so the
tight equity band is an asset-class mismatch. It was rejecting **ETC/KAS** —
ADF p=0.005, Hurst 0.37, 83 crossings, beta 0.218 stable across both halves
— purely because 0.218 sat under the 0.25 floor. This recovers exactly that
one genuinely-cointegrated pair; XMR/ZEC and LTC/BCH reach the cointegration
test with the wider band and then fail it on their own merits (FDR / unstable
beta), so the widening is not a backdoor for weak pairs.

**What was deliberately not changed:** the ADF/FDR cointegration threshold,
the split-half stability test, and the Hurst cap. Loosening any of those to
manufacture more trades is the false-discovery trap this repo exists to
avoid, and the live betas confirmed the gate is discriminating correctly.
The honest consequence is a thin book — one pair now, more as the daily
refit rolls onto fresh windows — and that is the intended shape of this
strategy on a less-cointegrated asset class. The competitive case rests on
survival, risk discipline, and reasoning-log quality (all scored by Track A),
not on forcing volume.

## Addendum — universe breadth check + one added pair (2026-07-22)

By day 3 the live book had gone thin to idle (refit pair count 1→2→2→1→0)
and the Sharpe — 40% of the Phase-1 score — was frozen by inactivity. Before
touching anything, we ran a read-only breadth diagnostic
(`deploy/universe_scan.py`): the SAME selection gates and FDR, applied to a
4x-wider set of **economically-motivated** sector pairs (55 within-group
pairs across 51 available whitelist symbols — never blind all-vs-all).

The honest result was **mostly a regime, not a too-small universe**: the wider
rigorous search passed only two pairs — RENDER/TAO (our existing pair,
re-oriented) and **AR/FIL** (Arweave/Filecoin, decentralized storage;
ADF p=0.0011, Hurst 0.39, half-life 22h, beta 0.74, 84 crossings). The other
~50 failed on genuine grounds (beta out of range, split-half, half-life,
crossings). So crypto cointegration is simply thin right now, and the agent
sitting mostly-idle is partly *correct* — it protects the low drawdown that is
our one banked edge; forcing trades in a trending tape would cost both Sharpe
and MDD.

**One change, disclosed:** AR/FIL is added to `CANDIDATES` — a genuine
storage-sector pair we were blind to, not a manufactured one. The gates
(ADF/FDR, split-half, Hurst, half-life, crossings) are **untouched**; this is
breadth with economic rationale, not loosening. Expectation set honestly: one
pair does not transform a thin book — it improves activity at the margin while
the strategy stays disciplined.

**Parked for careful review, not changed reactively:** the diagnostic showed
RENDER/TAO passing where our hardcoded TAO/RENDER orientation did not on the
same window — the Engle-Granger test is orientation-sensitive. Testing both
directions could recover a few more pairs but touches the FDR invariant, so it
is deferred to a considered review rather than a competition-day reflex.

## Addendum — reasoning-depth layer (2026-07-26)

The organizer's 2026-07-21 notice promised a **deep audit of AI Reasoning Logs**
for "logical depth of sentiment analysis, market anomaly detection, and
strategy adaptation," and warned that trading activity alongside negligible or
non-strategy AI usage may be read as an absence of an AI-driven process. Our
logs covered only the first of the three, and our token usage was the lowest in
the top 10 — a real audit exposure, and an unused differentiator, even though
AI engagement is explicitly display-only and not scored.

`deploy/ltp_analyst.py` closes the gap without touching the division of labour
that makes this strategy testable — **the math still decides every trade, and
the LLM may still only say no**:

- **Market anomaly detection.** Each bar, for each active pair, the organizer
  model reads the live spread state (z path, band geometry, half-life, hedge
  ratio, news verdicts) and rates the regime `normal` / `stressed` / `broken`.
  Every verdict is logged as `ai_spread_assessment`. A `broken` verdict
  **vetoes an entry** — the same risk-reducing-only contract as the news veto;
  it can never open, size up, or re-enter. `stressed` is informational by
  design, so ordinary volatility cannot quietly switch the strategy off.
- **Strategy adaptation.** Each refit, the model reviews which pairs passed,
  the rejection histogram, and what changed since the previous refit, logged as
  `ai_refit_review`. Advisory only; it never edits the selection, and its
  prompt forbids suggesting looser gates to obtain more trades.

Both analyses are written next to the quantitative state that prompted them and
the order (or veto) that followed, so the audit trail is one chain:
AI assessment → decision (with reasoning) → operations → outcome.

**Budget discipline:** analyses are sized to genuine need, not inflated for
appearance. Burning the USD 10/day allocation for show would be dishonest and
self-defeating — exhausting it blinds the news sentinel for the rest of the
day — so the analyst reads the gateway's own `/key/info` spend meter and stops
calling above a ceiling that leaves headroom. Everything fails open: no key, no
SDK, a malformed reply, or an exhausted budget degrades to "no analysis, no
veto" and the systematic strategy runs on. Pinned by `tests/test_ltp_analyst.py`.

## Addendum — canonical pair orientation + degeneracy guard (2026-07-26)

Engle-Granger is not symmetric: regressing A on B is a different test from B
on A. That meant the order a pair happened to be **typed into `CANDIDATES`**
silently decided whether a genuinely cointegrated pair was found — luck, not
rigour. The live scan made it concrete: `SOL/AVAX` fails in our hardcoded
direction while `AVAX/SOL` passes at ADF p=0.0024.

Measured three resolutions on the same 54-pair panel before changing anything:
the arbitrary-but-systematic alphabetical order found 3 distinct pairs, the
a-priori vol-rule found 3, and our hardcoded orientation found 2.

**Adopted: the vol-rule.** The more volatile series becomes the dependent
variable, so the cleaner series is the regressor — the standard
errors-in-variables mitigation, since noise in a regressor attenuates beta.
Decisive property: the rule is fixed in advance and **never inspects a
p-value**, so it adds no multiple testing. The rejected alternative was
"test both directions and keep whichever passes"; that finds at least as many
pairs *partly because it looks twice*, and the two orientations of one pair
are strongly correlated tests, which puts Benjamini-Hochberg on softer ground.
Since the vol-rule matched it at the top of the list, there was no case for
paying that price. Honest size of the win: **one extra pair (2 → 3)** — real,
principled, and not a Sharpe fix.

**Degeneracy guard (the more important find).** The diagnostic crashed with
`ValueError: Invalid input, x is constant` from `adfuller`: a halted or
untraded symbol gives a flat log-price series, a degenerate regression, and a
constant spread. In the live agent this exception propagated out of `refit()`
past a bar loop that caught only `RapidXError` — so **one bad whitelist symbol
would have killed the process, which systemd would restart straight back into
the same failing refit.** Now such pairs are rejected explicitly (with p=1.0
so they still count as tests in the FDR correction, per invariant 3), the
fitting is wrapped so a degenerate half-window can't escape either, and the
bar loop catches everything with a logged `bar_error` — a live agent that is
down cannot de-risk. Pinned by `test_selector_survives_degenerate_series`.

## Addendum — position reconciliation (2026-07-26)

Recorded because it is a live incident, not a hypothetical. Forcing a refit by
clearing the state file was done **while a TAO/RENDER pair was open**. The
agent restarted believing it was flat while the exchange still held ~1,193 USDT
of gross exposure: no exit, no stop, outside the gross-exposure budget — and
because the pair read as flat, the next entry signal would have opened a
*second* position in the same direction on top of it. It was caught in the
same session and closed manually (both legs, ~0.3 USDT unrealised).

The operator error was the trigger, but the failure mode does not need one:
entries place two legs sequentially, so a crash or an API error between them
leaves exactly the same inconsistency — and worse, a **naked directional leg**
in a book whose entire premise is being hedged.

`reconcile_positions()` now runs at startup and before every trade step:

- exchange positions no open pair accounts for are **closed**;
- a half-open pair (one leg live) is closed on sight;
- a pair the state records as open that the exchange has already closed has
  its side and hold clock cleared.

Unaccounted positions are **flattened rather than adopted**, deliberately.
Adopting means reconstructing the entry price, the hold clock and the hedge
ratio the legs were sized under; a mis-adopted pair is a mis-hedged one, which
is a directional bet wearing a market-neutral costume. Flattening costs one
round trip of fees, always reduces risk, and the strategy re-enters cleanly on
its own terms if the signal still holds. Pinned by `tests/test_ltp_reconcile.py`,
including the requirement that a *healthy* open pair is never churned.

## Addendum — a bug in the band optimiser, and Phase I as a sandbox (2026-07-28)

The largest finding of the competition so far, and it is a defect in our own
core math rather than anything about the market.

**The bug.** `optimal_bands` grid-searches (entry, exit) to maximise expected
profit per unit time. It scored each cell with a raw `profit / cycle` rate but
compared that against an incumbent stored as `rate * sigma_eq`. With `sigma_eq`
~0.03 in log-price units the incumbent's bar was deflated ~30x, so nearly any
later cell "won"; because the loops ascend in `a` and `b`, the search walked to
the largest feasible cell instead of the optimum. Every live pair reported
entry 3.0 / exit 1.5 — the exact grid corner.

**What it cost.** On the 15 live candidates the shipped optimiser chose bands
whose expected round trip ran from **83 days (RENDER/TAO) to 3.7 years
(BCH/LTC)**, against corrected optima cycling in 38–400 hours — 18–21x less
profit per hour. This, not thin crypto cointegration, is the explanation for a
book that has sat idle. One pair, PAXG/XAUT (`cost_z` 2.96), is *unchanged* by
the fix: the corner genuinely is its optimum, which is a useful check that the
objective itself is sound.

**Why nothing caught it.** The band tests asserted direction only
(`dear.entry_z >= cheap.entry_z`), which two saturated results satisfy
vacuously. Tests now check that the returned bands *are* the grid optimum.

**The honest cost of fixing it.** The reference equity backtest (31 names,
2006–2017, 19 OOS folds) moves from Sharpe 0.44 / 0.31% annual / −1.14% MDD to
**Sharpe 0.36 / 1.07% annual / −5.13% MDD**, with average gross leverage going
0.02x → 0.37x. The old, better-looking Sharpe came from a book that was almost
never on. `IMPROVEMENTS.md` has been corrected to the lower figure with the old
one left visible.

**A guard that did not work.** Hypothesis: the corrected 0.4–0.6 sigma bands
trade inside the noise of the fitted mean, since an autocorrelated OU series
gives far fewer independent observations than its length suggests (±0.22 sigma
for a 17h half-life on 960 bars; ±0.90 sigma for a 267h one). Adding an
estimation-error floor (`ou_mean_standard_error`, exposed as the
`min_entry_se` config on both `AgentConfig` and `PortfolioConfig`) did **not**
rescue the Sharpe — sweeping it showed results identical up to 1.0 SE and
strictly worse above. `min_entry_se` is kept at 1.0 anyway, not as a
performance tweak but as a safety rail: inert on the reference data, and
binding exactly where that data has no examples — slow-reverting crypto pairs
like ADA/DOT (0.6 SE) and BCH/LTC (0.45 SE).

**Phase I is now explicitly a sandbox, and this is a deliberate risk choice.**
Track A Phase I advances the **top 30 of a 29-team field**, and Track B does not
compete in Phase I, so a combined leaderboard is structurally impossible.
Advancement is therefore assured for anyone who stays above the 800 USDT floor,
and Phase I *rank is worth nothing*. What Phase I is still worth is evidence:
we would otherwise enter Phase II — where the ranking and the USD 300k actually
exist — with no data on how the corrected bands behave on crypto. So the
corrected optimiser is going live now, with `risk_per_pair` **halved from 0.004
to 0.002**. Scaling size scales return and drawdown together without changing
Sharpe, so the reduced budget costs nothing in evidence while bounding the
downside. Worst case is the kill switch latching near 889 USDT: still above the
floor, still advancing, and we will have learned the bands are too aggressive
for this asset class before that lesson could cost real money.

Stated plainly so the post-mortem can hold us to it: this is a decision to
spend drawdown budget on information, justified by advancement being assured.
If advancement turns out not to be assured, the decision was wrong.

**A second bug the first fix exposed, within the hour.** The corrected
optimiser chose `exit_z = 0.0` — take profit when the spread returns to its
mean. The exit condition was `abs(z) < exit_z`, which is never true at zero,
so the first position opened under the new bands had **no reachable profit
exit**: it could leave only via the structural-break stop or the max-hold
clock (~64 hours). The symmetric test had been correct-by-accident for as long
as the optimiser bug pinned `exit_z` at 1.5 forever. The exit is now
directional, which is what it always should have been — a long spread is
opened below the mean and profits as z rises, so it closes when z climbs back
to `-exit_z`, and the short side mirrors. Identical behaviour for `exit_z > 0`;
`exit_z = 0` is now expressible. Pinned by `tests/test_ltp_exit.py`, including
a source check so a refactor cannot quietly restore the symmetric form.

Worth recording as a pattern rather than a one-off: a long-lived bug had
been holding a second, dependent bug harmless. Fixing the first made the
second live immediately, in production, on a real position. The lesson is not
"fix fewer bugs" — it is that the first trade after a change to core maths
deserves to be watched, not assumed.

## Addendum — costs measured instead of assumed (2026-08-02)

Since launch the cost model has run on an assumption: `taker_fee = 5e-4`, 5 bps
per leg, chosen from Binance's public schedule and never checked. It feeds
`optimal_bands` through `roundtrip = 2 * taker_fee * (1 + |beta|)`
(`ltp_agent.py`), which decides both the entry band and whether a pair is
tradeable at all. A cost model built on an unverified fee is a backtest wearing
a live-trading costume, so week 2 measured it.

`portfolio user-fee-rate` — the obvious route — fails with upstream 2002 "API
Invalid Authorization", because the contest's simulated portfolio has no real
exchange account behind it to hold a fee tier. The platform's CSV exports come
back header-only. So the fee was measured from fills instead, via
`deploy/fills_report.py` and `transaction executions`, which is the better
number regardless: what we were charged, not what is advertised.

**Measured: 1.75 bps per side.** Exact to five significant figures across 22
fills (`0.07165148 / (63 × 6.499)`), `fee == tradingFee`, `rebate` zero,
`execType` TAKER throughout. `taker_fee` is therefore changed **5e-4 → 2e-4**,
a small margin over the measurement against a venue schedule change rather than
against measurement error.

**This is disclosed as a behavioural change.** `deploy/band_diagnostic.py`
reports `cost_z` (round-trip cost in units of `sigma_eq`) between 0.01 and 0.08
for every candidate: costs are roughly 8% of the entry band, not the dominant
term. Sweeping the fee from 5.0 bps to zero moves AVAX/SOL's entry band by at
most one grid step (0.6 → 0.4) and admits **no** new pairs — the diagnostic's
own words: *"HALVING EXECUTION COST would newly admit: NOTHING."*

> **Correction, 2026-08-03.** This section originally said the change was
> "expected to be inert." The first refit under the new fee put AVAX/SOL at
> entry ±0.4, down from ±0.6, so that was wrong and is retracted.
>
> The cause is neither the fee nor a regime shift, and the diagnostic isolates
> it: at a **constant** 2.5 bps — a column that does not read `AgentConfig` —
> four pairs (ETH/BTC, AVAX/SOL, TAO/RENDER, FIL/AR) flipped 0.6 → 0.4
> overnight, so the fee cannot explain it; yet `cost_z` scaled almost exactly
> by the fee ratio across the whole panel and half-lives barely moved, so the
> fit did not shift materially either. Both hold only if **the objective is
> nearly flat between 0.4 and 0.6 and the argmax sits on a knife edge**, where
> a ~6% nudge to `cost_z` from any direction flips the grid cell.
>
> The band should therefore be expected to oscillate 0.4 ↔ 0.6 between refits,
> carrying entry-to-stop distance 2.9σ ↔ 3.1σ with it. The accurate claim,
> which is what should have been written here, is: *the effect is small, but
> the band sits near a grid boundary where small effects move it one step.*
>
> ## RETRACTED, 2026-08-04 (later): the knife-edge reasoning was an artifact
>
> **The evidence for it was miscounted, and the original simple explanation was
> right: the fee change moved the band.**
>
> `band_diagnostic.py`'s fee-sweep columns are **multipliers of
> `cfg.taker_fee`**, but their labels were hardcoded strings. After `taker_fee`
> changed 5e-4 → 2e-4, the column reading "2.5bp" was actually **1.0bp**. The
> "four pairs flipped at a constant fee" observation compared 2.5bp against
> 1.0bp — the fee was never held constant, so it showed nothing.
>
> Read correctly, the 2026-08-02 sweep already predicted this: AVAX/SOL was 0.6
> at 2.5bp and 0.4 at 1.25bp. We set 2.0bp. It went to 0.4. **The fee tightened
> the band by one grid step, exactly as that sweep said it would**, and the
> disclosure above should simply have said so rather than reaching for a
> subtler mechanism.
>
> Fixed at the source: `fee_label()` now generates every column heading from
> the live config, so a label cannot silently stop being true, and
> `tests/test_band_probe.py` pins it.
>
> **What survives**: `a_grid = np.arange(0.4, 3.01, 0.2)` still means entry 0.4
> is the smallest value the optimiser can return, and `min_entry_se` (≈0.24σ)
> sits below it, so *whether 0.4 is optimal or clamped remains genuinely
> undetermined*. `band_diagnostic.py` section 3 now prints the objective across
> a probe grid reaching to 0.05 and labels each pair `interior` / `at floor` /
> `CLAMPED`. The live grid is still not to be widened on that evidence alone:
> a tighter entry means more trades on a thinner edge against an unchanged
> stop, and `optimal_bands` takes no stop parameter.
>
> <details><summary>Superseded reasoning, kept for the audit trail</summary>
>
> **Qualified again, 2026-08-04.** "Knife edge" assumed an interior optimum.
> `a_grid = np.arange(0.4, 3.01, 0.2)` and `b_grid = np.arange(0.0, 1.51, 0.25)`,
> so **entry 0.4 and exit 0.0 are the grid's minima** — the optimiser cannot
> return anything smaller, and the `min_entry_se` floor (≈0.24σ on this fit)
> sits below them and is not what binds. Whether 0.4 is optimal or merely
> clamped is **undetermined**, because the diagnostic prints the argmax and not
> the objective. Both readings are consistent with the observed flipping; only
> one of them is a knife edge. Settle it by printing the objective per candidate
> band, or by widening `a_grid` in a diagnostic-only run. **The live grid is not
> to be widened before that evidence exists**: a tighter entry means more trades
> on a thinner edge against an unchanged stop, and `optimal_bands` takes no stop
> parameter, so it cannot price that trade-off.
>
> </details>
>
> `taker_fee` is **not** being reverted, and the retraction above strengthens
> rather than weakens that. 1.75 bps is what the venue charges and 5.0 was a
> guess; restoring a knowingly wrong input because its output was preferred
> would be fitting the input to the answer. That the correct fee tightened the
> band by a step is the cost model working, not misbehaving. If the resulting
> geometry proves harmful the fix is `stop_z` — the genuinely unmodelled term,
> since `optimal_bands` takes no stop parameter — not a corrupted fee.

Two further assumptions closed at the same time, both previously listed as
honest gaps in `README_ltp.md`:

- **Funding carry**, never modelled: **−0.024 USDT across 34 settlements** over
  13 days, 0.002% of NAV. Read from `portfolio statement`, where the amount
  field is `deltaAmount` and reconciles against each row's own
  before/after balance.
- **Slippage**, never quantified: **0.57 bps mean, 0.0 median**, signed so that
  positive is adverse. Market orders on liquid perps cost essentially nothing.

The honest consequence is deflationary and worth stating plainly: **execution
cost is not what limits this strategy.** Breadth is limited by the statistical
gates — the 2026-08-02 refit rejected 14 of 15 candidates on split-half
cointegration, mean crossings, Hurst and beta stability, none of them on cost —
and those gates will not be loosened to manufacture trades. The remaining lever
on PnL and ROI is position size, which is why `risk_per_pair` is being restored
rather than the bands being tightened.

## Addendum — logging the paths that were not logged (2026-08-02)

No change to what the agent trades; a change to what it records. Four paths
that move money or change risk were leaving no durable trace, all found the
same day and all in one shape — the entry path is well instrumented and
everything else was thin:

- **`refit_drop`** (`ltp_agent.py`, the `flatten` branch). When a refit stops
  selecting a pair the agent flattens it, and wrote no ledger event at all: two
  orders reached the venue tagged `decision="close"` with no decision behind
  them and no reasoning for the exit. Now emits a `refit_drop` decision, before
  the close, so a failed close still records the intent.
- **`size_reduced`** (`ltp_news.py::size_mult`). A `watch` news rating halves
  the risk budget. It logged to the journal only — and on 2026-08-01 it halved
  the position on the worst trade of the competition, turning roughly −12 into
  −6, with no ledger trace that a control had acted. A risk control that acts
  silently is indistinguishable from one that never fires. Now emits
  `size_reduced`, and every `enter` row carries a `size_mult` field, since `g`
  is already multiplied by the time it is logged.
- **`close_position` outcomes** (`ltp_broker.py`). It emitted neither
  `executed_price` nor `executed_qty` — unlike `place_market`, which emits
  both — and its `order_id` was always null because the venue's close response
  has no `orderId` field. Together these meant **the ledger could not say what
  any exit had ever been done at**, and the fill could not be looked up
  afterwards either. Now probes several spellings for each and, when none
  match, records the response's own keys so the next gap is diagnosed by
  reading the ledger rather than by another live probing session.

- **`side_blocked`** (`ltp_agent.py`, the entry branch — added 2026-08-08, the
  fourth and last of this series). After a stop, the one-sided re-entry guard
  keeps that side shut until z heals back inside the entry band (invariant 4).
  `blocked` lived purely in runtime state, so a signal **refused by a risk
  control** was indistinguishable from a bar on which no signal existed. Now
  emits `skip` with `reason="side_blocked"`, the side it wanted, the healing
  threshold and the reasoning — and only when the block is genuinely what
  stopped the trade, never on a quiet bar, or the event buries itself in the
  noise it is meant to stand out from. Pinned by
  `tests/test_ltp_blocked_skip.py`, which also asserts the reported healing
  threshold matches the code that actually clears the block: a log that states
  when a control will release, and is wrong about it, is worse than one that
  says nothing.

Pinned by `tests/test_ltp_logging_gaps.py` as behavioural contracts rather
than style: Track A's Reasoning Audit correlates logged decisions against
executed orders, so these omissions were audit exposure, not untidiness.

With `side_blocked` the known set is closed. Every path that opens, closes,
resizes or refuses a position now writes what it did and what came back:
`enter`, `exit`, `stop`, `refit_drop`, `news_derisk`, `kill_switch`,
`maintenance`, `size_reduced`, and `skip` in five flavours (`gross_cap`,
`min_notional`, `anomaly_veto`, `news_veto`, `side_blocked`). If a new path is
added, it joins that list or the principle has quietly lapsed.

One related limit worth pre-registering, because it constrains the Phase I
post-mortem: **`transaction executions` does not serve fills older than about
seven days.** This is retention, not a query-width cap — a six-day window over
Jul 20–26 was rejected while two later windows of identical width succeeded.
Week 1's fills are unrecoverable through that endpoint, so the fills analysis
in the week 2 review covers 2026-07-26 onward, and `fills_report.py` must be
run weekly for the rest of the competition or each week's evidence expires
before it is captured.

## Addendum — a "reverted" exit that was the mean moving (2026-08-06)

No change to what the agent trades. A change to what it can be caught claiming.

On 2026-08-05 a short AVAX/SOL spread entered at z=+0.717 exited at z=−0.109
tagged `reverted`, with the reasoning line *"the mean-reversion cycle
completed."* It had not. Measured on the entry's own hedge ratio, **the spread
ROSE 0.0101 while z fell 0.827** — they moved in opposite directions — and the
position closed at −4.11 (`−g × Δspread = −407.3 × 0.010094`, against an
observed equity change of −4.06).

The mechanism is `mu`, not a bug. It is re-estimated at every refit as the mean
of the last 3 half-lives of spread, and two refits fired during the 38-hour
hold. Solving back with `sigma ≈ 0.02`, **the equilibrium moved up ~1.3σ while
the spread rose only 0.5σ**: the reversion target chased the price and overtook
it. This is the documented intent of a trailing mean — `BacktestConfig.z_window`
describes it as handling "hedge-ratio error & slow regime change" — but the
cost was never written down. **In a trending spread the trailing mean converts a
losing position into a "reverted" exit**, and it is side-agnostic: short into a
rising trend or long into a falling one both close at a loss reporting success.
That is precisely the regime the same day's refit identified, with 14 of 14
candidates failing across five different gates.

Disclosed here because the reasoning text was asserting something the numbers
contradicted, which for a Reasoning Audit is the same defect as the three
logging holes closed on 2026-08-02.

**What ships now** (additive, no behavioural change): `entry_mu` and
`entry_sigma` are snapshotted when a position opens and carried across refits;
`entry_frame()` reports `z_in_entry_coords`, `mu_shift_sigma` and
`equilibrium_reestimated` on every `exit` and `stop`; and when the equilibrium
has moved at least `MU_SHIFT_MATERIAL` (0.10σ), `reversion_note()` appends a
sentence saying the exit is measured against a different mean than the entry,
rather than claiming a completed cycle. Absence of the fields reads as
*unknown*, never as *the mean held steady*. Pinned by
`tests/test_ltp_entry_frame.py`.

**What does NOT ship**: freezing `mu` at entry for the life of a position. That
is a real behavioural change with its own failure mode — holding to a stale
mean is exactly what the trailing window exists to prevent — and n=1. Every
other reverted exit on record was profitable. It goes to the week 3 agenda
alongside the entry-band simulation, to be decided on realised Sharpe and MDD
rather than on one trade.

## Sources

- Alpha Arena S1 results and analyses: nof1.ai; iweaver.ai season-1 recap;
  howaiworks.ai leaderboard analysis; SCMP and China Academy coverage of the
  final standings (Qwen3 Max +22%, DeepSeek best Sharpe ~0.36, four of six
  agents in heavy drawdown).
- Multi-agent risk-supervisor findings: BlackRock/Columbia three-layer
  framework coverage; ContestTrade (arXiv 2508.00554); FinRL contest series.
- Liquidity Arena Track A rules and AI API policy: arena.liquiditytech.com
  (rules current as of 2026-07-15; the organizer may amend at any time).
