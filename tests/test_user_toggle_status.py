"""
Test suite for User Toggle Status Feature
Tests:
- PATCH /api/users/{user_id}/toggle-status endpoint
- Login rejection for deactivated users
- Admin cannot deactivate their own account
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@pharmaflow.com"
ADMIN_PASSWORD = "admin123"
PHARMACIEN_EMAIL = "pharmacien@pharmaflow.com"
PHARMACIEN_PASSWORD = "pharma123"
CAISSIER_EMAIL = "caissier@pharmaflow.com"
CAISSIER_PASSWORD = "caisse123"


class TestUserToggleStatus:
    """Tests for user activation/deactivation feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_admin_token(self):
        """Get admin authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"], response.json()["user"]["id"]
    
    def get_pharmacien_token(self):
        """Get pharmacien authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": PHARMACIEN_EMAIL,
            "password": PHARMACIEN_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"], response.json()["user"]["id"]
        return None, None
    
    def get_caissier_token(self):
        """Get caissier authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": CAISSIER_EMAIL,
            "password": CAISSIER_PASSWORD
        })
        if response.status_code == 200:
            return response.json()["access_token"], response.json()["user"]["id"]
        return None, None
    
    def test_admin_login_success(self):
        """Test admin can login successfully"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["is_active"] == True
        print(f"✓ Admin login successful: {data['user']['email']}")
    
    def test_get_users_list(self):
        """Test admin can get list of users"""
        token, _ = self.get_admin_token()
        response = self.session.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) > 0
        # Verify users have is_active field
        for user in users:
            assert "is_active" in user, f"User {user.get('email')} missing is_active field"
        print(f"✓ Got {len(users)} users, all have is_active field")
    
    def test_toggle_status_deactivate_user(self):
        """Test admin can deactivate another user"""
        token, admin_id = self.get_admin_token()
        
        # Get list of users to find a non-admin user
        response = self.session.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        users = response.json()
        
        # Find a user that is not the admin
        target_user = None
        for user in users:
            if user["id"] != admin_id and user.get("is_active", True):
                target_user = user
                break
        
        if not target_user:
            pytest.skip("No other active user found to test deactivation")
        
        initial_status = target_user.get("is_active", True)
        print(f"Target user: {target_user['email']}, initial status: {initial_status}")
        
        # Toggle status (deactivate)
        response = self.session.patch(
            f"{BASE_URL}/api/users/{target_user['id']}/toggle-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Toggle failed: {response.text}"
        
        updated_user = response.json()
        assert updated_user["is_active"] == (not initial_status), "Status should be toggled"
        print(f"✓ User status toggled from {initial_status} to {updated_user['is_active']}")
        
        # Store for cleanup
        self.deactivated_user_id = target_user["id"]
        self.deactivated_user_email = target_user["email"]
        
        # Reactivate the user for other tests
        response = self.session.patch(
            f"{BASE_URL}/api/users/{target_user['id']}/toggle-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        print(f"✓ User reactivated for cleanup")
    
    def test_admin_cannot_deactivate_self(self):
        """Test admin cannot deactivate their own account"""
        token, admin_id = self.get_admin_token()
        
        # Try to toggle own status
        response = self.session.patch(
            f"{BASE_URL}/api/users/{admin_id}/toggle-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        # Check for French error message
        assert "propre compte" in data["detail"].lower() or "own account" in data["detail"].lower()
        print(f"✓ Admin correctly prevented from deactivating self: {data['detail']}")
    
    def test_deactivated_user_cannot_login(self):
        """Test that a deactivated user cannot login"""
        token, admin_id = self.get_admin_token()
        
        # Get list of users to find a non-admin user
        response = self.session.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        users = response.json()
        
        # Find a user that is not the admin
        target_user = None
        target_password = None
        for user in users:
            if user["id"] != admin_id:
                if user["email"] == PHARMACIEN_EMAIL:
                    target_user = user
                    target_password = PHARMACIEN_PASSWORD
                    break
                elif user["email"] == CAISSIER_EMAIL:
                    target_user = user
                    target_password = CAISSIER_PASSWORD
                    break
        
        if not target_user:
            pytest.skip("No test user found to test deactivation login")
        
        print(f"Testing with user: {target_user['email']}")
        
        # Ensure user is active first
        if not target_user.get("is_active", True):
            response = self.session.patch(
                f"{BASE_URL}/api/users/{target_user['id']}/toggle-status",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
        
        # Verify user can login when active
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": target_user["email"],
            "password": target_password
        })
        assert login_response.status_code == 200, f"Active user should be able to login: {login_response.text}"
        print(f"✓ Active user can login")
        
        # Deactivate the user
        response = self.session.patch(
            f"{BASE_URL}/api/users/{target_user['id']}/toggle-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["is_active"] == False
        print(f"✓ User deactivated")
        
        # Try to login with deactivated user
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": target_user["email"],
            "password": target_password
        })
        
        assert login_response.status_code == 401, f"Deactivated user should not be able to login, got {login_response.status_code}"
        data = login_response.json()
        assert "désactivé" in data.get("detail", "").lower() or "disabled" in data.get("detail", "").lower()
        print(f"✓ Deactivated user correctly rejected: {data.get('detail')}")
        
        # Reactivate the user for cleanup
        response = self.session.patch(
            f"{BASE_URL}/api/users/{target_user['id']}/toggle-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["is_active"] == True
        print(f"✓ User reactivated for cleanup")
    
    def test_toggle_status_requires_admin(self):
        """Test that non-admin users cannot toggle status"""
        # First login as admin to get a user ID
        admin_token, admin_id = self.get_admin_token()
        
        # Get list of users
        response = self.session.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        users = response.json()
        
        # Find pharmacien user
        pharmacien_user = None
        for user in users:
            if user["email"] == PHARMACIEN_EMAIL:
                pharmacien_user = user
                break
        
        if not pharmacien_user:
            pytest.skip("Pharmacien user not found")
        
        # Ensure pharmacien is active
        if not pharmacien_user.get("is_active", True):
            response = self.session.patch(
                f"{BASE_URL}/api/users/{pharmacien_user['id']}/toggle-status",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
        
        # Login as pharmacien
        pharmacien_token, _ = self.get_pharmacien_token()
        if not pharmacien_token:
            pytest.skip("Could not login as pharmacien")
        
        # Try to toggle another user's status as pharmacien
        response = self.session.patch(
            f"{BASE_URL}/api/users/{admin_id}/toggle-status",
            headers={"Authorization": f"Bearer {pharmacien_token}"}
        )
        
        # Should be forbidden (403) or unauthorized (401)
        assert response.status_code in [401, 403], f"Non-admin should not be able to toggle status, got {response.status_code}"
        print(f"✓ Non-admin correctly prevented from toggling status: {response.status_code}")
    
    def test_toggle_nonexistent_user(self):
        """Test toggling status of non-existent user returns 404"""
        token, _ = self.get_admin_token()
        
        fake_user_id = "00000000-0000-0000-0000-000000000000"
        response = self.session.patch(
            f"{BASE_URL}/api/users/{fake_user_id}/toggle-status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404, f"Expected 404 for non-existent user, got {response.status_code}"
        print(f"✓ Non-existent user correctly returns 404")
    
    def test_user_response_includes_is_active(self):
        """Test that user responses include is_active field"""
        token, _ = self.get_admin_token()
        
        # Get users list
        response = self.session.get(
            f"{BASE_URL}/api/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        users = response.json()
        
        for user in users:
            assert "is_active" in user, f"User {user.get('email')} missing is_active field"
            assert isinstance(user["is_active"], bool), f"is_active should be boolean for {user.get('email')}"
        
        print(f"✓ All {len(users)} users have is_active boolean field")
    
    def test_get_single_user_includes_is_active(self):
        """Test that single user endpoint includes is_active field"""
        token, admin_id = self.get_admin_token()
        
        response = self.session.get(
            f"{BASE_URL}/api/users/{admin_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        user = response.json()
        
        assert "is_active" in user, "Single user response missing is_active field"
        assert isinstance(user["is_active"], bool), "is_active should be boolean"
        print(f"✓ Single user endpoint includes is_active: {user['is_active']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
