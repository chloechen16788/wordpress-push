from datetime import datetime
from typing import Any

from pydantic import BaseModel


class APIMessage(BaseModel):
    message: str


class BatchSummary(BaseModel):
    id: int
    task_id: int
    batch_uuid: str
    trigger_type: str
    status: str
    raw_count: int
    rewritten_count: int
    published_count: int
    cvr: float
    start_time: datetime | None
    end_time: datetime | None
    created_at: datetime


class StreamEvent(BaseModel):
    event: str
    data: dict[str, Any]

