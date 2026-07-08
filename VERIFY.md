# VERIFY.md — how to audit this track record

This project's only real asset is credibility: a live paper-trading record that
a stranger can check, rather than a backtest they have to trust. This document
explains exactly how to do that checking. If any step below fails, the record is
compromised and should not be believed — that is the point.

Nothing here requires access to the private Alpaca account. The steps a
third party can do alone are marked **[public]**; the ones that need the account
owner to publish an export are marked **[owner-assisted]**.

---

## What the record consists of

Everything lives under `track_record/`, appended one trading day at a time by
the scheduled workflow (`.github/workflows/live.yml`):

| File | Written by | Contents |
| :--- | :--------- | :------- |
| `equity.csv` | `deploy/snapshot.py` | one row per trading day: equity, cash, long/short MV, gross leverage, fill count |
| `positions/YYYY-MM-DD.json` | `deploy/snapshot.py` | full account snapshot, open positions, and that day's fills |
| `orders/YYYY-MM-DD.json` | `deploy/run_strategy.py` | every order the strategy submitted, with intended vs reference price and the Alpaca order id |
| `state.json` | `deploy/run_strategy.py` | the strategy's frozen models, open-position ledger, and post-stop blocks |
| `README.md`, `equity.svg` | `deploy/report.py` | derived summary — NOT authoritative; regenerated from the above |

The **authority is the raw data and its git history**, never the README.

---

## 1. The git history is the timestamp **[public]**

The record is committed, not hosted on a mutable dashboard, so the commit
history is a tamper-evident clock. To verify it:

```bash
git clone https://github.com/NDAR123909/ou-statarb
cd ou-statarb

# One commit per trading day, authored by the CI bot, in date order.
git log --follow --format='%h %ci %an  %s' -- track_record/equity.csv
```

Check that:

- **Commits are append-only.** Each day adds rows/files; earlier rows are never
  edited. Compare any two consecutive commits:
  ```bash
  git log --oneline -- track_record/ | tail -r        # oldest first
  git show <commit> -- track_record/equity.csv        # only new rows appear
  ```
- **Commit timestamps line up with US market days.** The workflow runs ~21:35
  UTC on weekdays; commits should cluster there and skip weekends/holidays.
- **History was never rewritten.** The upstream branch is protected against
  force-pushes; `git reflog` on the server side and the immutable commit hashes
  mean a retroactive edit would change every downstream hash. If the published
  hashes ever change, the record has been rewritten — treat it as void.

Because a commit hash commits to all prior history, you can anchor the record in
time even more strongly by noting a recent hash somewhere external (a tweet, an
archived page). Anyone can later confirm that hash is an ancestor of the current
tip:

```bash
git merge-base --is-ancestor <anchored-hash> origin/main && echo "intact"
```

## 2. Cross-check against Alpaca's own records **[owner-assisted]**

The committed JSON is what *our code* says happened. Alpaca independently
records what *actually* happened. They must agree.

The account owner exports account activity from Alpaca — either the dashboard
(**Account → Activity → export**) or the API:

```bash
curl -H "APCA-API-KEY-ID: $ALPACA_KEY_ID" \
     -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY" \
     "https://paper-api.alpaca.markets/v2/account/activities?activity_types=FILL"
# and portfolio history for the equity curve:
curl -H "APCA-API-KEY-ID: $ALPACA_KEY_ID" \
     -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY" \
     "https://paper-api.alpaca.markets/v2/account/portfolio/history?period=6M&timeframe=1D"
```

Publishing that export lets anyone diff it against the committed record:

- **Fills.** Every fill in Alpaca's `FILL` activities should appear in a
  `track_record/positions/*.json` `fills` array (and be traceable to an
  `orders/*.json` entry by `order_id`), with matching symbol, signed quantity,
  price, and timestamp. No committed fill should be missing from Alpaca, and no
  Alpaca fill should be missing from the record.
- **Equity curve.** Alpaca's daily portfolio-history equity should match the
  `equity` column of `equity.csv` day for day (small marking differences from
  snapshot timing are expected; large or one-directional gaps are not).
- **Order ids are real.** Each `order_id` in `orders/*.json` resolves to a real
  order under that Alpaca account.

A one-line pandas join is enough to check the whole thing; the logs are
structured for exactly that (see Phase 3 in `CLAUDE.md`).

## 3. Confirm the parameters were frozen in advance **[public]**

The strategy was preregistered in [`PREREGISTRATION.md`](PREREGISTRATION.md)
*before* the record accumulated. Verify two things:

- **The registration predates the data.** The commit that added
  `PREREGISTRATION.md` should be at or before the first `equity.csv` row's date:
  ```bash
  git log --format='%ci %s' -- PREREGISTRATION.md | tail -1
  head -2 track_record/equity.csv
  ```
- **No forbidden parameter changed during the window.** The preregistration
  allows bug fixes but forbids parameter tuning. Inspect the history of the
  files that define the strategy's numbers and confirm every change is a bug
  fix, not a threshold being nudged after a bad stretch:
  ```bash
  git log -p -- deploy/run_strategy.py statarb/selection.py statarb/costs.py
  ```
  Look specifically at `stop_z`, `risk_per_pair_bps`, the leverage caps, the
  selection thresholds, the fit `lookback`, and the universe. If any of these
  changed mid-experiment for a non-bug reason, the experiment was contaminated
  and (per the rules) should have been restarted as a new preregistration.

## 4. Reproduce the signals yourself **[public, with data]**

The strategy is deterministic: given the same Alpaca-adjusted daily bars, the
z-scores, selected pairs, and order directions are fully reproducible. With your
own market data you can recompute what the strategy *should* have done on a given
day and confirm it matches `orders/YYYY-MM-DD.json`:

- betas/bands are frozen weekly and recorded in `state.json` at each refit;
- the daily z-score uses only past data through that day's close
  (`pair_signal` in `deploy/run_strategy.py`);
- entries fire on the frozen bands, exits/stops on `stop_z` and the half-life
  max-hold, with the one-sided re-entry block.

Any discrepancy between a recomputed signal and the committed order is either a
bug (which should be fixed and disclosed) or a data difference (adjustments,
timing) — both are worth surfacing.

## 5. Structural integrity checks **[public]**

The harness is built so certain failures are impossible-by-construction; confirm
the invariants still hold:

- **No duplicate days.** `equity.csv` has one row per date:
  ```bash
  cut -d, -f1 track_record/equity.csv | tail -n +2 | sort | uniq -d   # empty
  ```
- **Every equity row has a positions file** and vice versa (dates line up).
- **Re-running a day is idempotent** — a second run on the same date replaces
  the row rather than appending, so the count of rows equals the count of
  distinct trading days.

---

## The honest limits of this record

Auditing proves the record is *real and unaltered*. It does not turn a paper
account into a live one. Known gaps, stated plainly so no one has to discover
them:

- **Paper, not real money.** Alpaca paper fills are simulated; there is no true
  market impact, no partial-fill/borrow-availability friction, and shorts never
  fail to locate. Real trading would be worse.
- **Borrow is modeled flat** at 50 bps/yr, not per-name; crowded shorts cost
  more in reality.
- **Free-tier data.** Latest trades come from the IEX feed (the broker records
  `last_feed_used`); a different feed could shift prices slightly.
- **Post-close execution.** Orders are decided on the close and fill at the next
  open — a real lag that is measured in `orders/*.json` (intended vs fill), not
  hidden.
- **Short history.** Until ~60 trading days, every performance number is noise,
  and the report labels it as such.

If you find a way the record could be faked that these checks would miss, that
is a bug in this document — please open an issue.
