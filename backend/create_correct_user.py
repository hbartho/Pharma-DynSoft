#!/usr/bin/env python3
"""
Script pour créer les utilisateurs de démonstration dans la base de données.
Crée un administrateur, un pharmacien et un caissier avec les bons champs.

Usage:
    python create_correct_user.py

Les utilisateurs créés:
    - Admin: admin@pharmaflow.com / admin123
    - Pharmacien: pharmacien@pharmaflow.com / pharma123  
    - Caissier: caissier@pharmaflow.com / caisse123
"""

import asyncio
import os
from datetime import datetime, timezone
from uuid import uuid4
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'pharmaflow')

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

async def create_users():
    """Créer les utilisateurs de démonstration"""
    
    # Connexion à MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Définition des utilisateurs à créer
    users_to_create = [
        {
            "id": str(uuid4()),
            "email": "admin@pharmaflow.com",
            "password": hash_password("admin123"),
            "name": "Administrateur",
            "role": "admin",
            "tenant_id": "default",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "email": "pharmacien@pharmaflow.com",
            "password": hash_password("pharma123"),
            "name": "Jean Pharmacien",
            "role": "pharmacien",
            "tenant_id": "default",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid4()),
            "email": "caissier@pharmaflow.com",
            "password": hash_password("caisse123"),
            "name": "Marie Caissière",
            "role": "caissier",
            "tenant_id": "default",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        # Garder l'utilisateur demo existant (admin)
        {
            "id": str(uuid4()),
            "email": "demo@pharmaflow.com",
            "password": hash_password("demo123"),
            "name": "Pharmacien Démo",
            "role": "admin",
            "tenant_id": "default",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    print("=" * 60)
    print("   CRÉATION DES UTILISATEURS DYNSOFT PHARMA")
    print("=" * 60)
    print()
    
    created_count = 0
    skipped_count = 0
    
    for user_data in users_to_create:
        # Vérifier si l'utilisateur existe déjà
        existing = await db.users.find_one({"email": user_data["email"]})
        
        if existing:
            print(f"⚠️  Utilisateur existant: {user_data['email']} ({user_data['role']})")
            skipped_count += 1
            
            # Mettre à jour pour s'assurer que tous les champs requis sont présents
            update_fields = {}
            if 'name' not in existing:
                update_fields['name'] = user_data['name']
            if 'created_at' not in existing:
                update_fields['created_at'] = user_data['created_at']
            if 'is_active' not in existing:
                update_fields['is_active'] = True
                
            if update_fields:
                await db.users.update_one(
                    {"email": user_data["email"]},
                    {"$set": update_fields}
                )
                print(f"   → Champs mis à jour: {list(update_fields.keys())}")
        else:
            # Créer le nouvel utilisateur
            await db.users.insert_one(user_data)
            print(f"✅ Utilisateur créé: {user_data['email']}")
            print(f"   → Nom: {user_data['name']}")
            print(f"   → Rôle: {user_data['role']}")
            created_count += 1
        
        print()
    
    print("=" * 60)
    print(f"   RÉSUMÉ: {created_count} créé(s), {skipped_count} existant(s)")
    print("=" * 60)
    print()
    print("📋 IDENTIFIANTS DE CONNEXION:")
    print("-" * 60)
    print("| Rôle         | Email                      | Mot de passe |")
    print("-" * 60)
    print("| Admin        | admin@pharmaflow.com       | admin123     |")
    print("| Admin (demo) | demo@pharmaflow.com        | demo123      |")
    print("| Pharmacien   | pharmacien@pharmaflow.com  | pharma123    |")
    print("| Caissier     | caissier@pharmaflow.com    | caisse123    |")
    print("-" * 60)
    print()
    print("💡 Permissions par rôle:")
    print("   - Admin: Accès complet + Gestion utilisateurs")
    print("   - Pharmacien: Produits, Ordonnances, Fournisseurs, Ventes, Clients, Rapports")
    print("   - Caissier: Ventes, Clients, Tableau de bord uniquement")
    print()
    
    # Fermer la connexion
    client.close()

if __name__ == "__main__":
    asyncio.run(create_users())
