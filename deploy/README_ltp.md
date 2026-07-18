# LTP Liquidity Arena deployment

`ltp_agent.py` is the statarb pipeline pointed at the Liquidity Arena 2026
competition (Track A): OU pairs trading on the contest's 50-symbol Binance
perp whitelist, hourly bars, hedge-mode orders through the official `rapidx`
CLI. The math is imported from `statarb/` unchanged — selection with FDR and
split-half stability, cost-aware optimal bands, z-stop with the one-sided
re-entry block. Only the clock (hours) and the venue are new.

## Setup (once)

```bash
# 1. Node 20+ and the organizer's CLI
npm install -g @liquiditytech/rapidx-cli@latest
rapidx --version

# 2. Credentials (issued by LTP at registration; never commit these)
export LTP_ACCESS_KEY="..."
export LTP_SECRET_KEY="..."
export LTP_API_HOST="https://api.ltp-contest.com"
rapidx auth check && rapidx self-check --read-only --json

# 3. Python side is just this repo
pip install -e .
```

## Running

```bash
python deploy/ltp_agent.py --dry-run          # data + intents, no orders
python deploy/ltp_agent.py --dry-run --once   # single bar, then exit
python deploy/ltp_agent.py                    # live (needs consent, below)
```

Live trading requires an automation session, and RapidX requires the consent
text to be authored by the human operator — the agent refuses to write it for
you. Set it yourself, in your own words, naming the scope you actually accept:

```bash
export LTP_AUTOMATION_CONSENT_TEXT="I authorize RapidX automation for the \
agent's whitelisted contest symbols with max 500 USDT per order and 4000 \
USDT total automated exposure, renewed daily while my agent runs."
```

## Competition rules the agent enforces on itself

| contest rule | agent behavior |
|---|---|
| equity < 800 USDT (NAV < 0.8) = eliminated | kill switch flattens everything at **12% off peak** and halts trading permanently. Peak starts at 1,000, so the switch fires at >= 880 USDT — always above the 800 floor |
| ~~uptime >= 90% required~~ (rule removed, 2026-07) | the always-on design stays anyway: a down agent can't de-risk, and the 800-floor doesn't care why you weren't watching. Errors are caught per bar, logged, and retried rather than crashing |
| 1 order write / 5 s | rate-limited inside `RapidXBroker`, 5.5 s spacing |
| every write preview -> submit | `place_market`/`close_position` implement preview -> submit -> readback; no blind retries |
| position mode (NET vs hedge) | `close_position` reads the position's **live** side and closes by it — omitting `positionSide` on a NET account (which carries `positionSide: NONE` and rejects any value on a reduceOnly close), keeping LONG/SHORT on a hedge account. The UAT account is NET; opens still send an explicit side, which the venue accepts |

## Track A: reasoning logs and the news sentinel

Track A scores "reasoning quality and macro sentiment capture" alongside
returns, with a Reasoning Audit for logic consistency. Two pieces address it:

- **Every decision in `deploy/ltp_ledger.jsonl` carries a `reasoning` field** —
  a plain-language narrative assembled from the quantitative facts (z-score vs
  the cost-aware band, fitted half-life, the gate the pair passed, why an exit
  fired). It is auditable precisely because it is generated FROM the decision
  inputs, not rationalized after the fact.
- **Every order/trade OPERATION is logged too.** The Track A rules require the
  log to cover every place/cancel/open/close with its final result, not just
  the decision behind it (organizer confirmation, 2026-07-15). The broker emits
  an `operation` record per API call — order state, executed qty and price from
  the readback, or the failure reason — each tagged with the `decision` and
  `pair` that caused it. The audit trail is one chain per order:
  decision (with reasoning) -> operations -> outcomes. Reconstruct it with
  `df = pd.read_json('deploy/ltp_ledger.jsonl', lines=True)` then
  `df[df.event=='operation'].groupby('decision')`.
- **`ltp_news.py` is the LLM layer**, and its role is deliberately narrow:
  hourly it reads LTP's news feed, asks Claude to rate event severity per
  traded asset (delistings, hacks, regulatory shocks — the structural breaks
  mean reversion dies on), and can VETO entries rated critical. The math
  decides trades; the LLM only ever says no. It fails open: no API key, no
  news, or an API error means no veto, and the systematic strategy runs
  unfiltered. Set `ANTHROPIC_API_KEY` (and optionally `ANTHROPIC_MODEL`,
  default claude-opus-4-8) to enable it; swap in the organizer-provided
  AI tokens when LTP distributes them.

## Streaming de-risk (the speed differentiator)

`ltp_stream.py` holds LTP's public news WebSocket open in a background
thread. When an item names an asset the agent is actively trading, the LLM
assessment fires immediately (only relevant items trigger calls — cheap on
the AI-token budget); a critical verdict wakes the agent from its inter-bar
sleep and flattens affected positions within seconds of the headline instead
of at the next hourly bar. Strictly risk-reducing: the stream can flatten or
block, never open or size up. Fails open at every layer — no `websockets`
package, a dropped connection, or a failed classification all degrade to the
hourly poll.

```bash
pip install websockets     # optional; the agent runs without it
```

The WS endpoint is public, so verify transport on the hosting machine before
the competition (this sandbox's proxy blocks WS):

```bash
python -c "
import asyncio, json, websockets
async def p():
    async with websockets.connect('wss://feeds.ltp-contest.com/feeds/v2/public') as ws:
        await ws.send(json.dumps({'event':'subscribe','arg':[{'channel':'news.category.all'}]}))
        print(await ws.recv())
asyncio.run(p())"
```

## Honest notes

- **Funding carry is not modeled.** Both perp legs pay/receive funding; the
  net on a hedged pair is usually small over day-scale holds but it is not
  zero. Logged as a gap for the Phase 1 post-mortem.
- **Fees are assumed 5 bps taker per leg** until `userFeeRate` is read from
  the live account. The optimal-bands step already refuses pairs whose edge
  can't pay this toll, so a higher real fee shrinks the tradeable set rather
  than silently losing money.
- **1,000 USDT is small.** Some symbols' `minNotional` may exceed what the
  vol-targeted sizing wants to trade; the agent skips those entries and says
  so in the log, rather than oversizing to clear the floor.
- The hourly refit/selection cadence, half-life band (6h to 1 week), and risk
  budget are set from reasoning, not from a tuned crypto backtest. Phase 1 is
  itself the out-of-sample test; expectations should be set accordingly.

## Hosting

The agent is a single process; anything that stays up works (a VPS, a spare
machine). GitHub Actions is a poor fit here — jobs cap at 6 hours and the
agent must stay alive to de-risk, not just to trade. Keep the state file
(`deploy/ltp_state.json`) on persistent disk: it carries the drawdown peak,
the halt flag, and per-pair stop blocks across restarts.
