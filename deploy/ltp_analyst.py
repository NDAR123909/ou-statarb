"""
Reasoning-depth layer: the organizer LLM as analyst, never as trader.

Track A's rules promise a deep audit of AI Reasoning Logs for "logical depth
of sentiment analysis, market anomaly detection, and strategy adaptation."
`ltp_news.py` already covers sentiment. This module covers the other two,
keeping the division of labor that makes the strategy testable:

    THE MATH DECIDES TRADES. THE LLM ANALYSES, AND MAY ONLY SAY NO.

Two analyses, both written to the decision ledger so every AI call is
timestamped next to the quantitative state that prompted it and the order (or
non-order) that followed:

  - `assess_spread`  MARKET ANOMALY DETECTION. Once per bar per active pair,
    the model reads the spread's live state (z path, band geometry, fitted
    half-life, hedge ratio, news verdicts) and judges whether the behaviour
    looks like ordinary mean reversion, stress, or a structural break. A
    "broken" verdict VETOES an entry — risk-reducing only, exactly like the
    news veto. It can never open, size up, or re-enter anything.
  - `review_refit`   STRATEGY ADAPTATION. Once per refit (daily), the model
    reviews which pairs passed the statistical gates, why the rest were
    rejected, and what changed since the last refit. Purely advisory: it is
    logged as the agent's own account of how its tradeable universe is
    adapting, and never edits the selection.

Budget discipline: the competition allocates USD 10 of tokens per day, which
does not roll over. Analyses are sized to genuine need (a few hundred tokens
of context, a short structured verdict), not inflated for appearance — burning
budget for show would be both dishonest and self-defeating, since exhausting
the allocation would blind the sentinel for the rest of the day. `spend_today`
reads the gateway's own /key/info meter and the analyst stops making calls
above `max_daily_spend`, leaving headroom.

Everything fails open: no key, no SDK, a bad response, or an exhausted budget
degrades to "no analysis, no veto", and the systematic strategy runs on.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

from deploy.ltp_news import organizer_client, model_name

try:
    import requests
except ImportError:
    requests = None


ANOMALY_SYSTEM = """\
You are the market-anomaly analyst for a systematic Ornstein-Uhlenbeck pairs-
trading agent. The agent trades mean reversion of a cointegrated spread
between two crypto perpetual futures. You do NOT choose trades: a
cost-aware statistical model does that. Your job is to judge whether the
spread's CURRENT behaviour is consistent with the mean-reverting process the
model assumes, or whether something has changed.

Mean reversion's fatal mode is a structural break: the spread stops being a
spring and starts being a trend, because the economic link between the two
assets has changed. Distinguish that from ordinary stretch, which is what the
strategy exists to trade.

Classify the regime:
- "normal": the spread is behaving like a mean-reverting process. Being far
  from the mean is NORMAL and is the strategy's entry signal, not an anomaly.
- "stressed": elevated volatility, unusually fast divergence, or a z path that
  is accelerating away rather than oscillating. Tradeable but worth flagging.
- "broken": positive evidence that the relationship itself has changed — the
  spread has trended monotonically for many bars with no oscillation, has blown
  far beyond its historical range, or news indicates a structural event in one
  leg. This VETOES an entry, so reserve it for genuine evidence.

Be conservative with "broken": false alarms forfeit the strategy's edge. A
large |z| by itself is NOT broken — it is the entry signal."""

ADAPTATION_SYSTEM = """\
You are the strategy-adaptation analyst for a systematic crypto pairs-trading
agent. Each day the agent re-runs pair selection: Engle-Granger cointegration
with a Benjamini-Hochberg false-discovery correction across every pair tested,
split-half stability of both the cointegration and the hedge ratio, a Hurst
anti-persistence cap, a half-life band, and a mean-crossing density floor.
Pairs that survive get cost-aware entry/exit bands from OU first-passage times.

You do NOT change the selection or the thresholds, and you must never suggest
loosening a statistical gate to obtain more trades — manufacturing pairs that
are not genuinely cointegrated is the false-discovery failure this pipeline
exists to prevent. Your job is to give an honest reading of what the day's
selection says about the market and the agent's opportunity set: what survived
and why it plausibly holds economically, what the rejection pattern implies
about the current regime, and which risks the tradeable set now carries."""


def _extract_json(text: str) -> dict | None:
    """Parse a JSON object out of model text. The MiniMax gateway is
    Anthropic-compatible only at the messages level and will not honour
    output_config, so the shape is requested in the prompt and dug out here."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    i, j = text.find("{"), text.rfind("}")
    if 0 <= i < j:
        try:
            return json.loads(text[i:j + 1])
        except json.JSONDecodeError:
            pass
    return None


