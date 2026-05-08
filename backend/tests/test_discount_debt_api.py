"""
Test complet de l'API pour vérifier le bug rabais-dette.
Ce test simule une vente complète via l'endpoint /api/sales.
"""
import requests
import json
import sys
import os

# Configuration
API_URL = "https://pharmacy-mgmt-portal.preview.emergentagent.com"

# Setup pour la connexion directe à la base de données
os.environ['SUPABASE_URL'] = 'postgresql://postgres.vwpakvjgnuwyynsixrab:DynSoftPharma1%23@aws-0-us-west-2.pooler.supabase.com:6543/postgres'
os.environ['DATABASE_TYPE'] = 'postgresql'

sys.path.insert(0, '/app/backend')


def get_test_token():
    """Obtenir un token d'authentification pour les tests."""
    from database.config import db_manager
    from database.models_tenant import User
    from passlib.context import CryptContext
    from auth import create_access_token, generate_session_id
    
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    
    # Mettre à jour le mot de passe admin pour le test
    with db_manager.get_master_session() as session:
        admin = session.query(User).filter(User.email == 'admin@pharmaflow.com').first()
        if admin:
            # Créer un token directement
            session_id = generate_session_id()
            token = create_access_token({
                "sub": str(admin.id),
                "role": admin.role,
                "employee_code": admin.employee_code or 'ADMIN',
                "tenant_id": "default"
            }, session_id)
            return token
    return None


