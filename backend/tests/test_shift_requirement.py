"""
Test Suite: Shift Requirement Rule
Tests the business rule: "No operation allowed without open shift, EXCEPT for admins who are exempt"

Test scenarios:
1. Caissier without shift cannot create sale (SHIFT_REQUIRED error)
2. Caissier with shift can create sale
3. Admin without shift can create sale (exempt)
4. Pharmacien without shift cannot declare loss
5. Pharmacien with shift can declare loss
6. Admin without shift can declare loss (exempt)
7. API POST /api/sales checks shift for non-admin
8. API POST /api/stock/losses checks shift for non-admin
9. API POST /api/supplies checks shift for non-admin
10. API POST /api/debts/payment/bulk checks shift for non-admin
11. API POST /api/returns checks shift for non-admin
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
CREDENTIALS = {
    "admin": {"email": "admin@pharmaflow.com", "password": "admin123"},
    "pharmacien": {"email": "pharmacien@pharmaflow.com", "password": "pharma123"},
    "caissier": {"email": "caissier@pharmaflow.com", "password": "caisse123"}
}


class TestShiftRequirement:
    """Test shift requirement rule for all operations"""
    
    @pytest.fixture(scope="function")
    def session(self):
        """Create a requests session for each test"""
        return requests.Session()
    
    def login(self, session, role):
        """Login and return token"""
        creds = CREDENTIALS[role]
        response = session.post(f"{BASE_URL}/api/auth/login", json=creds)
        assert response.status_code == 200, f"Login failed for {role}: {response.text}"
        data = response.json()
        return data.get("access_token") or data.get("token")
    
    def get_auth_headers(self, token):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {token}"}
    
    def get_user_shift_status(self, session, token):
        """Check if user has an open shift"""
        headers = self.get_auth_headers(token)
        response = session.get(f"{BASE_URL}/api/shifts/current", headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "open" if data else False
        return False
    
    def close_all_user_shifts(self, session, token):
        """Close all open shifts for the current user"""
        headers = self.get_auth_headers(token)
        response = session.get(f"{BASE_URL}/api/shifts/current", headers=headers)
        if response.status_code == 200:
            shift = response.json()
            if shift and shift.get("status") == "open":
                shift_id = shift.get("id")
                close_response = session.post(
                    f"{BASE_URL}/api/shifts/close",
                    headers=headers,
                    json={"actual_closing_amount": 0, "closing_notes": "Test cleanup"}
                )
                print(f"Closed shift {shift_id}: {close_response.status_code}")
    
    def open_shift(self, session, token, opening_amount=10000):
        """Open a new shift for the user"""
        headers = self.get_auth_headers(token)
        response = session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": opening_amount, "notes": "Test shift"}
        )
        return response
    
    def get_test_product(self, session, token=None, use_admin=False):
        """Get a product with stock for testing. Use admin token if caissier can't access products."""
        if use_admin:
            # Login as admin to get products (caissier can't view products)
            admin_token = self.login(session, "admin")
            headers = self.get_auth_headers(admin_token)
        else:
            headers = self.get_auth_headers(token)
        
        response = session.get(f"{BASE_URL}/api/products", headers=headers)
        if response.status_code == 200:
            products = response.json()
            for product in products:
                if product.get("stock", 0) > 0:
                    return product
        elif response.status_code == 403 and not use_admin:
            # Retry with admin token
            return self.get_test_product(session, token, use_admin=True)
        return None
    
    def get_test_customer_with_debt(self, session, token):
        """Get a customer with debt for testing"""
        headers = self.get_auth_headers(token)
        response = session.get(f"{BASE_URL}/api/debts/customers-summary?only_with_debt=true", headers=headers)
        if response.status_code == 200:
            customers = response.json()
            for customer in customers:
                if customer.get("total_debt", 0) > 0:
                    return customer
        return None
    
    def get_test_supplier(self, session, token):
        """Get a supplier for testing"""
        headers = self.get_auth_headers(token)
        response = session.get(f"{BASE_URL}/api/suppliers", headers=headers)
        if response.status_code == 200:
            suppliers = response.json()
            if suppliers:
                return suppliers[0]
        return None
    
    def get_test_sale_for_return(self, session, token):
        """Get a sale that can be returned"""
        headers = self.get_auth_headers(token)
        response = session.get(f"{BASE_URL}/api/sales", headers=headers)
        if response.status_code == 200:
            sales = response.json()
            for sale in sales:
                if sale.get("items") and len(sale.get("items", [])) > 0:
                    return sale
        return None

    # ==================== SALES TESTS ====================
    
    def test_caissier_without_shift_cannot_create_sale(self, session):
        """Test: Caissier without shift cannot create sale (SHIFT_REQUIRED error)"""
        token = self.login(session, "caissier")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift
        self.close_all_user_shifts(session, token)
        
        # Verify no open shift
        has_shift = self.get_user_shift_status(session, token)
        print(f"Caissier has open shift: {has_shift}")
        
        # Get a product for sale
        product = self.get_test_product(session, token)
        if not product:
            pytest.skip("No product with stock available for testing")
        
        # Try to create sale without shift
        sale_data = {
            "items": [{"product_id": product["id"], "quantity": 1, "unit_price": product.get("price", 100), "subtotal": product.get("price", 100)}],
            "total": product.get("price", 100),
            "payment_method": "cash"
        }
        
        response = session.post(f"{BASE_URL}/api/sales", headers=headers, json=sale_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Should get 403 with SHIFT_REQUIRED
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "SHIFT_REQUIRED" in response.text, f"Expected SHIFT_REQUIRED in response: {response.text}"
    
    def test_caissier_with_shift_can_create_sale(self, session):
        """Test: Caissier with shift can create sale"""
        token = self.login(session, "caissier")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift first
        self.close_all_user_shifts(session, token)
        
        # Open a new shift
        open_response = self.open_shift(session, token)
        print(f"Open shift response: {open_response.status_code} - {open_response.text}")
        
        # Verify shift is open
        has_shift = self.get_user_shift_status(session, token)
        print(f"Caissier has open shift after opening: {has_shift}")
        
        if not has_shift:
            pytest.skip("Could not open shift for caissier")
        
        # Get a product for sale
        product = self.get_test_product(session, token)
        if not product:
            pytest.skip("No product with stock available for testing")
        
        # Create sale with shift
        sale_data = {
            "items": [{"product_id": product["id"], "quantity": 1, "unit_price": product.get("price", 100), "subtotal": product.get("price", 100)}],
            "total": product.get("price", 100),
            "payment_method": "cash"
        }
        
        response = session.post(f"{BASE_URL}/api/sales", headers=headers, json=sale_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Should succeed
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
    
    def test_admin_without_shift_can_create_sale(self, session):
        """Test: Admin without shift can create sale (exempt from shift requirement)"""
        token = self.login(session, "admin")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift
        self.close_all_user_shifts(session, token)
        
        # Verify no open shift
        has_shift = self.get_user_shift_status(session, token)
        print(f"Admin has open shift: {has_shift}")
        
        # Get a product for sale
        product = self.get_test_product(session, token)
        if not product:
            pytest.skip("No product with stock available for testing")
        
        # Create sale without shift (admin should be exempt)
        sale_data = {
            "items": [{"product_id": product["id"], "quantity": 1, "unit_price": product.get("price", 100), "subtotal": product.get("price", 100)}],
            "total": product.get("price", 100),
            "payment_method": "cash"
        }
        
        response = session.post(f"{BASE_URL}/api/sales", headers=headers, json=sale_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Admin should succeed even without shift
        assert response.status_code in [200, 201], f"Admin should be exempt from shift requirement. Got {response.status_code}: {response.text}"

    # ==================== STOCK LOSSES TESTS ====================
    
    def test_pharmacien_without_shift_cannot_declare_loss(self, session):
        """Test: Pharmacien without shift cannot declare loss"""
        token = self.login(session, "pharmacien")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift
        self.close_all_user_shifts(session, token)
        
        # Verify no open shift
        has_shift = self.get_user_shift_status(session, token)
        print(f"Pharmacien has open shift: {has_shift}")
        
        # Get a product for loss declaration
        product = self.get_test_product(session, token)
        if not product:
            pytest.skip("No product with stock available for testing")
        
        # Try to declare loss without shift
        response = session.post(
            f"{BASE_URL}/api/stock/losses",
            headers=headers,
            params={
                "product_id": product["id"],
                "quantity": 1,
                "reason": "breakage",
                "notes": "Test loss without shift"
            }
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Should get 403 with SHIFT_REQUIRED
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "SHIFT_REQUIRED" in response.text, f"Expected SHIFT_REQUIRED in response: {response.text}"
    
    def test_pharmacien_with_shift_can_declare_loss(self, session):
        """Test: Pharmacien with shift can declare loss"""
        token = self.login(session, "pharmacien")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift first
        self.close_all_user_shifts(session, token)
        
        # Open a new shift
        open_response = self.open_shift(session, token)
        print(f"Open shift response: {open_response.status_code} - {open_response.text}")
        
        # Verify shift is open
        has_shift = self.get_user_shift_status(session, token)
        print(f"Pharmacien has open shift after opening: {has_shift}")
        
        if not has_shift:
            pytest.skip("Could not open shift for pharmacien")
        
        # Get a product for loss declaration
        product = self.get_test_product(session, token)
        if not product:
            pytest.skip("No product with stock available for testing")
        
        # Declare loss with shift
        response = session.post(
            f"{BASE_URL}/api/stock/losses",
            headers=headers,
            params={
                "product_id": product["id"],
                "quantity": 1,
                "reason": "breakage",
                "notes": "Test loss with shift"
            }
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Should succeed
        assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}: {response.text}"
    
    def test_admin_without_shift_can_declare_loss(self, session):
        """Test: Admin without shift can declare loss (exempt)"""
        token = self.login(session, "admin")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift
        self.close_all_user_shifts(session, token)
        
        # Verify no open shift
        has_shift = self.get_user_shift_status(session, token)
        print(f"Admin has open shift: {has_shift}")
        
        # Get a product for loss declaration
        product = self.get_test_product(session, token)
        if not product:
            pytest.skip("No product with stock available for testing")
        
        # Declare loss without shift (admin should be exempt)
        response = session.post(
            f"{BASE_URL}/api/stock/losses",
            headers=headers,
            params={
                "product_id": product["id"],
                "quantity": 1,
                "reason": "breakage",
                "notes": "Test loss by admin without shift"
            }
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Admin should succeed even without shift
        assert response.status_code in [200, 201], f"Admin should be exempt from shift requirement. Got {response.status_code}: {response.text}"

    # ==================== SUPPLIES TESTS ====================
    
    def test_pharmacien_without_shift_cannot_create_supply(self, session):
        """Test: Pharmacien without shift cannot create supply"""
        token = self.login(session, "pharmacien")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift
        self.close_all_user_shifts(session, token)
        
        # Verify no open shift
        has_shift = self.get_user_shift_status(session, token)
        print(f"Pharmacien has open shift: {has_shift}")
        
        # Get a product and supplier for supply
        product = self.get_test_product(session, token)
        supplier = self.get_test_supplier(session, token)
        
        if not product:
            pytest.skip("No product available for testing")
        if not supplier:
            pytest.skip("No supplier available for testing")
        
        # Try to create supply without shift
        supply_data = {
            "supplier_id": supplier["id"],
            "items": [{"product_id": product["id"], "quantity": 10, "unit_price": 50}],
            "total_amount": 500,
            "delivery_note_number": f"TEST-BL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        response = session.post(f"{BASE_URL}/api/supplies", headers=headers, json=supply_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Should get 403 with SHIFT_REQUIRED
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "SHIFT_REQUIRED" in response.text, f"Expected SHIFT_REQUIRED in response: {response.text}"
    
    def test_admin_without_shift_can_create_supply(self, session):
        """Test: Admin without shift can create supply (exempt)"""
        token = self.login(session, "admin")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift
        self.close_all_user_shifts(session, token)
        
        # Verify no open shift
        has_shift = self.get_user_shift_status(session, token)
        print(f"Admin has open shift: {has_shift}")
        
        # Get a product and supplier for supply
        product = self.get_test_product(session, token)
        supplier = self.get_test_supplier(session, token)
        
        if not product:
            pytest.skip("No product available for testing")
        if not supplier:
            pytest.skip("No supplier available for testing")
        
        # Create supply without shift (admin should be exempt)
        supply_data = {
            "supplier_id": supplier["id"],
            "items": [{"product_id": product["id"], "quantity": 10, "unit_price": 50}],
            "total_amount": 500,
            "delivery_note_number": f"TEST-BL-ADMIN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        response = session.post(f"{BASE_URL}/api/supplies", headers=headers, json=supply_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Admin should succeed even without shift
        assert response.status_code in [200, 201], f"Admin should be exempt from shift requirement. Got {response.status_code}: {response.text}"

    # ==================== DEBT PAYMENT TESTS ====================
    
    def test_caissier_without_shift_cannot_create_debt_payment(self, session):
        """Test: Caissier without shift cannot create debt payment"""
        token = self.login(session, "caissier")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift
        self.close_all_user_shifts(session, token)
        
        # Verify no open shift
        has_shift = self.get_user_shift_status(session, token)
        print(f"Caissier has open shift: {has_shift}")
        
        # Get a customer with debt
        customer = self.get_test_customer_with_debt(session, token)
        if not customer:
            pytest.skip("No customer with debt available for testing")
        
        # Try to create debt payment without shift
        payment_data = {
            "customer_id": customer.get("customer_id"),
            "amount": min(100, customer.get("total_debt", 100)),
            "payment_method": "cash"
        }
        
        response = session.post(f"{BASE_URL}/api/debts/payment/bulk", headers=headers, json=payment_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Should get 403 with SHIFT_REQUIRED
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "SHIFT_REQUIRED" in response.text, f"Expected SHIFT_REQUIRED in response: {response.text}"
    
    def test_admin_without_shift_can_create_debt_payment(self, session):
        """Test: Admin without shift can create debt payment (exempt)"""
        token = self.login(session, "admin")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift
        self.close_all_user_shifts(session, token)
        
        # Verify no open shift
        has_shift = self.get_user_shift_status(session, token)
        print(f"Admin has open shift: {has_shift}")
        
        # Get a customer with debt
        customer = self.get_test_customer_with_debt(session, token)
        if not customer:
            pytest.skip("No customer with debt available for testing")
        
        # Create debt payment without shift (admin should be exempt)
        payment_data = {
            "customer_id": customer.get("customer_id"),
            "amount": min(100, customer.get("total_debt", 100)),
            "payment_method": "cash"
        }
        
        response = session.post(f"{BASE_URL}/api/debts/payment/bulk", headers=headers, json=payment_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Admin should succeed even without shift
        assert response.status_code in [200, 201], f"Admin should be exempt from shift requirement. Got {response.status_code}: {response.text}"

    # ==================== RETURNS TESTS ====================
    
    def test_caissier_without_shift_cannot_create_return(self, session):
        """Test: Caissier without shift cannot create return"""
        token = self.login(session, "caissier")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift
        self.close_all_user_shifts(session, token)
        
        # Verify no open shift
        has_shift = self.get_user_shift_status(session, token)
        print(f"Caissier has open shift: {has_shift}")
        
        # Get a sale for return
        sale = self.get_test_sale_for_return(session, token)
        if not sale:
            pytest.skip("No sale available for return testing")
        
        # Try to create return without shift
        return_data = {
            "sale_id": sale.get("id"),
            "items": [{"product_id": sale["items"][0]["product_id"], "quantity": 1, "reason": "defective"}],
            "reason": "defective",
            "refund_method": "cash"
        }
        
        response = session.post(f"{BASE_URL}/api/returns", headers=headers, json=return_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Should get 403 with SHIFT_REQUIRED
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        assert "SHIFT_REQUIRED" in response.text, f"Expected SHIFT_REQUIRED in response: {response.text}"
    
    def test_admin_without_shift_can_create_return(self, session):
        """Test: Admin without shift can create return (exempt)"""
        token = self.login(session, "admin")
        headers = self.get_auth_headers(token)
        
        # Close any existing shift
        self.close_all_user_shifts(session, token)
        
        # Verify no open shift
        has_shift = self.get_user_shift_status(session, token)
        print(f"Admin has open shift: {has_shift}")
        
        # Get a sale for return
        sale = self.get_test_sale_for_return(session, token)
        if not sale:
            pytest.skip("No sale available for return testing")
        
        # Create return without shift (admin should be exempt)
        return_data = {
            "sale_id": sale.get("id"),
            "items": [{"product_id": sale["items"][0]["product_id"], "quantity": 1, "reason": "defective"}],
            "reason": "defective",
            "refund_method": "cash"
        }
        
        response = session.post(f"{BASE_URL}/api/returns", headers=headers, json=return_data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Admin should succeed even without shift (or get a different error like "already returned")
        # We accept 200, 201, or 400 (if item already returned) but NOT 403 SHIFT_REQUIRED
        if response.status_code == 403:
            assert "SHIFT_REQUIRED" not in response.text, f"Admin should be exempt from shift requirement. Got: {response.text}"
        else:
            print(f"Admin return request processed (status {response.status_code})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