@dataclass
class StrategyAnalyst:
    """LLM analysis of spread regime and selection adaptation, for the log."""

    max_daily_spend: float = 8.0     # of the USD 10/day allocation
    spend_ttl: float = 300.0         # seconds; the meter needn't be re-read
                                     # once per assessment (~73 HTTP calls/day)
    _spend: float | None = field(default=None, repr=False)
    _spend_at: float = field(default=0.0, repr=False)
    last_error: str = ""

    # ------------------------------------------------------------- budget --
    def spend_today(self) -> float | None:
        """USD spent on the organizer gateway today, or None if unreadable.
        The gateway exposes /key/info with a `spend` field (organizer Q&A,
        2026-07)."""
        if (self._spend is not None
                and time.monotonic() - self._spend_at < self.spend_ttl):
            return self._spend
        base = os.environ.get("LTP_AI_BASE_URL")
        key = os.environ.get("LTP_AI_API_KEY")
        if not (base and key and requests is not None):
            return None
        for headers in ({"x-api-key": key},
                        {"Authorization": f"Bearer {key}"}):
            try:
                r = requests.get(f"{base.rstrip('/')}/key/info",
                                 headers=headers, timeout=10)
                if r.status_code != 200:
                    continue
                body = r.json()
                for node in (body, body.get("data") or {}):
                    if isinstance(node, dict) and node.get("spend") is not None:
                        self._spend = float(node["spend"])
                        self._spend_at = time.monotonic()
                        return self._spend
            except (requests.RequestException, ValueError, TypeError):
                continue
        return None

    def within_budget(self) -> bool:
        """Never spend the sentinel out of a working day. Unreadable meter ->
        proceed (the organizer caps the allocation regardless)."""
        spend = self.spend_today()
        return True if spend is None else spend < self.max_daily_spend

    # ---------------------------------------------------------------- call --
    def _ask(self, system: str, prompt: str, max_tokens: int) -> dict:
        client = organizer_client()
        if client is None:
            return {}
        try:
            response = client.messages.create(
                model=model_name(), max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": prompt}])
        except Exception as exc:                  # never break the trade loop
            self.last_error = str(exc)[:200]
            return {}
        if getattr(response, "stop_reason", None) == "refusal":
            return {}
        text = next((b.text for b in response.content
                     if getattr(b, "type", None) == "text"), "")
        parsed = _extract_json(text)
        return parsed if isinstance(parsed, dict) else {}

    # ------------------------------------------- market anomaly detection --
    def assess_spread(self, pair: str, z: float, entry_z: float, exit_z: float,
                      stop_z: float, half_life: float, beta: float,
                      z_path: list[float], news_note: str,
                      holding: bool) -> dict:
        """Regime verdict for one pair on one bar. {} if unavailable."""
        if not self.within_budget():
            return {}
        path = ", ".join(f"{v:+.2f}" for v in z_path[-12:]) or f"{z:+.2f}"
        prompt = (
            "Return ONLY a JSON object, no prose or markdown fences, of exactly "
            'this shape: {"regime": "normal|stressed|broken", "anomaly": '
            '"<what stands out, or none>", "confidence": "low|medium|high", '
            '"rationale": "<two sentences of reasoning from the numbers>"}\n\n'
            f"Pair: {pair}\n"
            f"Position: {'holding' if holding else 'flat'}\n"
            f"Current spread z-score: {z:+.2f}\n"
            f"Entry band: +/-{entry_z:.2f}  exit band: +/-{exit_z:.2f}  "
            f"structural-break stop: +/-{stop_z:.2f}\n"
            f"Fitted OU half-life: {half_life:.1f} hours\n"
            f"Hedge ratio (beta): {beta:.3f}\n"
            f"Recent hourly z path (oldest to newest): {path}\n"
            f"{news_note}")
        out = self._ask(ANOMALY_SYSTEM, prompt, max_tokens=512)
        if out.get("regime") not in ("normal", "stressed", "broken"):
            return {}
        return out

    @staticmethod
    def anomaly_veto(assessment: dict) -> str | None:
        """Rationale if the analyst judged the spread structurally broken.
        Risk-reducing only: this can block an entry, never create one."""
        if assessment.get("regime") == "broken":
            return (f"spread regime rated BROKEN "
                    f"({assessment.get('confidence', 'unknown')} confidence): "
                    f"{assessment.get('rationale', 'structural break suspected')}")
        return None

    # ----------------------------------------------- strategy adaptation --
    def review_refit(self, passed: list[dict], rejects: dict,
                     previous: list[str]) -> dict:
        """Daily reading of how the tradeable universe is adapting. {} if
        unavailable. Advisory only — it never edits the selection."""
        if not self.within_budget():
            return {}
        if passed:
            lines = "\n".join(
                f"- {p['pair']}: ADF p={p['adf_p']:.4f}, Hurst={p['hurst']:.2f}, "
                f"half-life={p['half_life']:.0f}h, beta={p['beta']:+.2f}, "
                f"{p['crossings']} mean crossings" for p in passed)
        else:
            lines = "- (none passed this refit; the agent will hold no new risk)"
        prompt = (
            "Return ONLY a JSON object, no prose or markdown fences, of exactly "
            'this shape: {"assessment": "<what the day\'s selection says about '
            'the market regime>", "opportunity_set": "<honest read of the '
            'tradeable set and its economic rationale>", "risks": "<the main '
            'risk carried by this set>", "adaptation": "<how the agent\'s '
            'universe has shifted versus the previous refit>"}\n\n'
            f"Pairs that PASSED every statistical gate today:\n{lines}\n\n"
            f"Rejection reasons across all candidates tested: "
            f"{json.dumps(rejects)}\n"
            f"Previously active pairs: {', '.join(previous) or '(none)'}")
        return self._ask(ADAPTATION_SYSTEM, prompt, max_tokens=1024)
