"""Curs valutar EUR→RON: BNR (oficial) cu fallback ECB."""

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
ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

# Ordine: gazdele BNR care servește XML dedicat primul; restul pot eșua (HTML/reset).
BNR_URLS = (
    "https://curs.bnr.ro/nbrfxrates.xml",
    "https://curs.bnr.ro/nbrfxrates10days.xml",
    "https://www.bnr.ro/nbrfxrates.xml",
    "https://www.bnro.ro/nbrfxrates.xml",
    "https://bnr.ro/nbrfxrates.xml",
    "http://curs.bnr.ro/nbrfxrates.xml",
)

SUPPORTED_FX = frozenset({"EUR"})
_MONEY = Decimal("0.01")
_RATE_Q = Decimal("0.0001")
_USER_AGENT = (
    "Mozilla/5.0 (compatible; Cheltuieli-HA/1.0.7; "
    "+https://github.com/gnecula-zz/cheltuieli)"
)
_HEADERS = {
    "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8",
    "User-Agent": _USER_AGENT,
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
}

_lock = threading.Lock()
_cache_day: date | None = None
_cache_rates: dict[str, "FxRate"] | None = None
_cache_meta: dict[str, str] | None = None
_cache_fetched_at: datetime | None = None


@dataclass(frozen=True)
class FxRate:
    currency: str
    rate: Decimal
    rate_date: date
    multiplier: int = 1
    source: str = "BNR"
    source_url: str = BNR_DAILY_URL

    @property
    def ron_per_unit(self) -> Decimal:
        """Câți lei pentru 1 unitate de valută (ține cont de multiplier, ex. HUF=100)."""
        if self.multiplier <= 1:
            return self.rate
        return (self.rate / Decimal(self.multiplier)).quantize(_RATE_Q)


# Alias pentru compatibilitate cu importurile existente.
BnrRate = FxRate


class BnrRateError(Exception):
    """Eroare la preluarea sau interpretarea cursului valutar."""


def _local_today() -> date:
    return datetime.now().astimezone().date()


def _is_html(body: bytes, content_type: str) -> bool:
    ct = content_type.lower()
    if "html" in ct and "xml" not in ct:
        return True
    head = body.lstrip()[:200].lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def _http_get(url: str) -> httpx.Response:
    timeout = httpx.Timeout(connect=6.0, read=12.0, write=12.0, pool=6.0)
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        http2=False,
        trust_env=True,
    ) as client:
        return client.get(url, headers=_HEADERS)


def _parse_bnr_rates(xml_bytes: bytes, *, source_url: str) -> dict[str, FxRate]:
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

    rates: dict[str, FxRate] = {}
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
        rates[currency] = FxRate(
            currency=currency,
            rate=value,
            rate_date=rate_date,
            multiplier=multiplier,
            source="BNR",
            source_url=source_url,
        )
    if not rates:
        raise BnrRateError("XML-ul BNR nu conține rate de schimb.")
    return rates


