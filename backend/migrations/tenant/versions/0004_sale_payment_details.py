"""Ajoute sales.payment_details (références Mobile Money / chèque / carte d'un paiement unique).

Revision ID: 0004_sale_payment_details
Revises: 0003_sales_shift_link
Create Date: 2026-06-30
"""
from alembic import op
from sqlalchemy import text

revision = "0004_sale_payment_details"
down_revision = "0003_sales_shift_link"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(text("ALTER TABLE sales ADD COLUMN IF NOT EXISTS payment_details JSON"))


def downgrade():
    op.get_bind().execute(text("ALTER TABLE sales DROP COLUMN IF EXISTS payment_details"))
