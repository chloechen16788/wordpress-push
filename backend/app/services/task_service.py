import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AIResult, Batch, PublishItem, SourceRecord, Task
from app.services.ingest_service import fetch_amp_records
from app.services.llm_service import LLMInput, get_llm_runtime, rewrite_news
from app.services.transform_service import normalize_content


def _parse_amp_create_time(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.utcnow()


def ensure_default_task(db: Session) -> Task:
    task = db.scalar(select(Task).limit(1))
    if task is None:
        task = Task(name="全球科技新闻自动同步与精编", mode="manual", status="active")
        db.add(task)
        db.commit()
        db.refresh(task)
    return task


def run_test_batch(
    db: Session,
    task_id: int,
    start_time: datetime,
    end_time: datetime,
    *,
    trigger_type: str = "manual_test",
) -> Batch:
    settings = get_settings()
    task = db.get(Task, task_id)
    if task is None:
        raise ValueError(f"Task not found: {task_id}")

    batch = Batch(
        task_id=task_id,
        batch_uuid=f"batch-{uuid.uuid4().hex[:12]}",
        trigger_type=trigger_type,
        start_time=start_time,
        end_time=end_time,
        status="running",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    llm_runtime = get_llm_runtime(db)
    if not (llm_runtime.get("api_key") or "").strip():
        batch.status = "failed"
        db.add(batch)
        db.commit()
        raise ValueError("未配置 LLM API Key，无法进行改写")

    records = fetch_amp_records(db, start_time=start_time, end_time=end_time, max_rows=500)
    source_snapshots: list[dict] = []
    rewritten_count = 0
    for rec in records:
        normalized = normalize_content(rec)
        source = SourceRecord(
            batch_id=batch.id,
            original_id=str(rec.get("story_id") or rec.get("nm_transmission_id")),
            account_name=rec.get("account_name"),
            source_company=rec.get("account_name"),
            original_title=normalized["title"] or "",
            original_body=normalized["content_html"] or "",
            thumbnail_url=normalized.get("image_url"),
            fetched_at=_parse_amp_create_time(rec.get("create_time")),
            raw_json=normalized.get("raw_json"),
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        source_snapshots.append(
            {
                "source_record_id": source.id,
                "original_id": source.original_id,
                "title": source.original_title,
                "body": source.original_body,
                "account_name": source.account_name,
            }
        )

    llm_outputs: dict[int, dict] = {}
    max_workers = max(1, min(settings.llm_max_concurrency, len(source_snapshots) or 1))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(
                rewrite_news,
                LLMInput(
                    original_id=s["original_id"],
                    title=s["title"],
                    body=s["body"],
                    account_name=s["account_name"],
                ),
                None,
                llm_runtime,
            ): s["source_record_id"]
            for s in source_snapshots
        }
        for future in as_completed(future_map):
            source_id = future_map[future]
            try:
                llm_outputs[source_id] = future.result()["result"]
            except Exception as exc:  # noqa: BLE001
                llm_outputs[source_id] = {
                    "is_adopted": "否",
                    "adoption_reason": f"LLM 调用失败：{exc}",
                }

    for s in source_snapshots:
        llm_output = llm_outputs.get(s["source_record_id"], {"is_adopted": "否", "adoption_reason": "LLM 无返回"})
        ai = AIResult(
            source_record_id=s["source_record_id"],
            is_adopted=llm_output.get("is_adopted", "否"),
            adoption_reason=llm_output.get("adoption_reason", ""),
            industry_category=llm_output.get("industry_category"),
            edited_article=llm_output.get("edited_article"),
            news_brief=llm_output.get("news_brief"),
            headline_1=llm_output.get("headline_1"),
            headline_2=llm_output.get("headline_2"),
            headline_3=llm_output.get("headline_3"),
            ai_result_json=json.dumps(llm_output, ensure_ascii=False),
        )
        db.add(ai)

        status = "noise" if ai.is_adopted == "否" else "ready_to_publish"
        if status == "ready_to_publish":
            rewritten_count += 1
        db.add(
            PublishItem(
                batch_id=batch.id,
                source_record_id=s["source_record_id"],
                status=status,
                publish_payload_json=json.dumps(
                    {
                        "publish_title": llm_output.get("headline_1") or s["title"],
                        "publish_content": llm_output.get("edited_article") or "",
                    },
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()

    batch.raw_count = len(records)
    batch.rewritten_count = rewritten_count
    batch.published_count = 0
    batch.cvr = 0.0
    batch.status = "ready_to_publish" if task.mode == "manual" else "publishing"
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def run_scheduled_ingest(db: Session, task_id: int) -> Batch | None:
    """按任务的 publish_interval_hours 拉取 AMP 时间窗并生成批次；仅当任务为自动模式且已配置间隔时执行。"""
    task = db.get(Task, task_id)
    if task is None or task.mode != "auto" or task.status != "active":
        return None
    hours = task.publish_interval_hours
    if hours not in (1, 3, 12, 24):
        return None
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    return run_test_batch(
        db,
        task_id,
        start_time,
        end_time,
        trigger_type="scheduled",
    )

