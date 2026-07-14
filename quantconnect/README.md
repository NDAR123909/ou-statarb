# QuantConnect deployment

`main.py` is the OU pairs strategy from this repo ported to QuantConnect's LEAN
engine, so it can run on real infrastructure with a proper cost model and, if you
deploy it live, a public out-of-sample track record.

It keeps the methodology from the research code rather than starting over: the
hedge ratio is re-estimated weekly on a rolling window (the walk-forward idea),
an ADF test gates trading so the algorithm only acts while the spread is
stationary, the OU half-life sets the z-score window, and the legs are
dollar-neutral. LEAN's brokerage model handles fills and slippage.

## Running it

1. Make a free account at quantconnect.com.
2. Create a new Python algorithm and paste in `main.py`.
3. Backtest it. Read the out-of-sample stretch, not just the headline return.
4. Edit `CANDIDATES` only for pairs with an economic story you can defend.

## Where the results stand

The full 2019 to mid-2026 backtest of this algorithm is public:
[Measured Magenta Mosquito on QuantConnect](https://www.quantconnect.cloud/backtest/5619d7c9998bdb7638055166b9450c01/?theme=chrome).
Net +20.3%, max drawdown 6.3%, pairs overlay about +0.7%/yr after all costs,
QC Sharpe −0.59 against the T-bill hurdle. The Strategies hub requires backtest
Sharpe ≥ 0.4 to publish, and this strategy cannot honestly clear that on this
era's data — tuning until it did would be curve-fitting, so the static link
above is the record instead. The publish flow below is kept for a future
version that earns its way past the gate (or a competition, like CUATS, that
scores forward performance instead of a backtest).

## Publishing to the Strategies hub (the public track record)

The Strategies hub re-runs published strategies daily, so everything after the
publication date is third-party-verified out-of-sample. Their submission rules
that bit us: no try/except blocks anywhere in the code, no brokerage/fee model
overrides, backtest must finish in under an hour without runtime or
buying-power errors. `main.py` complies as committed — keep it that way.

Because LEAN backtests pay no interest on idle cash, a low-vol market-neutral
book scores a deeply negative Sharpe against the risk-free hurdle no matter
how it trades. `main.py` therefore parks spare cash in BIL (1-3 month
T-bills), which is what a real brokerage account earns anyway. Disclose it in
the strategy description: the equity curve is T-bill yield plus the pairs
overlay, and the pairs risk budget is 25 bps of NAV per pair per day.

1. Run a full backtest of the project (start 2019, no end date).
2. On quantconnect.com go to Strategies -> Publish Strategy, pick the project
   and that backtest, review the generated name/description, publish.
3. The strategy gets a permanent public page; the leaderboard score is the
   one-year Sharpe with a penalty until a full year of out-of-sample data has
   accrued — publish early, the OOS clock starts at publication.

## Honest notes

This is a starting template, not a tuned strategy. V/MA is a reasonable default
because the two move together, but the same caveats from the main project apply:
the in-sample cointegration can break, costs are real, and the live number will
sit below the backtest. The point of putting it here is the live, verifiable
record, which is worth more than any backtest curve.

Note: QuantConnect's quarterly Quant League contest wrapped up at the end of
2025 and is now folded into their "Strategies" hub, but the permanent public
strategy page and live out-of-sample tracking still work, which is the part that
matters for showing this to anyone.