def _parse_ecb_rates(xml_bytes: bytes) -> dict[str, FxRate]:
    """ECB publică unități de valută pentru 1 EUR; RON rate = lei pentru 1 EUR."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise BnrRateError("Răspunsul ECB nu este un XML valid.") from exc

    day_cube = None
    for cube in root.iter():
        tag = cube.tag.rsplit("}", 1)[-1]
        if tag == "Cube" and cube.attrib.get("time"):
            day_cube = cube
            break
    if day_cube is None:
        raise BnrRateError("Nu am găsit data cursului în XML-ul ECB.")

    try:
        rate_date = date.fromisoformat(day_cube.attrib["time"][:10])
    except (KeyError, ValueError) as exc:
        raise BnrRateError("Data cursului ECB este invalidă.") from exc

    ron_rate: Decimal | None = None
    for cube in day_cube:
        tag = cube.tag.rsplit("}", 1)[-1]
        if tag != "Cube":
            continue
        if (cube.attrib.get("currency") or "").upper() == "RON":
            raw = (cube.attrib.get("rate") or "").strip().replace(",", ".")
            try:
                ron_rate = Decimal(raw)
            except InvalidOperation as exc:
                raise BnrRateError("Cursul ECB pentru RON este invalid.") from exc
            break
    if ron_rate is None or ron_rate <= 0:
        raise BnrRateError("XML-ul ECB nu conține cursul RON.")

    # ECB: 1 EUR = ron_rate RON → exact ce ne trebuie pentru EUR.
    return {
        "EUR": FxRate(
            currency="EUR",
            rate=ron_rate,
            rate_date=rate_date,
            multiplier=1,
            source="ECB",
            source_url=ECB_DAILY_URL,
        )
    }


def _try_bnr_url(url: str) -> dict[str, FxRate]:
    response = _http_get(url)
    if response.status_code >= 400:
        raise BnrRateError(f"BNR a răspuns cu HTTP {response.status_code} ({url}).")
    body = response.content
    content_type = response.headers.get("content-type") or ""
    if _is_html(body, content_type):
        raise BnrRateError(f"BNR a returnat HTML în loc de XML ({url}).")
    if b"<DataSet" not in body and b"<Rate" not in body:
        raise BnrRateError(f"Răspunsul de la {url} nu arată a fi curs BNR.")
    return _parse_bnr_rates(body, source_url=url)


def _try_ecb() -> dict[str, FxRate]:
    response = _http_get(ECB_DAILY_URL)
    if response.status_code >= 400:
        raise BnrRateError(f"ECB a răspuns cu HTTP {response.status_code}.")
    body = response.content
    content_type = response.headers.get("content-type") or ""
    if _is_html(body, content_type):
        raise BnrRateError("ECB a returnat HTML în loc de XML.")
    return _parse_ecb_rates(body)


def _fetch_rates() -> tuple[dict[str, FxRate], dict[str, str]]:
    """Încearcă toate sursele BNR, apoi ECB. Eșuează doar dacă toate cad."""
    errors: list[str] = []

    seen: set[str] = set()
    for url in BNR_URLS:
        if url in seen:
            continue
        seen.add(url)
        try:
            rates = _try_bnr_url(url)
            logger.info("Curs valutar preluat de la BNR: %s", url)
            return rates, {"source": "BNR", "source_url": url}
        except Exception as exc:  # noqa: BLE001 — vrem fallback pe orice eșec de rețea/parse
            msg = f"{url}: {exc}"
            errors.append(msg)
            logger.warning("Preluare curs BNR eșuată de la %s: %s", url, exc)

    try:
        rates = _try_ecb()
        logger.info("Curs valutar preluat de la ECB (fallback): %s", ECB_DAILY_URL)
        return rates, {"source": "ECB", "source_url": ECB_DAILY_URL}
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{ECB_DAILY_URL}: {exc}")
        logger.warning("Preluare curs ECB eșuată: %s", exc)

    detail = "; ".join(errors[-3:]) if errors else "necunoscută"
    raise BnrRateError(
        "Nu am putut prelua cursul EUR/RON (BNR și ECB au eșuat). "
        f"Ultimele erori: {detail}. Verifică conexiunea la internet și încearcă din nou."
    )


def get_rates(*, force: bool = False) -> dict[str, FxRate]:
    """Returnează ratele; cache pe ziua calendaristică locală."""
    global _cache_day, _cache_rates, _cache_meta, _cache_fetched_at
    today = _local_today()
    with _lock:
        if not force and _cache_rates is not None and _cache_day == today:
            return _cache_rates
        rates, meta = _fetch_rates()
        _cache_rates = rates
        _cache_meta = meta
        _cache_day = today
        _cache_fetched_at = datetime.now(timezone.utc)
        return rates


def get_rate(currency: str, *, force: bool = False) -> FxRate:
    code = (currency or "").strip().upper()
    if code in {"", "RON", "LEI"}:
        raise BnrRateError("RON nu necesită conversie.")
    rates = get_rates(force=force)
    rate = rates.get(code)
    if rate is None:
        raise BnrRateError(
            f"Sursa de curs ({(_cache_meta or {}).get('source', '?')}) nu oferă {code}."
        )
    return rate


def convert_to_ron(amount: Decimal, currency: str) -> tuple[Decimal, FxRate]:
    """Convertește suma în RON la cursul zilei (BNR, sau ECB dacă BNR e indisponibil)."""
    code = (currency or "RON").strip().upper()
    if code in {"RON", "LEI"}:
        dummy = FxRate(
            currency="RON",
            rate=Decimal("1"),
            rate_date=_local_today(),
            multiplier=1,
            source="RON",
            source_url="",
        )
        return Decimal(amount).quantize(_MONEY, rounding=ROUND_HALF_UP), dummy
    if code not in SUPPORTED_FX:
        raise BnrRateError(f"Conversia automată este disponibilă doar pentru EUR (ai selectat {code}).")
    rate = get_rate(code)
    ron = (Decimal(amount) * rate.ron_per_unit).quantize(_MONEY, rounding=ROUND_HALF_UP)
    return ron, rate


def rate_public_dict(rate: FxRate) -> dict:
    source = rate.source or "BNR"
    label = {
        "BNR": "BNR (Banca Națională a României)",
        "ECB": "ECB (fallback — Banca Centrală Europeană)",
    }.get(source, source)
    return {
        "currency": rate.currency,
        "rate": float(rate.ron_per_unit),
        "rate_raw": float(rate.rate),
        "multiplier": rate.multiplier,
        "rate_date": rate.rate_date.isoformat(),
        "source": source,
        "source_label": label,
        "source_url": rate.source_url or BNR_DAILY_URL,
    }
