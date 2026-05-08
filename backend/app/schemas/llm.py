from pydantic import BaseModel


class RewritePreviewRequest(BaseModel):
    original_id: str = "preview"
    title: str
    body: str
    account_name: str | None = None


class RewritePreviewResponse(BaseModel):
    result: dict
