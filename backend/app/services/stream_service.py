import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class StreamMessage:
    event: str
    data: dict


class StreamHub:
    """Broadcast progress events to SSE subscribers."""

    def __init__(self) -> None:
        self._listeners: dict[str, set[asyncio.Queue[StreamMessage]]] = defaultdict(set)

    async def publish(self, key: str, event: str, data: dict) -> None:
        queues = list(self._listeners.get(key, set()))
        for queue in queues:
            await queue.put(StreamMessage(event=event, data=data))

    async def subscribe(self, key: str) -> AsyncIterator[str]:
        queue: asyncio.Queue[StreamMessage] = asyncio.Queue()
        self._listeners[key].add(queue)
        try:
            while True:
                msg = await queue.get()
                payload = json.dumps(msg.data, ensure_ascii=False)
                yield f"event: {msg.event}\ndata: {payload}\n\n"
        finally:
            self._listeners[key].discard(queue)
            if not self._listeners[key]:
                self._listeners.pop(key, None)


stream_hub = StreamHub()

