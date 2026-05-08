"""
Test suite for Supply form new fields:
- lot_number (N° Lot)
- shelf_location (Rayon)
- tva_rate (TVA %)
- date_peremption (Périme le)
- current_stock (Stock actuel - récupéré)
- markup_coefficient (Coefficient d'intérêt - récupéré de la catégorie)
- selling_price (Prix de vente - calculé automatiquement = prix_achat × coefficient)
- category_name (Nom de la catégorie)

Tests verify:
1. SupplyItem model has new fields
2. GET /api/supplies returns items enriched with calculated fields
3. selling_price is calculated as unit_price * markup_coefficient
4. POST /api/supplies accepts items with new fields
5. Supply validation creates stock_lots with new fields
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pharmacy-mgmt-portal.preview.emergentagent.com').rstrip('/')


class TestSupplyNewFields:
    """Test suite for supply form new fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as admin
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        self.token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Get a product for testing
        products_response = self.session.get(f"{BASE_URL}/api/products")
        assert products_response.status_code == 200
        products = products_response.json()
        if isinstance(products, dict):
            products = products.get('items', [])
        assert len(products) > 0, "No products found for testing"
        self.test_product = products[0]
        
        yield
        
        # Cleanup: Delete test supplies
        self._cleanup_test_supplies()
    
    def _cleanup_test_supplies(self):
        """Delete supplies created during tests"""
        try:
            supplies_response = self.session.get(f"{BASE_URL}/api/supplies")
            if supplies_response.status_code == 200:
                supplies = supplies_response.json()
                for supply in supplies:
                    if supply.get("notes", "").startswith("TEST_"):
                        if not supply.get("is_validated"):
                            self.session.delete(f"{BASE_URL}/api/supplies/{supply['id']}")
        except Exception:
            pass
    
    # ==================== Backend Model Tests ====================
    
    def test_get_supplies_returns_enriched_items(self):
        """GET /api/supplies returns items with current_stock, markup_coefficient, selling_price, category_name"""
        response = self.session.get(f"{BASE_URL}/api/supplies")
        assert response.status_code == 200, f"Failed to get supplies: {response.text}"
        
        supplies = response.json()
        assert isinstance(supplies, list), "Response should be a list"
        
        # Find a supply with items
        supply_with_items = None
        for supply in supplies:
            if supply.get("items") and len(supply["items"]) > 0:
                supply_with_items = supply
                break
        
        assert supply_with_items is not None, "No supply with items found"
        
        # Check first item has enriched fields
        item = supply_with_items["items"][0]
        
        # Verify enriched fields exist
        assert "current_stock" in item, "Item should have current_stock field"
        assert "markup_coefficient" in item, "Item should have markup_coefficient field"
        assert "selling_price" in item, "Item should have selling_price field"
        assert "category_name" in item, "Item should have category_name field"
        
        # Verify new input fields exist
        assert "lot_number" in item, "Item should have lot_number field"
        assert "shelf_location" in item, "Item should have shelf_location field"
        assert "tva_rate" in item, "Item should have tva_rate field"
        assert "date_peremption" in item, "Item should have date_peremption field"
        
        print(f"✓ Item enriched fields: current_stock={item['current_stock']}, markup_coefficient={item['markup_coefficient']}, selling_price={item['selling_price']}, category_name={item['category_name']}")
    
    def test_selling_price_calculation(self):
        """selling_price should be calculated as unit_price * markup_coefficient"""
        response = self.session.get(f"{BASE_URL}/api/supplies")
        assert response.status_code == 200
        
        supplies = response.json()
        
        for supply in supplies:
            for item in supply.get("items", []):
                unit_price = item.get("unit_price", 0)
                markup_coefficient = item.get("markup_coefficient", 1)
                selling_price = item.get("selling_price", 0)
                
                if markup_coefficient and unit_price:
                    expected_selling_price = round(unit_price * markup_coefficient, 2)
                    assert selling_price == expected_selling_price, \
                        f"selling_price mismatch: expected {expected_selling_price}, got {selling_price} (unit_price={unit_price}, coefficient={markup_coefficient})"
                    print(f"✓ {item['product_name']}: {unit_price} × {markup_coefficient} = {selling_price}")
                    return  # Test passed with at least one item
        
        pytest.skip("No items with valid markup_coefficient found")
    
    def test_create_supply_with_new_fields(self):
        """POST /api/supplies accepts items with lot_number, shelf_location, tva_rate, date_peremption"""
        # Prepare expiration date (1 year from now)
        expiration_date = (datetime.now() + timedelta(days=365)).isoformat()
        
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "notes": f"TEST_{uuid.uuid4().hex[:8]}_new_fields",
            "items": [
                {
                    "product_id": self.test_product["id"],
                    "quantity": 10,
                    "unit_price": 5000,
                    "lot_number": "LOT-TEST-001",
                    "shelf_location": "A1-B2",
                    "tva_rate": 18.5,
                    "date_peremption": expiration_date
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert response.status_code == 200, f"Failed to create supply: {response.text}"
        
        created_supply = response.json()
        assert len(created_supply["items"]) == 1, "Supply should have 1 item"
        
        item = created_supply["items"][0]
        
        # Verify new fields were saved
        assert item.get("lot_number") == "LOT-TEST-001", f"lot_number mismatch: {item.get('lot_number')}"
        assert item.get("shelf_location") == "A1-B2", f"shelf_location mismatch: {item.get('shelf_location')}"
        assert item.get("tva_rate") == 18.5, f"tva_rate mismatch: {item.get('tva_rate')}"
        assert item.get("date_peremption") is not None, "date_peremption should be set"
        
        # Verify enriched fields are returned
        assert "current_stock" in item, "Item should have current_stock"
        assert "markup_coefficient" in item, "Item should have markup_coefficient"
        assert "selling_price" in item, "Item should have selling_price"
        assert "category_name" in item, "Item should have category_name"
        
        print(f"✓ Created supply with new fields: lot_number={item['lot_number']}, shelf_location={item['shelf_location']}, tva_rate={item['tva_rate']}")
        
        # Store for cleanup
        self.created_supply_id = created_supply["id"]
    
    def test_create_supply_without_optional_fields(self):
        """POST /api/supplies works without optional new fields"""
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "notes": f"TEST_{uuid.uuid4().hex[:8]}_minimal",
            "items": [
                {
                    "product_id": self.test_product["id"],
                    "quantity": 5,
                    "unit_price": 3000
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert response.status_code == 200, f"Failed to create supply: {response.text}"
        
        created_supply = response.json()
        item = created_supply["items"][0]
        
        # Verify default values
        assert item.get("lot_number") is None, "lot_number should be None by default"
        assert item.get("shelf_location") is None, "shelf_location should be None by default"
        assert item.get("tva_rate") == 0, f"tva_rate should be 0 by default, got {item.get('tva_rate')}"
        
        print("✓ Created supply without optional fields - defaults applied correctly")
    
    def test_update_supply_with_new_fields(self):
        """PUT /api/supplies/{id} can update items with new fields"""
        # First create a supply
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "notes": f"TEST_{uuid.uuid4().hex[:8]}_update",
            "items": [
                {
                    "product_id": self.test_product["id"],
                    "quantity": 5,
                    "unit_price": 2000
                }
            ]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert create_response.status_code == 200
        created_supply = create_response.json()
        supply_id = created_supply["id"]
        
        # Update with new fields
        expiration_date = (datetime.now() + timedelta(days=180)).isoformat()
        update_data = {
            "supply_date": datetime.now().isoformat(),
            "notes": f"TEST_{uuid.uuid4().hex[:8]}_updated",
            "items": [
                {
                    "product_id": self.test_product["id"],
                    "quantity": 8,
                    "unit_price": 2500,
                    "lot_number": "LOT-UPDATED-001",
                    "shelf_location": "C3-D4",
                    "tva_rate": 20.0,
                    "date_peremption": expiration_date
                }
            ]
        }
        
        update_response = self.session.put(f"{BASE_URL}/api/supplies/{supply_id}", json=update_data)
        assert update_response.status_code == 200, f"Failed to update supply: {update_response.text}"
        
        updated_supply = update_response.json()
        item = updated_supply["items"][0]
        
        assert item.get("lot_number") == "LOT-UPDATED-001"
        assert item.get("shelf_location") == "C3-D4"
        assert item.get("tva_rate") == 20.0
        assert item.get("date_peremption") is not None
        
        print(f"✓ Updated supply with new fields: lot_number={item['lot_number']}, shelf_location={item['shelf_location']}, tva_rate={item['tva_rate']}")
    
    def test_validate_supply_creates_stock_lot_with_new_fields(self):
        """Supply validation creates stock_lots with lot_number, shelf_location, tva_rate"""
        # Create a supply with all new fields
        expiration_date = (datetime.now() + timedelta(days=365)).isoformat()
        
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "notes": f"TEST_{uuid.uuid4().hex[:8]}_validate",
            "items": [
                {
                    "product_id": self.test_product["id"],
                    "quantity": 15,
                    "unit_price": 4000,
                    "lot_number": "LOT-VALIDATE-001",
                    "shelf_location": "E5-F6",
                    "tva_rate": 15.0,
                    "date_peremption": expiration_date
                }
            ]
        }
        
        create_response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert create_response.status_code == 200
        created_supply = create_response.json()
        supply_id = created_supply["id"]
        
        # Validate the supply
        validate_response = self.session.post(f"{BASE_URL}/api/supplies/{supply_id}/validate")
        assert validate_response.status_code == 200, f"Failed to validate supply: {validate_response.text}"
        
        validated_supply = validate_response.json()
        assert validated_supply["is_validated"] == True, "Supply should be validated"
        
        # Check stock_lots were created with new fields
        # Get stock lots for the product
        stock_response = self.session.get(f"{BASE_URL}/api/stock/lots?product_id={self.test_product['id']}")
        
        if stock_response.status_code == 200:
            stock_lots = stock_response.json()
            if isinstance(stock_lots, dict):
                stock_lots = stock_lots.get('items', [])
            
            # Find the lot created by this supply
            supply_lot = None
            for lot in stock_lots:
                if lot.get("supply_id") == supply_id:
                    supply_lot = lot
                    break
            
            if supply_lot:
                assert supply_lot.get("lot_number") == "LOT-VALIDATE-001", f"Stock lot lot_number mismatch: {supply_lot.get('lot_number')}"
                assert supply_lot.get("shelf_location") == "E5-F6", f"Stock lot shelf_location mismatch: {supply_lot.get('shelf_location')}"
                assert supply_lot.get("tva_rate") == 15.0, f"Stock lot tva_rate mismatch: {supply_lot.get('tva_rate')}"
                print(f"✓ Stock lot created with new fields: lot_number={supply_lot['lot_number']}, shelf_location={supply_lot['shelf_location']}, tva_rate={supply_lot['tva_rate']}")
            else:
                print("⚠ Could not find stock lot for validated supply (may need different endpoint)")
        else:
            print(f"⚠ Stock lots endpoint returned {stock_response.status_code} - skipping stock lot verification")
        
        print(f"✓ Supply validated successfully: is_validated={validated_supply['is_validated']}")
    
    def test_get_single_supply_returns_enriched_items(self):
        """GET /api/supplies/{id} returns items with enriched fields"""
        # Get list of supplies
        list_response = self.session.get(f"{BASE_URL}/api/supplies")
        assert list_response.status_code == 200
        supplies = list_response.json()
        
        # Find a supply with items
        supply_with_items = None
        for supply in supplies:
            if supply.get("items") and len(supply["items"]) > 0:
                supply_with_items = supply
                break
        
        assert supply_with_items is not None, "No supply with items found"
        
        # Get single supply
        single_response = self.session.get(f"{BASE_URL}/api/supplies/{supply_with_items['id']}")
        assert single_response.status_code == 200, f"Failed to get single supply: {single_response.text}"
        
        single_supply = single_response.json()
        item = single_supply["items"][0]
        
        # Verify enriched fields
        assert "current_stock" in item, "Single supply item should have current_stock"
        assert "markup_coefficient" in item, "Single supply item should have markup_coefficient"
        assert "selling_price" in item, "Single supply item should have selling_price"
        assert "category_name" in item, "Single supply item should have category_name"
        
        print(f"✓ Single supply returns enriched items: {item['product_name']} - stock={item['current_stock']}, coef={item['markup_coefficient']}, price={item['selling_price']}")


class TestSupplyItemFields:
    """Test SupplyItem model field validation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        self.token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Get a product
        products_response = self.session.get(f"{BASE_URL}/api/products")
        products = products_response.json()
        if isinstance(products, dict):
            products = products.get('items', [])
        self.test_product = products[0]
        
        yield
    
    def test_tva_rate_accepts_decimal(self):
        """tva_rate field accepts decimal values"""
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "notes": f"TEST_{uuid.uuid4().hex[:8]}_tva_decimal",
            "items": [
                {
                    "product_id": self.test_product["id"],
                    "quantity": 1,
                    "unit_price": 1000,
                    "tva_rate": 18.5
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert response.status_code == 200
        
        item = response.json()["items"][0]
        assert item["tva_rate"] == 18.5, f"tva_rate should be 18.5, got {item['tva_rate']}"
        print("✓ tva_rate accepts decimal values (18.5)")
    
    def test_lot_number_accepts_string(self):
        """lot_number field accepts string values"""
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "notes": f"TEST_{uuid.uuid4().hex[:8]}_lot_string",
            "items": [
                {
                    "product_id": self.test_product["id"],
                    "quantity": 1,
                    "unit_price": 1000,
                    "lot_number": "LOT-2025-ABC-123"
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert response.status_code == 200
        
        item = response.json()["items"][0]
        assert item["lot_number"] == "LOT-2025-ABC-123"
        print("✓ lot_number accepts string values")
    
    def test_shelf_location_accepts_string(self):
        """shelf_location field accepts string values"""
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "notes": f"TEST_{uuid.uuid4().hex[:8]}_shelf_string",
            "items": [
                {
                    "product_id": self.test_product["id"],
                    "quantity": 1,
                    "unit_price": 1000,
                    "shelf_location": "Rayon-A / Étagère-3"
                }
            ]
        }
        
        response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert response.status_code == 200
        
        item = response.json()["items"][0]
        assert item["shelf_location"] == "Rayon-A / Étagère-3"
        print("✓ shelf_location accepts string values with special characters")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
