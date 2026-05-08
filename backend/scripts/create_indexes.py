"""
Script pour créer les index de base de données pour optimiser les performances
"""
import os
import sys
sys.path.insert(0, '/app/backend')

from database.config import get_database_url
from sqlalchemy import create_engine, text

SCHEMA = "public"

INDEXES = [
    # Index sur sales
    ("idx_sales_created_at", "sales", "created_at DESC"),
    ("idx_sales_customer_id", "sales", "customer_id"),
    ("idx_sales_agent_code", "sales", "agent_code"),
    ("idx_sales_payment_method", "sales", "payment_method"),
    ("idx_sales_status", "sales", "status"),
    ("idx_sales_sale_number", "sales", "sale_number"),
    
    # Index composé pour les requêtes courantes
    ("idx_sales_date_agent", "sales", "created_at DESC, agent_code"),
    
    # Index sur sale_items
    ("idx_sale_items_sale_id", "sale_items", "sale_id"),
    ("idx_sale_items_product_id", "sale_items", "product_id"),
    
    # Index sur products
    ("idx_products_name", "products", "name"),
    ("idx_products_barcode", "products", "barcode"),
    ("idx_products_category_id", "products", "category_id"),
    ("idx_products_is_active", "products", "is_active"),
    
    # Index sur customers
    ("idx_customers_name", "customers", "name"),
    ("idx_customers_phone", "customers", "phone"),
    ("idx_customers_is_active", "customers", "is_active"),
    
    # Index sur debts
    ("idx_debts_customer_id", "debts", "customer_id"),
    ("idx_debts_status", "debts", "status"),
    ("idx_debts_due_date", "debts", "due_date"),
    
    # Index sur stock_movements
    ("idx_stock_movements_product_id", "stock_movements", "product_id"),
    ("idx_stock_movements_created_at", "stock_movements", "created_at DESC"),
    
    # Index sur supplies
    ("idx_supplies_supplier_id", "supplies", "supplier_id"),
    ("idx_supplies_status", "supplies", "status"),
    ("idx_supplies_created_at", "supplies", "created_at DESC"),
]

def main():
    url = get_database_url()
    engine = create_engine(url)
    
    print("Création des index de base de données...\n")
    
    created = 0
    skipped = 0
    errors = 0
    
    with engine.connect() as conn:
        for idx_name, table, columns in INDEXES:
            try:
                # Vérifier si l'index existe déjà
                check = conn.execute(text(f"""
                    SELECT 1 FROM pg_indexes 
                    WHERE schemaname = '{SCHEMA}' 
                    AND indexname = '{idx_name}'
                """)).fetchone()
                
                if check:
                    print(f"  ⏭️  {idx_name} (existe déjà)")
                    skipped += 1
                    continue
                
                # Créer l'index
                sql = f"CREATE INDEX {idx_name} ON {SCHEMA}.{table} ({columns})"
                conn.execute(text(sql))
                conn.commit()
                print(f"  ✅ {idx_name} créé sur {table}({columns})")
                created += 1
                
            except Exception as e:
                print(f"  ❌ {idx_name}: {str(e)[:50]}")
                errors += 1
                conn.rollback()
    
    print(f"\n📊 Résumé: {created} créés, {skipped} existants, {errors} erreurs")

if __name__ == "__main__":
    main()
