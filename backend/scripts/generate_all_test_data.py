"""
Script pour générer des données de test complètes pour toutes les sections de l'application
"""
import os
import sys
sys.path.insert(0, '/app/backend')

from database.config import get_database_url
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, timezone, date
import random
import uuid
import json

SCHEMA = "public"

# Données existantes à récupérer
USERS = []
PRODUCTS = []
CUSTOMERS = []
SUPPLIERS = []
CATEGORIES = []

def get_existing_data(conn):
    """Récupère les données existantes nécessaires"""
    global USERS, PRODUCTS, CUSTOMERS, SUPPLIERS, CATEGORIES
    
    # Users
    result = conn.execute(text(f"SELECT id, name, employee_code, role FROM {SCHEMA}.users WHERE is_active = true")).fetchall()
    USERS = [{"id": str(r[0]), "name": r[1], "code": r[2], "role": r[3]} for r in result]
    print(f"  {len(USERS)} utilisateurs trouvés")
    
    # Products
    result = conn.execute(text(f"SELECT id, name, price, stock FROM {SCHEMA}.products WHERE is_active = true")).fetchall()
    PRODUCTS = [{"id": str(r[0]), "name": r[1], "price": float(r[2] or 5000), "stock": r[3] or 0} for r in result]
    print(f"  {len(PRODUCTS)} produits trouvés")
    
    # Customers
    result = conn.execute(text(f"SELECT id, name, phone FROM {SCHEMA}.customers WHERE is_active = true")).fetchall()
    CUSTOMERS = [{"id": str(r[0]), "name": r[1], "phone": r[2]} for r in result]
    print(f"  {len(CUSTOMERS)} clients trouvés")
    
    # Suppliers
    result = conn.execute(text(f"SELECT id, name FROM {SCHEMA}.suppliers WHERE is_active = true")).fetchall()
    SUPPLIERS = [{"id": str(r[0]), "name": r[1]} for r in result]
    print(f"  {len(SUPPLIERS)} fournisseurs trouvés")
    
    # Categories
    result = conn.execute(text(f"SELECT id, name FROM {SCHEMA}.categories")).fetchall()
    CATEGORIES = [{"id": str(r[0]), "name": r[1]} for r in result]
    print(f"  {len(CATEGORIES)} catégories trouvées")


