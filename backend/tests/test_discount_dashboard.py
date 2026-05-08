"""
Test cases for discount rules and dashboard discount display
- Verifies 3 discount rules exist (Volume, Loyalty, Expiration)
- Verifies /api/reports/today-sales-by-payment returns discount_info
- Verifies discount_info structure with total_discount and discount_count
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDiscountRulesAPI:
    """Test discount rules endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_discount_rules_exist(self):
        """Test that 3 discount rules exist"""
        response = requests.get(
            f"{BASE_URL}/api/discounts/rules",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "items" in data
        assert "total" in data
        assert data["total"] == 3, f"Expected 3 rules, got {data['total']}"
        
        # Verify rule types
        rule_types = [r["rule_type"] for r in data["items"]]
        assert "volume" in rule_types, "Volume rule missing"
        assert "loyalty" in rule_types, "Loyalty rule missing"
        assert "expiration" in rule_types, "Expiration rule missing"
    
    def test_volume_discount_rule(self):
        """Test volume discount rule configuration"""
        response = requests.get(
            f"{BASE_URL}/api/discounts/rules",
            headers=self.headers
        )
        assert response.status_code == 200
        rules = response.json()["items"]
        
        volume_rule = next((r for r in rules if r["rule_type"] == "volume"), None)
        assert volume_rule is not None, "Volume rule not found"
        
        assert volume_rule["name"] == "Rabais Volume > 50000 GNF"
        assert volume_rule["discount_type"] == "percent"
        assert volume_rule["discount_value"] == 3
        assert volume_rule["is_active"] == True
        assert volume_rule["conditions"]["min_amount"] == 50000
    
    def test_loyalty_discount_rule(self):
        """Test loyalty discount rule configuration"""
        response = requests.get(
            f"{BASE_URL}/api/discounts/rules",
            headers=self.headers
        )
        assert response.status_code == 200
        rules = response.json()["items"]
        
        loyalty_rule = next((r for r in rules if r["rule_type"] == "loyalty"), None)
        assert loyalty_rule is not None, "Loyalty rule not found"
        
        assert loyalty_rule["name"] == "Fidélité Client"
        assert loyalty_rule["discount_type"] == "percent"
        assert loyalty_rule["discount_value"] == 5
        assert loyalty_rule["is_active"] == True
        assert loyalty_rule["conditions"]["min_purchases"] == 20
    
    def test_expiration_discount_rule(self):
        """Test expiration (proche péremption) discount rule configuration"""
        response = requests.get(
            f"{BASE_URL}/api/discounts/rules",
            headers=self.headers
        )
        assert response.status_code == 200
        rules = response.json()["items"]
        
        expiration_rule = next((r for r in rules if r["rule_type"] == "expiration"), None)
        assert expiration_rule is not None, "Expiration rule not found"
        
        assert "Péremption Proche" in expiration_rule["name"]
        assert expiration_rule["discount_type"] == "percent"
        assert expiration_rule["discount_value"] == 10
        assert expiration_rule["is_active"] == True
        assert expiration_rule["conditions"]["days_before_expiry"] == 30


class TestSalesByPaymentDiscountInfo:
    """Test today-sales-by-payment endpoint with discount_info"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_today_sales_by_payment_endpoint(self):
        """Test that endpoint returns 200"""
        response = requests.get(
            f"{BASE_URL}/api/reports/today-sales-by-payment",
            headers=self.headers
        )
        assert response.status_code == 200
    
    def test_response_has_discount_info(self):
        """Test that response includes discount_info field"""
        response = requests.get(
            f"{BASE_URL}/api/reports/today-sales-by-payment",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "discount_info" in data, "discount_info field missing from response"
    
    def test_discount_info_structure(self):
        """Test discount_info has required fields"""
        response = requests.get(
            f"{BASE_URL}/api/reports/today-sales-by-payment",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        discount_info = data["discount_info"]
        assert "total_discount" in discount_info, "total_discount field missing"
        assert "discount_count" in discount_info, "discount_count field missing"
        
        # Verify types
        assert isinstance(discount_info["total_discount"], (int, float))
        assert isinstance(discount_info["discount_count"], int)
    
    def test_discount_info_values_non_negative(self):
        """Test that discount values are non-negative"""
        response = requests.get(
            f"{BASE_URL}/api/reports/today-sales-by-payment",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        discount_info = data["discount_info"]
        assert discount_info["total_discount"] >= 0, "total_discount should be non-negative"
        assert discount_info["discount_count"] >= 0, "discount_count should be non-negative"
    
    def test_full_response_structure(self):
        """Test complete response structure"""
        response = requests.get(
            f"{BASE_URL}/api/reports/today-sales-by-payment",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "date" in data
        assert "total_sales" in data
        assert "total_revenue" in data
        assert "by_payment_method" in data
        assert "discount_info" in data
        
        # by_payment_method should be a list
        assert isinstance(data["by_payment_method"], list)
        
        # Each payment method should have expected fields
        for payment in data["by_payment_method"]:
            assert "method" in payment
            assert "label" in payment
            assert "count" in payment
            assert "total" in payment
    
    def test_date_parameter(self):
        """Test endpoint with date parameter"""
        response = requests.get(
            f"{BASE_URL}/api/reports/today-sales-by-payment?date=2026-02-13",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["date"] == "2026-02-13"
        assert "discount_info" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
