from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import Base, engine
from app.models import LLMConfig, SourceConfig


def _migrate_sqlite_schema() -> None:
    """为已有 SQLite 库追加新列（create_all 不会修改旧表）。"""
    settings = get_settings()
    if settings.sqlite_path() is None:
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(tasks)")).fetchall()
        col_names = {r[1] for r in rows}
        if "publish_interval_hours" not in col_names:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN publish_interval_hours INTEGER"))
        llm_rows = conn.execute(text("PRAGMA table_info(llm_config)")).fetchall()
        llm_col_names = {r[1] for r in llm_rows}
        if "base_url" not in llm_col_names:
            conn.execute(text("ALTER TABLE llm_config ADD COLUMN base_url VARCHAR(255)"))


def init_db() -> None:
    settings = get_settings()
    sqlite_path = settings.sqlite_path()
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()

    with Session(bind=engine) as db:
        source_cfg = db.scalar(select(SourceConfig).limit(1))
        if source_cfg is None:
            db.add(
                SourceConfig(
                    amp_host=settings.amp_host,
                    amp_port=settings.amp_port,
                    amp_user=settings.amp_user,
                    amp_password=settings.amp_password,
                    amp_database=settings.amp_database,
                )
            )

        llm_cfg = db.scalar(select(LLMConfig).limit(1))
        if llm_cfg is None:
            db.add(
                LLMConfig(
                    provider=settings.llm_provider,
                    model=settings.llm_model,
                    api_key=settings.llm_api_key,
                    base_url=settings.llm_base_url,
                    system_prompt="",
                )
            )
        elif not llm_cfg.base_url:
            llm_cfg.base_url = settings.llm_base_url
            db.add(llm_cfg)
        db.commit()

