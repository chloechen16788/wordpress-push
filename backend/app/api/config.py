from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import LLMConfig, Platform, PublishLog, SourceConfig
from app.schemas.config import (
    LLMConfigOut,
    LLMConfigUpdate,
    PlatformCreate,
    PlatformOut,
    PlatformUpdate,
    SourceConfigOut,
    SourceConfigUpdate,
)
from app.utils.security import encrypt_secret

router = APIRouter(prefix="/api/config", tags=["config"])

_VALID_AUTH = frozenset({"rest_app_password", "cookie_nonce"})


@router.get("/source", response_model=SourceConfigOut)
def get_source_config(db: Session = Depends(get_db)) -> SourceConfigOut:
    cfg = db.scalar(select(SourceConfig).limit(1))
    if cfg is None:
        raise HTTPException(status_code=404, detail="source config not found")
    return SourceConfigOut(
        amp_host=cfg.amp_host,
        amp_port=cfg.amp_port,
        amp_user=cfg.amp_user,
        amp_database=cfg.amp_database,
    )


@router.put("/source", response_model=SourceConfigOut)
def update_source_config(payload: SourceConfigUpdate, db: Session = Depends(get_db)) -> SourceConfigOut:
    cfg = db.scalar(select(SourceConfig).limit(1))
    if cfg is None:
        cfg = SourceConfig(
            amp_host=payload.amp_host,
            amp_port=payload.amp_port,
            amp_user=payload.amp_user,
            amp_password=payload.amp_password,
            amp_database=payload.amp_database,
        )
    else:
        cfg.amp_host = payload.amp_host
        cfg.amp_port = payload.amp_port
        cfg.amp_user = payload.amp_user
        cfg.amp_password = payload.amp_password
        cfg.amp_database = payload.amp_database
    db.add(cfg)
    db.commit()
    return SourceConfigOut(
        amp_host=cfg.amp_host,
        amp_port=cfg.amp_port,
        amp_user=cfg.amp_user,
        amp_database=cfg.amp_database,
    )


@router.get("/llm", response_model=LLMConfigOut)
def get_llm_config(db: Session = Depends(get_db)) -> LLMConfigOut:
    cfg = db.scalar(select(LLMConfig).limit(1))
    if cfg is None:
        raise HTTPException(status_code=404, detail="llm config not found")
    return LLMConfigOut(
        provider=cfg.provider,
        model=cfg.model,
        base_url=cfg.base_url,
        has_api_key=bool(cfg.api_key),
        system_prompt=cfg.system_prompt,
    )


@router.put("/llm", response_model=LLMConfigOut)
def update_llm_config(payload: LLMConfigUpdate, db: Session = Depends(get_db)) -> LLMConfigOut:
    cfg = db.scalar(select(LLMConfig).limit(1))
    if cfg is None:
        cfg = LLMConfig()
    updates = payload.model_dump(exclude_unset=True)
    if "provider" in updates:
        cfg.provider = payload.provider
    if "model" in updates:
        cfg.model = payload.model
    if "api_key" in updates:
        cfg.api_key = payload.api_key
    if "base_url" in updates:
        cfg.base_url = payload.base_url
    if "system_prompt" in updates:
        cfg.system_prompt = payload.system_prompt
    db.add(cfg)
    db.commit()
    return LLMConfigOut(
        provider=cfg.provider,
        model=cfg.model,
        base_url=cfg.base_url,
        has_api_key=bool(cfg.api_key),
        system_prompt=cfg.system_prompt,
    )


@router.get("/platforms", response_model=list[PlatformOut])
def list_platforms(db: Session = Depends(get_db)) -> list[PlatformOut]:
    rows = db.scalars(select(Platform).order_by(Platform.id.asc())).all()
    return [PlatformOut.model_validate(row) for row in rows]


@router.post("/platforms", response_model=PlatformOut)
def create_platform(payload: PlatformCreate, db: Session = Depends(get_db)) -> PlatformOut:
    if payload.auth_type not in _VALID_AUTH:
        raise HTTPException(status_code=400, detail="invalid auth_type")
    row = Platform(
        name=payload.name,
        site_url=payload.site_url,
        auth_type=payload.auth_type,
        username=payload.username,
        secret_encrypted=encrypt_secret(payload.secret),
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PlatformOut.model_validate(row)


@router.put("/platforms/{platform_id}", response_model=PlatformOut)
def update_platform(platform_id: int, payload: PlatformUpdate, db: Session = Depends(get_db)) -> PlatformOut:
    row = db.get(Platform, platform_id)
    if row is None:
        raise HTTPException(status_code=404, detail="platform not found")
    if payload.auth_type not in _VALID_AUTH:
        raise HTTPException(status_code=400, detail="invalid auth_type")
    row.name = payload.name
    row.site_url = payload.site_url
    row.auth_type = payload.auth_type
    row.username = payload.username
    row.is_active = payload.is_active
    if payload.secret:
        row.secret_encrypted = encrypt_secret(payload.secret)
    db.add(row)
    db.commit()
    db.refresh(row)
    return PlatformOut.model_validate(row)


@router.delete("/platforms/{platform_id}")
def delete_platform(platform_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    row = db.get(Platform, platform_id)
    if row is None:
        raise HTTPException(status_code=404, detail="platform not found")
    log_count = db.scalar(
        select(func.count()).select_from(PublishLog).where(PublishLog.platform_id == platform_id)
    )
    if log_count and int(log_count) > 0:
        raise HTTPException(
            status_code=400,
            detail="platform has publish logs; remove or archive logs before delete",
        )
    db.delete(row)
    db.commit()
    return {"message": "deleted"}

