"""
Test suite for Shift End Alerts feature
Tests:
- expected_end_time field in shift opening
- default_shift_duration_hours in settings
- PATCH /api/shifts/mark-alert/{type} endpoint
- Alert flags (alert_30min_shown, alert_5min_shown, alert_end_shown)
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestShiftAlerts:
    """Test shift alert functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: Login and get token"""
        # Login as admin
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@pharmaflow.com",
            "password": "admin123"
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.admin_token = login_response.json().get("access_token")
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Login as caissier
        caissier_login = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "caissier@pharmaflow.com",
            "password": "caisse123"
        })
        assert caissier_login.status_code == 200, f"Caissier login failed: {caissier_login.text}"
        self.caissier_token = caissier_login.json().get("access_token")
        self.caissier_headers = {"Authorization": f"Bearer {self.caissier_token}"}
        
        # Close any existing shift for caissier
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 0},
                     headers=self.caissier_headers)
        
        yield
        
        # Cleanup: Close any open shift
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 0},
                     headers=self.caissier_headers)
    
    def test_01_settings_has_default_shift_duration(self):
        """TEST 1: Settings should have default_shift_duration_hours field"""
        response = requests.get(f"{BASE_URL}/api/settings", headers=self.admin_headers)
        assert response.status_code == 200, f"Failed to get settings: {response.text}"
        
        settings = response.json()
        assert "default_shift_duration_hours" in settings, "default_shift_duration_hours not in settings"
        assert isinstance(settings["default_shift_duration_hours"], int), "default_shift_duration_hours should be int"
        assert settings["default_shift_duration_hours"] > 0, "default_shift_duration_hours should be positive"
        print(f"✓ TEST 1 PASSED: default_shift_duration_hours = {settings['default_shift_duration_hours']}")
    
    def test_02_update_default_shift_duration(self):
        """TEST 2: Can update default_shift_duration_hours in settings"""
        # Update to 10 hours
        response = requests.put(f"{BASE_URL}/api/settings", 
                               json={"default_shift_duration_hours": 10},
                               headers=self.admin_headers)
        assert response.status_code == 200, f"Failed to update settings: {response.text}"
        
        # Verify update
        get_response = requests.get(f"{BASE_URL}/api/settings", headers=self.admin_headers)
        settings = get_response.json()
        assert settings["default_shift_duration_hours"] == 10, "Setting not updated"
        
        # Reset to 8 hours
        requests.put(f"{BASE_URL}/api/settings", 
                    json={"default_shift_duration_hours": 8},
                    headers=self.admin_headers)
        print("✓ TEST 2 PASSED: default_shift_duration_hours can be updated")
    
    def test_03_open_shift_with_expected_end_time(self):
        """TEST 3: Open shift with explicit expected_end_time"""
        # Calculate end time 2 hours from now
        end_time = (datetime.utcnow() + timedelta(hours=2)).strftime("%H:%M")
        
        response = requests.post(f"{BASE_URL}/api/shifts/open",
                                json={
                                    "opening_amount": 50000,
                                    "expected_end_time": end_time
                                },
                                headers=self.caissier_headers)
        assert response.status_code == 200, f"Failed to open shift: {response.text}"
        
        shift = response.json()
        assert "expected_end_time" in shift, "expected_end_time not in response"
        assert shift["expected_end_time"] is not None, "expected_end_time should not be null"
        
        # Verify alert flags are initialized to False
        assert shift.get("alert_30min_shown") == False, "alert_30min_shown should be False"
        assert shift.get("alert_5min_shown") == False, "alert_5min_shown should be False"
        assert shift.get("alert_end_shown") == False, "alert_end_shown should be False"
        
        print(f"✓ TEST 3 PASSED: Shift opened with expected_end_time = {shift['expected_end_time']}")
        
        # Close shift for next test
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 50000},
                     headers=self.caissier_headers)
    
    def test_04_open_shift_without_end_time_uses_default(self):
        """TEST 4: Open shift without expected_end_time uses default duration from settings"""
        # Get current default duration
        settings_response = requests.get(f"{BASE_URL}/api/settings", headers=self.admin_headers)
        default_duration = settings_response.json().get("default_shift_duration_hours", 8)
        
        # Open shift without expected_end_time
        response = requests.post(f"{BASE_URL}/api/shifts/open",
                                json={"opening_amount": 50000},
                                headers=self.caissier_headers)
        assert response.status_code == 200, f"Failed to open shift: {response.text}"
        
        shift = response.json()
        assert "expected_end_time" in shift, "expected_end_time not in response"
        assert shift["expected_end_time"] is not None, "expected_end_time should be calculated from default"
        
        # Verify the end time is approximately default_duration hours from now
        opened_at = datetime.fromisoformat(shift["opened_at"].replace("Z", "+00:00"))
        expected_end = datetime.fromisoformat(shift["expected_end_time"].replace("Z", "+00:00"))
        duration_hours = (expected_end - opened_at).total_seconds() / 3600
        
        # Allow 1 minute tolerance
        assert abs(duration_hours - default_duration) < 0.02, f"Duration mismatch: expected {default_duration}h, got {duration_hours}h"
        
        print(f"✓ TEST 4 PASSED: Shift uses default duration ({default_duration}h)")
        
        # Close shift for next test
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 50000},
                     headers=self.caissier_headers)
    
    def test_05_mark_alert_30min(self):
        """TEST 5: Mark 30min alert as shown"""
        # Open a shift first
        requests.post(f"{BASE_URL}/api/shifts/open",
                     json={"opening_amount": 50000},
                     headers=self.caissier_headers)
        
        # Mark 30min alert
        response = requests.patch(f"{BASE_URL}/api/shifts/mark-alert/30min",
                                 headers=self.caissier_headers)
        assert response.status_code == 200, f"Failed to mark alert: {response.text}"
        
        result = response.json()
        assert result.get("success") == True, "Response should indicate success"
        assert result.get("alert_type") == "30min", "Alert type should be 30min"
        assert result.get("marked") == True, "Alert should be marked"
        
        # Verify in current shift
        shift_response = requests.get(f"{BASE_URL}/api/shifts/current", headers=self.caissier_headers)
        shift = shift_response.json()
        assert shift.get("alert_30min_shown") == True, "alert_30min_shown should be True"
        
        print("✓ TEST 5 PASSED: 30min alert marked successfully")
        
        # Close shift
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 50000},
                     headers=self.caissier_headers)
    
    def test_06_mark_alert_5min(self):
        """TEST 6: Mark 5min alert as shown"""
        # Open a shift first
        requests.post(f"{BASE_URL}/api/shifts/open",
                     json={"opening_amount": 50000},
                     headers=self.caissier_headers)
        
        # Mark 5min alert
        response = requests.patch(f"{BASE_URL}/api/shifts/mark-alert/5min",
                                 headers=self.caissier_headers)
        assert response.status_code == 200, f"Failed to mark alert: {response.text}"
        
        result = response.json()
        assert result.get("success") == True, "Response should indicate success"
        assert result.get("alert_type") == "5min", "Alert type should be 5min"
        
        # Verify in current shift
        shift_response = requests.get(f"{BASE_URL}/api/shifts/current", headers=self.caissier_headers)
        shift = shift_response.json()
        assert shift.get("alert_5min_shown") == True, "alert_5min_shown should be True"
        
        print("✓ TEST 6 PASSED: 5min alert marked successfully")
        
        # Close shift
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 50000},
                     headers=self.caissier_headers)
    
    def test_07_mark_alert_end(self):
        """TEST 7: Mark end alert as shown"""
        # Open a shift first
        requests.post(f"{BASE_URL}/api/shifts/open",
                     json={"opening_amount": 50000},
                     headers=self.caissier_headers)
        
        # Mark end alert
        response = requests.patch(f"{BASE_URL}/api/shifts/mark-alert/end",
                                 headers=self.caissier_headers)
        assert response.status_code == 200, f"Failed to mark alert: {response.text}"
        
        result = response.json()
        assert result.get("success") == True, "Response should indicate success"
        assert result.get("alert_type") == "end", "Alert type should be end"
        
        # Verify in current shift
        shift_response = requests.get(f"{BASE_URL}/api/shifts/current", headers=self.caissier_headers)
        shift = shift_response.json()
        assert shift.get("alert_end_shown") == True, "alert_end_shown should be True"
        
        print("✓ TEST 7 PASSED: end alert marked successfully")
        
        # Close shift
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 50000},
                     headers=self.caissier_headers)
    
    def test_08_mark_alert_invalid_type(self):
        """TEST 8: Invalid alert type returns 400"""
        # Open a shift first
        requests.post(f"{BASE_URL}/api/shifts/open",
                     json={"opening_amount": 50000},
                     headers=self.caissier_headers)
        
        # Try invalid alert type
        response = requests.patch(f"{BASE_URL}/api/shifts/mark-alert/invalid",
                                 headers=self.caissier_headers)
        assert response.status_code == 400, f"Should return 400 for invalid type: {response.status_code}"
        
        print("✓ TEST 8 PASSED: Invalid alert type returns 400")
        
        # Close shift
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 50000},
                     headers=self.caissier_headers)
    
    def test_09_mark_alert_no_shift_returns_404(self):
        """TEST 9: Mark alert without open shift returns 404"""
        # Ensure no shift is open
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 0},
                     headers=self.caissier_headers)
        
        # Try to mark alert
        response = requests.patch(f"{BASE_URL}/api/shifts/mark-alert/30min",
                                 headers=self.caissier_headers)
        assert response.status_code == 404, f"Should return 404 when no shift: {response.status_code}"
        
        print("✓ TEST 9 PASSED: Mark alert without shift returns 404")
    
    def test_10_current_shift_includes_expected_end_time(self):
        """TEST 10: GET /shifts/current includes expected_end_time"""
        # Open a shift
        requests.post(f"{BASE_URL}/api/shifts/open",
                     json={"opening_amount": 50000, "expected_end_time": "18:00"},
                     headers=self.caissier_headers)
        
        # Get current shift
        response = requests.get(f"{BASE_URL}/api/shifts/current", headers=self.caissier_headers)
        assert response.status_code == 200, f"Failed to get current shift: {response.text}"
        
        shift = response.json()
        assert "expected_end_time" in shift, "expected_end_time should be in response"
        assert "alert_30min_shown" in shift, "alert_30min_shown should be in response"
        assert "alert_5min_shown" in shift, "alert_5min_shown should be in response"
        assert "alert_end_shown" in shift, "alert_end_shown should be in response"
        
        print("✓ TEST 10 PASSED: Current shift includes all alert fields")
        
        # Close shift
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 50000},
                     headers=self.caissier_headers)
    
    def test_11_open_shift_with_iso_datetime(self):
        """TEST 11: Open shift with ISO datetime format for expected_end_time"""
        # Use full ISO datetime
        end_time = (datetime.utcnow() + timedelta(hours=4)).isoformat() + "Z"
        
        response = requests.post(f"{BASE_URL}/api/shifts/open",
                                json={
                                    "opening_amount": 50000,
                                    "expected_end_time": end_time
                                },
                                headers=self.caissier_headers)
        assert response.status_code == 200, f"Failed to open shift: {response.text}"
        
        shift = response.json()
        assert shift["expected_end_time"] is not None, "expected_end_time should be set"
        
        print("✓ TEST 11 PASSED: Shift accepts ISO datetime format")
        
        # Close shift
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 50000},
                     headers=self.caissier_headers)
    
    def test_12_all_alerts_can_be_marked_sequentially(self):
        """TEST 12: All three alerts can be marked in sequence"""
        # Open a shift
        requests.post(f"{BASE_URL}/api/shifts/open",
                     json={"opening_amount": 50000},
                     headers=self.caissier_headers)
        
        # Mark all alerts
        for alert_type in ['30min', '5min', 'end']:
            response = requests.patch(f"{BASE_URL}/api/shifts/mark-alert/{alert_type}",
                                     headers=self.caissier_headers)
            assert response.status_code == 200, f"Failed to mark {alert_type} alert"
        
        # Verify all are marked
        shift_response = requests.get(f"{BASE_URL}/api/shifts/current", headers=self.caissier_headers)
        shift = shift_response.json()
        
        assert shift.get("alert_30min_shown") == True, "30min alert should be marked"
        assert shift.get("alert_5min_shown") == True, "5min alert should be marked"
        assert shift.get("alert_end_shown") == True, "end alert should be marked"
        
        print("✓ TEST 12 PASSED: All alerts can be marked sequentially")
        
        # Close shift
        requests.post(f"{BASE_URL}/api/shifts/close", 
                     json={"actual_closing_amount": 50000},
                     headers=self.caissier_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
