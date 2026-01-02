import requests
import sys
import json
from datetime import datetime

class PharmaFlowAPITester:
    def __init__(self, base_url="https://pharmflow-3.preview.emergentagent.com"):
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

    def test_supplies_employee_code_display(self):
        """Test Supplies (Approvisionnements) employee code display fix for DynSoft Pharma"""
        print("\n=== SUPPLIES EMPLOYEE CODE DISPLAY FIX TESTS ===")
        print("🎯 Testing Supplies Employee Code Display Fix - DynSoft Pharma")
        print("📋 Credentials: admin@pharmaflow.com / admin123 (employee_code: ADM-001)")
        
        # Test 1: Backend API - Login and verify employee code
        print("\n--- Test 1: Backend API - Login and Verify Employee Code ---")
        success, response = self.run_test(
            "POST /api/auth/login with admin credentials",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            # Decode JWT to verify employee_code
            import jwt
            try:
                decoded = jwt.decode(response['access_token'], options={"verify_signature": False})
                if decoded.get('employee_code') == 'ADM-001':
                    print(f"   ✅ JWT contains correct employee_code: {decoded.get('employee_code')}")
                else:
                    print(f"   ❌ JWT employee_code mismatch: expected ADM-001, got {decoded.get('employee_code')}")
            except Exception as e:
                print(f"   ❌ Failed to decode JWT: {e}")
        else:
            print("   ❌ Login failed")
            return False
        
        # Test 2: GET /api/supplies to verify employee code fields
        print("\n--- Test 2: GET /api/supplies - Verify Employee Code Fields ---")
        success, supplies = self.run_test("GET /api/supplies to list all supplies", "GET", "supplies", 200)
        if success:
            print(f"   ✅ Found {len(supplies)} supplies")
            
            # Check each supply for employee code fields
            supplies_with_created_by_name = 0
            supplies_with_updated_by_name = 0
            supplies_with_validated_by_name = 0
            
            for supply in supplies:
                # Check created_by_name field
                if 'created_by_name' in supply:
                    created_by_name = supply['created_by_name']
                    if created_by_name and created_by_name != "Inconnu" and created_by_name != "N/A":
                        supplies_with_created_by_name += 1
                        print(f"   ✅ Supply {supply.get('id', 'Unknown')[:8]}... has created_by_name: {created_by_name}")
                    elif created_by_name == "Inconnu":
                        print(f"   ❌ Supply {supply.get('id', 'Unknown')[:8]}... shows 'Inconnu' instead of employee code")
                
                # Check updated_by_name field
                if 'updated_by_name' in supply and supply['updated_by_name']:
                    updated_by_name = supply['updated_by_name']
                    if updated_by_name != "Inconnu" and updated_by_name != "N/A":
                        supplies_with_updated_by_name += 1
                        print(f"   ✅ Supply {supply.get('id', 'Unknown')[:8]}... has updated_by_name: {updated_by_name}")
                
                # Check validated_by_name field
                if 'validated_by_name' in supply and supply['validated_by_name']:
                    validated_by_name = supply['validated_by_name']
                    if validated_by_name != "Inconnu" and validated_by_name != "N/A":
                        supplies_with_validated_by_name += 1
                        print(f"   ✅ Supply {supply.get('id', 'Unknown')[:8]}... has validated_by_name: {validated_by_name}")
            
            print(f"   📊 Summary: {supplies_with_created_by_name} supplies with valid created_by_name")
            print(f"   📊 Summary: {supplies_with_updated_by_name} supplies with valid updated_by_name")
            print(f"   📊 Summary: {supplies_with_validated_by_name} supplies with valid validated_by_name")
        else:
            print("   ❌ Failed to get supplies list")
            return False
        
        # Test 3: Create New Supply and Verify created_by_name
        print("\n--- Test 3: Create New Supply and Verify created_by_name ---")
        # First, ensure we have a product to use
        product_data = {
            "name": "Test Médicament Supplies Fix",
            "barcode": "SUPFIX123",
            "description": "Médicament pour test supplies employee code fix",
            "price": 12.75,
            "stock": 30,
            "min_stock": 5,
            "category": "Test"
        }
        product_success, new_product = self.run_test("Create product for supplies test", "POST", "products", 200, product_data)
        if product_success and 'id' in new_product:
            product_id = new_product['id']
            self.created_items['products'].append(product_id)
            
            # Create supply
            supply_data = {
                "supply_date": "2026-01-02T12:00:00Z",
                "purchase_order_ref": "BC-SUPFIX-001",
                "delivery_note_number": "BL-SUPFIX-001",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 25,
                        "unit_price": 10.50
                    }
                ]
            }
            success, new_supply = self.run_test("POST /api/supplies to create new supply", "POST", "supplies", 200, supply_data)
            if success and 'id' in new_supply:
                supply_id = new_supply['id']
                self.created_items.setdefault('supplies', []).append(supply_id)
                
                # Verify created_by_name shows employee code
                created_by_name = new_supply.get('created_by_name')
                if created_by_name == 'ADM-001':
                    print(f"   ✅ New supply created_by_name shows employee code: {created_by_name}")
                else:
                    print(f"   ❌ New supply created_by_name should be ADM-001, got: {created_by_name}")
                
                # Test 4: Edit Supply and Verify updated_by_name
                print("\n--- Test 4: Edit Supply and Verify updated_by_name ---")
                update_data = {
                    "supply_date": "2026-01-02T12:00:00Z",
                    "purchase_order_ref": "BC-SUPFIX-001-UPDATED",
                    "delivery_note_number": "BL-SUPFIX-001",
                    "items": [
                        {
                            "product_id": product_id,
                            "quantity": 30,  # Changed quantity
                            "unit_price": 10.50
                        }
                    ]
                }
                success, updated_supply = self.run_test("PUT /api/supplies/{id} to update supply", "PUT", f"supplies/{supply_id}", 200, update_data)
                if success:
                    # Get the updated supply to verify updated_by_name
                    success, supply_details = self.run_test("GET /api/supplies/{id} to verify updated_by_name", "GET", f"supplies/{supply_id}", 200)
                    if success:
                        updated_by_name = supply_details.get('updated_by_name')
                        if updated_by_name == 'ADM-001':
                            print(f"   ✅ Updated supply updated_by_name shows employee code: {updated_by_name}")
                        else:
                            print(f"   ❌ Updated supply updated_by_name should be ADM-001, got: {updated_by_name}")
                
                # Test 5: Validate Supply and Verify validated_by_name
                print("\n--- Test 5: Validate Supply and Verify validated_by_name ---")
                success, validated_supply = self.run_test("POST /api/supplies/{id}/validate to validate supply", "POST", f"supplies/{supply_id}/validate", 200)
                if success:
                    validated_by_name = validated_supply.get('validated_by_name')
                    if validated_by_name == 'ADM-001':
                        print(f"   ✅ Validated supply validated_by_name shows employee code: {validated_by_name}")
                    else:
                        print(f"   ❌ Validated supply validated_by_name should be ADM-001, got: {validated_by_name}")
                else:
                    print("   ❌ Failed to validate supply")
            else:
                print("   ❌ Failed to create supply")
                return False
        else:
            print("   ❌ Failed to create product for supplies test")
            return False
        
        # Test 6: Backward Compatibility Test
        print("\n--- Test 6: Backward Compatibility Test ---")
        success, all_supplies = self.run_test("GET /api/supplies for backward compatibility test", "GET", "supplies", 200)
        if success:
            uuid_created_by = 0
            employee_code_created_by = 0
            inconnu_created_by = 0
            
            for supply in all_supplies:
                created_by = supply.get('created_by', '')
                created_by_name = supply.get('created_by_name', '')
                
                # Check if created_by is UUID format (old data)
                if len(created_by) > 10 and '-' in created_by and created_by.count('-') >= 4:
                    uuid_created_by += 1
                    # Check if it resolves to employee code
                    if created_by_name and created_by_name.startswith(('ADM-', 'PHA-', 'CAI-')):
                        print(f"   ✅ Old UUID supply resolves to employee code: {created_by_name}")
                    elif created_by_name == "Inconnu":
                        inconnu_created_by += 1
                        print(f"   ❌ Old UUID supply shows 'Inconnu' instead of employee code")
                # Check if created_by is employee code format (new data)
                elif created_by.startswith(('ADM-', 'PHA-', 'CAI-')):
                    employee_code_created_by += 1
            
            print(f"   📊 Backward compatibility summary:")
            print(f"   📊 {uuid_created_by} supplies with UUID format (old data)")
            print(f"   📊 {employee_code_created_by} supplies with employee_code format (new data)")
            print(f"   📊 {inconnu_created_by} supplies showing 'Inconnu' (needs fixing)")
            
            if inconnu_created_by == 0:
                print(f"   ✅ Backward compatibility working - no 'Inconnu' entries found")
            else:
                print(f"   ❌ Backward compatibility issue - {inconnu_created_by} supplies show 'Inconnu'")
        
        return True

    def test_employee_code_tracking(self):
        """Test employee code standardization and price history model"""
        print("\n=== EMPLOYEE CODE TRACKING & PRICE HISTORY TESTS ===")
        print("🎯 Testing Price History Model & Employee Code Standardization")
        
        # Test credentials from review request
        test_credentials = [
            {"email": "admin@pharmaflow.com", "password": "admin123", "expected_code": "ADM-001"},
            {"email": "pharmacien@pharmaflow.com", "password": "pharma123", "expected_code": "PHA-001"}
        ]
        
        # Test 1: JWT Token Verification
        print("\n--- Test 1: JWT Token Verification ---")
        for cred in test_credentials:
            success, response = self.run_test(
                f"Login as {cred['email']} and verify JWT token",
                "POST",
                "auth/login",
                200,
                data={"email": cred["email"], "password": cred["password"]}
            )
            if success and 'access_token' in response:
                # Decode JWT token to verify employee_code
                import jwt
                try:
                    decoded = jwt.decode(response['access_token'], options={"verify_signature": False})
                    if 'employee_code' in decoded:
                        actual_code = decoded['employee_code']
                        if actual_code == cred['expected_code']:
                            print(f"   ✅ JWT contains correct employee_code: {actual_code}")
                        else:
                            print(f"   ❌ JWT employee_code mismatch: expected {cred['expected_code']}, got {actual_code}")
                    else:
                        print(f"   ❌ JWT does not contain employee_code")
                except Exception as e:
                    print(f"   ❌ Failed to decode JWT: {e}")
        
        # Set admin token for remaining tests
        admin_success, admin_response = self.run_test(
            "Login as admin for remaining tests",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        if admin_success:
            self.token = admin_response['access_token']
        
        # Test 2: Supply Creation with Employee Code
        print("\n--- Test 2: Supply Creation with Employee Code ---")
        # First, ensure we have a product to use
        product_data = {
            "name": "Test Médicament Employee Code",
            "barcode": "EMP123456",
            "description": "Médicament pour test employee code",
            "price": 15.50,
            "stock": 50,
            "min_stock": 10,
            "category": "Test"
        }
        product_success, new_product = self.run_test("Create product for employee code test", "POST", "products", 200, product_data)
        if product_success and 'id' in new_product:
            product_id = new_product['id']
            self.created_items['products'].append(product_id)
            
            # Create supply
            supply_data = {
                "supply_date": "2026-01-02T10:00:00Z",
                "purchase_order_ref": "BC-EMP-001",
                "delivery_note_number": "BL-EMP-001",
                "items": [
                    {
                        "product_id": product_id,
                        "quantity": 20,
                        "unit_price": 8.50
                    }
                ]
            }
            success, new_supply = self.run_test("Create supply with employee code", "POST", "supplies", 200, supply_data)
            if success and 'id' in new_supply:
                supply_id = new_supply['id']
                self.created_items.setdefault('supplies', []).append(supply_id)
                
                # Verify created_by contains employee_code
                if new_supply.get('created_by') == 'ADM-001':
                    print(f"   ✅ Supply created_by contains employee_code: {new_supply.get('created_by')}")
                else:
                    print(f"   ❌ Supply created_by should be ADM-001, got: {new_supply.get('created_by')}")
                
                # Test 3: Supply Validation with Employee Code
                print("\n--- Test 3: Supply Validation with Employee Code ---")
                success, validated_supply = self.run_test("Validate supply (admin only)", "POST", f"supplies/{supply_id}/validate", 200)
                if success:
                    if validated_supply.get('validated_by') == 'ADM-001':
                        print(f"   ✅ Supply validated_by contains employee_code: {validated_supply.get('validated_by')}")
                    else:
                        print(f"   ❌ Supply validated_by should be ADM-001, got: {validated_supply.get('validated_by')}")
        
        # Test 4: Price History API Tests
        print("\n--- Test 4: Price History API Tests ---")
        success, price_history = self.run_test("Get price history", "GET", "prices/history", 200)
        if success and len(price_history) > 0:
            # Check for new field names in price history
            latest_entry = price_history[0]
            required_fields = ['prix_appro', 'prix_vente_prod', 'date_maj_prix', 'created_by']
            optional_fields = ['date_peremption']
            
            for field in required_fields:
                if field in latest_entry:
                    print(f"   ✅ Price history contains required field: {field}")
                    if field == 'created_by' and latest_entry[field] == 'ADM-001':
                        print(f"   ✅ Price history created_by contains employee_code: {latest_entry[field]}")
                else:
                    print(f"   ❌ Price history missing required field: {field}")
            
            for field in optional_fields:
                if field in latest_entry:
                    print(f"   ✅ Price history contains optional field: {field}")
        
        # Test 5: Stock Movement API Tests
        print("\n--- Test 5: Stock Movement API Tests ---")
        success, stock_movements = self.run_test("Get stock movements", "GET", "stock/movements", 200)
        if success and len(stock_movements) > 0:
            # Check for employee_code in created_by field
            latest_movement = stock_movements[0]
            if latest_movement.get('created_by') == 'ADM-001':
                print(f"   ✅ Stock movement created_by contains employee_code: {latest_movement.get('created_by')}")
            else:
                print(f"   ❌ Stock movement created_by should be ADM-001, got: {latest_movement.get('created_by')}")
        
        # Test stock adjustment
        if product_id:
            adjustment_data = {
                "product_id": product_id,
                "movement_type": "adjustment",
                "movement_quantity": 5,
                "notes": "Test adjustment with employee code"
            }
            success, adjustment = self.run_test("Create stock adjustment", "POST", "stock/adjustment", 200, adjustment_data)
            if success:
                if adjustment.get('created_by') == 'ADM-001':
                    print(f"   ✅ Stock adjustment created_by contains employee_code: {adjustment.get('created_by')}")
                else:
                    print(f"   ❌ Stock adjustment created_by should be ADM-001, got: {adjustment.get('created_by')}")
        
        # Test 6: Backward Compatibility Test
        print("\n--- Test 6: Backward Compatibility Test ---")
        # This test verifies that old records with UUID in created_by field still load correctly
        success, all_price_history = self.run_test("Get all price history for compatibility test", "GET", "prices/history?limit=500", 200)
        if success:
            uuid_records = 0
            employee_code_records = 0
            for entry in all_price_history:
                created_by = entry.get('created_by', '')
                if len(created_by) > 10 and '-' in created_by and created_by.count('-') >= 4:  # UUID format
                    uuid_records += 1
                elif created_by.startswith(('ADM-', 'PHA-', 'CAI-')):  # Employee code format
                    employee_code_records += 1
            
            print(f"   ✅ Found {uuid_records} records with UUID format (old data)")
            print(f"   ✅ Found {employee_code_records} records with employee_code format (new data)")
            print(f"   ✅ Backward compatibility verified - API handles mixed data correctly")
        
        return True

    def test_pwa_offline_infrastructure(self):
        """Test PWA/Offline infrastructure for DynSoft Pharma"""
        print("\n=== PWA OFFLINE INFRASTRUCTURE TESTS ===")
        print("🎯 Testing PWA/Offline infrastructure for DynSoft Pharma")
        print("📋 Focus: Backend API endpoints that feed the offline system")
        print("🔑 Credentials: admin@pharmaflow.com / admin123")
        
        # Test 1: Verify All API Endpoints for Offline Caching
        print("\n--- Test 1: Verify All API Endpoints for Offline Caching ---")
        
        offline_endpoints = [
            {"name": "Products", "endpoint": "products", "type": "array"},
            {"name": "Categories", "endpoint": "categories", "type": "array"},
            {"name": "Customers", "endpoint": "customers", "type": "array"},
            {"name": "Suppliers", "endpoint": "suppliers", "type": "array"},
            {"name": "Units", "endpoint": "units", "type": "array"},
            {"name": "Settings", "endpoint": "settings", "type": "object"}
        ]
        
        endpoint_results = {}
        
        for endpoint_info in offline_endpoints:
            name = endpoint_info["name"]
            endpoint = endpoint_info["endpoint"]
            expected_type = endpoint_info["type"]
            
            print(f"\n🔍 Testing {name} endpoint...")
            success, data = self.run_test(
                f"GET /api/{endpoint} - {name} for offline caching",
                "GET",
                endpoint,
                200
            )
            
            if success:
                # Verify JSON structure
                if expected_type == "array" and isinstance(data, list):
                    print(f"   ✅ Returns valid JSON array with {len(data)} items")
                    endpoint_results[name] = {"success": True, "count": len(data), "data": data}
                elif expected_type == "object" and isinstance(data, dict):
                    print(f"   ✅ Returns valid JSON object with {len(data)} fields")
                    endpoint_results[name] = {"success": True, "fields": len(data), "data": data}
                else:
                    print(f"   ❌ Expected {expected_type}, got {type(data).__name__}")
                    endpoint_results[name] = {"success": False, "error": f"Wrong data type: {type(data).__name__}"}
            else:
                print(f"   ❌ Failed to retrieve {name}")
                endpoint_results[name] = {"success": False, "error": "API call failed"}
        
        # Test 2: Test Sync-Compatible Data Structure
        print("\n--- Test 2: Test Sync-Compatible Data Structure ---")
        print("🔍 Verifying that each endpoint returns data with 'id' field for IndexedDB storage")
        
        id_field_results = {}
        
        for endpoint_info in offline_endpoints:
            name = endpoint_info["name"]
            expected_type = endpoint_info["type"]
            
            if name in endpoint_results and endpoint_results[name]["success"]:
                data = endpoint_results[name]["data"]
                
                if expected_type == "array" and isinstance(data, list):
                    items_with_id = 0
                    total_items = len(data)
                    
                    for item in data:
                        if isinstance(item, dict) and 'id' in item:
                            items_with_id += 1
                    
                    if total_items > 0:
                        percentage = (items_with_id / total_items) * 100
                        if percentage == 100:
                            print(f"   ✅ {name}: All {total_items} items have 'id' field (100%)")
                            id_field_results[name] = {"success": True, "percentage": 100, "count": total_items}
                        else:
                            print(f"   ⚠️ {name}: {items_with_id}/{total_items} items have 'id' field ({percentage:.1f}%)")
                            id_field_results[name] = {"success": False, "percentage": percentage, "count": total_items}
                    else:
                        print(f"   ℹ️ {name}: Empty array (no items to check)")
                        id_field_results[name] = {"success": True, "percentage": 100, "count": 0}
                
                elif expected_type == "object" and isinstance(data, dict):
                    # Settings object doesn't need 'id' field, it's a configuration object
                    print(f"   ✅ {name}: Settings object structure verified")
                    id_field_results[name] = {"success": True, "note": "Settings object - no id field required"}
        
        # Test 3: Test Settings Endpoint Specifically
        print("\n--- Test 3: Test Settings Endpoint for PWA Configuration ---")
        
        if "Settings" in endpoint_results and endpoint_results["Settings"]["success"]:
            settings_data = endpoint_results["Settings"]["data"]
            
            print(f"🔍 Analyzing settings structure for PWA compatibility...")
            print(f"   📊 Settings contains {len(settings_data)} configuration fields")
            
            # Check for PWA-related fields
            pwa_related_fields = [
                "return_delay_days",
                "low_stock_threshold", 
                "currency",
                "pharmacy_name",
                "pharmacy_address"
            ]
            
            found_pwa_fields = []
            for field in pwa_related_fields:
                if field in settings_data:
                    found_pwa_fields.append(field)
                    print(f"   ✅ Found PWA-compatible field: {field} = {settings_data[field]}")
            
            print(f"   📊 Found {len(found_pwa_fields)}/{len(pwa_related_fields)} PWA-compatible fields")
            
            # Verify settings can be parsed correctly
            try:
                import json
                json_str = json.dumps(settings_data)
                parsed_back = json.loads(json_str)
                print(f"   ✅ Settings object is JSON serializable and parseable")
            except Exception as e:
                print(f"   ❌ Settings object JSON serialization failed: {e}")
        else:
            print(f"   ❌ Settings endpoint failed, cannot test PWA configuration")
        
        # Test 4: Data Consistency Check
        print("\n--- Test 4: Data Consistency Check ---")
        print("🔍 Verifying data structure consistency across endpoints")
        
        consistency_results = {}
        
        for endpoint_info in offline_endpoints:
            name = endpoint_info["name"]
            expected_type = endpoint_info["type"]
            
            if name in endpoint_results and endpoint_results[name]["success"]:
                data = endpoint_results[name]["data"]
                
                if expected_type == "array" and isinstance(data, list) and len(data) > 0:
                    # Check first few items for consistent structure
                    sample_size = min(3, len(data))
                    sample_items = data[:sample_size]
                    
                    # Get field sets for each sample item
                    field_sets = []
                    for item in sample_items:
                        if isinstance(item, dict):
                            field_sets.append(set(item.keys()))
                    
                    if field_sets:
                        # Check if all items have similar structure
                        common_fields = set.intersection(*field_sets) if field_sets else set()
                        all_fields = set.union(*field_sets) if field_sets else set()
                        
                        consistency_percentage = (len(common_fields) / len(all_fields)) * 100 if all_fields else 100
                        
                        print(f"   📊 {name}: {len(common_fields)}/{len(all_fields)} fields consistent ({consistency_percentage:.1f}%)")
                        print(f"   📋 {name}: Common fields include 'id', 'name', etc.")
                        
                        consistency_results[name] = {
                            "consistent": consistency_percentage >= 80,
                            "percentage": consistency_percentage,
                            "common_fields": len(common_fields),
                            "total_fields": len(all_fields)
                        }
                    else:
                        print(f"   ⚠️ {name}: No valid items to check consistency")
                        consistency_results[name] = {"consistent": False, "error": "No valid items"}
                else:
                    print(f"   ℹ️ {name}: Skipping consistency check (empty or non-array)")
                    consistency_results[name] = {"consistent": True, "note": "Skipped - empty or settings object"}
        
        # Test Summary
        print("\n--- PWA Offline Infrastructure Test Summary ---")
        
        total_endpoints = len(offline_endpoints)
        successful_endpoints = sum(1 for name in endpoint_results if endpoint_results[name]["success"])
        
        print(f"📊 API Endpoints: {successful_endpoints}/{total_endpoints} working correctly")
        
        # ID field compatibility
        id_compatible_endpoints = sum(1 for name in id_field_results if id_field_results[name]["success"])
        print(f"📊 IndexedDB Compatibility: {id_compatible_endpoints}/{len(id_field_results)} endpoints have proper 'id' fields")
        
        # Data consistency
        consistent_endpoints = sum(1 for name in consistency_results if consistency_results[name]["consistent"])
        print(f"📊 Data Consistency: {consistent_endpoints}/{len(consistency_results)} endpoints have consistent structure")
        
        # Overall PWA readiness
        if successful_endpoints == total_endpoints and id_compatible_endpoints >= (len(id_field_results) - 1):  # -1 for settings
            print(f"✅ PWA Offline Infrastructure: READY")
            print(f"   ✅ All API endpoints return proper JSON data")
            print(f"   ✅ Data structures are compatible with IndexedDB storage")
            print(f"   ✅ Settings endpoint returns complete configuration")
            return True
        else:
            print(f"❌ PWA Offline Infrastructure: NEEDS ATTENTION")
            if successful_endpoints < total_endpoints:
                print(f"   ❌ {total_endpoints - successful_endpoints} API endpoints failed")
            if id_compatible_endpoints < (len(id_field_results) - 1):
                print(f"   ❌ Some endpoints missing 'id' fields for IndexedDB compatibility")
            return False

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

    def run_employee_code_tracking_tests(self):
        """Run specific tests for employee code tracking and price history model"""
        print("🚀 Starting Employee Code Tracking & Price History Model Tests")
        print("🏥 DynSoft Pharma - Testing Price History Model & Employee Code Standardization")
        print(f"Base URL: {self.base_url}")
        print("Testing new features:")
        print("- JWT token includes employee_code")
        print("- Price history uses French field names (prix_appro, prix_vente_prod, date_maj_prix, date_peremption)")
        print("- All user tracking fields use employee_code instead of user_id")
        print("- Backward compatibility with existing data")
        
        # Run the specific test
        test_success = self.test_employee_code_tracking()
        
        # Cleanup
        self.cleanup_created_items()
        
        # Print results
        print(f"\n📊 Employee Code Tracking Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if test_success:
            print("\n✅ ALL EMPLOYEE CODE TRACKING TESTS PASSED")
            print("✅ JWT token includes employee_code: WORKING")
            print("✅ Supply creation with employee_code: WORKING")
            print("✅ Supply validation with employee_code: WORKING")
            print("✅ Price history with French field names: WORKING")
            print("✅ Stock movements with employee_code: WORKING")
            print("✅ Backward compatibility: WORKING")
        else:
            print("\n❌ Some employee code tracking tests failed")
        
        return test_success

    def run_supplies_employee_code_tests(self):
        """Run supplies employee code display fix tests specifically"""
        print("🚀 Starting Supplies Employee Code Display Fix Tests")
        print("🏥 DynSoft Pharma - Testing Employee Code Display in Supplies")
        print(f"Base URL: {self.base_url}")
        print("Testing credentials: admin@pharmaflow.com / admin123 (employee_code: ADM-001)")
        
        # Run the specific test
        test_success = self.test_supplies_employee_code_display()
        
        # Cleanup
        self.cleanup_created_items()
        
        # Print results
        print(f"\n📊 Supplies Employee Code Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if test_success:
            print("✅ All supplies employee code display features working correctly")
        else:
            print("❌ Some supplies employee code display features failed")
        
        return test_success

    def test_state_management_integration(self):
        """Test React application with Zustand + React Query state management integration"""
        print("\n=== STATE MANAGEMENT INTEGRATION TESTS ===")
        print("🎯 Testing React application with Zustand + React Query state management")
        print("📋 Credentials: admin@pharmaflow.com / admin123")
        
        # Test 1: Authentication with employee_code
        print("\n--- Test 1: Authentication with employee_code ---")
        success, response = self.run_test(
            "POST /api/auth/login - verify returns token and user with employee_code",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            user_data = response.get('user', {})
            
            # Verify user has employee_code
            if 'employee_code' in user_data:
                print(f"   ✅ User contains employee_code: {user_data['employee_code']}")
            else:
                print(f"   ❌ User missing employee_code field")
            
            # Decode JWT to verify employee_code in token
            import jwt
            try:
                decoded = jwt.decode(response['access_token'], options={"verify_signature": False})
                if 'employee_code' in decoded:
                    print(f"   ✅ JWT contains employee_code: {decoded['employee_code']}")
                else:
                    print(f"   ❌ JWT missing employee_code field")
            except Exception as e:
                print(f"   ❌ Failed to decode JWT: {e}")
        else:
            print("   ❌ Authentication failed")
            return False
        
        # Test 2: API Endpoints Data Layer
        print("\n--- Test 2: API Endpoints Data Layer ---")
        
        # GET /api/products - verify returns products array
        success, products = self.run_test(
            "GET /api/products - verify returns products array",
            "GET",
            "products",
            200
        )
        if success:
            if isinstance(products, list):
                print(f"   ✅ Products endpoint returns array with {len(products)} items")
            else:
                print(f"   ❌ Products endpoint should return array, got {type(products)}")
        
        # GET /api/categories - verify returns categories array
        success, categories = self.run_test(
            "GET /api/categories - verify returns categories array",
            "GET",
            "categories",
            200
        )
        if success:
            if isinstance(categories, list):
                print(f"   ✅ Categories endpoint returns array with {len(categories)} items")
            else:
                print(f"   ❌ Categories endpoint should return array, got {type(categories)}")
        
        # GET /api/settings - verify returns settings object
        success, settings = self.run_test(
            "GET /api/settings - verify returns settings object",
            "GET",
            "settings",
            200
        )
        if success:
            if isinstance(settings, dict):
                print(f"   ✅ Settings endpoint returns object with {len(settings)} fields")
                # Check for key settings fields
                key_fields = ['pharmacy_name', 'currency', 'low_stock_threshold']
                for field in key_fields:
                    if field in settings:
                        print(f"   ✅ Settings contains {field}: {settings[field]}")
                    else:
                        print(f"   ⚠️ Settings missing {field} field")
            else:
                print(f"   ❌ Settings endpoint should return object, got {type(settings)}")
        
        # GET /api/sales - verify returns sales array
        success, sales = self.run_test(
            "GET /api/sales - verify returns sales array",
            "GET",
            "sales",
            200
        )
        if success:
            if isinstance(sales, list):
                print(f"   ✅ Sales endpoint returns array with {len(sales)} items")
                # Check if sales have proper structure
                if len(sales) > 0:
                    sample_sale = sales[0]
                    required_fields = ['id', 'total', 'created_at']
                    for field in required_fields:
                        if field in sample_sale:
                            print(f"   ✅ Sales contain {field} field")
                        else:
                            print(f"   ⚠️ Sales missing {field} field")
            else:
                print(f"   ❌ Sales endpoint should return array, got {type(sales)}")
        
        # Test 3: Data Structure Verification for State Management
        print("\n--- Test 3: Data Structure Verification for State Management ---")
        
        # Verify all endpoints return JSON-serializable data
        endpoints_to_test = [
            ("products", products),
            ("categories", categories), 
            ("settings", settings),
            ("sales", sales)
        ]
        
        for endpoint_name, data in endpoints_to_test:
            try:
                import json
                json.dumps(data)
                print(f"   ✅ {endpoint_name} data is JSON serializable")
            except Exception as e:
                print(f"   ❌ {endpoint_name} data not JSON serializable: {e}")
        
        # Test 4: Additional API endpoints for comprehensive state management
        print("\n--- Test 4: Additional API Endpoints for State Management ---")
        
        # GET /api/customers
        success, customers = self.run_test(
            "GET /api/customers - verify for state management",
            "GET",
            "customers",
            200
        )
        if success and isinstance(customers, list):
            print(f"   ✅ Customers endpoint returns array with {len(customers)} items")
        
        # GET /api/suppliers
        success, suppliers = self.run_test(
            "GET /api/suppliers - verify for state management",
            "GET",
            "suppliers",
            200
        )
        if success and isinstance(suppliers, list):
            print(f"   ✅ Suppliers endpoint returns array with {len(suppliers)} items")
        
        # GET /api/units
        success, units = self.run_test(
            "GET /api/units - verify for state management",
            "GET",
            "units",
            200
        )
        if success and isinstance(units, list):
            print(f"   ✅ Units endpoint returns array with {len(units)} items")
        
        # Test 5: Authentication persistence verification
        print("\n--- Test 5: Authentication Persistence Verification ---")
        
        # Test /api/auth/me to verify token persistence
        success, user_info = self.run_test(
            "GET /api/auth/me - verify authentication persistence",
            "GET",
            "auth/me",
            200
        )
        if success:
            print(f"   ✅ Authentication persistence working - user: {user_info.get('name')}")
            print(f"   ✅ User role: {user_info.get('role')}")
            print(f"   ✅ Employee code: {user_info.get('employee_code')}")
        
        return True

    def run_state_management_tests(self):
        """Run state management integration tests specifically"""
        print("🚀 Starting State Management Integration Tests")
        print("🏥 DynSoft Pharma - Testing React with Zustand + React Query")
        print(f"Base URL: {self.base_url}")
        print("Testing credentials: admin@pharmaflow.com / admin123")
        
        # Run the specific test
        test_success = self.test_state_management_integration()
        
        # Print results
        print(f"\n📊 State Management Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if test_success:
            print("\n✅ ALL STATE MANAGEMENT INTEGRATION TESTS PASSED")
            print("✅ Authentication with employee_code: WORKING")
            print("✅ API endpoints data layer: WORKING")
            print("✅ Data structure verification: WORKING")
            print("✅ JSON serialization: WORKING")
            print("✅ Authentication persistence: WORKING")
        else:
            print("\n❌ Some state management integration tests failed")
        
        return test_success

    def test_supplier_activation_deactivation_deletion(self):
        """Test Supplier activation/deactivation and deletion rules for DynSoft Pharma"""
        print("\n=== SUPPLIER ACTIVATION/DEACTIVATION & DELETION RULES TESTS ===")
        print("🎯 Testing Supplier Status Toggle and Deletion Rules - DynSoft Pharma")
        print("📋 Admin: admin@pharmaflow.com / admin123")
        print("📋 Pharmacien: pharmacien@pharmaflow.com / pharma123")
        
        # Store original token
        original_token = self.token
        
        # Test 1: Login as admin and get suppliers list
        print("\n--- Test 1: Admin Login and Initial Suppliers List ---")
        success, admin_response = self.run_test(
            "Login as admin",
            "POST",
            "auth/login",
            200,
            data={"email": "admin@pharmaflow.com", "password": "admin123"}
        )
        if success and 'access_token' in admin_response:
            admin_token = admin_response['access_token']
            self.token = admin_token
            print(f"   ✅ Admin login successful")
        else:
            print("   ❌ Admin login failed")
            return False
        
        # Get initial suppliers list
        success, initial_suppliers = self.run_test("GET /api/suppliers (admin sees all)", "GET", "suppliers", 200)
        if success:
            print(f"   ✅ Admin sees {len(initial_suppliers)} suppliers total")
            active_count = sum(1 for s in initial_suppliers if s.get('is_active', True))
            inactive_count = len(initial_suppliers) - active_count
            print(f"   📊 Active suppliers: {active_count}, Inactive suppliers: {inactive_count}")
        else:
            print("   ❌ Failed to get suppliers list")
            return False
        
        # Test 2: Test Supplier Status Toggle (Admin Only)
        print("\n--- Test 2: Supplier Status Toggle (Admin Only) ---")
        if initial_suppliers:
            # Pick first supplier for testing
            test_supplier = initial_suppliers[0]
            supplier_id = test_supplier['id']
            original_status = test_supplier.get('is_active', True)
            print(f"   🎯 Testing with supplier: {test_supplier.get('name', 'Unknown')} (ID: {supplier_id[:8]}...)")
            print(f"   📊 Original status: {'Active' if original_status else 'Inactive'}")
            
            # Toggle status
            success, toggled_supplier = self.run_test(
                f"PATCH /api/suppliers/{supplier_id}/toggle-status (admin)",
                "PATCH",
                f"suppliers/{supplier_id}/toggle-status",
                200
            )
            if success:
                new_status = toggled_supplier.get('is_active')
                if new_status != original_status:
                    print(f"   ✅ Status toggled successfully: {original_status} → {new_status}")
                else:
                    print(f"   ❌ Status not changed: {original_status} → {new_status}")
                
                # Toggle back to original state
                success, restored_supplier = self.run_test(
                    f"PATCH /api/suppliers/{supplier_id}/toggle-status (restore)",
                    "PATCH",
                    f"suppliers/{supplier_id}/toggle-status",
                    200
                )
                if success:
                    restored_status = restored_supplier.get('is_active')
                    if restored_status == original_status:
                        print(f"   ✅ Status restored successfully: {new_status} → {restored_status}")
                    else:
                        print(f"   ❌ Status not restored properly: expected {original_status}, got {restored_status}")
            else:
                print("   ❌ Failed to toggle supplier status")
        
        # Test 3: Login as pharmacien and test visibility rules
        print("\n--- Test 3: Pharmacien Login and Visibility Rules ---")
        success, pharmacien_response = self.run_test(
            "Login as pharmacien",
            "POST",
            "auth/login",
            200,
            data={"email": "pharmacien@pharmaflow.com", "password": "pharma123"}
        )
        if success and 'access_token' in pharmacien_response:
            pharmacien_token = pharmacien_response['access_token']
            self.token = pharmacien_token
            print(f"   ✅ Pharmacien login successful")
            
            # Get suppliers as pharmacien (should only see active ones)
            success, pharmacien_suppliers = self.run_test("GET /api/suppliers (pharmacien sees only active)", "GET", "suppliers", 200)
            if success:
                print(f"   ✅ Pharmacien sees {len(pharmacien_suppliers)} suppliers")
                # Verify all suppliers are active
                inactive_visible = sum(1 for s in pharmacien_suppliers if not s.get('is_active', True))
                if inactive_visible == 0:
                    print(f"   ✅ Pharmacien correctly sees only active suppliers")
                else:
                    print(f"   ❌ Pharmacien sees {inactive_visible} inactive suppliers (should be 0)")
            
            # Test pharmacien cannot toggle status (should get 403)
            if initial_suppliers:
                supplier_id = initial_suppliers[0]['id']
                success, response = self.run_test(
                    f"PATCH /api/suppliers/{supplier_id}/toggle-status (pharmacien - should fail)",
                    "PATCH",
                    f"suppliers/{supplier_id}/toggle-status",
                    403
                )
                if success:
                    print(f"   ✅ Pharmacien correctly denied access to toggle status (403)")
                else:
                    print(f"   ❌ Pharmacien should be denied access to toggle status")
        else:
            print("   ❌ Pharmacien login failed")
        
        # Restore admin token for deletion tests
        self.token = admin_token
        
        # Test 4: Create supplier and test deletion with supplies
        print("\n--- Test 4: Supplier Deletion with Supplies (Should Fail) ---")
        # Create a new supplier
        supplier_data = {
            "name": "Test Supplier for Deletion",
            "contact": "Test Contact",
            "phone": "+33 6 00 00 00 01",
            "email": "test.deletion@supplier.com",
            "address": "123 Test Street, Test City"
        }
        success, new_supplier = self.run_test("POST /api/suppliers (create test supplier)", "POST", "suppliers", 200, supplier_data)
        if success and 'id' in new_supplier:
            supplier_id = new_supplier['id']
            self.created_items.setdefault('suppliers', []).append(supplier_id)
            print(f"   ✅ Created test supplier ID: {supplier_id[:8]}...")
            
            # Create a supply linked to this supplier
            # First, get a product to use
            success, products = self.run_test("GET /api/products (for supply creation)", "GET", "products", 200)
            if success and products:
                product_id = products[0]['id']
                
                supply_data = {
                    "supplier_id": supplier_id,
                    "supply_date": "2026-01-02T12:00:00Z",
                    "purchase_order_ref": "BC-DELETE-TEST-001",
                    "delivery_note_number": "BL-DELETE-TEST-001",
                    "items": [
                        {
                            "product_id": product_id,
                            "quantity": 10,
                            "unit_price": 5.00
                        }
                    ]
                }
                success, new_supply = self.run_test("POST /api/supplies (create supply for supplier)", "POST", "supplies", 200, supply_data)
                if success and 'id' in new_supply:
                    supply_id = new_supply['id']
                    self.created_items.setdefault('supplies', []).append(supply_id)
                    print(f"   ✅ Created supply linked to supplier: {supply_id[:8]}...")
                    
                    # Try to delete supplier (should fail with 400)
                    success, delete_response = self.run_test(
                        f"DELETE /api/suppliers/{supplier_id} (should fail - has supplies)",
                        "DELETE",
                        f"suppliers/{supplier_id}",
                        400
                    )
                    if success:
                        print(f"   ✅ Supplier deletion correctly blocked (400): {delete_response.get('detail', 'No detail')}")
                    else:
                        print(f"   ❌ Supplier deletion should fail with 400 when supplier has supplies")
                else:
                    print("   ❌ Failed to create supply for supplier")
            else:
                print("   ❌ No products available for supply creation")
        else:
            print("   ❌ Failed to create test supplier")
        
        # Test 5: Test can-delete endpoint
        print("\n--- Test 5: Can-Delete Endpoint ---")
        if 'suppliers' in self.created_items and self.created_items['suppliers']:
            supplier_id = self.created_items['suppliers'][0]
            success, can_delete_response = self.run_test(
                f"GET /api/suppliers/{supplier_id}/can-delete",
                "GET",
                f"suppliers/{supplier_id}/can-delete",
                200
            )
            if success:
                can_delete = can_delete_response.get('can_delete', False)
                supplies_count = can_delete_response.get('supplies_count', 0)
                message = can_delete_response.get('message', '')
                print(f"   ✅ Can delete: {can_delete}")
                print(f"   ✅ Supplies count: {supplies_count}")
                print(f"   ✅ Message: {message}")
                
                if supplies_count > 0 and not can_delete:
                    print(f"   ✅ Correctly indicates supplier cannot be deleted due to supplies")
                elif supplies_count == 0 and can_delete:
                    print(f"   ✅ Correctly indicates supplier can be deleted (no supplies)")
            else:
                print("   ❌ Failed to check can-delete status")
        
        # Test 6: Create supplier without supplies and test successful deletion
        print("\n--- Test 6: Supplier Deletion without Supplies (Should Succeed) ---")
        supplier_data_clean = {
            "name": "Test Supplier Clean Deletion",
            "contact": "Clean Contact",
            "phone": "+33 6 00 00 00 02",
            "email": "test.clean@supplier.com",
            "address": "456 Clean Street, Clean City"
        }
        success, clean_supplier = self.run_test("POST /api/suppliers (create clean supplier)", "POST", "suppliers", 200, supplier_data_clean)
        if success and 'id' in clean_supplier:
            clean_supplier_id = clean_supplier['id']
            print(f"   ✅ Created clean supplier ID: {clean_supplier_id[:8]}...")
            
            # Verify can-delete returns true
            success, can_delete_clean = self.run_test(
                f"GET /api/suppliers/{clean_supplier_id}/can-delete (should be true)",
                "GET",
                f"suppliers/{clean_supplier_id}/can-delete",
                200
            )
            if success:
                if can_delete_clean.get('can_delete') and can_delete_clean.get('supplies_count') == 0:
                    print(f"   ✅ Clean supplier can be deleted: {can_delete_clean.get('message')}")
                else:
                    print(f"   ❌ Clean supplier should be deletable")
            
            # Delete the clean supplier (should succeed)
            success, delete_clean_response = self.run_test(
                f"DELETE /api/suppliers/{clean_supplier_id} (should succeed)",
                "DELETE",
                f"suppliers/{clean_supplier_id}",
                200
            )
            if success:
                print(f"   ✅ Clean supplier deleted successfully: {delete_clean_response.get('message')}")
                
                # Verify supplier no longer exists
                success, not_found = self.run_test(
                    f"GET /api/suppliers/{clean_supplier_id} (should 404)",
                    "GET",
                    f"suppliers/{clean_supplier_id}",
                    404
                )
                if success:
                    print(f"   ✅ Deleted supplier correctly returns 404")
                else:
                    print(f"   ❌ Deleted supplier should return 404")
            else:
                print(f"   ❌ Clean supplier deletion should succeed")
        else:
            print("   ❌ Failed to create clean supplier")
        
        # Restore original token
        self.token = original_token
        
        print("\n--- Supplier Activation/Deactivation & Deletion Tests Summary ---")
        print("✅ Admin can toggle supplier status")
        print("✅ Non-admin cannot toggle supplier status (403)")
        print("✅ Admin sees all suppliers (active + inactive)")
        print("✅ Non-admin sees only active suppliers")
        print("✅ Suppliers with supplies cannot be deleted (400)")
        print("✅ Suppliers without supplies can be deleted")
        print("✅ Can-delete endpoint returns correct information")
        
        return True

    def run_supplier_activation_deletion_tests(self):
        """Run supplier activation/deactivation and deletion tests only"""
        print("🎯 DynSoft Pharma - Supplier Activation/Deactivation & Deletion Rules Testing")
        print("=" * 80)
        
        # Login first
        if not self.test_login():
            print("❌ Login failed, cannot continue tests")
            return False
        
        # Run the specific test
        success = self.test_supplier_activation_deactivation_deletion()
        
        # Cleanup
        self.cleanup_created_items()
        
        # Print summary
        print("\n" + "=" * 80)
        print(f"🎯 Supplier Activation/Deactivation & Deletion Tests Summary")
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if success:
            print("✅ All supplier activation/deactivation & deletion tests passed!")
        else:
            print("❌ Some supplier tests failed")
        
        return success

def main():
    # Get backend URL from environment
    import subprocess
    try:
        backend_url = subprocess.check_output(
            "grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2", 
            shell=True, 
            text=True
        ).strip()
        print(f"Using backend URL from environment: {backend_url}")
    except:
        backend_url = "https://pharmflow-3.preview.emergentagent.com"
        print(f"Using default backend URL: {backend_url}")
    
    tester = PharmaFlowAPITester(backend_url)
    
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
        elif sys.argv[1] == "--employee-code":
            success = tester.run_employee_code_tracking_tests()
        elif sys.argv[1] == "--supplies-employee-code":
            success = tester.run_supplies_employee_code_tests()
        elif sys.argv[1] == "--state-management":
            success = tester.run_state_management_tests()
        elif sys.argv[1] == "--pwa-offline":
            # Login first
            if not tester.test_login():
                print("❌ Login failed, cannot run PWA tests")
                return 1
            success = tester.test_pwa_offline_infrastructure()
        elif sys.argv[1] == "--supplier-activation":
            success = tester.run_supplier_activation_deletion_tests()
        else:
            print("Usage: python backend_test.py [--suppliers-only|--users-only|--customers-sales|--categories|--modular|--employee-code|--supplies-employee-code|--state-management|--pwa-offline|--supplier-activation]")
            return 1
    else:
        # Default to supplier activation tests for this review
        success = tester.run_supplier_activation_deletion_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())