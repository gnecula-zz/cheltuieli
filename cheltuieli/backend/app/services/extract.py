from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
from PIL import Image
from sqlalchemy.orm import Session

from app.services.ai import call_vision, is_ai_configured
from app.services.categorize import suggest_category_id

MIN_TEXT_LEN = 80
MAX_VISION_PAGES = 4
IMAGE_MAX_SIDE = 1600

AMOUNT_RE = re.compile(
    r"(?<![\d.,])(-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|-?\d+(?:[.,]\d{2}))(?![\d])"
)
DATE_RE = re.compile(
    r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b|\b(\d{4})-(\d{2})-(\d{2})\b"
)
CUI_RE = re.compile(r"\b(?:CUI|CIF|C\.I\.F\.)[:\s]*([RO]{0,2}\d{6,10})\b", re.I)
INVOICE_RE = re.compile(
    r"(?:factura|factură|invoice|seria)[^\d]{0,20}(?:nr\.?|numărul)?\s*([A-Z0-9][-A-Z0-9/]{1,20})",
    re.I,
)

SYSTEM_PROMPT = """Ești un extractor de date financiare din documente românești (bon fiscal, factură, extras de cont).
Răspunde STRICT cu JSON, fără text în plus, în forma:
{
  "document_type": "bon" | "factura" | "extras" | "necunoscut",
  "items": [
    {
      "date": "YYYY-MM-DD" sau null,
      "merchant": "string",
      "description": "string",
      "amount": număr (cheltuială pozitivă),
      "currency": "RON" | "EUR" | "USD",
      "vat_amount": număr sau null,
      "invoice_number": "string",
      "cui": "string",
      "payment_method": "card" | "numerar"
    }
  ]
}
Reguli:
- Pentru extras de cont, include DOAR ieșirile (debit/cumpărări/plăți), nu încasările.
- Dacă sunt mai multe bonuri în imagine, un item separat pentru fiecare bon (nu le combina).
- amount este valoarea cheltuielii, pozitivă.
- Dacă e un bon sau o factură, un singur item cu totalul e suficient.
- Datele în format ISO. Dacă lipsește un câmp, folosește "" sau null.
"""


def parse_amount(raw: str) -> Decimal | None:
    text = raw.strip().replace("\xa0", "").replace(" ", "")
    if not text:
        return None
    if re.search(r",\d{1,2}$", text):
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return abs(value)


def parse_date(text: str) -> date | None:
    match = DATE_RE.search(text)
    if not match:
        return None
    try:
        if match.group(4):
            return date(int(match.group(4)), int(match.group(5)), int(match.group(6)))
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 100:
            year += 2000
        return date(year, month, day)
    except ValueError:
        return None


def detect_doc_type(text: str, filename: str) -> str:
    blob = f"{filename} {text}".lower()
    if any(word in blob for word in ("extras de cont", "extras", "iban", "sold initial", "sold final", "debit", "credit")):
        if "factura" not in blob[:400]:
            return "extras"
    if any(word in blob for word in ("factura", "factură", "invoice", "total de plata")):
        return "factura"
    if any(word in blob for word in ("bon fiscal", "bon", "casa de marcat", "anaf")):
        return "bon"
    return "necunoscut"


def _guess_payment(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ("numerar", "cash", "cash lei")):
        return "numerar"
    return "card"


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if len(cleaned) >= 3 and not cleaned.lower().startswith("%pdf"):
            return cleaned[:200]
    return ""


def parse_text_document(text: str, filename: str) -> tuple[str, list[dict]]:
    doc_type = detect_doc_type(text, filename)
    cui_match = CUI_RE.search(text)
    invoice_match = INVOICE_RE.search(text)
    cui = cui_match.group(1).upper() if cui_match else ""
    invoice_number = invoice_match.group(1) if invoice_match else ""
    payment = _guess_payment(text)
    found_date = parse_date(text)
    merchant = _first_nonempty_line(text)

    if doc_type == "extras":
        items = _parse_statement_lines(text, payment)
        return doc_type, items

    amount = _find_total(text)
    vat = _find_vat(text)
    item = {
        "date": found_date.isoformat() if found_date else None,
        "merchant": merchant,
        "description": "Factură" if doc_type == "factura" else "Bon fiscal",
        "amount": float(amount) if amount is not None else None,
        "currency": "EUR" if " eur" in text.lower() else "RON",
        "vat_amount": float(vat) if vat is not None else None,
        "invoice_number": invoice_number,
        "cui": cui,
        "payment_method": payment,
        "source": "factura" if doc_type == "factura" else "bon",
    }
    return doc_type, [item]


