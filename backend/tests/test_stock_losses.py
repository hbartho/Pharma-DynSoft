"""
Test suite for Stock Losses (Gestion des Pertes) feature
Tests:
- POST /api/stock/losses - Declare a loss (all users)
- GET /api/stock/losses/pending - Get pending losses
- POST /api/stock/losses/{id}/validate - Validate/reject loss (admin only)
- GET /api/stock/losses/stats - Get loss statistics
- GET /api/stock/losses/history - Get loss history
- GET /api/stock/losses/reasons - Get loss reasons
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestStockLossesAPI:
    """Test Stock Losses API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.admin_creds = {"email": "admin@pharmaflow.com", "password": "admin123"}
        self.pharmacien_creds = {"email": "pharmacien@pharmaflow.com", "password": "pharma123"}
        self.caissier_creds = {"email": "caissier@pharmaflow.com", "password": "caisse123"}
        
    def get_auth_token(self, credentials):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=credentials)
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
    
    def get_auth_headers(self, credentials):
        """Get headers with auth token"""
        token = self.get_auth_token(credentials)
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    def get_product_with_stock(self, headers):
        """Get a product with stock > 0"""
        response = requests.get(f"{BASE_URL}/api/products", headers=headers)
        if response.status_code == 200:
            products = response.json()
            for product in products:
                if product.get("stock", 0) > 0:
                    return product
        return None
    
    # ==================== GET /api/stock/losses/reasons ====================
    
    def test_get_loss_reasons(self):
        """Test getting loss reasons - should return list of valid reasons"""
        headers = self.get_auth_headers(self.admin_creds)
        response = requests.get(f"{BASE_URL}/api/stock/losses/reasons", headers=headers)
        
        assert response.status_code == 200
        reasons = response.json()
        assert isinstance(reasons, list)
        assert len(reasons) > 0
        
        # Check expected reasons exist
        reason_codes = [r["code"] for r in reasons]
        assert "breakage" in reason_codes
        assert "expiry" in reason_codes
        assert "theft" in reason_codes
        assert "counting_error" in reason_codes
        assert "other" in reason_codes
        
        # Check structure
        for reason in reasons:
            assert "code" in reason
            assert "label" in reason
        
        print(f"✓ GET /api/stock/losses/reasons - Found {len(reasons)} reasons")
    
    # ==================== POST /api/stock/losses ====================
    
    def test_declare_loss_as_admin(self):
        """Test admin can declare a loss"""
        headers = self.get_auth_headers(self.admin_creds)
        product = self.get_product_with_stock(headers)
        
        if not product:
            pytest.skip("No product with stock available")
        
        params = {
            "product_id": product["id"],
            "quantity": 1,
            "reason": "breakage",
            "reason_details": "Test casse admin"
        }
        
        response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "loss_id" in data
        assert data.get("status") == "pending"
        assert data.get("quantity") == 1
        
        print(f"✓ POST /api/stock/losses (admin) - Loss declared: {data.get('loss_id')}")
        return data.get("loss_id")
    
    def test_declare_loss_as_pharmacien(self):
        """Test pharmacien can declare a loss"""
        headers = self.get_auth_headers(self.pharmacien_creds)
        product = self.get_product_with_stock(headers)
        
        if not product:
            pytest.skip("No product with stock available")
        
        params = {
            "product_id": product["id"],
            "quantity": 1,
            "reason": "expiry",
            "reason_details": "Test péremption pharmacien"
        }
        
        response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("status") == "pending"
        
        print(f"✓ POST /api/stock/losses (pharmacien) - Loss declared")
    
    def test_declare_loss_as_caissier(self):
        """Test caissier can declare a loss"""
        headers = self.get_auth_headers(self.caissier_creds)
        product = self.get_product_with_stock(headers)
        
        if not product:
            pytest.skip("No product with stock available")
        
        params = {
            "product_id": product["id"],
            "quantity": 1,
            "reason": "counting_error",
            "reason_details": "Test erreur comptage caissier"
        }
        
        response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("status") == "pending"
        
        print(f"✓ POST /api/stock/losses (caissier) - Loss declared")
    
    def test_declare_loss_invalid_reason(self):
        """Test declaring loss with invalid reason fails"""
        headers = self.get_auth_headers(self.admin_creds)
        product = self.get_product_with_stock(headers)
        
        if not product:
            pytest.skip("No product with stock available")
        
        params = {
            "product_id": product["id"],
            "quantity": 1,
            "reason": "invalid_reason"
        }
        
        response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=headers)
        
        assert response.status_code == 400
        print(f"✓ POST /api/stock/losses (invalid reason) - Correctly rejected")
    
    def test_declare_loss_exceeds_stock(self):
        """Test declaring loss exceeding stock fails"""
        headers = self.get_auth_headers(self.admin_creds)
        product = self.get_product_with_stock(headers)
        
        if not product:
            pytest.skip("No product with stock available")
        
        params = {
            "product_id": product["id"],
            "quantity": product["stock"] + 100,  # Exceeds stock
            "reason": "breakage"
        }
        
        response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=headers)
        
        assert response.status_code == 400
        print(f"✓ POST /api/stock/losses (exceeds stock) - Correctly rejected")
    
    def test_declare_loss_invalid_product(self):
        """Test declaring loss for invalid product fails"""
        headers = self.get_auth_headers(self.admin_creds)
        
        params = {
            "product_id": "invalid-product-id",
            "quantity": 1,
            "reason": "breakage"
        }
        
        response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=headers)
        
        assert response.status_code == 404
        print(f"✓ POST /api/stock/losses (invalid product) - Correctly rejected")
    
    # ==================== GET /api/stock/losses/pending ====================
    
    def test_get_pending_losses(self):
        """Test getting pending losses"""
        headers = self.get_auth_headers(self.admin_creds)
        response = requests.get(f"{BASE_URL}/api/stock/losses/pending", headers=headers)
        
        assert response.status_code == 200
        losses = response.json()
        assert isinstance(losses, list)
        
        # Check structure if there are pending losses
        if len(losses) > 0:
            loss = losses[0]
            assert "id" in loss
            assert "product_id" in loss
            assert "product_name" in loss
            assert "quantity" in loss
            assert "reason" in loss
            assert "status" in loss
            assert loss["status"] == "pending"
        
        print(f"✓ GET /api/stock/losses/pending - Found {len(losses)} pending losses")
        return losses
    
    # ==================== POST /api/stock/losses/{id}/validate ====================
    
    def test_validate_loss_as_admin(self):
        """Test admin can validate a loss"""
        headers = self.get_auth_headers(self.admin_creds)
        
        # First create a loss to validate
        product = self.get_product_with_stock(headers)
        if not product:
            pytest.skip("No product with stock available")
        
        # Declare a loss
        params = {
            "product_id": product["id"],
            "quantity": 1,
            "reason": "breakage",
            "reason_details": "Test validation"
        }
        declare_response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=headers)
        assert declare_response.status_code == 200
        loss_id = declare_response.json().get("loss_id")
        
        # Validate the loss
        validate_params = {"action": "validate"}
        response = requests.post(
            f"{BASE_URL}/api/stock/losses/{loss_id}/validate",
            params=validate_params,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("action") == "validated"
        # Verify stock was updated (stock_after should be less than stock_before)
        assert data.get("stock_after") < data.get("stock_before")
        
        print(f"✓ POST /api/stock/losses/{loss_id}/validate (admin) - Loss validated, stock updated")
    
    def test_reject_loss_as_admin(self):
        """Test admin can reject a loss"""
        headers = self.get_auth_headers(self.admin_creds)
        
        # First create a loss to reject
        product = self.get_product_with_stock(headers)
        if not product:
            pytest.skip("No product with stock available")
        
        # Declare a loss
        params = {
            "product_id": product["id"],
            "quantity": 1,
            "reason": "theft",
            "reason_details": "Test rejection"
        }
        declare_response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=headers)
        assert declare_response.status_code == 200
        loss_id = declare_response.json().get("loss_id")
        
        # Reject the loss
        reject_params = {"action": "reject", "rejection_reason": "Insufficient evidence"}
        response = requests.post(
            f"{BASE_URL}/api/stock/losses/{loss_id}/validate",
            params=reject_params,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert data.get("action") == "rejected"
        
        print(f"✓ POST /api/stock/losses/{loss_id}/validate (reject) - Loss rejected")
    
    def test_validate_loss_as_pharmacien_fails(self):
        """Test pharmacien cannot validate a loss (admin only)"""
        admin_headers = self.get_auth_headers(self.admin_creds)
        pharmacien_headers = self.get_auth_headers(self.pharmacien_creds)
        
        # First create a loss as admin
        product = self.get_product_with_stock(admin_headers)
        if not product:
            pytest.skip("No product with stock available")
        
        params = {
            "product_id": product["id"],
            "quantity": 1,
            "reason": "breakage"
        }
        declare_response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=admin_headers)
        assert declare_response.status_code == 200
        loss_id = declare_response.json().get("loss_id")
        
        # Try to validate as pharmacien
        validate_params = {"action": "validate"}
        response = requests.post(
            f"{BASE_URL}/api/stock/losses/{loss_id}/validate",
            params=validate_params,
            headers=pharmacien_headers
        )
        
        assert response.status_code == 403
        print(f"✓ POST /api/stock/losses/{loss_id}/validate (pharmacien) - Correctly rejected (403)")
    
    def test_validate_loss_as_caissier_fails(self):
        """Test caissier cannot validate a loss (admin only)"""
        admin_headers = self.get_auth_headers(self.admin_creds)
        caissier_headers = self.get_auth_headers(self.caissier_creds)
        
        # First create a loss as admin
        product = self.get_product_with_stock(admin_headers)
        if not product:
            pytest.skip("No product with stock available")
        
        params = {
            "product_id": product["id"],
            "quantity": 1,
            "reason": "breakage"
        }
        declare_response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=admin_headers)
        assert declare_response.status_code == 200
        loss_id = declare_response.json().get("loss_id")
        
        # Try to validate as caissier
        validate_params = {"action": "validate"}
        response = requests.post(
            f"{BASE_URL}/api/stock/losses/{loss_id}/validate",
            params=validate_params,
            headers=caissier_headers
        )
        
        assert response.status_code == 403
        print(f"✓ POST /api/stock/losses/{loss_id}/validate (caissier) - Correctly rejected (403)")
    
    def test_reject_without_reason_fails(self):
        """Test rejecting without reason fails"""
        headers = self.get_auth_headers(self.admin_creds)
        
        # First create a loss
        product = self.get_product_with_stock(headers)
        if not product:
            pytest.skip("No product with stock available")
        
        params = {
            "product_id": product["id"],
            "quantity": 1,
            "reason": "breakage"
        }
        declare_response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=headers)
        assert declare_response.status_code == 200
        loss_id = declare_response.json().get("loss_id")
        
        # Try to reject without reason
        reject_params = {"action": "reject"}
        response = requests.post(
            f"{BASE_URL}/api/stock/losses/{loss_id}/validate",
            params=reject_params,
            headers=headers
        )
        
        assert response.status_code == 400
        print(f"✓ POST /api/stock/losses/{loss_id}/validate (reject without reason) - Correctly rejected")
    
    # ==================== GET /api/stock/losses/stats ====================
    
    def test_get_losses_stats(self):
        """Test getting loss statistics"""
        headers = self.get_auth_headers(self.admin_creds)
        response = requests.get(f"{BASE_URL}/api/stock/losses/stats", params={"period": "month"}, headers=headers)
        
        assert response.status_code == 200
        stats = response.json()
        
        # Check structure
        assert "period" in stats
        assert "total_losses" in stats
        assert "total_quantity" in stats
        assert "total_value" in stats
        assert "pending_count" in stats
        assert "by_reason" in stats
        
        print(f"✓ GET /api/stock/losses/stats - Stats retrieved: {stats.get('total_losses')} losses, {stats.get('pending_count')} pending")
    
    # ==================== GET /api/stock/losses/history ====================
    
    def test_get_losses_history(self):
        """Test getting loss history"""
        headers = self.get_auth_headers(self.admin_creds)
        response = requests.get(f"{BASE_URL}/api/stock/losses/history", headers=headers)
        
        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)
        
        # Check structure if there are entries
        if len(history) > 0:
            entry = history[0]
            assert "id" in entry
            assert "product_id" in entry
            assert "quantity" in entry
            assert "reason" in entry
            assert "status" in entry
        
        print(f"✓ GET /api/stock/losses/history - Found {len(history)} entries")
    
    def test_get_losses_history_with_filters(self):
        """Test getting loss history with filters"""
        headers = self.get_auth_headers(self.admin_creds)
        
        # Filter by status
        response = requests.get(
            f"{BASE_URL}/api/stock/losses/history",
            params={"status": "validated"},
            headers=headers
        )
        
        assert response.status_code == 200
        history = response.json()
        
        # All entries should be validated
        for entry in history:
            assert entry.get("status") == "validated"
        
        print(f"✓ GET /api/stock/losses/history (filtered) - Found {len(history)} validated entries")
    
    # ==================== Stock Update Verification ====================
    
    def test_stock_decreases_after_validation(self):
        """Test that product stock decreases after loss validation"""
        headers = self.get_auth_headers(self.admin_creds)
        
        # Get a product with stock
        product = self.get_product_with_stock(headers)
        if not product:
            pytest.skip("No product with stock available")
        
        loss_quantity = 2
        
        # Declare a loss
        params = {
            "product_id": product["id"],
            "quantity": loss_quantity,
            "reason": "breakage",
            "reason_details": "Test stock decrease"
        }
        declare_response = requests.post(f"{BASE_URL}/api/stock/losses", params=params, headers=headers)
        assert declare_response.status_code == 200
        loss_id = declare_response.json().get("loss_id")
        
        # Validate the loss
        validate_params = {"action": "validate"}
        validate_response = requests.post(
            f"{BASE_URL}/api/stock/losses/{loss_id}/validate",
            params=validate_params,
            headers=headers
        )
        assert validate_response.status_code == 200
        
        # Verify stock decreased from the validation response
        data = validate_response.json()
        assert data.get("stock_after") == data.get("stock_before") - loss_quantity
        
        print(f"✓ Stock verification - Stock decreased from {data.get('stock_before')} to {data.get('stock_after')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
