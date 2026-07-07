# v0.2: The viability upgrade

v0.1 was a research framework that was honest about being one. v0.2 closes the
specific gaps between that and something you could responsibly point real money
at. Every change below exists because its absence is a documented way pairs
strategies die in production.

## What changed

### 1. A portfolio, not a pair (`statarb/portfolio.py`)
A single pair is concentration risk. Real statistical arbitrage earns its
Sharpe from breadth: many small, roughly independent bets.
`walk_forward_portfolio()` runs the full pipeline — selection, fitting, band
optimization, trading — across a universe, in dollars against a NAV, with
per-pair risk budgets and a portfolio gross-leverage cap. All results are
out-of-sample by construction (train → test folds, refit each fold).

### 2. Selection that survives its own search (`statarb/selection.py`)
The old scan tested every pair at p<0.05 and kept the winners — the exact
procedure that manufactures false discoveries. The new selector applies:
- **Benjamini–Hochberg FDR** across every test run, so "best of N" comes with
  an honest error rate;
- **split-half stability**: cointegration must hold on both halves of the
  training window (at a power-appropriate threshold) and the two hedge ratios
  must agree — real economic linkages are stable, lucky samples are not;
- **half-life band** (3–50 days): fast enough to trade at daily bars, slow
  enough not to be microstructure noise;
- **mean-crossing count** and a **Hurst exponent** check — two cheap,
  ADF-independent confirmations that the spread actually oscillates.

### 3. Cost-aware optimal bands (`statarb/thresholds.py`)
entry=2.0 / exit=0.5 is folklore. For a given reversion speed, noise level, and
round-trip cost there is a band choice that maximizes expected profit per unit
time, computed here from exact OU first-passage times (verified against Monte
Carlo in the tests). Two consequences:
- fast spreads get tighter bands, slow ones wider — free money vs. the fixed rule;
- if no band choice is profitable after costs, the pair is flagged
  **untradeable and skipped**. "Mean-reverts" is upgraded to "mean-reverts
  enough to pay the toll."

### 4. Costs that hurt like real costs (`statarb/costs.py`)
The old backtest charged 5 bps on one leg. The new model charges commission +
half-spread on **both legs of every trade** (including hedge rebalancing),
accrues **borrow on the short leg every day** the position is on, and provides
a square-root-impact **capacity estimate** — the honest ceiling on how much
income a pair can produce before you become the market.

### 5. An escape hatch (`stop_z` in `ou.py` and everywhere downstream)
Mean reversion's catastrophic mode: the relationship breaks for good and the
model doubles down (the LTCM story). Every position now carries a z-stop; after
a stop, re-entry on the losing side is blocked until the spread heals back
inside the entry band. A regression test builds a spread that breaks mid-sample
and proves the stop caps the damage.

### 6. A deployable algorithm (`quantconnect/main.py`)
Rewritten from a single-pair template to the portfolio version: sector-
restricted candidates, weekly refits with the stability gate, vol-targeted
sizing, z-stops with re-entry blocks, half-life-scaled max holds, and a gross
leverage cap. Runs on QuantConnect against LEAN's brokerage cost model.

## What the improved system actually does on real data

`examples/real_data_portfolio.py`, 31 large caps, 2006–2017 (includes the GFC),
19 walk-forward folds, all out-of-sample, full costs including borrow:

| metric | value |
|---|---|
| net Sharpe | **0.44** |
| costs / gross PnL | 10% |
| max drawdown | ~1.1× the annual return (scales with risk budget) |
| pair-folds traded | 20 of ~800 tested (the selector rejects ~97%) |

Read that table the right way. 0.44 net is a real, positive, out-of-sample edge
after realistic costs on a deliberately small universe during a period when the
daily pairs edge was publicly known and decaying. It is not income yet. The two
levers that turn 0.44 into something fundable are both breadth, not cleverness:

1. **A bigger universe.** Sharpe scales roughly with √(number of independent
   bets). 42 candidates in 7 sectors is a toy; 300–500 liquid names across 20+
   industry groups (or the sector-ETF/constituent structure) is where this
   framework should live. The FDR machinery is exactly what makes a bigger scan
   safe.
2. **Intraday bars.** Daily-close mean reversion is the most crowded corner of
   the trade. The same OU machinery on 30–60 minute bars finds spreads with
   half-lives measured in hours, where the edge decayed less. The math doesn't
   change; only `periods_per_year` and the cost pressure do.

## What is still missing before real money

- **Execution.** Fills at the daily close are a fiction; you need an execution
  layer (the broker bridge is a start) and to measure your own slippage.
- **Borrow reality.** The model charges a flat 50 bps/yr; actual borrow is
  per-name, time-varying, and sometimes the trade simply isn't available.
  Query real locate rates before entry.
- **Corporate actions.** Mergers, spinoffs, and delistings are the #1 cause of
  "spread runs away forever." The z-stop limits the damage but a calendar-aware
  event filter should prevent the entry.
- **Regime awareness.** 2008-style correlation-to-one events hit every pair at
  once; the leverage cap helps but a portfolio-level drawdown brake belongs on top.
- **Paper first.** Run the QuantConnect algo or the Alpaca bridge for 3–6
  months and compare live fills to the backtest's assumptions before a single
  real dollar. Expect live Sharpe below backtest; if the gap is small, scale.

Nothing here is financial advice, and no backtest — including this one — is a
promise. What v0.2 guarantees is narrower and more valuable: when this system
trades, it is because the evidence survived every test we know how to run, and
when the evidence isn't there, it does the single most profitable thing a
statistical-arbitrage system can do, which is nothing.
