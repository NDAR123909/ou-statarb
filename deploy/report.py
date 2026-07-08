"""
Regenerate the human-readable track-record report after each run.

This is reporting ONLY. It reads the committed record
(`track_record/equity.csv` and the daily positions JSONs), computes summary
statistics, draws an equity curve, and writes `track_record/README.md` plus
`track_record/equity.svg`. It makes no broker calls and touches no trading
logic, so it is safe to run anywhere and cannot influence the experiment it
describes.

Two honesty rules are baked into the output rather than left to the reader:

  * Live Sharpe is labeled statistical noise until ~60 trading days have
    accumulated. A Sharpe computed from a handful of days is meaningless and
    saying so is not optional here.
  * The backtest number is shown next to the live number as a GAP, framed so
    the live result is expected to be at or below the backtest, never above.
    The whole point of the record is to measure that gap honestly.

The SVG is hand-built (no matplotlib backend, no fonts) so the committed chart
is deterministic and diffs cleanly day to day.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Reference backtest result, from IMPROVEMENTS.md / examples/real_data_portfolio.py.
# This is the honest baseline the live record is measured against.
BACKTEST_SHARPE = 0.44
BACKTEST_DESC = "31-name DJIA universe, 2006-2017 OOS, net of costs"
SHARPE_NOISE_DAYS = 60          # below this, live Sharpe is noise, full stop
PERIODS_PER_YEAR = 252


# --------------------------------------------------------------------------- #
#  Statistics                                                                 #
# --------------------------------------------------------------------------- #
def compute_stats(df: pd.DataFrame) -> dict:
    """Summary stats from the equity table. Everything degrades gracefully
    when there are too few rows to say anything (the common early case)."""
    n = len(df)
    eq = df["equity"].astype(float)
    out = {
        "n_days": n,
        "start_equity": float(eq.iloc[0]) if n else np.nan,
        "current_equity": float(eq.iloc[-1]) if n else np.nan,
        "first_date": df["date"].iloc[0] if n else None,
        "last_date": df["date"].iloc[-1] if n else None,
        "total_return_pct": np.nan,
        "sharpe": None,
        "sharpe_is_noise": True,
        "max_drawdown_pct": np.nan,
        "current_gross_leverage": float(df["gross_leverage"].iloc[-1]) if n else np.nan,
        "avg_gross_leverage": float(df["gross_leverage"].mean()) if n else np.nan,
        "total_fills": int(df["n_fills"].sum()) if n else 0,
    }
    if n >= 1 and out["start_equity"] > 0:
        out["total_return_pct"] = (out["current_equity"] / out["start_equity"] - 1) * 100.0
        dd = (eq / eq.cummax() - 1.0).min()
        out["max_drawdown_pct"] = float(dd) * 100.0

    rets = eq.pct_change().dropna()
    sd = rets.std(ddof=1) if len(rets) >= 2 else 0.0
    if len(rets) >= 2 and sd > 0:
        out["sharpe"] = float(np.sqrt(PERIODS_PER_YEAR) * rets.mean() / sd)
    out["sharpe_is_noise"] = out["n_days"] < SHARPE_NOISE_DAYS
    return out


# --------------------------------------------------------------------------- #
#  Equity curve SVG (deterministic, dependency-free)                          #
# --------------------------------------------------------------------------- #
def equity_svg(df: pd.DataFrame, width: int = 720, height: int = 240) -> str:
    """A clean line chart of equity over time. Colors are chosen to read on
    both light and dark GitHub themes; the baseline is the starting equity."""
    pad_l, pad_r, pad_t, pad_b = 56, 16, 16, 28
    eq = df["equity"].astype(float).to_numpy()
    n = len(eq)
    base = float(eq[0]) if n else 0.0

    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    if n >= 2:
        lo, hi = float(eq.min()), float(eq.max())
        span = max(hi - lo, abs(base) * 1e-4, 1e-9)
        lo -= span * 0.08
        hi += span * 0.08
    else:
        # one point (or none): show a flat line at the baseline
        lo, hi = base * 0.999 - 1, base * 1.001 + 1

    def x(i):
        return pad_l + (plot_w * (i / (n - 1)) if n > 1 else plot_w / 2)

    def y(v):
        return pad_t + plot_h * (1 - (v - lo) / (hi - lo))

    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(eq)) if n else ""
    y_base = y(base)
    axis = "#8b949e"
    line = "#2da44e" if (n and eq[-1] >= base) else "#cf222e"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="monospace" font-size="11">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="none"/>',
        # frame
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+plot_h}" stroke="{axis}" stroke-width="1"/>',
        f'<line x1="{pad_l}" y1="{pad_t+plot_h}" x2="{pad_l+plot_w}" y2="{pad_t+plot_h}" stroke="{axis}" stroke-width="1"/>',
        # starting-equity baseline
        f'<line x1="{pad_l}" y1="{y_base:.1f}" x2="{pad_l+plot_w}" y2="{y_base:.1f}" '
        f'stroke="{axis}" stroke-width="1" stroke-dasharray="4 3" opacity="0.7"/>',
        # y labels
        f'<text x="{pad_l-6}" y="{pad_t+4:.1f}" text-anchor="end" fill="{axis}">${hi:,.0f}</text>',
        f'<text x="{pad_l-6}" y="{pad_t+plot_h:.1f}" text-anchor="end" fill="{axis}">${lo:,.0f}</text>',
    ]
    if n:
        parts.append(
            f'<text x="{pad_l}" y="{height-8}" fill="{axis}">{df["date"].iloc[0]}</text>')
        parts.append(
            f'<text x="{pad_l+plot_w}" y="{height-8}" text-anchor="end" '
            f'fill="{axis}">{df["date"].iloc[-1]}</text>')
    if n >= 2:
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{line}" stroke-width="2"/>')
    elif n == 1:
        parts.append(f'<circle cx="{x(0):.1f}" cy="{y(eq[0]):.1f}" r="3" fill="{line}"/>')
    parts.append("</svg>")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
#  README                                                                     #
# --------------------------------------------------------------------------- #
def _fmt(v, spec="", dash="—"):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return dash
    return format(v, spec)


def render_readme(stats: dict) -> str:
    n = stats["n_days"]

    if stats["sharpe"] is None:
        sharpe_cell = "n/a (need ≥2 days with equity variation)"
    elif stats["sharpe_is_noise"]:
        sharpe_cell = (f"{stats['sharpe']:.2f}  ⚠️ **NOISE** — only {n} of "
                       f"~{SHARPE_NOISE_DAYS} days needed before this means anything")
    else:
        sharpe_cell = f"{stats['sharpe']:.2f}"

    gap_note = (
        f"The reference backtest netted **Sharpe ≈ {BACKTEST_SHARPE:.2f}** "
        f"({BACKTEST_DESC}). That is a weak-but-real edge, and the live result "
        f"is **expected to land at or below it** — costs, slippage, and the "
        f"post-close fill lag all subtract. The number worth watching is the "
        f"*gap*, not the live Sharpe alone, and it is not interpretable until "
        f"the ~{SHARPE_NOISE_DAYS}-day mark."
    )
    if stats["sharpe"] is not None and not stats["sharpe_is_noise"]:
        gap = stats["sharpe"] - BACKTEST_SHARPE
        gap_note += (f"\n\nCurrent live − backtest gap: **{gap:+.2f}** "
                     f"(live {stats['sharpe']:.2f} vs backtest {BACKTEST_SHARPE:.2f}).")

    lines = [
        "# Live paper-trading track record",
        "",
        "_Auto-generated by `deploy/report.py` after each run. Do not edit by "
        "hand — changes are overwritten. The authority is the committed data "
        "(`equity.csv`, `positions/`, `orders/`) and its git history, not this "
        "summary._",
        "",
        f"**Window:** {_fmt(stats['first_date'])} → {_fmt(stats['last_date'])} "
        f"· **{n} trading day(s) recorded**",
        "",
        "![equity curve](equity.svg)",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| :----- | :---- |",
        f"| Current equity | ${_fmt(stats['current_equity'], ',.2f')} |",
        f"| Total return | {_fmt(stats['total_return_pct'], '+.2f')}% |",
        f"| Max drawdown | {_fmt(stats['max_drawdown_pct'], '.2f')}% |",
        f"| Live Sharpe (annualized) | {sharpe_cell} |",
        f"| Current gross leverage | {_fmt(stats['current_gross_leverage'], '.2f')}× |",
        f"| Average gross leverage | {_fmt(stats['avg_gross_leverage'], '.2f')}× |",
        f"| Total fills to date | {stats['total_fills']} |",
        "",
        "## Backtest vs live",
        "",
        gap_note,
        "",
        "## How to read this",
        "",
        f"- **Sharpe is noise below ~{SHARPE_NOISE_DAYS} trading days.** A ratio "
        "from a handful of days is dominated by luck; it is flagged as noise "
        "above until enough data accumulates.",
        "- **Everything here is out-of-sample.** Parameters were frozen in "
        "[`PREREGISTRATION.md`](../PREREGISTRATION.md) before the record began.",
        "- **Borrow is modeled flat at 50 bps/yr**, not per-name — one of the "
        "known gaps to weigh when reading the backtest-vs-live gap.",
        "- To audit this record yourself, see [`VERIFY.md`](../VERIFY.md).",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
#  Entry point                                                                #
# --------------------------------------------------------------------------- #
def generate(root: Path) -> dict:
    """Write README.md and equity.svg under `root`; return the stats used."""
    root = Path(root)
    csv_path = root / "equity.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"date": str}).sort_values("date")
        df = df.reset_index(drop=True)
    else:
        df = pd.DataFrame(columns=[
            "date", "equity", "cash", "long_market_value", "short_market_value",
            "gross_leverage", "buying_power", "n_positions", "n_fills"])

    stats = compute_stats(df)
    (root / "equity.svg").write_text(equity_svg(df))
    (root / "README.md").write_text(render_readme(stats))
    return stats


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("track_record")
    stats = generate(root)
    print(f"report written: {stats['n_days']} day(s), "
          f"equity=${_fmt(stats['current_equity'], ',.2f')}, "
          f"sharpe={_fmt(stats['sharpe'], '.2f')}"
          f"{' (noise)' if stats['sharpe_is_noise'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
