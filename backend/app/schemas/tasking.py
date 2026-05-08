from datetime import datetime

from pydantic import BaseModel


class TaskCreate(BaseModel):
    name: str
    mode: str = "manual"
    cron_expr: str | None = None
    publish_interval_hours: int | None = None
    is_test_space: bool = False


class TaskUpdate(BaseModel):
    name: str | None = None
    mode: str | None = None
    cron_expr: str | None = None
    publish_interval_hours: int | None = None
    is_test_space: bool | None = None
    status: str | None = None


class TaskOut(BaseModel):
    id: int
    name: str
    mode: str
    cron_expr: str | None
    publish_interval_hours: int | None
    is_test_space: bool
    status: str

    model_config = {"from_attributes": True}


class RunTestRequest(BaseModel):
    task_id: int
    start_time: datetime
    end_time: datetime


class RunTestResponse(BaseModel):
    task_id: int
    batch_id: int
    batch_uuid: str
    status: str


class BatchPublishRequest(BaseModel):
    task_id: int
    batch_id: int


class SelectedPublishRequest(BaseModel):
    task_id: int
    batch_id: int
    publish_item_ids: list[int]


class PublishItemRequest(BaseModel):
    publish_item_id: int

