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
        for user_id in self.created_items['users']:
            success, response = self.run_test(f"Delete user {user_id}", "DELETE", f"users/{user_id}", 200)
            if success:
                print(f"   ✅ Deleted user {user_id}")
        
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
        
        return all_tests_passed

def main():
    tester = PharmaFlowAPITester()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--suppliers-only":
            success = tester.run_supplier_crud_tests_only()
        elif sys.argv[1] == "--users-only":
            success = tester.run_user_management_tests()
        else:
            print("Usage: python backend_test.py [--suppliers-only|--users-only]")
            return 1
    else:
        success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())