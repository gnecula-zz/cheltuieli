from sqlalchemy.orm import Session

from app.models import Category

KEYWORD_MAP: list[tuple[str, list[str]]] = [
    (
        "Alimente",
        [
            "mega image",
            "kaufland",
            "lidl",
            "auchan",
            "carrefour",
            "profi",
            "penny",
            "cora",
            "selgros",
            "metro",
            "la doi pasi",
            "megaimage",
        ],
    ),
    ("Transport", ["uber", "bolt", "petrom", "omv", "rompetrol", "lukoil", "cfr", "stb", "rata", "parcaj", "parking"]),
    ("Utilități", ["enel", "eon", "engie", "digi", "vodafone", "orange", "telekom", "apa nova", "electrica", "gdf"]),
    ("Restaurante", ["mcdonald", "kfc", "starbucks", "pizza", "restaurant", "cafe", "cafenea", "springtime", "tucano"]),
    ("Sănătate", ["farmacie", "catena", "sensiblu", "help net", "dr. max", "spital", "clinic"]),
    ("Divertisment", ["netflix", "spotify", "cinema", "hbo", "disney", "youtube"]),
    ("Abonamente", ["netflix", "spotify", "youtube premium", "icloud", "google one", "microsoft 365"]),
    ("Îmbrăcăminte", ["zara", "h&m", "reserved", "pull&bear", "bershka", "ccc", "dejcman"]),
    ("Casă", ["dedeman", "leroy", "ikea", "hornbach", "altex", "emag casa"]),
    ("Taxe", ["anaf", "impozit", "taxa", "amenzi"]),
]


def suggest_category_id(db: Session, merchant: str, description: str = "") -> int | None:
    blob = f"{merchant} {description}".lower()
    names = {c.name: c.id for c in db.query(Category).all()}
    for category_name, keywords in KEYWORD_MAP:
        if category_name not in names:
            continue
        if any(keyword in blob for keyword in keywords):
            return names[category_name]
    return names.get("Altele")
