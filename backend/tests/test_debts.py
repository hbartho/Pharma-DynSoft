"""
Test suite for Debt Management Feature
Tests: Dashboard, Customer Summary, Available Credit, Debt Payment, Sales with Debt
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@pharmaflow.com"
ADMIN_PASSWORD = "admin123"
PHARMACIEN_EMAIL = "pharmacien@pharmaflow.com"
PHARMACIEN_PASSWORD = "pharma123"


class TestDebtAPIs:
    """Test debt management API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with admin authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "tenant_id": "pharmacie-centrale"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.admin_token = token
        else:
            pytest.skip(f"Admin login failed: {login_response.status_code}")
        
        yield
        self.session.close()
    
    @pytest.fixture
    def pharmacien_session(self):
        """Create a session for pharmacien user"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PHARMACIEN_EMAIL,
            "password": PHARMACIEN_PASSWORD,
            "tenant_id": "pharmacie-centrale"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Pharmacien login failed: {login_response.status_code}")
        
        yield session
        session.close()
    
    # ============== DASHBOARD TESTS ==============
    
    def test_get_debt_dashboard(self):
        """Test GET /api/debts/dashboard - returns debt statistics"""
        response = self.session.get(f"{BASE_URL}/api/debts/dashboard")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "total_receivables" in data, "Missing total_receivables"
        assert "total_customers_with_debt" in data, "Missing total_customers_with_debt"
        assert "overdue_amount" in data, "Missing overdue_amount"
        assert "overdue_count" in data, "Missing overdue_count"
        assert "collected_this_month" in data, "Missing collected_this_month"
        assert "average_debt_per_customer" in data, "Missing average_debt_per_customer"
        
        # Verify data types
        assert isinstance(data["total_receivables"], (int, float))
        assert isinstance(data["total_customers_with_debt"], int)
        assert isinstance(data["overdue_amount"], (int, float))
        print(f"Dashboard stats: {data}")
    
    # ============== CUSTOMERS SUMMARY TESTS ==============
    
    def test_get_customers_debt_summary(self):
        """Test GET /api/debts/customers-summary - returns debt summary per customer"""
        response = self.session.get(f"{BASE_URL}/api/debts/customers-summary")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        
        if len(data) > 0:
            customer = data[0]
            # Verify customer summary structure
            assert "customer_id" in customer, "Missing customer_id"
            assert "customer_name" in customer, "Missing customer_name"
            assert "max_debt_limit" in customer, "Missing max_debt_limit"
            assert "total_debt" in customer, "Missing total_debt"
            assert "available_credit" in customer, "Missing available_credit"
            print(f"Found {len(data)} customers in summary")
    
    def test_get_customers_debt_summary_only_with_debt(self):
        """Test GET /api/debts/customers-summary?only_with_debt=true"""
        response = self.session.get(f"{BASE_URL}/api/debts/customers-summary", params={"only_with_debt": True})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        
        # All returned customers should have debt > 0
        for customer in data:
            assert customer.get("total_debt", 0) > 0, f"Customer {customer.get('customer_name')} has no debt but was returned"
        
        print(f"Found {len(data)} customers with debt")
    
    # ============== AVAILABLE CREDIT TESTS ==============
    
    def test_get_customer_available_credit(self):
        """Test GET /api/debts/customer/{customer_id}/available-credit"""
        # First get a customer with credit limit
        customers_response = self.session.get(f"{BASE_URL}/api/customers")
        assert customers_response.status_code == 200
        
        customers = customers_response.json()
        customer_with_credit = None
        
        for c in customers:
            if c.get("max_debt_limit", 0) > 0:
                customer_with_credit = c
                break
        
        if not customer_with_credit:
            pytest.skip("No customer with credit limit found")
        
        customer_id = customer_with_credit["id"]
        response = self.session.get(f"{BASE_URL}/api/debts/customer/{customer_id}/available-credit")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "customer_id" in data, "Missing customer_id"
        assert "customer_name" in data, "Missing customer_name"
        assert "max_debt_limit" in data, "Missing max_debt_limit"
        assert "current_debt" in data, "Missing current_debt"
        assert "available_credit" in data, "Missing available_credit"
        assert "can_use_credit" in data, "Missing can_use_credit"
        
        # Verify calculation
        expected_available = max(0, data["max_debt_limit"] - data["current_debt"])
        assert data["available_credit"] == expected_available, f"Available credit calculation wrong"
        
        print(f"Customer {data['customer_name']}: max={data['max_debt_limit']}, current={data['current_debt']}, available={data['available_credit']}")
    
    def test_get_available_credit_nonexistent_customer(self):
        """Test GET /api/debts/customer/{customer_id}/available-credit with invalid ID"""
        response = self.session.get(f"{BASE_URL}/api/debts/customer/nonexistent-id-12345/available-credit")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    # ============== DEBT PAYMENT TESTS ==============
    
    def test_create_debt_payment_no_debt(self):
        """Test POST /api/debts/payment with nonexistent debt"""
        response = self.session.post(f"{BASE_URL}/api/debts/payment", json={
            "debt_id": "nonexistent-debt-id",
            "amount": 1000,
            "payment_method": "cash"
        })
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_create_debt_payment_invalid_amount(self):
        """Test POST /api/debts/payment with invalid amount"""
        # First get an existing debt
        debts_response = self.session.get(f"{BASE_URL}/api/debts", params={"status": "pending"})
        
        if debts_response.status_code != 200 or len(debts_response.json()) == 0:
            pytest.skip("No pending debts found for testing")
        
        debt = debts_response.json()[0]
        
        # Try with zero amount
        response = self.session.post(f"{BASE_URL}/api/debts/payment", json={
            "debt_id": debt["id"],
            "amount": 0,
            "payment_method": "cash"
        })
        
        assert response.status_code == 400, f"Expected 400 for zero amount, got {response.status_code}"
    
    # ============== DEBTS LIST TESTS ==============
    
    def test_get_debts_list(self):
        """Test GET /api/debts - returns all debts"""
        response = self.session.get(f"{BASE_URL}/api/debts")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        
        if len(data) > 0:
            debt = data[0]
            # Verify debt structure
            assert "id" in debt, "Missing id"
            assert "customer_id" in debt, "Missing customer_id"
            assert "original_amount" in debt, "Missing original_amount"
            assert "remaining_amount" in debt, "Missing remaining_amount"
            assert "status" in debt, "Missing status"
        
        print(f"Found {len(data)} debts")
    
    def test_get_debts_by_status(self):
        """Test GET /api/debts?status=pending"""
        response = self.session.get(f"{BASE_URL}/api/debts", params={"status": "pending"})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        for debt in data:
            assert debt["status"] == "pending", f"Expected pending status, got {debt['status']}"
    
    # ============== PAYMENTS HISTORY TESTS ==============
    
    def test_get_payments_history(self):
        """Test GET /api/debts/payments/history"""
        response = self.session.get(f"{BASE_URL}/api/debts/payments/history")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert isinstance(data, list), "Expected list response"
        
        if len(data) > 0:
            payment = data[0]
            assert "id" in payment, "Missing id"
            assert "debt_id" in payment, "Missing debt_id"
            assert "amount" in payment, "Missing amount"
            assert "payment_method" in payment, "Missing payment_method"
        
        print(f"Found {len(data)} payment records")


class TestSalesWithDebt:
    """Test sales creation with debt payment method"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "tenant_id": "pharmacie-centrale"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Admin login failed: {login_response.status_code}")
        
        yield
        self.session.close()
    
    @pytest.fixture
    def pharmacien_session(self):
        """Create a session for pharmacien user"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PHARMACIEN_EMAIL,
            "password": PHARMACIEN_PASSWORD,
            "tenant_id": "pharmacie-centrale"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield session
        session.close()
    
    def test_sale_with_debt_requires_customer(self):
        """Test that debt sale requires a customer"""
        # Get a product with stock
        products_response = self.session.get(f"{BASE_URL}/api/products")
        assert products_response.status_code == 200
        
        products = products_response.json()
        product_with_stock = None
        for p in products:
            if p.get("stock", 0) > 0:
                product_with_stock = p
                break
        
        if not product_with_stock:
            pytest.skip("No product with stock found")
        
        # Try to create sale with debt but no customer
        sale_data = {
            "items": [{
                "product_id": product_with_stock["id"],
                "quantity": 1,
                "unit_price": product_with_stock.get("price", 1000),
                "subtotal": product_with_stock.get("price", 1000)
            }],
            "total": product_with_stock.get("price", 1000),
            "payment_method": "debt",
            "customer_id": None  # No customer
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        assert "client" in response.text.lower() or "customer" in response.text.lower(), "Error should mention customer requirement"
        print(f"Correctly blocked: {response.json().get('detail')}")
    
    def test_sale_with_debt_requires_admin(self, pharmacien_session):
        """Test that only admin can create debt sales"""
        # Get a product with stock
        products_response = pharmacien_session.get(f"{BASE_URL}/api/products")
        assert products_response.status_code == 200
        
        products = products_response.json()
        product_with_stock = None
        for p in products:
            if p.get("stock", 0) > 0:
                product_with_stock = p
                break
        
        if not product_with_stock:
            pytest.skip("No product with stock found")
        
        # Get a customer with credit
        customers_response = pharmacien_session.get(f"{BASE_URL}/api/customers")
        assert customers_response.status_code == 200
        
        customers = customers_response.json()
        customer_with_credit = None
        for c in customers:
            if c.get("max_debt_limit", 0) > 0:
                customer_with_credit = c
                break
        
        if not customer_with_credit:
            pytest.skip("No customer with credit found")
        
        # Try to create sale with debt as pharmacien
        sale_data = {
            "items": [{
                "product_id": product_with_stock["id"],
                "quantity": 1,
                "unit_price": product_with_stock.get("price", 1000),
                "subtotal": product_with_stock.get("price", 1000)
            }],
            "total": product_with_stock.get("price", 1000),
            "payment_method": "debt",
            "customer_id": customer_with_credit["id"]
        }
        
        response = pharmacien_session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        print(f"Correctly blocked non-admin: {response.json().get('detail')}")
    
    def test_sale_with_debt_checks_credit_limit(self):
        """Test that debt sale checks customer credit limit"""
        # Get a customer with no credit (max_debt_limit = 0)
        customers_response = self.session.get(f"{BASE_URL}/api/customers")
        assert customers_response.status_code == 200
        
        customers = customers_response.json()
        customer_no_credit = None
        for c in customers:
            if c.get("max_debt_limit", 0) == 0:
                customer_no_credit = c
                break
        
        if not customer_no_credit:
            pytest.skip("No customer without credit found")
        
        # Get a product with stock
        products_response = self.session.get(f"{BASE_URL}/api/products")
        products = products_response.json()
        product_with_stock = None
        for p in products:
            if p.get("stock", 0) > 0:
                product_with_stock = p
                break
        
        if not product_with_stock:
            pytest.skip("No product with stock found")
        
        # Try to create sale with debt for customer without credit
        sale_data = {
            "items": [{
                "product_id": product_with_stock["id"],
                "quantity": 1,
                "unit_price": product_with_stock.get("price", 1000),
                "subtotal": product_with_stock.get("price", 1000)
            }],
            "total": product_with_stock.get("price", 1000),
            "payment_method": "debt",
            "customer_id": customer_no_credit["id"]
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print(f"Correctly blocked no credit: {response.json().get('detail')}")


class TestPaymentMethods:
    """Test payment methods include debt option"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "tenant_id": "pharmacie-centrale"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        self.session.close()
    
    def test_debt_payment_method_exists(self):
        """Test that 'debt' payment method exists in the system"""
        response = self.session.get(f"{BASE_URL}/api/payment-methods")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        methods = response.json()
        debt_method = None
        for m in methods:
            if m.get("code") == "debt":
                debt_method = m
                break
        
        assert debt_method is not None, "Debt payment method not found"
        assert debt_method.get("admin_only") == True, "Debt method should be admin_only"
        assert debt_method.get("requires_customer") == True, "Debt method should require customer"
        
        print(f"Debt payment method: {debt_method}")


