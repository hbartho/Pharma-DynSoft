"""
Comprehensive Backend API Tests for PharmaFlow
Tests all essential features after MongoDB to PostgreSQL migration
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@pharmaflow.com"
ADMIN_PASSWORD = "admin123"


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_success(self):
        """Test successful login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL
        assert data["user"]["role"] == "admin"
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with authentication token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestDashboard:
    """Test dashboard/reports endpoints"""
    
    def test_reports_dashboard(self, auth_headers):
        """Test reports dashboard endpoint"""
        response = requests.get(f"{BASE_URL}/api/reports/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "today_sales_count" in data
        assert "today_revenue" in data
        assert "total_products" in data
        assert "low_stock_count" in data
        assert "total_stock_value" in data


class TestProducts:
    """Test products endpoints"""
    
    def test_get_products(self, auth_headers):
        """Test getting all products"""
        response = requests.get(f"{BASE_URL}/api/products", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_products_have_stock(self, auth_headers):
        """Test that products have stock > 0 (after supply validation)"""
        response = requests.get(f"{BASE_URL}/api/products", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        products_with_stock = [p for p in data if p.get('stock', 0) > 0]
        # According to context, there should be 36 products with stock
        assert len(products_with_stock) >= 30, f"Expected at least 30 products with stock, got {len(products_with_stock)}"


class TestCustomers:
    """Test customers endpoints"""
    
    def test_get_customers(self, auth_headers):
        """Test getting all customers"""
        response = requests.get(f"{BASE_URL}/api/customers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_customer_has_max_debt_limit(self, auth_headers):
        """Test that customers have max_debt_limit field"""
        response = requests.get(f"{BASE_URL}/api/customers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for customer in data:
            assert "max_debt_limit" in customer, f"Customer {customer.get('name')} missing max_debt_limit"
    
    def test_update_customer_max_debt_limit(self, auth_headers):
        """Test updating customer max_debt_limit"""
        # Get a customer
        response = requests.get(f"{BASE_URL}/api/customers", headers=auth_headers)
        assert response.status_code == 200
        customers = response.json()
        assert len(customers) > 0
        
        customer = customers[0]
        customer_id = customer["id"]
        original_limit = customer.get("max_debt_limit", 0)
        new_limit = original_limit + 10000
        
        # Update the customer
        update_response = requests.put(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers=auth_headers,
            json={"max_debt_limit": new_limit}
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["max_debt_limit"] == new_limit
        
        # Verify persistence
        verify_response = requests.get(f"{BASE_URL}/api/customers/{customer_id}", headers=auth_headers)
        assert verify_response.status_code == 200
        verified = verify_response.json()
        assert verified["max_debt_limit"] == new_limit
        
        # Restore original value
        requests.put(
            f"{BASE_URL}/api/customers/{customer_id}",
            headers=auth_headers,
            json={"max_debt_limit": original_limit}
        )


class TestSales:
    """Test sales endpoints"""
    
    def test_get_sales(self, auth_headers):
        """Test getting sales list"""
        response = requests.get(f"{BASE_URL}/api/sales", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
    
    def test_create_simple_sale(self, auth_headers):
        """Test creating a simple cash sale"""
        # Get a product with stock
        products_response = requests.get(f"{BASE_URL}/api/products", headers=auth_headers)
        assert products_response.status_code == 200
        products = products_response.json()
        product_with_stock = next((p for p in products if p.get('stock', 0) > 5), None)
        assert product_with_stock is not None, "No product with sufficient stock found"
        
        product_id = product_with_stock["id"]
        unit_price = product_with_stock["price"]
        
        # Create sale
        sale_data = {
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 1,
                    "unit_price": unit_price
                }
            ],
            "total": unit_price,
            "payment_method": "cash",
            "is_split_payment": False
        }
        
        response = requests.post(f"{BASE_URL}/api/sales", headers=auth_headers, json=sale_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "sale_number" in data
        assert data["total"] == unit_price
        assert data["payment_method"] == "cash"


class TestSupplies:
    """Test supplies endpoints"""
    
    def test_get_supplies(self, auth_headers):
        """Test getting all supplies"""
        response = requests.get(f"{BASE_URL}/api/supplies", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_validated_supplies(self, auth_headers):
        """Test getting validated supplies"""
        response = requests.get(f"{BASE_URL}/api/supplies?status=validated", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned supplies should be validated
        for supply in data:
            assert supply.get("is_validated") == True


class TestDebts:
    """Test debts endpoints"""
    
    def test_get_debts_dashboard(self, auth_headers):
        """Test debts dashboard"""
        response = requests.get(f"{BASE_URL}/api/debts/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_receivables" in data
        assert "total_customers_with_debt" in data
        assert "overdue_amount" in data
    
    def test_get_debts_list(self, auth_headers):
        """Test getting debts list"""
        response = requests.get(f"{BASE_URL}/api/debts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_customers_debt_summary(self, auth_headers):
        """Test getting customers debt summary"""
        response = requests.get(f"{BASE_URL}/api/debts/customers-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for summary in data:
            assert "customer_id" in summary
            assert "total_debt" in summary
            assert "max_debt_limit" in summary
    
    def test_get_payments_history(self, auth_headers):
        """Test getting payments history"""
        response = requests.get(f"{BASE_URL}/api/debts/payments/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestPrescriptions:
    """Test prescriptions endpoints"""
    
    def test_get_prescriptions(self, auth_headers):
        """Test getting prescriptions list"""
        response = requests.get(f"{BASE_URL}/api/prescriptions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestSuppliers:
    """Test suppliers endpoints"""
    
    def test_get_suppliers(self, auth_headers):
        """Test getting suppliers list"""
        response = requests.get(f"{BASE_URL}/api/suppliers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


class TestShifts:
    """Test shifts endpoints"""
    
    def test_get_current_shift(self, auth_headers):
        """Test getting current shift"""
        response = requests.get(f"{BASE_URL}/api/shifts/current", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have shift data or null
        if data:
            assert "id" in data
            assert "is_active" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
