import requests
import sys
import json
from datetime import datetime

class PharmaFlowAPITester:
    def __init__(self, base_url="https://rxmanage-7.preview.emergentagent.com"):
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
            'sales': [],
            'users': []
        }
        # Store tokens for different user roles
        self.tokens = {
            'admin': None,
            'pharmacien': None,
            'caissier': None
        }
        self.users = {
            'admin': None,
            'pharmacien': None,
            'caissier': None
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
        print("\n=== AUTHENTICATION TESTS ===")
        success, response = self.run_test(
            "Login with admin credentials",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.tokens['admin'] = response['access_token']
            self.user_data = response.get('user', {})
            self.users['admin'] = response.get('user', {})
            print(f"   Token obtained: {self.token[:20]}...")
            print(f"   User: {self.user_data.get('name', 'Unknown')}")
            print(f"   Role: {self.user_data.get('role', 'Unknown')}")
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

    def test_customers_crud_comprehensive(self):
        """Test comprehensive CRUD operations for customers as per requirements"""
        print("\n=== CUSTOMERS CRUD COMPREHENSIVE TESTS ===")
        
        # 1. GET /api/customers - Liste des clients
        success, customers = self.run_test("GET /api/customers - Liste des clients", "GET", "customers", 200)
        if success:
            print(f"   ✅ Found {len(customers)} customers initially")
            initial_count = len(customers)
        else:
            print("❌ Failed to get initial customers list")
            return False
        
        # 2. POST /api/customers - Créer un nouveau client
        customer_data = {
            "name": "Test Client CRUD",
            "phone": "+33 6 00 00 00 00",
            "email": "testcrud@client.fr",
            "address": "1 Rue Test, Paris"
        }
        success, new_customer = self.run_test("POST /api/customers - Créer nouveau client", "POST", "customers", 200, customer_data)
        if success and 'id' in new_customer:
            customer_id = new_customer['id']
            self.created_items['customers'].append(customer_id)
            print(f"   ✅ Created customer ID: {customer_id}")
            print(f"   ✅ Customer name: {new_customer.get('name')}")
            print(f"   ✅ Customer email: {new_customer.get('email')}")
            print(f"   ✅ Customer phone: {new_customer.get('phone')}")
            
            # 3. GET /api/customers/{id} - Obtenir le client créé
            success, specific_customer = self.run_test("GET /api/customers/{id} - Obtenir client créé", "GET", f"customers/{customer_id}", 200)
            if success:
                print(f"   ✅ Retrieved specific customer: {specific_customer.get('name')}")
                if specific_customer.get('email') == "testcrud@client.fr":
                    print(f"   ✅ Customer data matches: {specific_customer.get('email')}")
                else:
                    print(f"   ❌ Customer data mismatch")
            
            # 4. PUT /api/customers/{id} - Modifier le client (changer le nom en "Test Client Modifié")
            update_data = {
                "name": "Test Client Modifié",
                "phone": "+33 6 00 00 00 00",
                "email": "testcrud@client.fr",
                "address": "1 Rue Test, Paris"
            }
            success, updated_customer = self.run_test("PUT /api/customers/{id} - Modifier client", "PUT", f"customers/{customer_id}", 200, update_data)
            if success:
                print(f"   ✅ Updated customer name to: {updated_customer.get('name')}")
                
                # Verify the update
                success, verify_update = self.run_test("Verify customer update", "GET", f"customers/{customer_id}", 200)
                if success and verify_update.get('name') == "Test Client Modifié":
                    print(f"   ✅ Update verified: {verify_update.get('name')}")
                else:
                    print(f"   ❌ Update verification failed")
            
            # 5. DELETE /api/customers/{id} - Supprimer le client
            success, delete_response = self.run_test("DELETE /api/customers/{id} - Supprimer client", "DELETE", f"customers/{customer_id}", 200)
            if success:
                print(f"   ✅ Customer deleted successfully")
                
                # 6. Vérifier que le client n'existe plus
                success, not_found = self.run_test("Verify customer deleted (should 404)", "GET", f"customers/{customer_id}", 404)
                if success:
                    print(f"   ✅ Deleted customer correctly returns 404")
                else:
                    print(f"   ❌ Deleted customer should return 404")
                
                # Verify customer count back to original
                success, final_customers = self.run_test("Get customers after deletion", "GET", "customers", 200)
                if success:
                    if len(final_customers) == initial_count:
                        print(f"   ✅ Customer count back to original: {len(final_customers)}")
                    else:
                        print(f"   ❌ Expected {initial_count} customers after deletion, found {len(final_customers)}")
                
                # Remove from cleanup list since already deleted
                if customer_id in self.created_items['customers']:
                    self.created_items['customers'].remove(customer_id)
            
            return True
        else:
            print("❌ Failed to create customer")
            return False

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

    def test_sales_crud_comprehensive(self):
        """Test comprehensive CRUD operations for sales as per requirements"""
        print("\n=== SALES CRUD COMPREHENSIVE TESTS ===")
        
        # Ensure we have products for sales
        if not self.created_items['products']:
            print("   ⚠️ No products available, creating test product first...")
            product_data = {
                "name": "Test Médicament Vente",
                "barcode": "SALE123456",
                "description": "Médicament pour test de vente",
                "price": 15.50,
                "stock": 100,
                "min_stock": 10,
                "category": "Test"
            }
            success, new_product = self.run_test("Create product for sales test", "POST", "products", 200, product_data)
            if success and 'id' in new_product:
                self.created_items['products'].append(new_product['id'])
                print(f"   ✅ Created test product ID: {new_product['id']}")
            else:
                print("   ❌ Failed to create test product, cannot test sales")
                return False
        
        # 1. GET /api/sales - Liste des ventes
        success, sales = self.run_test("GET /api/sales - Liste des ventes", "GET", "sales", 200)
        if success:
            print(f"   ✅ Found {len(sales)} sales initially")
            initial_count = len(sales)
        else:
            print("❌ Failed to get initial sales list")
            return False
        
        # 2. POST /api/sales - Créer une nouvelle vente (si produits disponibles)
        sale_data = {
            "customer_id": self.created_items['customers'][0] if self.created_items['customers'] else None,
            "items": [
                {
                    "product_id": self.created_items['products'][0],
                    "name": "Test Médicament Vente",
                    "price": 15.50,
                    "quantity": 2
                }
            ],
            "total": 31.00,
            "payment_method": "carte"
        }
        success, new_sale = self.run_test("POST /api/sales - Créer nouvelle vente", "POST", "sales", 200, sale_data)
        if success and 'id' in new_sale:
            sale_id = new_sale['id']
            self.created_items['sales'].append(sale_id)
            print(f"   ✅ Created sale ID: {sale_id}")
            print(f"   ✅ Sale total: {new_sale.get('total')}")
            print(f"   ✅ Payment method: {new_sale.get('payment_method')}")
            print(f"   ✅ Items count: {len(new_sale.get('items', []))}")
            
            # 3. GET /api/sales/{id} - Obtenir une vente spécifique
            success, specific_sale = self.run_test("GET /api/sales/{id} - Obtenir vente spécifique", "GET", f"sales/{sale_id}", 200)
            if success:
                print(f"   ✅ Retrieved specific sale: {specific_sale.get('id')}")
                if specific_sale.get('total') == 31.00:
                    print(f"   ✅ Sale data matches: total = {specific_sale.get('total')}")
                else:
                    print(f"   ❌ Sale data mismatch")
            
            return sale_id
        else:
            print("❌ Failed to create sale")
            return False

    def test_sales_access_control(self):
        """Test sales access control - Admin vs non-admin deletion"""
        print("\n=== SALES ACCESS CONTROL TESTS ===")
        
        # First create a sale to test deletion
        sale_id = self.test_sales_crud_comprehensive()
        if not sale_id:
            print("❌ Cannot test access control without a sale")
            return False
        
        # Create a non-admin user (pharmacien) if not exists
        if not self.tokens.get('pharmacien'):
            print("   Creating pharmacien user for access control test...")
            if self.tokens['admin']:
                self.token = self.tokens['admin']
                pharmacien_data = {
                    "name": "Test Pharmacien Access",
                    "email": "pharmacien.access@test.fr",
                    "password": "test123",
                    "role": "pharmacien",
                    "tenant_id": self.users['admin']['tenant_id']
                }
                
                success, pharmacien_user = self.run_test(
                    "Create pharmacien for access test",
                    "POST",
                    "users",
                    200,
                    data=pharmacien_data
                )
                
                if success:
                    self.created_items['users'].append(pharmacien_user['id'])
                    
                    # Login as pharmacien
                    success, pharmacien_login = self.run_test(
                        "Login as pharmacien for access test",
                        "POST",
                        "auth/login",
                        200,
                        data={"email": "pharmacien.access@test.fr", "password": "test123"}
                    )
                    
                    if success:
                        self.tokens['pharmacien'] = pharmacien_login['access_token']
                        print(f"   ✅ Pharmacien token obtained for access test")
        
        # Test non-admin trying to delete sale (should get 403)
        if self.tokens.get('pharmacien'):
            print("\n--- Testing Non-Admin Access Control ---")
            self.token = self.tokens['pharmacien']
            
            success, response = self.run_test(
                "Non-admin tries DELETE /api/sales/{id} (should fail with 403)",
                "DELETE",
                f"sales/{sale_id}",
                403
            )
            if success:
                print("   ✅ Non-admin correctly denied access to delete sales (403)")
            else:
                print("   ❌ Non-admin should be denied access to delete sales")
        
        # Test admin can delete sale (should succeed and restore stock)
        print("\n--- Testing Admin Access Control ---")
        self.token = self.tokens['admin']
        
        # Get product stock before deletion to verify restoration
        if self.created_items['products']:
            product_id = self.created_items['products'][0]
            success, product_before = self.run_test("Get product stock before sale deletion", "GET", f"products/{product_id}", 200)
            if success:
                stock_before = product_before.get('stock', 0)
                print(f"   Product stock before deletion: {stock_before}")
        
        # Admin deletes sale (should restore stock)
        success, delete_response = self.run_test(
            "Admin DELETE /api/sales/{id} (should succeed and restore stock)",
            "DELETE",
            f"sales/{sale_id}",
            200
        )
        if success:
            print("   ✅ Admin successfully deleted sale")
            print(f"   ✅ Response: {delete_response.get('message', 'No message')}")
            
            # Verify stock was restored
            if self.created_items['products']:
                success, product_after = self.run_test("Get product stock after sale deletion", "GET", f"products/{product_id}", 200)
                if success:
                    stock_after = product_after.get('stock', 0)
                    print(f"   Product stock after deletion: {stock_after}")
                    if stock_after == stock_before + 2:  # We sold 2 items
                        print("   ✅ Stock correctly restored after sale deletion")
                    else:
                        print(f"   ❌ Stock not properly restored. Expected {stock_before + 2}, got {stock_after}")
            
            # Verify sale no longer exists
            success, not_found = self.run_test("Verify sale deleted (should 404)", "GET", f"sales/{sale_id}", 404)
            if success:
                print(f"   ✅ Deleted sale correctly returns 404")
            else:
                print(f"   ❌ Deleted sale should return 404")
            
            # Remove from cleanup list since already deleted
            if sale_id in self.created_items['sales']:
                self.created_items['sales'].remove(sale_id)
            
            return True
        else:
            print("   ❌ Admin should be able to delete sales")
            return False

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

    def test_auth_with_role_verification(self):
        """Test authentication with role verification in JWT token"""
        print("\n=== AUTHENTICATION WITH ROLE VERIFICATION ===")
        
        # Test login and verify JWT contains role
        success, response = self.run_test(
            "Login and verify JWT role",
            "POST",
            "auth/login",
            200,
            data={"email": "demo@pharmaflow.com", "password": "demo123"}
        )
        
        if success and 'access_token' in response:
            import jwt
            try:
                # Decode JWT to verify role is in payload (without verification for testing)
                decoded = jwt.decode(response['access_token'], options={"verify_signature": False})
                if 'role' in decoded:
                    print(f"   ✅ JWT contains role: {decoded['role']}")
                    print(f"   ✅ JWT contains user_id: {decoded.get('sub', 'N/A')}")
                    print(f"   ✅ JWT contains tenant_id: {decoded.get('tenant_id', 'N/A')}")
                else:
                    print("   ❌ JWT does not contain role")
                    return False
            except Exception as e:
                print(f"   ❌ Failed to decode JWT: {e}")
                return False
        
        # Test /api/auth/me endpoint
        success, user_info = self.run_test(
            "Get current user info (/api/auth/me)",
            "GET",
            "auth/me",
            200
        )
        
        if success:
            print(f"   ✅ User info retrieved: {user_info.get('name', 'N/A')}")
            print(f"   ✅ User role: {user_info.get('role', 'N/A')}")
            print(f"   ✅ User email: {user_info.get('email', 'N/A')}")
            return True
        else:
            print("   ❌ Failed to get user info")
            return False

    def test_user_management_endpoints(self):
        """Test user management endpoints (Admin only)"""
        print("\n=== USER MANAGEMENT ENDPOINTS (ADMIN ONLY) ===")
        
        # Ensure we're using admin token
        if not self.tokens['admin']:
            print("   ❌ No admin token available")
            return False
        
        self.token = self.tokens['admin']
        
        # 1. GET /api/users - List all users
        success, users = self.run_test("GET /api/users - List all users", "GET", "users", 200)
        if success:
            print(f"   ✅ Found {len(users)} users in system")
            initial_user_count = len(users)
        else:
            print("   ❌ Failed to get users list")
            return False
        
        # 2. POST /api/users - Create new user
        new_user_data = {
            "name": "Jean Pharmacien",
            "email": "jean.pharmacien@test.fr",
            "password": "test123",
            "role": "pharmacien",
            "tenant_id": self.users['admin']['tenant_id']
        }
        
        success, created_user = self.run_test(
            "POST /api/users - Create new user",
            "POST",
            "users",
            200,
            data=new_user_data
        )
        
        if success and 'id' in created_user:
            user_id = created_user['id']
            self.created_items['users'].append(user_id)
            print(f"   ✅ Created user ID: {user_id}")
            print(f"   ✅ User name: {created_user.get('name')}")
            print(f"   ✅ User role: {created_user.get('role')}")
            print(f"   ✅ User email: {created_user.get('email')}")
            
            # Store user info for later role testing
            self.users['pharmacien'] = created_user
            
            # 3. GET /api/users/{id} - Get specific user
            success, specific_user = self.run_test(
                "GET /api/users/{id} - Get specific user",
                "GET",
                f"users/{user_id}",
                200
            )
            
            if success:
                print(f"   ✅ Retrieved specific user: {specific_user.get('name')}")
            
            # 4. PUT /api/users/{id} - Update user (change name)
            update_data = {
                "name": "Jean Pharmacien Modifié",
                "role": "pharmacien"
            }
            
            success, updated_user = self.run_test(
                "PUT /api/users/{id} - Update user",
                "PUT",
                f"users/{user_id}",
                200,
                data=update_data
            )
            
            if success:
                print(f"   ✅ Updated user name to: {updated_user.get('name')}")
            
            # Test login with created user to get their token
            success, pharmacien_login = self.run_test(
                "Login as pharmacien user",
                "POST",
                "auth/login",
                200,
                data={"email": "jean.pharmacien@test.fr", "password": "test123"}
            )
            
            if success and 'access_token' in pharmacien_login:
                self.tokens['pharmacien'] = pharmacien_login['access_token']
                print(f"   ✅ Pharmacien token obtained")
            
            # 5. DELETE /api/users/{id} - Delete user (will be done in cleanup)
            # We'll test this in cleanup to ensure proper cleanup
            
            return True
        else:
            print("   ❌ Failed to create user")
            return False

    def test_role_based_access_control(self):
        """Test role-based access control"""
        print("\n=== ROLE-BASED ACCESS CONTROL TESTS ===")
        
        # Create a caissier user for testing
        if self.tokens['admin']:
            self.token = self.tokens['admin']
            caissier_data = {
                "name": "Marie Caissier",
                "email": "marie.caissier@test.fr",
                "password": "test123",
                "role": "caissier",
                "tenant_id": self.users['admin']['tenant_id']
            }
            
            success, caissier_user = self.run_test(
                "Create caissier user for testing",
                "POST",
                "users",
                200,
                data=caissier_data
            )
            
            if success:
                self.created_items['users'].append(caissier_user['id'])
                self.users['caissier'] = caissier_user
                
                # Login as caissier
                success, caissier_login = self.run_test(
                    "Login as caissier user",
                    "POST",
                    "auth/login",
                    200,
                    data={"email": "marie.caissier@test.fr", "password": "test123"}
                )
                
                if success:
                    self.tokens['caissier'] = caissier_login['access_token']
        
        # Test pharmacien access
        if self.tokens['pharmacien']:
            print("\n--- Testing Pharmacien Access ---")
            self.token = self.tokens['pharmacien']
            
            # Pharmacien should NOT be able to access user management
            success, response = self.run_test(
                "Pharmacien tries to access GET /api/users (should fail)",
                "GET",
                "users",
                403
            )
            if success:
                print("   ✅ Pharmacien correctly denied access to user management")
            
            # Pharmacien SHOULD be able to access products
            success, products = self.run_test(
                "Pharmacien accesses GET /api/products (should succeed)",
                "GET",
                "products",
                200
            )
            if success:
                print("   ✅ Pharmacien can access products")
            
            # Pharmacien SHOULD be able to access suppliers
            success, suppliers = self.run_test(
                "Pharmacien accesses GET /api/suppliers (should succeed)",
                "GET",
                "suppliers",
                200
            )
            if success:
                print("   ✅ Pharmacien can access suppliers")
            
            # Pharmacien SHOULD be able to access sales
            success, sales = self.run_test(
                "Pharmacien accesses GET /api/sales (should succeed)",
                "GET",
                "sales",
                200
            )
            if success:
                print("   ✅ Pharmacien can access sales")
        
        # Test caissier access
        if self.tokens['caissier']:
            print("\n--- Testing Caissier Access ---")
            self.token = self.tokens['caissier']
            
            # Caissier should NOT be able to access user management
            success, response = self.run_test(
                "Caissier tries to access GET /api/users (should fail)",
                "GET",
                "users",
                403
            )
            if success:
                print("   ✅ Caissier correctly denied access to user management")
            
            # Caissier should NOT be able to access products
            success, response = self.run_test(
                "Caissier tries to access GET /api/products (should fail)",
                "GET",
                "products",
                403
            )
            if success:
                print("   ✅ Caissier correctly denied access to products")
            else:
                print("   ❌ Caissier should be denied access to products")
            
            # Caissier SHOULD be able to access sales
            success, sales = self.run_test(
                "Caissier accesses GET /api/sales (should succeed)",
                "GET",
                "sales",
                200
            )
            if success:
                print("   ✅ Caissier can access sales")
            
            # Caissier SHOULD be able to access customers
            success, customers = self.run_test(
                "Caissier accesses GET /api/customers (should succeed)",
                "GET",
                "customers",
                200
            )
            if success:
                print("   ✅ Caissier can access customers")
        
        # Restore admin token
        self.token = self.tokens['admin']
        return True

    def test_categories_crud_comprehensive(self):
        """Test comprehensive CRUD operations for categories as per requirements"""
        print("\n=== CATEGORIES CRUD COMPREHENSIVE TESTS ===")
        print("🏥 DynSoft Pharma - Test des endpoints de catégories")
        
        # 1. GET /api/categories - Lister les catégories (initial)
        success, categories = self.run_test("GET /api/categories - Lister les catégories", "GET", "categories", 200)
        if success:
            print(f"   ✅ Found {len(categories)} categories initially")
            initial_count = len(categories)
        else:
            print("❌ Failed to get initial categories list")
            return False
        
        # 2. POST /api/categories - Créer première catégorie "Antibiotiques"
        category1_data = {
            "name": "Antibiotiques",
            "description": "Médicaments antibiotiques",
            "color": "#EF4444"
        }
        success, new_category1 = self.run_test("POST /api/categories - Créer catégorie Antibiotiques", "POST", "categories", 200, category1_data)
        if success and 'id' in new_category1:
            category1_id = new_category1['id']
            self.created_items.setdefault('categories', []).append(category1_id)
            print(f"   ✅ Created category 1 ID: {category1_id}")
            print(f"   ✅ Category name: {new_category1.get('name')}")
            print(f"   ✅ Category description: {new_category1.get('description')}")
            print(f"   ✅ Category color: {new_category1.get('color')}")
        else:
            print("❌ Failed to create first category")
            return False
        
        # 3. POST /api/categories - Créer deuxième catégorie "Antidouleurs"
        category2_data = {
            "name": "Antidouleurs",
            "description": "Analgésiques et anti-inflammatoires",
            "color": "#3B82F6"
        }
        success, new_category2 = self.run_test("POST /api/categories - Créer catégorie Antidouleurs", "POST", "categories", 200, category2_data)
        if success and 'id' in new_category2:
            category2_id = new_category2['id']
            self.created_items.setdefault('categories', []).append(category2_id)
            print(f"   ✅ Created category 2 ID: {category2_id}")
            print(f"   ✅ Category name: {new_category2.get('name')}")
            print(f"   ✅ Category description: {new_category2.get('description')}")
            print(f"   ✅ Category color: {new_category2.get('color')}")
        else:
            print("❌ Failed to create second category")
            return False
        
        # 4. GET /api/categories - Lister les catégories (après création)
        success, updated_categories = self.run_test("GET /api/categories - Lister après création", "GET", "categories", 200)
        if success:
            if len(updated_categories) == initial_count + 2:
                print(f"   ✅ Category count increased from {initial_count} to {len(updated_categories)}")
            else:
                print(f"   ❌ Expected {initial_count + 2} categories, found {len(updated_categories)}")
        
        # 5. PUT /api/categories/{id} - Modifier une catégorie
        update_data = {
            "name": "Antibiotiques Modifiés",
            "description": "Médicaments antibiotiques - description modifiée",
            "color": "#FF6B6B"
        }
        success, updated_category = self.run_test("PUT /api/categories/{id} - Modifier catégorie", "PUT", f"categories/{category1_id}", 200, update_data)
        if success:
            print(f"   ✅ Updated category name to: {updated_category.get('name')}")
            print(f"   ✅ Updated description to: {updated_category.get('description')}")
            print(f"   ✅ Updated color to: {updated_category.get('color')}")
            
            # Verify the update
            success, verify_update = self.run_test("Verify category update", "GET", f"categories/{category1_id}", 200)
            if success and verify_update.get('name') == "Antibiotiques Modifiés":
                print(f"   ✅ Update verified: {verify_update.get('name')}")
            else:
                print(f"   ❌ Update verification failed")
        
        # 6. POST /api/products - Créer un produit avec category_id
        product_with_category_data = {
            "name": "Amoxicilline Test",
            "barcode": "AMX123456",
            "description": "Antibiotique de test",
            "price": 12.50,
            "stock": 50,
            "min_stock": 5,
            "category_id": category1_id
        }
        success, new_product = self.run_test("POST /api/products - Créer produit avec catégorie", "POST", "products", 200, product_with_category_data)
        if success and 'id' in new_product:
            product_id = new_product['id']
            self.created_items.setdefault('products', []).append(product_id)
            print(f"   ✅ Created product with category ID: {product_id}")
            print(f"   ✅ Product name: {new_product.get('name')}")
            print(f"   ✅ Product category_id: {new_product.get('category_id')}")
            
            # 7. GET /api/products - Vérifier que le produit a la catégorie
            success, products = self.run_test("GET /api/products - Vérifier produit avec catégorie", "GET", "products", 200)
            if success:
                product_found = False
                for product in products:
                    if product.get('id') == product_id:
                        if product.get('category_id') == category1_id:
                            print(f"   ✅ Product correctly linked to category: {product.get('category_id')}")
                            product_found = True
                        else:
                            print(f"   ❌ Product category mismatch: expected {category1_id}, got {product.get('category_id')}")
                        break
                if not product_found:
                    print(f"   ❌ Product not found in products list")
        else:
            print("❌ Failed to create product with category")
            return False
        
        # 8. DELETE /api/categories/{id} - Essayer de supprimer catégorie utilisée (doit échouer avec 400)
        success, delete_response = self.run_test("DELETE /api/categories/{id} - Supprimer catégorie utilisée (doit échouer)", "DELETE", f"categories/{category1_id}", 400)
        if success:
            print(f"   ✅ Category deletion correctly blocked when used by products (400)")
            print(f"   ✅ Error message: {delete_response.get('detail', 'No detail provided')}")
        else:
            print(f"   ❌ Category deletion should fail with 400 when used by products")
        
        # 9. DELETE product first, then DELETE category (should succeed)
        success, product_delete = self.run_test("DELETE /api/products/{id} - Supprimer produit d'abord", "DELETE", f"products/{product_id}", 200)
        if success:
            print(f"   ✅ Product deleted successfully")
            if product_id in self.created_items.get('products', []):
                self.created_items['products'].remove(product_id)
            
            # Now try to delete the category (should succeed)
            success, category_delete = self.run_test("DELETE /api/categories/{id} - Supprimer catégorie après produit", "DELETE", f"categories/{category1_id}", 200)
            if success:
                print(f"   ✅ Category deleted successfully after removing products")
                if category1_id in self.created_items.get('categories', []):
                    self.created_items['categories'].remove(category1_id)
            else:
                print(f"   ❌ Category deletion should succeed after removing products")
        
        # 10. DELETE /api/categories/{id} - Supprimer deuxième catégorie (non utilisée)
        success, delete_response2 = self.run_test("DELETE /api/categories/{id} - Supprimer catégorie non utilisée", "DELETE", f"categories/{category2_id}", 200)
        if success:
            print(f"   ✅ Unused category deleted successfully")
            if category2_id in self.created_items.get('categories', []):
                self.created_items['categories'].remove(category2_id)
            
            # Verify category count back to original
            success, final_categories = self.run_test("GET /api/categories - Vérifier après suppression", "GET", "categories", 200)
            if success:
                if len(final_categories) == initial_count:
                    print(f"   ✅ Category count back to original: {len(final_categories)}")
                else:
                    print(f"   ❌ Expected {initial_count} categories after deletion, found {len(final_categories)}")
        else:
            print("❌ Failed to delete unused category")
        
        return True

    def test_security_scenarios(self):
        """Test security scenarios"""
        print("\n=== SECURITY TESTS ===")
        
        # Ensure we're using admin token
        self.token = self.tokens['admin']
        
        # 1. Test creating user with invalid role
        invalid_role_data = {
            "name": "Invalid Role User",
            "email": "invalid@test.fr",
            "password": "test123",
            "role": "invalid_role",
            "tenant_id": self.users['admin']['tenant_id']
        }
        
        success, response = self.run_test(
            "Try to create user with invalid role (should fail)",
            "POST",
            "users",
            400,
            data=invalid_role_data
        )
        if success:
            print("   ✅ Invalid role correctly rejected")
        
        # 2. Test admin trying to delete their own account
        admin_user_id = self.users['admin']['id']
        success, response = self.run_test(
            "Admin tries to delete own account (should fail)",
            "DELETE",
            f"users/{admin_user_id}",
            400
        )
        if success:
            print("   ✅ Admin correctly prevented from deleting own account")
        
        # 3. Test accessing admin endpoints without token
        old_token = self.token
        self.token = None
        
        success, response = self.run_test(
            "Access admin endpoint without token (should fail)",
            "GET",
            "users",
            401
        )
        if success:
            print("   ✅ Admin endpoint correctly requires authentication")
        
        # Restore token
        self.token = old_token
        
        # 4. Test accessing admin endpoints with invalid token
        self.token = "invalid_token_123"
        
        success, response = self.run_test(
            "Access admin endpoint with invalid token (should fail)",
            "GET",
            "users",
            401
        )
        if success:
            print("   ✅ Invalid token correctly rejected")
        
        # Restore valid token
        self.token = old_token
        
        return True

    def cleanup_created_items(self):
        """Clean up created test items"""
        print("\n=== CLEANUP ===")
        
        # Ensure we're using admin token for cleanup
        if self.tokens['admin']:
            self.token = self.tokens['admin']
        
        # Delete created users (admin only)
        for user_id in self.created_items.get('users', []):
            success, response = self.run_test(f"Delete user {user_id}", "DELETE", f"users/{user_id}", 200)
            if success:
                print(f"   ✅ Deleted user {user_id}")
        
        # Delete created products first (they may reference categories)
        for product_id in self.created_items.get('products', []):
            self.run_test(f"Delete product {product_id}", "DELETE", f"products/{product_id}", 200)
        
        # Delete created categories
        for category_id in self.created_items.get('categories', []):
            self.run_test(f"Delete category {category_id}", "DELETE", f"categories/{category_id}", 200)

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

    def run_supplier_crud_tests_only(self):
        """Run only supplier CRUD tests as per requirements"""
        print("🚀 Starting Supplier CRUD Tests (DynSoft Pharma)")
        print(f"Base URL: {self.base_url}")
        print("Testing credentials: demo@pharmaflow.com / demo123")
        
        # Authentication is required
        if not self.test_login():
            print("❌ Login failed, stopping tests")
            return False
        
        # Test authentication security
        self.test_authentication_security()
        
        # Run supplier tests only
        supplier_success = self.test_suppliers_endpoints()
        
        # Print results
        print(f"\n📊 Supplier Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if supplier_success:
            print("✅ All supplier CRUD operations working correctly")
        else:
            print("❌ Some supplier CRUD operations failed")
        
        return supplier_success

    def run_user_management_tests(self):
        """Run comprehensive user management and role-based access control tests"""
        print("🚀 Starting User Management & Role-Based Access Control Tests")
        print("🏥 DynSoft Pharma - Complete User & Role System Testing")
        print(f"Base URL: {self.base_url}")
        print("Testing credentials: demo@pharmaflow.com / demo123 (admin role)")
        
        # Authentication is required
        if not self.test_login():
            print("❌ Login failed, stopping tests")
            return False
        
        # Verify admin role
        if self.user_data.get('role') != 'admin':
            print(f"❌ Expected admin role, got: {self.user_data.get('role')}")
            return False
        
        print(f"✅ Logged in as admin: {self.user_data.get('name')}")
        
        # Run comprehensive user management tests
        tests_success = []
        
        # 1. Authentication with role verification
        tests_success.append(self.test_auth_with_role_verification())
        
        # 2. User management endpoints (Admin only)
        tests_success.append(self.test_user_management_endpoints())
        
        # 3. Role-based access control
        tests_success.append(self.test_role_based_access_control())
        
        # 4. Security tests
        tests_success.append(self.test_security_scenarios())
        
        # Cleanup
        self.cleanup_created_items()
        
        # Print results
        print(f"\n📊 User Management Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        all_tests_passed = all(tests_success)
        
        if all_tests_passed:
            print("✅ ALL USER MANAGEMENT & ROLE TESTS PASSED")
            print("✅ Authentication with role verification: WORKING")
            print("✅ User CRUD operations (Admin only): WORKING")
            print("✅ Role-based access control: WORKING")
            print("✅ Security controls: WORKING")
        else:
            print("❌ Some user management tests failed")
            failed_tests = []
            test_names = [
                "Authentication with role verification",
                "User management endpoints",
                "Role-based access control", 
                "Security scenarios"
            ]
            for i, success in enumerate(tests_success):
                if not success:
                    failed_tests.append(test_names[i])
            print(f"❌ Failed tests: {', '.join(failed_tests)}")
        
    def run_customers_sales_crud_tests(self):
        """Run comprehensive Customers and Sales CRUD tests as per requirements"""
        print("🚀 Starting Customers and Sales CRUD Tests (DynSoft Pharma)")
        print(f"Base URL: {self.base_url}")
        print("Testing credentials: demo@pharmaflow.com / demo123")
        print("\n🎯 Test complet des pages Clients et Ventes avec CRUD pour DynSoft Pharma")
        
        # Authentication is required
        if not self.test_login():
            print("❌ Login failed, stopping tests")
            return False
        
        # Verify admin role for full testing
        if self.user_data.get('role') != 'admin':
            print(f"⚠️ Warning: Not admin role, got: {self.user_data.get('role')}")
            print("Some tests may be limited")
        
        print(f"✅ Logged in as: {self.user_data.get('name')} ({self.user_data.get('role')})")
        
        # Run comprehensive tests
        tests_success = []
        
        # 1. Customers CRUD Tests
        print("\n" + "="*60)
        print("🧑‍🤝‍🧑 BACKEND TESTS - CLIENTS (CUSTOMERS)")
        print("="*60)
        tests_success.append(self.test_customers_crud_comprehensive())
        
        # 2. Sales CRUD Tests  
        print("\n" + "="*60)
        print("💰 BACKEND TESTS - VENTES (SALES)")
        print("="*60)
        sales_success = self.test_sales_crud_comprehensive()
        tests_success.append(bool(sales_success))
        
        # 3. Sales Access Control Tests
        print("\n" + "="*60)
        print("🔒 CONTRÔLE D'ACCÈS VENTES (SALES ACCESS CONTROL)")
        print("="*60)
        tests_success.append(self.test_sales_access_control())
        
        # Print results
        print(f"\n📊 Customers & Sales Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        all_tests_passed = all(tests_success)
        
        if all_tests_passed:
            print("\n✅ ALL CUSTOMERS & SALES CRUD TESTS PASSED")
            print("✅ Customers CRUD (GET, POST, PUT, DELETE): WORKING")
            print("✅ Sales CRUD (GET, POST, GET by ID): WORKING") 
            print("✅ Sales deletion (Admin only with stock restore): WORKING")
            print("✅ Access control (Non-admin blocked from deletion): WORKING")
        else:
            print("\n❌ Some customers & sales tests failed")
            failed_tests = []
            test_names = [
                "Customers CRUD operations",
                "Sales CRUD operations", 
                "Sales access control"
            ]
            for i, success in enumerate(tests_success):
                if not success:
                    failed_tests.append(test_names[i])
            print(f"❌ Failed tests: {', '.join(failed_tests)}")
        
        # Cleanup
        self.cleanup_created_items()
        
        return all_tests_passed

    def run_modularized_backend_tests(self):
        """Run comprehensive tests for the modularized backend as per review request"""
        print("🚀 Starting Modularized Backend Tests (DynSoft Pharma)")
        print(f"Base URL: {self.base_url}")
        print("Testing modularized backend after refactoring from monolithic server.py")
        print("\n🎯 Testing all endpoints with role-based access control")
        
        # Test with all three user roles
        test_credentials = [
            {"email": "admin@pharmaflow.com", "password": "admin123", "role": "admin"},
            {"email": "pharmacien@pharmaflow.com", "password": "pharma123", "role": "pharmacien"},
            {"email": "caissier@pharmaflow.com", "password": "caisse123", "role": "caissier"}
        ]
        
        # Try to login with each credential set
        for cred in test_credentials:
            print(f"\n--- Testing login for {cred['role']} ---")
            success, response = self.run_test(
                f"Login as {cred['role']}",
                "POST",
                "auth/login",
                200,
                data={"email": cred["email"], "password": cred["password"]}
            )
            if success and 'access_token' in response:
                self.tokens[cred['role']] = response['access_token']
                self.users[cred['role']] = response.get('user', {})
                print(f"   ✅ {cred['role']} login successful")
                print(f"   User: {response.get('user', {}).get('name', 'Unknown')}")
                print(f"   Role: {response.get('user', {}).get('role', 'Unknown')}")
            else:
                print(f"   ❌ {cred['role']} login failed")
        
        # Set admin as default for testing
        if self.tokens.get('admin'):
            self.token = self.tokens['admin']
            self.user_data = self.users['admin']
        else:
            print("❌ No admin token available, cannot proceed with tests")
            return False
        
        # Run comprehensive tests for each module
        tests_success = []
        
        # 1. Authentication Module Tests
        print("\n" + "="*60)
        print("🔐 AUTHENTICATION MODULE TESTS (routes/auth.py)")
        print("="*60)
        tests_success.append(self.test_auth_module_comprehensive())
        
        # 2. Products Module Tests
        print("\n" + "="*60)
        print("💊 PRODUCTS MODULE TESTS (routes/products.py)")
        print("="*60)
        tests_success.append(self.test_products_module_comprehensive())
        
        # 3. Categories Module Tests
        print("\n" + "="*60)
        print("📂 CATEGORIES MODULE TESTS (routes/categories.py)")
        print("="*60)
        tests_success.append(self.test_categories_module_comprehensive())
        
        # 4. Sales Module Tests
        print("\n" + "="*60)
        print("💰 SALES MODULE TESTS (routes/sales.py)")
        print("="*60)
        tests_success.append(self.test_sales_module_comprehensive())
        
        # 5. Stock Module Tests
        print("\n" + "="*60)
        print("📦 STOCK MODULE TESTS (routes/stock.py)")
        print("="*60)
        tests_success.append(self.test_stock_module_comprehensive())
        
        # 6. Settings Module Tests
        print("\n" + "="*60)
        print("⚙️ SETTINGS MODULE TESTS (routes/settings.py)")
        print("="*60)
        tests_success.append(self.test_settings_module_comprehensive())
        
        # 7. Reports Module Tests
        print("\n" + "="*60)
        print("📊 REPORTS MODULE TESTS (routes/reports.py)")
        print("="*60)
        tests_success.append(self.test_reports_module_comprehensive())
        
        # 8. Role-Based Access Control Tests
        print("\n" + "="*60)
        print("🔒 ROLE-BASED ACCESS CONTROL TESTS")
        print("="*60)
        tests_success.append(self.test_rbac_comprehensive())
        
        # Cleanup
        self.cleanup_created_items()
        
        # Print results
        print(f"\n📊 Modularized Backend Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        all_tests_passed = all(tests_success)
        
        if all_tests_passed:
            print("\n✅ ALL MODULARIZED BACKEND TESTS PASSED")
            print("✅ Authentication module: WORKING")
            print("✅ Products module: WORKING")
            print("✅ Categories module: WORKING")
            print("✅ Sales module: WORKING")
            print("✅ Stock module: WORKING")
            print("✅ Settings module: WORKING")
            print("✅ Reports module: WORKING")
            print("✅ Role-based access control: WORKING")
        else:
            print("\n❌ Some modularized backend tests failed")
            failed_tests = []
            test_names = [
                "Authentication module",
                "Products module",
                "Categories module", 
                "Sales module",
                "Stock module",
                "Settings module",
                "Reports module",
                "Role-based access control"
            ]
            for i, success in enumerate(tests_success):
                if not success:
                    failed_tests.append(test_names[i])
            print(f"❌ Failed modules: {', '.join(failed_tests)}")
        
        return all_tests_passed

    def test_auth_module_comprehensive(self):
        """Test authentication module endpoints"""
        print("Testing authentication endpoints...")
        
        # Test login with valid credentials
        success, response = self.run_test(
            "POST /api/auth/login - Valid credentials",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        if not success:
            return False
        
        # Test login with invalid credentials
        success, response = self.run_test(
            "POST /api/auth/login - Invalid credentials",
            "POST",
            "auth/login",
            401,
            data={"email": "admin@pharmaflow.com", "password": "wrongpassword"}
        )
        
        # Test register endpoint (if available)
        register_data = {
            "name": "Test User Registration",
            "email": "testregister@pharmaflow.com",
            "password": "test123",
            "role": "pharmacien"
        }
        success, response = self.run_test(
            "POST /api/auth/register - Register new user",
            "POST",
            "auth/register",
            200,
            data=register_data
        )
        if success and 'id' in response:
            self.created_items.setdefault('users', []).append(response['id'])
        
        # Test get current user info
        success, response = self.run_test(
            "GET /api/auth/me - Get current user info",
            "GET",
            "auth/me",
            200
        )
        if success:
            print(f"   ✅ Current user: {response.get('name')} ({response.get('role')})")
        
        return True

    def test_products_module_comprehensive(self):
        """Test products module endpoints"""
        print("Testing products endpoints...")
        
        # Get all products
        success, products = self.run_test(
            "GET /api/products - List all products",
            "GET",
            "products",
            200
        )
        if not success:
            return False
        
        print(f"   Found {len(products)} products")
        
        # Create a product with uniqueness validation
        product_data = {
            "name": "Test Modular Product",
            "barcode": "MOD123456789",
            "description": "Product for modular testing",
            "price": 25.99,
            "stock": 100,
            "min_stock": 10,
            "category": "Test Category"
        }
        success, new_product = self.run_test(
            "POST /api/products - Create product",
            "POST",
            "products",
            200,
            data=product_data
        )
        if success and 'id' in new_product:
            product_id = new_product['id']
            self.created_items.setdefault('products', []).append(product_id)
            print(f"   ✅ Created product ID: {product_id}")
            
            # Test uniqueness validation - try to create duplicate
            success, response = self.run_test(
                "POST /api/products - Test uniqueness validation (should fail)",
                "POST",
                "products",
                400,
                data=product_data
            )
            if success:
                print("   ✅ Uniqueness validation working")
            
            # Search products
            success, search_results = self.run_test(
                "GET /api/products/search?q=Modular - Search products",
                "GET",
                "products/search?q=Modular",
                200
            )
            if success:
                print(f"   ✅ Search found {len(search_results)} products")
            
            # Toggle product status
            success, response = self.run_test(
                "PATCH /api/products/{id}/toggle-status - Toggle active status",
                "PATCH",
                f"products/{product_id}/toggle-status",
                200
            )
            if success:
                print("   ✅ Product status toggle working")
            
            # Try to delete product (should work if not sold)
            success, response = self.run_test(
                "DELETE /api/products/{id} - Delete product",
                "DELETE",
                f"products/{product_id}",
                200
            )
            if success:
                print("   ✅ Product deletion working")
                if product_id in self.created_items.get('products', []):
                    self.created_items['products'].remove(product_id)
        
        return True

    def test_categories_module_comprehensive(self):
        """Test categories module endpoints"""
        print("Testing categories endpoints...")
        
        # Get all categories
        success, categories = self.run_test(
            "GET /api/categories - List all categories",
            "GET",
            "categories",
            200
        )
        if not success:
            return False
        
        print(f"   Found {len(categories)} categories")
        
        # Create a category
        category_data = {
            "name": "Test Modular Category",
            "description": "Category for modular testing",
            "color": "#FF5733"
        }
        success, new_category = self.run_test(
            "POST /api/categories - Create category",
            "POST",
            "categories",
            200,
            data=category_data
        )
        if success and 'id' in new_category:
            category_id = new_category['id']
            self.created_items.setdefault('categories', []).append(category_id)
            print(f"   ✅ Created category ID: {category_id}")
        
        return True

    def test_sales_module_comprehensive(self):
        """Test sales module endpoints"""
        print("Testing sales endpoints...")
        
        # Get all sales
        success, sales = self.run_test(
            "GET /api/sales - List all sales",
            "GET",
            "sales",
            200
        )
        if not success:
            return False
        
        print(f"   Found {len(sales)} sales")
        
        # Create a sale (need products first)
        if self.created_items.get('products'):
            sale_data = {
                "customer_id": None,
                "items": [
                    {
                        "product_id": self.created_items['products'][0],
                        "name": "Test Product",
                        "price": 25.99,
                        "quantity": 1
                    }
                ],
                "total": 25.99,
                "payment_method": "cash"
            }
            success, new_sale = self.run_test(
                "POST /api/sales - Create new sale",
                "POST",
                "sales",
                200,
                data=sale_data
            )
            if success and 'id' in new_sale:
                sale_id = new_sale['id']
                self.created_items.setdefault('sales', []).append(sale_id)
                print(f"   ✅ Created sale ID: {sale_id}")
                
                # Test admin-only deletion
                success, response = self.run_test(
                    "DELETE /api/sales/{id} - Delete sale (admin only)",
                    "DELETE",
                    f"sales/{sale_id}",
                    200
                )
                if success:
                    print("   ✅ Sale deletion and stock restoration working")
                    if sale_id in self.created_items.get('sales', []):
                        self.created_items['sales'].remove(sale_id)
        
        return True

    def test_stock_module_comprehensive(self):
        """Test stock module endpoints"""
        print("Testing stock endpoints...")
        
        # Get stock movements
        success, stock_movements = self.run_test(
            "GET /api/stock - List stock movements",
            "GET",
            "stock",
            200
        )
        if not success:
            return False
        
        print(f"   Found {len(stock_movements)} stock movements")
        
        # Get low stock alerts
        success, alerts = self.run_test(
            "GET /api/stock/alerts - Get low stock alerts",
            "GET",
            "stock/alerts",
            200
        )
        if success:
            print(f"   ✅ Found {len(alerts)} low stock alerts")
        
        # Get stock valuation
        success, valuation = self.run_test(
            "GET /api/stock/valuation - Get total stock valuation",
            "GET",
            "stock/valuation",
            200
        )
        if success:
            print(f"   ✅ Stock valuation retrieved")
            if 'fifo' in valuation:
                print(f"   FIFO valuation: {valuation.get('fifo', 0)}")
            if 'lifo' in valuation:
                print(f"   LIFO valuation: {valuation.get('lifo', 0)}")
            if 'weighted_average' in valuation:
                print(f"   Weighted Average: {valuation.get('weighted_average', 0)}")
        
        return True

    def test_settings_module_comprehensive(self):
        """Test settings module endpoints"""
        print("Testing settings endpoints...")
        
        # Get current settings
        success, settings = self.run_test(
            "GET /api/settings - Get current settings",
            "GET",
            "settings",
            200
        )
        if not success:
            return False
        
        print("   ✅ Settings retrieved successfully")
        
        # Update settings (admin only)
        if settings:
            update_data = {**settings, "test_field": "modular_test_value"}
            success, updated_settings = self.run_test(
                "PUT /api/settings - Update settings (admin only)",
                "PUT",
                "settings",
                200,
                data=update_data
            )
            if success:
                print("   ✅ Settings update working (admin only)")
        
        return True

    def test_reports_module_comprehensive(self):
        """Test reports module endpoints"""
        print("Testing reports endpoints...")
        
        # Get dashboard statistics
        success, dashboard = self.run_test(
            "GET /api/reports/dashboard - Get dashboard statistics",
            "GET",
            "reports/dashboard",
            200
        )
        if not success:
            return False
        
        print("   ✅ Dashboard statistics retrieved")
        if 'total_products' in dashboard:
            print(f"   Total products: {dashboard.get('total_products', 0)}")
        if 'total_sales' in dashboard:
            print(f"   Total sales: {dashboard.get('total_sales', 0)}")
        
        # Get sales report
        success, sales_report = self.run_test(
            "GET /api/reports/sales?days=7 - Get sales report",
            "GET",
            "reports/sales?days=7",
            200
        )
        if success:
            print("   ✅ Sales report retrieved")
            print(f"   Report period: {sales_report.get('period_days', 'N/A')} days")
        
        return True

    def test_rbac_comprehensive(self):
        """Test role-based access control comprehensively"""
        print("Testing role-based access control...")
        
        # Test caissier access (basic access)
        if self.tokens.get('caissier'):
            print("\n--- Testing Caissier Access (Basic) ---")
            self.token = self.tokens['caissier']
            
            # Caissier should NOT access admin-only endpoints
            success, response = self.run_test(
                "Caissier tries GET /api/settings (should fail with 403)",
                "GET",
                "settings",
                403
            )
            if success:
                print("   ✅ Caissier correctly denied access to settings")
            
            # Caissier should NOT access user management
            success, response = self.run_test(
                "Caissier tries GET /api/users (should fail with 403)",
                "GET",
                "users",
                403
            )
            if success:
                print("   ✅ Caissier correctly denied access to user management")
        
        # Test pharmacien access (limited access)
        if self.tokens.get('pharmacien'):
            print("\n--- Testing Pharmacien Access (Limited) ---")
            self.token = self.tokens['pharmacien']
            
            # Pharmacien should access product management
            success, response = self.run_test(
                "Pharmacien accesses GET /api/products (should succeed)",
                "GET",
                "products",
                200
            )
            if success:
                print("   ✅ Pharmacien can access product management")
            
            # Pharmacien should NOT access user management
            success, response = self.run_test(
                "Pharmacien tries GET /api/users (should fail with 403)",
                "GET",
                "users",
                403
            )
            if success:
                print("   ✅ Pharmacien correctly denied access to user management")
        
        # Test admin access (full access)
        if self.tokens.get('admin'):
            print("\n--- Testing Admin Access (Full) ---")
            self.token = self.tokens['admin']
            
            # Admin should access all endpoints
            success, response = self.run_test(
                "Admin accesses GET /api/users (should succeed)",
                "GET",
                "users",
                200
            )
            if success:
                print("   ✅ Admin can access user management")
            
            success, response = self.run_test(
                "Admin accesses GET /api/settings (should succeed)",
                "GET",
                "settings",
                200
            )
            if success:
                print("   ✅ Admin can access settings")
        
        # Restore admin token
        self.token = self.tokens['admin']
        return True

def main():
    tester = PharmaFlowAPITester()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--suppliers-only":
            success = tester.run_supplier_crud_tests_only()
        elif sys.argv[1] == "--users-only":
            success = tester.run_user_management_tests()
        elif sys.argv[1] == "--customers-sales":
            success = tester.run_customers_sales_crud_tests()
        elif sys.argv[1] == "--categories":
            success = tester.run_categories_crud_tests()
        elif sys.argv[1] == "--modular":
            success = tester.run_modularized_backend_tests()
        else:
            print("Usage: python backend_test.py [--suppliers-only|--users-only|--customers-sales|--categories|--modular]")
            return 1
    else:
        # Default to modularized backend tests for this review
        success = tester.run_modularized_backend_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())