def create_supplies(conn):
    """Créer des approvisionnements"""
    print("\n📦 Création des approvisionnements...")
    
    # Vider les tables existantes
    conn.execute(text(f"DELETE FROM {SCHEMA}.supply_items"))
    conn.execute(text(f"DELETE FROM {SCHEMA}.supplies"))
    conn.commit()
    
    now = datetime.now(timezone.utc)
    created = 0
    
    for days_ago in range(30, -1, -5):  # Un approvisionnement tous les 5 jours
        supply_date = (now - timedelta(days=days_ago)).date()
        supply_id = str(uuid.uuid4())
        supplier = random.choice(SUPPLIERS)
        
        # Sélectionner 3-8 produits pour cet approvisionnement
        num_items = random.randint(3, 8)
        selected_products = random.sample(PRODUCTS, min(num_items, len(PRODUCTS)))
        
        items_data = []
        total_amount = 0
        
        for prod in selected_products:
            qty = random.randint(10, 50)
            purchase_price = prod["price"] * 0.7  # Prix d'achat = 70% du prix de vente
            selling_price = prod["price"]
            subtotal = purchase_price * qty
            total_amount += subtotal
            
            # Date d'expiration dans 6-24 mois
            exp_date = supply_date + timedelta(days=random.randint(180, 720))
            
            items_data.append({
                "id": str(uuid.uuid4()),
                "supply_id": supply_id,
                "product_id": prod["id"],
                "quantity": qty,
                "purchase_price": purchase_price,
                "selling_price": selling_price,
                "subtotal": subtotal,
                "expiration_date": exp_date
            })
        
        # Insérer l'approvisionnement
        conn.execute(text(f"""
            INSERT INTO {SCHEMA}.supplies (
                id, supply_number, invoice_number, total_amount, tax_amount,
                supply_date, notes, supplier_id, created_at
            ) VALUES (
                :id, :supply_number, :invoice_number, :total_amount, 0,
                :supply_date, :notes, :supplier_id, :created_at
            )
        """), {
            "id": supply_id,
            "supply_number": f"APP-{1000 + created}",
            "invoice_number": f"FAC-{random.randint(10000, 99999)}",
            "total_amount": total_amount,
            "supply_date": supply_date,
            "notes": random.choice(["", "Livraison urgente", "Commande régulière"]),
            "supplier_id": supplier["id"],
            "created_at": datetime.combine(supply_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        })
        
        # Insérer les items
        for item in items_data:
            conn.execute(text(f"""
                INSERT INTO {SCHEMA}.supply_items (
                    id, supply_id, product_id, quantity, purchase_price,
                    selling_price, subtotal, expiration_date
                ) VALUES (
                    :id, :supply_id, :product_id, :quantity, :purchase_price,
                    :selling_price, :subtotal, :expiration_date
                )
            """), item)
        
        created += 1
    
    conn.commit()
    print(f"  ✅ {created} approvisionnements créés")


def create_shift_schedules(conn):
    """Créer des planifications de shifts"""
    print("\n📅 Création des planifications de shifts...")
    
    conn.execute(text(f"DELETE FROM {SCHEMA}.shift_schedules"))
    conn.commit()
    
    today = date.today()
    created = 0
    
    # Planifier pour les 14 prochains jours
    for day_offset in range(14):
        schedule_date = today + timedelta(days=day_offset)
        
        # Exclure les dimanches
        if schedule_date.weekday() == 6:
            continue
        
        # Planifier 2-4 employés par jour
        num_employees = random.randint(2, 4)
        selected_users = random.sample([u for u in USERS if u["role"] != "admin"], min(num_employees, len(USERS) - 1))
        
        for user in selected_users:
            schedule_id = str(uuid.uuid4())
            
            # Shift matin ou après-midi
            if random.random() > 0.5:
                start_time = "08:00"
                end_time = "14:00"
            else:
                start_time = "14:00"
                end_time = "20:00"
            
            conn.execute(text(f"""
                INSERT INTO {SCHEMA}.shift_schedules (
                    id, user_id, user_code, user_name, role,
                    schedule_date, start_time, end_time, max_duration_hours, notes
                ) VALUES (
                    :id, :user_id, :user_code, :user_name, :role,
                    :schedule_date, :start_time, :end_time, :max_duration_hours, :notes
                )
            """), {
                "id": schedule_id,
                "user_id": user["id"],
                "user_code": user["code"],
                "user_name": user["name"],
                "role": user["role"],
                "schedule_date": schedule_date,
                "start_time": start_time,
                "end_time": end_time,
                "max_duration_hours": 8.0,
                "notes": ""
            })
            created += 1
    
    conn.commit()
    print(f"  ✅ {created} planifications créées")


def create_stock_movements(conn):
    """Créer des mouvements de stock"""
    print("\n📊 Création des mouvements de stock...")
    
    conn.execute(text(f"DELETE FROM {SCHEMA}.stock_movements"))
    conn.commit()
    
    now = datetime.now(timezone.utc)
    created = 0
    
    movement_types = ["IN", "OUT", "ADJUSTMENT", "LOSS", "RETURN"]
    reasons = {
        "IN": ["Approvisionnement", "Retour client", "Transfert entrant"],
        "OUT": ["Vente", "Transfert sortant", "Échantillon"],
        "ADJUSTMENT": ["Inventaire", "Correction d'erreur", "Ajustement système"],
        "LOSS": ["Produit périmé", "Casse", "Vol"],
        "RETURN": ["Retour fournisseur", "Produit défectueux"]
    }
    
    # Créer des mouvements sur les 30 derniers jours
    for days_ago in range(30, -1, -1):
        movement_date = now - timedelta(days=days_ago)
        
        # 2-5 mouvements par jour
        num_movements = random.randint(2, 5)
        
        for _ in range(num_movements):
            product = random.choice(PRODUCTS)
            user = random.choice(USERS)
            m_type = random.choice(movement_types)
            
            # Quantité selon le type
            if m_type == "IN":
                quantity = random.randint(10, 50)
            elif m_type == "OUT":
                quantity = -random.randint(1, 10)
            elif m_type == "LOSS":
                quantity = -random.randint(1, 5)
            else:
                quantity = random.randint(-5, 5)
            
            movement_id = str(uuid.uuid4())
            stock_after = max(0, product["stock"] + quantity)
            
            conn.execute(text(f"""
                INSERT INTO {SCHEMA}.stock_movements (
                    id, product_id, movement_type, quantity, stock_after,
                    reference_type, agent_code, reason, created_at
                ) VALUES (
                    :id, :product_id, :movement_type, :quantity, :stock_after,
                    :reference_type, :agent_code, :reason, :created_at
                )
            """), {
                "id": movement_id,
                "product_id": product["id"],
                "movement_type": m_type,
                "quantity": abs(quantity) if m_type == "IN" else quantity,
                "stock_after": stock_after,
                "reference_type": m_type.lower(),
                "agent_code": user["code"],
                "reason": random.choice(reasons[m_type]),
                "created_at": movement_date
            })
            created += 1
    
    conn.commit()
    print(f"  ✅ {created} mouvements de stock créés")


def create_debts(conn):
    """Créer des dettes clients"""
    print("\n💳 Création des dettes clients...")
    
    conn.execute(text(f"DELETE FROM {SCHEMA}.debts"))
    conn.commit()
    
    now = datetime.now(timezone.utc)
    created = 0
    
    # Récupérer quelques ventes existantes
    result = conn.execute(text(f"SELECT id, total, customer_id FROM {SCHEMA}.sales WHERE customer_id IS NOT NULL LIMIT 20")).fetchall()
    sales = [{"id": str(r[0]), "total": float(r[1] or 0), "customer_id": str(r[2])} for r in result]
    
    if not sales:
        print("  ⚠️ Aucune vente avec client trouvée, création de dettes génériques...")
        # Créer des dettes sans vente associée
        for i in range(10):
            customer = random.choice(CUSTOMERS)
            debt_id = str(uuid.uuid4())
            original_amount = random.randint(50000, 500000)
            remaining = original_amount * random.uniform(0.3, 1.0)
            due_date = (now + timedelta(days=random.randint(-10, 30))).date()
            
            status = "PENDING" if remaining == original_amount else "PARTIAL"
            if remaining <= 0:
                status = "PAID"
                remaining = 0
            
            payments = []
            if status == "PARTIAL":
                payments = [{
                    "amount": original_amount - remaining,
                    "date": (now - timedelta(days=random.randint(1, 10))).isoformat(),
                    "method": random.choice(["cash", "mtn_money", "orange_money"])
                }]
            
            conn.execute(text(f"""
                INSERT INTO {SCHEMA}.debts (
                    id, customer_id, original_amount, remaining_amount,
                    status, due_date, payments, notes, created_at
                ) VALUES (
                    :id, :customer_id, :original_amount, :remaining_amount,
                    :status, :due_date, :payments, :notes, :created_at
                )
            """), {
                "id": debt_id,
                "customer_id": customer["id"],
                "original_amount": original_amount,
                "remaining_amount": remaining,
                "status": status,
                "due_date": due_date,
                "payments": json.dumps(payments),
                "notes": random.choice(["", "Client régulier", "Paiement attendu fin de mois"]),
                "created_at": now - timedelta(days=random.randint(1, 30))
            })
            created += 1
    else:
        # Créer des dettes basées sur les ventes existantes
        for sale in random.sample(sales, min(10, len(sales))):
            debt_id = str(uuid.uuid4())
            original_amount = sale["total"] * random.uniform(0.3, 0.8)  # 30-80% du total en dette
            remaining = original_amount * random.uniform(0.3, 1.0)
            due_date = (now + timedelta(days=random.randint(-10, 30))).date()
            
            status = "PENDING" if remaining == original_amount else "PARTIAL"
            if remaining <= 0:
                status = "PAID"
                remaining = 0
            
            payments = []
            if status == "PARTIAL":
                payments = [{
                    "amount": original_amount - remaining,
                    "date": (now - timedelta(days=random.randint(1, 10))).isoformat(),
                    "method": random.choice(["cash", "mtn_money", "orange_money"])
                }]
            
            conn.execute(text(f"""
                INSERT INTO {SCHEMA}.debts (
                    id, customer_id, sale_id, original_amount, remaining_amount,
                    status, due_date, payments, notes, created_at
                ) VALUES (
                    :id, :customer_id, :sale_id, :original_amount, :remaining_amount,
                    :status, :due_date, :payments, :notes, :created_at
                )
            """), {
                "id": debt_id,
                "customer_id": sale["customer_id"],
                "sale_id": sale["id"],
                "original_amount": original_amount,
                "remaining_amount": remaining,
                "status": status,
                "due_date": due_date,
                "payments": json.dumps(payments),
                "notes": random.choice(["", "Client régulier", "Paiement attendu"]),
                "created_at": now - timedelta(days=random.randint(1, 30))
            })
            created += 1
    
    conn.commit()
    print(f"  ✅ {created} dettes créées")


def create_prescriptions(conn):
    """Créer des ordonnances"""
    print("\n💊 Création des ordonnances...")
    
    conn.execute(text(f"DELETE FROM {SCHEMA}.prescriptions"))
    conn.commit()
    
    now = datetime.now(timezone.utc)
    created = 0
    
    doctors = [
        "Dr. Mamadou Diallo", "Dr. Fatoumata Bah", "Dr. Ibrahima Sow",
        "Dr. Aissatou Barry", "Dr. Ousmane Camara", "Dr. Mariama Diallo"
    ]
    
    statuses = ["PENDING", "FULFILLED", "COMPLETED", "CANCELLED"]
    
    for i in range(15):
        prescription_id = str(uuid.uuid4())
        customer = random.choice(CUSTOMERS)
        doctor = random.choice(doctors)
        status = random.choice(statuses)
        
        # Sélectionner 2-5 médicaments
        num_meds = random.randint(2, 5)
        selected_products = random.sample(PRODUCTS, min(num_meds, len(PRODUCTS)))
        
        medications = []
        for prod in selected_products:
            medications.append({
                "product_id": prod["id"],
                "product_name": prod["name"],
                "quantity": random.randint(1, 3),
                "dosage": random.choice(["1 comprimé 3x/jour", "2 comprimés 2x/jour", "1 cuillère à soupe 3x/jour", "1 application 2x/jour"]),
                "duration": f"{random.randint(5, 14)} jours",
                "dispensed": random.randint(0, 3) if status in ["PARTIAL", "COMPLETED"] else 0
            })
        
        created_at = now - timedelta(days=random.randint(0, 30))
        
        conn.execute(text(f"""
            INSERT INTO {SCHEMA}.prescriptions (
                id, customer_id, doctor_name, medications, status, notes, created_at
            ) VALUES (
                :id, :customer_id, :doctor_name, :medications, :status, :notes, :created_at
            )
        """), {
            "id": prescription_id,
            "customer_id": customer["id"],
            "doctor_name": doctor,
            "medications": json.dumps(medications),
            "status": status,
            "notes": random.choice(["", "Renouvellement", "Première consultation", "Suivi mensuel"]),
            "created_at": created_at
        })
        created += 1
    
    conn.commit()
    print(f"  ✅ {created} ordonnances créées")


def update_categories(conn):
    """Mettre à jour les catégories avec coefficients"""
    print("\n🏷️ Mise à jour des catégories (coefficients)...")
    
    coefficients = {
        "Médicaments": 1.35,
        "Cosmétiques": 1.50,
        "Compléments": 1.40,
        "Hygiène": 1.45,
        "Matériel médical": 1.30,
        "Bébé & Enfant": 1.40
    }
    
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"]
    
    updated = 0
    for cat in CATEGORIES:
        coef = coefficients.get(cat["name"], 1.35)
        color = random.choice(colors)
        
        conn.execute(text(f"""
            UPDATE {SCHEMA}.categories 
            SET markup_coefficient = :coef, color = :color
            WHERE id = :id
        """), {
            "id": cat["id"],
            "coef": coef,
            "color": color
        })
        updated += 1
    
    conn.commit()
    print(f"  ✅ {updated} catégories mises à jour")


def create_settings(conn):
    """Créer les paramètres de l'application incluant les modes de paiement"""
    print("\n⚙️ Mise à jour des paramètres (modes de paiement)...")
    
    payment_methods = [
        {"id": "cash", "name": "Espèces", "is_active": True, "icon": "banknote"},
        {"id": "card", "name": "Carte bancaire", "is_active": True, "icon": "credit-card"},
        {"id": "orange_money", "name": "Orange Money", "is_active": True, "icon": "smartphone"},
        {"id": "mtn_money", "name": "MTN Money", "is_active": True, "icon": "smartphone"},
        {"id": "check", "name": "Chèque", "is_active": True, "icon": "file-check"},
        {"id": "credit", "name": "Crédit", "is_active": True, "icon": "wallet"}
    ]
    
    # Vérifier si le setting existe
    result = conn.execute(text(f"SELECT id FROM {SCHEMA}.settings WHERE key = 'payment_methods'")).fetchone()
    
    if result:
        conn.execute(text(f"""
            UPDATE {SCHEMA}.settings 
            SET value = :value
            WHERE key = 'payment_methods'
        """), {"value": json.dumps(payment_methods)})
    else:
        conn.execute(text(f"""
            INSERT INTO {SCHEMA}.settings (id, key, value, description)
            VALUES (:id, 'payment_methods', :value, 'Modes de paiement disponibles')
        """), {
            "id": str(uuid.uuid4()),
            "value": json.dumps(payment_methods)
        })
    
    conn.commit()
    print(f"  ✅ Modes de paiement configurés")


def main():
    url = get_database_url()
    engine = create_engine(url)
    
    print("=" * 50)
    print("🚀 GÉNÉRATION DES DONNÉES DE TEST")
    print("=" * 50)
    
    with engine.connect() as conn:
        # Récupérer les données existantes
        print("\n📥 Récupération des données existantes...")
        get_existing_data(conn)
        
        if not USERS or not PRODUCTS or not CUSTOMERS or not SUPPLIERS:
            print("\n❌ Erreur: Données de base manquantes!")
            return
        
        # Générer les données de test
        create_supplies(conn)
        create_shift_schedules(conn)
        create_stock_movements(conn)
        create_debts(conn)
        create_prescriptions(conn)
        update_categories(conn)
        create_settings(conn)
    
    print("\n" + "=" * 50)
    print("✅ GÉNÉRATION TERMINÉE!")
    print("=" * 50)


if __name__ == "__main__":
    main()
