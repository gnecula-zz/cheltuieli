from sqlalchemy.orm import Session

from app.models import Category

DEFAULT_CATEGORIES = [
    ("Alimente", "🛒", "#3F6F5B", 10),
    ("Transport", "🚌", "#2F5D8C", 20),
    ("Utilități", "💡", "#C47B2C", 30),
    ("Casă", "🏠", "#6B4F3A", 40),
    ("Sănătate", "💊", "#9B3D4A", 50),
    ("Restaurante", "🍽️", "#B85C38", 60),
    ("Divertisment", "🎬", "#6A4C93", 70),
    ("Educație", "📚", "#3D6B8C", 80),
    ("Îmbrăcăminte", "👕", "#4A7C6D", 90),
    ("Abonamente", "📱", "#3A6B7C", 100),
    ("Taxe", "🏛️", "#5C5C5C", 110),
    ("Altele", "📦", "#7A6A53", 120),
]


def seed_categories(db: Session) -> None:
    if db.query(Category).count() > 0:
        return
    for name, icon, color, order in DEFAULT_CATEGORIES:
        db.add(Category(name=name, icon=icon, color=color, sort_order=order, is_system=True))
    db.commit()
