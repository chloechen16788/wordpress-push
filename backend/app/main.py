import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Reuse existing root-level scripts as requested in plan.
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api import build_api_router
from app.core.config import get_settings
from app.db.init_db import init_db
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.services.task_service import ensure_default_task
from app.db.session import SessionLocal

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.include_router(build_api_router())
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with SessionLocal() as db:
        ensure_default_task(db)
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_scheduler()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}

