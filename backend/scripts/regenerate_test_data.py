"""
Script pour régénérer les données de test avec les agents correctement assignés
"""
import os
import sys
sys.path.insert(0, '/app/backend')

from database.config import get_database_url
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, timezone
import random
import uuid

# Configuration
SCHEMA = "public"

# Utilisateurs (agents) disponibles
USERS = [
    {"id": "928cc5d2-86a1-44be-970f-046b951d3b29", "name": "Mamadou", "code": "ADM-001", "role": "admin"},
    {"id": "a99017af-c55c-42f1-8088-3f6a9e3ab5b1", "name": "Fatoumata", "code": "PHA-001", "role": "pharmacien"},
    {"id": "ebf168af-5c3e-415f-a2f8-d1c0b1426bd8", "name": "Ibrahima", "code": "CAI-001", "role": "caissier"},
    {"id": "1ec26be5-6e25-481e-9871-b58170a28ba9", "name": "Aissatou", "code": "PHA-002", "role": "pharmacien"},
    {"id": "adfe85ff-8cb4-4277-a37c-b89725e2dd3d", "name": "Oumar", "code": "CAI-002", "role": "caissier"},
]

# Modes de paiement (en majuscules pour l'enum PostgreSQL)
PAYMENT_METHODS = ["CASH", "CARD", "MTN_MONEY", "ORANGE_MONEY"]

def get_random_user():
    """Retourne un utilisateur aléatoire (priorité aux caissiers et pharmaciens)"""
    weights = [1, 3, 4, 3, 4]  # Plus de chances pour caissiers/pharmaciens
    return random.choices(USERS, weights=weights)[0]

def main():
    url = get_database_url()
    engine = create_engine(url)
    
    with engine.connect() as conn:
        # 1. Récupérer les produits existants
        products = conn.execute(text(f"SELECT id, name, price FROM {SCHEMA}.products WHERE is_active = true")).fetchall()
        products = [{"id": str(p[0]), "name": p[1], "price": float(p[2] or 5000)} for p in products]
        print(f"Produits trouvés: {len(products)}")
        
        # 2. Récupérer les clients existants
        customers = conn.execute(text(f"SELECT id, name FROM {SCHEMA}.customers WHERE is_active = true")).fetchall()
        customers = [{"id": str(c[0]), "name": c[1]} for c in customers]
        print(f"Clients trouvés: {len(customers)}")
        
        # 3. Supprimer les anciennes ventes et items
        print("\nSuppression des anciennes données...")
        conn.execute(text(f"DELETE FROM {SCHEMA}.sale_items"))
        conn.execute(text(f"DELETE FROM {SCHEMA}.sales"))
        conn.commit()
        print("Anciennes ventes supprimées.")
        
        # 4. Générer de nouvelles ventes sur les 14 derniers jours
        print("\nGénération des nouvelles ventes...")
        now = datetime.now(timezone.utc)
        sales_created = 0
        
        for days_ago in range(14, -1, -1):  # 14 jours jusqu'à aujourd'hui
            date = now - timedelta(days=days_ago)
            
            # Nombre de ventes par jour (variable)
            num_sales = random.randint(3, 12)
            
            for _ in range(num_sales):
                sale_id = str(uuid.uuid4())
                user = get_random_user()
                customer = random.choice(customers) if random.random() > 0.3 else None
                payment_method = random.choice(PAYMENT_METHODS)
                
                # Heure aléatoire dans la journée (8h-20h)
                hour = random.randint(8, 20)
                minute = random.randint(0, 59)
                sale_date = date.replace(hour=hour, minute=minute, second=random.randint(0, 59))
                
                # Sélectionner 1-5 produits pour cette vente
                num_items = random.randint(1, 5)
                selected_products = random.sample(products, min(num_items, len(products)))
                
                # Calculer le total
                items_data = []
                subtotal = 0
                for prod in selected_products:
                    qty = random.randint(1, 4)
                    price = prod["price"] if prod["price"] > 0 else random.randint(3000, 20000)
                    item_subtotal = price * qty
                    subtotal += item_subtotal
                    items_data.append({
                        "id": str(uuid.uuid4()),
                        "product_id": prod["id"],
                        "product_name": prod["name"],
                        "quantity": qty,
                        "unit_price": price,
                        "subtotal": item_subtotal
                    })
                
                # Générer le numéro de vente
                sale_number = f"VTE-{sales_created + 1001}"
                
                # Insérer la vente avec les colonnes correctes
                conn.execute(text(f"""
                    INSERT INTO {SCHEMA}.sales (
                        id, sale_number, subtotal, discount, tax_amount, 
                        total, amount_paid, payment_method, status,
                        customer_id, agent_code, agent_name, notes, created_at
                    ) VALUES (
                        :id, :sale_number, :subtotal, 0, 0,
                        :total, :amount_paid, :payment_method, 'COMPLETED',
                        :customer_id, :agent_code, :agent_name, :notes, :created_at
                    )
                """), {
                    "id": sale_id,
                    "sale_number": sale_number,
                    "subtotal": subtotal,
                    "total": subtotal,
                    "amount_paid": subtotal,
                    "payment_method": payment_method,
                    "customer_id": customer["id"] if customer else None,
                    "agent_code": user["code"],
                    "agent_name": user["name"],
                    "notes": random.choice(["", "", "", "Vente avec ordonnance", "Client régulier"]),
                    "created_at": sale_date
                })
                
                # Insérer les items de la vente
                for item in items_data:
                    conn.execute(text(f"""
                        INSERT INTO {SCHEMA}.sale_items (
                            id, sale_id, product_id, product_name,
                            quantity, unit_price, subtotal
                        ) VALUES (
                            :id, :sale_id, :product_id, :product_name,
                            :quantity, :unit_price, :subtotal
                        )
                    """), {
                        "id": item["id"],
                        "sale_id": sale_id,
                        "product_id": item["product_id"],
                        "product_name": item["product_name"],
                        "quantity": item["quantity"],
                        "unit_price": item["unit_price"],
                        "subtotal": item["subtotal"]
                    })
                
                sales_created += 1
        
        conn.commit()
        print(f"\n✅ {sales_created} ventes créées avec succès!")
        
        # Vérification
        result = conn.execute(text(f"""
            SELECT agent_name, COUNT(*) as count 
            FROM {SCHEMA}.sales 
            GROUP BY agent_name 
            ORDER BY count DESC
        """)).fetchall()
        
        print("\nRépartition des ventes par agent:")
        for row in result:
            print(f"  {row[0]}: {row[1]} ventes")

if __name__ == "__main__":
    main()
