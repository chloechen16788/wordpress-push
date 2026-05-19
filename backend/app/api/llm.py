from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.llm import RewritePreviewRequest, RewritePreviewResponse
from app.services.llm_service import LLMInput, rewrite_news

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.post("/rewrite-preview", response_model=RewritePreviewResponse)
def rewrite_preview(payload: RewritePreviewRequest, db: Session = Depends(get_db)) -> RewritePreviewResponse:
    try:
        out = rewrite_news(
            LLMInput(
                original_id=payload.original_id,
                title=payload.title,
                body=payload.body,
                account_name=payload.account_name,
            ),
            db=db,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RewritePreviewResponse(result=out["result"])
