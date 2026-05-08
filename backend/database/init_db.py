"""
Script d'initialisation des bases de données PostgreSQL

Ce script:
1. Crée les tables dans la base master (gestion des tenants)
2. Crée les tables dans les bases tenant
3. Enregistre le premier tenant (Pharmacie Centrale)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.config import db_manager, get_database_url, get_tenant_db_name
from database.base import Base as TenantBase
from database.models_master import Base as MasterBase, Tenant
from database.models_tenant import (
    User, Category, Unit, Product, Customer, Supplier,
    Sale, SaleItem, Supply, SupplyItem, Shift, ShiftSchedule,
    PendingSale, Debt, Prescription, StockMovement, Setting
)
from sqlalchemy import create_engine, text
import uuid


def init_master_database():
    """Initialise la base de données master."""
    print("📦 Initialisation de la base master...")
    
    engine = db_manager._engines["master"]
    
    # Créer les tables master
    MasterBase.metadata.create_all(engine)
    
    print("✅ Tables master créées")


def init_tenant_database(tenant_slug: str):
    """Initialise les tables pour un tenant spécifique."""
    db_name = get_tenant_db_name(tenant_slug)
    print(f"📦 Initialisation de la base tenant: {db_name}...")
    
    # S'assurer que la BD existe
    db_manager.create_tenant_database(tenant_slug)
    
    # Créer le moteur pour ce tenant
    engine = db_manager.get_tenant_engine(tenant_slug)
    
    # Créer toutes les tables tenant
    TenantBase.metadata.create_all(engine)
    
    print(f"✅ Tables créées pour {db_name}")


def register_tenant(slug: str, name: str, address: str = None, phone: str = None):
    """Enregistre un nouveau tenant dans la base master."""
    print(f"📝 Enregistrement du tenant: {name}...")
    
    db_name = get_tenant_db_name(slug)
    
    with db_manager.get_master_session() as session:
        # Vérifier si le tenant existe déjà
        existing = session.query(Tenant).filter_by(slug=slug).first()
        if existing:
            print(f"⚠️  Tenant '{slug}' existe déjà")
            return existing
        
        # Créer le tenant
        tenant = Tenant(
            id=uuid.uuid4(),
            slug=slug,
            name=name,
            address=address,
            phone=phone,
            database_name=db_name,
            is_active=True,
            settings={}
        )
        session.add(tenant)
        session.commit()
        
        print(f"✅ Tenant '{name}' enregistré (DB: {db_name})")
        return tenant


def create_default_settings(tenant_slug: str):
    """Crée les paramètres par défaut pour un tenant."""
    print(f"⚙️  Création des paramètres par défaut...")
    
    default_settings = [
        ("currency", "GNF", "Devise utilisée"),
        ("timezone", "Africa/Conakry", "Fuseau horaire"),
        ("expiration_alert_days", 30, "Jours avant alerte péremption"),
        ("default_min_stock", 10, "Stock minimum par défaut"),
        ("shift_max_duration", 12, "Durée max shift (heures)"),
        ("pending_sale_expiration_hours", 24, "Expiration ventes en attente (heures)"),
    ]
    
    with db_manager.get_tenant_session(tenant_slug) as session:
        for key, value, description in default_settings:
            existing = session.query(Setting).filter_by(key=key).first()
            if not existing:
                setting = Setting(
                    id=uuid.uuid4(),
                    key=key,
                    value=value,
                    description=description
                )
                session.add(setting)
        
        session.commit()
    
    print("✅ Paramètres créés")


def main():
    """Point d'entrée principal."""
    print("\n" + "="*60)
    print("🚀 INITIALISATION POSTGRESQL MULTI-TENANT")
    print("="*60 + "\n")
    
    # 1. Initialiser la base master
    init_master_database()
    
    # 2. Enregistrer le premier tenant (Pharmacie Centrale)
    tenant = register_tenant(
        slug="pharmacie_centrale",
        name="Pharmacie Centrale",
        address="Conakry, Guinée",
        phone="+224 620 00 00 00"
    )
    
    # 3. Initialiser les tables du tenant
    init_tenant_database("pharmacie_centrale")
    
    # 4. Créer les paramètres par défaut
    create_default_settings("pharmacie_centrale")
    
    print("\n" + "="*60)
    print("✅ INITIALISATION TERMINÉE AVEC SUCCÈS!")
    print("="*60)
    print("\nProchaine étape: Migration des données MongoDB → PostgreSQL")
    print("Exécuter: python database/migrate_data.py\n")


if __name__ == "__main__":
    main()
