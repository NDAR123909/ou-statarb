"""
deploy/universe_scan.py — read-only breadth diagnostic (NO trading).

The live agent tests only 14 hand-picked pairs and has been thin-to-idle. This
answers the one question that decides what to do about it: is a *wider but
equally rigorous* universe finding genuine mean-reverting pairs (a breadth
problem we can fix), or is the whole market trending so that even a broad
search comes up empty on the Hurst/crossings gates (a regime, where sitting
out is correct and forcing trades loses money)?

It changes nothing: it fetches klines, runs the EXACT same selection gates
(`select_pairs` + the same `SelectionConfig` the agent builds at refit, with
Benjamini-Hochberg FDR applied across every pair tested), and prints what
passes. Nothing is loosened. Pairs are formed only *within* economically
defined sector groups — restricting the search space is itself a
multiple-testing correction and the one that carries economic meaning, so we
never test blind all-vs-all combinations.

    set -a; source /root/ltp.env; set +a
    python deploy/universe_scan.py

Honest reading of the result:
  - If the expanded universe passes several pairs the current 14 don't ->
    breadth problem; a disclosed CANDIDATES expansion is warranted.
  - If it also comes back mostly Hurst/crossings rejects -> regime; idle is
    the correct, drawdown-protecting state and we do not manufacture trades.
"""

from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.ltp_broker import RapidXBroker                       # noqa: E402
from deploy.ltp_agent import AgentConfig, fetch_panel, CANDIDATES  # noqa: E402
from statarb.selection import SelectionConfig, select_pairs      # noqa: E402


def _sym(base: str) -> str:
    return f"BINANCE_PERP_{base}_USDT"


# Economically-motivated sector groups. Pairs are formed only WITHIN a group.
# A coin may sit in more than one group (different economic lenses); duplicate
# pairs are de-duplicated. Symbols not on the whitelist simply return no data
# and are dropped, so an over-broad list here is harmless.
SECTOR_GROUPS: dict[str, list[str]] = {
    "gold": ["XAUT", "PAXG"],
    "privacy": ["XMR", "ZEC", "DASH"],
    "pow": ["ETC", "KAS", "LTC", "BCH"],
    "payments": ["XRP", "XLM"],
    "l1_smartcontract_v1": ["ADA", "DOT", "ATOM"],
    "l1_highperf": ["SOL", "AVAX", "SUI", "APT"],
    "l1_enterprise": ["HBAR", "ALGO", "VET"],
    "compute_platform": ["NEAR", "ICP"],
    "cosmos": ["ATOM", "TIA", "INJ"],
    "storage": ["FIL", "AR"],
    "ai_compute": ["TAO", "RENDER", "FET", "WLD"],
    "memes": ["DOGE", "1000SHIB", "1000PEPE", "WIF"],
    "defi_lending": ["AAVE", "COMP", "MKR"],
    "defi_dex": ["UNI", "CRV", "SUSHI"],
    "liquid_staking": ["LDO", "RPL"],
    "oracle": ["LINK", "BAND", "PYTH"],
    "middleware": ["LINK", "QNT"],
    "l2_eth": ["ARB", "OP", "STRK"],
    "exchange": ["BNB", "OKB"],
}


def _sel_cfg(cfg: AgentConfig) -> SelectionConfig:
    """Identical to the SelectionConfig the agent builds in refit()."""
    return SelectionConfig(
        fdr_q=cfg.fdr_q,
        min_half_life=cfg.min_half_life,
        max_half_life=cfg.max_half_life,
        periods_per_year=cfg.bars_per_year,
        min_crossings_per_year=8.0 * (cfg.bars_per_year / 252),
        min_abs_beta=cfg.min_abs_beta,
        max_abs_beta=cfg.max_abs_beta,
    )


def _base(sym: str) -> str:
    parts = sym.split("_")
    return parts[2] if len(parts) > 2 else sym


def _report(table, label: str) -> int:
    passed = table[table.passed]
    print(f"\n== {label}: {len(passed)}/{len(table)} pass ==")
    for _, r in passed.sort_values("adf_pvalue").iterrows():
        print(f"   {_base(r.a)}/{_base(r.b):<9} adf_p={r.adf_pvalue:.4f} "
              f"hurst={r.hurst:.2f} half_life={r.half_life:.0f}h "
              f"beta={r.beta:+.2f} crossings={int(r.crossings)}")
    if len(passed) < len(table):
        rej = table.loc[~table.passed, "reject_reason"].value_counts().to_dict()
        print(f"   rejects: {rej}")
    return len(passed)


def main() -> int:
    cfg = AgentConfig()
    broker = RapidXBroker()
    sel = _sel_cfg(cfg)

    all_syms = sorted({_sym(b) for g in SECTOR_GROUPS.values() for b in g})
    print(f"fetching {len(all_syms)} candidate symbols "
          f"({cfg.lookback_bars} bars each; this takes a couple minutes) ...")
    panel = fetch_panel(broker, all_syms, cfg)
    if panel.empty:
        print("no data panel — aborting.")
        return 1

    available = set(panel.columns)
    missing = sorted(_base(s) for s in all_syms if s not in available)
    print(f"\navailable on whitelist: {len(available)}/{len(all_syms)}")
    print(f"dropped (no data): {missing}")

    # within-group pairs among available symbols, de-duplicated
    pairs: set[tuple[str, str]] = set()
    for group in SECTOR_GROUPS.values():
        syms = sorted(_sym(b) for b in group if _sym(b) in available)
        pairs.update(combinations(syms, 2))
    pairs_list = sorted(pairs)

    expanded = select_pairs(panel, candidates=pairs_list, cfg=sel)
    n_expanded = _report(expanded, f"EXPANDED universe ({len(pairs_list)} "
                                    f"sector pairs, FDR across all)")

    # apples-to-apples: the current 14, scored on the same panel
    current = [(a, b) for a, b in CANDIDATES
               if a in available and b in available]
    cur_table = select_pairs(panel, candidates=current, cfg=sel)
    n_current = _report(cur_table, f"CURRENT universe ({len(current)} pairs)")

    print("\n" + "=" * 60)
    if n_expanded > n_current and n_expanded >= 3:
        print(f"VERDICT: breadth helps — {n_expanded} genuine pairs pass the "
              f"unchanged gates vs {n_current} in the current set. A disclosed "
              f"CANDIDATES expansion is warranted.")
    elif n_expanded <= 1:
        print(f"VERDICT: regime — even {len(pairs_list)} rigorous sector pairs "
              f"yield {n_expanded}. Mean-reversion is hard right now; idle is "
              f"the correct, drawdown-protecting state. Do not force trades.")
    else:
        print(f"VERDICT: marginal — {n_expanded} vs {n_current}. Read the "
              f"reject reasons above before deciding; breadth is not a clear win.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
