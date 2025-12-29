#!/usr/bin/env python3
"""
Script pour créer les données de démonstration dans la base de données.
Crée des utilisateurs, catégories, produits, clients, fournisseurs, ventes et ordonnances.

Usage:
    python create_correct_user.py

Les utilisateurs créés:
    - Admin: admin@pharmaflow.com / admin123
    - Pharmacien: pharmacien@pharmaflow.com / pharma123  
    - Caissier: caissier@pharmaflow.com / caisse123
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import bcrypt
import random
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'pharmaflow')
TENANT_ID = "default"

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def generate_id():
    return str(uuid4())

def get_timestamp(days_ago=0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()

async def create_demo_data():
    """Créer toutes les données de démonstration"""
    
    # Connexion à MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("=" * 60)
    print("   CRÉATION DES DONNÉES DE DÉMONSTRATION")
    print("   DYNSOFT PHARMA")
    print("=" * 60)
    print()
    
    # ============================================
    # 1. UTILISATEURS
    # ============================================
    print("[1/7] Création des utilisateurs...")
    
    users_to_create = [
        {
            "id": generate_id(),
            "email": "admin@pharmaflow.com",
            "password": hash_password("admin123"),
            "name": "Administrateur",
            "role": "admin",
            "tenant_id": TENANT_ID,
            "is_active": True,
            "created_at": get_timestamp(30)
        },
        {
            "id": generate_id(),
            "email": "pharmacien@pharmaflow.com",
            "password": hash_password("pharma123"),
            "name": "Jean Pharmacien",
            "role": "pharmacien",
            "tenant_id": TENANT_ID,
            "is_active": True,
            "created_at": get_timestamp(25)
        },
        {
            "id": generate_id(),
            "email": "caissier@pharmaflow.com",
            "password": hash_password("caisse123"),
            "name": "Marie Caissière",
            "role": "caissier",
            "tenant_id": TENANT_ID,
            "is_active": True,
            "created_at": get_timestamp(20)
        },
        {
            "id": generate_id(),
            "email": "demo@pharmaflow.com",
            "password": hash_password("demo123"),
            "name": "Pharmacien Démo",
            "role": "admin",
            "tenant_id": TENANT_ID,
            "is_active": True,
            "created_at": get_timestamp(15)
        }
    ]
    
    users_created = 0
    for user_data in users_to_create:
        existing = await db.users.find_one({"email": user_data["email"]})
        if not existing:
            await db.users.insert_one(user_data)
            users_created += 1
    print(f"       ✓ {users_created} utilisateur(s) créé(s)")
    
    # ============================================
    # 2. CATÉGORIES
    # ============================================
    print("[2/7] Création des catégories...")
    
    categories_data = [
        {"name": "Antibiotiques", "description": "Médicaments antibactériens", "color": "#EF4444"},
        {"name": "Antidouleurs", "description": "Analgésiques et anti-inflammatoires", "color": "#F59E0B"},
        {"name": "Vitamines", "description": "Compléments vitaminiques", "color": "#10B981"},
        {"name": "Dermato", "description": "Soins dermatologiques", "color": "#8B5CF6"},
        {"name": "Cardio", "description": "Médicaments cardiovasculaires", "color": "#EC4899"},
        {"name": "Gastro", "description": "Médicaments gastro-intestinaux", "color": "#06B6D4"},
        {"name": "Respiratoire", "description": "Médicaments respiratoires", "color": "#3B82F6"},
        {"name": "Hygiène", "description": "Produits d'hygiène", "color": "#84CC16"},
    ]
    
    category_ids = {}
    categories_created = 0
    for cat_data in categories_data:
        existing = await db.categories.find_one({"name": cat_data["name"], "tenant_id": TENANT_ID})
        if not existing:
            cat_id = generate_id()
            category_ids[cat_data["name"]] = cat_id
            await db.categories.insert_one({
                "id": cat_id,
                "name": cat_data["name"],
                "description": cat_data["description"],
                "color": cat_data["color"],
                "tenant_id": TENANT_ID,
                "created_at": get_timestamp(30)
            })
            categories_created += 1
        else:
            category_ids[cat_data["name"]] = existing["id"]
    print(f"       ✓ {categories_created} catégorie(s) créée(s)")
    
    # ============================================
    # 3. PRODUITS
    # ============================================
    print("[3/7] Création des produits...")
    
    products_data = [
        # Antibiotiques
        {"name": "Amoxicilline 500mg", "barcode": "3400930000001", "price": 8.50, "stock": 150, "min_stock": 20, "category": "Antibiotiques", "description": "Antibiotique à large spectre"},
        {"name": "Augmentin 1g", "barcode": "3400930000002", "price": 12.90, "stock": 80, "min_stock": 15, "category": "Antibiotiques", "description": "Amoxicilline + Acide clavulanique"},
        {"name": "Azithromycine 250mg", "barcode": "3400930000003", "price": 15.20, "stock": 60, "min_stock": 10, "category": "Antibiotiques", "description": "Antibiotique macrolide"},
        
        # Antidouleurs
        {"name": "Doliprane 1000mg", "barcode": "3400930000010", "price": 2.50, "stock": 500, "min_stock": 100, "category": "Antidouleurs", "description": "Paracétamol"},
        {"name": "Ibuprofène 400mg", "barcode": "3400930000011", "price": 3.20, "stock": 300, "min_stock": 50, "category": "Antidouleurs", "description": "Anti-inflammatoire non stéroïdien"},
        {"name": "Aspirine 500mg", "barcode": "3400930000012", "price": 2.80, "stock": 250, "min_stock": 40, "category": "Antidouleurs", "description": "Acide acétylsalicylique"},
        {"name": "Tramadol 50mg", "barcode": "3400930000013", "price": 7.50, "stock": 45, "min_stock": 10, "category": "Antidouleurs", "description": "Antalgique opioïde"},
        
        # Vitamines
        {"name": "Vitamine C 1000mg", "barcode": "3400930000020", "price": 6.90, "stock": 200, "min_stock": 30, "category": "Vitamines", "description": "Acide ascorbique effervescent"},
        {"name": "Vitamine D3 1000UI", "barcode": "3400930000021", "price": 8.50, "stock": 180, "min_stock": 25, "category": "Vitamines", "description": "Cholécalciférol"},
        {"name": "Magnésium B6", "barcode": "3400930000022", "price": 9.90, "stock": 120, "min_stock": 20, "category": "Vitamines", "description": "Magnésium + Vitamine B6"},
        {"name": "Fer + Acide folique", "barcode": "3400930000023", "price": 7.20, "stock": 90, "min_stock": 15, "category": "Vitamines", "description": "Complément fer et folates"},
        
        # Dermato
        {"name": "Crème Hydratante", "barcode": "3400930000030", "price": 12.50, "stock": 75, "min_stock": 15, "category": "Dermato", "description": "Crème hydratante corps"},
        {"name": "Biafine", "barcode": "3400930000031", "price": 8.90, "stock": 100, "min_stock": 20, "category": "Dermato", "description": "Émulsion pour brûlures"},
        {"name": "Cicaplast Baume B5", "barcode": "3400930000032", "price": 11.50, "stock": 60, "min_stock": 10, "category": "Dermato", "description": "Baume réparateur"},
        
        # Cardio
        {"name": "Kardegic 75mg", "barcode": "3400930000040", "price": 4.50, "stock": 200, "min_stock": 30, "category": "Cardio", "description": "Aspirine faible dose"},
        {"name": "Tahor 10mg", "barcode": "3400930000041", "price": 18.90, "stock": 80, "min_stock": 15, "category": "Cardio", "description": "Statine hypocholestérolémiante"},
        
        # Gastro
        {"name": "Gaviscon", "barcode": "3400930000050", "price": 7.90, "stock": 150, "min_stock": 25, "category": "Gastro", "description": "Anti-reflux gastrique"},
        {"name": "Smecta", "barcode": "3400930000051", "price": 5.50, "stock": 180, "min_stock": 30, "category": "Gastro", "description": "Pansement digestif"},
        {"name": "Imodium", "barcode": "3400930000052", "price": 6.20, "stock": 120, "min_stock": 20, "category": "Gastro", "description": "Anti-diarrhéique"},
        
        # Respiratoire
        {"name": "Ventoline spray", "barcode": "3400930000060", "price": 4.20, "stock": 90, "min_stock": 15, "category": "Respiratoire", "description": "Bronchodilatateur"},
        {"name": "Rhinofluimucil", "barcode": "3400930000061", "price": 6.80, "stock": 100, "min_stock": 20, "category": "Respiratoire", "description": "Spray nasal décongestionnant"},
        {"name": "Toplexil sirop", "barcode": "3400930000062", "price": 5.90, "stock": 80, "min_stock": 15, "category": "Respiratoire", "description": "Sirop antitussif"},
        
        # Hygiène
        {"name": "Gel hydroalcoolique 500ml", "barcode": "3400930000070", "price": 4.50, "stock": 300, "min_stock": 50, "category": "Hygiène", "description": "Solution désinfectante"},
        {"name": "Masques chirurgicaux x50", "barcode": "3400930000071", "price": 9.90, "stock": 200, "min_stock": 40, "category": "Hygiène", "description": "Masques de protection"},
        {"name": "Sérum physiologique", "barcode": "3400930000072", "price": 3.50, "stock": 250, "min_stock": 40, "category": "Hygiène", "description": "Doses de sérum physiologique"},
    ]
    
    product_ids = []
    products_created = 0
    for prod_data in products_data:
        existing = await db.products.find_one({"barcode": prod_data["barcode"], "tenant_id": TENANT_ID})
        if not existing:
            prod_id = generate_id()
            product_ids.append({"id": prod_id, "name": prod_data["name"], "price": prod_data["price"]})
            await db.products.insert_one({
                "id": prod_id,
                "name": prod_data["name"],
                "barcode": prod_data["barcode"],
                "description": prod_data.get("description", ""),
                "price": prod_data["price"],
                "stock": prod_data["stock"],
                "min_stock": prod_data["min_stock"],
                "category_id": category_ids.get(prod_data["category"]),
                "tenant_id": TENANT_ID,
                "created_at": get_timestamp(random.randint(5, 30)),
                "updated_at": get_timestamp(random.randint(0, 5))
            })
            products_created += 1
        else:
            product_ids.append({"id": existing["id"], "name": existing["name"], "price": existing["price"]})
    print(f"       ✓ {products_created} produit(s) créé(s)")
    
    # ============================================
    # 4. CLIENTS
    # ============================================
    print("[4/7] Création des clients...")
    
    customers_data = [
        {"name": "Jean Dupont", "phone": "06 12 34 56 78", "email": "jean.dupont@email.fr", "address": "12 Rue de la Paix, 75001 Paris"},
        {"name": "Marie Martin", "phone": "06 23 45 67 89", "email": "marie.martin@email.fr", "address": "45 Avenue des Champs, 75008 Paris"},
        {"name": "Pierre Bernard", "phone": "06 34 56 78 90", "email": "pierre.bernard@email.fr", "address": "8 Boulevard Haussmann, 75009 Paris"},
        {"name": "Sophie Petit", "phone": "06 45 67 89 01", "email": "sophie.petit@email.fr", "address": "23 Rue du Commerce, 75015 Paris"},
        {"name": "Lucas Moreau", "phone": "06 56 78 90 12", "email": "lucas.moreau@email.fr", "address": "67 Avenue Victor Hugo, 75016 Paris"},
        {"name": "Emma Leroy", "phone": "06 67 89 01 23", "email": "emma.leroy@email.fr", "address": "15 Rue de Rivoli, 75004 Paris"},
        {"name": "Thomas Roux", "phone": "06 78 90 12 34", "email": "thomas.roux@email.fr", "address": "92 Boulevard Saint-Germain, 75006 Paris"},
        {"name": "Camille Fournier", "phone": "06 89 01 23 45", "email": "camille.fournier@email.fr", "address": "34 Rue de la République, 69001 Lyon"},
        {"name": "Antoine Girard", "phone": "06 90 12 34 56", "email": "antoine.girard@email.fr", "address": "56 Cours Lafayette, 69003 Lyon"},
        {"name": "Léa Bonnet", "phone": "06 01 23 45 67", "email": "lea.bonnet@email.fr", "address": "78 Avenue Jean Jaurès, 69007 Lyon"},
    ]
    
    customer_ids = []
    customers_created = 0
    for cust_data in customers_data:
        existing = await db.customers.find_one({"email": cust_data["email"], "tenant_id": TENANT_ID})
        if not existing:
            cust_id = generate_id()
            customer_ids.append(cust_id)
            await db.customers.insert_one({
                "id": cust_id,
                "name": cust_data["name"],
                "phone": cust_data["phone"],
                "email": cust_data["email"],
                "address": cust_data["address"],
                "tenant_id": TENANT_ID,
                "created_at": get_timestamp(random.randint(10, 60))
            })
            customers_created += 1
        else:
            customer_ids.append(existing["id"])
    print(f"       ✓ {customers_created} client(s) créé(s)")
    
    # ============================================
    # 5. FOURNISSEURS
    # ============================================
    print("[5/7] Création des fournisseurs...")
    
    suppliers_data = [
        {"name": "Pharma Distribution", "phone": "01 23 45 67 89", "email": "contact@pharmadistrib.fr", "address": "Zone Industrielle Nord, 93100 Montreuil"},
        {"name": "MedSupply France", "phone": "01 34 56 78 90", "email": "commandes@medsupply.fr", "address": "45 Rue de l'Industrie, 92000 Nanterre"},
        {"name": "Laboratoires Santé+", "phone": "01 45 67 89 01", "email": "pro@santeplus.fr", "address": "12 Avenue de la Recherche, 69100 Villeurbanne"},
        {"name": "Alliance Healthcare", "phone": "01 56 78 90 12", "email": "service@alliance-healthcare.fr", "address": "Parc d'Activités, 31000 Toulouse"},
        {"name": "OCP Répartition", "phone": "01 67 89 01 23", "email": "contact@ocp.fr", "address": "Boulevard de l'Europe, 33000 Bordeaux"},
    ]
    
    suppliers_created = 0
    for supp_data in suppliers_data:
        existing = await db.suppliers.find_one({"email": supp_data["email"], "tenant_id": TENANT_ID})
        if not existing:
            await db.suppliers.insert_one({
                "id": generate_id(),
                "name": supp_data["name"],
                "phone": supp_data["phone"],
                "email": supp_data["email"],
                "address": supp_data["address"],
                "tenant_id": TENANT_ID,
                "created_at": get_timestamp(random.randint(30, 90))
            })
            suppliers_created += 1
    print(f"       ✓ {suppliers_created} fournisseur(s) créé(s)")
    
    # ============================================
    # 6. VENTES
    # ============================================
    print("[6/7] Création des ventes...")
    
    payment_methods = ["cash", "card", "check"]
    sales_created = 0
    
    # Créer 15 ventes sur les 7 derniers jours (avec quelques ventes aujourd'hui)
    for i in range(15):
        # Sélectionner 1-4 produits aléatoires
        num_items = random.randint(1, 4)
        selected_products = random.sample(product_ids, min(num_items, len(product_ids)))
        
        items = []
        total = 0
        for prod in selected_products:
            qty = random.randint(1, 3)
            items.append({
                "product_id": prod["id"],
                "name": prod["name"],
                "price": prod["price"],
                "quantity": qty
            })
            total += prod["price"] * qty
        
        # Client aléatoire (ou anonyme)
        customer_id = random.choice(customer_ids) if random.random() > 0.3 else None
        
        # Les 3 premières ventes sont aujourd'hui (days_ago=0)
        days_ago = 0 if i < 3 else random.randint(1, 7)
        
        await db.sales.insert_one({
            "id": generate_id(),
            "customer_id": customer_id,
            "items": items,
            "total": round(total, 2),
            "payment_method": random.choice(payment_methods),
            "tenant_id": TENANT_ID,
            "created_at": get_timestamp(days_ago)
        })
        sales_created += 1
    
    print(f"       ✓ {sales_created} vente(s) créée(s) (dont 3 aujourd'hui)")
    
    # ============================================
    # 7. ORDONNANCES
    # ============================================
    print("[7/7] Création des ordonnances...")
    
    doctors = ["Dr. Martin", "Dr. Dubois", "Dr. Laurent", "Dr. Simon", "Dr. Michel"]
    statuses = ["pending", "fulfilled", "cancelled"]
    
    # Médicaments de démonstration
    demo_medications = [
        {"name": "Amoxicilline 500mg", "dosage": "3 fois par jour", "quantity": "21 comprimés"},
        {"name": "Doliprane 1000mg", "dosage": "En cas de douleur", "quantity": "8 comprimés"},
        {"name": "Ibuprofène 400mg", "dosage": "2 fois par jour", "quantity": "14 comprimés"},
        {"name": "Ventoline spray", "dosage": "2 bouffées si besoin", "quantity": "1 flacon"},
        {"name": "Augmentin 1g", "dosage": "2 fois par jour", "quantity": "14 comprimés"},
        {"name": "Smecta", "dosage": "3 sachets par jour", "quantity": "12 sachets"},
        {"name": "Toplexil sirop", "dosage": "3 cuillères par jour", "quantity": "1 flacon"},
        {"name": "Vitamine C 1000mg", "dosage": "1 fois par jour", "quantity": "30 comprimés"},
    ]
    
    prescriptions_created = 0
    pending_count = 0
    for i in range(8):
        customer_id = random.choice(customer_ids)
        status = random.choices(statuses, weights=[0.5, 0.4, 0.1])[0]
        if status == "pending":
            pending_count += 1
        
        # Sélectionner 1-3 médicaments aléatoires
        num_meds = random.randint(1, 3)
        selected_meds = random.sample(demo_medications, num_meds)
        
        await db.prescriptions.insert_one({
            "id": generate_id(),
            "customer_id": customer_id,
            "doctor_name": random.choice(doctors),
            "medications": selected_meds,
            "notes": f"Ordonnance du {datetime.now().strftime('%d/%m/%Y')}" if random.random() > 0.5 else None,
            "status": status,
            "tenant_id": TENANT_ID,
            "created_at": get_timestamp(random.randint(0, 14))
        })
        prescriptions_created += 1
    
    print(f"       ✓ {prescriptions_created} ordonnance(s) créée(s) (dont {pending_count} en attente)")
    
    # ============================================
    # RÉSUMÉ
    # ============================================
    print()
    print("=" * 60)
    print("   RÉSUMÉ DE LA CRÉATION")
    print("=" * 60)
    print()
    print("📋 IDENTIFIANTS DE CONNEXION:")
    print("-" * 60)
    print("| Rôle         | Email                      | Mot de passe |")
    print("-" * 60)
    print("| Admin        | admin@pharmaflow.com       | admin123     |")
    print("| Pharmacien   | pharmacien@pharmaflow.com  | pharma123    |")
    print("| Caissier     | caissier@pharmaflow.com    | caisse123    |")
    print("| Demo (Admin) | demo@pharmaflow.com        | demo123      |")
    print("-" * 60)
    print()
    print("📊 DONNÉES CRÉÉES:")
    print(f"   • {len(categories_data)} catégories")
    print(f"   • {len(products_data)} produits")
    print(f"   • {len(customers_data)} clients")
    print(f"   • {len(suppliers_data)} fournisseurs")
    print(f"   • 15 ventes")
    print(f"   • 8 ordonnances")
    print()
    print("💡 Permissions par rôle:")
    print("   - Admin: Accès complet + Gestion utilisateurs")
    print("   - Pharmacien: Produits, Ordonnances, Fournisseurs, Ventes, Clients")
    print("   - Caissier: Ventes, Clients, Tableau de bord uniquement")
    print()
    
    # Fermer la connexion
    client.close()

if __name__ == "__main__":
    asyncio.run(create_demo_data())
