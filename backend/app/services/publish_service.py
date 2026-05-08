import asyncio
import json
import threading
from collections import defaultdict
from datetime import datetime
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Batch, Platform, PublishItem, PublishLog
from app.services.stream_service import stream_hub
from app.services.wp_clients.cookie_nonce_client import CookieNoncePublisherClient
from app.services.wp_clients.rest_client import RestPublisherClient
from app.utils.security import decrypt_secret

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "能动": ("能动", "nengdong"),
    "财见": ("财见", "caijian"),
    "知消": ("知消", "retailwatch"),
    "旅游": ("旅报", "travel", "gtdaily"),
    "TMT": ("tmt", "全球tmt"),
    "医药": ("医药", "健闻", "mhn"),
    "其他": ("其他",),
}


def _publisher(platform: Platform):
    secret = decrypt_secret(platform.secret_encrypted)
    if platform.auth_type == "cookie_nonce":
        return CookieNoncePublisherClient(
            base_url=platform.site_url,
            username=platform.username,
            password=secret,
        )
    return RestPublisherClient(
        base_url=platform.site_url,
        username=platform.username,
        app_password=secret,
    )


def _guess_platform_category(name: str) -> str | None:
    name_low = name.lower()
    for category, keys in CATEGORY_KEYWORDS.items():
        if any(key.lower() in name_low for key in keys):
            return category
    return None


def _update_batch_stats(db: Session, batch_id: int) -> None:
    batch = db.get(Batch, batch_id)
    if batch is None:
        return
    raw_count = db.scalar(
        select(func.count()).select_from(PublishItem).where(PublishItem.batch_id == batch_id)
    ) or 0
    published_count = db.scalar(
        select(func.count())
        .select_from(PublishItem)
        .where(PublishItem.batch_id == batch_id, PublishItem.status == "published")
    ) or 0
    batch.raw_count = int(raw_count)
    batch.published_count = int(published_count)
    batch.cvr = (published_count / raw_count) if raw_count else 0.0
    db.add(batch)
    db.commit()


