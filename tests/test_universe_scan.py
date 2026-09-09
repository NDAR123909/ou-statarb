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
from deploy.universe_scan import SECTOR_GROUPS, _sym         # noqa: E402


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
