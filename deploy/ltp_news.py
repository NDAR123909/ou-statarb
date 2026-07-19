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

try:
    import requests
except ImportError:      # the news sentinel is optional infrastructure; with
    requests = None      # no requests it fetches nothing and the math trades on

FEEDS_BASE = os.environ.get("LTP_API_HOST", "https://api.ltp-contest.com")

# The verdict contract, kept as documentation of the shape the prompt asks
# for. Not sent to the API: the MiniMax gateway is Anthropic-compatible only
# at the messages level and won't honor output_config structured outputs, so
# the shape is requested in the prompt and parsed defensively instead.
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


# The two official sources disagree on the V2 string-to-sign: the GitHub docs
# (and their own Python sample) append the nonce as "&"+nonce, while the
# organizer's Telegram clarification of 2026-07 appends it with NO separator
# (worked example: "page=1&pageSize=201723456789"). Rather than bet on either,
# try one, fall back to the other on a signature error (code 1004), and
# remember the winner for the rest of the run.
_sign_sep: bool | None = None


def _sign_v2(params: dict, nonce: int, secret: str, sep: bool) -> str:
    payload = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    s = payload + (f"&{nonce}" if sep else f"{nonce}")
    return hmac.new(secret.encode(), s.encode(), hashlib.sha256).hexdigest()


def _feeds_get(path: str, params: dict, key: str, secret: str) -> dict:
    """Signed GET with signature-variant fallback."""
    global _sign_sep
    body: dict = {}
    variants = [_sign_sep] if _sign_sep is not None else [True, False]
    for sep in variants:
        nonce = int(time.time())
        headers = {"X-MBX-APIKEY": key, "nonce": str(nonce),
                   "signature": _sign_v2(params, nonce, secret, sep)}
        r = requests.get(f"{FEEDS_BASE}{path}", params=params,
                         headers=headers, timeout=15)
        body = r.json()
        if body.get("code") == 200:
            _sign_sep = sep
            return body
        if body.get("code") != 1004:      # not a signature problem
            return body
    return body


def fetch_news(hours: float = 2.0, page_size: int = 40) -> list[dict]:
    """Recent items from the LTP feeds API. Empty list on any failure."""
    if requests is None:                       # dependency absent: fail open
        return []
    key = os.environ.get("LTP_ACCESS_KEY", "")
    secret = os.environ.get("LTP_SECRET_KEY", "")
    if not (key and secret):
        return []
    now_ms = int(time.time() * 1000)
    params = {"startTime": str(now_ms - int(hours * 3_600_000)),
              "endTime": str(now_ms), "page": "1", "pageSize": str(page_size)}
    try:
        body = _feeds_get("/api/v1/feeds/queryNews", params, key, secret)
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
        """Organizer AI gateway first; own key only outside competition mode.

        The gateway (LTP_AI_BASE_URL) serves MiniMax-M3 behind an
        Anthropic-compatible endpoint, so the anthropic SDK drives it with
        only a base_url swap. Its notes require timeout >= 300s and <= 3
        retries on transient errors; both are set here."""
        try:
            import anthropic
        except ImportError:
            return None
        base = os.environ.get("LTP_AI_BASE_URL")
        key = os.environ.get("LTP_AI_API_KEY")
        if base and key:
            return anthropic.Anthropic(base_url=base, api_key=key,
                                       timeout=300.0, max_retries=3)
        if os.environ.get("LTP_COMPETITION_MODE"):
            # Using a self-provided AI API during the competition is a
            # disqualification offense. No organizer endpoint configured ->
            # no LLM at all; the sentinel fails open and the math trades on.
            return None
        if os.environ.get("ANTHROPIC_API_KEY"):
            return anthropic.Anthropic()
        return None

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        """Parse a JSON object out of model text. MiniMax behind a compat
        shim will not honor Anthropic's output_config structured-output
        constraint, so we ask for JSON in the prompt and dig it out here:
        direct parse first, then the outermost {...} span (handles markdown
        fences and any prose the model wraps around it)."""
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

    def _classify(self, assets: list[str], items: list[dict]) -> dict:
        client = self._client()
        if client is None:
            return {}

        digest = []
        for it in items[: self.max_items]:
            syms = ",".join((c.get("symbol") or "") for c in (it.get("currencies") or []))
            digest.append(f"- [{syms or 'general'}] {(it.get('title') or '')[:200]}")
        if not digest:
            return {}

        instruction = (
            "Return ONLY a JSON object, no prose and no markdown fences, of "
            'exactly this shape: {"assessments": [{"symbol": "<one of the '
            'listed assets>", "severity": "none|watch|critical", "rationale": '
            '"<short reason>"}]}. Include every listed asset exactly once.')
        prompt = (f"{instruction}\n\nAssets the agent may trade: "
                  f"{', '.join(assets)}\n\nNews from the last two hours:\n"
                  + "\n".join(digest))

        # The sentinel must never crash the trade loop, and the caller
        # (main) only catches RapidXError, so ANY failure here fails open.
        try:
            response = client.messages.create(
                model=os.environ.get("LTP_AI_MODEL")
                or os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8"),
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            return {}
        if getattr(response, "stop_reason", None) == "refusal":
            return {}
        text = next((b.text for b in response.content
                     if getattr(b, "type", None) == "text"), "")
        parsed = self._extract_json(text)
        if not isinstance(parsed, dict):
            return {}
        out = {}
        for a in parsed.get("assessments", []):
            sym = str(a.get("symbol", "")).upper()
            sev = a.get("severity")
            if sym and sev in ("none", "watch", "critical"):
                out[sym] = a
        return out

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
