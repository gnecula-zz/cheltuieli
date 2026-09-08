from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Category, Expense, User
from app.schemas import CategoryCreate, CategoryPublic, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryPublic])
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[Category]:
    return db.query(Category).order_by(Category.sort_order, Category.name).all()


@router.post("", response_model=CategoryPublic)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Category:
    if db.query(Category).filter(Category.name == payload.name.strip()).first():
        raise HTTPException(status_code=400, detail="Categoria există deja")
    max_order = db.query(Category).count()
    category = Category(
        name=payload.name.strip(),
        icon=payload.icon,
        color=payload.color,
        sort_order=(max_order + 1) * 10,
        is_system=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryPublic)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> Category:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categorie inexistentă")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        data["name"] = data["name"].strip()
        exists = db.query(Category).filter(Category.name == data["name"], Category.id != category_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Categoria există deja")
    for key, value in data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Categorie inexistentă")
    in_use = db.query(Expense).filter(Expense.category_id == category_id).count()
    if in_use:
        raise HTTPException(status_code=400, detail="Categoria e folosită la cheltuieli")
    db.delete(category)
    db.commit()
    return {"ok": True}
