import requests
import sys
import json
from datetime import datetime

class PharmaFlowAPITester:
    def __init__(self, base_url="https://medmanager-43.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_items = {
            'products': [],
            'customers': [],
            'suppliers': [],
            'prescriptions': [],
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
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
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
        """Test login with demo credentials"""
        print("\n=== AUTHENTICATION TESTS ===")
        success, response = self.run_test(
            "Login with demo credentials",
            "POST",
            "auth/login",
            200,
            data={"email": "demo@pharmaflow.com", "password": "demo123"}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_data = response.get('user', {})
            print(f"   Token obtained: {self.token[:20]}...")
            print(f"   User: {self.user_data.get('name', 'Unknown')}")
            return True
        return False

    def test_authentication_security(self):
        """Test authentication security with invalid token"""
        print("\n=== AUTHENTICATION SECURITY TESTS ===")
        
        # Store current valid token
        valid_token = self.token
        
        # Test with invalid token
        self.token = "invalid_token_12345"
        success, response = self.run_test("Test invalid token", "GET", "suppliers", 401)
        if success:
            print("   ✅ Invalid token correctly rejected with 401")
        else:
            print("   ❌ Invalid token should return 401")
        
        # Test with no token
        self.token = None
        success, response = self.run_test("Test no token", "GET", "suppliers", 401)
        if success:
            print("   ✅ No token correctly rejected with 401")
        else:
            print("   ❌ No token should return 401")
        
        # Restore valid token
        self.token = valid_token
        print("   ✅ Valid token restored")

    def test_products_endpoints(self):
        """Test all product-related endpoints"""
        print("\n=== PRODUCTS TESTS ===")
        
        # Get products
        success, products = self.run_test("Get products", "GET", "products", 200)
        if success:
            print(f"   Found {len(products)} products")
        
        # Create product
        product_data = {
            "name": "Test Paracétamol",
            "barcode": "TEST123456",
            "description": "Médicament de test",
            "price": 5.99,
            "stock": 100,
            "min_stock": 10,
            "category": "Antalgique"
        }
        success, new_product = self.run_test("Create product", "POST", "products", 200, product_data)
        if success and 'id' in new_product:
            self.created_items['products'].append(new_product['id'])
            print(f"   Created product ID: {new_product['id']}")
            
            # Get specific product
            self.run_test("Get specific product", "GET", f"products/{new_product['id']}", 200)
            
            # Update product
            update_data = {**product_data, "price": 6.99, "stock": 90}
            self.run_test("Update product", "PUT", f"products/{new_product['id']}", 200, update_data)
        
        # Search products
        self.run_test("Search products", "GET", "products/search?q=test", 200)

    def test_customers_endpoints(self):
        """Test customer endpoints"""
        print("\n=== CUSTOMERS TESTS ===")
        
        # Get customers
        success, customers = self.run_test("Get customers", "GET", "customers", 200)
        if success:
            print(f"   Found {len(customers)} customers")
        
        # Create customer
        customer_data = {
            "name": "Jean Dupont",
            "phone": "0123456789",
            "email": "jean.dupont@test.com",
            "address": "123 Rue de Test, 75001 Paris"
        }
        success, new_customer = self.run_test("Create customer", "POST", "customers", 200, customer_data)
        if success and 'id' in new_customer:
            self.created_items['customers'].append(new_customer['id'])
            print(f"   Created customer ID: {new_customer['id']}")

    def test_suppliers_endpoints(self):
        """Test supplier CRUD endpoints comprehensively"""
        print("\n=== SUPPLIERS CRUD TESTS ===")
        
        # 1. Get suppliers (initial list)
        success, suppliers = self.run_test("Get suppliers", "GET", "suppliers", 200)
        if success:
            print(f"   Found {len(suppliers)} suppliers initially")
            initial_count = len(suppliers)
        else:
            print("❌ Failed to get initial suppliers list")
            return False
        
        # 2. Create supplier with exact test data from requirements
        supplier_data = {
            "name": "Test Fournisseur",
            "phone": "+33 6 12 34 56 78",
            "email": "test@fournisseur.com",
            "address": "123 Rue Test, Paris"
        }
        success, new_supplier = self.run_test("Create supplier", "POST", "suppliers", 200, supplier_data)
        if success and 'id' in new_supplier:
            supplier_id = new_supplier['id']
            self.created_items['suppliers'].append(supplier_id)
            print(f"   ✅ Created supplier ID: {supplier_id}")
            print(f"   ✅ Supplier name: {new_supplier.get('name')}")
            print(f"   ✅ Supplier email: {new_supplier.get('email')}")
            
            # 3. Verify supplier appears in list
            success, updated_suppliers = self.run_test("Get suppliers after creation", "GET", "suppliers", 200)
            if success:
                if len(updated_suppliers) == initial_count + 1:
                    print(f"   ✅ Supplier count increased from {initial_count} to {len(updated_suppliers)}")
                else:
                    print(f"   ❌ Expected {initial_count + 1} suppliers, found {len(updated_suppliers)}")
            
            # 4. Get specific supplier
            success, specific_supplier = self.run_test("Get specific supplier", "GET", f"suppliers/{supplier_id}", 200)
            if success:
                print(f"   ✅ Retrieved specific supplier: {specific_supplier.get('name')}")
            
            # 5. Update supplier (change name as per requirements)
            update_data = {
                "name": "Test Fournisseur Modifié",
                "phone": "+33 6 12 34 56 78",
                "email": "test@fournisseur.com",
                "address": "123 Rue Test, Paris"
            }
            success, updated_supplier = self.run_test("Update supplier", "PUT", f"suppliers/{supplier_id}", 200, update_data)
            if success:
                print(f"   ✅ Updated supplier name to: {updated_supplier.get('name')}")
                
                # Verify the update
                success, verify_update = self.run_test("Verify supplier update", "GET", f"suppliers/{supplier_id}", 200)
                if success and verify_update.get('name') == "Test Fournisseur Modifié":
                    print(f"   ✅ Update verified: {verify_update.get('name')}")
                else:
                    print(f"   ❌ Update verification failed")
            
            # 6. Delete supplier
            success, delete_response = self.run_test("Delete supplier", "DELETE", f"suppliers/{supplier_id}", 200)
            if success:
                print(f"   ✅ Supplier deleted successfully")
                
                # 7. Verify supplier no longer exists
                success, final_suppliers = self.run_test("Get suppliers after deletion", "GET", "suppliers", 200)
                if success:
                    if len(final_suppliers) == initial_count:
                        print(f"   ✅ Supplier count back to original: {len(final_suppliers)}")
                    else:
                        print(f"   ❌ Expected {initial_count} suppliers after deletion, found {len(final_suppliers)}")
                
                # 8. Verify 404 when trying to get deleted supplier
                success, not_found = self.run_test("Verify supplier deleted (should 404)", "GET", f"suppliers/{supplier_id}", 404)
                if success:
                    print(f"   ✅ Deleted supplier correctly returns 404")
                else:
                    print(f"   ❌ Deleted supplier should return 404")
                
                # Remove from cleanup list since already deleted
                if supplier_id in self.created_items['suppliers']:
                    self.created_items['suppliers'].remove(supplier_id)
            
            return True
        else:
            print("❌ Failed to create supplier")
            return False

    def test_prescriptions_endpoints(self):
        """Test prescription endpoints"""
        print("\n=== PRESCRIPTIONS TESTS ===")
        
        # Get prescriptions
        success, prescriptions = self.run_test("Get prescriptions", "GET", "prescriptions", 200)
        if success:
            print(f"   Found {len(prescriptions)} prescriptions")
        
        # Create prescription (need a customer first)
        if self.created_items['customers']:
            prescription_data = {
                "customer_id": self.created_items['customers'][0],
                "doctor_name": "Dr. Martin",
                "medications": [
                    {"name": "Paracétamol", "dosage": "500mg", "quantity": 20}
                ],
                "notes": "Prescription de test",
                "status": "pending"
            }
            success, new_prescription = self.run_test("Create prescription", "POST", "prescriptions", 200, prescription_data)
            if success and 'id' in new_prescription:
                self.created_items['prescriptions'].append(new_prescription['id'])
                print(f"   Created prescription ID: {new_prescription['id']}")
                
                # Update prescription status
                self.run_test("Update prescription status", "PUT", f"prescriptions/{new_prescription['id']}?status=fulfilled", 200)

    def test_sales_endpoints(self):
        """Test sales endpoints"""
        print("\n=== SALES TESTS ===")
        
        # Get sales
        success, sales = self.run_test("Get sales", "GET", "sales", 200)
        if success:
            print(f"   Found {len(sales)} sales")
        
        # Create sale (need products)
        if self.created_items['products']:
            sale_data = {
                "customer_id": self.created_items['customers'][0] if self.created_items['customers'] else None,
                "items": [
                    {
                        "product_id": self.created_items['products'][0],
                        "name": "Test Paracétamol",
                        "price": 5.99,
                        "quantity": 2
                    }
                ],
                "total": 11.98,
                "payment_method": "cash"
            }
            success, new_sale = self.run_test("Create sale", "POST", "sales", 200, sale_data)
            if success and 'id' in new_sale:
                self.created_items['sales'].append(new_sale['id'])
                print(f"   Created sale ID: {new_sale['id']}")

    def test_stock_endpoints(self):
        """Test stock management endpoints"""
        print("\n=== STOCK TESTS ===")
        
        # Get stock movements
        self.run_test("Get stock movements", "GET", "stock", 200)
        
        # Get stock alerts
        self.run_test("Get stock alerts", "GET", "stock/alerts", 200)
        
        # Create stock movement
        if self.created_items['products']:
            stock_data = {
                "product_id": self.created_items['products'][0],
                "type": "in",
                "quantity": 50,
                "reason": "Réapprovisionnement test"
            }
            self.run_test("Create stock movement", "POST", "stock", 200, stock_data)

    def test_reports_endpoints(self):
        """Test reports endpoints"""
        print("\n=== REPORTS TESTS ===")
        
        # Get dashboard stats
        success, dashboard = self.run_test("Get dashboard stats", "GET", "reports/dashboard", 200)
        if success:
            print(f"   Dashboard stats: {dashboard}")
        
        # Get sales report
        success, sales_report = self.run_test("Get sales report", "GET", "reports/sales?days=7", 200)
        if success:
            print(f"   Sales report period: {sales_report.get('period_days', 'N/A')} days")

    def test_sync_endpoints(self):
        """Test sync endpoints"""
        print("\n=== SYNC TESTS ===")
        
        # Test sync pull
        self.run_test("Sync pull", "GET", "sync/pull", 200)
        
        # Test sync push
        sync_data = {
            "changes": [
                {
                    "type": "product",
                    "action": "update",
                    "payload": {
                        "id": "test-sync-id",
                        "name": "Sync Test Product",
                        "price": 10.0,
                        "stock": 5
                    }
                }
            ]
        }
        self.run_test("Sync push", "POST", "sync/push", 200, sync_data)

    def cleanup_created_items(self):
        """Clean up created test items"""
        print("\n=== CLEANUP ===")
        
        # Delete created products
        for product_id in self.created_items['products']:
            self.run_test(f"Delete product {product_id}", "DELETE", f"products/{product_id}", 200)

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting PharmaFlow API Tests")
        print(f"Base URL: {self.base_url}")
        
        # Authentication is required for all other tests
        if not self.test_login():
            print("❌ Login failed, stopping tests")
            return False
        
        # Test authentication security
        self.test_authentication_security()
        
        # Run all endpoint tests
        self.test_products_endpoints()
        self.test_customers_endpoints()
        self.test_suppliers_endpoints()
        self.test_prescriptions_endpoints()
        self.test_sales_endpoints()
        self.test_stock_endpoints()
        self.test_reports_endpoints()
        self.test_sync_endpoints()
        
        # Cleanup
        self.cleanup_created_items()
        
        # Print results
        print(f"\n📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = PharmaFlowAPITester()
    
    # Check if we should run only supplier tests
    if len(sys.argv) > 1 and sys.argv[1] == "--suppliers-only":
        success = tester.run_supplier_crud_tests_only()
    else:
        success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())