"""
Test suite for Product Model Refactoring - DynSoft Pharma
Tests the new architecture where:
- Product model only stores basic info (name, barcode, category, unit, description)
- Stock is calculated from stock_lots table (created during supply validation)
- Prices come from price_history table
- min_stock from stock_config table
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pharmacy-mgmt-portal.preview.emergentagent.com').rstrip('/')


class TestProductRefactoring:
    """Test suite for Product model restructuring"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login as admin"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        token = response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.admin_token = token
        
        # Store test product IDs for cleanup
        self.test_product_ids = []
        self.test_supply_ids = []
        
        yield
        
        # Cleanup test data
        for product_id in self.test_product_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/products/{product_id}")
            except:
                pass
        
        for supply_id in self.test_supply_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/supplies/{supply_id}")
            except:
                pass
    
    # ==================== BACKEND TESTS ====================
    
    def test_get_products_returns_enriched_data(self):
        """GET /api/products returns products with calculated stock, price from stock_lots and price_history"""
        response = self.session.get(f"{BASE_URL}/api/products")
        assert response.status_code == 200, f"Failed to get products: {response.text}"
        
        products = response.json()
        assert isinstance(products, list), "Products should be a list"
        
        if len(products) > 0:
            product = products[0]
            # Verify enriched fields are present
            assert "stock" in product, "Product should have 'stock' field (calculated)"
            assert "price" in product, "Product should have 'price' field (from price_history)"
            assert "purchase_price" in product, "Product should have 'purchase_price' field"
            assert "min_stock" in product, "Product should have 'min_stock' field"
            assert "lots_count" in product, "Product should have 'lots_count' field"
            assert "expired_lots_count" in product, "Product should have 'expired_lots_count' field"
            
            # Verify basic fields
            assert "id" in product
            assert "name" in product
            assert "tenant_id" in product
            
            print(f"✓ Product '{product['name']}' has stock={product['stock']}, price={product['price']}, lots_count={product['lots_count']}")
    
    def test_create_product_without_price_stock(self):
        """POST /api/products creates product without price/stock fields (only basic info)"""
        unique_id = str(uuid.uuid4())[:8]
        product_data = {
            "name": f"TEST_Product_NoPrice_{unique_id}",
            "barcode": f"TEST{unique_id}",
            "description": "Test product created without price/stock",
            "category_id": None,
            "unit_id": None
        }
        
        response = self.session.post(f"{BASE_URL}/api/products", json=product_data)
        assert response.status_code == 200, f"Failed to create product: {response.text}"
        
        created = response.json()
        self.test_product_ids.append(created["id"])
        
        # Verify basic fields are set
        assert created["name"] == product_data["name"]
        assert created["barcode"] == product_data["barcode"]
        assert created["description"] == product_data["description"]
        
        # Verify calculated fields default to 0
        assert created["stock"] == 0, "New product should have stock=0"
        assert created["price"] == 0, "New product should have price=0"
        assert created["purchase_price"] == 0, "New product should have purchase_price=0"
        assert created["min_stock"] == 10, "New product should have default min_stock=10"
        assert created["lots_count"] == 0, "New product should have lots_count=0"
        
        print(f"✓ Created product '{created['name']}' with stock=0, price=0 (as expected)")
    
    def test_update_product_basic_info_only(self):
        """PUT /api/products updates product basic info without price/stock"""
        # First create a product
        unique_id = str(uuid.uuid4())[:8]
        create_response = self.session.post(f"{BASE_URL}/api/products", json={
            "name": f"TEST_Product_Update_{unique_id}",
            "barcode": f"TESTUPD{unique_id}",
            "description": "Original description"
        })
        assert create_response.status_code == 200
        product = create_response.json()
        product_id = product["id"]
        self.test_product_ids.append(product_id)
        
        # Update only basic info
        update_data = {
            "name": f"TEST_Product_Updated_{unique_id}",
            "description": "Updated description",
            "internal_reference": "REF-001"
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/products/{product_id}", json=update_data)
        assert update_response.status_code == 200, f"Failed to update product: {update_response.text}"
        
        updated = update_response.json()
        assert updated["name"] == update_data["name"]
        assert updated["description"] == update_data["description"]
        assert updated["internal_reference"] == update_data["internal_reference"]
        
        # Stock and price should still be 0 (not affected by update)
        assert updated["stock"] == 0
        assert updated["price"] == 0
        
        print(f"✓ Updated product basic info, stock/price unchanged")
    
    def test_get_product_lots_endpoint(self):
        """GET /api/products/{id}/lots returns stock lots for a product"""
        # Get an existing product
        products_response = self.session.get(f"{BASE_URL}/api/products")
        assert products_response.status_code == 200
        products = products_response.json()
        
        if len(products) > 0:
            product_id = products[0]["id"]
            
            # Get lots for this product
            lots_response = self.session.get(f"{BASE_URL}/api/products/{product_id}/lots")
            assert lots_response.status_code == 200, f"Failed to get lots: {lots_response.text}"
            
            lots_data = lots_response.json()
            assert "product_id" in lots_data
            assert "product_name" in lots_data
            assert "lots" in lots_data
            assert "total_lots" in lots_data
            assert "active_lots" in lots_data
            assert isinstance(lots_data["lots"], list)
            
            print(f"✓ Product '{lots_data['product_name']}' has {lots_data['total_lots']} total lots, {lots_data['active_lots']} active")
    
    def test_supply_validation_creates_stock_lots(self):
        """Validate supply creates stock_lots entries when validated"""
        unique_id = str(uuid.uuid4())[:8]
        
        # 1. Create a test product
        product_response = self.session.post(f"{BASE_URL}/api/products", json={
            "name": f"TEST_Product_Supply_{unique_id}",
            "barcode": f"TESTSUP{unique_id}"
        })
        assert product_response.status_code == 200
        product = product_response.json()
        product_id = product["id"]
        self.test_product_ids.append(product_id)
        
        # Verify initial stock is 0
        assert product["stock"] == 0, "Initial stock should be 0"
        
        # 2. Create a supply with this product
        expiration_date = (datetime.now() + timedelta(days=365)).isoformat()
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "supplier_id": None,
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 100,
                    "unit_price": 5000,
                    "date_peremption": expiration_date
                }
            ],
            "notes": "Test supply for refactoring"
        }
        
        supply_response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert supply_response.status_code == 200, f"Failed to create supply: {supply_response.text}"
        supply = supply_response.json()
        supply_id = supply["id"]
        self.test_supply_ids.append(supply_id)
        
        # Verify supply is not validated yet
        assert supply["is_validated"] == False
        
        # 3. Validate the supply
        validate_response = self.session.post(f"{BASE_URL}/api/supplies/{supply_id}/validate")
        assert validate_response.status_code == 200, f"Failed to validate supply: {validate_response.text}"
        
        validated_supply = validate_response.json()
        assert validated_supply["is_validated"] == True
        
        # 4. Check that stock_lots were created
        lots_response = self.session.get(f"{BASE_URL}/api/products/{product_id}/lots")
        assert lots_response.status_code == 200
        lots_data = lots_response.json()
        
        assert lots_data["total_lots"] >= 1, "Should have at least 1 lot after supply validation"
        assert lots_data["active_lots"] >= 1, "Should have at least 1 active lot"
        
        # Find the lot created by our supply
        our_lot = None
        for lot in lots_data["lots"]:
            if lot.get("supply_id") == supply_id:
                our_lot = lot
                break
        
        assert our_lot is not None, "Should find lot created by our supply"
        assert our_lot["initial_quantity"] == 100
        assert our_lot["current_quantity"] == 100
        assert our_lot["purchase_price"] == 5000
        
        # 5. Verify product stock is now updated
        product_response = self.session.get(f"{BASE_URL}/api/products/{product_id}")
        assert product_response.status_code == 200
        updated_product = product_response.json()
        
        assert updated_product["stock"] >= 100, f"Stock should be at least 100, got {updated_product['stock']}"
        assert updated_product["lots_count"] >= 1
        
        print(f"✓ Supply validation created stock lot: qty={our_lot['current_quantity']}, price={our_lot['purchase_price']}")
        print(f"✓ Product stock updated to {updated_product['stock']}")
    
    def test_product_price_from_price_history(self):
        """Verify product price comes from price_history table after supply validation"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create product
        product_response = self.session.post(f"{BASE_URL}/api/products", json={
            "name": f"TEST_Product_Price_{unique_id}",
            "barcode": f"TESTPRC{unique_id}"
        })
        assert product_response.status_code == 200
        product = product_response.json()
        product_id = product["id"]
        self.test_product_ids.append(product_id)
        
        # Initial price should be 0
        assert product["price"] == 0
        assert product["purchase_price"] == 0
        
        # Create and validate supply with specific prices
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 50,
                    "unit_price": 7500  # Purchase price
                }
            ]
        }
        
        supply_response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert supply_response.status_code == 200
        supply_id = supply_response.json()["id"]
        self.test_supply_ids.append(supply_id)
        
        # Validate supply
        validate_response = self.session.post(f"{BASE_URL}/api/supplies/{supply_id}/validate")
        assert validate_response.status_code == 200
        
        # Check product now has price from price_history
        product_response = self.session.get(f"{BASE_URL}/api/products/{product_id}")
        assert product_response.status_code == 200
        updated_product = product_response.json()
        
        assert updated_product["purchase_price"] == 7500, f"Purchase price should be 7500, got {updated_product['purchase_price']}"
        
        print(f"✓ Product price updated from price_history: purchase_price={updated_product['purchase_price']}")
    
    def test_product_min_stock_default(self):
        """Verify new products have default min_stock of 10"""
        unique_id = str(uuid.uuid4())[:8]
        
        product_response = self.session.post(f"{BASE_URL}/api/products", json={
            "name": f"TEST_Product_MinStock_{unique_id}"
        })
        assert product_response.status_code == 200
        product = product_response.json()
        self.test_product_ids.append(product["id"])
        
        assert product["min_stock"] == 10, f"Default min_stock should be 10, got {product['min_stock']}"
        print(f"✓ Product has default min_stock=10")
    
    def test_update_product_min_stock(self):
        """Test updating product min_stock via dedicated endpoint"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create product
        product_response = self.session.post(f"{BASE_URL}/api/products", json={
            "name": f"TEST_Product_MinStockUpdate_{unique_id}"
        })
        assert product_response.status_code == 200
        product = product_response.json()
        product_id = product["id"]
        self.test_product_ids.append(product_id)
        
        # Update min_stock
        update_response = self.session.patch(
            f"{BASE_URL}/api/products/{product_id}/min-stock",
            params={"min_stock": 25}
        )
        assert update_response.status_code == 200, f"Failed to update min_stock: {update_response.text}"
        
        # Verify min_stock was updated
        product_response = self.session.get(f"{BASE_URL}/api/products/{product_id}")
        assert product_response.status_code == 200
        updated_product = product_response.json()
        
        assert updated_product["min_stock"] == 25, f"min_stock should be 25, got {updated_product['min_stock']}"
        print(f"✓ Product min_stock updated to 25")
    
    def test_product_alerts_endpoint(self):
        """Test /api/products/alerts returns low stock and expiration alerts"""
        response = self.session.get(f"{BASE_URL}/api/products/alerts")
        assert response.status_code == 200, f"Failed to get alerts: {response.text}"
        
        alerts = response.json()
        assert "low_stock" in alerts
        assert "near_expiration" in alerts
        assert "expired" in alerts
        
        assert "count" in alerts["low_stock"]
        assert "products" in alerts["low_stock"]
        assert "count" in alerts["near_expiration"]
        assert "products" in alerts["near_expiration"]
        
        print(f"✓ Alerts: {alerts['low_stock']['count']} low stock, {alerts['near_expiration']['count']} near expiration, {alerts['expired']['count']} expired")


