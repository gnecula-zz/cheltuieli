from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import decode_token, token_from_request
from app.config import settings
from app.database import get_db
from app.ha_ingress import ingress_identity, provision_ha_user
from app.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    identity = ingress_identity(request)
    if identity:
        ha_user_id, username, display = identity
        return provision_ha_user(db, ha_user_id, username, display)
    if settings.is_homeassistant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Deschide Cheltuieli din bara Home Assistant (Ingress).",
        )
    token = token_from_request(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autentificare necesară")
    payload = decode_token(token)
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cont inactiv sau inexistent")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doar administratorul poate face asta")
    return user
