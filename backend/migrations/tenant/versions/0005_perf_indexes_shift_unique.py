"""Index de performance sur les requêtes fréquentes + un seul shift ouvert par utilisateur.

Revision ID: 0005_perf_indexes
Revises: 0004_sale_payment_details
Create Date: 2026-06-30
"""
from alembic import op
from sqlalchemy import text

revision = "0005_perf_indexes"
down_revision = "0004_sale_payment_details"
branch_labels = None
depends_on = None

INDEXES = [
    ("idx_sale_shift", "sales", "shift_id"),
    ("idx_sale_customer", "sales", "customer_id"),
    ("idx_sale_status_date", "sales", "status, created_at"),
    ("idx_sale_agent", "sales", "agent_code"),
    ("idx_sale_item_sale", "sale_items", "sale_id"),
    ("idx_sale_item_product", "sale_items", "product_id"),
    ("idx_supply_item_supply", "supply_items", "supply_id"),
    ("idx_supply_item_product", "supply_items", "product_id"),
    ("idx_supply_item_expiration", "supply_items", "expiration_date"),
    ("idx_shift_user_started", "shifts", "user_id, started_at"),
    ("idx_debt_customer_status", "debts", "customer_id, status"),
    ("idx_debt_status_due", "debts", "status, due_date"),
    ("idx_movement_product_date", "stock_movements", "product_id, created_at"),
    ("idx_movement_reference", "stock_movements", "reference_id"),
    ("idx_movement_type_status", "stock_movements", "movement_type, validation_status"),
    ("idx_inventory_item_session", "inventory_items", "session_id"),
    ("idx_supplier_debt_supplier", "supplier_debts", "supplier_id"),
    ("idx_product_category", "products", "category_id"),
]


def upgrade():
    bind = op.get_bind()
    for name, table, cols in INDEXES:
        bind.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})"))
    # Doublons éventuels : on ne garde ouvert que le shift le plus récent de chaque utilisateur
    bind.execute(text("""
        UPDATE shifts s SET is_active = FALSE, ended_at = COALESCE(s.ended_at, NOW())
        WHERE s.is_active = TRUE AND EXISTS (
            SELECT 1 FROM shifts o
            WHERE o.user_id = s.user_id AND o.is_active = TRUE AND o.id <> s.id
              AND (o.started_at > s.started_at OR (o.started_at = s.started_at AND o.id > s.id))
        )
    """))
    bind.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_shift_active_user ON shifts (user_id) WHERE is_active"))


def downgrade():
    bind = op.get_bind()
    bind.execute(text("DROP INDEX IF EXISTS uq_shift_active_user"))
    for name, _t, _c in INDEXES:
        bind.execute(text(f"DROP INDEX IF EXISTS {name}"))
