from collections import defaultdict
from datetime import date
from decimal import Decimal
from io import StringIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models import Budget, Expense, User
from app.routers.expenses import month_bounds, visible_query

router = APIRouter(prefix="/reports", tags=["reports"])


def _filter_month(db: Session, user: User, year: int, month: int | None, user_id: int | None):
    query = visible_query(db, user, user_id)
    if month:
        start, end = month_bounds(year, month)
        return query.filter(Expense.date >= start, Expense.date < end)
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    return query.filter(Expense.date >= start, Expense.date < end)


@router.get("/summary")
def summary(
    year: int = Query(...),
    month: int | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    rows = _filter_month(db, user, year, month, user_id).all()
    total = sum((r.amount for r in rows), Decimal("0"))
    shared = sum((r.amount for r in rows if r.is_shared), Decimal("0"))
    personal = total - shared
    by_category: dict[str, dict] = {}
    for row in rows:
        name = row.category.name if row.category else "Fără categorie"
        color = row.category.color if row.category else "#7A6A53"
        icon = row.category.icon if row.category else "•"
        bucket = by_category.setdefault(name, {"name": name, "color": color, "icon": icon, "total": Decimal("0")})
        bucket["total"] += row.amount

    by_person: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_merchant: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in rows:
        by_person[row.user.name] += row.amount
        merchant = row.merchant or "(fără comerciant)"
        by_merchant[merchant] += row.amount

    budgets = []
    if month:
        budget_rows = (
            db.query(Budget)
            .options(joinedload(Budget.category))
            .filter(Budget.year == year, Budget.month == month)
            .all()
        )
        spent_by_cat: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
        for row in rows:
            if row.category_id:
                spent_by_cat[row.category_id] += row.amount
        for budget in budget_rows:
            budgets.append(
                {
                    "category_id": budget.category_id,
                    "category_name": budget.category.name if budget.category else "",
                    "amount": float(budget.amount),
                    "spent": float(spent_by_cat.get(budget.category_id, Decimal("0"))),
                }
            )

    return {
        "year": year,
        "month": month,
        "count": len(rows),
        "total": float(total),
        "shared": float(shared),
        "personal": float(personal),
        "by_category": [
            {**item, "total": float(item["total"])}
            for item in sorted(by_category.values(), key=lambda x: x["total"], reverse=True)
        ],
        "by_person": [
            {"name": name, "total": float(total_p)}
            for name, total_p in sorted(by_person.items(), key=lambda x: x[1], reverse=True)
        ],
        "by_merchant": [
            {"name": name, "total": float(total_m)}
            for name, total_m in sorted(by_merchant.items(), key=lambda x: x[1], reverse=True)[:12]
        ],
        "budgets": budgets,
    }


@router.get("/export.csv")
def export_csv(
    year: int = Query(...),
    month: int | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    rows = _filter_month(db, user, year, month, user_id).order_by(Expense.date, Expense.id).all()
    buffer = StringIO()
    buffer.write("Data,Comerciant,Descriere,Categorie,Suma,Moneda,TVA,Plata,Tip,Comuna,Persoana,Sursa,Factura,CUI\n")
    for row in rows:
        cells = [
            row.date.isoformat(),
            _csv(row.merchant),
            _csv(row.description),
            _csv(row.category.name if row.category else ""),
            f"{row.amount:.2f}",
            row.currency,
            f"{row.vat_amount:.2f}" if row.vat_amount is not None else "",
            row.payment_method,
            _csv("comuna" if row.is_shared else "personala"),
            _csv(row.user.name if row.user else ""),
            row.source,
            _csv(row.invoice_number),
            _csv(row.cui),
        ]
        buffer.write(",".join(cells) + "\n")
    filename = f"cheltuieli-{year}{f'-{month:02d}' if month else ''}.csv"
    payload = buffer.getvalue().encode("utf-8-sig")
    return StreamingResponse(
        iter([payload]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _csv(value: str) -> str:
    text = (value or "").replace('"', '""')
    return f'"{text}"'
