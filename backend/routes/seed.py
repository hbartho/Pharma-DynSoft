"""
Database Seed Routes - Reset and populate with test data
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone, timedelta
from auth import require_role
from sqlalchemy import text
import uuid
import random

router = APIRouter(prefix="/seed", tags=["Seed"])

# Import repositories and database
from database.repositories import (
    ProductRepository, CategoryRepository, CustomerRepository,
    SupplierRepository, SettingsRepository
)
from database.config import db_manager

def generate_id():
    return str(uuid.uuid4())

@router.post("/reset-and-seed")
async def reset_and_seed_database(current_user: dict = Depends(require_role(["admin"]))):
    """
    Reset all data and seed with coherent test data.
    WARNING: This will delete ALL existing data!
    """
    try:
        results = {
            "deleted": {},
            "created": {},
            "errors": []
        }
        
        # ========== STEP 1: DELETE ALL DATA VIA SQL ==========
        session = db_manager.get_tenant_session("default")
        with session as s:
            # Order matters due to foreign keys - delete in reverse dependency order
            tables_to_clear = [
                "sale_items",
                "sales",
                "supply_items",
                "supplies",
                "debts",
                "stock_movements",
                "pending_sales",
                "shifts",
                "prescriptions",
                "sale_returns",
                "products",
                "customers",
                "suppliers",
                "categories"
            ]
            
            for table in tables_to_clear:
                try:
                    result = s.execute(text(f"DELETE FROM {table}"))
                    results["deleted"][table] = result.rowcount
                    s.commit()  # Commit each delete separately to avoid transaction issues
                except Exception as e:
                    s.rollback()
                    results["errors"].append(f"Delete {table}: {str(e)[:100]}")
        
        # ========== STEP 2: CREATE TEST DATA ==========
        now = datetime.now(timezone.utc)
        cat_repo = CategoryRepository()
        supplier_repo = SupplierRepository()
        customer_repo = CustomerRepository()
        product_repo = ProductRepository()
        settings_repo = SettingsRepository()
        
        # --- Categories ---
        categories_data = [
            {"id": generate_id(), "name": "Antalgiques", "description": "Médicaments contre la douleur", "coefficient": 1.35, "tva_rate": 0},
            {"id": generate_id(), "name": "Antibiotiques", "description": "Médicaments antibactériens", "coefficient": 1.40, "tva_rate": 0},
            {"id": generate_id(), "name": "Anti-inflammatoires", "description": "Médicaments anti-inflammatoires", "coefficient": 1.35, "tva_rate": 0},
            {"id": generate_id(), "name": "Vitamines", "description": "Compléments vitaminiques", "coefficient": 1.30, "tva_rate": 18},
            {"id": generate_id(), "name": "Dermatologie", "description": "Soins de la peau", "coefficient": 1.45, "tva_rate": 18},
            {"id": generate_id(), "name": "Hygiène", "description": "Produits d'hygiène", "coefficient": 1.25, "tva_rate": 18},
        ]
        
        created_categories = []
        for cat in categories_data:
            try:
                created = cat_repo.create(cat)
                created_categories.append(created)
            except Exception as e:
                results["errors"].append(f"Category {cat['name']}: {str(e)[:100]}")
        results["created"]["categories"] = len(created_categories)
        
        # --- Suppliers ---
        suppliers_data = [
            {"id": generate_id(), "name": "Pharma Distribution Guinée", "contact": "M. Diallo", "phone": "+224 622 11 22 33", "email": "contact@pdg.gn", "address": "Kaloum, Conakry"},
            {"id": generate_id(), "name": "MediStock Africa", "contact": "Mme Camara", "phone": "+224 621 44 55 66", "email": "commande@medistock.com", "address": "Matam, Conakry"},
            {"id": generate_id(), "name": "Laborex Guinée", "contact": "M. Barry", "phone": "+224 620 77 88 99", "email": "laborex@gn.com", "address": "Dixinn, Conakry"},
        ]
        
        created_suppliers = []
        for sup in suppliers_data:
            try:
                created = supplier_repo.create(sup)
                created_suppliers.append(created)
            except Exception as e:
                results["errors"].append(f"Supplier {sup['name']}: {str(e)[:100]}")
        results["created"]["suppliers"] = len(created_suppliers)
        
        # --- Customers ---
        customers_data = [
            {"id": generate_id(), "name": "Client Comptant", "phone": "+224 620 00 00 00", "email": "", "address": "Conakry", "max_debt_limit": 0, "notes": "Client par défaut pour ventes comptant"},
            {"id": generate_id(), "name": "Mamadou Diallo", "phone": "+224 621 11 11 11", "email": "mamadou.diallo@email.com", "address": "Ratoma, Conakry", "max_debt_limit": 500000, "notes": "Client fidèle"},
            {"id": generate_id(), "name": "Fatoumata Camara", "phone": "+224 622 22 22 22", "email": "fatou.camara@email.com", "address": "Matam, Conakry", "max_debt_limit": 300000, "notes": ""},
            {"id": generate_id(), "name": "Ibrahima Sow", "phone": "+224 623 33 33 33", "email": "", "address": "Dixinn, Conakry", "max_debt_limit": 0, "notes": "Pas de crédit autorisé"},
            {"id": generate_id(), "name": "Centre de Santé Matam", "phone": "+224 624 44 44 44", "email": "csmatam@sante.gn", "address": "Matam, Conakry", "max_debt_limit": 2000000, "notes": "Centre de santé partenaire"},
            {"id": generate_id(), "name": "Clinique Ambroise Paré", "phone": "+224 625 55 55 55", "email": "clinique.ap@email.com", "address": "Kaloum, Conakry", "max_debt_limit": 5000000, "notes": "Clinique privée"},
        ]
        
        created_customers = []
        for cust in customers_data:
            try:
                created = customer_repo.create(cust)
                created_customers.append(created)
            except Exception as e:
                results["errors"].append(f"Customer {cust['name']}: {str(e)[:100]}")
        results["created"]["customers"] = len(created_customers)
        
        # --- Products ---
        products_data = [
            # Antalgiques
            {"name": "Paracétamol 500mg", "category_id": created_categories[0]["id"], "barcode": "3400930000011", "purchase_price": 1500, "price": 2000, "stock": 200, "min_stock": 50},
            {"name": "Paracétamol 1000mg", "category_id": created_categories[0]["id"], "barcode": "3400930000012", "purchase_price": 2500, "price": 3500, "stock": 150, "min_stock": 40},
            {"name": "Doliprane Sirop Enfant", "category_id": created_categories[0]["id"], "barcode": "3400930000013", "purchase_price": 8000, "price": 11000, "stock": 80, "min_stock": 20},
            {"name": "Tramadol 50mg", "category_id": created_categories[0]["id"], "barcode": "3400930000014", "purchase_price": 15000, "price": 20000, "stock": 30, "min_stock": 10},
            
            # Antibiotiques
            {"name": "Amoxicilline 500mg", "category_id": created_categories[1]["id"], "barcode": "3400930000021", "purchase_price": 5000, "price": 7000, "stock": 100, "min_stock": 30},
            {"name": "Amoxicilline 1g", "category_id": created_categories[1]["id"], "barcode": "3400930000022", "purchase_price": 8000, "price": 11000, "stock": 80, "min_stock": 25},
            {"name": "Azithromycine 250mg", "category_id": created_categories[1]["id"], "barcode": "3400930000023", "purchase_price": 12000, "price": 17000, "stock": 50, "min_stock": 15},
            {"name": "Ciprofloxacine 500mg", "category_id": created_categories[1]["id"], "barcode": "3400930000024", "purchase_price": 6000, "price": 8500, "stock": 60, "min_stock": 20},
            
            # Anti-inflammatoires
            {"name": "Ibuprofène 400mg", "category_id": created_categories[2]["id"], "barcode": "3400930000031", "purchase_price": 3000, "price": 4000, "stock": 120, "min_stock": 35},
            {"name": "Diclofénac 50mg", "category_id": created_categories[2]["id"], "barcode": "3400930000032", "purchase_price": 4000, "price": 5500, "stock": 90, "min_stock": 25},
            {"name": "Voltarène Gel 1%", "category_id": created_categories[2]["id"], "barcode": "3400930000033", "purchase_price": 10000, "price": 14000, "stock": 40, "min_stock": 10},
            
            # Vitamines
            {"name": "Vitamine C 1000mg", "category_id": created_categories[3]["id"], "barcode": "3400930000041", "purchase_price": 5000, "price": 6500, "stock": 100, "min_stock": 30},
            {"name": "Vitamine D3 1000UI", "category_id": created_categories[3]["id"], "barcode": "3400930000042", "purchase_price": 8000, "price": 10500, "stock": 70, "min_stock": 20},
            {"name": "Complexe Vitamine B", "category_id": created_categories[3]["id"], "barcode": "3400930000043", "purchase_price": 12000, "price": 15500, "stock": 50, "min_stock": 15},
            
            # Dermatologie
            {"name": "Crème Hydratante Visage", "category_id": created_categories[4]["id"], "barcode": "3400930000051", "purchase_price": 15000, "price": 22000, "stock": 30, "min_stock": 10},
            {"name": "Pommade Cicatrisante", "category_id": created_categories[4]["id"], "barcode": "3400930000052", "purchase_price": 8000, "price": 12000, "stock": 45, "min_stock": 15},
            
            # Hygiène
            {"name": "Gel Hydroalcoolique 500ml", "category_id": created_categories[5]["id"], "barcode": "3400930000061", "purchase_price": 5000, "price": 6500, "stock": 80, "min_stock": 25},
            {"name": "Masques Chirurgicaux (x50)", "category_id": created_categories[5]["id"], "barcode": "3400930000062", "purchase_price": 10000, "price": 12500, "stock": 40, "min_stock": 10},
            
            # Produits avec stock bas (pour tester alertes)
            {"name": "Aspirine 500mg", "category_id": created_categories[0]["id"], "barcode": "3400930000071", "purchase_price": 2000, "price": 2700, "stock": 5, "min_stock": 20},
            {"name": "Métronidazole 500mg", "category_id": created_categories[1]["id"], "barcode": "3400930000072", "purchase_price": 4500, "price": 6300, "stock": 8, "min_stock": 15},
        ]
        
        created_products = []
        for prod in products_data:
            prod["id"] = generate_id()
            # Do not set expiration_date or created_at - let the repository handle dates
            try:
                created = product_repo.create(prod)
                created_products.append(created)
            except Exception as e:
                results["errors"].append(f"Product {prod['name']}: {str(e)[:100]}")
        results["created"]["products"] = len(created_products)
        
        # --- Update Settings ---
        settings_repo.set("pharmacy_name", "Ma Pharmacie")
        settings_repo.set("currency", "GNF")
        settings_repo.set("low_stock_threshold", 10)
        settings_repo.set("expiration_alert_days", 30)
        results["created"]["settings"] = "Updated"
        
        return {
            "success": True,
            "message": "Base de données réinitialisée avec succès!",
            "summary": results,
            "test_accounts": {
                "admin": {"email": "admin@pharmaflow.com", "password": "admin123", "code": "ADM-001"},
                "pharmacien": {"email": "pharmacien@pharmaflow.com", "password": "pharma123", "code": "PHA-001"},
                "caissier": {"email": "caissier@pharmaflow.com", "password": "caisse123", "code": "CAI-001"}
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du seed: {str(e)}")


@router.get("/status")
async def get_seed_status():
    """Get current data counts in database"""
    try:
        counts = {}
        
        counts["categories"] = len(CategoryRepository().get_all())
        counts["products"] = len(ProductRepository().get_all())
        counts["customers"] = len(CustomerRepository().get_all())
        counts["suppliers"] = len(SupplierRepository().get_all())
        
        return {
            "success": True,
            "counts": counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrate-split-payments")
async def migrate_split_payments(current_user: dict = Depends(require_role(["admin"]))):
    """Add split payment columns to sales table if they don't exist."""
    try:
        session = db_manager.get_tenant_session("default")
        results = {"columns_added": []}
        
        with session as s:
            # Add is_split_payment column
            try:
                s.execute(text("""
                    ALTER TABLE sales 
                    ADD COLUMN IF NOT EXISTS is_split_payment BOOLEAN DEFAULT FALSE;
                """))
                s.commit()
                results["columns_added"].append("is_split_payment")
            except Exception as e:
                s.rollback()
                results["is_split_payment_error"] = str(e)[:100]
            
            # Add split_payments column
            try:
                s.execute(text("""
                    ALTER TABLE sales 
                    ADD COLUMN IF NOT EXISTS split_payments JSONB DEFAULT NULL;
                """))
                s.commit()
                results["columns_added"].append("split_payments")
            except Exception as e:
                s.rollback()
                results["split_payments_error"] = str(e)[:100]
        
        return {
            "success": True,
            "message": "Migration completed",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration error: {str(e)}")
