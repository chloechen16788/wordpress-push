import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.services.stream_service import stream_hub

router = APIRouter(prefix="/api", tags=["stream"])


@router.get("/stream")
async def stream_events(task_id: int, batch_id: int) -> StreamingResponse:
    settings = get_settings()
    key = f"{task_id}:{batch_id}"

    async def event_generator():
        async for message in stream_hub.subscribe(key):
            yield message
            await asyncio.sleep(0)
        # keepalive for compatibility if no events (unlikely due stream close)
        while True:
            yield "event: keepalive\ndata: {}\n\n"
            await asyncio.sleep(settings.stream_keepalive_seconds)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

