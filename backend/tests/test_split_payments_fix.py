"""
Test suite for Split Payments Bug Fix Verification
Bug: is_split_payment and split_payments columns were not being saved during sale creation

Tests verify:
1. POST /api/sales with is_split_payment=true saves split_payments correctly
2. GET /api/sales/{id} returns is_split_payment and split_payments
3. GET /api/sales (paginated list) includes is_split_payment and split_payments
4. Simple (non-split) sales still work with is_split_payment=false
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSplitPaymentsFix:
    """Test suite verifying the split payments bug fix"""
    
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
        
        # Get a product with stock for testing
        products_response = self.session.get(f"{BASE_URL}/api/products")
        products = products_response.json()
        self.test_product = next((p for p in products if p.get('stock', 0) > 5), None)
        assert self.test_product is not None, "No product with stock > 5 available for testing"
        
        yield
        self.session.close()
    
    def test_01_create_split_payment_sale(self):
        """TEST 1: Create sale with split payment (cash + orange_money)"""
        product_id = self.test_product['id']
        product_price = self.test_product['price']
        
        sale_data = {
            "items": [{
                "product_id": product_id,
                "quantity": 1,
                "unit_price": product_price,
                "subtotal": product_price
            }],
            "total": product_price,
            "payment_method": "mixed",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": product_price // 2, "details": None},
                {"method": "orange_money", "amount": product_price - (product_price // 2), 
                 "details": {"sender_number": "+224622102030", "ticket_ref": "TEST-FIX-001"}}
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        
        sale = response.json()
        
        # Verify split payment fields are saved
        assert sale["is_split_payment"] == True, "is_split_payment should be True"
        assert sale["split_payments"] is not None, "split_payments should not be None"
        assert len(sale["split_payments"]) == 2, "Should have 2 split payments"
        assert sale["payment_method"] == "mixed", "payment_method should be 'mixed'"
        
        # Verify split payment amounts
        methods = [sp["method"] for sp in sale["split_payments"]]
        assert "cash" in methods, "Should have cash payment"
        assert "orange_money" in methods, "Should have orange_money payment"
        
        # Store sale_id for next test
        self.split_sale_id = sale["id"]
        print(f"✓ TEST 1 PASSED: Split payment sale created - ID: {sale['id'][:8]}...")
        return sale
    
    def test_02_get_split_payment_sale_by_id(self):
        """TEST 2: GET /api/sales/{id} returns split payment data correctly"""
        # First create a split payment sale
        product_id = self.test_product['id']
        product_price = self.test_product['price']
        
        sale_data = {
            "items": [{
                "product_id": product_id,
                "quantity": 1,
                "unit_price": product_price,
                "subtotal": product_price
            }],
            "total": product_price,
            "payment_method": "mixed",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": 3000},
                {"method": "mtn_money", "amount": product_price - 3000, 
                 "details": {"sender_number": "+224666778899"}}
            ]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        assert create_response.status_code == 200
        sale_id = create_response.json()["id"]
        
        # Get sale by ID
        get_response = self.session.get(f"{BASE_URL}/api/sales/{sale_id}")
        
        assert get_response.status_code == 200, f"GET sale failed: {get_response.text}"
        
        sale = get_response.json()
        
        # Verify split payment fields are returned
        assert sale["is_split_payment"] == True, "is_split_payment should be True"
        assert sale["split_payments"] is not None, "split_payments should not be None"
        assert len(sale["split_payments"]) == 2, "Should have 2 split payments"
        
        print(f"✓ TEST 2 PASSED: GET /api/sales/{{id}} returns split payment data correctly")
    
    def test_03_split_payments_in_paginated_list(self):
        """TEST 3: GET /api/sales returns split payments in paginated list"""
        response = self.session.get(f"{BASE_URL}/api/sales?limit=10")
        
        assert response.status_code == 200, f"GET sales failed: {response.text}"
        
        data = response.json()
        sales = data.get("items", [])
        
        # Find split payment sales
        split_sales = [s for s in sales if s.get("is_split_payment") == True]
        
        assert len(split_sales) > 0, "Should have at least one split payment sale"
        
        for sale in split_sales:
            assert sale.get("split_payments") is not None, f"Sale {sale['id']} missing split_payments"
            assert len(sale["split_payments"]) >= 2, f"Sale {sale['id']} should have >= 2 split payments"
            
            # Verify each split payment has required fields
            for sp in sale["split_payments"]:
                assert "method" in sp, "Split payment missing 'method'"
                assert "amount" in sp, "Split payment missing 'amount'"
        
        print(f"✓ TEST 3 PASSED: Found {len(split_sales)} split payment sales in paginated list")
    
    def test_04_simple_sale_still_works(self):
        """TEST 4: Simple (non-split) sale with is_split_payment=false still works"""
        product_id = self.test_product['id']
        product_price = self.test_product['price']
        
        sale_data = {
            "items": [{
                "product_id": product_id,
                "quantity": 1,
                "unit_price": product_price,
                "subtotal": product_price
            }],
            "total": product_price,
            "payment_method": "cash",
            "is_split_payment": False
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 200, f"Sale creation failed: {response.text}"
        
        sale = response.json()
        
        # Verify simple sale fields
        assert sale["is_split_payment"] == False, "is_split_payment should be False"
        assert sale["split_payments"] is None or sale["split_payments"] == [], "split_payments should be None or empty"
        assert sale["payment_method"] == "cash", "payment_method should be 'cash'"
        
        # Verify via GET
        get_response = self.session.get(f"{BASE_URL}/api/sales/{sale['id']}")
        assert get_response.status_code == 200
        
        fetched_sale = get_response.json()
        assert fetched_sale["is_split_payment"] == False
        
        print(f"✓ TEST 4 PASSED: Simple cash sale works - ID: {sale['id'][:8]}...")
    
    def test_05_verify_existing_split_payment_sale(self):
        """TEST 5: Verify pre-existing split payment sale VNT-6F8CAD7D is correctly stored"""
        # Get sales and find VNT-6F8CAD7D
        response = self.session.get(f"{BASE_URL}/api/sales?limit=50")
        assert response.status_code == 200
        
        data = response.json()
        sales = data.get("items", [])
        
        # Find the specific test sale
        test_sale = next((s for s in sales if s.get("sale_number") == "VNT-6F8CAD7D"), None)
        
        if test_sale:
            assert test_sale["is_split_payment"] == True, "VNT-6F8CAD7D should have is_split_payment=True"
            assert test_sale["split_payments"] is not None, "VNT-6F8CAD7D should have split_payments"
            assert len(test_sale["split_payments"]) >= 2, "VNT-6F8CAD7D should have >= 2 payment methods"
            
            print(f"✓ TEST 5 PASSED: VNT-6F8CAD7D verified - has {len(test_sale['split_payments'])} payment methods")
        else:
            print("⚠ TEST 5 SKIPPED: VNT-6F8CAD7D not found (may have been cleaned up)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
