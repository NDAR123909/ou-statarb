"""
Each pair is tested on its own history, not on the history every symbol shares.

`fetch_panel` used to end in an inner join across every fetched symbol, so one
young, gappy or market-hours symbol shortened the data for EVERY pair. Task 07
(2026-09-30) caught it: the same pair, same orientation, same day read 80 mean
crossings and ADF p 7.7e-05 on the live 30-symbol panel, and 38 crossings and
p 0.0158 on the universe scan's 112-symbol panel. So any widening of
`CANDIDATES` would have weakened the evidence for the pair already traded, on
top of the FDR price -- a cost recorded nowhere.

This changes what the live gate sees, so the first test here is the one that
matters most: on a COMPLETE panel -- which is what the live 30-symbol refit is
believed to be -- the new gate returns exactly the old gate's table. The change
may only differ where the old behaviour was the defect.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import deploy.ltp_agent as agent                          # noqa: E402
from deploy.ltp_agent import (                            # noqa: E402
    AgentConfig, orient, pair_frame, panel_summary, selection_config,
)
from statarb.selection import SelectionConfig, select_pairs  # noqa: E402

A, B = "BINANCE_PERP_1000SHIB_USDT", "BINANCE_PERP_DOGE_USDT"
GAPPY = "OKX_PERP_TSLA_USDT"


def _logs(n=960, seed=3):
    """A cointegrated pair (~15-bar half-life) plus a random-walk third leg."""
    rng = np.random.default_rng(seed)
    phi = np.exp(-np.log(2) / 15.0)
    ou = np.zeros(n)
    for t in range(1, n):
        ou[t] = phi * ou[t - 1] + rng.normal(0, 0.01)
    lb = np.log(0.098) + np.cumsum(rng.normal(0, 0.012, n))  # beta identifiable
    return {A: -3.18 + 0.84 * lb + ou, B: lb,
            GAPPY: np.log(250.0) + np.cumsum(rng.normal(0, 0.01, n))}


def _old_config(cfg):
    """The SelectionConfig refit() built before 2026-09-30, verbatim."""
    return SelectionConfig(
        fdr_q=cfg.fdr_q, min_half_life=cfg.min_half_life,
        max_half_life=cfg.max_half_life, periods_per_year=cfg.bars_per_year,
        min_crossings_per_year=8.0 * (cfg.bars_per_year / 252),
        min_abs_beta=cfg.min_abs_beta, max_abs_beta=cfg.max_abs_beta)


def test_on_a_complete_panel_the_new_gate_is_the_old_gate():
    cfg = AgentConfig()
    logp = pd.DataFrame(_logs())
    cands = [orient(logp, A, B), orient(logp, A, GAPPY), orient(logp, B, GAPPY)]
    old = select_pairs(logp, candidates=cands, cfg=_old_config(cfg))
    new = select_pairs(logp, candidates=cands, cfg=selection_config(cfg))
    pd.testing.assert_frame_equal(old, new)
    # ...and the orientation rule agrees with the old whole-panel form.
    for a, b in ((A, B), (A, GAPPY), (B, GAPPY)):
        old_orient = ((a, b) if np.std(np.diff(logp[a].values))
                      >= np.std(np.diff(logp[b].values)) else (b, a))
        assert orient(logp, a, b) == old_orient


def _gappy_panel():
    """The market-hours / newly-listed case: the third symbol has only the
    last 500 of 960 bars. An outer join, as fetch_panel(align='pairwise')
    returns it."""
    logs = _logs()
    frames = {A: pd.Series(logs[A]), B: pd.Series(logs[B]),
              GAPPY: pd.Series(logs[GAPPY][460:], index=range(460, 960))}
    return pd.DataFrame(frames)


def test_a_gappy_third_symbol_no_longer_shortens_the_pair():
    cfg = AgentConfig()
    outer = _gappy_panel()
    ab = orient(outer, A, B)
    # The defect, reproduced: the old all-symbol join halves the pair's data.
    old = select_pairs(outer.dropna(), candidates=[ab], cfg=_old_config(cfg))
    new = select_pairs(outer, candidates=[ab], cfg=selection_config(cfg))
    assert len(outer.dropna()) == 500 and len(pair_frame(outer, A, B)) == 960
    assert new.adf_pvalue[0] < old.adf_pvalue[0]      # more data, more power
    assert new.crossings[0] > old.crossings[0]        # the 80-vs-38 signature


def test_too_short_an_overlap_is_rejected_and_still_counted():
    """A pair without enough shared history is not tested on scraps -- and
    because the test was still run, it stays in the FDR family (invariant 3)
    at p = 1.0 rather than vanishing from the denominator."""
    cfg = AgentConfig()
    outer = _gappy_panel()
    outer[GAPPY] = outer[GAPPY].where(outer.index >= 700)   # 260 bars left
    t = select_pairs(outer, candidates=[orient(outer, A, B), (GAPPY, A)],
                     cfg=selection_config(cfg))
    short = t[t.a == GAPPY].iloc[0]
    assert short.reject_reason == "insufficient overlap"
    assert short.adf_pvalue == 1.0 and not short.passed
    assert len(t) == 2


def test_the_default_config_is_unchanged_for_every_other_caller():
    """The backtests and the reference run call select_pairs with the
    default config; alignment is opt-in, and a NaN still reads as degenerate
    there exactly as before."""
    assert SelectionConfig().align_pairs is False
    outer = _gappy_panel()
    t = select_pairs(outer, candidates=[(GAPPY, A)], cfg=SelectionConfig())
    assert t.reject_reason[0] == "degenerate price series"


def test_the_panel_summary_says_what_the_old_join_would_have_kept():
    s = panel_summary(_gappy_panel(), [A, B, GAPPY, "BINANCE_PERP_GONE_USDT"])
    assert s["bars"] == 960 and s["complete_bars"] == 500
    assert s["excluded"] == ["BINANCE_PERP_GONE_USDT"]
    json.dumps(s)


class _KlinesBroker:
    def __init__(self, frames):
        self.frames = frames

    def klines(self, symbol, interval, limit):
        return self.frames[symbol]

    def __getattr__(self, name):
        raise AssertionError(f"refit touched broker.{name}")


def test_refit_end_to_end_with_a_gappy_symbol(tmp_path, monkeypatch):
    """The live path: a CANDIDATES leg with only 500 bars must not cost the
    cointegrated pair half its history, and the refit record must say what it
    saw."""
    ledger = tmp_path / "l.jsonl"
    monkeypatch.setattr(agent, "_LEDGER_PATH", str(ledger))
    rng = np.random.default_rng(11)
    syms = sorted({s for p in agent.CANDIDATES for s in p})
    logs = {s: np.log(10.0) + np.cumsum(rng.normal(0, 0.01, 960)) for s in syms}
    base = _logs()
    logs[A], logs[B] = base[A], base[B]
    frames = {s: pd.DataFrame({"close": np.exp(v)}) for s, v in logs.items()}
    gappy = "BINANCE_PERP_XAUT_USDT"
    frames[gappy] = frames[gappy].iloc[460:]                 # 500 bars only
    cfg = AgentConfig(state_path=str(tmp_path / "s.json"),
                      hwm_path=str(tmp_path / "h.json"))
    state = {"peak_equity": 1000.0, "halted": False, "pairs": {}, "bar": 0}

    agent.refit(_KlinesBroker(frames), cfg, state)
    rec = [json.loads(l) for l in ledger.read_text().splitlines()
           if '"event": "refit"' in l][0]
    assert rec["panel"]["bars"] == 960 and rec["panel"]["complete_bars"] == 500
    shib = next(c for c in rec["candidates"] if "1000SHIB" in c["pair"])
    assert shib["bars"] == 960 and shib["passed"]
    xaut = next(c for c in rec["candidates"] if "XAUT" in c["pair"])
    assert xaut["bars"] == 500
