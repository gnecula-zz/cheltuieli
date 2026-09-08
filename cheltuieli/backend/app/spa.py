"""Serve the React build behind Home Assistant Ingress."""

from __future__ import annotations

import html
import re
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from app.config import settings

_BASE_RE = re.compile(r"<base\s+href=\"[^\"]*\"\s*/?>", re.IGNORECASE)


def frontend_root() -> Path | None:
    raw = (settings.frontend_dir or "").strip()
    if not raw:
        return None
    path = Path(raw).resolve()
    if path.is_dir() and (path / "index.html").is_file():
        return path
    return None


def _ingress_path(request: Request) -> str:
    path = (request.headers.get("x-ingress-path") or "").strip().rstrip("/")
    if path and path.startswith("/") and ".." not in path:
        return path
    return ""


def spa_index(request: Request) -> Response:
    root = frontend_root()
    if not root:
        raise HTTPException(status_code=404, detail="Frontend indisponibil")
    html_text = (root / "index.html").read_text(encoding="utf-8")
    ingress = _ingress_path(request)
    href = f"{html.escape(ingress, quote=True)}/" if ingress else "./"
    tag = f'<base href="{href}">'
    if _BASE_RE.search(html_text):
        html_text = _BASE_RE.sub(tag, html_text, count=1)
    else:
        html_text = html_text.replace("<head>", f"<head>\n    {tag}", 1)
    return HTMLResponse(html_text)


def spa_file(request: Request, full_path: str) -> Response:
    root = frontend_root()
    if not root:
        raise HTTPException(status_code=404)
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404)
    candidate = (root / full_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return spa_index(request)
    if candidate.is_file():
        return FileResponse(candidate)
    return spa_index(request)
