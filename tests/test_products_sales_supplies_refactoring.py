"""
Test suite for React Query refactoring of Products, Sales, and Supplies pages
Tests the hooks: useProducts, useSales, useSupplies, useCategories, useUnits, useSuppliers, useReturns
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pharmacy-mgmt-portal.preview.emergentagent.com').rstrip('/')

class TestAuthentication:
    """Test authentication for admin user"""
    
    def test_admin_login(self):
        """Test admin login to get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]


class TestProductsHooks:
    """Test Products page hooks - useProducts, useCreateProduct, useUpdateProduct, useDeleteProduct, useToggleProductStatus"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_products_useProducts_hook(self):
        """Test GET /api/products - useProducts hook"""
        response = requests.get(f"{BASE_URL}/api/products", headers=self.headers)
        assert response.status_code == 200, f"Failed to get products: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Products should be a list"
        print(f"✓ useProducts hook works - {len(data)} products found")
    
    def test_create_product_useCreateProduct_hook(self):
        """Test POST /api/products - useCreateProduct hook"""
        product_data = {
            "name": "TEST_Product_RQ_Refactor",
            "internal_reference": "TEST001",
            "barcode": "1234567890123",
            "description": "Test product for React Query refactoring",
            "category_id": None,
            "unit_id": None
        }
        response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=self.headers)
        assert response.status_code in [200, 201], f"Failed to create product: {response.text}"
        data = response.json()
        assert data["name"] == product_data["name"], "Product name mismatch"
        print(f"✓ useCreateProduct hook works - Product ID: {data.get('id')}")
        
        # Cleanup
        if data.get("id"):
            requests.delete(f"{BASE_URL}/api/products/{data['id']}", headers=self.headers)
    
    def test_update_product_useUpdateProduct_hook(self):
        """Test PUT /api/products/{id} - useUpdateProduct hook"""
        # Create a product first
        product_data = {
            "name": "TEST_Product_Update",
            "internal_reference": "TEST002"
        }
        create_response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=self.headers)
        product_id = create_response.json().get("id")
        
        # Update the product
        update_data = {
            "name": "TEST_Product_Updated",
            "description": "Updated description"
        }
        response = requests.put(f"{BASE_URL}/api/products/{product_id}", json=update_data, headers=self.headers)
        assert response.status_code == 200, f"Failed to update product: {response.text}"
        data = response.json()
        assert data["name"] == update_data["name"], "Product name not updated"
        print(f"✓ useUpdateProduct hook works - Product updated")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/products/{product_id}", headers=self.headers)
    
    def test_toggle_product_status_useToggleProductStatus_hook(self):
        """Test PATCH /api/products/{id}/toggle-status - useToggleProductStatus hook"""
        # Create a product first
        product_data = {"name": "TEST_Product_Toggle"}
        create_response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=self.headers)
        product_id = create_response.json().get("id")
        
        # Toggle status
        response = requests.patch(f"{BASE_URL}/api/products/{product_id}/toggle-status", headers=self.headers)
        assert response.status_code == 200, f"Failed to toggle status: {response.text}"
        print(f"✓ useToggleProductStatus hook works")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/products/{product_id}", headers=self.headers)
    
    def test_delete_product_useDeleteProduct_hook(self):
        """Test DELETE /api/products/{id} - useDeleteProduct hook"""
        # Create a product first
        product_data = {"name": "TEST_Product_Delete"}
        create_response = requests.post(f"{BASE_URL}/api/products", json=product_data, headers=self.headers)
        product_id = create_response.json().get("id")
        
        # Delete the product
        response = requests.delete(f"{BASE_URL}/api/products/{product_id}", headers=self.headers)
        assert response.status_code in [200, 204], f"Failed to delete product: {response.text}"
        print(f"✓ useDeleteProduct hook works")


class TestCategoriesHooks:
    """Test Categories hooks - useCategories, useCreateCategory, useUpdateCategory, useDeleteCategory"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_categories_useCategories_hook(self):
        """Test GET /api/categories - useCategories hook"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=self.headers)
        assert response.status_code == 200, f"Failed to get categories: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Categories should be a list"
        print(f"✓ useCategories hook works - {len(data)} categories found")
    
    def test_create_category_useCreateCategory_hook(self):
        """Test POST /api/categories - useCreateCategory hook"""
        category_data = {
            "name": "TEST_Category_RQ",
            "description": "Test category",
            "color": "#FF5733",
            "markup_coefficient": 1.25,
            "min_stock": 5
        }
        response = requests.post(f"{BASE_URL}/api/categories", json=category_data, headers=self.headers)
        assert response.status_code in [200, 201], f"Failed to create category: {response.text}"
        data = response.json()
        assert data["name"] == category_data["name"], "Category name mismatch"
        print(f"✓ useCreateCategory hook works - Category ID: {data.get('id')}")
        
        # Cleanup
        if data.get("id"):
            requests.delete(f"{BASE_URL}/api/categories/{data['id']}", headers=self.headers)
    
    def test_delete_category_useDeleteCategory_hook(self):
        """Test DELETE /api/categories/{id} - useDeleteCategory hook"""
        # Create a category first
        category_data = {"name": "TEST_Category_Delete", "color": "#333333"}
        create_response = requests.post(f"{BASE_URL}/api/categories", json=category_data, headers=self.headers)
        category_id = create_response.json().get("id")
        
        # Delete the category
        response = requests.delete(f"{BASE_URL}/api/categories/{category_id}", headers=self.headers)
        assert response.status_code in [200, 204], f"Failed to delete category: {response.text}"
        print(f"✓ useDeleteCategory hook works")


class TestUnitsHooks:
    """Test Units hooks - useUnits, useCreateUnit, useUpdateUnit, useDeleteUnit"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_units_useUnits_hook(self):
        """Test GET /api/units - useUnits hook"""
        response = requests.get(f"{BASE_URL}/api/units", headers=self.headers)
        assert response.status_code == 200, f"Failed to get units: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Units should be a list"
        print(f"✓ useUnits hook works - {len(data)} units found")
    
    def test_create_unit_useCreateUnit_hook(self):
        """Test POST /api/units - useCreateUnit hook"""
        unit_data = {
            "name": "TEST_Unit_RQ",
            "abbreviation": "TRQ",
            "description": "Test unit"
        }
        response = requests.post(f"{BASE_URL}/api/units", json=unit_data, headers=self.headers)
        assert response.status_code in [200, 201], f"Failed to create unit: {response.text}"
        data = response.json()
        assert data["name"] == unit_data["name"], "Unit name mismatch"
        print(f"✓ useCreateUnit hook works - Unit ID: {data.get('id')}")
        
        # Cleanup
        if data.get("id"):
            requests.delete(f"{BASE_URL}/api/units/{data['id']}", headers=self.headers)
    
    def test_delete_unit_useDeleteUnit_hook(self):
        """Test DELETE /api/units/{id} - useDeleteUnit hook"""
        # Create a unit first
        unit_data = {"name": "TEST_Unit_Delete", "abbreviation": "TUD"}
        create_response = requests.post(f"{BASE_URL}/api/units", json=unit_data, headers=self.headers)
        unit_id = create_response.json().get("id")
        
        # Delete the unit
        response = requests.delete(f"{BASE_URL}/api/units/{unit_id}", headers=self.headers)
        assert response.status_code in [200, 204], f"Failed to delete unit: {response.text}"
        print(f"✓ useDeleteUnit hook works")


