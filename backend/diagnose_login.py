"""
Script de diagnostic complet pour le login
DynSoft Pharma
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
import requests
import json

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def diagnose_login():
    print("="*60)
    print("DIAGNOSTIC COMPLET LOGIN")
    print("="*60)
    print()
    
    # Connexion MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["pharma_db"]
    
    email = "demo@pharmaflow.com"
    password = "demo123"
    
    # 1. Vérifier l'utilisateur en BD
    print("[1/4] Vérification utilisateur en base de données...")
    user = await db.users.find_one({"email": email})
    
    if not user:
        print(f"❌ PROBLÈME : Utilisateur {email} introuvable en BD")
        print()
        print("SOLUTION : Créez l'utilisateur avec :")
        print("  python add_user.py")
        client.close()
        return False
    
    print(f"✓ Utilisateur trouvé :")
    print(f"  Email : {user.get('email')}")
    print(f"  Name : {user.get('name', 'NON DÉFINI')}")
    print(f"  Full Name : {user.get('full_name', 'NON DÉFINI')}")
    print(f"  Role : {user.get('role')}")
    print(f"  Tenant ID : {user.get('tenant_id')}")
    print()
    
    # Vérifier le champ name
    if 'name' not in user or not user['name']:
        print("⚠️ ATTENTION : Le champ 'name' est manquant ou vide !")
        print("Le backend attend un champ 'name', pas 'full_name'")
        print()
    
    # 2. Vérifier le mot de passe
    print("[2/4] Vérification du mot de passe...")
    stored_password = user.get("password")
    
    if not stored_password:
        print("❌ PROBLÈME : Pas de mot de passe en base")
        client.close()
        return False
    
    print(f"  Password hash : {stored_password[:30]}...")
    
    try:
        is_valid = pwd_context.verify(password, stored_password)
        
        if is_valid:
            print(f"✓ Mot de passe correct")
        else:
            print(f"❌ PROBLÈME : Mot de passe incorrect")
            print(f"   Le hash ne correspond pas au mot de passe '{password}'")
            client.close()
            return False
    except Exception as e:
        print(f"❌ PROBLÈME : Erreur de vérification : {e}")
        client.close()
        return False
    
    print()
    
    # 3. Tester l'API avec requests
    print("[3/4] Test de l'API backend avec requests...")
    
    try:
        response = requests.post(
            "http://localhost:8001/api/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        print(f"  Status code : {response.status_code}")
        
        if response.status_code == 200:
            print(f"✓ API fonctionne correctement")
            data = response.json()
            print(f"  Token reçu : {data['access_token'][:30]}...")
            print(f"  User : {data['user']['email']}")
        else:
            print(f"❌ PROBLÈME : API retourne une erreur")
            print(f"  Réponse : {response.text}")
            client.close()
            return False
    except requests.exceptions.ConnectionError:
        print("❌ PROBLÈME : Impossible de se connecter au backend")
        print("  Le backend est-il démarré sur le port 8001 ?")
        print()
        print("SOLUTION : Démarrez le backend :")
        print("  cd backend")
        print("  venv\\Scripts\\activate.bat")
        print("  uvicorn server:app --host 0.0.0.0 --port 8001 --reload")
        client.close()
        return False
    except Exception as e:
        print(f"❌ PROBLÈME : Erreur lors du test API : {e}")
        client.close()
        return False
    
    print()
    
    # 4. Résumé
    print("[4/4] Résumé...")
    print()
    print("="*60)
    print("✅ DIAGNOSTIC COMPLET")
    print("="*60)
    print()
    print("Base de données :")
    print(f"  ✓ Utilisateur {email} existe")
    print(f"  ✓ Mot de passe correct")
    print()
    print("Backend API :")
    print(f"  ✓ Backend accessible sur http://localhost:8001")
    print(f"  ✓ Login API fonctionne")
    print()
    print("Le problème vient du FRONTEND")
    print()
    print("Vérifications à faire :")
    print("1. Ouvrir http://localhost:3000")
    print("2. Appuyer sur F12 → Console")
    print("3. Essayer de se connecter")
    print("4. Regarder les erreurs dans la console")
    print()
    print("5. F12 → Network → Chercher 'login'")
    print("6. Vérifier la requête envoyée (Payload)")
    print("7. Vérifier la réponse (Response)")
    print()
    print("Identifiants de connexion :")
    print(f"  Email : {email}")
    print(f"  Password : {password}")
    print("="*60)
    
    client.close()
    return True

if __name__ == "__main__":
    success = asyncio.run(diagnose_login())
    
    if success:
        print()
        print("✓ Backend et base de données OK")
        print("  Le problème vient probablement du frontend")
        print()
    else:
        print()
        print("✗ Problème détecté, voir les messages ci-dessus")
        print()
    
    input("\nAppuyez sur Entrée pour quitter...")
