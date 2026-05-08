from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="manual")
    cron_expr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publish_interval_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_test_space: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    batches: Mapped[list["Batch"]] = relationship("Batch", back_populates="task")


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    batch_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    trigger_type: Mapped[str] = mapped_column(String(30), default="manual_test")
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    raw_count: Mapped[int] = mapped_column(Integer, default=0)
    rewritten_count: Mapped[int] = mapped_column(Integer, default=0)
    published_count: Mapped[int] = mapped_column(Integer, default=0)
    cvr: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="running")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    task: Mapped["Task"] = relationship("Task", back_populates="batches")
    source_records: Mapped[list["SourceRecord"]] = relationship(
        "SourceRecord", back_populates="batch", cascade="all, delete-orphan"
    )
    publish_items: Mapped[list["PublishItem"]] = relationship(
        "PublishItem", back_populates="batch", cascade="all, delete-orphan"
    )


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False, index=True)
    original_id: Mapped[str] = mapped_column(String(128), index=True)
    account_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_company: Mapped[str | None] = mapped_column(String(120), nullable=True)
    original_title: Mapped[str] = mapped_column(Text, nullable=False)
    original_body: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="source_records")
    ai_result: Mapped["AIResult"] = relationship(
        "AIResult", back_populates="source_record", uselist=False, cascade="all, delete-orphan"
    )
    publish_item: Mapped["PublishItem"] = relationship(
        "PublishItem", back_populates="source_record", uselist=False, cascade="all, delete-orphan"
    )


class AIResult(Base):
    __tablename__ = "ai_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_record_id: Mapped[int] = mapped_column(
        ForeignKey("source_records.id"), nullable=False, unique=True, index=True
    )
    is_adopted: Mapped[str] = mapped_column(String(8), default="否")
    adoption_reason: Mapped[str] = mapped_column(Text, default="")
    industry_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    edited_article: Mapped[str | None] = mapped_column(Text, nullable=True)
    news_brief: Mapped[str | None] = mapped_column(Text, nullable=True)
    headline_1: Mapped[str | None] = mapped_column(String(120), nullable=True)
    headline_2: Mapped[str | None] = mapped_column(String(120), nullable=True)
    headline_3: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ai_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    source_record: Mapped["SourceRecord"] = relationship("SourceRecord", back_populates="ai_result")


class PublishItem(Base):
    __tablename__ = "publish_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False, index=True)
    source_record_id: Mapped[int] = mapped_column(
        ForeignKey("source_records.id"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="ready_to_publish")
    publish_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    batch: Mapped["Batch"] = relationship("Batch", back_populates="publish_items")
    source_record: Mapped["SourceRecord"] = relationship("SourceRecord", back_populates="publish_item")
    logs: Mapped[list["PublishLog"]] = relationship(
        "PublishLog", back_populates="publish_item", cascade="all, delete-orphan"
    )


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    site_url: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_type: Mapped[str] = mapped_column(String(32), default="rest_app_password")
    username: Mapped[str] = mapped_column(String(120), nullable=False)
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    logs: Mapped[list["PublishLog"]] = relationship("PublishLog", back_populates="platform")


class PublishLog(Base):
    __tablename__ = "publish_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    publish_item_id: Mapped[int] = mapped_column(
        ForeignKey("publish_items.id"), nullable=False, index=True
    )
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    wp_post_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wp_media_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)

    publish_item: Mapped["PublishItem"] = relationship("PublishItem", back_populates="logs")
    platform: Mapped["Platform"] = relationship("Platform", back_populates="logs")


class SourceConfig(Base):
    __tablename__ = "source_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amp_host: Mapped[str] = mapped_column(String(120), nullable=False)
    amp_port: Mapped[int] = mapped_column(Integer, nullable=False, default=3460)
    amp_user: Mapped[str] = mapped_column(String(120), nullable=False)
    amp_password: Mapped[str] = mapped_column(String(255), nullable=False)
    amp_database: Mapped[str] = mapped_column(String(64), nullable=False, default="media")


class LLMConfig(Base):
    __tablename__ = "llm_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40), default="mock")
    model: Mapped[str] = mapped_column(String(80), default="gpt-4.1-mini")
    api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, default="")

