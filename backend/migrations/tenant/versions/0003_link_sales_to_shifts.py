"""Rattache les ventes sans shift_id au shift du caissier ouvert au moment de la vente (ventes admin historiques).

Revision ID: 0003_sales_shift_link
Revises: 0002_supply_in_mvts
Create Date: 2026-06-30
"""
from alembic import op
from sqlalchemy import text

revision = "0003_sales_shift_link"
down_revision = "0002_supply_in_mvts"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(text("""
        UPDATE sales s
        SET shift_id = sh.id
        FROM shifts sh
        JOIN users u ON u.id = sh.user_id
        WHERE s.shift_id IS NULL
          AND s.agent_code = u.employee_code
          AND u.role::text <> 'ADMIN'
          AND s.created_at >= sh.started_at
          AND s.created_at <= COALESCE(sh.ended_at, NOW())
    """))


def downgrade():
    pass
