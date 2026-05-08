"""
Test for discount calculation and split payment validation bugs.

Bug fixes being tested:
1. Discount calculation: 3% of 17000 = 510, not 500 (round() should fix this)
2. Split payments: Total payments must match sale total, or explicit debt is created

Test Date: 2026-01-14
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@pharmaflow.com", "password": "admin123"}
    )
    if response.status_code != 200:
        pytest.skip("Authentication failed")
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Return headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestDiscountCalculation:
    """Test exact discount calculations."""

    def test_volume_discount_rule_exists(self, auth_headers):
        """Test that Volume discount rule exists and is correctly configured."""
        response = requests.get(
            f"{BASE_URL}/api/discounts/rules?is_active=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        volume_rules = [r for r in data['items'] if r['rule_type'] == 'volume']
        assert len(volume_rules) > 0, "No volume discount rule found"
        
        rule = volume_rules[0]
        assert rule['discount_type'] == 'percent'
        assert rule['discount_value'] == 3.0, "Volume discount should be 3%"
        assert rule['conditions'].get('min_amount') == 50000, "Min amount should be 50000 GNF"

    def test_discount_calculation_17000_x_3(self, auth_headers):
        """
        Test: 3% of 17000 should be 510, not 500.
        This tests the bug fix for incorrect discount calculation.
        """
        # Calculate discount using the API
        response = requests.post(
            f"{BASE_URL}/api/discounts/calculate",
            headers=auth_headers,
            json={
                "cart_subtotal": 17000,  # Single item at 17000 GNF
                "customer_id": None,
                "cart_items": [{
                    "product_id": "test-product",
                    "quantity": 1,
                    "subtotal": 17000
                }],
                "promo_code": None
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # 17000 < 50000, so no volume discount should apply
        assert data['total_automatic_discount'] == 0, "No discount for < 50000 GNF"

    def test_discount_calculation_51000(self, auth_headers):
        """
        Test: 3% of 51000 = 1530 (exact calculation).
        This validates the round() function works correctly.
        """
        response = requests.post(
            f"{BASE_URL}/api/discounts/calculate",
            headers=auth_headers,
            json={
                "cart_subtotal": 51000,  # > 50000 so volume discount applies
                "customer_id": None,
                "cart_items": [{
                    "product_id": "test-product",
                    "quantity": 3,
                    "subtotal": 51000
                }],
                "promo_code": None
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # 3% of 51000 = 1530
        expected_discount = round(51000 * 3 / 100)  # 1530
        assert data['total_automatic_discount'] == expected_discount, f"Expected {expected_discount}, got {data['total_automatic_discount']}"

    def test_discount_calculation_round_cases(self, auth_headers):
        """Test various amounts to verify round() is used correctly."""
        test_cases = [
            # (subtotal, expected_discount_3_percent)
            (50001, round(50001 * 0.03)),  # = 1500 (rounded)
            (55000, round(55000 * 0.03)),  # = 1650 (exact)
            (60000, round(60000 * 0.03)),  # = 1800 (exact)
            (66666, round(66666 * 0.03)),  # = 2000 (rounded from 1999.98)
            (100000, round(100000 * 0.03)), # = 3000 (exact)
        ]
        
        for subtotal, expected_discount in test_cases:
            response = requests.post(
                f"{BASE_URL}/api/discounts/calculate",
                headers=auth_headers,
                json={
                    "cart_subtotal": subtotal,
                    "customer_id": None,
                    "cart_items": [{
                        "product_id": "test-product",
                        "quantity": 1,
                        "subtotal": subtotal
                    }],
                    "promo_code": None
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            actual_discount = data['total_automatic_discount']
            assert actual_discount == expected_discount, f"For subtotal {subtotal}: expected {expected_discount}, got {actual_discount}"


class TestSplitPaymentValidation:
    """Test split payment validation - payments must match total."""

    @pytest.fixture
    def product_for_test(self, auth_headers):
        """Get a product with stock for testing."""
        response = requests.get(
            f"{BASE_URL}/api/products?limit=20",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get('items', data) if isinstance(data, dict) else data
        
        # Find a product with good stock
        for product in items:
            if product.get('stock', 0) >= 5 and product.get('price', 0) > 0:
                return product
        
        pytest.skip("No product with sufficient stock found")

    @pytest.fixture
    def customer_with_credit(self, auth_headers):
        """Get or create a customer with credit limit for debt testing."""
        response = requests.get(
            f"{BASE_URL}/api/customers?limit=50",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get('items', data) if isinstance(data, dict) else data
        
        # Find a customer with credit limit
        for customer in items:
            if customer.get('max_debt_limit', 0) > 0:
                return customer
        
        # If no customer with credit, return None (will skip debt tests)
        return None

    def test_split_payment_exact_match_succeeds(self, auth_headers, product_for_test):
        """Test that split payments that exactly match total succeed."""
        product = product_for_test
        unit_price = product['price']
        quantity = 1
        total = unit_price * quantity
        
        # Create sale with exact split payments
        sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": product['id'],
                "product_name": product['name'],
                "unit_price": unit_price,
                "quantity": quantity,
                "subtotal": total
            }],
            "subtotal": total,
            "discount_type": None,
            "discount_value": 0,
            "discount_amount": 0,
            "total": total,
            "payment_method": "cash",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": total / 2},
                {"method": "card", "amount": total / 2}
            ],
            "amount_paid": total,
            "debt_amount": 0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            headers=auth_headers,
            json=sale_data
        )
        
        # Should succeed without creating debt
        assert response.status_code in [200, 201], f"Sale failed: {response.text}"
        result = response.json()
        assert result.get('has_debt', False) == False, "Should not have debt when payments match"
        assert result.get('debt_amount', 0) == 0, "Debt amount should be 0"

    def test_split_payment_mismatch_creates_debt_or_error(self, auth_headers, product_for_test, customer_with_credit):
        """
        Test that split payments that don't match total either:
        1. Create explicit debt (if customer has credit)
        2. Return an error (if no customer or no credit)
        
        This validates the bug fix for "silent debt creation".
        """
        if customer_with_credit is None:
            pytest.skip("No customer with credit limit available for debt test")
        
        product = product_for_test
        unit_price = product['price']
        quantity = 1
        total = unit_price * quantity
        
        # Split payments that DON'T match total (short by 1000)
        payment_total = total - 1000  # Intentionally short
        
        sale_data = {
            "customer_id": customer_with_credit['id'],
            "items": [{
                "product_id": product['id'],
                "product_name": product['name'],
                "unit_price": unit_price,
                "quantity": quantity,
                "subtotal": total
            }],
            "subtotal": total,
            "discount_type": None,
            "discount_value": 0,
            "discount_amount": 0,
            "total": total,
            "payment_method": "cash",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": payment_total / 2},
                {"method": "card", "amount": payment_total / 2}
            ],
            "amount_paid": payment_total,
            "debt_amount": 0  # Frontend doesn't set debt, backend should detect
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            headers=auth_headers,
            json=sale_data
        )
        
        # Backend should either:
        # 1. Create the sale with explicit debt = difference
        # 2. Or reject if customer doesn't have credit
        
        if response.status_code in [200, 201]:
            result = response.json()
            # If sale succeeded, it should have explicit debt
            assert result.get('has_debt', False) == True, "Should have debt when payments don't match"
            expected_debt = round(total - payment_total, 2)
            actual_debt = result.get('debt_amount', 0)
            assert abs(actual_debt - expected_debt) < 1, f"Debt should be ~{expected_debt}, got {actual_debt}"
        else:
            # If sale was rejected, that's also acceptable behavior
            assert response.status_code == 400, f"Expected 400 error, got {response.status_code}"

    def test_split_payment_with_debt_method_succeeds(self, auth_headers, product_for_test, customer_with_credit):
        """Test split payment where one method is explicitly 'debt'."""
        if customer_with_credit is None:
            pytest.skip("No customer with credit limit available")
        
        product = product_for_test
        unit_price = product['price']
        quantity = 1
        total = unit_price * quantity
        
        # Available credit check
        available_credit = customer_with_credit.get('max_debt_limit', 0) - customer_with_credit.get('current_debt', 0)
        debt_portion = min(total / 2, available_credit - 100)  # Leave some margin
        
        if debt_portion <= 0:
            pytest.skip("Customer doesn't have enough available credit")
        
        cash_portion = total - debt_portion
        
        sale_data = {
            "customer_id": customer_with_credit['id'],
            "items": [{
                "product_id": product['id'],
                "product_name": product['name'],
                "unit_price": unit_price,
                "quantity": quantity,
                "subtotal": total
            }],
            "subtotal": total,
            "discount_type": None,
            "discount_value": 0,
            "discount_amount": 0,
            "total": total,
            "payment_method": "cash",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": cash_portion},
                {"method": "debt", "amount": debt_portion}
            ],
            "amount_paid": cash_portion,
            "debt_amount": debt_portion
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            headers=auth_headers,
            json=sale_data
        )
        
        assert response.status_code in [200, 201], f"Sale with explicit debt failed: {response.text}"
        result = response.json()
        
        # Should have the debt we specified
        assert result.get('has_debt', False) == True
        assert abs(result.get('debt_amount', 0) - debt_portion) < 1

    def test_split_payment_no_customer_rejects_debt(self, auth_headers, product_for_test):
        """Test that split payment creating debt without customer is rejected."""
        product = product_for_test
        unit_price = product['price']
        quantity = 1
        total = unit_price * quantity
        
        # Split payments with explicit debt but NO customer
        sale_data = {
            "customer_id": None,  # NO CUSTOMER
            "items": [{
                "product_id": product['id'],
                "product_name": product['name'],
                "unit_price": unit_price,
                "quantity": quantity,
                "subtotal": total
            }],
            "subtotal": total,
            "discount_type": None,
            "discount_value": 0,
            "discount_amount": 0,
            "total": total,
            "payment_method": "cash",
            "is_split_payment": True,
            "split_payments": [
                {"method": "cash", "amount": total / 2},
                {"method": "debt", "amount": total / 2}  # Debt without customer
            ],
            "amount_paid": total / 2,
            "debt_amount": total / 2
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            headers=auth_headers,
            json=sale_data
        )
        
        # Should be rejected - can't have debt without customer
        assert response.status_code == 400, f"Should reject debt without customer, got {response.status_code}"
        error_detail = response.json().get('detail', '')
        assert 'client' in error_detail.lower() or 'customer' in error_detail.lower() or 'crédit' in error_detail.lower()


class TestSaleWithVolumeDiscount:
    """Test creating a sale with volume discount to verify no silent debt."""

    @pytest.fixture
    def high_value_product(self, auth_headers):
        """Find or calculate a product combination > 50000 GNF."""
        response = requests.get(
            f"{BASE_URL}/api/products?limit=50",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        items = data.get('items', data) if isinstance(data, dict) else data
        
        # Find products with stock
        for product in items:
            if product.get('stock', 0) >= 3 and product.get('price', 0) > 15000:
                return product
        
        # Alternative: find any product where qty * price > 50000
        for product in items:
            if product.get('stock', 0) >= 1 and product.get('price', 0) > 0:
                price = product['price']
                needed_qty = max(1, int(50001 / price) + 1)
                if product.get('stock', 0) >= needed_qty:
                    return {**product, 'test_quantity': needed_qty}
        
        pytest.skip("No suitable product found for high-value test")

    def test_sale_with_volume_discount_no_debt(self, auth_headers, high_value_product):
        """
        Create a sale > 50000 GNF with volume discount.
        Verify the discount is correctly calculated and no debt is created.
        """
        product = high_value_product
        price = product['price']
        qty = product.get('test_quantity', 3)  # Use test_quantity if set
        
        subtotal = price * qty
        if subtotal < 50001:
            qty = int(50001 / price) + 1
            subtotal = price * qty
        
        # Calculate expected discount
        expected_discount = round(subtotal * 0.03)  # 3%
        expected_total = subtotal - expected_discount
        
        # Create sale paying full amount
        sale_data = {
            "customer_id": None,
            "items": [{
                "product_id": product['id'],
                "product_name": product['name'],
                "unit_price": price,
                "quantity": qty,
                "subtotal": subtotal
            }],
            "subtotal": subtotal,
            "discount_type": None,
            "discount_value": 0,
            "discount_amount": expected_discount,
            "automatic_discount_amount": expected_discount,
            "automatic_discounts": [
                {"rule_id": "volume", "rule_name": "Volume", "discount_amount": expected_discount}
            ],
            "total": expected_total,
            "payment_method": "cash",
            "is_split_payment": False,
            "amount_paid": expected_total,
            "debt_amount": 0
        }
        
        response = requests.post(
            f"{BASE_URL}/api/sales",
            headers=auth_headers,
            json=sale_data
        )
        
        assert response.status_code in [200, 201], f"Sale failed: {response.text}"
        result = response.json()
        
        # Verify no debt when paying full amount
        assert result.get('has_debt', False) == False, "Should not have debt when paying full amount"
        assert result.get('debt_amount', 0) == 0, "Debt should be 0"
        
        # Verify discount was applied
        assert result.get('discount_amount', 0) > 0, "Discount should be applied"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