def _find_total(text: str) -> Decimal | None:
    patterns = [
        r"(?:total de plat[aă]|total plata|total general|total cu tva|suma de plata|total)[^\d]{0,20}(-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|-?\d+(?:[.,]\d{2}))",
        r"(?:total)[:\s]+(-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|-?\d+(?:[.,]\d{2}))",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.I)
        if matches:
            parsed = parse_amount(matches[-1])
            if parsed is not None:
                return parsed
    amounts = [parse_amount(m) for m in AMOUNT_RE.findall(text)]
    amounts = [a for a in amounts if a is not None and a > 0]
    return max(amounts) if amounts else None


def _find_vat(text: str) -> Decimal | None:
    match = re.search(
        r"(?:tva|valoare tva)[^\d]{0,20}(-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|-?\d+(?:[.,]\d{2}))",
        text,
        flags=re.I,
    )
    if match:
        return parse_amount(match.group(1))
    return None


def _parse_statement_lines(text: str, payment: str) -> list[dict]:
    items: list[dict] = []
    amount_on_line = re.compile(
        r"(-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2})\s*(?:RON|EUR|USD|lei)?",
        re.I,
    )
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if len(line) < 8:
            continue
        lower = line.lower()
        if any(
            word in lower
            for word in (
                "sold",
                "iban",
                "extras de cont",
                "extras cont",
                "credit",
                "incasare",
                "încasare",
                "virament primit",
            )
        ):
            if "debit" not in lower:
                continue
        line_date = parse_date(line)
        amount_match = amount_on_line.findall(line)
        if not line_date or not amount_match:
            continue
        amount = parse_amount(amount_match[-1])
        if amount is None or amount <= 0:
            continue
        merchant = DATE_RE.sub("", line)
        merchant = amount_on_line.sub("", merchant)
        merchant = re.sub(r"\b(RON|EUR|USD|debit|card|lei)\b", "", merchant, flags=re.I)
        merchant = re.sub(r"\s+", " ", merchant).strip(" -–|")[:200]
        if not merchant:
            continue
        items.append(
            {
                "date": line_date.isoformat(),
                "merchant": merchant,
                "description": "Tranzacție extras",
                "amount": float(amount),
                "currency": "RON",
                "vat_amount": None,
                "invoice_number": "",
                "cui": "",
                "payment_method": payment,
                "source": "extras",
            }
        )
    return items[:200]


def extract_pdf_text(path: Path) -> str:
    chunks: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:20]:
            chunks.append(page.extract_text() or "")
    return "\n".join(chunks).strip()


def rasterize_pdf(path: Path, max_pages: int = MAX_VISION_PAGES) -> list[Image.Image]:
    pdf = pdfium.PdfDocument(str(path))
    images: list[Image.Image] = []
    try:
        count = min(len(pdf), max_pages)
        for index in range(count):
            page = pdf[index]
            bitmap = page.render(scale=2)
            images.append(bitmap.to_pil().convert("RGB"))
    finally:
        pdf.close()
    return images


def prepare_image(path: Path) -> Image.Image:
    image = Image.open(path)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    elif image.mode == "L":
        image = image.convert("RGB")
    image.thumbnail((IMAGE_MAX_SIDE, IMAGE_MAX_SIDE))
    return image


