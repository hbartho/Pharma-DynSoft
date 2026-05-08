"""
Test suite for Split Payments (Paiements Multiples) feature
Tests:
- Simple payment (cash only)
- Mixed payment (Orange Money + Cash)
- Mixed payment with debt (Cash + Debt)
- Debt creation verification
- Split payments display in sales list
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
PRODUCT_ID = "f6bfce32-24ae-4600-8c8b-3ca28da4cc0d"  # Diazépam 10mg - Price: 7700
CUSTOMER_WITH_CREDIT_ID = "5a9c8e27-c1a3-4b89-9111-921a4dfee284"  # Mamadou Camara - max_debt: 500000
CUSTOMER_NO_CREDIT_ID = "49b26551-0000-0000-0000-000000000000"  # Ibrahim Diallo - max_debt: 0

class TestSplitPayments:
    """Test suite for split payments functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        
        self.session.close()
    
    # ==================== SIMPLE PAYMENT TESTS ====================
    
    def test_01_simple_cash_payment(self):
        """TEST 1: Create sale with simple cash payment"""
        sale_data = {
            "items": [{
                "product_id": PRODUCT_ID,
                "quantity": 1,
                "unit_price": 7700,
                "subtotal": 7700
            }],
            "total": 7700,
            "payment_method": "cash",
            "is_split_payment": False
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        
        sale = response.json()
        assert sale["payment_method"] == "cash"
        assert sale["is_split_payment"] == False
        assert sale["split_payments"] is None or sale["split_payments"] == []
        assert sale["has_debt"] == False
        assert sale["total"] == 7700
        
        print(f"✓ TEST 1 PASSED: Simple cash payment - Sale ID: {sale['id'][:8]}...")
        return sale
    
    def test_02_simple_orange_money_payment(self):
        """TEST 2: Create sale with simple Orange Money payment"""
        sale_data = {
            "items": [{
                "product_id": PRODUCT_ID,
                "quantity": 1,
                "unit_price": 7700,
                "subtotal": 7700
            }],
            "total": 7700,
            "payment_method": "orange_money",
            "payment_details": {
                "sender_number": "+224622102030",
                "ticket_ref": "OM-TEST-001"
            },
            "is_split_payment": False
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        
        sale = response.json()
        assert sale["payment_method"] == "orange_money"
        assert sale["is_split_payment"] == False
        assert sale["has_debt"] == False
        
        print(f"✓ TEST 2 PASSED: Simple Orange Money payment - Sale ID: {sale['id'][:8]}...")
        return sale
    
    # ==================== SPLIT PAYMENT TESTS ====================
    
    def test_03_split_payment_orange_money_plus_cash(self):
        """TEST 3: Create sale with split payment (Orange Money + Cash)"""
        total = 15400  # 2 units of Diazépam
        
        sale_data = {
            "items": [{
                "product_id": PRODUCT_ID,
                "quantity": 2,
                "unit_price": 7700,
                "subtotal": 15400
            }],
            "total": total,
            "payment_method": "mixed",
            "is_split_payment": True,
            "split_payments": [
                {
                    "method": "orange_money",
                    "amount": 10000,
                    "details": {
                        "sender_number": "+224622102030",
                        "ticket_ref": "OM-SPLIT-001"
                    }
                },
                {
                    "method": "cash",
                    "amount": 5400,
                    "details": None
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        
        sale = response.json()
        assert sale["payment_method"] == "mixed"
        assert sale["is_split_payment"] == True
        assert sale["split_payments"] is not None
        assert len(sale["split_payments"]) == 2
        assert sale["has_debt"] == False
        
        # Verify split payment amounts
        split_total = sum(sp["amount"] for sp in sale["split_payments"])
        assert split_total == total, f"Split total {split_total} != sale total {total}"
        
        # Verify payment methods in split
        methods = [sp["method"] for sp in sale["split_payments"]]
        assert "orange_money" in methods
        assert "cash" in methods
        
        print(f"✓ TEST 3 PASSED: Split payment (Orange Money + Cash) - Sale ID: {sale['id'][:8]}...")
        return sale
    
    def test_04_split_payment_cash_plus_debt(self):
        """TEST 4: Create sale with split payment including debt (Cash + Debt)"""
        total = 15400  # 2 units of Diazépam
        cash_amount = 10000
        debt_amount = 5400
        
        sale_data = {
            "customer_id": CUSTOMER_WITH_CREDIT_ID,
            "items": [{
                "product_id": PRODUCT_ID,
                "quantity": 2,
                "unit_price": 7700,
                "subtotal": 15400
            }],
            "total": total,
            "payment_method": "mixed",
            "is_split_payment": True,
            "split_payments": [
                {
                    "method": "cash",
                    "amount": cash_amount,
                    "details": None
                },
                {
                    "method": "debt",
                    "amount": debt_amount,
                    "details": None
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        
        sale = response.json()
        assert sale["payment_method"] == "mixed"
        assert sale["is_split_payment"] == True
        assert sale["has_debt"] == True
        assert sale["debt_amount"] == debt_amount
        assert sale["amount_paid"] == cash_amount
        
        # Verify debt_id is created
        assert sale.get("debt_id") is not None, "Debt ID should be created for split payment with debt"
        
        print(f"✓ TEST 4 PASSED: Split payment (Cash + Debt) - Sale ID: {sale['id'][:8]}..., Debt ID: {sale['debt_id'][:8]}...")
        return sale
    
    def test_05_split_payment_mtn_plus_card(self):
        """TEST 5: Create sale with split payment (MTN Money + Card)"""
        total = 7700
        
        sale_data = {
            "items": [{
                "product_id": PRODUCT_ID,
                "quantity": 1,
                "unit_price": 7700,
                "subtotal": 7700
            }],
            "total": total,
            "payment_method": "mixed",
            "is_split_payment": True,
            "split_payments": [
                {
                    "method": "mtn_money",
                    "amount": 5000,
                    "details": {
                        "sender_number": "+224666778899",
                        "ticket_ref": "MTN-SPLIT-001"
                    }
                },
                {
                    "method": "card",
                    "amount": 2700,
                    "details": {
                        "holder_name": "Test User",
                        "last_digits": "1234",
                        "bank": "Test Bank"
                    }
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        
        sale = response.json()
        assert sale["is_split_payment"] == True
        assert len(sale["split_payments"]) == 2
        
        print(f"✓ TEST 5 PASSED: Split payment (MTN Money + Card) - Sale ID: {sale['id'][:8]}...")
        return sale
    
    # ==================== DEBT VALIDATION TESTS ====================
    
    def test_06_debt_requires_customer(self):
        """TEST 6: Debt payment requires customer selection"""
        sale_data = {
            # No customer_id
            "items": [{
                "product_id": PRODUCT_ID,
                "quantity": 1,
                "unit_price": 7700,
                "subtotal": 7700
            }],
            "total": 7700,
            "payment_method": "mixed",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": 5000},
                {"method": "debt", "amount": 2700}
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "client" in response.text.lower() or "crédit" in response.text.lower()
        
        print("✓ TEST 6 PASSED: Debt payment correctly requires customer selection")
    
    def test_07_debt_exceeds_credit_limit(self):
        """TEST 7: Debt amount cannot exceed customer credit limit"""
        # Use customer with limited credit
        customer_response = self.session.get(f"{BASE_URL}/api/customers")
        customers = customer_response.json()
        
        # Find customer with low available credit
        customer = next((c for c in customers if c.get("max_debt_limit", 0) > 0 and 
                        c.get("max_debt_limit", 0) - c.get("current_debt", 0) < 100000), None)
        
        if not customer:
            pytest.skip("No customer with limited credit available for test")
        
        available_credit = customer["max_debt_limit"] - customer.get("current_debt", 0)
        excessive_debt = available_credit + 50000  # Exceed by 50000
        
        sale_data = {
            "customer_id": customer["id"],
            "items": [{
                "product_id": PRODUCT_ID,
                "quantity": 1,
                "unit_price": 7700,
                "subtotal": 7700
            }],
            "total": excessive_debt + 1000,  # Total must be >= debt
            "payment_method": "mixed",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": 1000},
                {"method": "debt", "amount": excessive_debt}
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        # Should fail due to credit limit
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        print(f"✓ TEST 7 PASSED: Debt exceeding credit limit correctly rejected")
    
    # ==================== DEBT CREATION VERIFICATION ====================
    
    def test_08_verify_debt_created_in_debts_collection(self):
        """TEST 8: Verify debt is created in debts collection for split payment with debt"""
        total = 7700
        debt_amount = 3000
        
        sale_data = {
            "customer_id": CUSTOMER_WITH_CREDIT_ID,
            "items": [{
                "product_id": PRODUCT_ID,
                "quantity": 1,
                "unit_price": 7700,
                "subtotal": 7700
            }],
            "total": total,
            "payment_method": "mixed",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": total - debt_amount},
                {"method": "debt", "amount": debt_amount}
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        
        sale = response.json()
        debt_id = sale.get("debt_id")
        assert debt_id is not None, "Debt ID should be present"
        
        # Verify debt exists in debts collection
        debts_response = self.session.get(f"{BASE_URL}/api/debts")
        assert debts_response.status_code == 200
        
        debts = debts_response.json()
        debt = next((d for d in debts if d.get("id") == debt_id), None)
        
        assert debt is not None, f"Debt {debt_id} not found in debts collection"
        assert debt["original_amount"] == debt_amount, f"Expected {debt_amount}, got {debt.get('original_amount')}"
        assert debt["customer_id"] == CUSTOMER_WITH_CREDIT_ID
        assert debt["sale_id"] == sale["id"]
        
        print(f"✓ TEST 8 PASSED: Debt correctly created in debts collection - Debt ID: {debt_id[:8]}...")
    
    # ==================== SALES LIST DISPLAY TESTS ====================
    
    def test_09_split_payments_in_sales_list(self):
        """TEST 9: Verify split payments are returned correctly in sales list"""
        # Get all sales
        response = self.session.get(f"{BASE_URL}/api/sales")
        assert response.status_code == 200
        
        sales = response.json()
        
        # Find sales with split payments
        split_sales = [s for s in sales if s.get("is_split_payment") == True]
        
        assert len(split_sales) > 0, "No split payment sales found"
        
        for sale in split_sales[:3]:  # Check first 3
            assert sale.get("split_payments") is not None, f"Sale {sale['id']} missing split_payments"
            assert len(sale["split_payments"]) >= 2, f"Sale {sale['id']} should have at least 2 split payments"
            
            for sp in sale["split_payments"]:
                assert "method" in sp, "Split payment missing 'method'"
                assert "amount" in sp, "Split payment missing 'amount'"
        
        print(f"✓ TEST 9 PASSED: Split payments correctly returned in sales list ({len(split_sales)} found)")
    
    def test_10_sale_detail_with_split_payments(self):
        """TEST 10: Verify sale detail endpoint returns split payments correctly"""
        # First create a split payment sale
        sale_data = {
            "items": [{
                "product_id": PRODUCT_ID,
                "quantity": 1,
                "unit_price": 7700,
                "subtotal": 7700
            }],
            "total": 7700,
            "payment_method": "mixed",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": 4000},
                {"method": "orange_money", "amount": 3700, "details": {"sender_number": "+224622102030"}}
            ]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        assert create_response.status_code == 200
        
        sale_id = create_response.json()["id"]
        
        # Get sale detail
        detail_response = self.session.get(f"{BASE_URL}/api/sales/{sale_id}")
        assert detail_response.status_code == 200
        
        sale = detail_response.json()
        assert sale["is_split_payment"] == True
        assert sale["split_payments"] is not None
        assert len(sale["split_payments"]) == 2
        
        print(f"✓ TEST 10 PASSED: Sale detail correctly returns split payments - Sale ID: {sale_id[:8]}...")


class TestFullDebtPayment:
    """Test suite for full debt payment (100% debt)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        self.session.close()
    
    def test_11_full_debt_payment(self):
        """TEST 11: Create sale with 100% debt payment"""
        total = 7700
        
        sale_data = {
            "customer_id": CUSTOMER_WITH_CREDIT_ID,
            "items": [{
                "product_id": PRODUCT_ID,
                "quantity": 1,
                "unit_price": 7700,
                "subtotal": 7700
            }],
            "total": total,
            "payment_method": "debt",
            "debt_amount": total,
            "amount_paid": 0
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        
        sale = response.json()
        assert sale["payment_method"] == "debt"
        assert sale["has_debt"] == True
        assert sale["debt_amount"] == total
        assert sale["amount_paid"] == 0
        assert sale.get("debt_id") is not None
        
        print(f"✓ TEST 11 PASSED: Full debt payment - Sale ID: {sale['id'][:8]}..., Debt: {total}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
