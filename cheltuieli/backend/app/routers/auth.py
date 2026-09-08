from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth import clear_auth_cookie, create_token, hash_password, set_auth_cookie, verify_password
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import AuthStatus, LoginRequest, UserCreate, UserPublic, UserSelfUpdate
from app.services.ai import is_ai_configured, resolve_ai

router = APIRouter(prefix="/auth", tags=["auth"])


def _reject_local_auth() -> None:
    if settings.is_homeassistant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Autentificarea se face prin Home Assistant.",
        )


@router.get("/status", response_model=AuthStatus)
def auth_status(db: Session = Depends(get_db)) -> AuthStatus:
    configured = is_ai_configured(db)
    provider, model = "", ""
    if configured:
        provider, model, _ = resolve_ai(db)
    ha = settings.is_homeassistant
    return AuthStatus(
        registration_open=False if ha else db.query(User).count() == 0,
        openai_configured=configured,
        ai_configured=configured,
        ai_provider=provider,
        ai_model=model,
        auth_mode="homeassistant" if ha else "local",
    )


@router.post("/register", response_model=UserPublic)
def register(payload: UserCreate, response: Response, db: Session = Depends(get_db)) -> User:
    _reject_local_auth()
    if db.query(User).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Înregistrarea este închisă. Cere unui administrator să-ți creeze contul.",
        )
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email deja folosit")
    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    set_auth_cookie(response, create_token(user.id, user.role))
    return user


@router.post("/login", response_model=UserPublic)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> User:
    _reject_local_auth()
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email sau parolă greșită")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Cont dezactivat")
    set_auth_cookie(response, create_token(user.id, user.role))
    return user


@router.post("/logout")
def logout(response: Response) -> dict:
    clear_auth_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserPublic)
def patch_me(
    payload: UserSelfUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    from app.routers.users import apply_user_changes

    return apply_user_changes(db, user, payload.model_dump(exclude_unset=True), user, allow_role=False)
