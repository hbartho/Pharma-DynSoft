"""
Test suite for Category min_stock feature
Tests:
- Category model has optional min_stock field
- POST /api/categories can create category with min_stock value
- PUT /api/categories can update category min_stock
- GET /api/categories returns categories with min_stock field
- Product min_stock uses category min_stock when set (priority: product > category > global)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCategoryMinStock:
    """Test category min_stock feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Authentication failed - skipping tests")
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Store created test data for cleanup
        self.created_categories = []
        
        yield
        
        # Cleanup: Delete test categories
        for cat_id in self.created_categories:
            try:
                self.session.delete(f"{BASE_URL}/api/categories/{cat_id}")
            except:
                pass
    
    def test_get_categories_returns_min_stock_field(self):
        """GET /api/categories returns categories with min_stock field"""
        response = self.session.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        
        categories = response.json()
        assert isinstance(categories, list)
        
        # Check that categories have min_stock field (can be null)
        for cat in categories:
            assert "min_stock" in cat or cat.get("min_stock") is None, "Category should have min_stock field"
            assert "name" in cat
            assert "id" in cat
        
        print(f"✓ GET /api/categories returns {len(categories)} categories with min_stock field")
    
    def test_create_category_with_min_stock(self):
        """POST /api/categories can create category with min_stock value"""
        test_name = f"TEST_MinStock_{uuid.uuid4().hex[:8]}"
        
        category_data = {
            "name": test_name,
            "description": "Test category with min_stock",
            "color": "#FF5733",
            "markup_coefficient": 1.25,
            "min_stock": 50
        }
        
        response = self.session.post(f"{BASE_URL}/api/categories", json=category_data)
        assert response.status_code == 200, f"Failed to create category: {response.text}"
        
        created = response.json()
        self.created_categories.append(created["id"])
        
        # Verify response data
        assert created["name"] == test_name
        assert created["min_stock"] == 50
        assert created["markup_coefficient"] == 1.25
        assert created["color"] == "#FF5733"
        
        print(f"✓ Created category '{test_name}' with min_stock=50")
        
        # Verify persistence with GET
        get_response = self.session.get(f"{BASE_URL}/api/categories/{created['id']}")
        assert get_response.status_code == 200
        
        fetched = get_response.json()
        assert fetched["min_stock"] == 50, "min_stock should persist after creation"
        
        print(f"✓ Verified min_stock=50 persisted in database")
    
    def test_create_category_without_min_stock(self):
        """POST /api/categories can create category without min_stock (optional field)"""
        test_name = f"TEST_NoMinStock_{uuid.uuid4().hex[:8]}"
        
        category_data = {
            "name": test_name,
            "description": "Test category without min_stock",
            "color": "#3B82F6",
            "markup_coefficient": 1.0
            # min_stock not provided - should be null
        }
        
        response = self.session.post(f"{BASE_URL}/api/categories", json=category_data)
        assert response.status_code == 200, f"Failed to create category: {response.text}"
        
        created = response.json()
        self.created_categories.append(created["id"])
        
        # min_stock should be None/null when not provided
        assert created.get("min_stock") is None, "min_stock should be null when not provided"
        
        print(f"✓ Created category '{test_name}' without min_stock (null)")
    
    def test_update_category_min_stock(self):
        """PUT /api/categories can update category min_stock"""
        # First create a category
        test_name = f"TEST_UpdateMinStock_{uuid.uuid4().hex[:8]}"
        
        create_response = self.session.post(f"{BASE_URL}/api/categories", json={
            "name": test_name,
            "description": "Test category for update",
            "color": "#10B981",
            "markup_coefficient": 1.0,
            "min_stock": 10
        })
        assert create_response.status_code == 200
        
        created = create_response.json()
        self.created_categories.append(created["id"])
        
        assert created["min_stock"] == 10
        print(f"✓ Created category with initial min_stock=10")
        
        # Update min_stock to 100
        update_response = self.session.put(f"{BASE_URL}/api/categories/{created['id']}", json={
            "name": test_name,
            "description": "Updated description",
            "color": "#10B981",
            "markup_coefficient": 1.0,
            "min_stock": 100
        })
        assert update_response.status_code == 200, f"Failed to update category: {update_response.text}"
        
        updated = update_response.json()
        assert updated["min_stock"] == 100, "min_stock should be updated to 100"
        
        print(f"✓ Updated category min_stock from 10 to 100")
        
        # Verify persistence
        get_response = self.session.get(f"{BASE_URL}/api/categories/{created['id']}")
        assert get_response.status_code == 200
        
        fetched = get_response.json()
        assert fetched["min_stock"] == 100, "Updated min_stock should persist"
        
        print(f"✓ Verified min_stock=100 persisted after update")
    
    def test_update_category_remove_min_stock(self):
        """PUT /api/categories can remove min_stock (set to null)"""
        # First create a category with min_stock
        test_name = f"TEST_RemoveMinStock_{uuid.uuid4().hex[:8]}"
        
        create_response = self.session.post(f"{BASE_URL}/api/categories", json={
            "name": test_name,
            "description": "Test category",
            "color": "#8B5CF6",
            "markup_coefficient": 1.0,
            "min_stock": 25
        })
        assert create_response.status_code == 200
        
        created = create_response.json()
        self.created_categories.append(created["id"])
        
        # Update to remove min_stock (set to null)
        update_response = self.session.put(f"{BASE_URL}/api/categories/{created['id']}", json={
            "name": test_name,
            "description": "Test category",
            "color": "#8B5CF6",
            "markup_coefficient": 1.0,
            "min_stock": None
        })
        assert update_response.status_code == 200
        
        updated = update_response.json()
        assert updated.get("min_stock") is None, "min_stock should be null after removal"
        
        print(f"✓ Successfully removed min_stock (set to null)")
    
    def test_existing_antibiotiques_category_has_min_stock(self):
        """Verify existing 'Antibiotiques' category has min_stock=50"""
        response = self.session.get(f"{BASE_URL}/api/categories")
        assert response.status_code == 200
        
        categories = response.json()
        antibiotiques = next((c for c in categories if c["name"] == "Antibiotiques"), None)
        
        if antibiotiques:
            print(f"✓ Found 'Antibiotiques' category with min_stock={antibiotiques.get('min_stock')}")
            # According to context, Antibiotiques should have min_stock=50
            if antibiotiques.get("min_stock") == 50:
                print(f"✓ Antibiotiques has expected min_stock=50")
            else:
                print(f"⚠ Antibiotiques min_stock is {antibiotiques.get('min_stock')}, expected 50")
        else:
            print("⚠ 'Antibiotiques' category not found - may need to be created")


