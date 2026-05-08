from pydantic import BaseModel, Field


class SourceConfigOut(BaseModel):
    amp_host: str
    amp_port: int
    amp_user: str
    amp_database: str


class SourceConfigUpdate(BaseModel):
    amp_host: str
    amp_port: int = 3460
    amp_user: str
    amp_password: str
    amp_database: str = "media"


class LLMConfigOut(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    has_api_key: bool = False
    system_prompt: str


class LLMConfigUpdate(BaseModel):
    provider: str = "mock"
    model: str = "gpt-4.1-mini"
    api_key: str | None = None
    base_url: str | None = None
    system_prompt: str = ""


class PlatformBase(BaseModel):
    name: str
    site_url: str
    auth_type: str = Field(default="rest_app_password")
    username: str
    is_active: bool = True


class PlatformCreate(PlatformBase):
    secret: str


class PlatformUpdate(PlatformBase):
    secret: str | None = None


class PlatformOut(PlatformBase):
    id: int

    model_config = {"from_attributes": True}

