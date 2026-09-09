import json
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile
from pydantic import ValidationError
from sqlalchemy import exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.deps import get_current_user
from app.models import Category, Document, Expense, User
from app.routers.expenses import to_public, visible_query
from app.schemas import ConfirmImportRequest, DocumentExtractResponse, ExpensePublic, ExtractedItem
from app.services.ai import is_ai_configured
from app.services.extract import extract_file

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
MAX_BYTES = 20 * 1024 * 1024


def _parse_items(raw_json: str) -> list[ExtractedItem]:
    try:
        raw = json.loads(raw_json or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    items: list[ExtractedItem] = []
    for entry in raw:
        try:
            items.append(ExtractedItem.model_validate(entry))
        except ValidationError:
            continue
    return items


def _to_response(document: Document, db: Session) -> DocumentExtractResponse:
    items = _parse_items(document.extraction_json) if document.status == "processed" else []
    return DocumentExtractResponse(
        document_id=document.id,
        filename=document.filename,
        doc_type=document.doc_type,
        method=document.method,
        warning=document.warning,
        openai_configured=is_ai_configured(db),
        items=items,
        status=document.status,
    )


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"


def run_extract_job(document_id: int) -> None:
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if not document:
            return
        result = extract_file(Path(document.stored_path), document.filename, document.mime_type, db)
        document.doc_type = result["doc_type"]
        document.status = "processed"
        document.method = result["method"]
        document.raw_text = result.get("raw_text") or ""
        document.extraction_json = json.dumps(result.get("items") or [], ensure_ascii=False)
        document.warning = result.get("warning") or ""
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        document = db.get(Document, document_id)
        if document:
            document.status = "error"
            document.warning = str(exc)[:2000]
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=DocumentExtractResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentExtractResponse:
    filename = file.filename or "document.jpg"
    suffix = Path(filename).suffix.lower()
    if not suffix and (file.content_type or "").startswith("image/"):
        suffix = ".jpg"
        filename = f"{filename}{suffix}"
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Acceptăm PDF, JPG, PNG sau WEBP")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="Fișierul depășește 20 MB")

    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    stored_name = f"{user.id}_{uuid.uuid4().hex}{suffix}"
    stored_path = upload_root / stored_name
    stored_path.write_bytes(data)

    document = Document(
        user_id=user.id,
        filename=filename,
        stored_path=str(stored_path),
        mime_type=file.content_type or "application/octet-stream",
        doc_type="necunoscut",
        status="processing",
        method="",
        raw_text="",
        extraction_json="[]",
        warning="",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    background_tasks.add_task(run_extract_job, document.id)
    return _to_response(document, db)


@router.get("", response_model=list[DocumentExtractResponse])
def list_unsaved_documents(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DocumentExtractResponse]:
    _no_store(response)
    saved = exists().where(Expense.document_id == Document.id)
    rows = (
        db.query(Document)
        .filter(
            Document.user_id == user.id,
            Document.status == "processed",
            ~saved,
        )
        .order_by(Document.id.desc())
        .limit(15)
        .all()
    )
    return [_to_response(row, db) for row in rows]


@router.get("/{document_id}", response_model=DocumentExtractResponse)
def get_document(
    document_id: int,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentExtractResponse:
    _no_store(response)
    document = db.get(Document, document_id)
    if not document or (document.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Document inexistent")
    return _to_response(document, db)


@router.post("/{document_id}/confirm", response_model=list[ExpensePublic])
def confirm_document(
    document_id: int,
    payload: ConfirmImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ExpensePublic]:
    document = db.get(Document, document_id)
    if not document or (document.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Document inexistent")
    if document.status != "processed":
        raise HTTPException(status_code=400, detail="Documentul încă se procesează")

    created: list[Expense] = []
    for item in payload.items:
        if not item.selected:
            continue
        if item.amount is None or item.amount <= 0:
            continue
        category_id = item.category_id
        if category_id and db.get(Category, category_id) is None:
            category_id = None
        expense = Expense(
            user_id=user.id,
            category_id=category_id,
            document_id=document.id,
            amount=Decimal(item.amount),
            currency=(item.currency or "RON")[:8],
            date=item.date or date.today(),
            merchant=(item.merchant or "").strip()[:200],
            description=(item.description or "").strip()[:400],
            vat_amount=item.vat_amount,
            payment_method=item.payment_method if item.payment_method in {"card", "numerar"} else "card",
            is_shared=item.is_shared,
            source=item.source if item.source in {"manual", "bon", "extras", "factura"} else document.doc_type,
            invoice_number=(item.invoice_number or "").strip()[:80],
            cui=(item.cui or "").strip()[:20],
        )
        db.add(expense)
        created.append(expense)

    if not created:
        raise HTTPException(status_code=400, detail="Nu ai selectat nicio cheltuială validă (verifică suma).")

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Nu am putut salva cheltuiala. Verifică categoria și suma.") from exc
    ids = [row.id for row in created]
    rows = visible_query(db, user).filter(Expense.id.in_(ids)).all()
    return [to_public(row) for row in rows]
