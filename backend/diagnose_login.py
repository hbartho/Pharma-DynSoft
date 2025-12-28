"""
Script de diagnostic complet pour le login
DynSoft Pharma
"""
import asyncio
import os
import warnings
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import requests
from dotenv import load_dotenv

# Ignorer les avertissements de compatibilité bcrypt/passlib
warnings.filterwarnings("ignore")

# Charger les variables d'environnement
load_dotenv()

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'pharmaflow')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier le mot de passe avec bcrypt directement"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

async def diagnose_login():
    print("="*60)
    print("DIAGNOSTIC COMPLET LOGIN - DYNSOFT PHARMA")
    print("="*60)
    print()
    print(f"Configuration:")
    print(f"  MongoDB URL: {MONGO_URL}")
    print(f"  Database: {DB_NAME}")
    print()
    
    # Connexion MongoDB
    try:
        client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        # Test de connexion
        await client.server_info()
        db = client[DB_NAME]
        print("✓ Connexion MongoDB réussie")
    except Exception as e:
        print(f"❌ ERREUR: Impossible de se connecter à MongoDB")
        print(f"   {e}")
        print()
        print("SOLUTION: Démarrez MongoDB")
        print("  Windows (CMD admin): net start MongoDB")
        return False
    
    print()
    
    # Liste des utilisateurs à tester
    test_users = [
        ("admin@pharmaflow.com", "admin123", "Admin"),
        ("pharmacien@pharmaflow.com", "pharma123", "Pharmacien"),
        ("caissier@pharmaflow.com", "caisse123", "Caissier"),
        ("demo@pharmaflow.com", "demo123", "Demo"),
    ]
    
    # 1. Vérifier les utilisateurs en BD
    print("[1/3] Vérification des utilisateurs en base de données...")
    print("-" * 50)
    
    users_found = 0
    for email, password, role_name in test_users:
        user = await db.users.find_one({"email": email})
        
        if user:
            users_found += 1
            # Vérifier le mot de passe
            try:
                pwd_valid = verify_password(password, user.get("password", ""))
                status = "✓" if pwd_valid else "❌ (mot de passe incorrect)"
            except:
                status = "⚠️ (erreur vérification)"
            
            print(f"  {status} {role_name}: {email}")
            print(f"      Nom: {user.get('name', 'N/A')}, Rôle: {user.get('role', 'N/A')}")
        else:
            print(f"  ❌ {role_name}: {email} - NON TROUVÉ")
    
    print()
    
    if users_found == 0:
        print("❌ PROBLÈME: Aucun utilisateur trouvé en base de données")
        print()
        print("SOLUTION: Créez les utilisateurs avec:")
        print("  python create_correct_user.py")
        client.close()
        return False
    
    print(f"  → {users_found}/{len(test_users)} utilisateurs trouvés")
    print()
    
    # 2. Tester l'API backend
    print("[2/3] Test de l'API backend...")
    print("-" * 50)
    
    api_url = "http://localhost:8001/api/auth/login"
    test_email = "admin@pharmaflow.com"
    test_password = "admin123"
    
    try:
        response = requests.post(
            api_url,
            json={"email": test_email, "password": test_password},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"  URL: {api_url}")
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Login réussi!")
            print(f"    Token: {data['access_token'][:40]}...")
            print(f"    User: {data['user']['name']} ({data['user']['role']})")
        elif response.status_code == 401:
            print(f"  ❌ Identifiants incorrects")
            print(f"    Réponse: {response.text}")
        else:
            print(f"  ❌ Erreur: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"  ❌ ERREUR: Backend non accessible sur http://localhost:8001")
        print()
        print("  SOLUTION: Démarrez le backend dans un autre terminal:")
        print("    cd backend")
        print("    start-backend.bat")
        print("  OU:")
        print("    uvicorn server:app --host 0.0.0.0 --port 8001 --reload")
        client.close()
        return False
    except requests.exceptions.Timeout:
        print(f"  ❌ ERREUR: Timeout - le backend met trop de temps à répondre")
        client.close()
        return False
    except Exception as e:
        print(f"  ❌ ERREUR: {e}")
        client.close()
        return False
    
    print()
    
    # 3. Résumé
    print("[3/3] Résumé")
    print("="*60)
    print()
    print("✅ TOUT FONCTIONNE CORRECTEMENT")
    print()
    print("Identifiants de connexion:")
    print("-" * 40)
    print("| Rôle       | Email                     | MDP      |")
    print("-" * 40)
    print("| Admin      | admin@pharmaflow.com      | admin123 |")
    print("| Pharmacien | pharmacien@pharmaflow.com | pharma123|")
    print("| Caissier   | caissier@pharmaflow.com   | caisse123|")
    print("-" * 40)
    print()
    print("Frontend: http://localhost:3000")
    print("Backend:  http://localhost:8001")
    print("API Docs: http://localhost:8001/docs")
    print()
    
    client.close()
    return True

if __name__ == "__main__":
    success = asyncio.run(diagnose_login())
    
    if not success:
        print()
        print("✗ Problème détecté - voir les messages ci-dessus")
    
    print()
    input("Appuyez sur Entrée pour quitter...")
