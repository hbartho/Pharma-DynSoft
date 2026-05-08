"""
Test pour vérifier que les rabais ne créent PAS de dette incorrectement.
Bug: Quand un rabais est appliqué, le montant du rabais était incorrectement
enregistré comme une dette client.
"""
import pytest
import os
import sys

# Setup environment
os.environ['SUPABASE_URL'] = 'postgresql://postgres.vwpakvjgnuwyynsixrab:DynSoftPharma1%23@aws-0-us-west-2.pooler.supabase.com:6543/postgres'
os.environ['DATABASE_TYPE'] = 'postgresql'

sys.path.insert(0, '/app/backend')

from database.repositories import ProductRepository
from database.repositories_extended import SaleRepository


class TestDiscountDebtBug:
    """Tests pour le bug rabais-dette"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup des repositories"""
        self.product_repo = ProductRepository()
        self.sale_repo = SaleRepository()
        
        # Récupérer un produit existant
        products = self.product_repo.get_all()
        assert len(products) > 0, "Au moins un produit doit exister"
        self.test_product = products[0]
        print(f"\nProduit de test: {self.test_product['name']}, Prix: {self.test_product['price']}")
    
    def test_sale_with_manual_discount_no_debt(self):
        """
        TEST 1: Vente avec rabais manuel - pas de dette
        
        Scénario:
        - Prix produit: 10000 GNF
        - Quantité: 1
        - Rabais manuel: 2000 GNF
        - Total attendu: 8000 GNF
        - Montant payé: 8000 GNF (paiement complet)
        - Dette attendue: 0 GNF
        """
        price = self.test_product['price']
        quantity = 1
        subtotal = price * quantity
        discount_amount = 2000
        final_total = subtotal - discount_amount
        amount_paid = final_total  # Paiement complet
        
        # Créer les données de vente
        sale_data = {
            'sale_number': 'TEST-DISCOUNT-001',
            'customer_id': None,
            'customer_name': None,
            'items': [
                {
                    'product_id': self.test_product['id'],
                    'product_name': self.test_product['name'],
                    'unit_price': price,
                    'quantity': quantity,
                    'subtotal': subtotal,
                }
            ],
            'subtotal': subtotal,
            'discount_type': 'amount',
            'discount_value': discount_amount,
            'discount_amount': discount_amount,
            'total': final_total,
            'total_ht': final_total,
            'tva_total': 0,
            'payment_method': 'cash',
            'is_split_payment': False,
            'split_payments': None,
            'amount_paid': amount_paid,
            'debt_amount': 0,
            'has_debt': False,
            'employee_code': 'TEST',
            'user_name': 'Test User',
        }
        
        # Créer la vente
        result = self.sale_repo.create(sale_data, sale_data['items'])
        
        print(f"\n=== Résultat de la vente ===")
        print(f"Subtotal: {result.get('subtotal')}")
        print(f"Discount: {result.get('discount_amount')}")
        print(f"Total: {result.get('total')}")
        print(f"Amount Paid: {result.get('amount_paid')}")
        print(f"Debt Amount: {result.get('debt_amount')}")
        print(f"Has Debt: {result.get('has_debt')}")
        
        # Vérifications
        assert result['total'] == final_total, f"Total incorrect: {result['total']} != {final_total}"
        assert result['amount_paid'] == amount_paid, f"Amount paid incorrect: {result['amount_paid']} != {amount_paid}"
        assert result['debt_amount'] == 0, f"DETTE INCORRECTE! La dette devrait être 0, pas {result['debt_amount']}"
        assert result['has_debt'] == False, f"has_debt devrait être False, pas {result['has_debt']}"
        
        print("\n✅ TEST PASSED: Vente avec rabais - pas de dette créée incorrectement")
    
    def test_sale_with_product_discount_no_debt(self):
        """
        TEST 2: Vente avec rabais par produit - pas de dette
        """
        price = self.test_product['price']
        quantity = 2
        subtotal = price * quantity
        product_discount = 1500  # Rabais sur le produit
        final_total = subtotal - product_discount
        amount_paid = final_total
        
        sale_data = {
            'sale_number': 'TEST-DISCOUNT-002',
            'customer_id': None,
            'customer_name': None,
            'items': [
                {
                    'product_id': self.test_product['id'],
                    'product_name': self.test_product['name'],
                    'unit_price': price,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'discount_type': 'amount',
                    'discount_value': product_discount,
                    'discount_amount': product_discount,
                }
            ],
            'subtotal': subtotal,
            'discount_type': None,
            'discount_value': 0,
            'discount_amount': product_discount,  # Total des rabais
            'total': final_total,
            'total_ht': final_total,
            'tva_total': 0,
            'payment_method': 'cash',
            'is_split_payment': False,
            'split_payments': None,
            'amount_paid': amount_paid,
            'debt_amount': 0,
            'has_debt': False,
            'employee_code': 'TEST',
            'user_name': 'Test User',
        }
        
        result = self.sale_repo.create(sale_data, sale_data['items'])
        
        print(f"\n=== Test 2: Rabais produit ===")
        print(f"Subtotal: {result.get('subtotal')}, Total: {result.get('total')}, Paid: {result.get('amount_paid')}, Debt: {result.get('debt_amount')}")
        
        assert result['debt_amount'] == 0, f"DETTE INCORRECTE! {result['debt_amount']}"
        print("✅ TEST PASSED: Rabais produit - pas de dette")
    
    def test_sale_percent_discount_no_debt(self):
        """
        TEST 3: Vente avec rabais en pourcentage - pas de dette
        """
        price = self.test_product['price']
        quantity = 1
        subtotal = price * quantity
        discount_percent = 10  # 10%
        discount_amount = round(subtotal * discount_percent / 100)
        final_total = subtotal - discount_amount
        amount_paid = final_total
        
        sale_data = {
            'sale_number': 'TEST-DISCOUNT-003',
            'customer_id': None,
            'customer_name': None,
            'items': [
                {
                    'product_id': self.test_product['id'],
                    'product_name': self.test_product['name'],
                    'unit_price': price,
                    'quantity': quantity,
                    'subtotal': subtotal,
                }
            ],
            'subtotal': subtotal,
            'discount_type': 'percent',
            'discount_value': discount_percent,
            'discount_amount': discount_amount,
            'total': final_total,
            'total_ht': final_total,
            'tva_total': 0,
            'payment_method': 'cash',
            'is_split_payment': False,
            'split_payments': None,
            'amount_paid': amount_paid,
            'debt_amount': 0,
            'has_debt': False,
            'employee_code': 'TEST',
            'user_name': 'Test User',
        }
        
        result = self.sale_repo.create(sale_data, sale_data['items'])
        
        print(f"\n=== Test 3: Rabais % ===")
        print(f"Subtotal: {result.get('subtotal')}, Discount: {discount_amount}, Total: {result.get('total')}, Paid: {result.get('amount_paid')}, Debt: {result.get('debt_amount')}")
        
        assert result['debt_amount'] == 0, f"DETTE INCORRECTE! {result['debt_amount']}"
        print("✅ TEST PASSED: Rabais % - pas de dette")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
