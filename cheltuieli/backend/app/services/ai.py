from __future__ import annotations

import base64
import io
import json
import re

import httpx
from openai import OpenAI
from PIL import Image
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AppConfig

PROVIDERS: dict[str, dict] = {
    "openai": {
        "label": "OpenAI",
        "kind": "openai",
        "base_url": None,
        "default_model": "gpt-4o-mini",
        "models": [
            ("gpt-4o-mini", "GPT-4o mini"),
            ("gpt-4o", "GPT-4o"),
            ("gpt-4.1-mini", "GPT-4.1 mini"),
            ("gpt-4.1", "GPT-4.1"),
        ],
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "kind": "anthropic",
        "default_model": "claude-sonnet-4-20250514",
        "models": [
            ("claude-sonnet-4-20250514", "Claude Sonnet 4"),
            ("claude-3-5-sonnet-latest", "Claude 3.5 Sonnet"),
            ("claude-3-5-haiku-latest", "Claude 3.5 Haiku"),
        ],
    },
    "google": {
        "label": "Google (Gemini)",
        "kind": "google",
        "default_model": "gemini-2.0-flash",
        "models": [
            ("gemini-2.0-flash", "Gemini 2.0 Flash"),
            ("gemini-2.5-flash", "Gemini 2.5 Flash"),
            ("gemini-1.5-flash", "Gemini 1.5 Flash"),
        ],
    },
    "openrouter": {
        "label": "OpenRouter",
        "kind": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o-mini",
        "models": [
            ("openai/gpt-4o-mini", "GPT-4o mini"),
            ("openai/gpt-4o", "GPT-4o"),
            ("google/gemini-2.0-flash-001", "Gemini 2.0 Flash"),
            ("anthropic/claude-3.5-sonnet", "Claude 3.5 Sonnet"),
        ],
    },
}


def get_or_create_config(db: Session) -> AppConfig:
    row = db.query(AppConfig).order_by(AppConfig.id).first()
    if row:
        return row
    row = AppConfig(
        ai_provider="openai",
        ai_model=settings.openai_model or "gpt-4o-mini",
        ai_api_key=settings.openai_api_key.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def resolve_ai(db: Session) -> tuple[str, str, str]:
    row = get_or_create_config(db)
    provider = row.ai_provider if row.ai_provider in PROVIDERS else "openai"
    key = (row.ai_api_key or "").strip() or settings.openai_api_key.strip()
    model = (row.ai_model or "").strip() or PROVIDERS[provider]["default_model"]
    return provider, model, key


def is_ai_configured(db: Session) -> bool:
    _, _, key = resolve_ai(db)
    return bool(key)


def key_hint(key: str) -> str:
    key = key.strip()
    if len(key) < 8:
        return "setată" if key else ""
    return f"••••{key[-4:]}"


def providers_catalog() -> list[dict]:
    return [
        {
            "id": pid,
            "label": spec["label"],
            "models": [{"id": mid, "label": label} for mid, label in spec["models"]],
        }
        for pid, spec in PROVIDERS.items()
    ]


def image_jpeg_b64(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def image_to_data_url(image: Image.Image) -> str:
    return f"data:image/jpeg;base64,{image_jpeg_b64(image)}"


def _parse_json_content(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text or "{}")


def call_vision(
    db: Session,
    system_prompt: str,
    images: list[Image.Image] | None = None,
    text: str | None = None,
) -> dict:
    provider, model, key = resolve_ai(db)
    if not key:
        raise RuntimeError("Agentul AI nu este configurat. Adaugă cheia API în Setări.")
    spec = PROVIDERS.get(provider) or PROVIDERS["openai"]
    kind = spec["kind"]
    user_text = "Extrage cheltuielile din documentul atașat. Documente în română (bon, factură sau extras)."
    if text:
        user_text += "\n\n" + text[:12000]
    images = images or []

    if kind == "openai":
        return _call_openai_compatible(spec.get("base_url"), key, model, system_prompt, user_text, images)
    if kind == "anthropic":
        return _call_anthropic(key, model, system_prompt, user_text, images)
    if kind == "google":
        return _call_google(key, model, system_prompt, user_text, images)
    raise RuntimeError(f"Furnizor AI necunoscut: {provider}")


def _call_openai_compatible(
    base_url: str | None,
    key: str,
    model: str,
    system_prompt: str,
    user_text: str,
    images: list[Image.Image],
) -> dict:
    client = OpenAI(api_key=key, base_url=base_url) if base_url else OpenAI(api_key=key)
    content: list[dict] = [{"type": "text", "text": user_text}]
    for image in images:
        content.append({"type": "image_url", "image_url": {"url": image_to_data_url(image)}})
    kwargs: dict = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
    }
    try:
        response = client.chat.completions.create(response_format={"type": "json_object"}, **kwargs)
    except Exception:
        response = client.chat.completions.create(**kwargs)
    return _parse_json_content(response.choices[0].message.content or "{}")


def _call_anthropic(key: str, model: str, system_prompt: str, user_text: str, images: list[Image.Image]) -> dict:
    content: list[dict] = []
    for image in images:
        content.append(
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": image_jpeg_b64(image)},
            }
        )
    content.append({"type": "text", "text": user_text + "\nRăspunde doar cu JSON."})
    with httpx.Client(timeout=90) as client:
        response = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 4096,
                "system": system_prompt,
                "messages": [{"role": "user", "content": content}],
            },
        )
        response.raise_for_status()
        data = response.json()
    parts = [block.get("text") or "" for block in data.get("content") or [] if block.get("type") == "text"]
    return _parse_json_content("\n".join(parts))


def _call_google(key: str, model: str, system_prompt: str, user_text: str, images: list[Image.Image]) -> dict:
    parts: list[dict] = [{"text": f"{system_prompt}\n\n{user_text}"}]
    for image in images:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_jpeg_b64(image)}})
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    with httpx.Client(timeout=90) as client:
        response = client.post(
            url,
            params={"key": key},
            json={
                "contents": [{"parts": parts}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
            },
        )
        response.raise_for_status()
        data = response.json()
    candidates = data.get("candidates") or []
    raw_parts = (((candidates[0] if candidates else {}).get("content") or {}).get("parts") or [])
    text = "".join(part.get("text") or "" for part in raw_parts)
    return _parse_json_content(text)
