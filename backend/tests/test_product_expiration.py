import requests
import sys
import json
from datetime import datetime, timedelta
import uuid

class ProductExpirationTester:
    def __init__(self, base_url="https://pharmamgmt.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_items = {
            'products': [],
            'sales': []
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

    def test_login(self):
        """Test login with admin credentials"""
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
            self.user_data = response.get('user', {})
            print(f"   Token obtained: {self.token[:20]}...")
            print(f"   User: {self.user_data.get('name', 'Unknown')}")
            print(f"   Role: {self.user_data.get('role', 'Unknown')}")
            return True
        return False

    def test_sale_number_format(self):
        """Test 1: Sale Number Format - VNT-XXXXXXXX (8 chars from UUID)"""
        print("\n=== TEST 1: SALE NUMBER FORMAT ===")
        
        # Generate unique product name
        unique_id = str(uuid.uuid4())[:8]
        
        # First create a product to sell
        product_data = {
            "name": f"Test Product for Sale {unique_id}",
            "barcode": f"SALE{unique_id}",
            "description": "Product for sale number test",
            "price": 10.0,
            "stock": 100,
            "min_stock": 10
        }
        success, new_product = self.run_test("Create product for sale", "POST", "products", 200, product_data)
        if not success or 'id' not in new_product:
            print("❌ Failed to create product for sale test")
            return False
        
        product_id = new_product['id']
        self.created_items['products'].append(product_id)
        
        # Create a sale
        sale_data = {
            "items": [
                {
                    "product_id": product_id,
                    "name": f"Test Product for Sale {unique_id}",
                    "price": 10.0,
                    "quantity": 1
                }
            ],
            "total": 10.0,
            "payment_method": "cash"
        }
        success, new_sale = self.run_test("Create sale with VNT-XXXXXXXX format", "POST", "sales", 200, sale_data)
        if success and 'id' in new_sale:
            sale_id = new_sale['id']
            self.created_items['sales'].append(sale_id)
            sale_number = new_sale.get('sale_number', '')
            
            # Verify sale number format: VNT-XXXXXXXX (8 uppercase chars)
            if sale_number.startswith('VNT-') and len(sale_number) == 12:
                suffix = sale_number[4:]  # Get the part after VNT-
                if len(suffix) == 8 and suffix.isupper() and suffix.isalnum():
                    print(f"   ✅ Sale number format correct: {sale_number}")
                    print(f"   ✅ Format: VNT-{suffix} (8 uppercase chars)")
                    return True
                else:
                    print(f"   ❌ Sale number suffix incorrect: {suffix} (should be 8 uppercase alphanumeric)")
            else:
                print(f"   ❌ Sale number format incorrect: {sale_number} (should be VNT-XXXXXXXX)")
        
        return False

    def test_product_with_expiration_date(self):
        """Test 2: Product with Expiration Date"""
        print("\n=== TEST 2: PRODUCT WITH EXPIRATION DATE ===")
        
        # Generate unique product name
        unique_id = str(uuid.uuid4())[:8]
        
        # Create product with expiration date (10 days from now)
        expiration_date = (datetime.now() + timedelta(days=10)).isoformat()
        product_data = {
            "name": f"Test Product with Expiration {unique_id}",
            "barcode": f"EXP{unique_id}",
            "description": "Product with expiration date",
            "price": 15.0,
            "stock": 50,
            "min_stock": 5,
            "expiration_date": expiration_date
        }
        success, new_product = self.run_test("Create product with expiration date", "POST", "products", 200, product_data)
        if success and 'id' in new_product:
            product_id = new_product['id']
            self.created_items['products'].append(product_id)
            
            # Get the product and verify expiration_date is stored
            success, retrieved_product = self.run_test("Get product with expiration date", "GET", f"products/{product_id}", 200)
            if success:
                stored_expiration = retrieved_product.get('expiration_date')
                if stored_expiration:
                    print(f"   ✅ Product expiration date stored: {stored_expiration}")
                    print(f"   ✅ Original date: {expiration_date}")
                    return True
                else:
                    print(f"   ❌ Product expiration date not stored")
            else:
                print(f"   ❌ Failed to retrieve product")
        else:
            print(f"   ❌ Failed to create product with expiration date")
        
        return False

    def test_product_alerts_endpoint(self):
        """Test 3: Product Alerts Endpoint"""
        print("\n=== TEST 3: PRODUCT ALERTS ENDPOINT ===")
        
        success, alerts = self.run_test("Get product alerts", "GET", "products/alerts", 200)
        if success:
            # Verify response structure
            required_keys = ['low_stock', 'near_expiration', 'expired']
            for key in required_keys:
                if key not in alerts:
                    print(f"   ❌ Missing key in alerts response: {key}")
                    return False
            
            # Verify low_stock structure
            low_stock = alerts['low_stock']
            if 'count' in low_stock and 'threshold' in low_stock and 'products' in low_stock:
                print(f"   ✅ low_stock structure correct: count={low_stock['count']}, threshold={low_stock['threshold']}")
            else:
                print(f"   ❌ low_stock structure incorrect: {low_stock}")
                return False
            
            # Verify near_expiration structure
            near_expiration = alerts['near_expiration']
            if 'count' in near_expiration and 'alert_days' in near_expiration and 'products' in near_expiration:
                print(f"   ✅ near_expiration structure correct: count={near_expiration['count']}, alert_days={near_expiration['alert_days']}")
            else:
                print(f"   ❌ near_expiration structure incorrect: {near_expiration}")
                return False
            
            # Verify expired structure
            expired = alerts['expired']
            if 'count' in expired and 'products' in expired:
                print(f"   ✅ expired structure correct: count={expired['count']}")
            else:
                print(f"   ❌ expired structure incorrect: {expired}")
                return False
            
            print(f"   ✅ Product alerts endpoint working correctly")
            return True
        else:
            print(f"   ❌ Failed to get product alerts")
        
        return False

    def test_expiration_alert_days_setting(self):
        """Test 4: Expiration Alert Days Setting"""
        print("\n=== TEST 4: EXPIRATION ALERT DAYS SETTING ===")
        
        # Get current settings and verify expiration_alert_days exists
        success, settings = self.run_test("Get settings - verify expiration_alert_days", "GET", "settings", 200)
        if not success:
            print("   ❌ Failed to get settings")
            return False
        
        initial_alert_days = settings.get('expiration_alert_days', 30)
        print(f"   ✅ Current expiration_alert_days: {initial_alert_days}")
        
        # Update expiration_alert_days to 15
        update_data = {"expiration_alert_days": 15}
        success, updated_settings = self.run_test("Update expiration_alert_days to 15", "PUT", "settings", 200, update_data)
        if not success:
            print("   ❌ Failed to update expiration_alert_days")
            return False
        
        if updated_settings.get('expiration_alert_days') == 15:
            print(f"   ✅ expiration_alert_days updated to 15")
        else:
            print(f"   ❌ expiration_alert_days not updated correctly: {updated_settings.get('expiration_alert_days')}")
            return False
        
        # Generate unique product name
        unique_id = str(uuid.uuid4())[:8]
        
        # Create a product expiring in 20 days
        expiration_date_20_days = (datetime.now() + timedelta(days=20)).isoformat()
        product_data = {
            "name": f"Test Product 20 Days Expiry {unique_id}",
            "barcode": f"EXP20D{unique_id}",
            "description": "Product expiring in 20 days",
            "price": 12.0,
            "stock": 30,
            "min_stock": 5,
            "expiration_date": expiration_date_20_days
        }
        success, product_20_days = self.run_test("Create product expiring in 20 days", "POST", "products", 200, product_data)
        if not success:
            print("   ❌ Failed to create product expiring in 20 days")
            return False
        
        product_20_id = product_20_days['id']
        self.created_items['products'].append(product_20_id)
        
        # Get alerts - product should NOT be in near_expiration (20 > 15)
        success, alerts = self.run_test("Get alerts - 20 days > 15 alert days", "GET", "products/alerts", 200)
        if success:
            near_expiration_products = alerts['near_expiration']['products']
            product_in_alerts = any(p['id'] == product_20_id for p in near_expiration_products)
            if not product_in_alerts:
                print(f"   ✅ Product NOT in near_expiration (20 days > 15 alert days)")
            else:
                print(f"   ❌ Product should NOT be in near_expiration (20 days > 15 alert days)")
                return False
        
        # Update expiration_alert_days to 25
        update_data = {"expiration_alert_days": 25}
        success, updated_settings = self.run_test("Update expiration_alert_days to 25", "PUT", "settings", 200, update_data)
        if not success:
            print("   ❌ Failed to update expiration_alert_days to 25")
            return False
        
        # Get alerts - product should now BE in near_expiration (20 < 25)
        success, alerts = self.run_test("Get alerts - 20 days < 25 alert days", "GET", "products/alerts", 200)
        if success:
            near_expiration_products = alerts['near_expiration']['products']
            product_in_alerts = any(p['id'] == product_20_id for p in near_expiration_products)
            if product_in_alerts:
                print(f"   ✅ Product IS in near_expiration (20 days < 25 alert days)")
            else:
                print(f"   ❌ Product should BE in near_expiration (20 days < 25 alert days)")
                return False
        
        # Restore original setting
        restore_data = {"expiration_alert_days": initial_alert_days}
        self.run_test("Restore original expiration_alert_days", "PUT", "settings", 200, restore_data)
        
        print(f"   ✅ Expiration alert days setting working correctly")
        return True

    def test_product_sorting(self):
        """Test 5: Product Sorting Priority"""
        print("\n=== TEST 5: PRODUCT SORTING PRIORITY ===")
        
        # Create products with different priorities
        now = datetime.now()
        unique_id = str(uuid.uuid4())[:8]
        
        # 1. Low stock product (needs restock)
        low_stock_product = {
            "name": f"A Low Stock Product {unique_id}",
            "barcode": f"LOWST{unique_id}",
            "description": "Product with low stock",
            "price": 20.0,
            "stock": 2,  # Below min_stock
            "min_stock": 10
        }
        success, low_stock = self.run_test("Create low stock product", "POST", "products", 200, low_stock_product)
        if success:
            self.created_items['products'].append(low_stock['id'])
        
        # 2. Expired product
        expired_product = {
            "name": f"B Expired Product {unique_id}",
            "barcode": f"EXPIR{unique_id}",
            "description": "Product that is expired",
            "price": 25.0,
            "stock": 50,
            "min_stock": 10,
            "expiration_date": (now - timedelta(days=5)).isoformat()  # Expired 5 days ago
        }
        success, expired = self.run_test("Create expired product", "POST", "products", 200, expired_product)
        if success:
            self.created_items['products'].append(expired['id'])
        
        # 3. Near expiration product
        near_expiration_product = {
            "name": f"C Near Expiration Product {unique_id}",
            "barcode": f"NEARX{unique_id}",
            "description": "Product near expiration",
            "price": 30.0,
            "stock": 40,
            "min_stock": 10,
            "expiration_date": (now + timedelta(days=5)).isoformat()  # Expires in 5 days
        }
        success, near_exp = self.run_test("Create near expiration product", "POST", "products", 200, near_expiration_product)
        if success:
            self.created_items['products'].append(near_exp['id'])
        
        # 4. Normal product (alphabetical)
        normal_product = {
            "name": f"D Normal Product {unique_id}",
            "barcode": f"NORML{unique_id}",
            "description": "Normal product",
            "price": 35.0,
            "stock": 100,
            "min_stock": 10
        }
        success, normal = self.run_test("Create normal product", "POST", "products", 200, normal_product)
        if success:
            self.created_items['products'].append(normal['id'])
        
        # Get products and verify sorting
        success, products = self.run_test("Get products with priority sorting", "GET", "products", 200)
        if success:
            # Find our test products in the list
            test_products = []
            for product in products:
                if product['id'] in [low_stock['id'], expired['id'], near_exp['id'], normal['id']]:
                    test_products.append(product)
            
            if len(test_products) == 4:
                # Verify sorting order
                product_names = [p['name'] for p in test_products]
                print(f"   Product order: {product_names}")
                
                # Expected order: Low stock > Expired > Near expiration > Normal (alphabetical)
                expected_order = [
                    f"A Low Stock Product {unique_id}",    # Low stock first
                    f"B Expired Product {unique_id}",      # Then expired
                    f"C Near Expiration Product {unique_id}",  # Then near expiration
                    f"D Normal Product {unique_id}"        # Then alphabetical
                ]
                
                # Check if our products appear in the correct relative order
                positions = {}
                for i, product in enumerate(products):
                    if product['name'] in expected_order:
                        positions[product['name']] = i
                
                # Verify low stock comes before others
                low_stock_pos = positions.get(f"A Low Stock Product {unique_id}", 999)
                expired_pos = positions.get(f"B Expired Product {unique_id}", 999)
                near_exp_pos = positions.get(f"C Near Expiration Product {unique_id}", 999)
                normal_pos = positions.get(f"D Normal Product {unique_id}", 999)
                
                if (low_stock_pos < expired_pos < near_exp_pos < normal_pos):
                    print(f"   ✅ Product sorting correct: Low stock({low_stock_pos}) > Expired({expired_pos}) > Near expiration({near_exp_pos}) > Normal({normal_pos})")
                    return True
                else:
                    print(f"   ❌ Product sorting incorrect: positions {positions}")
                    print(f"   Expected: Low stock < Expired < Near expiration < Normal")
            else:
                print(f"   ❌ Not all test products found: {len(test_products)}/4")
        else:
            print(f"   ❌ Failed to get products")
        
        return False

    def cleanup_created_items(self):
        """Clean up created test items"""
        print("\n=== CLEANUP ===")
        
        # Delete created products
        for product_id in self.created_items.get('products', []):
            self.run_test(f"Delete product {product_id}", "DELETE", f"products/{product_id}", 200)

    def run_all_tests(self):
        """Run all product expiration and sorting tests"""
        print("🚀 Starting Product Expiration & Sorting Enhancement Tests")
        print(f"Base URL: {self.base_url}")
        print("Test Credentials: admin@pharmaflow.com / admin123")
        
        # Authentication is required for all tests
        if not self.test_login():
            print("❌ Login failed, stopping tests")
            return False
        
        # Run all tests
        test_results = []
        test_results.append(self.test_sale_number_format())
        test_results.append(self.test_product_with_expiration_date())
        test_results.append(self.test_product_alerts_endpoint())
        test_results.append(self.test_expiration_alert_days_setting())
        test_results.append(self.test_product_sorting())
        
        # Cleanup
        self.cleanup_created_items()
        
        # Print results
        print(f"\n📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        passed_tests = sum(test_results)
        total_tests = len(test_results)
        print(f"Feature Tests: {passed_tests}/{total_tests} passed")
        
        if passed_tests == total_tests:
            print("✅ All Product Expiration & Sorting Enhancement tests passed!")
        else:
            print("❌ Some tests failed")
        
        return passed_tests == total_tests


if __name__ == "__main__":
    tester = ProductExpirationTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)