"""
News sentinel for the LTP competition agent: LLM-assessed event risk.

Track A of Liquidity Arena scores "reasoning quality and macro sentiment
capture" alongside returns, and this repo's own wishlist has long included
an event filter before entry (corporate actions in equities; hacks,
delistings and regulatory shocks in crypto — the failure mode the z-stop
only limits after the fact). This module is both, with a strict division
of labor that keeps the strategy testable:

    THE MATH DECIDES TRADES. THE LLM ONLY EVER SAYS NO.

Hourly, the sentinel pulls recent items from LTP's news feed, asks Claude
to rate event severity per asset, and caches the verdicts. The agent
consults the cache before entering a pair; a CRITICAL verdict vetoes the
entry (with the rationale written to the decision ledger). The LLM never
originates positions, never sizes anything, and its absence fails open:
no API key, no news, or an API error all degrade to "no veto", so the
systematic strategy runs unfiltered rather than halting.

COMPETITION COMPLIANCE (Track A AI API policy): teams must EXCLUSIVELY use
the organizer-provided AI API — using your own key during the competition is
grounds for immediate disqualification, verified by correlating AI decision
logs with orders. Therefore:

  - LTP_AI_BASE_URL + LTP_AI_API_KEY   organizer AI gateway (preferred always)
  - LTP_COMPETITION_MODE=1             hard-refuses any non-organizer API;
                                       set this for the whole competition
  - ANTHROPIC_API_KEY                  pre-competition development ONLY

Env: LTP_ACCESS_KEY / LTP_SECRET_KEY  (news feed auth, same keys as trading)
     LTP_AI_MODEL / ANTHROPIC_MODEL   (default claude-opus-4-8)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

FEEDS_BASE = os.environ.get("LTP_API_HOST", "https://api.ltp-contest.com")

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "severity": {"type": "string",
                                 "enum": ["none", "watch", "critical"]},
                    "rationale": {"type": "string"},
                },
                "required": ["symbol", "severity", "rationale"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["assessments"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """\
You are the event-risk sentinel for a systematic crypto pairs-trading agent.
The strategy trades mean reversion between cointegrated perpetual futures on
hour-scale horizons. Mean reversion's fatal mode is a structural break: an
event that permanently changes one asset's value relative to its partner.

You will receive recent news items and a list of base assets the agent may
trade. For each listed asset, rate the event risk evident in the news:

- "critical": a credible structural event for THIS asset — exchange delisting,
  protocol hack or exploit, insolvency of the issuer/foundation, regulatory
  enforcement action naming it, a depeg, chain halt, or key-person arrest.
  Entering a mean-reversion trade against this would bet on a broken spring.
- "watch": elevated uncertainty (major upgrade in progress, unconfirmed
  rumors from low-credibility accounts, large unlock imminent) that does not
  yet invalidate historical price relationships.
- "none": ordinary price commentary, sponsored content, memes, or news that
  does not bear on this asset's structural value.

