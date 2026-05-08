"""
Test suite for Shift Schedules API
Tests the shift scheduling feature including:
- Calendar view (admin only)
- Week view (admin only)
- Eligibility check for opening shifts
- CRUD operations for schedules
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDS = {"email": "admin@pharmaflow.com", "password": "admin123"}
CAISSIER_CREDS = {"email": "caissier@pharmaflow.com", "password": "caisse123"}
PHARMACIEN_CREDS = {"email": "pharmacien@pharmaflow.com", "password": "pharma123"}


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def caissier_token():
    """Get caissier authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=CAISSIER_CREDS)
    assert response.status_code == 200, f"Caissier login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def pharmacien_token():
    """Get pharmacien authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=PHARMACIEN_CREDS)
    assert response.status_code == 200, f"Pharmacien login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def caissier_headers(caissier_token):
    """Headers with caissier auth"""
    return {"Authorization": f"Bearer {caissier_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def pharmacien_headers(pharmacien_token):
    """Headers with pharmacien auth"""
    return {"Authorization": f"Bearer {pharmacien_token}", "Content-Type": "application/json"}


class TestShiftSchedulesAccess:
    """Test access control for shift schedules endpoints"""
    
    def test_calendar_view_admin_access(self, admin_headers):
        """Admin should access calendar view"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/calendar?year=2026&month=2",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "year" in data
        assert "month" in data
        assert "schedules" in data
        assert "users" in data
        assert data["year"] == 2026
        assert data["month"] == 2
    
    def test_calendar_view_caissier_denied(self, caissier_headers):
        """Caissier should NOT access calendar view (admin only)"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/calendar?year=2026&month=2",
            headers=caissier_headers
        )
        assert response.status_code == 403
    
    def test_calendar_view_pharmacien_denied(self, pharmacien_headers):
        """Pharmacien should NOT access calendar view (admin only)"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/calendar?year=2026&month=2",
            headers=pharmacien_headers
        )
        assert response.status_code == 403
    
    def test_week_view_admin_access(self, admin_headers):
        """Admin should access week view"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/week?start_date=2026-02-01",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "start_date" in data
        assert "end_date" in data
        assert "schedules_by_user" in data
        assert "users" in data
    
    def test_week_view_caissier_denied(self, caissier_headers):
        """Caissier should NOT access week view (admin only)"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/week?start_date=2026-02-01",
            headers=caissier_headers
        )
        assert response.status_code == 403


