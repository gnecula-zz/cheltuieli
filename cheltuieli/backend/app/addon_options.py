"""Home Assistant add-on options from /data/options.json."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from app.config import settings
from app.models import AppConfig

OPTIONS_PATH = Path("/data/options.json")
SECRET_PATH = Path("/data/secret_key")


def read_addon_options() -> dict:
    if not OPTIONS_PATH.is_file():
        return {}
    try:
        data = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def apply_addon_options() -> dict:
    opts = read_addon_options()
    if settings.is_homeassistant:
        Path("/data").mkdir(parents=True, exist_ok=True)
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
        if SECRET_PATH.is_file():
            key = SECRET_PATH.read_text(encoding="utf-8").strip()
            if key:
                settings.secret_key = key
        elif settings.secret_key == "schimba-aceasta-cheie-in-productie":
            key = secrets.token_hex(32)
            SECRET_PATH.write_text(key, encoding="utf-8")
            settings.secret_key = key

    admins = opts.get("admin_users", "")
    if isinstance(admins, list):
        admins = ",".join(str(item).strip() for item in admins if str(item).strip())
    if admins:
        settings.hass_admin_users = str(admins)

    token = opts.get("supervisor_token") or settings.supervisor_token
    if token:
        settings.supervisor_token = str(token)
    return opts


def apply_ai_options(db, opts: dict) -> None:
    """Copy the add-on API key only when the app has none.

    Supervisor rewrites /data/options.json on every start with schema defaults
    (ai_provider=openai). Those must not overwrite provider/model from Setări.
    """
    key = str(opts.get("ai_api_key") or "").strip()
    if not key:
        return
    row = db.query(AppConfig).order_by(AppConfig.id).first()
    if not row or (row.ai_api_key or "").strip():
        return
    row.ai_api_key = key
    db.commit()
