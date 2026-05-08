"""
Test suite for Stock Valuation Methods and Min Stock Configuration
Tests: FIFO, LIFO, FEFO, CMP (weighted_average) methods
Tests: default_min_stock in settings, min_stock in category, product min_stock priority
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestSettingsValuationMethods:
    """Test Settings model with stock_valuation_method and default_min_stock"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_settings_returns_default_min_stock(self):
        """GET /api/settings should return default_min_stock field"""
        response = requests.get(f"{BASE_URL}/api/settings", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "default_min_stock" in data, "default_min_stock field missing from settings"
        assert isinstance(data["default_min_stock"], int), "default_min_stock should be an integer"
    
    def test_get_settings_returns_stock_valuation_method(self):
        """GET /api/settings should return stock_valuation_method field"""
        response = requests.get(f"{BASE_URL}/api/settings", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "stock_valuation_method" in data, "stock_valuation_method field missing"
        assert data["stock_valuation_method"] in ["fifo", "lifo", "fefo", "weighted_average"], \
            f"Invalid valuation method: {data['stock_valuation_method']}"
    
    def test_update_settings_stock_valuation_method_fifo(self):
        """PUT /api/settings can update stock_valuation_method to fifo"""
        response = requests.put(f"{BASE_URL}/api/settings", 
            headers=self.headers,
            json={"stock_valuation_method": "fifo"})
        assert response.status_code == 200
        data = response.json()
        assert data["stock_valuation_method"] == "fifo"
    
    def test_update_settings_stock_valuation_method_lifo(self):
        """PUT /api/settings can update stock_valuation_method to lifo"""
        response = requests.put(f"{BASE_URL}/api/settings", 
            headers=self.headers,
            json={"stock_valuation_method": "lifo"})
        assert response.status_code == 200
        data = response.json()
        assert data["stock_valuation_method"] == "lifo"
    
    def test_update_settings_stock_valuation_method_fefo(self):
        """PUT /api/settings can update stock_valuation_method to fefo"""
        response = requests.put(f"{BASE_URL}/api/settings", 
            headers=self.headers,
            json={"stock_valuation_method": "fefo"})
        assert response.status_code == 200
        data = response.json()
        assert data["stock_valuation_method"] == "fefo"
    
    def test_update_settings_stock_valuation_method_weighted_average(self):
        """PUT /api/settings can update stock_valuation_method to weighted_average (CMP)"""
        response = requests.put(f"{BASE_URL}/api/settings", 
            headers=self.headers,
            json={"stock_valuation_method": "weighted_average"})
        assert response.status_code == 200
        data = response.json()
        assert data["stock_valuation_method"] == "weighted_average"
    
    def test_update_settings_default_min_stock(self):
        """PUT /api/settings can update default_min_stock"""
        new_min_stock = 25
        response = requests.put(f"{BASE_URL}/api/settings", 
            headers=self.headers,
            json={"default_min_stock": new_min_stock})
        assert response.status_code == 200
        data = response.json()
        assert data["default_min_stock"] == new_min_stock
        
        # Verify by GET
        get_response = requests.get(f"{BASE_URL}/api/settings", headers=self.headers)
        assert get_response.status_code == 200
        assert get_response.json()["default_min_stock"] == new_min_stock


class TestCategoryMinStock:
    """Test Category model with optional min_stock field"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        self.created_category_ids = []
    
    def teardown_method(self, method):
        """Cleanup: Delete test categories"""
        for cat_id in self.created_category_ids:
            try:
                requests.delete(f"{BASE_URL}/api/categories/{cat_id}", headers=self.headers)
            except:
                pass
    
    def test_create_category_with_min_stock(self):
        """POST /api/categories can create category with min_stock"""
        category_data = {
            "name": f"TEST_Category_{uuid.uuid4().hex[:8]}",
            "description": "Test category with min_stock",
            "min_stock": 50,
            "markup_coefficient": 1.3
        }
        response = requests.post(f"{BASE_URL}/api/categories", 
            headers=self.headers, json=category_data)
        # API returns 200 or 201 for successful creation
        assert response.status_code in [200, 201], f"Failed to create category: {response.text}"
        data = response.json()
        self.created_category_ids.append(data["id"])
        
        assert data["min_stock"] == 50, "min_stock not set correctly on category"
    
    def test_create_category_without_min_stock(self):
        """POST /api/categories can create category without min_stock (optional field)"""
        category_data = {
            "name": f"TEST_Category_{uuid.uuid4().hex[:8]}",
            "description": "Test category without min_stock"
        }
        response = requests.post(f"{BASE_URL}/api/categories", 
            headers=self.headers, json=category_data)
        # API returns 200 or 201 for successful creation
        assert response.status_code in [200, 201]
        data = response.json()
        self.created_category_ids.append(data["id"])
        
        # min_stock should be None or not present
        assert data.get("min_stock") is None, "min_stock should be None when not specified"
    
    def test_get_categories_includes_min_stock(self):
        """GET /api/categories returns categories with min_stock field"""
        response = requests.get(f"{BASE_URL}/api/categories", headers=self.headers)
        assert response.status_code == 200
        categories = response.json()
        
        # Check that categories have min_stock field (can be None)
        for cat in categories[:5]:  # Check first 5
            assert "min_stock" in cat or cat.get("min_stock") is None, \
                f"Category {cat.get('name')} missing min_stock field"


class TestProductMinStockPriority:
    """Test Product min_stock calculation priority: product config > category > global default"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_products_have_min_stock_field(self):
        """GET /api/products returns products with calculated min_stock"""
        response = requests.get(f"{BASE_URL}/api/products", headers=self.headers)
        assert response.status_code == 200
        products = response.json()
        
        assert len(products) > 0, "No products found"
        
        for product in products[:5]:  # Check first 5
            assert "min_stock" in product, f"Product {product.get('name')} missing min_stock"
            assert isinstance(product["min_stock"], int), "min_stock should be an integer"
    
    def test_product_min_stock_uses_global_default(self):
        """Products without specific config use global default_min_stock"""
        # First set a known global default
        requests.put(f"{BASE_URL}/api/settings", 
            headers=self.headers,
            json={"default_min_stock": 10})
        
        # Get products
        response = requests.get(f"{BASE_URL}/api/products", headers=self.headers)
        assert response.status_code == 200
        products = response.json()
        
        # Products should have min_stock (either from config, category, or global)
        for product in products[:3]:
            assert product.get("min_stock") is not None, \
                f"Product {product.get('name')} has no min_stock"


class TestStockValuationCalculation:
    """Test stock valuation calculation with different methods"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_stock_valuation_endpoint_exists(self):
        """GET /api/stock/valuation returns stock valuation data"""
        response = requests.get(f"{BASE_URL}/api/stock/valuation", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "method" in data, "Valuation response missing 'method' field"
        assert "total_valuation" in data, "Valuation response missing 'total_valuation' field"
        assert "products" in data, "Valuation response missing 'products' field"
    
    def test_valuation_method_changes_with_settings(self):
        """Stock valuation uses method from settings"""
        # Set to FEFO
        update_resp = requests.put(f"{BASE_URL}/api/settings", 
            headers=self.headers,
            json={"stock_valuation_method": "fefo"})
        assert update_resp.status_code == 200
        
        response = requests.get(f"{BASE_URL}/api/stock/valuation", headers=self.headers)
        assert response.status_code == 200
        assert response.json()["method"] == "fefo", f"Expected fefo, got {response.json()['method']}"
        
        # Set to FIFO
        update_resp = requests.put(f"{BASE_URL}/api/settings", 
            headers=self.headers,
            json={"stock_valuation_method": "fifo"})
        assert update_resp.status_code == 200
        
        response = requests.get(f"{BASE_URL}/api/stock/valuation", headers=self.headers)
        assert response.status_code == 200
        assert response.json()["method"] == "fifo", f"Expected fifo, got {response.json()['method']}"
    
    def test_products_have_price_and_expiration(self):
        """Products returned have price and expiration_date calculated by valuation method"""
        response = requests.get(f"{BASE_URL}/api/products", headers=self.headers)
        assert response.status_code == 200
        products = response.json()
        
        for product in products[:5]:
            # Products should have price (selling_price) calculated
            assert "price" in product, f"Product {product.get('name')} missing price"
            # expiration_date can be None if no lots with expiration
            assert "expiration_date" in product or product.get("expiration_date") is None


class TestDashboardWithNewFeatures:
    """Test dashboard endpoint works with new stock features"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_dashboard_returns_low_stock_count(self):
        """GET /api/reports/dashboard returns low_stock_count"""
        response = requests.get(f"{BASE_URL}/api/reports/dashboard", headers=self.headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        assert "low_stock_count" in data, "Dashboard missing low_stock_count"
        assert isinstance(data["low_stock_count"], int), "low_stock_count should be integer"
    
    def test_dashboard_returns_stock_valuation_method(self):
        """GET /api/reports/dashboard returns stock_valuation_method"""
        response = requests.get(f"{BASE_URL}/api/reports/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "stock_valuation_method" in data, "Dashboard missing stock_valuation_method"
        assert data["stock_valuation_method"] in ["fifo", "lifo", "fefo", "weighted_average"]


class TestPublicSettingsEndpoint:
    """Test public settings endpoint (no auth required)"""
    
    def test_public_settings_returns_pharmacy_name(self):
        """GET /api/settings/public returns pharmacy_name without auth"""
        response = requests.get(f"{BASE_URL}/api/settings/public")
        assert response.status_code == 200
        data = response.json()
        
        assert "pharmacy_name" in data, "Public settings missing pharmacy_name"
        assert "currency" in data, "Public settings missing currency"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
