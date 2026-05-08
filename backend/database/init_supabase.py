"""
Script d'initialisation des tables PostgreSQL sur Supabase
Ce script crée toutes les tables nécessaires dans la base Supabase.
"""

import os
import sys

# S'assurer que le répertoire backend est dans le path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text, inspect
from database.models_tenant import Base as TenantBase
from database.config import get_database_url, USE_SUPABASE

def init_supabase():
    """Initialise les tables sur Supabase."""
    
    if not USE_SUPABASE:
        print("❌ SUPABASE_URL non configuré. Vérifiez le fichier .env")
        return False
    
    print("=" * 60)
    print("🚀 INITIALISATION SUPABASE")
    print("=" * 60)
    
    try:
        # Connexion à Supabase
        db_url = get_database_url()
        print(f"\n📡 Connexion à Supabase...")
        engine = create_engine(db_url, pool_pre_ping=True)
        
        # Tester la connexion
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connecté! PostgreSQL: {version[:50]}...")
        
        # Créer les tables du tenant
        print(f"\n📋 Création des tables...")
        TenantBase.metadata.create_all(bind=engine)
        
        # Vérifier les tables créées
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ {len(tables)} tables créées/vérifiées:")
        for table in sorted(tables):
            print(f"   - {table}")
        
        print("\n" + "=" * 60)
        print("✅ INITIALISATION SUPABASE TERMINÉE!")
        print("=" * 60)
        print("\nProchaine étape: Migrer les données depuis MongoDB")
        print("Exécuter: python database/migrate_to_supabase.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_supabase()
    sys.exit(0 if success else 1)
