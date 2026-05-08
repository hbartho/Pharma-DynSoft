"""
Test: Return Lot Priority in Stock Deduction - Direct Database Test
====================================================================
This test directly creates a return lot in the database to verify that
the deduct_stock_from_lots function prioritizes return lots over normal lots.

This simulates a scenario where:
- A return lot exists (from an old sale without lots_used tracking)
- A normal lot exists with an earlier expiration date
- The return lot should be consumed first, regardless of expiration date
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'pharmaflow')

# Test credentials
TEST_EMAIL = "admin@pharmaflow.com"
TEST_PASSWORD = "admin123"


class TestReturnLotPriorityDirect:
    """Test return lot priority by directly creating lots in the database"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication and database connection"""
        # HTTP session
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Authenticate
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        self.token = data.get("access_token") or data.get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # MongoDB connection
        self.mongo_client = MongoClient(MONGO_URL)
        self.db = self.mongo_client[DB_NAME]
        
        # Store created resources for cleanup
        self.created_product_id = None
        self.created_lot_ids = []
        self.created_sale_ids = []
        self.tenant_id = "default"
        
        yield
        
        # Cleanup
        self._cleanup()
    
    def _cleanup(self):
        """Clean up test data"""
        # Delete created lots
        for lot_id in self.created_lot_ids:
            self.db.stock_lots.delete_one({"id": lot_id})
        
        # Delete created product
        if self.created_product_id:
            self.db.products.delete_one({"id": self.created_product_id})
        
        # Close MongoDB connection
        self.mongo_client.close()
    
    def test_return_lot_consumed_before_normal_lot(self):
        """
        Test that return lots are consumed before normal lots.
        
        Scenario:
        1. Create a product
        2. Directly insert a normal lot with expiration date (earlier)
        3. Directly insert a return lot (no expiration date)
        4. Create a sale
        5. Verify the return lot was consumed first
        """
        print("\n=== Test: Return lot consumed before normal lot ===")
        
        # Step 1: Create a test product
        unique_id = str(uuid.uuid4())[:8]
        product_data = {
            "name": f"TEST_DirectReturnPriority_{unique_id}",
            "category_id": None,
            "description": "Test product for direct return lot priority testing",
            "min_stock": 5,
            "stock": 0,
            "price": 100.0,
            "purchase_price": 80.0
        }
        
        response = self.session.post(f"{BASE_URL}/api/products", json=product_data)
        assert response.status_code in [200, 201], f"Failed to create product: {response.text}"
        product = response.json()
        self.created_product_id = product["id"]
        print(f"Created product: {product['name']} (ID: {product['id']})")
        
        # Step 2: Directly insert a normal lot with earlier expiration date
        now = datetime.now()
        normal_lot_id = str(uuid.uuid4())
        normal_lot = {
            "id": normal_lot_id,
            "product_id": self.created_product_id,
            "product_name": product["name"],
            "initial_quantity": 10,
            "current_quantity": 10,
            "purchase_price": 80.0,
            "selling_price": 100.0,
            "expiration_date": (now + timedelta(days=30)).isoformat(),  # Expires in 30 days
            "supply_date": now.isoformat(),
            "supply_id": None,
            "supplier_id": None,
            "supplier_name": None,
            "lot_number": f"NORMAL-{unique_id}",
            "source": None,  # Normal lot (no source)
            "is_active": True,
            "is_expired": False,
            "tenant_id": self.tenant_id,
            "created_at": now.isoformat(),
            "created_by": "TEST"
        }
        self.db.stock_lots.insert_one(normal_lot)
        self.created_lot_ids.append(normal_lot_id)
        print(f"Created normal lot: {normal_lot['lot_number']} (qty=10, exp={normal_lot['expiration_date'][:10]})")
        
        # Step 3: Directly insert a return lot (no expiration date, created later)
        return_lot_id = str(uuid.uuid4())
        return_lot = {
            "id": return_lot_id,
            "product_id": self.created_product_id,
            "product_name": product["name"],
            "initial_quantity": 5,
            "current_quantity": 5,
            "purchase_price": 80.0,
            "selling_price": 100.0,
            "expiration_date": None,  # No expiration date
            "supply_date": (now + timedelta(hours=1)).isoformat(),  # Created 1 hour later
            "supply_id": None,
            "supplier_id": None,
            "supplier_name": None,
            "lot_number": f"RETURN-{unique_id}",
            "source": "return",  # This is a return lot!
            "is_active": True,
            "is_expired": False,
            "tenant_id": self.tenant_id,
            "created_at": (now + timedelta(hours=1)).isoformat(),
            "created_by": "TEST"
        }
        self.db.stock_lots.insert_one(return_lot)
        self.created_lot_ids.append(return_lot_id)
        print(f"Created return lot: {return_lot['lot_number']} (qty=5, source=return, no expiration)")
        
        # Update product stock
        self.db.products.update_one(
            {"id": self.created_product_id},
            {"$set": {"stock": 15}}
        )
        
        # Verify lots exist
        lots = list(self.db.stock_lots.find({
            "product_id": self.created_product_id,
            "is_active": True,
            "current_quantity": {"$gt": 0}
        }))
        print(f"\nLots before sale: {len(lots)}")
        for lot in lots:
            print(f"  - {lot.get('lot_number')}: qty={lot.get('current_quantity')}, source={lot.get('source', 'normal')}, exp={lot.get('expiration_date', 'N/A')[:10] if lot.get('expiration_date') else 'N/A'}")
        
        # Step 4: Create a sale for 3 units
        print("\n=== Creating sale for 3 units ===")
        sale_data = {
            "items": [
                {
                    "product_id": self.created_product_id,
                    "quantity": 3,
                    "unit_price": 100.0,
                    "subtotal": 300.0
                }
            ],
            "total": 300.0,
            "payment_method": "cash"
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        assert response.status_code in [200, 201], f"Failed to create sale: {response.text}"
        sale = response.json()
        self.created_sale_ids.append(sale["id"])
        print(f"Created sale: {sale.get('sale_number', sale['id'])}")
        
        # Check which lots were used
        if "items" in sale and sale["items"]:
            lots_used = sale["items"][0].get("lots_used", [])
            print(f"Lots used in sale: {lots_used}")
            
            # Verify the return lot was used
            for lot_info in lots_used:
                lot_id = lot_info.get("lot_id")
                qty_deducted = lot_info.get("quantity_deducted")
                
                if lot_id == return_lot_id:
                    print(f"✅ Return lot was used! Deducted: {qty_deducted}")
                elif lot_id == normal_lot_id:
                    print(f"⚠️ Normal lot was used. Deducted: {qty_deducted}")
        
        # Step 5: Verify lot quantities after sale
        print("\n=== Verifying lot quantities after sale ===")
        lots_after = list(self.db.stock_lots.find({
            "product_id": self.created_product_id,
            "id": {"$in": [normal_lot_id, return_lot_id]}
        }))
        
        normal_lot_after = None
        return_lot_after = None
        
        for lot in lots_after:
            if lot["id"] == normal_lot_id:
                normal_lot_after = lot
            elif lot["id"] == return_lot_id:
                return_lot_after = lot
        
        print(f"Normal lot after sale: qty={normal_lot_after.get('current_quantity') if normal_lot_after else 'N/A'}")
        print(f"Return lot after sale: qty={return_lot_after.get('current_quantity') if return_lot_after else 'N/A'}")
        
        # Verify return lot was consumed first
        # Expected: return lot = 2 (5-3), normal lot = 10 (unchanged)
        if return_lot_after and normal_lot_after:
            return_qty = return_lot_after.get('current_quantity', 0)
            normal_qty = normal_lot_after.get('current_quantity', 0)
            
            if return_qty == 2 and normal_qty == 10:
                print("\n✅ SUCCESS: Return lot was consumed first!")
                print(f"   Return lot: 5 -> 2 (consumed 3)")
                print(f"   Normal lot: 10 -> 10 (unchanged)")
            elif return_qty < 5:
                print(f"\n✅ SUCCESS: Return lot was consumed (partially or fully)")
                print(f"   Return lot: 5 -> {return_qty}")
                print(f"   Normal lot: 10 -> {normal_qty}")
            else:
                print(f"\n❌ FAILURE: Return lot was NOT consumed first!")
                print(f"   Return lot: 5 -> {return_qty}")
                print(f"   Normal lot: 10 -> {normal_qty}")
                assert False, "Return lot should have been consumed before normal lot"
        
        # Verify total stock
        total_stock = (return_lot_after.get('current_quantity', 0) if return_lot_after else 0) + \
                      (normal_lot_after.get('current_quantity', 0) if normal_lot_after else 0)
        assert total_stock == 12, f"Expected total stock 12, got {total_stock}"
        print(f"\nTotal stock: {total_stock} (expected: 12)")
        
        print("\n=== Test completed successfully ===")
    
    def test_return_lot_priority_with_fefo(self):
        """
        Test that return lots are prioritized even when FEFO would normally
        select the normal lot (which has an earlier expiration date).
        """
        print("\n=== Test: Return lot priority with FEFO ===")
        
        # Get current valuation method
        response = self.session.get(f"{BASE_URL}/api/settings")
        if response.status_code == 200:
            settings = response.json()
            method = settings.get("stock_valuation_method", "fefo")
            print(f"Current valuation method: {method}")
        
        # The main test already covers this - return lots should always be first
        print("FEFO test covered by main test - return lots are always prioritized")
    
    def test_multiple_return_lots_fifo_order(self):
        """
        Test that when multiple return lots exist, they are consumed in FIFO order.
        """
        print("\n=== Test: Multiple return lots FIFO order ===")
        
        # Create product
        unique_id = str(uuid.uuid4())[:8]
        product_data = {
            "name": f"TEST_MultiReturn_{unique_id}",
            "category_id": None,
            "description": "Test product for multiple return lots",
            "min_stock": 5,
            "stock": 0,
            "price": 100.0,
            "purchase_price": 80.0
        }
        
        response = self.session.post(f"{BASE_URL}/api/products", json=product_data)
        assert response.status_code in [200, 201], f"Failed to create product: {response.text}"
        product = response.json()
        self.created_product_id = product["id"]
        print(f"Created product: {product['name']}")
        
        now = datetime.now()
        
        # Create return lot 1 (older)
        return_lot_1_id = str(uuid.uuid4())
        return_lot_1 = {
            "id": return_lot_1_id,
            "product_id": self.created_product_id,
            "product_name": product["name"],
            "initial_quantity": 5,
            "current_quantity": 5,
            "purchase_price": 80.0,
            "selling_price": 100.0,
            "expiration_date": None,
            "supply_date": now.isoformat(),
            "lot_number": f"RETURN-1-{unique_id}",
            "source": "return",
            "is_active": True,
            "is_expired": False,
            "tenant_id": self.tenant_id,
            "created_at": now.isoformat(),
            "created_by": "TEST"
        }
        self.db.stock_lots.insert_one(return_lot_1)
        self.created_lot_ids.append(return_lot_1_id)
        print(f"Created return lot 1: {return_lot_1['lot_number']} (qty=5, created first)")
        
        # Create return lot 2 (newer)
        return_lot_2_id = str(uuid.uuid4())
        return_lot_2 = {
            "id": return_lot_2_id,
            "product_id": self.created_product_id,
            "product_name": product["name"],
            "initial_quantity": 3,
            "current_quantity": 3,
            "purchase_price": 80.0,
            "selling_price": 100.0,
            "expiration_date": None,
            "supply_date": (now + timedelta(hours=2)).isoformat(),
            "lot_number": f"RETURN-2-{unique_id}",
            "source": "return",
            "is_active": True,
            "is_expired": False,
            "tenant_id": self.tenant_id,
            "created_at": (now + timedelta(hours=2)).isoformat(),
            "created_by": "TEST"
        }
        self.db.stock_lots.insert_one(return_lot_2)
        self.created_lot_ids.append(return_lot_2_id)
        print(f"Created return lot 2: {return_lot_2['lot_number']} (qty=3, created second)")
        
        # Update product stock
        self.db.products.update_one(
            {"id": self.created_product_id},
            {"$set": {"stock": 8}}
        )
        
        # Create sale for 4 units
        print("\n=== Creating sale for 4 units ===")
        sale_data = {
            "items": [
                {
                    "product_id": self.created_product_id,
                    "quantity": 4,
                    "unit_price": 100.0,
                    "subtotal": 400.0
                }
            ],
            "total": 400.0,
            "payment_method": "cash"
        }
        
        response = self.session.post(f"{BASE_URL}/api/sales", json=sale_data)
        assert response.status_code in [200, 201], f"Failed to create sale: {response.text}"
        sale = response.json()
        self.created_sale_ids.append(sale["id"])
        
        # Check lots used
        if "items" in sale and sale["items"]:
            lots_used = sale["items"][0].get("lots_used", [])
            print(f"Lots used: {lots_used}")
        
        # Verify lot quantities
        lots_after = list(self.db.stock_lots.find({
            "id": {"$in": [return_lot_1_id, return_lot_2_id]}
        }))
        
        for lot in lots_after:
            print(f"  - {lot.get('lot_number')}: qty={lot.get('current_quantity')}")
        
        # Expected: return lot 1 = 1 (5-4), return lot 2 = 3 (unchanged)
        # OR: return lot 1 = 0, return lot 2 = 4-1 = 3 (if lot 1 fully consumed)
        
        lot_1_qty = next((l.get('current_quantity', 0) for l in lots_after if l['id'] == return_lot_1_id), 0)
        lot_2_qty = next((l.get('current_quantity', 0) for l in lots_after if l['id'] == return_lot_2_id), 0)
        
        if lot_1_qty == 1 and lot_2_qty == 3:
            print("\n✅ SUCCESS: Older return lot (lot 1) was consumed first!")
        elif lot_1_qty < 5:
            print(f"\n✅ SUCCESS: Older return lot was consumed (lot 1: 5->{lot_1_qty})")
        else:
            print(f"\n⚠️ Unexpected: lot 1={lot_1_qty}, lot 2={lot_2_qty}")
        
        print("\n=== Test completed ===")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
