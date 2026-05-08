from datetime import datetime

from pydantic import BaseModel


class PlatformPublishStatus(BaseModel):
    platform_id: int
    platform_name: str
    status: str
    preview_url: str | None = None
    wp_post_id: int | None = None
    error_msg: str | None = None


class RecordItemOut(BaseModel):
    source_record_id: int
    publish_item_id: int | None = None
    original_id: str
    fetched_at: datetime
    thumbnail_url: str | None
    original_title: str
    original_body: str
    is_adopted: str
    adoption_reason: str
    industry_category: str | None
    edited_article: str | None
    news_brief: str | None
    headline_1: str | None
    headline_2: str | None
    headline_3: str | None
    publish_status: str
    platform_statuses: list[PlatformPublishStatus]

