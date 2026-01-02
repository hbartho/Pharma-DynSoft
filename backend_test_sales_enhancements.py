#!/usr/bin/env python3
"""
Backend API Testing for Sales Page Enhancements
Tests the backend functionality for:
1. Return quantity validation
2. Sales API with sale numbers
3. Returns API with return numbers and sale references
4. Return eligibility checking
"""

import requests
import json
from datetime import datetime, timedelta
import sys

class SalesEnhancementsAPITester:
    def __init__(self, base_url="https://pharmflow-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_items = {
            'sales': [],
            'returns': [],
            'products': []
        }

    def login(self, email, password):
        """Login and get JWT token"""
        url = f"{self.base_url}/api/auth/login"
        data = {"email": email, "password": password}
        
        print(f"🔐 Logging in as {email}...")
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            result = response.json()
            self.token = result['access_token']
            self.user_data = result['user']
            print(f"✅ Login successful - Employee Code: {self.user_data.get('employee_code', 'N/A')}")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers)
            else:
                print(f"❌ Unsupported method: {method}")
                return None

            print(f"   Status: {response.status_code}")
            
            if response.status_code == expected_status:
                print(f"✅ {name} - PASSED")
                self.tests_passed += 1
                try:
                    return response.json()
                except:
                    return response.text
            else:
                print(f"❌ {name} - FAILED")
                print(f"   Expected: {expected_status}, Got: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ {name} - ERROR: {str(e)}")
            return None

    def test_get_products(self):
        """Get products to use in sales tests"""
        print("\n" + "="*60)
        print("🛍️  TESTING: Get Products for Sales")
        print("="*60)
        
        products = self.run_test(
            "Get Products",
            "GET",
            "products",
            200
        )
        
        if products and len(products) > 0:
            # Filter products with stock > 0
            available_products = [p for p in products if p.get('stock', 0) > 0]
            if available_products:
                print(f"✅ Found {len(available_products)} products with stock")
                return available_products[:2]  # Return first 2 products
            else:
                print("⚠️  No products with stock found")
                return []
        return []

    def test_create_sale(self, products):
        """Test creating a sale with sale number generation"""
        print("\n" + "="*60)
        print("💰 TESTING: Create Sale with Sale Number")
        print("="*60)
        
        if not products or len(products) < 1:
            print("❌ No products available for sale creation")
            return None
            
        # Create sale with first product
        product = products[0]
        sale_data = {
            "items": [
                {
                    "product_id": product['id'],
                    "name": product['name'],
                    "quantity": 2,
                    "price": product.get('selling_price', 1000)
                }
            ],
            "total": product.get('selling_price', 1000) * 2,
            "payment_method": "cash"
        }
        
        sale = self.run_test(
            "Create Sale",
            "POST",
            "sales",
            200,
            sale_data
        )
        
        if sale:
            print(f"✅ Sale created with ID: {sale['id']}")
            print(f"✅ Sale Number: {sale.get('sale_number', 'N/A')}")
            print(f"✅ Employee Code: {sale.get('employee_code', 'N/A')}")
            self.created_items['sales'].append(sale)
            return sale
        return None

    def test_get_sales(self):
        """Test getting all sales with sale numbers"""
        print("\n" + "="*60)
        print("📋 TESTING: Get All Sales with Sale Numbers")
        print("="*60)
        
        sales = self.run_test(
            "Get All Sales",
            "GET",
            "sales",
            200
        )
        
        if sales:
            print(f"✅ Retrieved {len(sales)} sales")
            
            # Check if all sales have sale_number
            sales_with_numbers = [s for s in sales if s.get('sale_number')]
            print(f"✅ Sales with sale_number: {len(sales_with_numbers)}/{len(sales)}")
            
            # Check sale number format (VNT-XXXXXXXX)
            valid_format_count = 0
            for sale in sales_with_numbers:
                sale_number = sale.get('sale_number', '')
                if sale_number.startswith('VNT-') and len(sale_number) == 12:
                    valid_format_count += 1
            
            print(f"✅ Sales with valid VNT-XXXXXXXX format: {valid_format_count}/{len(sales_with_numbers)}")
            return sales
        return []

    def test_return_quantity_validation(self, sale):
        """Test return quantity validation - core backend functionality"""
        print("\n" + "="*60)
        print("🔄 TESTING: Return Quantity Validation")
        print("="*60)
        
        if not sale:
            print("❌ No sale available for return testing")
            return False
            
        # Get the first item from the sale
        if not sale.get('items') or len(sale['items']) == 0:
            print("❌ Sale has no items")
            return False
            
        sale_item = sale['items'][0]
        sold_quantity = sale_item['quantity']
        
        print(f"📦 Testing return for product: {sale_item['name']}")
        print(f"📦 Original quantity sold: {sold_quantity}")
        
        # Test 1: Try to return MORE than sold quantity (should fail)
        print("\n🧪 Test 1: Return MORE than sold quantity")
        invalid_return_data = {
            "sale_id": sale['id'],
            "items": [
                {
                    "product_id": sale_item['product_id'],
                    "quantity": sold_quantity + 5  # More than sold
                }
            ],
            "reason": "Test return - invalid quantity"
        }
        
        invalid_return = self.run_test(
            "Return More Than Sold (Should Fail)",
            "POST",
            "returns",
            400,  # Should fail with 400
            invalid_return_data
        )
        
        if invalid_return is None:
            print("✅ Correctly rejected return with excessive quantity")
        else:
            print("❌ Should have rejected return with excessive quantity")
            
        # Test 2: Return valid quantity (should succeed)
        print("\n🧪 Test 2: Return valid quantity")
        valid_quantity = min(sold_quantity, 1)  # Return 1 or less if sold quantity is 1
        valid_return_data = {
            "sale_id": sale['id'],
            "items": [
                {
                    "product_id": sale_item['product_id'],
                    "quantity": valid_quantity
                }
            ],
            "reason": "Test return - valid quantity"
        }
        
        valid_return = self.run_test(
            "Return Valid Quantity",
            "POST",
            "returns",
            200,
            valid_return_data
        )
        
        if valid_return:
            print(f"✅ Return created with ID: {valid_return['id']}")
            print(f"✅ Return Number: {valid_return.get('return_number', 'N/A')}")
            print(f"✅ Sale Number Reference: {valid_return.get('sale_number', 'N/A')}")
            print(f"✅ Employee Code: {valid_return.get('employee_code', 'N/A')}")
            self.created_items['returns'].append(valid_return)
            
            # Test 3: Try to return remaining + more (should fail)
            if sold_quantity > valid_quantity:
                print("\n🧪 Test 3: Return remaining quantity + more (should fail)")
                remaining_quantity = sold_quantity - valid_quantity
                excessive_return_data = {
                    "sale_id": sale['id'],
                    "items": [
                        {
                            "product_id": sale_item['product_id'],
                            "quantity": remaining_quantity + 1  # More than remaining
                        }
                    ],
                    "reason": "Test return - excessive remaining"
                }
                
                excessive_return = self.run_test(
                    "Return More Than Remaining (Should Fail)",
                    "POST",
                    "returns",
                    400,
                    excessive_return_data
                )
                
                if excessive_return is None:
                    print("✅ Correctly rejected return exceeding remaining quantity")
                else:
                    print("❌ Should have rejected return exceeding remaining quantity")
            
            return True
        else:
            print("❌ Failed to create valid return")
            return False

    def test_return_eligibility_check(self, sale):
        """Test return eligibility checking endpoint"""
        print("\n" + "="*60)
        print("⏰ TESTING: Return Eligibility Check")
        print("="*60)
        
        if not sale:
            print("❌ No sale available for eligibility testing")
            return False
            
        eligibility = self.run_test(
            "Check Return Eligibility",
            "GET",
            f"returns/check-eligibility/{sale['id']}",
            200
        )
        
        if eligibility:
            print(f"✅ Eligibility check response:")
            print(f"   - Sale ID: {eligibility.get('sale_id')}")
            print(f"   - Is Eligible: {eligibility.get('is_eligible')}")
            print(f"   - Message: {eligibility.get('message')}")
            print(f"   - Days Remaining: {eligibility.get('days_remaining')}")
            print(f"   - Return Delay Days: {eligibility.get('return_delay_days')}")
            return True
        return False

    def test_get_returns(self):
        """Test getting all returns with sale number references"""
        print("\n" + "="*60)
        print("📋 TESTING: Get All Returns with Sale Numbers")
        print("="*60)
        
        returns = self.run_test(
            "Get All Returns",
            "GET",
            "returns",
            200
        )
        
        if returns:
            print(f"✅ Retrieved {len(returns)} returns")
            
            # Check if all returns have return_number
            returns_with_numbers = [r for r in returns if r.get('return_number')]
            print(f"✅ Returns with return_number: {len(returns_with_numbers)}/{len(returns)}")
            
            # Check if all returns have sale_number reference
            returns_with_sale_numbers = [r for r in returns if r.get('sale_number')]
            print(f"✅ Returns with sale_number reference: {len(returns_with_sale_numbers)}/{len(returns)}")
            
            # Check return number format (RET-XXXXXXXX)
            valid_format_count = 0
            for ret in returns_with_numbers:
                return_number = ret.get('return_number', '')
                if return_number.startswith('RET-') and len(return_number) == 12:
                    valid_format_count += 1
            
            print(f"✅ Returns with valid RET-XXXXXXXX format: {valid_format_count}/{len(returns_with_numbers)}")
            return returns
        return []

    def test_operations_history(self):
        """Test operations history endpoint"""
        print("\n" + "="*60)
        print("📚 TESTING: Operations History")
        print("="*60)
        
        history = self.run_test(
            "Get Operations History",
            "GET",
            "returns/history",
            200
        )
        
        if history:
            print(f"✅ Retrieved {len(history)} operations")
            
            # Separate sales and returns
            sales_in_history = [op for op in history if op.get('type') == 'sale']
            returns_in_history = [op for op in history if op.get('type') == 'return']
            
            print(f"✅ Sales in history: {len(sales_in_history)}")
            print(f"✅ Returns in history: {len(returns_in_history)}")
            
            # Check if all operations have operation_number
            ops_with_numbers = [op for op in history if op.get('operation_number')]
            print(f"✅ Operations with operation_number: {len(ops_with_numbers)}/{len(history)}")
            
            # Check if all returns have sale_number reference
            returns_with_sale_ref = [op for op in returns_in_history if op.get('sale_number')]
            print(f"✅ Returns with sale_number reference: {len(returns_with_sale_ref)}/{len(returns_in_history)}")
            
            return history
        return []

    def run_all_tests(self):
        """Run all sales enhancement tests"""
        print("🚀 Starting Sales Page Enhancements Backend API Tests")
        print("="*80)
        
        # Login
        if not self.login("admin@pharmaflow.com", "admin123"):
            print("❌ Failed to login. Cannot proceed with tests.")
            return False
        
        # Get products for testing
        products = self.test_get_products()
        
        # Test sales API
        sale = self.test_create_sale(products)
        self.test_get_sales()
        
        # Test return quantity validation (core functionality)
        if sale:
            self.test_return_quantity_validation(sale)
            self.test_return_eligibility_check(sale)
        
        # Test returns API
        self.test_get_returns()
        self.test_operations_history()
        
        # Print summary
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("⚠️  SOME TESTS FAILED")
            return False

if __name__ == "__main__":
    tester = SalesEnhancementsAPITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)