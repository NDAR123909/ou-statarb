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
4. Swap `self.tickers` for a pair with an economic story you can defend, and
   tune `entry_z`, `exit_z`, and `lookback`.
5. To build a real track record, deploy it live (paper is fine) and publish the
   strategy so the forward performance is tracked on a permanent page.

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
