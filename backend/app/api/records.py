from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models import Platform, PublishLog, PublishItem, SourceRecord
from app.schemas.records import PlatformPublishStatus, RecordItemOut

router = APIRouter(prefix="/api", tags=["records"])


@router.get("/batches/{batch_id}/records", response_model=list[RecordItemOut])
def list_batch_records(
    batch_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[RecordItemOut]:
    source_rows = db.scalars(
        select(SourceRecord)
        .options(joinedload(SourceRecord.ai_result), joinedload(SourceRecord.publish_item))
        .where(SourceRecord.batch_id == batch_id)
        .order_by(SourceRecord.id.desc())
    ).all()
    logs = db.scalars(
        select(PublishLog)
        .join(PublishItem, PublishItem.id == PublishLog.publish_item_id)
        .where(PublishItem.batch_id == batch_id)
    ).all()
    platforms = {p.id: p.name for p in db.scalars(select(Platform)).all()}

    by_item_id: dict[int, list[PublishLog]] = {}
    for log in logs:
        by_item_id.setdefault(log.publish_item_id, []).append(log)

    out: list[RecordItemOut] = []
    for row in source_rows:
        ai = row.ai_result
        publish = row.publish_item
        publish_status = publish.status if publish else "unknown"
        if status and publish_status != status:
            continue
        status_rows = []
        if publish is not None:
            for log in by_item_id.get(publish.id, []):
                status_rows.append(
                    PlatformPublishStatus(
                        platform_id=log.platform_id,
                        platform_name=platforms.get(log.platform_id, f"platform-{log.platform_id}"),
                        status=log.status,
                        preview_url=log.preview_url,
                        wp_post_id=log.wp_post_id,
                        error_msg=log.error_msg,
                    )
                )

        out.append(
            RecordItemOut(
                source_record_id=row.id,
                publish_item_id=publish.id if publish else None,
                original_id=row.original_id,
                fetched_at=row.fetched_at,
                thumbnail_url=row.thumbnail_url,
                original_title=row.original_title,
                original_body=row.original_body,
                is_adopted=ai.is_adopted if ai else "否",
                adoption_reason=ai.adoption_reason if ai else "",
                industry_category=ai.industry_category if ai else None,
                edited_article=ai.edited_article if ai else None,
                news_brief=ai.news_brief if ai else None,
                headline_1=ai.headline_1 if ai else None,
                headline_2=ai.headline_2 if ai else None,
                headline_3=ai.headline_3 if ai else None,
                publish_status=publish_status,
                platform_statuses=status_rows,
            )
        )
    return out

