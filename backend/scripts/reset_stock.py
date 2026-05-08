#!/usr/bin/env python3
"""
Script pour mettre tous les stocks de produits à 0
"""
import psycopg2
from urllib.parse import unquote

# Configuration Supabase
SUPABASE_URL = "postgresql://postgres.vwpakvjgnuwyynsixrab:DynSoftPharma1%23@aws-0-us-west-2.pooler.supabase.com:6543/postgres"

def reset_all_stock():
    connection_string = unquote(SUPABASE_URL)
    
    try:
        conn = psycopg2.connect(connection_string)
        cursor = conn.cursor()
        
        # Compter les produits
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        print(f"Nombre de produits trouvés: {count}")
        
        # Mettre tous les stocks à 0
        cursor.execute("""
            UPDATE products 
            SET stock = 0
        """)
        
        updated_count = cursor.rowcount
        conn.commit()
        
        print(f"Mise à jour réussie: {updated_count} produits mis à jour avec stock = 0")
        
        # Vérifier les résultats
        cursor.execute("SELECT name, stock FROM products ORDER BY name LIMIT 10")
        results = cursor.fetchall()
        print("\nAperçu des 10 premiers produits:")
        for name, stock in results:
            print(f"  - {name}: stock = {stock}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Erreur: {e}")
        return False

if __name__ == "__main__":
    reset_all_stock()
