from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Press Flow API"
    app_env: str = "dev"
    database_url: str = "sqlite:///./backend/data/press_flow.db"
    timezone: str = "Asia/Shanghai"
    stream_keepalive_seconds: int = 15

    amp_host: str = "139.198.21.183"
    amp_port: int = 3460
    amp_user: str = "prnqa"
    amp_password: str = "Comeon2019_prn"
    amp_database: str = "media"

    llm_provider: str = "mock"
    llm_model: str = "gpt-4.1-mini"
    llm_api_key: str | None = None
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_max_concurrency: int = 50

    model_config = SettingsConfigDict(
        env_prefix="PRESS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def sqlite_path(self) -> Path | None:
        if not self.database_url.startswith("sqlite:///"):
            return None
        raw = self.database_url.replace("sqlite:///", "", 1)
        return Path(raw).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()

