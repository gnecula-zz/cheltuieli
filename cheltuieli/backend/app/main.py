from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.addon_options import apply_addon_options, apply_ai_options
from app.config import settings
from app.database import Base, SessionLocal, engine, ensure_sqlite_schema
from app.routers import auth, budgets, categories, documents, expenses, reports, settings as settings_router, users
from app.seed import seed_categories
from app.services.ai import get_or_create_config
from app.spa import frontend_root, spa_file

addon_opts = apply_addon_options()


def run_migrations() -> None:
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        ensure_sqlite_schema()
        return
    from alembic import command
    from alembic.config import Config

    ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(ini))
    command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    run_migrations()
    db = SessionLocal()
    try:
        seed_categories(db)
        get_or_create_config(db)
        apply_ai_options(db, addon_opts)
    finally:
        db.close()
    yield


app = FastAPI(title="Cheltuieli", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(budgets.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "auth_mode": "homeassistant" if settings.is_homeassistant else "local"}


if frontend_root() is not None:

    @app.get("/{full_path:path}")
    def spa(request: Request, full_path: str):
        return spa_file(request, full_path)
