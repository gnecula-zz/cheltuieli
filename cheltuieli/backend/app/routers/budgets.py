from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models import Budget, Expense, User
from app.routers.expenses import month_bounds, visible_query
from app.schemas import BudgetPublic, BudgetSaveRequest

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetPublic])
def list_budgets(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BudgetPublic]:
    start, end = month_bounds(year, month)
    expenses = visible_query(db, user).filter(Expense.date >= start, Expense.date < end).all()
    spent: dict[int, Decimal] = {}
    for row in expenses:
        if row.category_id:
            spent[row.category_id] = spent.get(row.category_id, Decimal("0")) + row.amount
    rows = (
        db.query(Budget)
        .options(joinedload(Budget.category))
        .filter(Budget.year == year, Budget.month == month)
        .all()
    )
    return [
        BudgetPublic(
            id=row.id,
            category_id=row.category_id,
            year=row.year,
            month=row.month,
            amount=row.amount,
            category_name=row.category.name if row.category else "",
            spent=spent.get(row.category_id, Decimal("0")),
        )
        for row in rows
    ]


@router.put("", response_model=list[BudgetPublic])
def save_budgets(
    payload: BudgetSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[BudgetPublic]:
    existing = {
        row.category_id: row
        for row in db.query(Budget).filter(Budget.year == payload.year, Budget.month == payload.month).all()
    }
    seen: set[int] = set()
    for item in payload.items:
        seen.add(item.category_id)
        if item.category_id in existing:
            existing[item.category_id].amount = item.amount
        else:
            db.add(Budget(category_id=item.category_id, year=payload.year, month=payload.month, amount=item.amount))
    for category_id, row in existing.items():
        if category_id not in seen:
            db.delete(row)
    db.commit()
    return list_budgets(payload.year, payload.month, db, user)
