import json
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Document, Expense, User
from app.routers.expenses import to_public, visible_query
from app.schemas import ConfirmImportRequest, DocumentExtractResponse, ExpensePublic, ExtractedItem
from app.services.ai import is_ai_configured
from app.services.extract import extract_file

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_SUFFIXES = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
MAX_BYTES = 20 * 1024 * 1024


@router.post("/upload", response_model=DocumentExtractResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentExtractResponse:
    filename = file.filename or "document"
    suffix = Path(filename).suffix.lower()
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

    try:
        result = extract_file(stored_path, filename, file.content_type or "", db)
    except ValueError as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail=f"Extragerea a eșuat: {exc}") from exc

    document = Document(
        user_id=user.id,
        filename=filename,
        stored_path=str(stored_path),
        mime_type=file.content_type or "application/octet-stream",
        doc_type=result["doc_type"],
        status="processed",
        method=result["method"],
        raw_text=result.get("raw_text") or "",
        extraction_json=json.dumps(result.get("items") or [], ensure_ascii=False),
        warning=result.get("warning") or "",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    items = [ExtractedItem.model_validate(item) for item in result.get("items") or []]
    return DocumentExtractResponse(
        document_id=document.id,
        filename=filename,
        doc_type=document.doc_type,
        method=document.method,
        warning=document.warning,
        openai_configured=is_ai_configured(db),
        items=items,
    )


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

    created: list[Expense] = []
    for item in payload.items:
        if not item.selected:
            continue
        if item.amount is None or item.amount <= 0:
            continue
        expense = Expense(
            user_id=user.id,
            category_id=item.category_id,
            document_id=document.id,
            amount=Decimal(item.amount),
            currency=item.currency or "RON",
            date=item.date or date.today(),
            merchant=(item.merchant or "").strip(),
            description=(item.description or "").strip(),
            vat_amount=item.vat_amount,
            payment_method=item.payment_method if item.payment_method in {"card", "numerar"} else "card",
            is_shared=item.is_shared,
            source=item.source if item.source in {"manual", "bon", "extras", "factura"} else document.doc_type,
            invoice_number=(item.invoice_number or "").strip(),
            cui=(item.cui or "").strip(),
        )
        db.add(expense)
        created.append(expense)

    if not created:
        raise HTTPException(status_code=400, detail="Nu ai selectat nicio cheltuială validă")

    db.commit()
    ids = [row.id for row in created]
    rows = visible_query(db, user).filter(Expense.id.in_(ids)).all()
    return [to_public(row) for row in rows]
