"""initial schema

Revision ID: 003_ha_user
Revises: 002_app_config
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa

revision = "003_ha_user"
down_revision = "002_app_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("ha_user_id", sa.String(length=64), nullable=True))
        batch.create_index("ix_users_ha_user_id", ["ha_user_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_ha_user_id")
        batch.drop_column("ha_user_id")
