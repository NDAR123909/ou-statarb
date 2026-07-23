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

## Sources

- Alpha Arena S1 results and analyses: nof1.ai; iweaver.ai season-1 recap;
  howaiworks.ai leaderboard analysis; SCMP and China Academy coverage of the
  final standings (Qwen3 Max +22%, DeepSeek best Sharpe ~0.36, four of six
  agents in heavy drawdown).
- Multi-agent risk-supervisor findings: BlackRock/Columbia three-layer
  framework coverage; ContestTrade (arXiv 2508.00554); FinRL contest series.
- Liquidity Arena Track A rules and AI API policy: arena.liquiditytech.com
  (rules current as of 2026-07-15; the organizer may amend at any time).
