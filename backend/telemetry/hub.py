"""WebSocket fan-out helpers for live dashboard updates."""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class LiveEventHub:
    """Broadcast structured events to subscribed websocket clients."""

    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._channels[channel].add(websocket)

    async def disconnect(self, channel: str, websocket: WebSocket) -> None:
        async with self._lock:
            if channel in self._channels:
                self._channels[channel].discard(websocket)

    async def broadcast(self, channel: str, payload: dict[str, Any]) -> None:
        message = json.dumps(payload)
        async with self._lock:
            recipients = list(self._channels.get(channel, set()))

        dead: list[WebSocket] = []
        for websocket in recipients:
            try:
                await websocket.send_text(message)
            except Exception:
                dead.append(websocket)

        if dead:
            async with self._lock:
                for websocket in dead:
                    self._channels[channel].discard(websocket)