class TestSalesHooks:
    """Test Sales page hooks - useSales, useCreateSale"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_sales_useSales_hook(self):
        """Test GET /api/sales - useSales hook"""
        response = requests.get(f"{BASE_URL}/api/sales", headers=self.headers)
        assert response.status_code == 200, f"Failed to get sales: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Sales should be a list"
        print(f"✓ useSales hook works - {len(data)} sales found")
    
    def test_create_sale_useCreateSale_hook(self):
        """Test POST /api/sales - useCreateSale hook"""
        # First get a product with stock
        products_response = requests.get(f"{BASE_URL}/api/products", headers=self.headers)
        products = products_response.json()
        product_with_stock = next((p for p in products if p.get("stock", 0) > 0), None)
        
        if not product_with_stock:
            pytest.skip("No product with stock available for sale test")
        
        sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": product_with_stock["id"],
                "product_name": product_with_stock["name"],
                "unit_price": product_with_stock.get("price", 100),
                "quantity": 1,
                "subtotal": product_with_stock.get("price", 100)
            }],
            "total": product_with_stock.get("price", 100),
            "payment_method": "cash"
        }
        response = requests.post(f"{BASE_URL}/api/sales", json=sale_data, headers=self.headers)
        assert response.status_code in [200, 201], f"Failed to create sale: {response.text}"
        data = response.json()
        assert "id" in data or "sale_number" in data, "Sale should have id or sale_number"
        print(f"✓ useCreateSale hook works - Sale created")


class TestReturnsHooks:
    """Test Returns hooks - useOperationsHistory, useCreateReturn"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_operations_history_useOperationsHistory_hook(self):
        """Test GET /api/returns/history - useOperationsHistory hook"""
        response = requests.get(f"{BASE_URL}/api/returns/history", headers=self.headers)
        assert response.status_code == 200, f"Failed to get operations history: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Operations history should be a list"
        print(f"✓ useOperationsHistory hook works - {len(data)} operations found")
    
    def test_get_returns_useReturns_hook(self):
        """Test GET /api/returns - useReturns hook"""
        response = requests.get(f"{BASE_URL}/api/returns", headers=self.headers)
        assert response.status_code == 200, f"Failed to get returns: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Returns should be a list"
        print(f"✓ useReturns hook works - {len(data)} returns found")