def test_sale_with_discount_via_api():
    """
    Test de vente avec rabais via l'API.
    Vérifie que le rabais ne crée pas de dette incorrecte.
    """
    print("\n" + "="*60)
    print("TEST: Vente avec rabais via l'API")
    print("="*60)
    
    # Obtenir un token
    token = get_test_token()
    if not token:
        print("❌ Impossible d'obtenir un token de test")
        return False
    
    print(f"✅ Token obtenu: {token[:30]}...")
    
    # Récupérer un produit existant
    from database.repositories import ProductRepository
    product_repo = ProductRepository()
    products = product_repo.get_all()
    
    if not products:
        print("❌ Aucun produit trouvé")
        return False
    
    test_product = products[0]
    print(f"✅ Produit de test: {test_product['name']}, Prix: {test_product['price']}")
    
    # Préparer les données de vente avec rabais
    price = test_product['price']
    quantity = 1
    subtotal = price * quantity
    discount_amount = 2500  # Rabais de 2500 GNF
    final_total = subtotal - discount_amount
    amount_paid = final_total  # Paiement complet
    
    sale_data = {
        "customer_id": None,
        "items": [
            {
                "product_id": test_product['id'],
                "product_name": test_product['name'],
                "unit_price": price,
                "quantity": quantity,
                "subtotal": subtotal,
                "discount_type": None,
                "discount_value": 0,
                "discount_amount": 0,
                "discount_reason": None,
                "final_subtotal": subtotal
            }
        ],
        "subtotal": subtotal,
        "discount_type": "amount",
        "discount_value": discount_amount,
        "discount_amount": discount_amount,  # Rabais manuel
        "promo_code": None,
        "promo_discount_amount": 0,
        "automatic_discounts": [],
        "automatic_discount_amount": 0,
        "total_discount_amount": discount_amount,
        "total": final_total,
        "payment_method": "cash",
        "payment_details": None,
        "amount_paid": amount_paid,
        "debt_amount": 0,
        "is_split_payment": False,
        "split_payments": None
    }
    
    print(f"\n📤 Données envoyées:")
    print(f"   Subtotal: {subtotal}")
    print(f"   Rabais: {discount_amount}")
    print(f"   Total: {final_total}")
    print(f"   Montant payé: {amount_paid}")
    print(f"   Dette demandée: 0")
    
    # Envoyer la requête
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.post(
        f"{API_URL}/api/sales",
        headers=headers,
        json=sale_data,
        timeout=30
    )
    
    print(f"\n📥 Réponse API: Status {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Erreur API: {response.text}")
        return False
    
    result = response.json()
    
    print(f"\n📊 Résultat de la vente:")
    print(f"   ID: {result.get('id', 'N/A')}")
    print(f"   Numéro: {result.get('sale_number', 'N/A')}")
    print(f"   Subtotal: {result.get('subtotal')}")
    print(f"   Discount: {result.get('discount_amount')}")
    print(f"   Total: {result.get('total')}")
    print(f"   Amount Paid: {result.get('amount_paid')}")
    print(f"   Debt Amount: {result.get('debt_amount')}")
    print(f"   Has Debt: {result.get('has_debt')}")
    
    # Vérifications
    errors = []
    
    if result.get('total') != final_total:
        errors.append(f"Total incorrect: {result.get('total')} != {final_total}")
    
    if result.get('amount_paid') != amount_paid:
        errors.append(f"Amount paid incorrect: {result.get('amount_paid')} != {amount_paid}")
    
    if result.get('debt_amount', 0) != 0:
        errors.append(f"DETTE INCORRECTE! La dette devrait être 0, pas {result.get('debt_amount')}")
    
    if result.get('has_debt'):
        errors.append(f"has_debt devrait être False, pas {result.get('has_debt')}")
    
    if errors:
        print("\n❌ ÉCHEC DU TEST:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print("\n✅ TEST RÉUSSI: Vente avec rabais - pas de dette créée incorrectement!")
    return True


def test_sale_with_product_discount_via_api():
    """
    Test de vente avec rabais par produit via l'API.
    """
    print("\n" + "="*60)
    print("TEST: Vente avec rabais par produit via l'API")
    print("="*60)
    
    token = get_test_token()
    if not token:
        print("❌ Impossible d'obtenir un token")
        return False
    
    from database.repositories import ProductRepository
    product_repo = ProductRepository()
    products = product_repo.get_all()
    test_product = products[0]
    
    price = test_product['price']
    quantity = 2
    subtotal = price * quantity
    product_discount = 1500  # Rabais sur le produit
    final_total = subtotal - product_discount
    amount_paid = final_total
    
    sale_data = {
        "customer_id": None,
        "items": [
            {
                "product_id": test_product['id'],
                "product_name": test_product['name'],
                "unit_price": price,
                "quantity": quantity,
                "subtotal": subtotal,
                "discount_type": "amount",
                "discount_value": product_discount,
                "discount_amount": product_discount,
                "discount_reason": "Promotion test",
                "final_subtotal": subtotal - product_discount
            }
        ],
        "subtotal": subtotal,
        "discount_type": None,
        "discount_value": 0,
        "discount_amount": 0,  # Pas de rabais manuel global
        "promo_code": None,
        "promo_discount_amount": 0,
        "automatic_discounts": [],
        "automatic_discount_amount": 0,
        "total_discount_amount": product_discount,  # Total = rabais produit
        "total": final_total,
        "payment_method": "cash",
        "payment_details": None,
        "amount_paid": amount_paid,
        "debt_amount": 0,
        "is_split_payment": False,
        "split_payments": None
    }
    
    print(f"\n📤 Données envoyées:")
    print(f"   Subtotal: {subtotal}")
    print(f"   Rabais produit: {product_discount}")
    print(f"   Total: {final_total}")
    print(f"   Montant payé: {amount_paid}")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.post(
        f"{API_URL}/api/sales",
        headers=headers,
        json=sale_data,
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"❌ Erreur API: {response.text}")
        return False
    
    result = response.json()
    
    print(f"\n📊 Résultat:")
    print(f"   Total: {result.get('total')}, Paid: {result.get('amount_paid')}, Debt: {result.get('debt_amount')}")
    
    if result.get('debt_amount', 0) != 0:
        print(f"❌ DETTE INCORRECTE! {result.get('debt_amount')}")
        return False
    
    print("✅ TEST RÉUSSI: Rabais produit - pas de dette!")
    return True


if __name__ == '__main__':
    print("\n" + "="*60)
    print("TESTS DU BUG RABAIS-DETTE")
    print("="*60)
    
    results = []
    
    # Test 1: Rabais manuel
    results.append(("Rabais manuel", test_sale_with_discount_via_api()))
    
    # Test 2: Rabais par produit
    results.append(("Rabais produit", test_sale_with_product_discount_via_api()))
    
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {name}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("🎉 TOUS LES TESTS ONT RÉUSSI!")
        sys.exit(0)
    else:
        print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ!")
        sys.exit(1)
