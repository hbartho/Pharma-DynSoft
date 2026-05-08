"""
Test suite for Debt Write-Off (Abandon) functionality
Tests the POST /api/debts/{debt_id}/write-off endpoint
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@pharmaflow.com"
ADMIN_PASSWORD = "admin123"
CASHIER_EMAIL = "caissier@pharmaflow.com"
CASHIER_PASSWORD = "caisse123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def cashier_token():
    """Get cashier authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": CASHIER_EMAIL,
        "password": CASHIER_PASSWORD
    })
    assert response.status_code == 200, f"Cashier login failed: {response.text}"
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def active_debt_id(admin_token):
    """Get an active debt ID for testing"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = requests.get(f"{BASE_URL}/api/debts", headers=headers)
    assert response.status_code == 200
    
    debts = response.json()
    # Find a debt that is not already abandoned or paid
    for debt in debts:
        if debt.get("status") in ["pending", "partial"]:
            return debt.get("id")
    
    pytest.skip("No active debt found for testing")


class TestWriteOffPermissions:
    """Test write-off endpoint permission checks"""
    
    def test_write_off_returns_403_for_cashier(self, cashier_token, active_debt_id):
        """Cashier should get 403 Forbidden when trying to write-off a debt"""
        headers = {"Authorization": f"Bearer {cashier_token}"}
        response = requests.post(
            f"{BASE_URL}/api/debts/{active_debt_id}/write-off",
            headers=headers,
            json={"reason": "Test abandon by cashier"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        data = response.json()
        assert "administrateurs" in data.get("detail", "").lower() or "admin" in data.get("detail", "").lower()
    
    def test_write_off_returns_401_or_403_without_auth(self, active_debt_id):
        """Unauthenticated request should get 401 or 403"""
        response = requests.post(
            f"{BASE_URL}/api/debts/{active_debt_id}/write-off",
            json={"reason": "Test abandon without auth"}
        )
        
        # Accept both 401 (Unauthorized) and 403 (Forbidden) for unauthenticated requests
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"


class TestWriteOffValidation:
    """Test write-off endpoint validation"""
    
    def test_write_off_requires_reason(self, admin_token, active_debt_id):
        """Write-off should fail without a reason"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(
            f"{BASE_URL}/api/debts/{active_debt_id}/write-off",
            headers=headers,
            json={}
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        data = response.json()
        # Check that reason field is required
        assert any("reason" in str(err).lower() for err in data.get("detail", []))
    
    def test_write_off_returns_404_for_invalid_debt(self, admin_token):
        """Write-off should return 404 for non-existent debt"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(
            f"{BASE_URL}/api/debts/invalid-debt-id-12345/write-off",
            headers=headers,
            json={"reason": "Test invalid debt"}
        )
        
        assert response.status_code == 404


class TestWriteOffFunctionality:
    """Test write-off endpoint functionality"""
    
    def test_admin_can_write_off_debt(self, admin_token):
        """Admin should be able to write-off a debt with valid reason"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # First, get an active debt
        response = requests.get(f"{BASE_URL}/api/debts", headers=headers)
        assert response.status_code == 200
        
        debts = response.json()
        active_debt = None
        for debt in debts:
            if debt.get("status") in ["pending", "partial"] and debt.get("remaining_amount", 0) > 0:
                active_debt = debt
                break
        
        if not active_debt:
            pytest.skip("No active debt with remaining amount found")
        
        debt_id = active_debt["id"]
        original_amount = active_debt["remaining_amount"]
        
        # Write-off the debt
        write_off_reason = f"TEST_WRITE_OFF_{datetime.now().isoformat()}"
        response = requests.post(
            f"{BASE_URL}/api/debts/{debt_id}/write-off",
            headers=headers,
            json={"reason": write_off_reason}
        )
        
        assert response.status_code == 200, f"Write-off failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True
        assert data.get("debt_id") == debt_id
        assert data.get("written_off_amount") == original_amount
        assert data.get("reason") == write_off_reason
        assert "written_off_by" in data
        assert "written_off_at" in data
        
        # Verify debt status changed to abandoned
        response = requests.get(f"{BASE_URL}/api/debts/{debt_id}", headers=headers)
        assert response.status_code == 200
        
        updated_debt = response.json()
        assert updated_debt.get("status") == "abandoned"
        assert updated_debt.get("remaining_amount") == 0
        assert updated_debt.get("abandon_reason") == write_off_reason
        assert updated_debt.get("abandoned_at") is not None
        assert updated_debt.get("abandoned_by") is not None
        assert updated_debt.get("abandoned_by_name") is not None
    
    def test_write_off_creates_payment_history_entry(self, admin_token):
        """Write-off should create a payment history entry with type 'write_off'"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Check payment history for write_off entries
        response = requests.get(
            f"{BASE_URL}/api/debts/payments/history",
            headers=headers,
            params={"payment_method": "write_off", "limit": 10}
        )
        
        assert response.status_code == 200
        payments = response.json()
        
        # Should have at least one write_off entry
        assert len(payments) > 0, "No write_off entries found in payment history"
        
        # Verify write_off entry structure
        write_off_entry = payments[0]
        assert write_off_entry.get("payment_method") == "write_off"
        assert write_off_entry.get("transaction_type") == "write_off"
        assert write_off_entry.get("amount") > 0
        assert "Passage en perte" in write_off_entry.get("notes", "")
    
    def test_cannot_write_off_already_abandoned_debt(self, admin_token):
        """Should not be able to write-off an already abandoned debt"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get abandoned debts
        response = requests.get(
            f"{BASE_URL}/api/debts",
            headers=headers,
            params={"status": "abandoned"}
        )
        assert response.status_code == 200
        
        abandoned_debts = response.json()
        if not abandoned_debts:
            pytest.skip("No abandoned debt found for testing")
        
        abandoned_debt_id = abandoned_debts[0]["id"]
        
        # Try to write-off again
        response = requests.post(
            f"{BASE_URL}/api/debts/{abandoned_debt_id}/write-off",
            headers=headers,
            json={"reason": "Test double abandon"}
        )
        
        assert response.status_code == 400
        assert "déjà abandonnée" in response.json().get("detail", "").lower()


class TestDashboardWriteOffStats:
    """Test dashboard statistics for write-offs"""
    
    def test_dashboard_includes_write_off_stats(self, admin_token):
        """Dashboard should include write-off statistics"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/debts/dashboard", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify write-off stats are present
        assert "written_off_this_period" in data
        assert "written_off_count" in data
        assert isinstance(data["written_off_this_period"], (int, float))
        assert isinstance(data["written_off_count"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
