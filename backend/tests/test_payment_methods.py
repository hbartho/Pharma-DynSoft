"""
Test Payment Methods API - Dynamic Payment Methods Feature
Tests the /api/payment-methods endpoint and related functionality
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPaymentMethodsAPI:
    """Test suite for Payment Methods API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - authenticate and get token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_all_payment_methods(self):
        """Test GET /api/payment-methods returns all 5 payment methods"""
        response = requests.get(
            f"{BASE_URL}/api/payment-methods",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        methods = response.json()
        
        # Should have 5 payment methods
        assert len(methods) == 5, f"Expected 5 methods, got {len(methods)}"
        
        # Verify all expected codes are present
        codes = [m["code"] for m in methods]
        expected_codes = ["cash", "orange_money", "card", "check", "mtn_money"]
        for code in expected_codes:
            assert code in codes, f"Missing payment method: {code}"
        
        print(f"✓ GET /api/payment-methods returns {len(methods)} methods")
    
    def test_get_active_payment_methods(self):
        """Test GET /api/payment-methods?active_only=true"""
        response = requests.get(
            f"{BASE_URL}/api/payment-methods?active_only=true",
            headers=self.headers
        )
        
        assert response.status_code == 200
        methods = response.json()
        
        # All methods should be active
        for method in methods:
            assert method["is_active"] == True, f"Method {method['code']} is not active"
        
        print(f"✓ GET /api/payment-methods?active_only=true returns {len(methods)} active methods")
    
    def test_cash_method_has_no_required_fields(self):
        """Test that cash payment method has no required fields"""
        response = requests.get(
            f"{BASE_URL}/api/payment-methods",
            headers=self.headers
        )
        
        methods = response.json()
        cash_method = next((m for m in methods if m["code"] == "cash"), None)
        
        assert cash_method is not None, "Cash method not found"
        assert cash_method["required_fields"] == [], f"Cash should have no required fields, got {cash_method['required_fields']}"
        assert cash_method["color"] == "green", f"Cash color should be green, got {cash_method['color']}"
        assert cash_method["icon"] == "banknote", f"Cash icon should be banknote, got {cash_method['icon']}"
        
        print("✓ Cash method has 0 required fields, color=green, icon=banknote")
    
    def test_orange_money_has_correct_required_fields(self):
        """Test Orange Money has 2 required fields: sender_number, ticket_ref"""
        response = requests.get(
            f"{BASE_URL}/api/payment-methods",
            headers=self.headers
        )
        
        methods = response.json()
        orange_method = next((m for m in methods if m["code"] == "orange_money"), None)
        
        assert orange_method is not None, "Orange Money method not found"
        assert len(orange_method["required_fields"]) == 2, f"Orange Money should have 2 fields, got {len(orange_method['required_fields'])}"
        
        field_names = [f["name"] for f in orange_method["required_fields"]]
        assert "sender_number" in field_names, "Missing sender_number field"
        assert "ticket_ref" in field_names, "Missing ticket_ref field"
        
        assert orange_method["color"] == "orange", f"Orange Money color should be orange, got {orange_method['color']}"
        
        # Verify field properties
        sender_field = next(f for f in orange_method["required_fields"] if f["name"] == "sender_number")
        assert sender_field["type"] == "tel", f"sender_number type should be tel, got {sender_field['type']}"
        assert sender_field["required"] == True, "sender_number should be required"
        
        print("✓ Orange Money has 2 required fields (sender_number, ticket_ref), color=orange")
    
    def test_card_method_has_correct_required_fields(self):
        """Test Card method has 3 required fields: holder_name, last_digits, bank"""
        response = requests.get(
            f"{BASE_URL}/api/payment-methods",
            headers=self.headers
        )
        
        methods = response.json()
        card_method = next((m for m in methods if m["code"] == "card"), None)
        
        assert card_method is not None, "Card method not found"
        assert len(card_method["required_fields"]) == 3, f"Card should have 3 fields, got {len(card_method['required_fields'])}"
        
        field_names = [f["name"] for f in card_method["required_fields"]]
        assert "holder_name" in field_names, "Missing holder_name field"
        assert "last_digits" in field_names, "Missing last_digits field"
        assert "bank" in field_names, "Missing bank field"
        
        assert card_method["color"] == "purple", f"Card color should be purple, got {card_method['color']}"
        
        # Verify last_digits has maxLength=4
        last_digits_field = next(f for f in card_method["required_fields"] if f["name"] == "last_digits")
        assert last_digits_field.get("maxLength") == 4, f"last_digits maxLength should be 4, got {last_digits_field.get('maxLength')}"
        
        print("✓ Card method has 3 required fields (holder_name, last_digits, bank), color=purple")
    
    def test_check_method_has_correct_required_fields(self):
        """Test Check method has 3 required fields: holder_name, check_number, bank"""
        response = requests.get(
            f"{BASE_URL}/api/payment-methods",
            headers=self.headers
        )
        
        methods = response.json()
        check_method = next((m for m in methods if m["code"] == "check"), None)
        
        assert check_method is not None, "Check method not found"
        assert len(check_method["required_fields"]) == 3, f"Check should have 3 fields, got {len(check_method['required_fields'])}"
        
        field_names = [f["name"] for f in check_method["required_fields"]]
        assert "holder_name" in field_names, "Missing holder_name field"
        assert "check_number" in field_names, "Missing check_number field"
        assert "bank" in field_names, "Missing bank field"
        
        assert check_method["color"] == "blue", f"Check color should be blue, got {check_method['color']}"
        
        print("✓ Check method has 3 required fields (holder_name, check_number, bank), color=blue")
    
    def test_mtn_money_has_correct_required_fields(self):
        """Test MTN Money has 2 required fields: sender_number, ticket_ref"""
        response = requests.get(
            f"{BASE_URL}/api/payment-methods",
            headers=self.headers
        )
        
        methods = response.json()
        mtn_method = next((m for m in methods if m["code"] == "mtn_money"), None)
        
        assert mtn_method is not None, "MTN Money method not found"
        assert len(mtn_method["required_fields"]) == 2, f"MTN Money should have 2 fields, got {len(mtn_method['required_fields'])}"
        
        field_names = [f["name"] for f in mtn_method["required_fields"]]
        assert "sender_number" in field_names, "Missing sender_number field"
        assert "ticket_ref" in field_names, "Missing ticket_ref field"
        
        assert mtn_method["color"] == "yellow", f"MTN Money color should be yellow, got {mtn_method['color']}"
        
        print("✓ MTN Money has 2 required fields (sender_number, ticket_ref), color=yellow")
    
    def test_payment_methods_sorted_by_display_order(self):
        """Test that payment methods are sorted by display_order"""
        response = requests.get(
            f"{BASE_URL}/api/payment-methods",
            headers=self.headers
        )
        
        methods = response.json()
        display_orders = [m["display_order"] for m in methods]
        
        # Verify sorted in ascending order
        assert display_orders == sorted(display_orders), f"Methods not sorted by display_order: {display_orders}"
        
        # Verify expected order: cash(1), orange_money(2), card(3), check(4), mtn_money(5)
        expected_order = ["cash", "orange_money", "card", "check", "mtn_money"]
        actual_order = [m["code"] for m in methods]
        assert actual_order == expected_order, f"Expected order {expected_order}, got {actual_order}"
        
        print("✓ Payment methods sorted by display_order correctly")
    
    def test_each_method_has_required_structure(self):
        """Test that each payment method has all required fields in structure"""
        response = requests.get(
            f"{BASE_URL}/api/payment-methods",
            headers=self.headers
        )
        
        methods = response.json()
        required_keys = ["id", "code", "name", "icon", "color", "required_fields", "is_active", "display_order", "tenant_id"]
        
        for method in methods:
            for key in required_keys:
                assert key in method, f"Method {method.get('code', 'unknown')} missing key: {key}"
        
        print(f"✓ All {len(methods)} methods have required structure")


class TestSaleWithPaymentMethod:
    """Test creating sales with different payment methods"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - authenticate and get token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        assert login_response.status_code == 200
        self.token = login_response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # Get a product with stock for testing
        products_response = requests.get(
            f"{BASE_URL}/api/products",
            headers=self.headers
        )
        if products_response.status_code == 200:
            products = products_response.json()
            self.test_product = next((p for p in products if p.get("stock", 0) > 0), None)
    
    def test_create_sale_with_cash_payment(self):
        """Test creating a sale with cash payment (no payment details required)"""
        if not hasattr(self, 'test_product') or not self.test_product:
            pytest.skip("No product with stock available for testing")
        
        sale_data = {
            "items": [{
                "product_id": self.test_product["id"],
                "product_name": self.test_product["name"],
                "unit_price": self.test_product["price"],
                "quantity": 1,
                "subtotal": self.test_product["price"]
            }],
            "subtotal": self.test_product["price"],
            "total": self.test_product["price"],
            "payment_method": "cash",
            "payment_details": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            headers=self.headers,
            json=sale_data
        )
        
        assert response.status_code in [200, 201], f"Sale creation failed: {response.text}"
        sale = response.json()
        assert sale["payment_method"] == "cash"
        
        print("✓ Sale with cash payment created successfully")
    
    def test_create_sale_with_orange_money_payment(self):
        """Test creating a sale with Orange Money payment (with payment details)"""
        if not hasattr(self, 'test_product') or not self.test_product:
            pytest.skip("No product with stock available for testing")
        
        sale_data = {
            "items": [{
                "product_id": self.test_product["id"],
                "product_name": self.test_product["name"],
                "unit_price": self.test_product["price"],
                "quantity": 1,
                "subtotal": self.test_product["price"]
            }],
            "subtotal": self.test_product["price"],
            "total": self.test_product["price"],
            "payment_method": "orange_money",
            "payment_details": {
                "sender_number": "620123456",
                "ticket_ref": "TRX123456789"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            headers=self.headers,
            json=sale_data
        )
        
        assert response.status_code in [200, 201], f"Sale creation failed: {response.text}"
        sale = response.json()
        assert sale["payment_method"] == "orange_money"
        assert sale.get("payment_details") is not None
        
        print("✓ Sale with Orange Money payment created successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