def normalize_items(raw_items: list[dict], fallback_source: str, db: Session) -> list[dict]:
    normalized: list[dict] = []
    for raw in raw_items:
        amount = raw.get("amount")
        try:
            amount_dec = Decimal(str(amount)) if amount not in (None, "") else None
        except (InvalidOperation, TypeError, ValueError):
            amount_dec = None
        if amount_dec is not None:
            amount_dec = abs(amount_dec)
        vat = raw.get("vat_amount")
        try:
            vat_dec = Decimal(str(vat)) if vat not in (None, "") else None
        except (InvalidOperation, TypeError, ValueError):
            vat_dec = None
        item_date = raw.get("date")
        parsed_date: date | None = None
        if isinstance(item_date, date):
            parsed_date = item_date
        elif isinstance(item_date, str) and item_date:
            try:
                parsed_date = datetime.strptime(item_date[:10], "%Y-%m-%d").date()
            except ValueError:
                parsed_date = parse_date(item_date)
        merchant = str(raw.get("merchant") or "")[:200]
        description = str(raw.get("description") or "")[:400]
        source = str(raw.get("source") or fallback_source)
        category_id = suggest_category_id(db, merchant, description)
        normalized.append(
            {
                "date": parsed_date.isoformat() if parsed_date else None,
                "merchant": merchant,
                "description": description,
                "amount": float(amount_dec) if amount_dec is not None else None,
                "currency": str(raw.get("currency") or "RON")[:8],
                "vat_amount": float(vat_dec) if vat_dec is not None else None,
                "payment_method": str(raw.get("payment_method") or "card"),
                "is_shared": bool(raw.get("is_shared", False)),
                "source": source if source in {"manual", "bon", "extras", "factura"} else fallback_source,
                "category_id": category_id,
                "invoice_number": str(raw.get("invoice_number") or "")[:80],
                "cui": str(raw.get("cui") or "")[:20],
                "selected": True,
            }
        )
    return normalized


def extract_file(path: Path, filename: str, mime: str, db: Session) -> dict:
    suffix = path.suffix.lower()
    is_pdf = suffix == ".pdf" or "pdf" in mime
    is_image = suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"} or mime.startswith("image/")

    if is_pdf:
        text = extract_pdf_text(path)
        if len(text) >= MIN_TEXT_LEN:
            doc_type, items = parse_text_document(text, filename)
            return {
                "doc_type": doc_type,
                "method": "local_text",
                "raw_text": text[:20000],
                "warning": "",
                "items": normalize_items(items, "extras" if doc_type == "extras" else doc_type, db),
            }
        if not is_ai_configured(db):
            return {
                "doc_type": "necunoscut",
                "method": "manual",
                "raw_text": text,
                "warning": "PDF-ul pare scanat (fără text). Configurează un agent AI și cheia API în Setări sau completează manual.",
                "items": normalize_items(
                    [{"merchant": filename, "description": "", "source": "factura"}],
                    "factura",
                    db,
                ),
            }
        images = rasterize_pdf(path)
        result = call_vision(db, SYSTEM_PROMPT, images=images)
        doc_type = result.get("document_type") or "necunoscut"
        return {
            "doc_type": doc_type,
            "method": "ai_vision",
            "raw_text": text,
            "warning": "",
            "items": normalize_items(result.get("items") or [], doc_type if doc_type != "necunoscut" else "bon", db),
        }

    if is_image:
        if not is_ai_configured(db):
            return {
                "doc_type": "bon",
                "method": "manual",
                "raw_text": "",
                "warning": "Pozele de bonuri necesită un agent AI configurat în Setări. Completează datele manual după încărcare.",
                "items": normalize_items(
                    [{"merchant": "", "description": "Bon fiscal", "source": "bon", "date": date.today().isoformat()}],
                    "bon",
                    db,
                ),
            }
        image = prepare_image(path)
        result = call_vision(db, SYSTEM_PROMPT, images=[image])
        doc_type = result.get("document_type") or "bon"
        return {
            "doc_type": doc_type,
            "method": "ai_vision",
            "raw_text": "",
            "warning": "",
            "items": normalize_items(result.get("items") or [], doc_type if doc_type != "necunoscut" else "bon", db),
        }

    raise ValueError("Format nesuportat. Încarcă o imagine (JPG/PNG) sau un PDF.")
