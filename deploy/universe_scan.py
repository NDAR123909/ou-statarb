"""
deploy/universe_scan.py — read-only breadth diagnostic (NO trading).

The live agent tests 15 hand-picked crypto pairs and has been thin-to-idle.
This answers the one question that decides what to do about it: is a *wider but
equally rigorous* universe finding genuine mean-reverting pairs (a breadth
problem we can fix), or is the whole market trending so that even a broad
search comes up empty on the Hurst/crossings gates (a regime, where sitting
out is correct and forcing trades loses money)?

**2026-09-11: the question changed shape, because the universe did.** The
organizer confirmed that any instrument orderable under the RapidX perp
portfolio is eligible regardless of underlying, and a probe sweep
(`universe_discover.py`) found **60 live symbols on Binance** against the 30 in
CANDIDATES -- including WTI crude (CL), Brent (BZ), soybeans (ZS), an S&P
contract (SPX) and four mega-cap equities.

That matters because the 0-of-55 result on 2026-09-09 was a **one-factor**
finding: every crypto perp shares BTC beta, so when the complex trends they all
fail the split-half and crossing gates together, and widening *within* crypto
cannot help. Grouping by ECONOMIC DRIVER rather than by crypto narrative is the
first time this scan has been able to test anything else. CL/BZ in particular
is a physical arbitrage relationship, not a thematic one.

It changes nothing: it fetches klines, runs the EXACT same selection gates
(`select_pairs` + the same `SelectionConfig` the agent builds at refit, with
Benjamini-Hochberg FDR applied across every pair tested), and prints what
passes. Nothing is loosened. Pairs are formed only *within* economically
defined sector groups — restricting the search space is itself a
multiple-testing correction and the one that carries economic meaning, so we
never test blind all-vs-all combinations.

The CURRENT-universe comparison is only worth something if it covers the whole
live book. It silently did not until 2026-09-09: symbols were fetched from
SECTOR_GROUPS alone, so any CANDIDATES pair whose legs were not also listed
there was dropped without a word. Two fixes, because either alone would rot
again — the fetch set is now the *union* of both lists, and any candidate pair
still excluded for missing data is named in the output rather than subtracted
from a count.

    set -a; source /root/ltp.env; set +a
    python deploy/universe_discover.py      # refresh the manifest first
    python deploy/universe_scan.py

Honest reading of the result:
  - If the expanded universe passes several pairs the current 14 don't ->
    breadth problem; a disclosed CANDIDATES expansion is warranted.
  - If it also comes back mostly Hurst/crossings rejects -> regime; idle is
    the correct, drawdown-protecting state and we do not manufacture trades.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from deploy.ltp_broker import RapidXBroker                       # noqa: E402
from deploy.ltp_agent import AgentConfig, fetch_panel, CANDIDATES  # noqa: E402
from statarb.ou import fit_spread_model                         # noqa: E402
from statarb.selection import SelectionConfig, select_pairs      # noqa: E402
import numpy as np                                              # noqa: E402


# ~~The standing venue decision~~ -- ANSWERED 2026-09-11 by the organizer:
# "You can place orders on both Binance and OKX for a single RapidX portfolio
# but only on perpetuals for Phase II." So there is no choice to make; we take
# the union. VENUE remains the default for `_sym` and for the live agent, whose
# CANDIDATES are all Binance.
VENUE = "BINANCE"
VENUES = ("BINANCE", "OKX")


def _sym(base: str, venue: str | None = None) -> str:
    return f"{venue or VENUE}_PERP_{base}_USDT"


# Groups by ECONOMIC DRIVER. Pairs are formed only WITHIN a group, and that
# restriction is itself a multiple-testing correction -- the one that carries
# economic meaning -- so we never test blind all-vs-all combinations. A symbol
# may sit in more than one group (different lenses); duplicate pairs are
# de-duplicated.
#
# The non-crypto groups arrived 2026-09-11 and are the point of this file now.
# Every crypto perp shares BTC beta, which is why the 09-09 scan failed all 55
# pairs at once on split-half and crossings: a single factor trending takes the
# whole set down together. Crude, equities and an index are driven by different
# things, so the probability that SOMETHING is mean-reverting at a given moment
# is structurally higher.
#
# A note on gaps, since it cuts the other way from the obvious worry: these
# perps trade 24/7 while their underlyings do not, so a weekend move arrives as
# a jump -- which the z-stop handles worst. But WITHIN a driver both legs jump
# together, so the SPREAD is largely insulated. The gap risk lands on
# cross-driver pairs, which this grouping already excludes on economic grounds.
NON_CRYPTO = ("energy", "megacap_equity", "index_vs_member", "ags")

SECTOR_GROUPS: dict[str, list[str]] = {
    # WTI and Brent: two grades of the same physical commodity, arbitraged
    # against each other for decades. Spot-checked 2026-09-11 at 96.63 / 100.83
    # -- a $4.20 differential, which is where that spread actually lives. This
    # is the strongest economic prior in the whole file and nothing in crypto
    # comes close to it.
    "energy": ["CL", "BZ"],
    # The asset class this framework was WRITTEN for. The reference backtest is
    # 31 DJIA names at 0.36 net Sharpe OOS; we have been running an equity
    # statarb engine on crypto for eight weeks because that is what the Phase I
    # whitelist contained.
    "megacap_equity": ["AAPL", "MSFT", "NVDA", "TSLA"],
    # An index against its own large constituents is cointegrated close to by
    # construction, since each is a material weight of the other.
    "index_vs_member": ["SPX", "AAPL", "MSFT", "NVDA", "TSLA"],
    # ZS (soybeans) has no partner on Binance, so it forms no pair. Listed so
    # the manifest check reports it rather than leaving it invisible.
    "ags": ["ZS"],
    # The two largest assets. Omitted until 2026-09-09, which silently dropped
    # ETH/BTC from the CURRENT-universe comparison -- the pair that passed the
    # gate on six of the eight refits before that date. The scan reported
    # "CURRENT universe (14 pairs)" against a live book of 15 and nothing said
    # why. See the union in main(): a symbol in CANDIDATES is now always
    # fetched whether or not anyone remembers to list it here.
    "majors": ["BTC", "ETH"],
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


MANIFESTS = ("universe_manifest.json", "universe_manifest_nc.json")


def live_symbols() -> set[str] | None:
    """Symbols confirmed live by `universe_discover.py`, or None if unprobed.

    There is no listing endpoint -- all 53 RapidX capabilities take a symbol as
    input -- so "is this tradeable" is only answerable by probing, and the
    manifests are that probe's output. Read here so an unlisted name is NAMED
    below rather than vanishing into `fetch_panel`'s silent drop, which is how
    ETH/BTC went untested for a day and would have hidden every non-crypto
    symbol just as quietly.

    Returns None rather than an empty set when no manifest exists: "not probed"
    and "probed and found nothing" must not look alike.
    """
    here = Path(__file__).resolve().parent
    out: set[str] = set()
    found = False
    for name in MANIFESTS:
        path = here / name
        if not path.exists():
            continue
        found = True
        try:
            blob = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        out |= {r["symbol"] for r in blob.get("symbols", [])
                if r.get("state") == "live"}
    return out if found else None


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


def _cost_z(panel, a: str, b: str, cfg: AgentConfig) -> float | None:
    """Round-trip cost measured in units of the spread's OWN sigma.

    "Cointegrates" and "is tradeable" are different claims and this scan
    conflated them until 2026-09-11. It matters most for the cross-venue pairs
    added that day: the same underlying priced on two venues is the purest
    cointegration in the universe -- one asset, one price, the spread is
    nothing but venue basis -- and it is precisely that purity which makes the
    spread tiny. A few bps of basis against ~7-14 bps of round trip (two legs,
    each way, at the measured taker fee) leaves nothing. `optimal_bands` is
    entitled to say no, and this number is why it would.
    """
    try:
        m = fit_spread_model(panel[a].values, panel[b].values)
    except Exception:                                        # noqa: BLE001
        return None
    if not np.isfinite(m.ou.sigma_eq) or m.ou.sigma_eq <= 0:
        return None
    return (2.0 * cfg.taker_fee * (1.0 + abs(m.beta))) / m.ou.sigma_eq


def _stratified_diagnostic(panel, groups: dict, sel, pooled_pass: int) -> None:
    """What FDR *within* each pre-declared stratum would yield. A DIAGNOSTIC.

    Nothing here changes selection. `CLAUDE.md` invariant 3 stands: the live
    gate applies FDR across every test run, and it still does.

    This exists because the 2026-09-11 review owes a decision on stratified
    correction, and that decision was deferred with a pre-committed test --
    "run it both ways on the same panel and compare what ELSE passes, not just
    whether CL/BZ does." Producing that comparison is not making the change.
    The distinction matters: CL/BZ passed every economic and statistical gate
    (hurst 0.35, hl 23.9h, beta +0.95) and died only to Benjamini-Hochberg at
    m=66, so the temptation to re-cut the family is real and is exactly why the
    decision needs evidence about the junk it would also admit.
    """
    print("\n" + "=" * 60)
    print("STRATIFIED DIAGNOSTIC — FDR within each stratum, NOT the live gate")
    print("=" * 60)
    print(f"   pooled (live behaviour, invariant 3): {pooled_pass} pass\n")
    total = 0
    for name, pairs in sorted(groups.items()):
        if len(pairs) < 1:
            continue
        table = select_pairs(panel, candidates=sorted(pairs), cfg=sel)
        passed = table[table.passed]
        total += len(passed)
        if len(passed):
            names = ", ".join(f"{_base(r.a)}/{_base(r.b)}"
                              for _, r in passed.iterrows())
            print(f"   {name:<18}{len(passed)}/{len(pairs):<4} {names}")
    print(f"\n   stratified total: {total} pass vs {pooled_pass} pooled")
    print("   READ THE DIFFERENCE AS THE PRICE, not as the prize: every extra")
    print("   pass here is a hypothesis the pooled correction was refusing.")


def _report_group(table, bases: set[str], label: str) -> None:
    """EVERY pair in a set, passing or not, with the gate that rejected it.

    Added 2026-09-11, because the first driver-grouped run printed only the
    passing rows and so could not answer the question it existed to ask.

    CL/BZ is WTI against Brent -- two grades of one physical commodity, a
    $4.20 differential spot-checked the same day. It is as close to a known
    true positive as this project will ever get, which makes it a **control on
    the gates** rather than merely a candidate. A pipeline that rejects it is
    telling us something about itself, and an aggregate reject tally cannot say
    which gate did it. `half-life out of band` and `too few mean crossings`
    would mean the 6h-168h band -- chosen for hourly crypto -- excludes
    commodity spreads for being SLOW, not for failing to revert. That is a
    very different finding from `fails split-half cointegration`, which would
    mean the relationship genuinely broke inside the window.
    """
    rows = [r for _, r in table.iterrows()
            if _base(r.a) in bases and _base(r.b) in bases]
    print(f"\n== {label}: {sum(1 for r in rows if r.passed)}/{len(rows)} pass ==")
    for r in sorted(rows, key=lambda r: r.adf_pvalue):
        verdict = "PASS" if r.passed else f"rejected: {r.reject_reason}"
        print(f"   {_base(r.a)}/{_base(r.b):<9} adf_p={r.adf_pvalue:.4f} "
              f"hurst={r.hurst:.2f} hl={r.half_life:>7.1f}h beta={r.beta:+.2f} "
              f"cross={int(r.crossings):>3}  {verdict}")


def _return_vol(panel, sym: str) -> float:
    """Volatility of log returns for one symbol on the panel."""
    import numpy as np
    return float(np.std(np.diff(panel[sym].values), ddof=1))


def compare_orientations(panel, unordered: list[tuple[str, str]], sel) -> None:
    """Engle-Granger is orientation-sensitive: regressing A on B is not the
    same test as B on A, so which direction we happened to type into
    CANDIDATES silently decides whether a genuinely cointegrated pair is
    found. That is luck, not rigour. Compare three ways of resolving it:

      alpha    — alphabetical (arbitrary; the status quo)
      vol-rule — deterministic and chosen a priori: the MORE volatile series
                 is the dependent variable, so the cleaner series is the
                 regressor. This is the standard errors-in-variables
                 mitigation (measurement noise in the regressor attenuates
                 beta), and it never looks at a p-value, so it adds no
                 multiple testing at all.
      both     — test both directions and accept a pair if either passes,
                 with the FDR correction applied across ALL 2N tests. This is
                 the honest price: doubling the tests raises the bar for
                 everyone (repo invariant 3).

    'both' will always find at least as many pairs as the others; the
    question the numbers have to answer is whether it finds them because the
    relationships are real or because we looked twice."""
    alpha = sorted(unordered)
    volrule = [(a, b) if _return_vol(panel, a) >= _return_vol(panel, b)
               else (b, a) for a, b in alpha]
    both = [p for a, b in alpha for p in ((a, b), (b, a))]

    for label, cands in (("alpha (status quo)", alpha),
                         ("vol-rule (a priori)", volrule),
                         ("both directions (FDR over 2N)", both)):
        table = select_pairs(panel, candidates=cands, cfg=sel)
        passed = table[table.passed]
        uniq = {frozenset((r.a, r.b)) for _, r in passed.iterrows()}
        print(f"\n-- orientation policy: {label} -- "
              f"{len(uniq)} distinct pairs pass ({len(cands)} tests)")
        for _, r in passed.sort_values("adf_pvalue").iterrows():
            print(f"   {_base(r.a)}/{_base(r.b):<9} adf_p={r.adf_pvalue:.4f} "
                  f"hurst={r.hurst:.2f} hl={r.half_life:.0f}h "
                  f"beta={r.beta:+.2f} cross={int(r.crossings)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="breadth diagnostic, no trading")
    ap.add_argument("--venues", default=",".join(VENUES))
    ap.add_argument("--no-cross-venue", action="store_true",
                    help="skip same-underlying-two-venue pairs")
    args = ap.parse_args()
    venues = [v.strip().upper() for v in args.venues.split(",") if v.strip()]

    cfg = AgentConfig()
    broker = RapidXBroker()
    sel = _sel_cfg(cfg)

    # Union, deliberately. The sector groups define the EXPANDED search; the
    # live CANDIDATES define what the book actually trades. Fetching only the
    # first silently narrows the second, which is how ETH/BTC went untested.
    all_bases = sorted({b for g in SECTOR_GROUPS.values() for b in g}
                       | {s.split("_")[2] for p in CANDIDATES for s in p})
    sector_syms = {_sym(b, v) for b in all_bases for v in venues}
    cand_syms = {s for p in CANDIDATES for s in p}
    all_syms = sorted(sector_syms | cand_syms)

    known_live = live_symbols()
    if known_live is None:
        print("note: no manifest found — run deploy/universe_discover.py first "
              "so unlisted symbols are named rather than silently dropped")
    else:
        # Probe-confirmed absences, named per venue. An unlisted symbol that
        # merely vanishes into fetch_panel looks identical to a market with
        # nothing in it, which is the wrong conclusion to hand a reader.
        all_syms = [s for s in all_syms if s in known_live or s in cand_syms]
        for group, bases in SECTOR_GROUPS.items():
            for v in venues:
                absent = [b for b in bases if _sym(b, v) not in known_live]
                if absent:
                    left = len(bases) - len(absent)
                    tag = "  <- forms no pair" if left < 2 else ""
                    print(f"  {group:<18} not live on {v:<8}: {absent}{tag}")

    print(f"fetching {len(all_syms)} symbols across {venues} "
          f"({cfg.lookback_bars} bars each; this takes a couple minutes) ...")
    panel = fetch_panel(broker, all_syms, cfg)
    if panel.empty:
        print("no data panel — aborting.")
        return 1

    available = set(panel.columns)
    missing = sorted(s for s in all_syms if s not in available)
    print(f"\navailable: {len(available)}/{len(all_syms)}")
    print(f"dropped (no data): {missing}")

    # Pairs are formed WITHIN a driver and WITHIN a venue. Cross-driver pairs
    # have no economic prior; cross-venue pairs of DIFFERENT underlyings add
    # execution risk (two venues, two fills) without adding economic content,
    # so they are deliberately not formed.
    groups: dict[str, set[tuple[str, str]]] = {}
    for name, bases in SECTOR_GROUPS.items():
        for v in venues:
            syms = sorted(_sym(b, v) for b in bases if _sym(b, v) in available)
            if len(syms) >= 2:
                groups.setdefault(f"{name}@{v}", set()).update(
                    combinations(syms, 2))

    # The exception, and it is a real one: the SAME underlying on two venues.
    # One asset, priced twice -- the purest cointegration available anywhere in
    # this universe, and for exactly that reason the spread is only venue basis
    # and may not clear the toll. See `_cost_z`.
    if len(venues) >= 2 and not args.no_cross_venue:
        cross: set[tuple[str, str]] = set()
        for b in all_bases:
            syms = sorted(_sym(b, v) for v in venues if _sym(b, v) in available)
            cross.update(combinations(syms, 2))
        if cross:
            groups["cross_venue"] = cross
            print(f"\ncross-venue: {len(cross)} same-underlying pairs "
                  f"(purest cointegration here; watch cost_z, not adf_p)")

    pairs: set[tuple[str, str]] = set()
    for g in groups.values():
        pairs |= g
    pairs_list = sorted(pairs)

    expanded = select_pairs(panel, candidates=pairs_list, cfg=sel)
    n_expanded = _report(expanded, f"EXPANDED universe ({len(pairs_list)} "
                                    f"sector pairs, FDR across all)")

    # apples-to-apples: the live book, scored on the same panel. Any pair that
    # cannot be scored is NAMED -- a comparison that quietly shrinks its own
    # denominator reads as evidence about the market when it is evidence about
    # the fetch list.
    current, missing_pairs = [], []
    for a, b in CANDIDATES:
        if a in available and b in available:
            current.append((a, b))
        else:
            missing_pairs.append(f"{_base(a)}/{_base(b)}")
    if missing_pairs:
        print(f"\n** {len(missing_pairs)} of {len(CANDIDATES)} live candidate "
              f"pairs EXCLUDED for missing data: {missing_pairs}\n"
              f"   The CURRENT result below is NOT the whole book. **")
    cur_table = select_pairs(panel, candidates=current, cfg=sel)
    n_current = _report(cur_table, f"CURRENT universe ({len(current)} of "
                                   f"{len(CANDIDATES)} live pairs)")

    print("\n" + "=" * 60)
    print("ORIENTATION SENSITIVITY (Engle-Granger is not symmetric)")
    print("=" * 60)
    compare_orientations(panel, pairs_list, sel)

    # The whole point of the 09-11 expansion: did anything OUTSIDE crypto's
    # single factor pass? A breadth result driven entirely by crypto is the
    # 09-09 finding again, and should not be read as a new one.
    nc_bases = {b for g in NON_CRYPTO for b in SECTOR_GROUPS.get(g, [])}
    print("\n" + "=" * 60)
    print("NON-CRYPTO — every pair, with the gate that rejected it")
    print("=" * 60)
    _report_group(expanded, nc_bases, "outside crypto's single factor")

    # cost_z for the rows worth costing: the non-crypto set and anything that
    # actually passed. A pair that cointegrates and cannot pay the toll is a
    # different result from one that does neither, and the scan said nothing
    # about the difference until now.
    interesting = [(r.a, r.b) for _, r in expanded.iterrows()
                   if r.passed or (_base(r.a) in nc_bases
                                   and _base(r.b) in nc_bases)]
    cross_pairs = groups.get("cross_venue", set())
    interesting += [ab for ab in sorted(cross_pairs)][:12]
    if interesting:
        print("\n   cost_z = round-trip cost in units of the spread's own "
              "sigma.\n   Above ~1 there is no edge left to capture after "
              "fees, whatever\n   the statistics say.")
        for a, b in dict.fromkeys(interesting):
            cz = _cost_z(panel, a, b, cfg)
            venue_tag = "" if a.split("_")[0] == b.split("_")[0] else "  [cross-venue]"
            print(f"   {_base(a)}/{_base(b):<9} cost_z="
                  f"{'n/a' if cz is None else f'{cz:6.3f}'}{venue_tag}")
    print(f"\n   agent half-life band: {cfg.min_half_life:.0f}h to "
          f"{cfg.max_half_life:.0f}h. A commodity or equity spread rejected "
          f"for being SLOW\n   is a statement about that band, which was set "
          f"for hourly crypto, not about\n   whether the relationship exists.")

    _stratified_diagnostic(panel, groups, sel, n_expanded)

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