class TestProductFormValidation:
    """Test product form validation - no price/stock fields accepted"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        token = response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        self.test_product_ids = []
        yield
        
        for product_id in self.test_product_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/products/{product_id}")
            except:
                pass
    
    def test_create_product_ignores_price_stock_fields(self):
        """Verify that price/stock fields in request are ignored (model has extra='ignore')"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Try to create product with price/stock fields (should be ignored)
        product_data = {
            "name": f"TEST_Product_IgnoreFields_{unique_id}",
            "barcode": f"TESTIG{unique_id}",
            "price": 99999,  # Should be ignored
            "stock": 500,    # Should be ignored
            "min_stock": 50, # Should be ignored
            "purchase_price": 88888  # Should be ignored
        }
        
        response = self.session.post(f"{BASE_URL}/api/products", json=product_data)
        assert response.status_code == 200, f"Failed to create product: {response.text}"
        
        created = response.json()
        self.test_product_ids.append(created["id"])
        
        # Verify price/stock fields were NOT set from request
        assert created["stock"] == 0, "Stock should be 0 (calculated, not from request)"
        assert created["price"] == 0, "Price should be 0 (from price_history, not request)"
        assert created["purchase_price"] == 0, "Purchase price should be 0"
        assert created["min_stock"] == 10, "min_stock should be default 10"
        
        print(f"✓ Price/stock fields in request were correctly ignored")


