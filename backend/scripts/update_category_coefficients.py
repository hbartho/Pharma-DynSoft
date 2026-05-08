#!/usr/bin/env python3
"""
Script pour mettre à jour le coefficient de toutes les catégories à 1.4
"""
import psycopg2
from urllib.parse import unquote

# Configuration Supabase
SUPABASE_URL = "postgresql://postgres.vwpakvjgnuwyynsixrab:DynSoftPharma1%23@aws-0-us-west-2.pooler.supabase.com:6543/postgres"

def update_category_coefficients():
    # Décoder l'URL pour le mot de passe
    connection_string = unquote(SUPABASE_URL)
    
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