Be conservative with "critical": it blocks trades, and false alarms erode the
strategy's edge. Hype, price predictions, and influencer noise are "none".
Rate ONLY the assets in the provided list, every one of them, using exactly
the symbols given."""


def _sign_v2(params: dict, nonce: int, secret: str) -> str:
    s = "&".join(f"{k}={v}" for k, v in sorted(params.items())) + f"&{nonce}"
    return hmac.new(secret.encode(), s.encode(), hashlib.sha256).hexdigest()


def fetch_news(hours: float = 2.0, page_size: int = 40) -> list[dict]:
    """Recent items from the LTP feeds API. Empty list on any failure."""
    key = os.environ.get("LTP_ACCESS_KEY", "")
    secret = os.environ.get("LTP_SECRET_KEY", "")
    if not (key and secret):
        return []
    now_ms = int(time.time() * 1000)
    params = {"startTime": str(now_ms - int(hours * 3_600_000)),
              "endTime": str(now_ms), "page": "1", "pageSize": str(page_size)}
    nonce = int(time.time())
    headers = {"X-MBX-APIKEY": key, "nonce": str(nonce),
               "signature": _sign_v2(params, nonce, secret)}
    try:
        r = requests.get(f"{FEEDS_BASE}/api/v1/feeds/queryNews",
                         params=params, headers=headers, timeout=15)
        body = r.json()
        if body.get("code") != 200:
            return []
        return body.get("data", {}).get("list") or []
    except (requests.RequestException, ValueError):
        return []


@dataclass
class NewsSentinel:
    """Hourly news -> per-asset severity verdicts, consumed by the agent."""

    max_items: int = 30
    verdicts: dict = field(default_factory=dict)   # base asset -> verdict dict
    last_refresh: str = ""

    @staticmethod
    def _client():
        """Organizer AI gateway first; own key only outside competition mode."""
        try:
            import anthropic
        except ImportError:
            return None
        base = os.environ.get("LTP_AI_BASE_URL")
        key = os.environ.get("LTP_AI_API_KEY")
        if base and key:
            return anthropic.Anthropic(base_url=base, api_key=key)
        if os.environ.get("LTP_COMPETITION_MODE"):
            # Using a self-provided AI API during the competition is a
            # disqualification offense. No organizer endpoint configured ->
            # no LLM at all; the sentinel fails open and the math trades on.
            return None
        if os.environ.get("ANTHROPIC_API_KEY"):
            return anthropic.Anthropic()
        return None

    def _classify(self, assets: list[str], items: list[dict]) -> dict:
        client = self._client()
        if client is None:
            return {}
        import anthropic

        digest = []
        for it in items[: self.max_items]:
            syms = ",".join((c.get("symbol") or "") for c in (it.get("currencies") or []))
            digest.append(f"- [{syms or 'general'}] {(it.get('title') or '')[:200]}")
        if not digest:
            return {}

        try:
            response = client.messages.create(
                model=os.environ.get("LTP_AI_MODEL")
                or os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8"),
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                output_config={"format": {"type": "json_schema",
                                          "schema": VERDICT_SCHEMA}},
                messages=[{
                    "role": "user",
                    "content": (f"Assets the agent may trade: {', '.join(assets)}\n\n"
                                f"News from the last two hours:\n" + "\n".join(digest)),
                }],
            )
        except anthropic.RateLimitError:
            return {}
        except anthropic.APIStatusError:
            return {}
        except anthropic.APIConnectionError:
            return {}
        if response.stop_reason == "refusal":
            return {}
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return {a["symbol"].upper(): a for a in parsed.get("assessments", [])}

    def refresh(self, base_assets: list[str]) -> None:
        """One feeds call + one Claude call; fail-open on any problem."""
        items = fetch_news()
        self.verdicts = self._classify(sorted(set(base_assets)), items) if items else {}
        self.last_refresh = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def veto(self, *base_assets: str) -> str | None:
        """Rationale string if any asset is rated critical, else None."""
        for a in base_assets:
            v = self.verdicts.get(a.upper())
            if v and v.get("severity") == "critical":
                return f"{a}: {v.get('rationale', 'critical news event')}"
        return None

    def size_mult(self, *base_assets: str) -> float:
        """Risk-budget multiplier: 0.5 if any leg is rated 'watch', else 1.0.
        Like the veto, this can only REDUCE risk, never add it."""
        for a in base_assets:
            v = self.verdicts.get(a.upper())
            if v and v.get("severity") == "watch":
                return 0.5
        return 1.0

    def note(self, *base_assets: str) -> str:
        """One-line news context for the reasoning log, always available."""
        if not self.verdicts:
            return "news sentinel: no verdicts (feed empty or LLM unavailable)"
        parts = []
        for a in base_assets:
            v = self.verdicts.get(a.upper())
            parts.append(f"{a}={v['severity'] if v else 'none'}")
        return "news sentinel: " + ", ".join(parts)
