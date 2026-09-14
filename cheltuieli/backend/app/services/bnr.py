"""Curs BNR (National Bank of Romania) — XML oficial de pe curs.bnr.ro."""

from __future__ import annotations

import logging
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import httpx

logger = logging.getLogger(__name__)

BNR_DAILY_URL = "https://curs.bnr.ro/nbrfxrates.xml"
# Fallback istoric pe domeniul principal (unele instalări mai vechi îl folosesc încă).
BNR_FALLBACK_URLS = (
    "https://curs.bnr.ro/nbrfxrates.xml",
    "https://www.bnr.ro/nbrfxrates.xml",
)

SUPPORTED_FX = frozenset({"EUR"})
_MONEY = Decimal("0.01")
_RATE_Q = Decimal("0.0001")

_lock = threading.Lock()
_cache_day: date | None = None
_cache_rates: dict[str, "BnrRate"] | None = None
_cache_fetched_at: datetime | None = None


@dataclass(frozen=True)
class BnrRate:
    currency: str
    rate: Decimal
    rate_date: date
    multiplier: int = 1

    @property
    def ron_per_unit(self) -> Decimal:
        """Câți lei pentru 1 unitate de valută (ține cont de multiplier, ex. HUF=100)."""
        if self.multiplier <= 1:
            return self.rate
        return (self.rate / Decimal(self.multiplier)).quantize(_RATE_Q)


class BnrRateError(Exception):
    """Eroare la preluarea sau interpretarea cursului BNR."""


def _local_today() -> date:
    return datetime.now().astimezone().date()


def _parse_rates(xml_bytes: bytes) -> dict[str, BnrRate]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise BnrRateError("Răspunsul BNR nu este un XML valid.") from exc

    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0][1:]

    def q(tag: str) -> str:
        return f"{{{ns}}}{tag}" if ns else tag

    cube = None
    for candidate in root.iter(q("Cube")):
        if candidate.attrib.get("date"):
            cube = candidate
    if cube is None:
        raise BnrRateError("Nu am găsit data cursului în XML-ul BNR.")

    try:
        rate_date = date.fromisoformat(cube.attrib["date"][:10])
    except (KeyError, ValueError) as exc:
        raise BnrRateError("Data cursului BNR este invalidă.") from exc

    rates: dict[str, BnrRate] = {}
    for rate_el in cube.findall(q("Rate")):
        currency = (rate_el.attrib.get("currency") or "").strip().upper()
        if not currency:
            continue
        raw = (rate_el.text or "").strip().replace(",", ".")
        try:
            value = Decimal(raw)
        except InvalidOperation:
            continue
        multiplier = 1
        mult_raw = rate_el.attrib.get("multiplier")
        if mult_raw:
            try:
                multiplier = max(1, int(mult_raw))
            except ValueError:
                multiplier = 1
        rates[currency] = BnrRate(
            currency=currency,
            rate=value,
            rate_date=rate_date,
            multiplier=multiplier,
        )
    if not rates:
        raise BnrRateError("XML-ul BNR nu conține rate de schimb.")
    return rates


def _fetch_xml() -> bytes:
    last_error: Exception | None = None
    # Păstrăm URL-urile unice, în ordine.
    urls: list[str] = []
    for url in BNR_FALLBACK_URLS:
        if url not in urls:
            urls.append(url)
    for url in urls:
        try:
            with httpx.Client(timeout=12.0, follow_redirects=True) as client:
                response = client.get(
                    url,
                    headers={
                        "Accept": "application/xml,text/xml,*/*",
                        "User-Agent": "Cheltuieli-HA/1.0 (curs BNR)",
                    },
                )
            if response.status_code >= 400:
                last_error = BnrRateError(f"BNR a răspuns cu HTTP {response.status_code}.")
                continue
            content_type = (response.headers.get("content-type") or "").lower()
            body = response.content
            if "html" in content_type or body.lstrip().startswith(b"<!DOCTYPE") or body.lstrip().startswith(b"<html"):
                last_error = BnrRateError("BNR a returnat o pagină HTML în loc de XML.")
                continue
            if b"<DataSet" not in body and b"<Cube" not in body:
                last_error = BnrRateError("Răspunsul BNR nu conține cursuri valutare.")
                continue
            return body
        except httpx.HTTPError as exc:
            last_error = exc
            logger.warning("Preluare curs BNR eșuată de la %s: %s", url, exc)
    detail = str(last_error) if last_error else "necunoscută"
    raise BnrRateError(
        f"Nu am putut prelua cursul BNR pentru ziua curentă ({detail}). "
        "Verifică conexiunea la internet și încearcă din nou."
    )


def get_rates(*, force: bool = False) -> dict[str, BnrRate]:
    """Returnează ratele BNR; cache pe ziua calendaristică locală."""
    global _cache_day, _cache_rates, _cache_fetched_at
    today = _local_today()
    with _lock:
        if not force and _cache_rates is not None and _cache_day == today:
            return _cache_rates
        rates = _parse_rates(_fetch_xml())
        _cache_rates = rates
        _cache_day = today
        _cache_fetched_at = datetime.now(timezone.utc)
        return rates


def get_rate(currency: str, *, force: bool = False) -> BnrRate:
    code = (currency or "").strip().upper()
    if code in {"", "RON", "LEI"}:
        raise BnrRateError("RON nu necesită conversie.")
    rates = get_rates(force=force)
    rate = rates.get(code)
    if rate is None:
        raise BnrRateError(f"BNR nu publică curs pentru {code}.")
    return rate


def convert_to_ron(amount: Decimal, currency: str) -> tuple[Decimal, BnrRate]:
    """Convertește suma în RON la cursul BNR al zilei (ultima publicare disponibilă)."""
    code = (currency or "RON").strip().upper()
    if code in {"RON", "LEI"}:
        dummy = BnrRate(currency="RON", rate=Decimal("1"), rate_date=_local_today(), multiplier=1)
        return Decimal(amount).quantize(_MONEY, rounding=ROUND_HALF_UP), dummy
    if code not in SUPPORTED_FX:
        raise BnrRateError(f"Conversia automată este disponibilă doar pentru EUR (ai selectat {code}).")
    rate = get_rate(code)
    ron = (Decimal(amount) * rate.ron_per_unit).quantize(_MONEY, rounding=ROUND_HALF_UP)
    return ron, rate


def rate_public_dict(rate: BnrRate) -> dict:
    return {
        "currency": rate.currency,
        "rate": float(rate.ron_per_unit),
        "rate_raw": float(rate.rate),
        "multiplier": rate.multiplier,
        "rate_date": rate.rate_date.isoformat(),
        "source": "BNR",
        "source_url": BNR_DAILY_URL,
    }