async def publish_batch(
    db_factory: Callable[[], Session],
    task_id: int,
    batch_id: int,
    publish_item_ids: list[int] | None = None,
) -> None:
    with db_factory() as db:
        stmt = select(PublishItem.id).where(
            PublishItem.batch_id == batch_id,
            PublishItem.status.in_(["ready_to_publish", "failed"]),
        )
        if publish_item_ids:
            stmt = stmt.where(PublishItem.id.in_(publish_item_ids))
        item_ids = db.scalars(stmt).all()
        platforms = db.scalars(select(Platform).where(Platform.is_active.is_(True))).all()
        platform_specs = [
            {
                "id": p.id,
                "name": p.name,
                "site_url": p.site_url,
                "auth_type": p.auth_type,
                "username": p.username,
                "secret_encrypted": p.secret_encrypted,
            }
            for p in platforms
        ]
        platforms_by_category: dict[str, list[dict]] = defaultdict(list)
        for p in platform_specs:
            category = _guess_platform_category(p["name"])
            if category:
                platforms_by_category[category].append(p)
        total = max(len(item_ids), 1)
        processed = 0

    for item_id in item_ids:
        with db_factory() as db:
            item = db.get(PublishItem, item_id)
            if item is None:
                continue
            item.status = "publishing"
            db.add(item)
            db.commit()

        await stream_hub.publish(
            f"{task_id}:{batch_id}",
            "item_status",
            {"publish_item_id": item_id, "status": "publishing"},
        )

        with db_factory() as db:
            item = db.get(PublishItem, item_id)
            if item is None:
                continue
            ai_result = item.source_record.ai_result
            category = ai_result.industry_category if ai_result else None
            target_platforms = platforms_by_category.get(category or "其他", [])
            if not target_platforms and category != "其他":
                target_platforms = platforms_by_category.get("其他", [])

            if not target_platforms:
                reason = f"未找到与行业标签匹配的平台: {category or '其他'}"
                item.status = "failed"
                item.error_msg = reason
                db.add(item)
                db.commit()
                await stream_hub.publish(
                    f"{task_id}:{batch_id}",
                    "item_status",
                    {"publish_item_id": item_id, "status": "failed"},
                )
                processed += 1
                await stream_hub.publish(
                    f"{task_id}:{batch_id}",
                    "batch_progress",
                    {
                        "batch_id": batch_id,
                        "processed": processed,
                        "total": total,
                        "percent": int((processed / total) * 100),
                    },
                )
                continue

        has_success = False
        last_error: str | None = None
        for platform in target_platforms:
            platform_success = False
            with db_factory() as db:
                item = db.get(PublishItem, item_id)
                if item is None:
                    continue
                source_title = item.source_record.original_title
                source_body = item.source_record.original_body
                source_thumbnail_url = item.source_record.thumbnail_url
                log = PublishLog(
                    publish_item_id=item_id,
                    platform_id=platform["id"],
                    status="sending",
                    started_at=datetime.utcnow(),
                )
                db.add(log)
                db.commit()
                db.refresh(log)

            try:
                publisher = _publisher(
                    Platform(
                        id=platform["id"],
                        name=platform["name"],
                        site_url=platform["site_url"],
                        auth_type=platform["auth_type"],
                        username=platform["username"],
                        secret_encrypted=platform["secret_encrypted"],
                        is_active=True,
                    )
                )
                media_ids: list[int] = []
                featured_media_id: int | None = None
                if source_thumbnail_url:
                    uploaded_media = publisher.upload_media_from_url(source_thumbnail_url)
                    featured_media_id = int(uploaded_media["id"])
                    media_ids.append(featured_media_id)
                post = publisher.create_post(
                    title=source_title,
                    content=source_body,
                    status="draft",
                    featured_media_id=featured_media_id,
                )
                with db_factory() as db:
                    log = db.get(PublishLog, log.id)
                    if log is None:
                        continue
                    log.status = "published"
                    log.wp_post_id = int(post.get("id")) if post.get("id") else None
                    log.wp_media_ids_json = json.dumps(media_ids, ensure_ascii=False) if media_ids else None
                    log.preview_url = post.get("link") or post.get("guid", {}).get("rendered")
                    log.finished_at = datetime.utcnow()
                    db.add(log)
                    db.commit()
                has_success = True
                platform_success = True
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                with db_factory() as db:
                    log = db.get(PublishLog, log.id)
                    if log is not None:
                        log.status = "failed"
                        log.error_msg = str(exc)
                        log.finished_at = datetime.utcnow()
                        db.add(log)
                    db.commit()

            await stream_hub.publish(
                f"{task_id}:{batch_id}",
                "platform_status",
                {
                    "publish_item_id": item_id,
                    "platform_id": platform["id"],
                    "platform_name": platform["name"],
                    "status": "published" if platform_success else "failed",
                },
            )

        with db_factory() as db:
            item_db = db.get(PublishItem, item_id)
            if item_db is not None:
                if has_success:
                    item_db.status = "published"
                    item_db.error_msg = None
                else:
                    item_db.status = "failed"
                    item_db.error_msg = last_error or "全部目标平台发布失败"
                db.add(item_db)
                db.commit()

        processed += 1
        await stream_hub.publish(
            f"{task_id}:{batch_id}",
            "batch_progress",
            {
                "batch_id": batch_id,
                "processed": processed,
                "total": total,
                "percent": int((processed / total) * 100),
            },
        )

    with db_factory() as db:
        batch = db.get(Batch, batch_id)
        if batch is not None:
            batch.status = "completed"
            batch.end_time = datetime.utcnow()
            db.add(batch)
            db.commit()
        _update_batch_stats(db, batch_id)

    await stream_hub.publish(
        f"{task_id}:{batch_id}",
        "batch_done",
        {"batch_id": batch_id, "status": "completed"},
    )


def trigger_publish_task(
    db_factory: Callable[[], Session],
    task_id: int,
    batch_id: int,
    publish_item_ids: list[int] | None = None,
) -> None:
    def runner() -> None:
        asyncio.run(publish_batch(db_factory, task_id, batch_id, publish_item_ids))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()