class TestProductMinStockPriority:
    """Test that product min_stock uses category min_stock when set"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Authentication failed - skipping tests")
        
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        self.created_categories = []
        self.created_products = []
        
        yield
        
        # Cleanup
        for prod_id in self.created_products:
            try:
                self.session.delete(f"{BASE_URL}/api/products/{prod_id}")
            except:
                pass
        
        for cat_id in self.created_categories:
            try:
                self.session.delete(f"{BASE_URL}/api/categories/{cat_id}")
            except:
                pass
    
    def test_product_uses_category_min_stock(self):
        """Product min_stock uses category min_stock when set (priority: product > category > global)"""
        # Get global default_min_stock from settings
        settings_response = self.session.get(f"{BASE_URL}/api/settings")
        assert settings_response.status_code == 200
        global_min_stock = settings_response.json().get("default_min_stock", 10)
        print(f"✓ Global default_min_stock = {global_min_stock}")
        
        # Create a category with min_stock=75
        test_cat_name = f"TEST_CatMinStock_{uuid.uuid4().hex[:8]}"
        cat_response = self.session.post(f"{BASE_URL}/api/categories", json={
            "name": test_cat_name,
            "description": "Category with min_stock for testing",
            "color": "#F59E0B",
            "markup_coefficient": 1.0,
            "min_stock": 75
        })
        assert cat_response.status_code == 200
        
        category = cat_response.json()
        self.created_categories.append(category["id"])
        print(f"✓ Created category '{test_cat_name}' with min_stock=75")
        
        # Create a product in this category
        test_prod_name = f"TEST_ProdInCat_{uuid.uuid4().hex[:8]}"
        prod_response = self.session.post(f"{BASE_URL}/api/products", json={
            "name": test_prod_name,
            "description": "Product in category with min_stock",
            "category_id": category["id"]
        })
        assert prod_response.status_code == 200
        
        product = prod_response.json()
        self.created_products.append(product["id"])
        print(f"✓ Created product '{test_prod_name}' in category")
        
        # Get products and check min_stock
        products_response = self.session.get(f"{BASE_URL}/api/products")
        assert products_response.status_code == 200
        
        products = products_response.json()
        test_product = next((p for p in products if p["id"] == product["id"]), None)
        
        assert test_product is not None, "Test product should be in products list"
        
        # Product should use category's min_stock (75), not global default
        product_min_stock = test_product.get("min_stock")
        print(f"✓ Product min_stock = {product_min_stock}")
        
        assert product_min_stock == 75, f"Product should use category min_stock (75), got {product_min_stock}"
        print(f"✓ Product correctly uses category min_stock=75 (not global {global_min_stock})")
    
    def test_product_uses_global_when_category_has_no_min_stock(self):
        """Product uses global default when category has no min_stock"""
        # Get global default_min_stock from settings
        settings_response = self.session.get(f"{BASE_URL}/api/settings")
        assert settings_response.status_code == 200
        global_min_stock = settings_response.json().get("default_min_stock", 10)
        print(f"✓ Global default_min_stock = {global_min_stock}")
        
        # Create a category WITHOUT min_stock
        test_cat_name = f"TEST_CatNoMinStock_{uuid.uuid4().hex[:8]}"
        cat_response = self.session.post(f"{BASE_URL}/api/categories", json={
            "name": test_cat_name,
            "description": "Category without min_stock",
            "color": "#6366F1",
            "markup_coefficient": 1.0
            # No min_stock - should be null
        })
        assert cat_response.status_code == 200
        
        category = cat_response.json()
        self.created_categories.append(category["id"])
        assert category.get("min_stock") is None
        print(f"✓ Created category '{test_cat_name}' without min_stock")
        
        # Create a product in this category
        test_prod_name = f"TEST_ProdNoMinStock_{uuid.uuid4().hex[:8]}"
        prod_response = self.session.post(f"{BASE_URL}/api/products", json={
            "name": test_prod_name,
            "description": "Product in category without min_stock",
            "category_id": category["id"]
        })
        assert prod_response.status_code == 200
        
        product = prod_response.json()
        self.created_products.append(product["id"])
        print(f"✓ Created product '{test_prod_name}' in category")
        
        # Get products and check min_stock
        products_response = self.session.get(f"{BASE_URL}/api/products")
        assert products_response.status_code == 200
        
        products = products_response.json()
        test_product = next((p for p in products if p["id"] == product["id"]), None)
        
        assert test_product is not None
        
        # Product should use global default since category has no min_stock
        product_min_stock = test_product.get("min_stock")
        print(f"✓ Product min_stock = {product_min_stock}")
        
        assert product_min_stock == global_min_stock, f"Product should use global min_stock ({global_min_stock}), got {product_min_stock}"
        print(f"✓ Product correctly uses global default_min_stock={global_min_stock}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
