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
| drawdown > 20% from peak = disqualified | kill switch flattens everything at **12%** and halts trading permanently; the process stays alive |
| uptime >= 90% required | one long-running process; errors are caught per bar, logged, and retried next bar rather than crashing |
| 1 order write / 5 s | rate-limited inside `RapidXBroker`, 5.5 s spacing |
| every write preview -> submit | `place_market`/`close_position` implement preview -> submit -> readback; no blind retries |
| hedge (BOTH) position mode | every order carries an explicit `positionSide` |

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
uptime requirement is on the agent, not on a cron. Keep the state file
(`deploy/ltp_state.json`) on persistent disk: it carries the drawdown peak,
the halt flag, and per-pair stop blocks across restarts.
