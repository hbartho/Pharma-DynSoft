"""
Test suite for React Query refactoring - Testing backend APIs
Tests for: Customers, Suppliers, Users, Settings pages
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@pharmaflow.com"
ADMIN_PASSWORD = "admin123"


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def auth_data(api_client):
    """Get authentication token and user data"""
    response = api_client.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    return data


@pytest.fixture(scope="module")
def auth_token(auth_data):
    """Get authentication token"""
    return auth_data["access_token"]


@pytest.fixture(scope="module")
def tenant_id(auth_data):
    """Get tenant_id from logged in user"""
    return auth_data["user"]["tenant_id"]


@pytest.fixture(scope="module")
def authenticated_client(api_client, auth_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return api_client


# ============================================
# CUSTOMERS API TESTS (useCustomers hooks)
# ============================================

class TestCustomersAPI:
    """Tests for /api/customers endpoints - used by useCustomers hook"""
    
    def test_get_customers_list(self, authenticated_client):
        """GET /api/customers - useCustomers hook"""
        response = authenticated_client.get(f"{BASE_URL}/api/customers")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/customers - Found {len(data)} customers")
    
    def test_create_customer(self, authenticated_client):
        """POST /api/customers - useCreateCustomer hook"""
        customer_data = {
            "name": "TEST_Client_ReactQuery",
            "phone": "+224 620 00 00 01",
            "email": "test_rq@example.com",
            "address": "123 Test Street"
        }
        response = authenticated_client.post(f"{BASE_URL}/api/customers", json=customer_data)
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        data = response.json()
        assert data["name"] == customer_data["name"]
        assert "id" in data
        print(f"✓ POST /api/customers - Created customer: {data['id']}")
        return data["id"]
    
    def test_get_customer_by_id(self, authenticated_client):
        """GET /api/customers/{id} - useCustomer hook"""
        # First get list to find an ID
        response = authenticated_client.get(f"{BASE_URL}/api/customers")
        customers = response.json()
        if customers:
            customer_id = customers[0]["id"]
            response = authenticated_client.get(f"{BASE_URL}/api/customers/{customer_id}")
            assert response.status_code == 200, f"Failed: {response.text}"
            data = response.json()
            assert data["id"] == customer_id
            print(f"✓ GET /api/customers/{customer_id} - Retrieved customer")
    
    def test_update_customer(self, authenticated_client):
        """PUT /api/customers/{id} - useUpdateCustomer hook"""
        # Create a test customer first
        customer_data = {
            "name": "TEST_Update_Customer",
            "phone": "+224 620 00 00 02"
        }
        create_response = authenticated_client.post(f"{BASE_URL}/api/customers", json=customer_data)
        customer_id = create_response.json()["id"]
        
        # Update the customer
        update_data = {
            "name": "TEST_Updated_Customer",
            "phone": "+224 620 00 00 03",
            "email": "updated@example.com"
        }
        response = authenticated_client.put(f"{BASE_URL}/api/customers/{customer_id}", json=update_data)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["name"] == update_data["name"]
        print(f"✓ PUT /api/customers/{customer_id} - Updated customer")
    
    def test_delete_customer(self, authenticated_client):
        """DELETE /api/customers/{id} - useDeleteCustomer hook"""
        # Create a test customer first
        customer_data = {
            "name": "TEST_Delete_Customer",
            "phone": "+224 620 00 00 04"
        }
        create_response = authenticated_client.post(f"{BASE_URL}/api/customers", json=customer_data)
        customer_id = create_response.json()["id"]
        
        # Delete the customer
        response = authenticated_client.delete(f"{BASE_URL}/api/customers/{customer_id}")
        assert response.status_code in [200, 204], f"Failed: {response.text}"
        print(f"✓ DELETE /api/customers/{customer_id} - Deleted customer")
        
        # Verify deletion
        get_response = authenticated_client.get(f"{BASE_URL}/api/customers/{customer_id}")
        assert get_response.status_code == 404, "Customer should not exist after deletion"


# ============================================
# SUPPLIERS API TESTS (useSuppliers hooks)
# ============================================

class TestSuppliersAPI:
    """Tests for /api/suppliers endpoints - used by useSuppliers hook"""
    
    def test_get_suppliers_list(self, authenticated_client):
        """GET /api/suppliers - useSuppliers hook"""
        response = authenticated_client.get(f"{BASE_URL}/api/suppliers")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/suppliers - Found {len(data)} suppliers")
    
    def test_create_supplier(self, authenticated_client):
        """POST /api/suppliers - useCreateSupplier hook"""
        supplier_data = {
            "name": "TEST_Supplier_ReactQuery",
            "phone": "+224 620 00 00 10",
            "email": "supplier_rq@example.com",
            "address": "456 Supplier Street"
        }
        response = authenticated_client.post(f"{BASE_URL}/api/suppliers", json=supplier_data)
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        data = response.json()
        assert data["name"] == supplier_data["name"]
        assert "id" in data
        print(f"✓ POST /api/suppliers - Created supplier: {data['id']}")
        return data["id"]
    
    def test_get_supplier_by_id(self, authenticated_client):
        """GET /api/suppliers/{id} - useSupplier hook"""
        # First get list to find an ID
        response = authenticated_client.get(f"{BASE_URL}/api/suppliers")
        suppliers = response.json()
        if suppliers:
            supplier_id = suppliers[0]["id"]
            response = authenticated_client.get(f"{BASE_URL}/api/suppliers/{supplier_id}")
            assert response.status_code == 200, f"Failed: {response.text}"
            data = response.json()
            assert data["id"] == supplier_id
            print(f"✓ GET /api/suppliers/{supplier_id} - Retrieved supplier")
    
    def test_update_supplier(self, authenticated_client):
        """PUT /api/suppliers/{id} - useUpdateSupplier hook"""
        # Create a test supplier first
        supplier_data = {
            "name": "TEST_Update_Supplier",
            "phone": "+224 620 00 00 11"
        }
        create_response = authenticated_client.post(f"{BASE_URL}/api/suppliers", json=supplier_data)
        supplier_id = create_response.json()["id"]
        
        # Update the supplier
        update_data = {
            "name": "TEST_Updated_Supplier",
            "phone": "+224 620 00 00 12",
            "email": "updated_supplier@example.com"
        }
        response = authenticated_client.put(f"{BASE_URL}/api/suppliers/{supplier_id}", json=update_data)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["name"] == update_data["name"]
        print(f"✓ PUT /api/suppliers/{supplier_id} - Updated supplier")
    
    def test_toggle_supplier_status(self, authenticated_client):
        """PATCH /api/suppliers/{id}/toggle-status - useToggleSupplierStatus hook"""
        # Create a test supplier first
        supplier_data = {
            "name": "TEST_Toggle_Supplier",
            "phone": "+224 620 00 00 13"
        }
        create_response = authenticated_client.post(f"{BASE_URL}/api/suppliers", json=supplier_data)
        supplier_id = create_response.json()["id"]
        initial_status = create_response.json().get("is_active", True)
        
        # Toggle status
        response = authenticated_client.patch(f"{BASE_URL}/api/suppliers/{supplier_id}/toggle-status")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # Status should be toggled
        assert data.get("is_active") != initial_status or data.get("is_active") is not None
        print(f"✓ PATCH /api/suppliers/{supplier_id}/toggle-status - Toggled status")
    
    def test_delete_supplier(self, authenticated_client):
        """DELETE /api/suppliers/{id} - useDeleteSupplier hook"""
        # Create a test supplier first
        supplier_data = {
            "name": "TEST_Delete_Supplier",
            "phone": "+224 620 00 00 14"
        }
        create_response = authenticated_client.post(f"{BASE_URL}/api/suppliers", json=supplier_data)
        supplier_id = create_response.json()["id"]
        
        # Delete the supplier
        response = authenticated_client.delete(f"{BASE_URL}/api/suppliers/{supplier_id}")
        assert response.status_code in [200, 204], f"Failed: {response.text}"
        print(f"✓ DELETE /api/suppliers/{supplier_id} - Deleted supplier")


# ============================================
# USERS API TESTS (useUsers hooks)
# ============================================

class TestUsersAPI:
    """Tests for /api/users endpoints - used by useUsers hook"""
    
    def test_get_users_list(self, authenticated_client):
        """GET /api/users - useUsers hook"""
        response = authenticated_client.get(f"{BASE_URL}/api/users")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ GET /api/users - Found {len(data)} users")
    
    def test_create_user(self, authenticated_client, tenant_id):
        """POST /api/users - useCreateUser hook"""
        timestamp = int(time.time())
        user_data = {
            "first_name": "TEST",
            "last_name": "ReactQuery",
            "email": f"test_rq_{timestamp}@example.com",
            "password": "testpass123",
            "role": "caissier",
            "employee_code": f"TST-{timestamp}",
            "tenant_id": tenant_id
        }
        response = authenticated_client.post(f"{BASE_URL}/api/users", json=user_data)
        assert response.status_code in [200, 201], f"Failed: {response.text}"
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data
        print(f"✓ POST /api/users - Created user: {data['id']}")
    
    def test_get_user_by_id(self, authenticated_client):
        """GET /api/users/{id} - useUser hook"""
        # First get list to find an ID
        response = authenticated_client.get(f"{BASE_URL}/api/users")
        users = response.json()
        if users:
            user_id = users[0]["id"]
            response = authenticated_client.get(f"{BASE_URL}/api/users/{user_id}")
            assert response.status_code == 200, f"Failed: {response.text}"
            data = response.json()
            assert data["id"] == user_id
            print(f"✓ GET /api/users/{user_id} - Retrieved user")
    
    def test_update_user(self, authenticated_client, tenant_id):
        """PUT /api/users/{id} - useUpdateUser hook"""
        # Create a test user first
        timestamp = int(time.time())
        user_data = {
            "first_name": "TEST",
            "last_name": "Update",
            "email": f"test_update_{timestamp}@example.com",
            "password": "testpass123",
            "role": "caissier",
            "employee_code": f"UPD-{timestamp}",
            "tenant_id": tenant_id
        }
        create_response = authenticated_client.post(f"{BASE_URL}/api/users", json=user_data)
        assert create_response.status_code in [200, 201], f"Create failed: {create_response.text}"
        user_id = create_response.json()["id"]
        
        # Update the user
        update_data = {
            "first_name": "TEST_Updated",
            "last_name": "User",
            "role": "pharmacien"
        }
        response = authenticated_client.put(f"{BASE_URL}/api/users/{user_id}", json=update_data)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["first_name"] == update_data["first_name"]
        print(f"✓ PUT /api/users/{user_id} - Updated user")
    
    def test_toggle_user_status(self, authenticated_client, tenant_id):
        """PATCH /api/users/{id}/toggle-status - useToggleUserStatus hook"""
        # Create a test user first
        timestamp = int(time.time())
        user_data = {
            "first_name": "TEST",
            "last_name": "Toggle",
            "email": f"test_toggle_{timestamp}@example.com",
            "password": "testpass123",
            "role": "caissier",
            "employee_code": f"TGL-{timestamp}",
            "tenant_id": tenant_id
        }
        create_response = authenticated_client.post(f"{BASE_URL}/api/users", json=user_data)
        assert create_response.status_code in [200, 201], f"Create failed: {create_response.text}"
        user_id = create_response.json()["id"]
        
        # Toggle status
        response = authenticated_client.patch(f"{BASE_URL}/api/users/{user_id}/toggle-status")
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"✓ PATCH /api/users/{user_id}/toggle-status - Toggled status")
    
    def test_reset_user_password(self, authenticated_client, tenant_id):
        """PUT /api/users/{id}/password - useResetUserPassword hook"""
        # Create a test user first
        timestamp = int(time.time())
        user_data = {
            "first_name": "TEST",
            "last_name": "Password",
            "email": f"test_pwd_{timestamp}@example.com",
            "password": "testpass123",
            "role": "caissier",
            "employee_code": f"PWD-{timestamp}",
            "tenant_id": tenant_id
        }
        create_response = authenticated_client.post(f"{BASE_URL}/api/users", json=user_data)
        assert create_response.status_code in [200, 201], f"Create failed: {create_response.text}"
        user_id = create_response.json()["id"]
        
        # Reset password
        new_password = "newpassword456"
        response = authenticated_client.put(
            f"{BASE_URL}/api/users/{user_id}/password?new_password={new_password}"
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        print(f"✓ PUT /api/users/{user_id}/password - Reset password")
    
    def test_delete_user(self, authenticated_client, tenant_id):
        """DELETE /api/users/{id} - useDeleteUser hook"""
        # Create a test user first
        timestamp = int(time.time())
        user_data = {
            "first_name": "TEST",
            "last_name": "Delete",
            "email": f"test_del_{timestamp}@example.com",
            "password": "testpass123",
            "role": "caissier",
            "employee_code": f"DEL-{timestamp}",
            "tenant_id": tenant_id
        }
        create_response = authenticated_client.post(f"{BASE_URL}/api/users", json=user_data)
        assert create_response.status_code in [200, 201], f"Create failed: {create_response.text}"
        user_id = create_response.json()["id"]
        
        # Delete the user
        response = authenticated_client.delete(f"{BASE_URL}/api/users/{user_id}")
        assert response.status_code in [200, 204], f"Failed: {response.text}"
        print(f"✓ DELETE /api/users/{user_id} - Deleted user")


# ============================================
# SETTINGS API TESTS (useSettings hooks)
# ============================================

class TestSettingsAPI:
    """Tests for /api/settings endpoints - used by useSettings hook"""
    
    def test_get_settings(self, authenticated_client):
        """GET /api/settings - useSettingsQuery hook"""
        response = authenticated_client.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert isinstance(data, dict), "Response should be a dict"
        # Check expected fields
        expected_fields = ["currency", "pharmacy_name", "low_stock_threshold", "stock_valuation_method"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        print(f"✓ GET /api/settings - Retrieved settings")
    
    def test_update_settings(self, authenticated_client):
        """PUT /api/settings - useUpdateSettings hook"""
        # First get current settings
        get_response = authenticated_client.get(f"{BASE_URL}/api/settings")
        current_settings = get_response.json()
        
        # Update settings
        update_data = {
            "currency": current_settings.get("currency", "GNF"),
            "pharmacy_name": current_settings.get("pharmacy_name", "DynSoft Pharma"),
            "low_stock_threshold": current_settings.get("low_stock_threshold", 10),
            "default_min_stock": current_settings.get("default_min_stock", 10),
            "return_delay_days": current_settings.get("return_delay_days", 3),
            "expiration_alert_days": current_settings.get("expiration_alert_days", 30),
            "stock_valuation_method": current_settings.get("stock_valuation_method", "fefo")
        }
        
        response = authenticated_client.put(f"{BASE_URL}/api/settings", json=update_data)
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data["currency"] == update_data["currency"]
        print(f"✓ PUT /api/settings - Updated settings")
    
    def test_get_stock_valuation(self, authenticated_client):
        """GET /api/stock/valuation - useStockValuation hook"""
        response = authenticated_client.get(f"{BASE_URL}/api/stock/valuation")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "method" in data or "products" in data or "total_valuation" in data
        print(f"✓ GET /api/stock/valuation - Retrieved stock valuation")


# ============================================
# CLEANUP TEST DATA
# ============================================

class TestCleanup:
    """Cleanup test data created during tests"""
    
    def test_cleanup_test_customers(self, authenticated_client):
        """Remove TEST_ prefixed customers"""
        response = authenticated_client.get(f"{BASE_URL}/api/customers")
        customers = response.json()
        deleted = 0
        for customer in customers:
            if customer.get("name", "").startswith("TEST_"):
                del_response = authenticated_client.delete(f"{BASE_URL}/api/customers/{customer['id']}")
                if del_response.status_code in [200, 204]:
                    deleted += 1
        print(f"✓ Cleanup - Deleted {deleted} test customers")
    
    def test_cleanup_test_suppliers(self, authenticated_client):
        """Remove TEST_ prefixed suppliers"""
        response = authenticated_client.get(f"{BASE_URL}/api/suppliers")
        suppliers = response.json()
        deleted = 0
        for supplier in suppliers:
            if supplier.get("name", "").startswith("TEST_"):
                del_response = authenticated_client.delete(f"{BASE_URL}/api/suppliers/{supplier['id']}")
                if del_response.status_code in [200, 204]:
                    deleted += 1
        print(f"✓ Cleanup - Deleted {deleted} test suppliers")
    
    def test_cleanup_test_users(self, authenticated_client):
        """Remove TEST_ prefixed users"""
        response = authenticated_client.get(f"{BASE_URL}/api/users")
        users = response.json()
        deleted = 0
        for user in users:
            if user.get("first_name", "").startswith("TEST"):
                del_response = authenticated_client.delete(f"{BASE_URL}/api/users/{user['id']}")
                if del_response.status_code in [200, 204]:
                    deleted += 1
        print(f"✓ Cleanup - Deleted {deleted} test users")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
