"""
Script pour créer l'utilisateur de démonstration
DynSoft Pharma
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from dotenv import load_dotenv
from uuid import uuid4

# Charger les variables d'environnement
load_dotenv()

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/pharma_db")
DB_NAME = os.getenv("DB_NAME", "pharma_db")

# Contexte de hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_demo_user():
    """Créer l'utilisateur de démonstration"""
    
    # Connexion à MongoDB
    print(f"Connexion à MongoDB: {MONGO_URL}")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        # Vérifier la connexion
        await client.admin.command('ping')
        print("✓ Connexion MongoDB réussie")
        
        # Données de l'utilisateur de démo
        demo_email = "demo@pharmaflow.com"
        demo_password = "demo123"
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = await db.users.find_one({"email": demo_email}, {"_id": 0})
        
        if existing_user:
            print(f"\n⚠️  L'utilisateur {demo_email} existe déjà")
            print(f"   ID: {existing_user.get('id')}")
            print(f"   Nom: {existing_user.get('full_name')}")
            print(f"   Rôle: {existing_user.get('role')}")
            
            # Demander si on veut réinitialiser le mot de passe
            reset = input("\nVoulez-vous réinitialiser le mot de passe ? (o/n): ")
            if reset.lower() == 'o':
                hashed_password = pwd_context.hash(demo_password)
                await db.users.update_one(
                    {"email": demo_email},
                    {"$set": {"password": hashed_password}}
                )
                print("✓ Mot de passe réinitialisé avec succès")
        else:
            # Créer l'utilisateur
            print(f"\nCréation de l'utilisateur {demo_email}...")
            
            hashed_password = pwd_context.hash(demo_password)
            
            demo_user = {
                "id": str(uuid4()),
                "email": demo_email,
                "password": hashed_password,
                "full_name": "Pharmacien Démo (admin)",
                "role": "admin",
                "tenant_id": "demo_tenant"
            }
            
            await db.users.insert_one(demo_user)
            print("✓ Utilisateur créé avec succès")
        
        # Afficher les informations de connexion
        print("\n" + "="*50)
        print("INFORMATIONS DE CONNEXION")
        print("="*50)
        print(f"Email:        {demo_email}")
        print(f"Mot de passe: {demo_password}")
        print("="*50)
        
        # Compter le nombre total d'utilisateurs
        total_users = await db.users.count_documents({})
        print(f"\n✓ Nombre total d'utilisateurs: {total_users}")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        return False
    finally:
        client.close()
    
    return True

if __name__ == "__main__":
    print("="*50)
    print("Création de l'utilisateur de démonstration")
    print("DynSoft Pharma")
    print("="*50)
    print()
    
    asyncio.run(create_demo_user())
    
    print("\n✓ Terminé")
    input("\nAppuyez sur Entrée pour quitter...")
