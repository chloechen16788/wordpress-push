from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Task
from app.services.publish_service import trigger_publish_task
from app.services.task_service import run_scheduled_ingest

settings = get_settings()
scheduler = BackgroundScheduler(timezone=settings.timezone)

JOB_PREFIX = "task_interval_"
_ALLOWED = {1, 3, 12, 24}


def _scheduled_job(task_id: int) -> None:
    with SessionLocal() as db:
        batch = run_scheduled_ingest(db, task_id)
        if batch is None:
            return
        batch_id = batch.id
        task_id_final = task_id
    trigger_publish_task(SessionLocal, task_id_final, batch_id)


def refresh_scheduled_jobs() -> None:
    """根据数据库中的任务重建定时间隔任务（自动模式 + 1/3/12/24 小时）。"""
    for job in scheduler.get_jobs():
        if job.id and job.id.startswith(JOB_PREFIX):
            scheduler.remove_job(job.id)

    with SessionLocal() as db:
        tasks = db.scalars(select(Task).where(Task.status == "active")).all()
        for t in tasks:
            if t.mode != "auto":
                continue
            hours = t.publish_interval_hours
            if hours not in _ALLOWED:
                continue
            scheduler.add_job(
                _scheduled_job,
                IntervalTrigger(hours=hours),
                args=[t.id],
                id=f"{JOB_PREFIX}{t.id}",
                replace_existing=True,
            )


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
    refresh_scheduled_jobs()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