class TestShiftEligibility:
    """Test shift eligibility check endpoint"""
    
    def test_admin_always_eligible(self, admin_headers):
        """Admin should always be eligible (exempt from scheduling)"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/check-eligibility",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_eligible"] == True
        assert data["reason"] is None
        assert data["schedule"] is None  # Admin has no schedule
        assert data["max_duration_hours"] == 8.0  # Default for admin
    
    def test_caissier_eligible_when_scheduled(self, caissier_headers):
        """Caissier should be eligible when scheduled for today"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/check-eligibility",
            headers=caissier_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_eligible"] == True
        assert data["reason"] is None
        # Should have schedule details
        assert data["schedule"] is not None
        assert data["schedule"]["employee_code"] == "CAI-001"
        assert data["schedule"]["scheduled_date"] == "2026-02-01"
        assert data["suggested_end_time"] == "16:00"
        assert data["max_duration_hours"] == 8.0
    
    def test_pharmacien_not_eligible_before_scheduled_hours(self, pharmacien_headers):
        """Pharmacien scheduled 14:00-22:00 should NOT be eligible before 14:00 (current ~10:14 UTC)"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/check-eligibility",
            headers=pharmacien_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_eligible"] == False
        # Should have specific message about shift starting later
        assert "commence à 14:00" in data["reason"]
        # Should still have schedule details (user IS scheduled, just before hours)
        assert data["schedule"] is not None
        assert data["schedule"]["employee_code"] == "PHA-001"
        assert data["schedule"]["start_time"] == "14:00"
        assert data["schedule"]["end_time"] == "22:00"
        assert data["suggested_end_time"] == "22:00"
        assert data["max_duration_hours"] == 8


class TestShiftScheduleCRUD:
    """Test CRUD operations for shift schedules"""
    
    def test_create_schedule_admin_only(self, admin_headers, pharmacien_headers):
        """Only admin can create schedules"""
        # Get pharmacien user ID
        response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        users = response.json()
        pharmacien_user = next((u for u in users if u.get("employee_code") == "PHA-001"), None)
        assert pharmacien_user is not None
        
        # Use a future date that doesn't have a schedule
        schedule_data = {
            "user_id": pharmacien_user["id"],
            "scheduled_date": "2026-02-15",
            "start_time": "09:00",
            "end_time": "17:00",
            "max_duration_hours": 8.0,
            "notes": "Test schedule"
        }
        
        # Pharmacien cannot create
        response = requests.post(
            f"{BASE_URL}/api/shift-schedules",
            headers=pharmacien_headers,
            json=schedule_data
        )
        assert response.status_code == 403
        
        # Admin can create
        response = requests.post(
            f"{BASE_URL}/api/shift-schedules",
            headers=admin_headers,
            json=schedule_data
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["schedule"]["scheduled_date"] == "2026-02-15"
        
        # Cleanup - delete the created schedule
        schedule_id = data["id"]
        requests.delete(f"{BASE_URL}/api/shift-schedules/{schedule_id}", headers=admin_headers)
    
    def test_cannot_schedule_admin_user(self, admin_headers):
        """Admin users cannot be scheduled (exempt)"""
        # Get admin user ID
        response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        users = response.json()
        admin_user = next((u for u in users if u.get("role") == "admin"), None)
        assert admin_user is not None
        
        schedule_data = {
            "user_id": admin_user["id"],
            "scheduled_date": "2026-02-03",
            "start_time": "08:00",
            "end_time": "16:00"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/shift-schedules",
            headers=admin_headers,
            json=schedule_data
        )
        assert response.status_code == 400
        assert "exempt" in response.json()["detail"].lower()
    
    def test_duplicate_schedule_rejected(self, admin_headers):
        """Cannot create duplicate schedule for same user/date"""
        # Caissier already has schedule for 2026-02-01
        response = requests.get(f"{BASE_URL}/api/users", headers=admin_headers)
        users = response.json()
        caissier_user = next((u for u in users if u.get("employee_code") == "CAI-001"), None)
        
        schedule_data = {
            "user_id": caissier_user["id"],
            "scheduled_date": "2026-02-01",  # Already scheduled
            "start_time": "10:00",
            "end_time": "18:00"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/shift-schedules",
            headers=admin_headers,
            json=schedule_data
        )
        assert response.status_code == 400
        assert "existe déjà" in response.json()["detail"].lower()


class TestMySchedule:
    """Test my-schedule endpoint for users"""
    
    def test_caissier_can_see_own_schedule(self, caissier_headers):
        """Caissier can see their own schedule"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/my-schedule?date=2026-02-01",
            headers=caissier_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert data["employee_code"] == "CAI-001"
        assert data["scheduled_date"] == "2026-02-01"
    
    def test_pharmacien_has_schedule(self, pharmacien_headers):
        """Pharmacien has schedule for today (14:00-22:00)"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/my-schedule?date=2026-02-01",
            headers=pharmacien_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert data["employee_code"] == "PHA-001"
        assert data["scheduled_date"] == "2026-02-01"
        assert data["start_time"] == "14:00"
        assert data["end_time"] == "22:00"


class TestCalendarData:
    """Test calendar data structure"""
    
    def test_calendar_returns_users_list(self, admin_headers):
        """Calendar should return list of schedulable users (non-admin)"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/calendar?year=2026&month=2",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        users = data["users"]
        assert len(users) > 0
        
        # No admin users in the list
        for user in users:
            assert user["role"] != "admin"
            assert user["role"] in ["caissier", "pharmacien"]
    
    def test_calendar_schedules_grouped_by_date(self, admin_headers):
        """Schedules should be grouped by date"""
        response = requests.get(
            f"{BASE_URL}/api/shift-schedules/calendar?year=2026&month=2",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        schedules = data["schedules"]
        # Should have 2026-02-01 with caissier schedule
        assert "2026-02-01" in schedules
        assert len(schedules["2026-02-01"]) >= 1
        
        # Check schedule structure
        schedule = schedules["2026-02-01"][0]
        assert "user_id" in schedule
        assert "employee_code" in schedule
        assert "start_time" in schedule
        assert "end_time" in schedule


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