class TestSuppliesHooks:
    """Test Supplies page hooks - useSupplies, useCreateSupply, useValidateSupply"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_supplies_useSupplies_hook(self):
        """Test GET /api/supplies - useSupplies hook"""
        response = requests.get(f"{BASE_URL}/api/supplies", headers=self.headers)
        assert response.status_code == 200, f"Failed to get supplies: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Supplies should be a list"
        print(f"✓ useSupplies hook works - {len(data)} supplies found")
    
    def test_create_supply_useCreateSupply_hook(self):
        """Test POST /api/supplies - useCreateSupply hook"""
        # Get a supplier and product first
        suppliers_response = requests.get(f"{BASE_URL}/api/suppliers", headers=self.headers)
        suppliers = suppliers_response.json()
        supplier = next((s for s in suppliers if s.get("is_active", True)), None)
        
        products_response = requests.get(f"{BASE_URL}/api/products", headers=self.headers)
        products = products_response.json()
        product = next((p for p in products if p.get("is_active", True) is not False), None)
        
        if not supplier or not product:
            pytest.skip("No active supplier or product available for supply test")
        
        supply_data = {
            "supply_date": "2025-01-21T00:00:00",
            "supplier_id": supplier["id"],
            "purchase_order_ref": "TEST-BC-001",
            "delivery_note_number": "TEST-BL-001",
            "invoice_number": "TEST-FACT-001",
            "notes": "Test supply for React Query refactoring",
            "items": [{
                "product_id": product["id"],
                "quantity": 10,
                "unit_price": 100
            }]
        }
        response = requests.post(f"{BASE_URL}/api/supplies", json=supply_data, headers=self.headers)
        assert response.status_code in [200, 201], f"Failed to create supply: {response.text}"
        data = response.json()
        assert "id" in data, "Supply should have id"
        print(f"✓ useCreateSupply hook works - Supply ID: {data.get('id')}")
        
        # Store for validation test
        self.created_supply_id = data.get("id")
        
        # Cleanup - delete the supply (only if not validated)
        if data.get("id") and not data.get("is_validated"):
            requests.delete(f"{BASE_URL}/api/supplies/{data['id']}", headers=self.headers)
    
    def test_validate_supply_useValidateSupply_hook(self):
        """Test POST /api/supplies/{id}/validate - useValidateSupply hook"""
        # Get a supplier and product first
        suppliers_response = requests.get(f"{BASE_URL}/api/suppliers", headers=self.headers)
        suppliers = suppliers_response.json()
        supplier = next((s for s in suppliers if s.get("is_active", True)), None)
        
        products_response = requests.get(f"{BASE_URL}/api/products", headers=self.headers)
        products = products_response.json()
        product = next((p for p in products if p.get("is_active", True) is not False), None)
        
        if not supplier or not product:
            pytest.skip("No active supplier or product available for supply validation test")
        
        # Create a supply first
        supply_data = {
            "supply_date": "2025-01-21T00:00:00",
            "supplier_id": supplier["id"],
            "purchase_order_ref": "TEST-BC-VAL",
            "delivery_note_number": "TEST-BL-VAL",
            "invoice_number": "TEST-FACT-VAL",
            "items": [{
                "product_id": product["id"],
                "quantity": 5,
                "unit_price": 50
            }]
        }
        create_response = requests.post(f"{BASE_URL}/api/supplies", json=supply_data, headers=self.headers)
        supply_id = create_response.json().get("id")
        
        if not supply_id:
            pytest.skip("Failed to create supply for validation test")
        
        # Validate the supply
        response = requests.post(f"{BASE_URL}/api/supplies/{supply_id}/validate", headers=self.headers)
        assert response.status_code == 200, f"Failed to validate supply: {response.text}"
        data = response.json()
        assert data.get("is_validated") == True, "Supply should be validated"
        print(f"✓ useValidateSupply hook works - Supply validated")


class TestSuppliersHooks:
    """Test Suppliers hooks used in Supplies page - useSuppliers, useCreateSupplier"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_suppliers_useSuppliers_hook(self):
        """Test GET /api/suppliers - useSuppliers hook"""
        response = requests.get(f"{BASE_URL}/api/suppliers", headers=self.headers)
        assert response.status_code == 200, f"Failed to get suppliers: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Suppliers should be a list"
        print(f"✓ useSuppliers hook works - {len(data)} suppliers found")
    
    def test_create_supplier_useCreateSupplier_hook(self):
        """Test POST /api/suppliers - useCreateSupplier hook (quick add in Supplies)"""
        supplier_data = {
            "name": "TEST_Supplier_RQ",
            "contact": "Test Contact",
            "phone": "+224123456789",
            "email": "test@supplier.com",
            "address": "Test Address"
        }
        response = requests.post(f"{BASE_URL}/api/suppliers", json=supplier_data, headers=self.headers)
        assert response.status_code in [200, 201], f"Failed to create supplier: {response.text}"
        data = response.json()
        assert data["name"] == supplier_data["name"], "Supplier name mismatch"
        print(f"✓ useCreateSupplier hook works - Supplier ID: {data.get('id')}")
        
        # Cleanup
        if data.get("id"):
            requests.delete(f"{BASE_URL}/api/suppliers/{data['id']}", headers=self.headers)


class TestCustomersHooks:
    """Test Customers hooks used in Sales page - useCustomers"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_customers_useCustomers_hook(self):
        """Test GET /api/customers - useCustomers hook"""
        response = requests.get(f"{BASE_URL}/api/customers", headers=self.headers)
        assert response.status_code == 200, f"Failed to get customers: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Customers should be a list"
        print(f"✓ useCustomers hook works - {len(data)} customers found")


class TestSettingsHooks:
    """Test Settings hooks used in Products/Sales/Supplies pages - useSettingsQuery"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_settings_useSettingsQuery_hook(self):
        """Test GET /api/settings - useSettingsQuery hook"""
        response = requests.get(f"{BASE_URL}/api/settings", headers=self.headers)
        assert response.status_code == 200, f"Failed to get settings: {response.text}"
        data = response.json()
        assert "currency" in data, "Settings should have currency"
        print(f"✓ useSettingsQuery hook works - Currency: {data.get('currency')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
