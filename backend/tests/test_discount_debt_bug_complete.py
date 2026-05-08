"""
Test complet du bug rabais-dette - Vérification finale
Bug critique: Quand un rabais était appliqué à une vente, le montant du rabais 
était incorrectement enregistré comme une dette client au lieu d'être simplement 
déduit du total.

Correction: backend/routes/sales.py - calcul correct de total_discount_amount 
incluant tous les types de rabais (manuel + promo + automatique + produit)

Tests:
1. Vente avec rabais manuel - debt_amount = 0
2. Vente avec rabais par produit - debt_amount = 0
3. Vente avec code promo (si disponible) - debt_amount = 0
4. Vente SANS rabais - fonctionnement normal
5. Vérifier l'historique des rabais
"""
import pytest
import requests
import json
import sys
import os
import uuid
from datetime import datetime

# Configuration
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pharmacy-mgmt-portal.preview.emergentagent.com')

# Setup pour la connexion directe
os.environ['SUPABASE_URL'] = 'postgresql://postgres.vwpakvjgnuwyynsixrab:DynSoftPharma1%23@aws-0-us-west-2.pooler.supabase.com:6543/postgres'
os.environ['DATABASE_TYPE'] = 'postgresql'

sys.path.insert(0, '/app/backend')


class TestDiscountDebtBugComplete:
    """Tests complets pour le bug rabais-dette"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup initial - obtenir token et produit de test"""
        self.base_url = BASE_URL
        self.token = self._get_token()
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        self.test_product = self._get_test_product()
        print(f"\n[Setup] Produit de test: {self.test_product['name']}, Prix: {self.test_product['price']}")
    
    def _get_token(self):
        """Obtenir un token d'authentification"""
        from database.config import db_manager
        from database.models_tenant import User
        from auth import create_access_token, generate_session_id
        
        with db_manager.get_master_session() as session:
            admin = session.query(User).filter(User.email == 'admin@pharmaflow.com').first()
            if admin:
                session_id = generate_session_id()
                token = create_access_token({
                    "sub": str(admin.id),
                    "role": admin.role,
                    "employee_code": admin.employee_code or 'ADMIN',
                    "tenant_id": "default"
                }, session_id)
                return token
        raise Exception("Impossible d'obtenir le token admin")
    
    def _get_test_product(self):
        """Récupérer un produit avec du stock"""
        from database.repositories import ProductRepository
        product_repo = ProductRepository()
        products = product_repo.get_all()
        
        # Trouver un produit avec du stock
        for p in products:
            if p.get('stock', 0) > 0:
                return p
        
        # Sinon retourner le premier
        if products:
            return products[0]
        raise Exception("Aucun produit disponible pour les tests")
    
    def _create_sale(self, sale_data):
        """Créer une vente via l'API"""
        response = requests.post(
            f"{self.base_url}/api/sales",
            headers=self.headers,
            json=sale_data,
            timeout=30
        )
        return response
    
    def test_01_sale_with_manual_discount_no_debt(self):
        """
        TEST 1: Vente avec rabais manuel - debt_amount doit être 0
        
        Scénario:
        - Produit avec prix X
        - Quantité: 1
        - Rabais manuel: 2000 GNF
        - Total = Prix - Rabais
        - Paiement complet
        - RÉSULTAT ATTENDU: debt_amount = 0
        """
        price = self.test_product['price']
        quantity = 1
        subtotal = price * quantity
        discount_amount = 2000  # Rabais manuel de 2000 GNF
        final_total = subtotal - discount_amount
        amount_paid = final_total  # Paiement complet
        
        sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": self.test_product['id'],
                "product_name": self.test_product['name'],
                "unit_price": price,
                "quantity": quantity,
                "subtotal": subtotal,
                "discount_type": None,
                "discount_value": 0,
                "discount_amount": 0,
                "discount_reason": None,
                "final_subtotal": subtotal
            }],
            "subtotal": subtotal,
            # Rabais MANUEL (global)
            "discount_type": "amount",
            "discount_value": discount_amount,
            "discount_amount": discount_amount,
            # Pas de code promo
            "promo_code": None,
            "promo_discount_amount": 0,
            # Pas de rabais automatique
            "automatic_discounts": [],
            "automatic_discount_amount": 0,
            # Total des rabais
            "total_discount_amount": discount_amount,
            "total": final_total,
            "payment_method": "cash",
            "payment_details": None,
            "amount_paid": amount_paid,
            "debt_amount": 0,
            "is_split_payment": False,
            "split_payments": None
        }
        
        print(f"\n=== TEST 1: Rabais manuel ===")
        print(f"   Subtotal: {subtotal}")
        print(f"   Rabais manuel: {discount_amount}")
        print(f"   Total attendu: {final_total}")
        print(f"   Montant payé: {amount_paid}")
        
        response = self._create_sale(sale_data)
        
        assert response.status_code == 200, f"API error: {response.text}"
        
        result = response.json()
        print(f"\n   RÉSULTAT:")
        print(f"   - Total: {result.get('total')}")
        print(f"   - Amount Paid: {result.get('amount_paid')}")
        print(f"   - Debt Amount: {result.get('debt_amount')}")
        print(f"   - Has Debt: {result.get('has_debt')}")
        
        # VÉRIFICATION CRITIQUE
        assert result.get('debt_amount', 0) == 0, \
            f"BUG: debt_amount devrait être 0, pas {result.get('debt_amount')}!"
        assert result.get('has_debt') == False, \
            f"BUG: has_debt devrait être False!"
        assert result.get('total') == final_total, \
            f"Total incorrect: {result.get('total')} != {final_total}"
        assert result.get('amount_paid') == amount_paid, \
            f"Amount paid incorrect: {result.get('amount_paid')} != {amount_paid}"
        
        print("   ✅ TEST PASSED: Rabais manuel - pas de dette incorrecte")
        return result.get('id')
    
    def test_02_sale_with_product_discount_no_debt(self):
        """
        TEST 2: Vente avec rabais par produit - debt_amount doit être 0
        """
        price = self.test_product['price']
        quantity = 2
        subtotal = price * quantity
        product_discount = 1500  # Rabais sur le produit
        final_total = subtotal - product_discount
        amount_paid = final_total
        
        sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": self.test_product['id'],
                "product_name": self.test_product['name'],
                "unit_price": price,
                "quantity": quantity,
                "subtotal": subtotal,
                # Rabais PAR PRODUIT
                "discount_type": "amount",
                "discount_value": product_discount,
                "discount_amount": product_discount,
                "discount_reason": "Promotion test",
                "final_subtotal": subtotal - product_discount
            }],
            "subtotal": subtotal,
            # Pas de rabais manuel global
            "discount_type": None,
            "discount_value": 0,
            "discount_amount": 0,
            "promo_code": None,
            "promo_discount_amount": 0,
            "automatic_discounts": [],
            "automatic_discount_amount": 0,
            "total_discount_amount": product_discount,
            "total": final_total,
            "payment_method": "cash",
            "payment_details": None,
            "amount_paid": amount_paid,
            "debt_amount": 0,
            "is_split_payment": False,
            "split_payments": None
        }
        
        print(f"\n=== TEST 2: Rabais par produit ===")
        print(f"   Subtotal: {subtotal}")
        print(f"   Rabais produit: {product_discount}")
        print(f"   Total attendu: {final_total}")
        
        response = self._create_sale(sale_data)
        
        assert response.status_code == 200, f"API error: {response.text}"
        
        result = response.json()
        print(f"\n   RÉSULTAT: Total={result.get('total')}, Paid={result.get('amount_paid')}, Debt={result.get('debt_amount')}")
        
        # VÉRIFICATION CRITIQUE
        assert result.get('debt_amount', 0) == 0, \
            f"BUG: debt_amount devrait être 0, pas {result.get('debt_amount')}!"
        assert result.get('has_debt') == False, \
            f"BUG: has_debt devrait être False!"
        
        print("   ✅ TEST PASSED: Rabais produit - pas de dette incorrecte")
    
    def test_03_sale_with_percent_discount_no_debt(self):
        """
        TEST 3: Vente avec rabais en pourcentage - debt_amount doit être 0
        """
        price = self.test_product['price']
        quantity = 1
        subtotal = price * quantity
        discount_percent = 15  # 15%
        discount_amount = round(subtotal * discount_percent / 100)
        final_total = subtotal - discount_amount
        amount_paid = final_total
        
        sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": self.test_product['id'],
                "product_name": self.test_product['name'],
                "unit_price": price,
                "quantity": quantity,
                "subtotal": subtotal,
                "discount_type": None,
                "discount_value": 0,
                "discount_amount": 0,
                "discount_reason": None,
                "final_subtotal": subtotal
            }],
            "subtotal": subtotal,
            # Rabais en %
            "discount_type": "percent",
            "discount_value": discount_percent,
            "discount_amount": discount_amount,
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
        
        print(f"\n=== TEST 3: Rabais en pourcentage ===")
        print(f"   Subtotal: {subtotal}")
        print(f"   Rabais: {discount_percent}% = {discount_amount}")
        print(f"   Total attendu: {final_total}")
        
        response = self._create_sale(sale_data)
        
        assert response.status_code == 200, f"API error: {response.text}"
        
        result = response.json()
        print(f"\n   RÉSULTAT: Total={result.get('total')}, Paid={result.get('amount_paid')}, Debt={result.get('debt_amount')}")
        
        # VÉRIFICATION CRITIQUE
        assert result.get('debt_amount', 0) == 0, \
            f"BUG: debt_amount devrait être 0, pas {result.get('debt_amount')}!"
        
        print("   ✅ TEST PASSED: Rabais % - pas de dette incorrecte")
    
    def test_04_sale_without_discount_normal(self):
        """
        TEST 4: Vente SANS rabais - fonctionnement normal
        """
        price = self.test_product['price']
        quantity = 1
        subtotal = price * quantity
        final_total = subtotal  # Pas de rabais
        amount_paid = final_total
        
        sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": self.test_product['id'],
                "product_name": self.test_product['name'],
                "unit_price": price,
                "quantity": quantity,
                "subtotal": subtotal,
                "discount_type": None,
                "discount_value": 0,
                "discount_amount": 0,
                "discount_reason": None,
                "final_subtotal": subtotal
            }],
            "subtotal": subtotal,
            "discount_type": None,
            "discount_value": 0,
            "discount_amount": 0,
            "promo_code": None,
            "promo_discount_amount": 0,
            "automatic_discounts": [],
            "automatic_discount_amount": 0,
            "total_discount_amount": 0,
            "total": final_total,
            "payment_method": "cash",
            "payment_details": None,
            "amount_paid": amount_paid,
            "debt_amount": 0,
            "is_split_payment": False,
            "split_payments": None
        }
        
        print(f"\n=== TEST 4: Vente SANS rabais ===")
        print(f"   Subtotal: {subtotal}")
        print(f"   Total: {final_total}")
        
        response = self._create_sale(sale_data)
        
        assert response.status_code == 200, f"API error: {response.text}"
        
        result = response.json()
        print(f"\n   RÉSULTAT: Total={result.get('total')}, Paid={result.get('amount_paid')}, Debt={result.get('debt_amount')}")
        
        assert result.get('debt_amount', 0) == 0, \
            f"Vente sans rabais: dette devrait être 0!"
        assert result.get('total') == final_total, \
            f"Total incorrect sans rabais"
        
        print("   ✅ TEST PASSED: Vente sans rabais - fonctionnement normal")
    
    def test_05_sale_with_combined_discounts_no_debt(self):
        """
        TEST 5: Vente avec rabais combinés (produit + manuel) - debt_amount = 0
        """
        price = self.test_product['price']
        quantity = 3
        subtotal = price * quantity
        product_discount = 500  # Par produit
        manual_discount = 1000  # Manuel global
        total_discount = product_discount + manual_discount
        final_total = subtotal - total_discount
        amount_paid = final_total
        
        sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": self.test_product['id'],
                "product_name": self.test_product['name'],
                "unit_price": price,
                "quantity": quantity,
                "subtotal": subtotal,
                "discount_type": "amount",
                "discount_value": product_discount,
                "discount_amount": product_discount,
                "discount_reason": "Rabais produit",
                "final_subtotal": subtotal - product_discount
            }],
            "subtotal": subtotal,
            # Rabais manuel global en plus
            "discount_type": "amount",
            "discount_value": manual_discount,
            "discount_amount": manual_discount,
            "promo_code": None,
            "promo_discount_amount": 0,
            "automatic_discounts": [],
            "automatic_discount_amount": 0,
            "total_discount_amount": total_discount,
            "total": final_total,
            "payment_method": "cash",
            "payment_details": None,
            "amount_paid": amount_paid,
            "debt_amount": 0,
            "is_split_payment": False,
            "split_payments": None
        }
        
        print(f"\n=== TEST 5: Rabais combinés ===")
        print(f"   Subtotal: {subtotal}")
        print(f"   Rabais produit: {product_discount}")
        print(f"   Rabais manuel: {manual_discount}")
        print(f"   Total rabais: {total_discount}")
        print(f"   Total attendu: {final_total}")
        
        response = self._create_sale(sale_data)
        
        assert response.status_code == 200, f"API error: {response.text}"
        
        result = response.json()
        print(f"\n   RÉSULTAT: Total={result.get('total')}, Paid={result.get('amount_paid')}, Debt={result.get('debt_amount')}")
        
        # VÉRIFICATION CRITIQUE
        assert result.get('debt_amount', 0) == 0, \
            f"BUG: debt_amount devrait être 0, pas {result.get('debt_amount')}!"
        
        print("   ✅ TEST PASSED: Rabais combinés - pas de dette incorrecte")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
