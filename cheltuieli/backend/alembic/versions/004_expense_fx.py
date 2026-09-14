"""expense FX fields for BNR conversion

Revision ID: 004_expense_fx
Revises: 003_ha_user
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa

revision = "004_expense_fx"
down_revision = "003_ha_user"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("expenses") as batch:
        batch.add_column(sa.Column("original_amount", sa.Numeric(12, 2), nullable=True))
        batch.add_column(sa.Column("original_currency", sa.String(length=8), nullable=True))
        batch.add_column(sa.Column("exchange_rate", sa.Numeric(12, 6), nullable=True))
        batch.add_column(sa.Column("exchange_rate_date", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("expenses") as batch:
        batch.drop_column("exchange_rate_date")
        batch.drop_column("exchange_rate")
        batch.drop_column("original_currency")
        batch.drop_column("original_amount")
