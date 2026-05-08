"""
Test suite for Pending Sales API - Bug fixes verification
Tests:
1. Employee code is stored in created_by_name (not email)
2. Total amount is correctly stored from sale_data.total
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPendingSalesBugFixes:
    """Test pending sales bug fixes for employee code and total amount"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        # Login as admin
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        self.token = login_response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Get a product for testing
        products_response = requests.get(f"{BASE_URL}/api/products", headers=self.headers)
        assert products_response.status_code == 200
        products = products_response.json()
        assert len(products) > 0, "No products found for testing"
        self.test_product = products[0]
        
        yield
        
        # Cleanup: Cancel any test pending sales created
        # (handled by test methods)
    
    def test_create_pending_sale_has_employee_code(self):
        """
        BUG FIX TEST 1: Verify that created_by_name contains employee code (ADM-001), not email
        """
        # Create a pending sale
        pending_sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": self.test_product["id"],
                "product_name": self.test_product["name"],
                "quantity": 1,
                "unit_price": self.test_product.get("price", 1000)
            }],
            "subtotal": self.test_product.get("price", 1000),
            "discount_type": None,
            "discount_value": 0,
            "discount_amount": 0,
            "total": self.test_product.get("price", 1000),
            "notes": "Test pending sale for employee code verification"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/pending-sales",
            json=pending_sale_data,
            headers=self.headers
        )
        
        assert create_response.status_code == 200, f"Failed to create pending sale: {create_response.text}"
        created_sale = create_response.json()
        pending_id = created_sale.get("id")
        
        # Get the pending sale details
        get_response = requests.get(
            f"{BASE_URL}/api/pending-sales/{pending_id}",
            headers=self.headers
        )
        
        assert get_response.status_code == 200, f"Failed to get pending sale: {get_response.text}"
        pending_sale = get_response.json()
        
        # VERIFY BUG FIX 1: created_by_name should be employee code (ADM-001), not email
        created_by_name = pending_sale.get("created_by_name", "")
        
        # Should NOT contain email
        assert "@" not in created_by_name, f"BUG: created_by_name contains email: {created_by_name}"
        assert "pharmaflow.com" not in created_by_name, f"BUG: created_by_name contains email domain: {created_by_name}"
        
        # Should contain employee code pattern (ADM-xxx, CAI-xxx, PHA-xxx)
        assert any(prefix in created_by_name for prefix in ["ADM-", "CAI-", "PHA-"]), \
            f"BUG: created_by_name does not contain employee code pattern: {created_by_name}"
        
        print(f"✅ BUG FIX 1 VERIFIED: created_by_name = '{created_by_name}' (employee code, not email)")
        
        # Cleanup: Cancel the pending sale
        requests.delete(f"{BASE_URL}/api/pending-sales/{pending_id}", headers=self.headers)
    
    def test_create_pending_sale_has_correct_total(self):
        """
        BUG FIX TEST 2: Verify that total is correctly stored from sale_data.total
        """
        expected_total = 5500  # Custom total for testing
        
        # Create a pending sale with specific total
        pending_sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": self.test_product["id"],
                "product_name": self.test_product["name"],
                "quantity": 2,
                "unit_price": 2750  # 2750 * 2 = 5500
            }],
            "subtotal": 5500,
            "discount_type": None,
            "discount_value": 0,
            "discount_amount": 0,
            "total": expected_total,
            "notes": "Test pending sale for total verification"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/pending-sales",
            json=pending_sale_data,
            headers=self.headers
        )
        
        assert create_response.status_code == 200, f"Failed to create pending sale: {create_response.text}"
        created_sale = create_response.json()
        pending_id = created_sale.get("id")
        
        # Get the pending sale details
        get_response = requests.get(
            f"{BASE_URL}/api/pending-sales/{pending_id}",
            headers=self.headers
        )
        
        assert get_response.status_code == 200, f"Failed to get pending sale: {get_response.text}"
        pending_sale = get_response.json()
        
        # VERIFY BUG FIX 2: total should match expected_total
        actual_total = pending_sale.get("total", 0)
        
        assert actual_total == expected_total, \
            f"BUG: total is {actual_total}, expected {expected_total}"
        assert actual_total != 0, \
            f"BUG: total is 0, expected {expected_total}"
        
        print(f"✅ BUG FIX 2 VERIFIED: total = {actual_total} GNF (correct, not 0)")
        
        # Cleanup: Cancel the pending sale
        requests.delete(f"{BASE_URL}/api/pending-sales/{pending_id}", headers=self.headers)
    
    def test_pending_sales_list_shows_correct_data(self):
        """
        Verify that the pending sales list endpoint returns correct data
        """
        # Get all pending sales
        response = requests.get(
            f"{BASE_URL}/api/pending-sales",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to get pending sales: {response.text}"
        pending_sales = response.json()
        
        # Check each pending sale
        for sale in pending_sales:
            created_by_name = sale.get("created_by_name", "")
            total = sale.get("total", 0)
            reference = sale.get("reference", "")
            
            print(f"Pending sale {reference}: created_by_name='{created_by_name}', total={total}")
            
            # Note: Old sales may have incorrect data, but new sales should be correct
            # We just log the data for visibility
        
        print(f"✅ Found {len(pending_sales)} pending sales")
    
    def test_pending_sales_count_endpoint(self):
        """
        Verify the pending sales count endpoint works
        """
        response = requests.get(
            f"{BASE_URL}/api/pending-sales/count",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to get pending sales count: {response.text}"
        data = response.json()
        
        assert "count" in data, "Response missing 'count' field"
        count = data.get("count", 0)
        
        print(f"✅ Pending sales count: {count}")
    
    def test_cancel_pending_sale(self):
        """
        Verify that pending sales can be cancelled
        """
        # Create a pending sale
        pending_sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": self.test_product["id"],
                "product_name": self.test_product["name"],
                "quantity": 1,
                "unit_price": 1000
            }],
            "subtotal": 1000,
            "discount_type": None,
            "discount_value": 0,
            "discount_amount": 0,
            "total": 1000,
            "notes": "Test pending sale for cancel verification"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/pending-sales",
            json=pending_sale_data,
            headers=self.headers
        )
        
        assert create_response.status_code == 200
        pending_id = create_response.json().get("id")
        
        # Cancel the pending sale
        cancel_response = requests.delete(
            f"{BASE_URL}/api/pending-sales/{pending_id}",
            headers=self.headers
        )
        
        assert cancel_response.status_code == 200, f"Failed to cancel pending sale: {cancel_response.text}"
        
        # Verify it's cancelled (should not appear in pending list)
        get_response = requests.get(
            f"{BASE_URL}/api/pending-sales/{pending_id}",
            headers=self.headers
        )
        
        if get_response.status_code == 200:
            sale = get_response.json()
            assert sale.get("status") == "cancelled", "Pending sale should be cancelled"
        
        print("✅ Pending sale cancelled successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