class TestCustomerDebtFields:
    """Test customer model has debt-related fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "tenant_id": "pharmacie-centrale"
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        self.session.close()
    
    def test_customer_has_debt_fields(self):
        """Test that customers have max_debt_limit and current_debt fields"""
        response = self.session.get(f"{BASE_URL}/api/customers")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        customers = response.json()
        assert len(customers) > 0, "No customers found"
        
        customer = customers[0]
        assert "max_debt_limit" in customer, "Customer missing max_debt_limit field"
        assert "current_debt" in customer, "Customer missing current_debt field"
        
        print(f"Customer {customer.get('name')}: max_debt_limit={customer.get('max_debt_limit')}, current_debt={customer.get('current_debt')}")
    
    def test_update_customer_max_debt_limit(self):
        """Test updating customer max_debt_limit"""
        # Get a customer
        response = self.session.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200
        
        customers = response.json()
        if len(customers) == 0:
            pytest.skip("No customers found")
        
        customer = customers[0]
        original_limit = customer.get("max_debt_limit", 0)
        
        # Update the limit - include name as it's required by the API
        new_limit = original_limit + 10000
        update_response = self.session.put(f"{BASE_URL}/api/customers/{customer['id']}", json={
            "name": customer.get("name"),  # Required field
            "max_debt_limit": new_limit
        })
        
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        # Verify the update
        verify_response = self.session.get(f"{BASE_URL}/api/customers/{customer['id']}")
        assert verify_response.status_code == 200
        
        updated_customer = verify_response.json()
        assert updated_customer.get("max_debt_limit") == new_limit, f"max_debt_limit not updated correctly"
        
        # Restore original value
        self.session.put(f"{BASE_URL}/api/customers/{customer['id']}", json={
            "name": customer.get("name"),
            "max_debt_limit": original_limit
        })
        
        print(f"Successfully updated max_debt_limit from {original_limit} to {new_limit}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
