#!/usr/bin/env python3
"""
Test Return Delay Policy & Sale Numbers
Tests the return delay validation, sale numbers, and return numbers functionality
"""

import requests
import sys
import json
import os
from datetime import datetime, timedelta

class ReturnDelayPolicyTester:
    def __init__(self):
        # Get backend URL from environment
        self.base_url = os.getenv('REACT_APP_BACKEND_URL', 'https://pharmamgmt.preview.emergentagent.com')
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_items = {
            'sales': [],
            'returns': [],
            'products': []
        }

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
            response = None
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def login(self):
        """Login with admin credentials"""
        print("\n=== AUTHENTICATION ===")
        success, response = self.run_test(
            "Login with admin credentials",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   Token obtained: {self.token[:20]}...")
            print(f"   User: {response.get('user', {}).get('name', 'Unknown')}")
            print(f"   Employee Code: {response.get('user', {}).get('employee_code', 'N/A')}")
            return True
        return False

    def test_settings_return_delay(self):
        """Test 1: Settings - Return Delay Configuration"""
        print("\n=== TEST 1: SETTINGS - RETURN DELAY CONFIGURATION ===")
        
        # Get current settings
        success, settings = self.run_test(
            "GET /api/settings - Verify return_delay_days field exists",
            "GET",
            "settings",
            200
        )
        
        if success:
            if 'return_delay_days' in settings:
                current_delay = settings['return_delay_days']
                print(f"   ✅ return_delay_days field exists: {current_delay}")
            else:
                print(f"   ❌ return_delay_days field missing from settings")
                return False
        else:
            print(f"   ❌ Failed to get settings")
            return False
        
        # Update return delay to 5 days
        update_data = {
            "return_delay_days": 5
        }
        success, updated_settings = self.run_test(
            "PUT /api/settings - Update return_delay_days to 5",
            "PUT",
            "settings",
            200,
            data=update_data
        )
        
        if success:
            print(f"   ✅ Settings updated successfully")
        else:
            print(f"   ❌ Failed to update settings")
            return False
        
        # Verify the update was saved
        success, verify_settings = self.run_test(
            "GET /api/settings - Verify update was saved",
            "GET",
            "settings",
            200
        )
        
        if success:
            if verify_settings.get('return_delay_days') == 5:
                print(f"   ✅ return_delay_days correctly updated to: {verify_settings['return_delay_days']}")
            else:
                print(f"   ❌ return_delay_days not updated correctly: {verify_settings.get('return_delay_days')}")
                return False
        else:
            print(f"   ❌ Failed to verify settings update")
            return False
        
        # Reset to original value
        reset_data = {
            "return_delay_days": current_delay
        }
        self.run_test(
            "Reset return_delay_days to original value",
            "PUT",
            "settings",
            200,
            data=reset_data
        )
        
        return True

    def create_test_product(self):
        """Create a test product for sales"""
        product_data = {
            "name": "Test Médicament Retour",
            "barcode": "RET123456",
            "description": "Médicament pour test de retour",
            "price": 25.00,
            "stock": 100,
            "min_stock": 10,
            "category": "Test"
        }
        
        success, product = self.run_test(
            "Create test product for return tests",
            "POST",
            "products",
            200,
            data=product_data
        )
        
        if success and 'id' in product:
            self.created_items['products'].append(product['id'])
            print(f"   ✅ Created test product: {product['id']}")
            return product['id']
        else:
            print(f"   ❌ Failed to create test product")
            return None

    def test_return_eligibility_check(self):
        """Test 2: Return Eligibility Check"""
        print("\n=== TEST 2: RETURN ELIGIBILITY CHECK ===")
        
        # First create a sale to test eligibility
        product_id = self.create_test_product()
        if not product_id:
            return False
        
        # Create a sale
        sale_data = {
            "items": [
                {
                    "product_id": product_id,
                    "name": "Test Médicament Retour",
                    "price": 25.00,
                    "quantity": 2
                }
            ],
            "total": 50.00,
            "payment_method": "cash"
        }
        
        success, sale = self.run_test(
            "Create sale for eligibility test",
            "POST",
            "sales",
            200,
            data=sale_data
        )
        
        if success and 'id' in sale:
            sale_id = sale['id']
            self.created_items['sales'].append(sale_id)
            print(f"   ✅ Created test sale: {sale_id}")
            print(f"   ✅ Sale number: {sale.get('sale_number', 'N/A')}")
        else:
            print(f"   ❌ Failed to create test sale")
            return False
        
        # Check return eligibility for the recent sale
        success, eligibility = self.run_test(
            f"GET /api/returns/check-eligibility/{sale_id} - Check eligibility",
            "GET",
            f"returns/check-eligibility/{sale_id}",
            200
        )
        
        if success:
            required_fields = ['is_eligible', 'message', 'days_remaining', 'return_delay_days']
            for field in required_fields:
                if field in eligibility:
                    print(f"   ✅ Response has {field}: {eligibility[field]}")
                else:
                    print(f"   ❌ Response missing {field}")
                    return False
            
            if eligibility['is_eligible']:
                print(f"   ✅ Sale is eligible for return")
            else:
                print(f"   ⚠️ Sale not eligible: {eligibility['message']}")
        else:
            print(f"   ❌ Failed to check return eligibility")
            return False
        
        return True

    def test_create_return_within_delay(self):
        """Test 3: Create Return Within Delay"""
        print("\n=== TEST 3: CREATE RETURN WITHIN DELAY ===")
        
        # Use the sale created in previous test
        if not self.created_items['sales']:
            print("   ❌ No sales available for return test")
            return False
        
        sale_id = self.created_items['sales'][0]
        product_id = self.created_items['products'][0]
        
        # Create a return for the sale immediately (should succeed)
        return_data = {
            "sale_id": sale_id,
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 1
                }
            ],
            "reason": "Produit défectueux - test"
        }
        
        success, return_obj = self.run_test(
            "Create return within delay period",
            "POST",
            "returns",
            200,
            data=return_data
        )
        
        if success and 'id' in return_obj:
            self.created_items['returns'].append(return_obj['id'])
            print(f"   ✅ Return created successfully: {return_obj['id']}")
            print(f"   ✅ Return number: {return_obj.get('return_number', 'N/A')}")
            print(f"   ✅ Sale number: {return_obj.get('sale_number', 'N/A')}")
            print(f"   ✅ Employee code: {return_obj.get('employee_code', 'N/A')}")
            print(f"   ✅ Total refund: {return_obj.get('total_refund', 0)}")
            return True
        else:
            print(f"   ❌ Failed to create return within delay")
            return False

    def test_return_delay_enforcement(self):
        """Test 4: Return Delay Enforcement"""
        print("\n=== TEST 4: RETURN DELAY ENFORCEMENT ===")
        
        # Set return_delay_days to 0 (disable returns)
        disable_data = {
            "return_delay_days": 0
        }
        success, _ = self.run_test(
            "Set return_delay_days to 0 (disable returns)",
            "PUT",
            "settings",
            200,
            data=disable_data
        )
        
        if not success:
            print(f"   ❌ Failed to disable returns")
            return False
        
        # Try to create a return for the recent sale (should fail)
        if not self.created_items['sales']:
            print("   ❌ No sales available for return test")
            return False
        
        sale_id = self.created_items['sales'][0]
        product_id = self.created_items['products'][0]
        
        return_data = {
            "sale_id": sale_id,
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 1
                }
            ],
            "reason": "Test avec délai désactivé"
        }
        
        success, error_response = self.run_test(
            "Try to create return with delay disabled (should fail)",
            "POST",
            "returns",
            400,
            data=return_data
        )
        
        if success:
            print(f"   ✅ Return correctly blocked with appropriate error")
            print(f"   ✅ Error message: {error_response.get('detail', 'No detail')}")
        else:
            print(f"   ❌ Return should have been blocked")
            return False
        
        # Reset return_delay_days back to 3
        reset_data = {
            "return_delay_days": 3
        }
        success, _ = self.run_test(
            "Reset return_delay_days back to 3",
            "PUT",
            "settings",
            200,
            data=reset_data
        )
        
        if success:
            print(f"   ✅ Return delay reset to 3 days")
        else:
            print(f"   ❌ Failed to reset return delay")
            return False
        
        return True

    def test_sales_api_sale_numbers(self):
        """Test 5: Sales API - Sale Numbers"""
        print("\n=== TEST 5: SALES API - SALE NUMBERS ===")
        
        # Get all sales
        success, sales = self.run_test(
            "GET /api/sales - Verify sale numbers",
            "GET",
            "sales",
            200
        )
        
        if success:
            print(f"   ✅ Retrieved {len(sales)} sales")
            
            sales_with_numbers = 0
            sales_with_employee_code = 0
            
            for sale in sales:
                if 'sale_number' in sale and sale['sale_number']:
                    sales_with_numbers += 1
                    if sale['sale_number'].startswith('VNT-'):
                        print(f"   ✅ Sale has correct format: {sale['sale_number']}")
                    else:
                        print(f"   ⚠️ Sale number format unexpected: {sale['sale_number']}")
                
                if 'employee_code' in sale and sale['employee_code']:
                    sales_with_employee_code += 1
            
            print(f"   ✅ Sales with sale_number: {sales_with_numbers}/{len(sales)}")
            print(f"   ✅ Sales with employee_code: {sales_with_employee_code}/{len(sales)}")
            
            if sales_with_numbers == len(sales):
                print(f"   ✅ All sales have sale_number field")
            else:
                print(f"   ⚠️ Some sales missing sale_number field")
            
            return True
        else:
            print(f"   ❌ Failed to get sales")
            return False

    def test_returns_api_return_numbers(self):
        """Test 6: Returns API - Return Numbers and Sale Reference"""
        print("\n=== TEST 6: RETURNS API - RETURN NUMBERS AND SALE REFERENCE ===")
        
        # Get all returns
        success, returns = self.run_test(
            "GET /api/returns - Verify return numbers and sale references",
            "GET",
            "returns",
            200
        )
        
        if success:
            print(f"   ✅ Retrieved {len(returns)} returns")
            
            returns_with_numbers = 0
            returns_with_sale_numbers = 0
            
            for return_obj in returns:
                if 'return_number' in return_obj and return_obj['return_number']:
                    returns_with_numbers += 1
                    if return_obj['return_number'].startswith('RET-'):
                        print(f"   ✅ Return has correct format: {return_obj['return_number']}")
                    else:
                        print(f"   ⚠️ Return number format unexpected: {return_obj['return_number']}")
                
                if 'sale_number' in return_obj and return_obj['sale_number']:
                    returns_with_sale_numbers += 1
                    print(f"   ✅ Return references sale: {return_obj['return_number']} → {return_obj['sale_number']}")
            
            print(f"   ✅ Returns with return_number: {returns_with_numbers}/{len(returns)}")
            print(f"   ✅ Returns with sale_number: {returns_with_sale_numbers}/{len(returns)}")
            
            if returns_with_numbers == len(returns):
                print(f"   ✅ All returns have return_number field")
            else:
                print(f"   ⚠️ Some returns missing return_number field")
            
            if returns_with_sale_numbers == len(returns):
                print(f"   ✅ All returns have sale_number field")
            else:
                print(f"   ⚠️ Some returns missing sale_number field")
            
            return True
        else:
            print(f"   ❌ Failed to get returns")
            return False

    def test_operations_history(self):
        """Test 7: Operations History"""
        print("\n=== TEST 7: OPERATIONS HISTORY ===")
        
        # Get operations history
        success, history = self.run_test(
            "GET /api/returns/history - Verify operations history",
            "GET",
            "returns/history",
            200
        )
        
        if success:
            print(f"   ✅ Retrieved {len(history)} operations")
            
            sales_count = 0
            returns_count = 0
            operations_with_numbers = 0
            returns_with_sale_ref = 0
            
            for operation in history:
                if operation.get('type') == 'sale':
                    sales_count += 1
                    if 'operation_number' in operation and operation['operation_number'].startswith('VNT-'):
                        operations_with_numbers += 1
                        print(f"   ✅ Sale operation: {operation['operation_number']}")
                
                elif operation.get('type') == 'return':
                    returns_count += 1
                    if 'operation_number' in operation and operation['operation_number'].startswith('RET-'):
                        operations_with_numbers += 1
                        print(f"   ✅ Return operation: {operation['operation_number']}")
                    
                    if 'sale_number' in operation and operation['sale_number']:
                        returns_with_sale_ref += 1
                        print(f"   ✅ Return references sale: {operation['operation_number']} → {operation['sale_number']}")
            
            print(f"   ✅ Sales in history: {sales_count}")
            print(f"   ✅ Returns in history: {returns_count}")
            print(f"   ✅ Operations with numbers: {operations_with_numbers}/{len(history)}")
            print(f"   ✅ Returns with sale reference: {returns_with_sale_ref}/{returns_count}")
            
            if operations_with_numbers == len(history):
                print(f"   ✅ All operations have operation_number field")
            else:
                print(f"   ⚠️ Some operations missing operation_number field")
            
            if returns_count > 0 and returns_with_sale_ref == returns_count:
                print(f"   ✅ All returns have sale_number reference")
            else:
                print(f"   ⚠️ Some returns missing sale_number reference")
            
            return True
        else:
            print(f"   ❌ Failed to get operations history")
            return False

    def cleanup(self):
        """Clean up created test items"""
        print("\n=== CLEANUP ===")
        
        # Note: We don't delete sales as they are protected
        # Just clean up products if needed
        for product_id in self.created_items['products']:
            self.run_test(f"Delete test product {product_id}", "DELETE", f"products/{product_id}", 200)

    def run_all_tests(self):
        """Run all return delay policy and sale numbers tests"""
        print("🚀 Starting Return Delay Policy & Sale Numbers Tests")
        print("🏥 DynSoft Pharma - Return Policy & Numbering System Testing")
        print(f"Base URL: {self.base_url}")
        
        # Authentication is required
        if not self.login():
            print("❌ Login failed, stopping tests")
            return False
        
        # Run all tests
        tests = [
            self.test_settings_return_delay,
            self.test_return_eligibility_check,
            self.test_create_return_within_delay,
            self.test_return_delay_enforcement,
            self.test_sales_api_sale_numbers,
            self.test_returns_api_return_numbers,
            self.test_operations_history
        ]
        
        test_results = []
        for test in tests:
            try:
                result = test()
                test_results.append(result)
            except Exception as e:
                print(f"❌ Test failed with exception: {e}")
                test_results.append(False)
        
        # Cleanup
        self.cleanup()
        
        # Print results
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        
        print(f"\n📊 Test Results: {self.tests_passed}/{self.tests_run} API calls passed")
        print(f"📊 Feature Tests: {passed_tests}/{total_tests} test suites passed")
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if passed_tests == total_tests:
            print("✅ All return delay policy and sale numbers features working correctly")
        else:
            print("❌ Some features failed testing")
        
        return passed_tests == total_tests


if __name__ == "__main__":
    tester = ReturnDelayPolicyTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)