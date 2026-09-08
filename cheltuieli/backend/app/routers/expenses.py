from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models import Expense, User
from app.schemas import ExpenseCreate, ExpensePublic, ExpenseUpdate

router = APIRouter(prefix="/expenses", tags=["expenses"])


def visible_query(db: Session, user: User, user_id: int | None = None):
    query = db.query(Expense).options(joinedload(Expense.user), joinedload(Expense.category))
    if user.role == "admin":
        if user_id:
            query = query.filter(Expense.user_id == user_id)
        return query
    return query.filter(or_(Expense.user_id == user.id, Expense.is_shared.is_(True)))


def to_public(expense: Expense) -> ExpensePublic:
    return ExpensePublic(
        id=expense.id,
        user_id=expense.user_id,
        category_id=expense.category_id,
        document_id=expense.document_id,
        amount=expense.amount,
        currency=expense.currency,
        date=expense.date,
        merchant=expense.merchant,
        description=expense.description,
        vat_amount=expense.vat_amount,
        payment_method=expense.payment_method,
        is_shared=expense.is_shared,
        source=expense.source,
        invoice_number=expense.invoice_number,
        cui=expense.cui,
        created_at=expense.created_at,
        user_name=expense.user.name if expense.user else "",
        category_name=expense.category.name if expense.category else None,
        category_color=expense.category.color if expense.category else None,
        category_icon=expense.category.icon if expense.category else None,
    )


def can_edit(expense: Expense, user: User) -> bool:
    return user.role == "admin" or expense.user_id == user.id


@router.get("", response_model=list[ExpensePublic])
def list_expenses(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    category_id: int | None = None,
    user_id: int | None = None,
    shared: bool | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ExpensePublic]:
    query = visible_query(db, user, user_id)
    if date_from:
        query = query.filter(Expense.date >= date_from)
    if date_to:
        query = query.filter(Expense.date <= date_to)
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if shared is True:
        query = query.filter(Expense.is_shared.is_(True))
    if shared is False:
        query = query.filter(Expense.is_shared.is_(False))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(Expense.merchant.ilike(like), Expense.description.ilike(like)))
    rows = query.order_by(Expense.date.desc(), Expense.id.desc()).limit(1000).all()
    return [to_public(row) for row in rows]


@router.post("", response_model=ExpensePublic)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExpensePublic:
    expense = Expense(
        user_id=user.id,
        category_id=payload.category_id,
        amount=payload.amount,
        currency=payload.currency or "RON",
        date=payload.date,
        merchant=payload.merchant.strip(),
        description=payload.description.strip(),
        vat_amount=payload.vat_amount,
        payment_method=payload.payment_method if payload.payment_method in {"card", "numerar"} else "card",
        is_shared=payload.is_shared,
        source=payload.source if payload.source in {"manual", "bon", "extras", "factura"} else "manual",
        invoice_number=payload.invoice_number.strip(),
        cui=payload.cui.strip(),
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    expense = visible_query(db, user).filter(Expense.id == expense.id).one()
    return to_public(expense)


@router.patch("/{expense_id}", response_model=ExpensePublic)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExpensePublic:
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Cheltuiala nu există")
    if not can_edit(expense, user):
        raise HTTPException(status_code=403, detail="Nu poți edita cheltuiala altcuiva")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(expense, key, value)
    db.commit()
    expense = visible_query(db, user).filter(Expense.id == expense.id).one()
    return to_public(expense)


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    expense = db.get(Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Cheltuiala nu există")
    if not can_edit(expense, user):
        raise HTTPException(status_code=403, detail="Nu poți șterge cheltuiala altcuiva")
    db.delete(expense)
    db.commit()
    return {"ok": True}


def month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def sum_amount(rows: list[Expense]) -> Decimal:
    return sum((row.amount for row in rows), Decimal("0"))
