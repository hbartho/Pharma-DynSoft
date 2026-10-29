"""Reconstitue les mouvements d'entrée (IN) des approvisionnements validés avant l'historisation.

Revision ID: 0002_supply_in_mvts
Revises: 0001_baseline
Create Date: 2026-06-29
"""
from alembic import op
from sqlalchemy import text

revision = "0002_supply_in_mvts"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().execute(text("""
        INSERT INTO stock_movements (id, product_id, movement_type, quantity, stock_after, reference_type, reference_id,
                                     agent_code, reason, validation_status, validated_by, validated_at, created_at, updated_at)
        SELECT gen_random_uuid(), si.product_id, 'IN', si.quantity, COALESCE(p.stock, 0), 'supply', s.id,
               COALESCE(s.validated_by, s.created_by),
               'Appro ' || s.supply_number || COALESCE(' - Lot ' || si.lot_number, '') || ' (historique reconstitué)',
               'validated', s.validated_by, s.validated_at,
               COALESCE(s.validated_at, s.created_at), COALESCE(s.validated_at, s.created_at)
        FROM supplies s
        JOIN supply_items si ON si.supply_id = s.id
        LEFT JOIN products p ON p.id = si.product_id
        WHERE s.is_validated
          AND si.quantity > 0
          AND NOT EXISTS (
              SELECT 1 FROM stock_movements m
              WHERE m.reference_id = s.id AND m.reference_type = 'supply' AND m.product_id = si.product_id
          )
    """))


def downgrade():
    op.get_bind().execute(text("DELETE FROM stock_movements WHERE reference_type = 'supply' AND reason LIKE '%(historique reconstitué)'"))
