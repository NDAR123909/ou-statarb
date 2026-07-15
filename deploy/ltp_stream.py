"""
Streaming news listener: sub-minute de-risking for the LTP agent.

Speed is a scored dimension of Track A ("AI's speed in interpreting
unstructured data and converting it into trading signals"), and the hourly
sentinel poll leaves up to an hour between a structural event and the agent
noticing. This listener holds LTP's public news WebSocket open in a
background thread; when an item names an asset the agent is ACTIVELY
trading, it fires the LLM assessment immediately. A critical verdict raises
the urgent flag, the agent wakes from its inter-bar sleep, and affected
positions are flattened within seconds of the headline.

Same invariant as everything else the LLM touches: risk-reducing only.
The stream can flatten or block; it can never open, add, or size up.
And it fails open at every layer — no websockets library, a dropped
connection, or a classification failure all degrade to the hourly poll.

The WebSocket endpoint is public (no credentials), so this whole path is
testable before the competition keys arrive. Protocol per LTP docs:
subscribe to news.category.all, ping every 20s ({"ping": ms}), 90s server
timeout, subscriptions do not survive reconnects.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque

FEEDS_WS = "wss://feeds.ltp-contest.com/feeds/v2/public"
CHANNELS = ["news.category.all", "news.hot.all"]
HEARTBEAT_S = 20.0


class NewsStream:
    """Background WS consumer -> immediate sentinel verdicts + urgent flag."""

    def __init__(self, sentinel, active_assets_fn, url: str = FEEDS_WS):
        self.sentinel = sentinel
        self.active_assets_fn = active_assets_fn   # () -> list[str] of base assets
        self.url = url
        self.urgent = threading.Event()
        self._critical: set[str] = set()
        self._lock = threading.Lock()
        self._seen: deque = deque(maxlen=500)
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------- pure logic --
    def handle_item(self, item: dict) -> set[str]:
        """Process one news item. Returns assets newly rated critical.

        Kept free of any socket so the whole decision path is testable:
        dedupe -> relevance prefilter -> targeted LLM call -> verdict merge
        -> urgency signal.
        """
        news_id = item.get("newsId") or item.get("id")
        if news_id in self._seen:
            return set()
        self._seen.append(news_id)

        active = {a.upper() for a in self.active_assets_fn()}
        if not active:
            return set()

        mentioned = {(c.get("symbol") or "").upper()
                     for c in (item.get("currencies") or [])}
        title = (item.get("title") or "").upper()
        # currencies metadata first; word-boundary-ish title match as backup
        relevant = (mentioned & active) | {
            a for a in active
            if len(a) >= 3 and f" {a} " in f" {title.replace(':', ' ').replace(',', ' ')} "
        }
        if not relevant:
            return set()

        verdicts = self.sentinel._classify(sorted(relevant), [item])
        if not verdicts:
            return set()
        self.sentinel.verdicts.update(verdicts)

        criticals = {a for a, v in verdicts.items()
                     if v.get("severity") == "critical"}
        if criticals:
            with self._lock:
                self._critical |= criticals
            self.urgent.set()
        return criticals

    def take_critical(self) -> set[str]:
        """Pop the pending critical set (called by the agent on wake)."""
        with self._lock:
            crit, self._critical = self._critical, set()
        return crit

    # --------------------------------------------------------------- transport --
    def start(self) -> bool:
        """Spawn the listener thread. False (and no thread) if unavailable."""
        try:
            import websockets  # noqa: F401
        except ImportError:
            return False
        self._thread = threading.Thread(target=self._thread_main, daemon=True,
                                        name="ltp-news-stream")
        self._thread.start()
        return True

    def _thread_main(self) -> None:
        import asyncio
        asyncio.run(self._run())

    async def _run(self) -> None:
        import asyncio
        import websockets

        delay = 1.0
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    delay = 1.0
                    await ws.send(json.dumps(
                        {"event": "subscribe",
                         "arg": [{"channel": c} for c in CHANNELS]}))

                    async def heartbeat():
                        while True:
                            await asyncio.sleep(HEARTBEAT_S)
                            await ws.send(json.dumps(
                                {"ping": int(time.time() * 1000)}))

                    hb = asyncio.create_task(heartbeat())
                    try:
                        async for raw in ws:
                            try:
                                msg = json.loads(raw)
                            except json.JSONDecodeError:
                                continue
                            if "pong" in msg or msg.get("event"):
                                continue
                            data = msg.get("data")
                            if isinstance(data, dict):
                                # classification blocks; fine on this thread
                                self.handle_item(data)
                    finally:
                        hb.cancel()
            except Exception:
                # any transport failure: back off and reconnect; the hourly
                # poll remains the floor, so silence here is safe
                pass
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60.0)
