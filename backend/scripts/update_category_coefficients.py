#!/usr/bin/env python3
"""
Script pour mettre à jour le coefficient de toutes les catégories à 1.4
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
SUPABASE_URL = os.environ.get("SUPABASE_URL") or os.environ.get("DATABASE_URL")

def update_category_coefficients():
    if not SUPABASE_URL:
        raise SystemExit("SUPABASE_URL ou DATABASE_URL manquant dans .env")
    connection_string = SUPABASE_URL
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        # Compter les catégories
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        print(f"Nombre de catégories trouvées: {count}")
        
        # Mettre à jour toutes les catégories avec coefficient = 1.4
        cursor.execute("""
            UPDATE categories 
            SET markup_coefficient = 1.4
        """)
        
        updated_count = cursor.rowcount
        conn.commit()
        
        print(f"Mise à jour réussie: {updated_count} catégories mises à jour avec coefficient = 1.4")
        
        # Vérifier les résultats
        cursor.execute("SELECT name, markup_coefficient FROM categories ORDER BY name LIMIT 10")
        results = cursor.fetchall()
        print("\nAperçu des 10 premières catégories:")
        for name, coef in results:
            print(f"  - {name}: coefficient = {coef}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Erreur: {e}")
        return False

if __name__ == "__main__":
    update_category_coefficients()
