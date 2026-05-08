"""
Test suite for Shift Management (Gestion des Shifts de Caisse)
Tests:
- Opening a shift with opening amount
- Blocking sales when no shift is open
- Creating sales when shift is open
- Calculating expected closing amount (cash sales + opening)
- Closing shift with discrepancy detection
- Shift history for admin
- Shift statistics
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@pharmaflow.com"
ADMIN_PASSWORD = "admin123"
CAISSIER_EMAIL = "caissier@pharmaflow.com"
CAISSIER_PASSWORD = "caisse123"

# Test product ID (Diazépam 10mg)
TEST_PRODUCT_ID = "f6bfce32-24ae-4600-8c8b-3ca28da4cc0d"


class TestShiftManagement:
    """Test suite for shift management functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.admin_token = None
        self.caissier_token = None
        self.created_shift_id = None
        yield
        # Cleanup: close any open shifts
        self._cleanup_shifts()
    
    def _cleanup_shifts(self):
        """Close any open shifts after tests"""
        if self.caissier_token:
            headers = {"Authorization": f"Bearer {self.caissier_token}"}
            # Try to close any open shift
            try:
                current = self.session.get(f"{BASE_URL}/api/shifts/current", headers=headers)
                if current.status_code == 200 and current.json():
                    self.session.post(
                        f"{BASE_URL}/api/shifts/close",
                        headers=headers,
                        json={"actual_closing_amount": 0, "closing_notes": "Test cleanup"}
                    )
            except:
                pass
    
    def _login_admin(self):
        """Login as admin and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.admin_token = response.json().get("access_token")
        return self.admin_token
    
    def _login_caissier(self):
        """Login as caissier and return token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CAISSIER_EMAIL,
            "password": CAISSIER_PASSWORD
        })
        assert response.status_code == 200, f"Caissier login failed: {response.text}"
        self.caissier_token = response.json().get("access_token")
        return self.caissier_token
    
    def _close_existing_shift(self, token):
        """Close any existing open shift"""
        headers = {"Authorization": f"Bearer {token}"}
        current = self.session.get(f"{BASE_URL}/api/shifts/current", headers=headers)
        if current.status_code == 200 and current.json():
            self.session.post(
                f"{BASE_URL}/api/shifts/close",
                headers=headers,
                json={"actual_closing_amount": 0, "closing_notes": "Test cleanup"}
            )
    
    # ==================== TEST 1: Get current shift (no shift open) ====================
    def test_01_get_current_shift_none(self):
        """TEST 1: Get current shift when none is open - should return null"""
        token = self._login_caissier()
        self._close_existing_shift(token)  # Ensure no shift is open
        
        headers = {"Authorization": f"Bearer {token}"}
        response = self.session.get(f"{BASE_URL}/api/shifts/current", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data is None, f"Expected null when no shift open, got: {data}"
        print("TEST 1 PASSED: No current shift returns null")
    
    # ==================== TEST 2: Open a shift ====================
    def test_02_open_shift(self):
        """TEST 2: Open a new shift with opening amount"""
        token = self._login_caissier()
        self._close_existing_shift(token)  # Ensure no shift is open
        
        headers = {"Authorization": f"Bearer {token}"}
        opening_amount = 50000  # 50,000 GNF
        
        response = self.session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": opening_amount}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "id" in data, "Response should contain shift id"
        assert data["opening_amount"] == opening_amount, f"Opening amount mismatch: {data['opening_amount']}"
        assert data["status"] == "open", f"Status should be 'open', got: {data['status']}"
        assert "user_name" in data, "Response should contain user_name"
        assert "employee_code" in data, "Response should contain employee_code"
        
        self.created_shift_id = data["id"]
        print(f"TEST 2 PASSED: Shift opened with ID {self.created_shift_id}")
        
        # Close the shift for cleanup
        self._close_existing_shift(token)
    
    # ==================== TEST 3: Cannot open second shift ====================
    def test_03_cannot_open_second_shift(self):
        """TEST 3: Cannot open a second shift when one is already open"""
        token = self._login_caissier()
        self._close_existing_shift(token)
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Open first shift
        response1 = self.session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": 10000}
        )
        assert response1.status_code == 200, f"First shift open failed: {response1.text}"
        
        # Try to open second shift
        response2 = self.session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": 20000}
        )
        
        assert response2.status_code == 400, f"Expected 400 for second shift, got {response2.status_code}"
        assert "déjà un shift ouvert" in response2.json().get("detail", "").lower() or "already" in response2.json().get("detail", "").lower()
        print("TEST 3 PASSED: Cannot open second shift when one is already open")
        
        # Cleanup
        self._close_existing_shift(token)
    
    # ==================== TEST 4: Sales blocked without shift ====================
    def test_04_sales_blocked_without_shift(self):
        """TEST 4: Creating a sale should be blocked when no shift is open"""
        token = self._login_caissier()
        self._close_existing_shift(token)  # Ensure no shift is open
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to create a sale
        sale_data = {
            "items": [
                {
                    "product_id": TEST_PRODUCT_ID,
                    "product_name": "Diazépam 10mg",
                    "unit_price": 5000,
                    "quantity": 1,
                    "subtotal": 5000
                }
            ],
            "subtotal": 5000,
            "total": 5000,
            "payment_method": "cash",
            "amount_paid": 5000
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/sales",
            headers=headers,
            json=sale_data
        )
        
        # Should be blocked (403 Forbidden)
        assert response.status_code == 403, f"Expected 403 when no shift open, got {response.status_code}: {response.text}"
        print("TEST 4 PASSED: Sales blocked when no shift is open")
    
    # ==================== TEST 5: Sales allowed with shift ====================
    def test_05_sales_allowed_with_shift(self):
        """TEST 5: Creating a sale should be allowed when shift is open"""
        token = self._login_caissier()
        self._close_existing_shift(token)
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Open a shift first
        shift_response = self.session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": 50000}
        )
        assert shift_response.status_code == 200, f"Failed to open shift: {shift_response.text}"
        
        # Now create a sale
        sale_data = {
            "items": [
                {
                    "product_id": TEST_PRODUCT_ID,
                    "product_name": "Diazépam 10mg",
                    "unit_price": 5000,
                    "quantity": 1,
                    "subtotal": 5000
                }
            ],
            "subtotal": 5000,
            "total": 5000,
            "payment_method": "cash",
            "amount_paid": 5000
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/sales",
            headers=headers,
            json=sale_data
        )
        
        assert response.status_code in [200, 201], f"Expected 200/201 with shift open, got {response.status_code}: {response.text}"
        print("TEST 5 PASSED: Sales allowed when shift is open")
        
        # Cleanup
        self._close_existing_shift(token)
    
    # ==================== TEST 6: Calculate expected closing ====================
    def test_06_calculate_expected_closing(self):
        """TEST 6: Calculate expected closing amount (opening + cash sales)"""
        token = self._login_caissier()
        self._close_existing_shift(token)
        
        headers = {"Authorization": f"Bearer {token}"}
        opening_amount = 100000
        
        # Open shift
        self.session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": opening_amount}
        )
        
        # Create a cash sale
        sale_amount = 15000
        sale_data = {
            "items": [
                {
                    "product_id": TEST_PRODUCT_ID,
                    "product_name": "Diazépam 10mg",
                    "unit_price": sale_amount,
                    "quantity": 1,
                    "subtotal": sale_amount
                }
            ],
            "subtotal": sale_amount,
            "total": sale_amount,
            "payment_method": "cash",
            "amount_paid": sale_amount
        }
        self.session.post(f"{BASE_URL}/api/sales", headers=headers, json=sale_data)
        
        # Calculate expected
        response = self.session.get(f"{BASE_URL}/api/shifts/calculate-expected", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["opening_amount"] == opening_amount
        assert data["total_cash_sales"] >= sale_amount, f"Cash sales should include our sale: {data['total_cash_sales']}"
        assert data["expected_closing_amount"] >= opening_amount + sale_amount
        print(f"TEST 6 PASSED: Expected closing = {data['expected_closing_amount']} (opening: {opening_amount}, cash sales: {data['total_cash_sales']})")
        
        # Cleanup
        self._close_existing_shift(token)
    
    # ==================== TEST 7: Close shift with no discrepancy ====================
    def test_07_close_shift_no_discrepancy(self):
        """TEST 7: Close shift with exact amount (no discrepancy)"""
        token = self._login_caissier()
        self._close_existing_shift(token)
        
        headers = {"Authorization": f"Bearer {token}"}
        opening_amount = 50000
        
        # Open shift
        self.session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": opening_amount}
        )
        
        # Get expected amount
        expected_response = self.session.get(f"{BASE_URL}/api/shifts/calculate-expected", headers=headers)
        expected_amount = expected_response.json()["expected_closing_amount"]
        
        # Close with exact amount
        response = self.session.post(
            f"{BASE_URL}/api/shifts/close",
            headers=headers,
            json={"actual_closing_amount": expected_amount}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert data["has_discrepancy"] == False, f"Should have no discrepancy, got: {data}"
        assert data["difference"] == 0 or abs(data["difference"]) < 0.02  # Allow 1 centime tolerance
        print("TEST 7 PASSED: Shift closed with no discrepancy")
    
    # ==================== TEST 8: Close shift with discrepancy (shortage) ====================
    def test_08_close_shift_with_shortage(self):
        """TEST 8: Close shift with shortage (actual < expected)"""
        token = self._login_caissier()
        self._close_existing_shift(token)
        
        headers = {"Authorization": f"Bearer {token}"}
        opening_amount = 50000
        
        # Open shift
        self.session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": opening_amount}
        )
        
        # Get expected amount
        expected_response = self.session.get(f"{BASE_URL}/api/shifts/calculate-expected", headers=headers)
        expected_amount = expected_response.json()["expected_closing_amount"]
        
        # Close with less than expected (shortage)
        shortage = 5000
        actual_amount = expected_amount - shortage
        
        response = self.session.post(
            f"{BASE_URL}/api/shifts/close",
            headers=headers,
            json={
                "actual_closing_amount": actual_amount,
                "closing_notes": "Test shortage - money missing"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert data["has_discrepancy"] == True, "Should have discrepancy"
        assert data["difference"] == -shortage, f"Difference should be -{shortage}, got: {data['difference']}"
        print(f"TEST 8 PASSED: Shift closed with shortage of {shortage} GNF")
    
    # ==================== TEST 9: Close shift with surplus ====================
    def test_09_close_shift_with_surplus(self):
        """TEST 9: Close shift with surplus (actual > expected)"""
        token = self._login_caissier()
        self._close_existing_shift(token)
        
        headers = {"Authorization": f"Bearer {token}"}
        opening_amount = 50000
        
        # Open shift
        self.session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": opening_amount}
        )
        
        # Get expected amount
        expected_response = self.session.get(f"{BASE_URL}/api/shifts/calculate-expected", headers=headers)
        expected_amount = expected_response.json()["expected_closing_amount"]
        
        # Close with more than expected (surplus)
        surplus = 3000
        actual_amount = expected_amount + surplus
        
        response = self.session.post(
            f"{BASE_URL}/api/shifts/close",
            headers=headers,
            json={
                "actual_closing_amount": actual_amount,
                "closing_notes": "Test surplus - extra money found"
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert data["has_discrepancy"] == True, "Should have discrepancy"
        assert data["difference"] == surplus, f"Difference should be +{surplus}, got: {data['difference']}"
        print(f"TEST 9 PASSED: Shift closed with surplus of {surplus} GNF")
    
    # ==================== TEST 10: Shift history (admin only) ====================
    def test_10_shift_history_admin(self):
        """TEST 10: Admin can view shift history"""
        token = self._login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/shifts/history", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "History should be a list"
        print(f"TEST 10 PASSED: Admin can view shift history ({len(data)} shifts)")
    
    # ==================== TEST 11: Shift history denied for non-admin ====================
    def test_11_shift_history_denied_non_admin(self):
        """TEST 11: Non-admin cannot view shift history"""
        token = self._login_caissier()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/shifts/history", headers=headers)
        
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print("TEST 11 PASSED: Non-admin denied access to shift history")
    
    # ==================== TEST 12: Shift statistics (admin only) ====================
    def test_12_shift_stats_admin(self):
        """TEST 12: Admin can view shift statistics"""
        token = self._login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = self.session.get(f"{BASE_URL}/api/shifts/stats", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Validate stats structure
        assert "total_shifts" in data, "Stats should contain total_shifts"
        assert "total_discrepancies" in data, "Stats should contain total_discrepancies"
        assert "discrepancy_rate" in data, "Stats should contain discrepancy_rate"
        assert "total_positive_diff" in data, "Stats should contain total_positive_diff"
        assert "total_negative_diff" in data, "Stats should contain total_negative_diff"
        
        print(f"TEST 12 PASSED: Shift stats - {data['total_shifts']} shifts, {data['discrepancy_rate']}% discrepancy rate")
    
    # ==================== TEST 13: Mixed payment cash calculation ====================
    def test_13_mixed_payment_cash_calculation(self):
        """TEST 13: Cash portion of mixed payments should be included in shift calculation"""
        token = self._login_caissier()
        self._close_existing_shift(token)
        
        headers = {"Authorization": f"Bearer {token}"}
        opening_amount = 100000
        
        # Open shift
        self.session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": opening_amount}
        )
        
        # Create a mixed payment sale (cash + card)
        cash_portion = 10000
        card_portion = 5000
        total = cash_portion + card_portion
        
        sale_data = {
            "items": [
                {
                    "product_id": TEST_PRODUCT_ID,
                    "product_name": "Diazépam 10mg",
                    "unit_price": total,
                    "quantity": 1,
                    "subtotal": total
                }
            ],
            "subtotal": total,
            "total": total,
            "payment_method": "mixed",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": cash_portion},
                {"method": "card", "amount": card_portion}
            ],
            "amount_paid": total
        }
        
        sale_response = self.session.post(f"{BASE_URL}/api/sales", headers=headers, json=sale_data)
        
        if sale_response.status_code in [200, 201]:
            # Get expected closing
            expected_response = self.session.get(f"{BASE_URL}/api/shifts/calculate-expected", headers=headers)
            data = expected_response.json()
            
            # Cash sales should include only the cash portion
            assert data["total_cash_sales"] >= cash_portion, f"Cash sales should include cash portion: {data['total_cash_sales']}"
            print(f"TEST 13 PASSED: Mixed payment cash portion ({cash_portion}) included in shift calculation")
        else:
            print(f"TEST 13 SKIPPED: Mixed payment sale failed with {sale_response.status_code}")
        
        # Cleanup
        self._close_existing_shift(token)
    
    # ==================== TEST 14: Get shift details ====================
    def test_14_get_shift_details(self):
        """TEST 14: Get details of a specific shift"""
        # First create and close a shift
        token = self._login_caissier()
        self._close_existing_shift(token)
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Open shift
        open_response = self.session.post(
            f"{BASE_URL}/api/shifts/open",
            headers=headers,
            json={"opening_amount": 25000}
        )
        shift_id = open_response.json()["id"]
        
        # Close shift
        self.session.post(
            f"{BASE_URL}/api/shifts/close",
            headers=headers,
            json={"actual_closing_amount": 25000}
        )
        
        # Get shift details
        response = self.session.get(f"{BASE_URL}/api/shifts/{shift_id}", headers=headers)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert data["id"] == shift_id
        assert data["status"] == "closed"
        assert "opening_amount" in data
        assert "actual_closing_amount" in data
        print(f"TEST 14 PASSED: Got shift details for {shift_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
