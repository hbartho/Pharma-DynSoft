#!/usr/bin/env python3
"""
Test Sale Number Integration in Returns
Tests the integration of sale_number and return_number fields in the returns system.
"""

import requests
import json
import sys
from datetime import datetime

class SaleReturnNumberTester:
    def __init__(self, base_url="https://pharmamgmt.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_items = {
            'products': [],
            'sales': [],
            'returns': []
        }

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")

    def api_call(self, method, endpoint, data=None, expected_status=200):
        """Make API call with authentication"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                try:
                    error_detail = response.json()
                    return False, {"error": error_detail, "status": response.status_code}
                except:
                    return False, {"error": response.text, "status": response.status_code}

        except Exception as e:
            return False, {"error": str(e)}

    def login(self):
        """Login with admin credentials"""
        print("🔐 Logging in as admin...")
        success, response = self.api_call(
            "POST", 
            "auth/login", 
            {"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            user_data = response.get('user', {})
            employee_code = user_data.get('employee_code', 'N/A')
            self.log_test(
                "Admin login successful", 
                True, 
                f"Employee code: {employee_code}"
            )
            return True
        else:
            self.log_test("Admin login failed", False, str(response))
            return False

    def create_test_product(self):
        """Create a test product for sales"""
        print("\n📦 Creating test product...")
        product_data = {
            "name": "Test Médicament Retour",
            "barcode": "RET123456",
            "description": "Médicament pour test de retour",
            "price": 25.50,
            "stock": 100,
            "min_stock": 10,
            "category": "Test"
        }
        
        success, response = self.api_call("POST", "products", product_data)
        if success and 'id' in response:
            product_id = response['id']
            self.created_items['products'].append(product_id)
            self.log_test(
                "Test product created", 
                True, 
                f"Product ID: {product_id}, Stock: {response.get('stock')}"
            )
            return product_id
        else:
            self.log_test("Test product creation failed", False, str(response))
            return None

    def test_create_sale_with_number(self, product_id):
        """Test 1: Create a new sale and verify sale_number format"""
        print("\n🛒 Test 1: Create Sale with Sale Number")
        
        sale_data = {
            "items": [
                {
                    "product_id": product_id,
                    "name": "Test Médicament Retour",
                    "price": 25.50,
                    "quantity": 3
                }
            ],
            "total": 76.50,
            "payment_method": "carte"
        }
        
        success, response = self.api_call("POST", "sales", sale_data)
        if success and 'id' in response:
            sale_id = response['id']
            sale_number = response.get('sale_number')
            employee_code = response.get('employee_code')
            
            self.created_items['sales'].append(sale_id)
            
            # Verify sale_number format (VNT-XXXX)
            if sale_number and sale_number.startswith('VNT-') and len(sale_number) >= 7:
                self.log_test(
                    "Sale created with correct sale_number format", 
                    True, 
                    f"Sale ID: {sale_id}, Sale Number: {sale_number}, Employee: {employee_code}"
                )
            else:
                self.log_test(
                    "Sale created but sale_number format incorrect", 
                    False, 
                    f"Expected VNT-XXXX format, got: {sale_number}"
                )
                return None
            
            # Verify employee_code is present
            if employee_code and employee_code != 'N/A':
                self.log_test(
                    "Sale includes employee_code", 
                    True, 
                    f"Employee code: {employee_code}"
                )
            else:
                self.log_test(
                    "Sale missing employee_code", 
                    False, 
                    f"Employee code: {employee_code}"
                )
            
            return sale_id, sale_number
        else:
            self.log_test("Sale creation failed", False, str(response))
            return None

    def test_create_return_with_sale_number(self, sale_id, expected_sale_number):
        """Test 2: Create a return and verify it includes sale_number"""
        print("\n↩️ Test 2: Create Return with Sale Number Reference")
        
        return_data = {
            "sale_id": sale_id,
            "items": [
                {
                    "product_id": self.created_items['products'][0],
                    "quantity": 1
                }
            ],
            "reason": "Produit défectueux - test retour"
        }
        
        success, response = self.api_call("POST", "returns", return_data)
        if success and 'id' in response:
            return_id = response['id']
            return_number = response.get('return_number')
            sale_number = response.get('sale_number')
            employee_code = response.get('employee_code')
            
            self.created_items['returns'].append(return_id)
            
            # Verify return_number format (RET-XXXX)
            if return_number and return_number.startswith('RET-') and len(return_number) >= 7:
                self.log_test(
                    "Return created with correct return_number format", 
                    True, 
                    f"Return Number: {return_number}"
                )
            else:
                self.log_test(
                    "Return created but return_number format incorrect", 
                    False, 
                    f"Expected RET-XXXX format, got: {return_number}"
                )
            
            # Verify sale_number matches original sale
            if sale_number == expected_sale_number:
                self.log_test(
                    "Return includes correct sale_number", 
                    True, 
                    f"Sale Number: {sale_number}"
                )
            else:
                self.log_test(
                    "Return sale_number mismatch", 
                    False, 
                    f"Expected: {expected_sale_number}, Got: {sale_number}"
                )
            
            # Verify employee_code is present
            if employee_code and employee_code != 'N/A':
                self.log_test(
                    "Return includes employee_code", 
                    True, 
                    f"Employee code: {employee_code}"
                )
            else:
                self.log_test(
                    "Return missing employee_code", 
                    False, 
                    f"Employee code: {employee_code}"
                )
            
            return return_id
        else:
            self.log_test("Return creation failed", False, str(response))
            return None

    def test_get_all_returns(self):
        """Test 3: Get all returns and verify sale_number field"""
        print("\n📋 Test 3: Get All Returns with Sale Numbers")
        
        success, response = self.api_call("GET", "returns")
        if success and isinstance(response, list):
            returns_count = len(response)
            self.log_test(
                "Retrieved returns list", 
                True, 
                f"Found {returns_count} returns"
            )
            
            # Check each return has sale_number field
            returns_with_sale_number = 0
            for ret in response:
                if ret.get('sale_number'):
                    returns_with_sale_number += 1
            
            if returns_with_sale_number == returns_count:
                self.log_test(
                    "All returns have sale_number field", 
                    True, 
                    f"{returns_with_sale_number}/{returns_count} returns have sale_number"
                )
            else:
                self.log_test(
                    "Some returns missing sale_number field", 
                    False, 
                    f"Only {returns_with_sale_number}/{returns_count} returns have sale_number"
                )
            
            return response
        else:
            self.log_test("Failed to retrieve returns", False, str(response))
            return []

    def test_get_operations_history(self):
        """Test 4: Get operations history and verify sale_number in returns"""
        print("\n📊 Test 4: Get Operations History with Sale Numbers")
        
        success, response = self.api_call("GET", "returns/history")
        if success and isinstance(response, list):
            operations_count = len(response)
            self.log_test(
                "Retrieved operations history", 
                True, 
                f"Found {operations_count} operations"
            )
            
            # Check returns in history have sale_number
            returns_in_history = [op for op in response if op.get('type') == 'return']
            returns_with_sale_number = [op for op in returns_in_history if op.get('sale_number')]
            
            if len(returns_with_sale_number) == len(returns_in_history):
                self.log_test(
                    "All returns in history have sale_number", 
                    True, 
                    f"{len(returns_with_sale_number)}/{len(returns_in_history)} returns have sale_number"
                )
            else:
                self.log_test(
                    "Some returns in history missing sale_number", 
                    False, 
                    f"Only {len(returns_with_sale_number)}/{len(returns_in_history)} returns have sale_number"
                )
            
            # Verify operation_number field exists
            operations_with_number = [op for op in response if op.get('operation_number')]
            if len(operations_with_number) == operations_count:
                self.log_test(
                    "All operations have operation_number field", 
                    True, 
                    f"{len(operations_with_number)}/{operations_count} operations have operation_number"
                )
            else:
                self.log_test(
                    "Some operations missing operation_number", 
                    False, 
                    f"Only {len(operations_with_number)}/{operations_count} operations have operation_number"
                )
            
            return response
        else:
            self.log_test("Failed to retrieve operations history", False, str(response))
            return []

    def test_get_returns_for_sale(self, sale_id):
        """Test 5: Get returns for specific sale and verify sale_number"""
        print("\n🔍 Test 5: Get Returns for Specific Sale")
        
        success, response = self.api_call("GET", f"returns/sale/{sale_id}")
        if success and isinstance(response, list):
            returns_count = len(response)
            self.log_test(
                "Retrieved returns for specific sale", 
                True, 
                f"Found {returns_count} returns for sale {sale_id}"
            )
            
            # Check all returns have sale_number
            returns_with_sale_number = [ret for ret in response if ret.get('sale_number')]
            if len(returns_with_sale_number) == returns_count:
                self.log_test(
                    "All returns for sale include sale_number", 
                    True, 
                    f"{len(returns_with_sale_number)}/{returns_count} returns have sale_number"
                )
            else:
                self.log_test(
                    "Some returns for sale missing sale_number", 
                    False, 
                    f"Only {len(returns_with_sale_number)}/{returns_count} returns have sale_number"
                )
            
            return response
        else:
            self.log_test("Failed to retrieve returns for sale", False, str(response))
            return []

    def cleanup(self):
        """Clean up created test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete returns first
        for return_id in self.created_items['returns']:
            success, _ = self.api_call("DELETE", f"returns/{return_id}")
            if success:
                print(f"   ✅ Deleted return {return_id}")
        
        # Delete sales (note: sales deletion might be disabled)
        for sale_id in self.created_items['sales']:
            success, response = self.api_call("DELETE", f"sales/{sale_id}")
            if success:
                print(f"   ✅ Deleted sale {sale_id}")
            else:
                print(f"   ⚠️ Could not delete sale {sale_id} (may be disabled)")
        
        # Delete products
        for product_id in self.created_items['products']:
            success, _ = self.api_call("DELETE", f"products/{product_id}")
            if success:
                print(f"   ✅ Deleted product {product_id}")

    def run_all_tests(self):
        """Run all sale number integration tests"""
        print("🚀 Starting Sale Number Integration in Returns Tests")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)
        
        # Login
        if not self.login():
            return False
        
        # Create test product
        product_id = self.create_test_product()
        if not product_id:
            return False
        
        # Test 1: Create sale with sale_number
        sale_result = self.test_create_sale_with_number(product_id)
        if not sale_result:
            return False
        
        sale_id, sale_number = sale_result
        
        # Test 2: Create return with sale_number reference
        return_id = self.test_create_return_with_sale_number(sale_id, sale_number)
        if not return_id:
            return False
        
        # Test 3: Get all returns
        self.test_get_all_returns()
        
        # Test 4: Get operations history
        self.test_get_operations_history()
        
        # Test 5: Get returns for specific sale
        self.test_get_returns_for_sale(sale_id)
        
        # Cleanup
        self.cleanup()
        
        # Print results
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("✅ All sale number integration tests passed!")
            return True
        else:
            print("❌ Some tests failed")
            return False

if __name__ == "__main__":
    tester = SaleReturnNumberTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)