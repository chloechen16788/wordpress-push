from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Batch, Task
from app.schemas.common import BatchSummary
from app.schemas.tasking import RunTestRequest, RunTestResponse, TaskCreate, TaskOut, TaskUpdate
from app.services.scheduler_service import refresh_scheduled_jobs
from app.services.task_service import ensure_default_task, run_test_batch

router = APIRouter(prefix="/api", tags=["tasks"])

_ALLOWED_INTERVAL_HOURS = {1, 3, 12, 24}


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(db: Session = Depends(get_db)) -> list[TaskOut]:
    ensure_default_task(db)
    rows = db.scalars(select(Task).order_by(Task.id.asc())).all()
    return [TaskOut.model_validate(row) for row in rows]


@router.post("/tasks", response_model=TaskOut)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)) -> TaskOut:
    if payload.publish_interval_hours is not None and payload.publish_interval_hours not in _ALLOWED_INTERVAL_HOURS:
        raise HTTPException(
            status_code=400,
            detail="publish_interval_hours must be null or one of 1, 3, 12, 24",
        )
    row = Task(
        name=payload.name,
        mode=payload.mode,
        cron_expr=payload.cron_expr,
        publish_interval_hours=payload.publish_interval_hours,
        is_test_space=payload.is_test_space,
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    refresh_scheduled_jobs()
    return TaskOut.model_validate(row)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)) -> TaskOut:
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if payload.name is not None:
        task.name = payload.name
    if payload.mode is not None:
        task.mode = payload.mode
    if payload.cron_expr is not None:
        task.cron_expr = payload.cron_expr
    updates = payload.model_dump(exclude_unset=True)
    if "publish_interval_hours" in updates:
        val = updates["publish_interval_hours"]
        if val is None or val == 0:
            task.publish_interval_hours = None
        elif val in _ALLOWED_INTERVAL_HOURS:
            task.publish_interval_hours = val
        else:
            raise HTTPException(
                status_code=400,
                detail="publish_interval_hours must be null, 0 (off), or one of 1, 3, 12, 24",
            )
    if payload.is_test_space is not None:
        task.is_test_space = payload.is_test_space
    if payload.status is not None:
        task.status = payload.status
    db.add(task)
    db.commit()
    db.refresh(task)
    refresh_scheduled_jobs()
    return TaskOut.model_validate(task)


@router.post("/tasks/run-test", response_model=RunTestResponse)
def run_test(payload: RunTestRequest, db: Session = Depends(get_db)) -> RunTestResponse:
    task = db.get(Task, payload.task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    try:
        batch = run_test_batch(
            db,
            task_id=payload.task_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RunTestResponse(
        task_id=payload.task_id,
        batch_id=batch.id,
        batch_uuid=batch.batch_uuid,
        status=batch.status,
    )


@router.get("/batches", response_model=list[BatchSummary])
def list_batches(task_id: int, db: Session = Depends(get_db)) -> list[BatchSummary]:
    rows = db.scalars(
        select(Batch).where(Batch.task_id == task_id).order_by(Batch.created_at.desc())
    ).all()
    return [
        BatchSummary(
            id=row.id,
            task_id=row.task_id,
            batch_uuid=row.batch_uuid,
            trigger_type=row.trigger_type,
            status=row.status,
            raw_count=row.raw_count,
            rewritten_count=row.rewritten_count,
            published_count=row.published_count,
            cvr=row.cvr,
            start_time=row.start_time,
            end_time=row.end_time,
            created_at=row.created_at,
        )
        for row in rows
    ]

