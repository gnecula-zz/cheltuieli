"""Identity from Home Assistant Ingress. Trust only Supervisor's proxy IP."""

from __future__ import annotations

import ipaddress
import secrets

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import settings
from app.models import User

HA_EMAIL_SUFFIX = "@homeassistant.local"


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return ""


def _ip_trusted(ip: str) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip in settings.ingress_ip_list
    for allowed in settings.ingress_ip_list:
        try:
            if "/" in allowed:
                if addr in ipaddress.ip_network(allowed, strict=False):
                    return True
            elif addr == ipaddress.ip_address(allowed):
                return True
        except ValueError:
            if ip == allowed:
                return True
    return False


def ingress_identity(request: Request) -> tuple[str, str, str] | None:
    if not settings.is_homeassistant:
        return None
    if not _ip_trusted(_client_ip(request)):
        return None
    user_id = (request.headers.get("x-remote-user-id") or "").strip()
    username = (request.headers.get("x-remote-user-name") or "").strip()
    display = (request.headers.get("x-remote-user-display-name") or "").strip()
    if not user_id:
        return None
    return user_id, username, display


def _wanted_admin(ha_user_id: str, username: str, db: Session) -> bool:
    admins = settings.hass_admin_user_list
    if admins:
        return ha_user_id.lower() in admins or username.lower() in admins
    if db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count() == 0:
        return True
    return False


def provision_ha_user(db: Session, ha_user_id: str, username: str, display: str) -> User:
    user = db.query(User).filter(User.ha_user_id == ha_user_id).first()
    name = (display or username or "Utilizator HA").strip()[:120]
    email = f"{(username or ha_user_id).lower()}{HA_EMAIL_SUFFIX}"[:255]
    want_admin = _wanted_admin(ha_user_id, username, db)
    if user:
        user.name = name
        if settings.hass_admin_user_list:
            user.role = "admin" if want_admin else "membru"
        elif want_admin and user.role != "admin":
            user.role = "admin"
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cont dezactivat")
        db.commit()
        db.refresh(user)
        return user

    taken = db.query(User).filter(User.email == email).first()
    if taken:
        email = f"ha-{ha_user_id}{HA_EMAIL_SUFFIX}"
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(secrets.token_urlsafe(24)),
        role="admin" if want_admin else "membru",
        ha_user_id=ha_user_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
