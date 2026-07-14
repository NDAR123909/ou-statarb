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

## Publishing to the Strategies hub (the public track record)

The Strategies hub re-runs published strategies daily, so everything after the
publication date is third-party-verified out-of-sample. Their submission rules
that bit us: no try/except blocks anywhere in the code, no brokerage/fee model
overrides, backtest must finish in under an hour without runtime or
buying-power errors. `main.py` complies as committed — keep it that way.

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
