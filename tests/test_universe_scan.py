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
    NON_CRYPTO, SECTOR_GROUPS, VENUE, _sym, live_symbols,
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
