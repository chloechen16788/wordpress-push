from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models import PublishItem
from app.schemas.common import APIMessage
from app.schemas.tasking import BatchPublishRequest, PublishItemRequest, SelectedPublishRequest
from app.services.publish_service import trigger_publish_task

router = APIRouter(prefix="/api/publish", tags=["publish"])


@router.post("/batch", response_model=APIMessage)
def publish_batch(payload: BatchPublishRequest, db: Session = Depends(get_db)) -> APIMessage:
    trigger_publish_task(SessionLocal, payload.task_id, payload.batch_id)
    return APIMessage(message="batch publish job started")


@router.post("/selected", response_model=APIMessage)
def publish_selected(payload: SelectedPublishRequest, db: Session = Depends(get_db)) -> APIMessage:
    if not payload.publish_item_ids:
        raise HTTPException(status_code=400, detail="publish_item_ids cannot be empty")
    trigger_publish_task(
        SessionLocal,
        payload.task_id,
        payload.batch_id,
        publish_item_ids=payload.publish_item_ids,
    )
    return APIMessage(message="selected publish job started")


@router.post("/item", response_model=APIMessage)
def publish_item(payload: PublishItemRequest, db: Session = Depends(get_db)) -> APIMessage:
    item = db.get(PublishItem, payload.publish_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="publish item not found")
    trigger_publish_task(
        SessionLocal,
        item.batch.task_id,
        item.batch_id,
        publish_item_ids=[payload.publish_item_id],
    )
    return APIMessage(message="single item publish started")

