"""app config for AI provider

Revision ID: 002_app_config
Revises: 001_initial
Create Date: 2026-09-07
"""

from alembic import op
import sqlalchemy as sa

revision = "002_app_config"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ai_provider", sa.String(length=40), nullable=False, server_default="openai"),
        sa.Column("ai_model", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("ai_api_key", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_table("app_config")
