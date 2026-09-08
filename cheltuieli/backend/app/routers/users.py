from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Document, Expense, User
from app.schemas import UserCreate, UserPublic, UserSelfUpdate, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()


def apply_user_changes(db: Session, user: User, data: dict, current: User, *, allow_role: bool) -> User:
    ha_managed = settings.is_homeassistant and bool(user.ha_user_id)
    if ha_managed:
        data.pop("password", None)
        data.pop("email", None)
        data.pop("name", None)
    if "password" in data:
        password = data.pop("password")
        if password:
            user.password_hash = hash_password(password)
    if "email" in data and data["email"]:
        data["email"] = data["email"].strip().lower()
        exists = db.query(User).filter(User.email == data["email"], User.id != user.id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Email deja folosit")
    if "name" in data and data["name"]:
        data["name"] = data["name"].strip()
    if not allow_role:
        data.pop("role", None)
        data.pop("is_active", None)
    if data.get("role") and data["role"] not in {"admin", "membru"}:
        raise HTTPException(status_code=400, detail="Rol invalid")
    if data.get("role") == "membru" and user.role == "admin" and _admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Trebuie să rămână cel puțin un administrator")
    if data.get("is_active") is False and user.id == current.id:
        raise HTTPException(status_code=400, detail="Nu îți poți dezactiva propriul cont")
    for key, value in data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserPublic])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserPublic)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)) -> User:
    if settings.is_homeassistant:
        raise HTTPException(
            status_code=403,
            detail="Utilizatorii vin din Home Assistant. Deschide aplicația cu fiecare cont HA.",
        )
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email deja folosit")
    role = payload.role if payload.role in {"admin", "membru"} else "membru"
    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/me", response_model=UserPublic)
def update_me(
    payload: UserSelfUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> User:
    data = payload.model_dump(exclude_unset=True)
    return apply_user_changes(db, current, data, current, allow_role=False)


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilizator inexistent")
    data = payload.model_dump(exclude_unset=True)
    return apply_user_changes(db, user, data, current, allow_role=True)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilizator inexistent")
    if user.id == current.id:
        raise HTTPException(status_code=400, detail="Nu îți poți șterge propriul cont")
    if settings.is_homeassistant:
        raise HTTPException(
            status_code=403,
            detail="Utilizatorii Home Assistant nu se șterg din aplicație.",
        )
    if user.role == "admin" and _admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Trebuie să rămână cel puțin un administrator")
    db.query(Document).filter(Document.user_id == user.id).update({Document.user_id: current.id})
    db.query(Expense).filter(Expense.user_id == user.id).update({Expense.user_id: current.id})
    db.delete(user)
    db.commit()
    return {"ok": True}