class TestPharmacienRole:
    """Test that pharmacien role can also manage products"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as pharmacien
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "pharmacien@pharmaflow.com",
            "password": "pharma123"
        })
        assert response.status_code == 200, f"Pharmacien login failed: {response.text}"
        token = response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        self.test_product_ids = []
        yield
        
        for product_id in self.test_product_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/products/{product_id}")
            except:
                pass
    
    def test_pharmacien_can_create_product(self):
        """Pharmacien can create products"""
        unique_id = str(uuid.uuid4())[:8]
        
        response = self.session.post(f"{BASE_URL}/api/products", json={
            "name": f"TEST_Pharmacien_Product_{unique_id}"
        })
        assert response.status_code == 200, f"Pharmacien should be able to create products: {response.text}"
        
        product = response.json()
        self.test_product_ids.append(product["id"])
        print(f"✓ Pharmacien created product successfully")
    
    def test_pharmacien_can_update_product(self):
        """Pharmacien can update products"""
        unique_id = str(uuid.uuid4())[:8]
        
        # Create
        create_response = self.session.post(f"{BASE_URL}/api/products", json={
            "name": f"TEST_Pharmacien_Update_{unique_id}"
        })
        assert create_response.status_code == 200
        product_id = create_response.json()["id"]
        self.test_product_ids.append(product_id)
        
        # Update
        update_response = self.session.put(f"{BASE_URL}/api/products/{product_id}", json={
            "description": "Updated by pharmacien"
        })
        assert update_response.status_code == 200, f"Pharmacien should be able to update products: {update_response.text}"
        print(f"✓ Pharmacien updated product successfully")
    
    def test_pharmacien_can_view_product_lots(self):
        """Pharmacien can view product lots"""
        # Get any product
        products_response = self.session.get(f"{BASE_URL}/api/products")
        assert products_response.status_code == 200
        products = products_response.json()
        
        if len(products) > 0:
            product_id = products[0]["id"]
            lots_response = self.session.get(f"{BASE_URL}/api/products/{product_id}/lots")
            assert lots_response.status_code == 200, f"Pharmacien should be able to view lots: {lots_response.text}"
            print(f"✓ Pharmacien can view product lots")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
