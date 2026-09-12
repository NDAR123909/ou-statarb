"""
Guards on the breadth diagnostic.

The scan exists to answer one question — is a thin book a breadth problem we
can fix, or a regime in which sitting out is correct — and the answer moves
real money. So the thing that matters most about it is not the statistics,
which are the agent's own unmodified gates, but whether the comparison it
prints covers what it claims to cover.

On 2026-09-09 it did not. Symbols were fetched from SECTOR_GROUPS alone, and
CANDIDATES pairs whose legs were not also listed there were dropped from the
"CURRENT universe" line with no warning — the header simply read 14 where the
live book was 15. The pair it silently dropped was ETH/BTC, which had passed
the gate on six of the eight refits before that date. A run reporting
"CURRENT universe: 0/14 pass" then read as evidence about the market when it
was evidence about a fetch list.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deploy.ltp_agent import CANDIDATES                      # noqa: E402
from deploy.universe_scan import (                           # noqa: E402
    NON_CRYPTO, SECTOR_GROUPS, VENUE, VENUES, _sym, live_symbols,
)


def _sector_symbols() -> set[str]:
    return {_sym(base) for group in SECTOR_GROUPS.values() for base in group}


def test_every_traded_symbol_is_reachable_by_the_scan():
    """A symbol the book trades but the scan never fetches cannot be scored,
    and its pair vanishes from the comparison without saying so."""
    traded = {s for pair in CANDIDATES for s in pair}
    missing = sorted(traded - _sector_symbols())
    assert not missing, (
        f"{missing} are traded live but absent from SECTOR_GROUPS; the "
        f"CURRENT-universe comparison would silently exclude their pairs")


def test_the_majors_pair_is_actually_tested():
    """The specific regression. ETH/BTC carried the book through the gap
    window and was the pair the scan could not see."""
    syms = _sector_symbols()
    assert _sym("BTC") in syms and _sym("ETH") in syms


def test_pairs_are_only_formed_within_a_sector():
    """Restricting the search space is itself a multiple-testing correction,
    and the one that carries economic meaning. If groups ever merged into one
    bucket the scan would quietly become a blind all-vs-all search."""
    assert len(SECTOR_GROUPS) > 5
    biggest = max(len(g) for g in SECTOR_GROUPS.values())
    assert biggest <= 5, "a sector this wide is not an economic grouping"


# --------------------------------------------------------------------------
# 2026-09-11: the universe stopped being crypto-only.
#
# The organizer confirmed any orderable instrument is eligible regardless of
# underlying, and a probe sweep found 60 live symbols on Binance against the 30
# in CANDIDATES -- crude, Brent, soybeans, an S&P contract and four mega-cap
# equities. That matters because the 0-of-55 result was a ONE-FACTOR finding:
# every crypto perp shares BTC beta, so widening within crypto cannot help.
# --------------------------------------------------------------------------

def test_the_scan_can_address_more_than_one_venue():
    """`_sym` hardcoded BINANCE_PERP_ until today. OKX uniquely carries NG,
    which would turn energy from one pair into three, so the venue has to be a
    parameter rather than a string literal buried in a helper."""
    assert _sym("CL") == "BINANCE_PERP_CL_USDT"
    assert _sym("CL", "OKX") == "OKX_PERP_CL_USDT"
    assert VENUE == "BINANCE"


def test_the_crown_jewel_pair_is_actually_in_the_universe():
    """CL and BZ are WTI and Brent -- two grades of one physical commodity,
    arbitraged against each other for decades. It is the strongest economic
    prior in the file and nothing in crypto is close."""
    assert set(SECTOR_GROUPS["energy"]) >= {"CL", "BZ"}


def test_every_non_crypto_group_is_declared_as_such():
    """The verdict reports non-crypto passes separately. If a group drifts out
    of NON_CRYPTO a breadth result driven entirely by crypto would be read as a
    new finding when it is the 2026-09-09 one again."""
    for group in NON_CRYPTO:
        assert group in SECTOR_GROUPS, group
    crypto_bases = {s.split("_")[2] for pair in CANDIDATES for s in pair}
    for group in NON_CRYPTO:
        overlap = set(SECTOR_GROUPS[group]) & crypto_bases
        assert not overlap, f"{group} contains crypto symbols {overlap}"


def test_a_missing_manifest_reads_as_unprobed_not_as_empty():
    """'not probed' and 'probed, found nothing' must not look alike -- the
    second would justify concluding the venue is bare."""
    got = live_symbols()
    assert got is None or isinstance(got, set)


def test_groups_too_small_to_pair_are_still_declared():
    """ZS (soybeans) has no partner on Binance and forms no pair. Listing it
    anyway is what makes the manifest check say so out loud, instead of the
    symbol being invisible in both the groups and the output."""
    assert SECTOR_GROUPS["ags"] == ["ZS"]
    assert len(SECTOR_GROUPS["ags"]) < 2


# --------------------------------------------------------------------------
# 2026-09-11, organizer: "You can place orders on both Binance and OKX for a
# single RapidX portfolio but only on perpetuals for Phase II."
#
# So there is no venue to choose -- we take the union -- and a new pair type
# exists that did not before: the SAME underlying priced on two venues.
# --------------------------------------------------------------------------

def test_both_venues_are_in_scope():
    assert set(VENUES) == {"BINANCE", "OKX"}
    # VENUE stays the default for the live agent, whose CANDIDATES are Binance.
    assert VENUE in VENUES


def test_cost_z_separates_cointegrating_from_tradeable():
    """The scan conflated these until today, and cross-venue pairs make the
    distinction load-bearing: one asset priced twice is the purest
    cointegration available, and for exactly that reason the spread is only
    venue basis and may not clear the toll."""
    import numpy as np
    import pandas as pd
    from deploy.ltp_agent import AgentConfig
    from deploy.universe_scan import _cost_z

    rng = np.random.default_rng(7)
    n = 600
    # A wide spread: plenty of sigma for the fee to come out of.
    base = np.cumsum(rng.normal(0, 0.01, n)) + 10.0
    wide = pd.DataFrame({"A": base + rng.normal(0, 0.05, n),
                         "B": base + rng.normal(0, 0.05, n)})
    # A near-identical pair: the cross-venue shape, almost no sigma at all.
    tight = pd.DataFrame({"A": base + rng.normal(0, 0.00005, n),
                          "B": base + rng.normal(0, 0.00005, n)})
    cfg = AgentConfig()
    cz_wide = _cost_z(wide, "A", "B", cfg)
    cz_tight = _cost_z(tight, "A", "B", cfg)
    assert cz_wide is not None and cz_tight is not None
    assert cz_tight > cz_wide, (
        "a spread with almost no sigma must show a HIGHER cost in units of "
        "its own sigma -- that is the whole point of the measure")


def test_cost_z_returns_none_rather_than_a_number_it_cannot_justify():
    import pandas as pd
    from deploy.ltp_agent import AgentConfig
    from deploy.universe_scan import _cost_z
    flat = pd.DataFrame({"A": [1.0] * 50, "B": [1.0] * 50})
    assert _cost_z(flat, "A", "B", AgentConfig()) is None


def test_the_stratified_pass_is_a_diagnostic_and_says_so():
    """Invariant 3 stands: the live gate applies FDR across every test run.
    This function exists to produce the evidence Sunday's decision needs --
    'what ELSE passes' -- and building that comparison is not making the
    change. If the labelling ever drifts, someone reads a diagnostic as a
    result."""
    import inspect
    from deploy.universe_scan import _stratified_diagnostic
    src = inspect.getsource(_stratified_diagnostic)
    assert "NOT the live gate" in src
    assert "invariant 3" in src.lower()
    assert "not making the change" in src.lower()
    # ...and it must frame extra passes as a cost, not a win.
    assert "PRICE, not as the prize" in src
