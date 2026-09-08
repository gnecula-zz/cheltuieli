"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="membru"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("icon", sa.String(length=16), nullable=False, server_default="•"),
        sa.Column("color", sa.String(length=16), nullable=False, server_default="#3F6F5B"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_categories_name", "categories", ["name"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("doc_type", sa.String(length=20), nullable=False, server_default="necunoscut"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="processed"),
        sa.Column("method", sa.String(length=30), nullable=False, server_default="local_text"),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("extraction_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("warning", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="RON"),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("merchant", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("description", sa.String(length=400), nullable=False, server_default=""),
        sa.Column("vat_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("payment_method", sa.String(length=20), nullable=False, server_default="card"),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("invoice_number", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("cui", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_expenses_user_id", "expenses", ["user_id"])
    op.create_index("ix_expenses_date", "expenses", ["date"])

    op.create_table(
        "budgets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.UniqueConstraint("category_id", "year", "month", name="uq_budget_cat_month"),
    )


def downgrade() -> None:
    op.drop_table("budgets")
    op.drop_table("expenses")
    op.drop_table("documents")
    op.drop_table("categories")
    op.drop_table("users")
