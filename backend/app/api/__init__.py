from fastapi import APIRouter

from app.api import config, llm, publish, records, stream, tasks


def build_api_router() -> APIRouter:
    router = APIRouter()
    router.include_router(tasks.router)
    router.include_router(config.router)
    router.include_router(records.router)
    router.include_router(publish.router)
    router.include_router(stream.router)
    router.include_router(llm.router)
    return router

