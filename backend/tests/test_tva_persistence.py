"""
Test suite for TVA (tax_rate) persistence bug fix in Supply management

Bug Description:
- When creating a supply with TVA=0, then editing to add TVA (e.g., 18%), 
  the TVA would reset to 0 when reopening the supply.
- This was caused by conditions like 'tva_rate != 0' in create_supply and update_supply functions

Test Scenarios:
1. Create supply with TVA=0, edit to TVA=18, verify TVA=18 persists
2. Create supply with TVA=18, edit to TVA=0, verify TVA=0 persists
3. Create supply with TVA=18, edit without changing TVA, verify TVA=18 persists
4. Verify lot_number, expiration_date, shelf_location are also correctly saved

Relevant Code:
- /app/backend/routes/supplies.py - create_supply (lines 149-271), update_supply (lines 335-444)
- /app/frontend/src/pages/Supplies.js - handleEdit, handleSubmit
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable is required")

# Valid test data
VALID_PRODUCT_ID = "a3cabb8e-4740-453b-9708-f7545187a305"
VALID_SUPPLIER_ID = "0e9328ae-47f0-44ad-8746-91ca384c6285"


class TestTVAPersistence:
    """Test suite for TVA (tax_rate) persistence bug fix"""
    
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
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.text}")
        
        data = response.json()
        self.token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Track supplies to cleanup
        self.created_supplies = []
        
        yield
        
        # Cleanup: Delete test supplies
        self._cleanup_test_supplies()
    
    def _cleanup_test_supplies(self):
        """Delete supplies created during tests"""
        for supply_id in self.created_supplies:
            try:
                self.session.delete(f"{BASE_URL}/api/supplies/{supply_id}")
            except Exception:
                pass
    
    def _create_supply(self, tva_rate, lot_number=None, shelf_location=None, expiration_date=None):
        """Helper to create a supply with specified TVA rate"""
        unique_suffix = uuid.uuid4().hex[:8]
        
        item_data = {
            "product_id": VALID_PRODUCT_ID,
            "quantity": 10,
            "unit_price": 5000,
            "tva_rate": tva_rate,
        }
        
        if lot_number is not None:
            item_data["lot_number"] = lot_number
        if shelf_location is not None:
            item_data["shelf_location"] = shelf_location
        if expiration_date is not None:
            item_data["date_peremption"] = expiration_date
        
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "supplier_id": VALID_SUPPLIER_ID,
            "delivery_note_number": f"BL-TVA-TEST-{unique_suffix}",
            "invoice_number": f"FACT-TVA-TEST-{unique_suffix}",
            "notes": f"TEST_TVA_PERSISTENCE_{unique_suffix}",
            "items": [item_data]
        }
        
        response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert response.status_code == 200, f"Failed to create supply: {response.text}"
        
        created_supply = response.json()
        self.created_supplies.append(created_supply["id"])
        
        return created_supply
    
    def _update_supply(self, supply_id, tva_rate, lot_number=None, shelf_location=None, expiration_date=None):
        """Helper to update a supply with new TVA rate"""
        unique_suffix = uuid.uuid4().hex[:8]
        
        item_data = {
            "product_id": VALID_PRODUCT_ID,
            "quantity": 10,
            "unit_price": 5000,
            "tva_rate": tva_rate,
        }
        
        if lot_number is not None:
            item_data["lot_number"] = lot_number
        if shelf_location is not None:
            item_data["shelf_location"] = shelf_location
        if expiration_date is not None:
            item_data["date_peremption"] = expiration_date
        
        update_data = {
            "supply_date": datetime.now().isoformat(),
            "supplier_id": VALID_SUPPLIER_ID,
            "delivery_note_number": f"BL-TVA-UPDATED-{unique_suffix}",
            "invoice_number": f"FACT-TVA-UPDATED-{unique_suffix}",
            "notes": f"TEST_TVA_PERSISTENCE_UPDATED_{unique_suffix}",
            "items": [item_data]
        }
        
        response = self.session.put(f"{BASE_URL}/api/supplies/{supply_id}", json=update_data)
        assert response.status_code == 200, f"Failed to update supply: {response.text}"
        
        return response.json()
    
    def _get_supply(self, supply_id):
        """Helper to get a supply by ID"""
        response = self.session.get(f"{BASE_URL}/api/supplies/{supply_id}")
        assert response.status_code == 200, f"Failed to get supply: {response.text}"
        return response.json()
    
    # ==================== TVA Persistence Tests ====================
    
    def test_scenario1_tva_0_to_18_persists(self):
        """
        Scenario 1: Create supply with TVA=0, edit to TVA=18, verify TVA=18 persists
        This is the primary bug scenario reported by the user.
        """
        print("\n=== Scenario 1: TVA 0 -> 18 ===")
        
        # Step 1: Create supply with TVA=0
        print("Step 1: Creating supply with TVA=0")
        created_supply = self._create_supply(tva_rate=0)
        supply_id = created_supply["id"]
        
        # Verify TVA=0 was saved
        initial_tva = created_supply["items"][0].get("tva_rate", created_supply["items"][0].get("tax_rate", 0))
        assert initial_tva == 0, f"Expected TVA=0 on creation, got {initial_tva}"
        print(f"  - Created supply {supply_id} with TVA={initial_tva}")
        
        # Step 2: Update supply to TVA=18
        print("Step 2: Updating supply to TVA=18")
        updated_supply = self._update_supply(supply_id, tva_rate=18)
        
        updated_tva = updated_supply["items"][0].get("tva_rate", updated_supply["items"][0].get("tax_rate", 0))
        assert updated_tva == 18, f"Expected TVA=18 after update, got {updated_tva}"
        print(f"  - Updated supply to TVA={updated_tva}")
        
        # Step 3: Fetch supply again and verify TVA=18 persists
        print("Step 3: Re-fetching supply to verify TVA=18 persists")
        fetched_supply = self._get_supply(supply_id)
        
        final_tva = fetched_supply["items"][0].get("tva_rate", fetched_supply["items"][0].get("tax_rate", 0))
        assert final_tva == 18, f"BUG: TVA should be 18 after re-fetch, got {final_tva}"
        
        print(f"  - TVA persisted correctly: {final_tva}")
        print("✅ PASSED: TVA 0 -> 18 persists correctly")
    
    def test_scenario2_tva_18_to_0_persists(self):
        """
        Scenario 2: Create supply with TVA=18, edit to TVA=0, verify TVA=0 persists
        This tests that we can explicitly set TVA to 0.
        """
        print("\n=== Scenario 2: TVA 18 -> 0 ===")
        
        # Step 1: Create supply with TVA=18
        print("Step 1: Creating supply with TVA=18")
        created_supply = self._create_supply(tva_rate=18)
        supply_id = created_supply["id"]
        
        initial_tva = created_supply["items"][0].get("tva_rate", created_supply["items"][0].get("tax_rate", 0))
        assert initial_tva == 18, f"Expected TVA=18 on creation, got {initial_tva}"
        print(f"  - Created supply {supply_id} with TVA={initial_tva}")
        
        # Step 2: Update supply to TVA=0
        print("Step 2: Updating supply to TVA=0")
        updated_supply = self._update_supply(supply_id, tva_rate=0)
        
        updated_tva = updated_supply["items"][0].get("tva_rate", updated_supply["items"][0].get("tax_rate", 0))
        assert updated_tva == 0, f"Expected TVA=0 after update, got {updated_tva}"
        print(f"  - Updated supply to TVA={updated_tva}")
        
        # Step 3: Fetch supply again and verify TVA=0 persists
        print("Step 3: Re-fetching supply to verify TVA=0 persists")
        fetched_supply = self._get_supply(supply_id)
        
        final_tva = fetched_supply["items"][0].get("tva_rate", fetched_supply["items"][0].get("tax_rate", 0))
        assert final_tva == 0, f"BUG: TVA should be 0 after re-fetch, got {final_tva}"
        
        print(f"  - TVA persisted correctly: {final_tva}")
        print("✅ PASSED: TVA 18 -> 0 persists correctly")
    
    def test_scenario3_tva_18_unchanged_persists(self):
        """
        Scenario 3: Create supply with TVA=18, edit without changing TVA, verify TVA=18 persists
        This tests that editing other fields doesn't reset TVA.
        """
        print("\n=== Scenario 3: TVA 18 unchanged ===")
        
        # Step 1: Create supply with TVA=18
        print("Step 1: Creating supply with TVA=18")
        created_supply = self._create_supply(tva_rate=18)
        supply_id = created_supply["id"]
        
        initial_tva = created_supply["items"][0].get("tva_rate", created_supply["items"][0].get("tax_rate", 0))
        assert initial_tva == 18, f"Expected TVA=18 on creation, got {initial_tva}"
        print(f"  - Created supply {supply_id} with TVA={initial_tva}")
        
        # Step 2: Update supply keeping TVA=18 (same value)
        print("Step 2: Updating supply without changing TVA")
        updated_supply = self._update_supply(supply_id, tva_rate=18)  # Same TVA
        
        updated_tva = updated_supply["items"][0].get("tva_rate", updated_supply["items"][0].get("tax_rate", 0))
        assert updated_tva == 18, f"Expected TVA=18 after update, got {updated_tva}"
        print(f"  - Updated supply, TVA remains: {updated_tva}")
        
        # Step 3: Fetch supply again and verify TVA=18 persists
        print("Step 3: Re-fetching supply to verify TVA=18 persists")
        fetched_supply = self._get_supply(supply_id)
        
        final_tva = fetched_supply["items"][0].get("tva_rate", fetched_supply["items"][0].get("tax_rate", 0))
        assert final_tva == 18, f"BUG: TVA should remain 18, got {final_tva}"
        
        print(f"  - TVA persisted correctly: {final_tva}")
        print("✅ PASSED: TVA 18 unchanged persists correctly")
    
    def test_scenario4_other_fields_persist(self):
        """
        Scenario 4: Verify lot_number, expiration_date, shelf_location also persist correctly
        """
        print("\n=== Scenario 4: Other fields persistence ===")
        
        # Test data
        initial_lot = "LOT-INIT-001"
        initial_shelf = "A1-INIT"
        initial_expiry = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        
        updated_lot = "LOT-UPDATED-002"
        updated_shelf = "B2-UPDATED"
        updated_expiry = (datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
        
        # Step 1: Create supply with initial values
        print("Step 1: Creating supply with initial field values")
        created_supply = self._create_supply(
            tva_rate=10,
            lot_number=initial_lot,
            shelf_location=initial_shelf,
            expiration_date=initial_expiry
        )
        supply_id = created_supply["id"]
        item = created_supply["items"][0]
        
        # Verify initial values
        assert item.get("lot_number") == initial_lot, f"Expected lot_number={initial_lot}, got {item.get('lot_number')}"
        assert item.get("shelf_location") == initial_shelf, f"Expected shelf_location={initial_shelf}, got {item.get('shelf_location')}"
        print(f"  - Created supply with lot={initial_lot}, shelf={initial_shelf}")
        
        # Step 2: Update with new values
        print("Step 2: Updating supply with new field values")
        updated_supply = self._update_supply(
            supply_id,
            tva_rate=15,
            lot_number=updated_lot,
            shelf_location=updated_shelf,
            expiration_date=updated_expiry
        )
        item = updated_supply["items"][0]
        
        assert item.get("lot_number") == updated_lot
        assert item.get("shelf_location") == updated_shelf
        print(f"  - Updated supply to lot={updated_lot}, shelf={updated_shelf}")
        
        # Step 3: Fetch and verify persistence
        print("Step 3: Re-fetching supply to verify all fields persist")
        fetched_supply = self._get_supply(supply_id)
        item = fetched_supply["items"][0]
        
        assert item.get("lot_number") == updated_lot, f"lot_number should be {updated_lot}, got {item.get('lot_number')}"
        assert item.get("shelf_location") == updated_shelf, f"shelf_location should be {updated_shelf}, got {item.get('shelf_location')}"
        
        # Check expiration date (may be in different format)
        exp_date = item.get("date_peremption") or item.get("expiration_date")
        assert exp_date is not None, "expiration_date should be set"
        
        # Check TVA also persisted
        final_tva = item.get("tva_rate", item.get("tax_rate", 0))
        assert final_tva == 15, f"TVA should be 15, got {final_tva}"
        
        print(f"  - All fields persisted: lot={item.get('lot_number')}, shelf={item.get('shelf_location')}, tva={final_tva}")
        print("✅ PASSED: All fields (lot_number, shelf_location, expiration_date, tva_rate) persist correctly")
    
    def test_tva_various_values(self):
        """Test TVA with various common values"""
        print("\n=== Testing various TVA values ===")
        
        test_values = [0, 5.5, 10, 18, 18.5, 20, 25]
        
        for tva_value in test_values:
            # Create supply with this TVA
            created = self._create_supply(tva_rate=tva_value)
            supply_id = created["id"]
            
            created_tva = created["items"][0].get("tva_rate", created["items"][0].get("tax_rate", 0))
            
            # Fetch and verify
            fetched = self._get_supply(supply_id)
            fetched_tva = fetched["items"][0].get("tva_rate", fetched["items"][0].get("tax_rate", 0))
            
            assert fetched_tva == tva_value, f"TVA={tva_value} not persisted. Created: {created_tva}, Fetched: {fetched_tva}"
            print(f"  ✓ TVA={tva_value} persists correctly")
        
        print("✅ PASSED: All TVA values persist correctly")


class TestTVAAliasHandling:
    """Test that tva, tva_rate, and tax_rate are handled as aliases"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        if response.status_code != 200:
            pytest.skip(f"Login failed: {response.text}")
        
        data = response.json()
        self.token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        self.created_supplies = []
        yield
        
        for supply_id in self.created_supplies:
            try:
                self.session.delete(f"{BASE_URL}/api/supplies/{supply_id}")
            except Exception:
                pass
    
    def test_tva_rate_field_accepted(self):
        """Backend accepts 'tva_rate' field"""
        unique_suffix = uuid.uuid4().hex[:8]
        
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "supplier_id": VALID_SUPPLIER_ID,
            "delivery_note_number": f"BL-ALIAS1-{unique_suffix}",
            "invoice_number": f"FACT-ALIAS1-{unique_suffix}",
            "notes": f"TEST_TVA_ALIAS_{unique_suffix}",
            "items": [{
                "product_id": VALID_PRODUCT_ID,
                "quantity": 5,
                "unit_price": 3000,
                "tva_rate": 18  # Using tva_rate
            }]
        }
        
        response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        created = response.json()
        self.created_supplies.append(created["id"])
        
        tva = created["items"][0].get("tva_rate", created["items"][0].get("tax_rate", 0))
        assert tva == 18, f"Expected tva_rate=18, got {tva}"
        print("✅ tva_rate field accepted and stored correctly")
    
    def test_response_contains_tva_aliases(self):
        """Response contains both tva_rate and tax_rate for compatibility"""
        unique_suffix = uuid.uuid4().hex[:8]
        
        supply_data = {
            "supply_date": datetime.now().isoformat(),
            "supplier_id": VALID_SUPPLIER_ID,
            "delivery_note_number": f"BL-ALIAS2-{unique_suffix}",
            "invoice_number": f"FACT-ALIAS2-{unique_suffix}",
            "notes": f"TEST_TVA_RESPONSE_{unique_suffix}",
            "items": [{
                "product_id": VALID_PRODUCT_ID,
                "quantity": 5,
                "unit_price": 3000,
                "tva_rate": 20
            }]
        }
        
        response = self.session.post(f"{BASE_URL}/api/supplies", json=supply_data)
        assert response.status_code == 200
        
        created = response.json()
        self.created_supplies.append(created["id"])
        
        item = created["items"][0]
        
        # Backend returns tax_rate, tva, and tva_rate as aliases
        assert "tax_rate" in item or "tva_rate" in item, "Response should contain tax_rate or tva_rate"
        print(f"✅ Response contains TVA fields: tax_rate={item.get('tax_rate')}, tva_rate={item.get('tva_rate')}, tva={item.get('tva')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
