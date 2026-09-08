from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models import User
from app.schemas import AiSettingsPublic, AiSettingsUpdate
from app.services.ai import PROVIDERS, get_or_create_config, key_hint, providers_catalog, resolve_ai

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/ai", response_model=AiSettingsPublic)
def get_ai_settings(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> AiSettingsPublic:
    provider, model, key = resolve_ai(db)
    return AiSettingsPublic(
        provider=provider,
        model=model,
        api_key_set=bool(key),
        api_key_hint=key_hint(key) if key else "",
        providers=providers_catalog(),  # type: ignore[arg-type]
    )


@router.put("/ai", response_model=AiSettingsPublic)
def save_ai_settings(
    payload: AiSettingsUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AiSettingsPublic:
    row = get_or_create_config(db)
    provider = payload.provider if payload.provider in PROVIDERS else "openai"
    row.ai_provider = provider
    allowed = {mid for mid, _ in PROVIDERS[provider]["models"]}
    row.ai_model = payload.model if payload.model in allowed else PROVIDERS[provider]["default_model"]
    if payload.clear_api_key:
        row.ai_api_key = ""
    elif payload.api_key is not None and payload.api_key.strip():
        row.ai_api_key = payload.api_key.strip()
    db.commit()
    provider, model, key = resolve_ai(db)
    return AiSettingsPublic(
        provider=provider,
        model=model,
        api_key_set=bool(key),
        api_key_hint=key_hint(key) if key else "",
        providers=providers_catalog(),  # type: ignore[arg-type]
    )
