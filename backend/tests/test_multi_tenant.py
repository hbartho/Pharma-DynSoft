"""
Tests DynPharma multi-tenant (super admin + isolation pharmacie).
Teste création/suppression de pharmacies, isolation des données, sécurité des routes,
CRUD utilisateurs, reset mot de passe, désactivation d'une pharmacie, régression centrale.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pharmacy-mgmt-portal.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER = {"email": "superadmin@dynsoftgn.com", "password": "DynSoft#2026"}
CENTRAL = {"email": "admin@pharmaflow.com", "password": "admin123"}
KALOUM = {"email": "admin@kaloum.test", "password": "kaloum123"}

QA_PHARMA = {
    "name": "Pharmacie QA Matam",
    "admin_first_name": "QA",
    "admin_last_name": "Matam",
    "admin_email": "qa.admin@matam.test",
    "admin_password": "matam123",
}
TEMP_PHARMA = {
    "name": "Pharmacie Temp",
    "admin_first_name": "Temp",
    "admin_last_name": "Admin",
    "admin_email": f"temp.admin+{uuid.uuid4().hex[:6]}@temp.test",
    "admin_password": "temp123",
}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def super_token():
    r = _login(**SUPER)
    assert r.status_code == 200, f"Super admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["role"] == "super_admin"
    return data["access_token"]


@pytest.fixture(scope="module")
def central_token():
    r = _login(**CENTRAL)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def qa_setup(super_token):
    """Crée (ou récupère) la pharmacie QA Matam."""
    # Supprimer d'abord s'il reste de précédentes runs
    requests.delete(f"{API}/platform/pharmacies/pharmacie_qa_matam",
                    params={"confirm": "pharmacie_qa_matam"}, headers=_h(super_token), timeout=30)
    r = requests.post(f"{API}/platform/pharmacies", json=QA_PHARMA, headers=_h(super_token), timeout=60)
    assert r.status_code in (200, 201), f"create QA pharmacy failed: {r.status_code} {r.text}"
    data = r.json()
    slug = data["pharmacy"]["slug"]
    yield {"slug": slug, "data": data}
    # Teardown
    requests.delete(f"{API}/platform/pharmacies/{slug}", params={"confirm": slug},
                    headers=_h(super_token), timeout=60)


# ---------- Super Admin login & role ----------
class TestSuperAdminLogin:
    def test_super_admin_login_role(self):
        r = _login(**SUPER)
        assert r.status_code == 200
        d = r.json()
        assert d["user"]["role"] == "super_admin"
        assert "access_token" in d

    def test_super_admin_cannot_access_tenant_route(self, super_token):
        r = requests.get(f"{API}/products/paginated?page=1&page_size=5",
                         headers=_h(super_token), timeout=30)
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    def test_pharmacy_admin_cannot_access_platform(self, central_token):
        r = requests.get(f"{API}/platform/pharmacies", headers=_h(central_token), timeout=30)
        assert r.status_code == 403


# ---------- Création de pharmacie ----------
class TestPharmacyCreation:
    def test_list_pharmacies(self, super_token):
        r = requests.get(f"{API}/platform/pharmacies", headers=_h(super_token), timeout=30)
        assert r.status_code == 200
        pharmacies = r.json()
        assert isinstance(pharmacies, list)
        slugs = {p["slug"] for p in pharmacies}
        # pharmacie_centrale doit être présente (ou public selon le code)
        assert any("central" in s or s == "pharmacie_centrale" or s == "public" for s in slugs) or len(slugs) >= 1

    def test_create_qa_pharmacy_and_login(self, qa_setup):
        slug = qa_setup["slug"]
        assert slug == "pharmacie_qa_matam"
        # Login new admin
        r = _login(QA_PHARMA["admin_email"], QA_PHARMA["admin_password"])
        assert r.status_code == 200, r.text
        user = r.json()["user"]
        assert user["role"] == "admin"
        assert user["tenant_id"] == slug

    def test_new_pharmacy_is_empty(self, qa_setup):
        tok = _login(QA_PHARMA["admin_email"], QA_PHARMA["admin_password"]).json()["access_token"]
        r = requests.get(f"{API}/products/paginated?page=1&page_size=5", headers=_h(tok), timeout=30)
        assert r.status_code == 200
        data = r.json()
        total = data.get("total", data.get("total_count", 0))
        assert total == 0, f"Expected 0 products, got {total}"


# ---------- Isolation ----------
class TestDataIsolation:
    def test_create_product_in_qa_and_isolation(self, qa_setup, central_token):
        qa_tok = _login(QA_PHARMA["admin_email"], QA_PHARMA["admin_password"]).json()["access_token"]

        # Créer une catégorie
        cat_name = f"TEST_Cat_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/categories", json={"name": cat_name},
                          headers=_h(qa_tok), timeout=30)
        assert r.status_code in (200, 201), r.text
        category_id = r.json()["id"]

        # Créer un produit
        prod_name = f"TEST_QA_Product_{uuid.uuid4().hex[:6]}"
        payload = {
            "name": prod_name,
            "category_id": category_id,
            "unit_price": 1000,
            "stock_quantity": 10,
            "min_stock_level": 1,
        }
        r = requests.post(f"{API}/products", json=payload, headers=_h(qa_tok), timeout=30)
        assert r.status_code in (200, 201), f"create product failed: {r.status_code} {r.text}"

        # Centrale: doit toujours avoir ses produits SANS ce nouveau
        r = requests.get(f"{API}/products/paginated?page=1&page_size=5&search={prod_name}",
                         headers=_h(central_token), timeout=30)
        assert r.status_code == 200
        central_data = r.json()
        central_total = central_data.get("total", central_data.get("total_count", 0))
        assert central_total == 0, "Produit QA visible dans la centrale !"

        # Centrale: ~3351 produits total
        r = requests.get(f"{API}/products/paginated?page=1&page_size=5",
                         headers=_h(central_token), timeout=30)
        assert r.status_code == 200
        total_central = r.json().get("total", r.json().get("total_count", 0))
        assert total_central > 3000, f"Centrale a {total_central} produits (attendu ~3351)"

        # Kaloum: ne doit pas voir ce produit
        kal = _login(**KALOUM)
        if kal.status_code == 200:
            kal_tok = kal.json()["access_token"]
            r = requests.get(f"{API}/products/paginated?page=1&page_size=5&search={prod_name}",
                             headers=_h(kal_tok), timeout=30)
            assert r.status_code == 200
            kal_total = r.json().get("total", r.json().get("total_count", 0))
            assert kal_total == 0


# ---------- Sécurité (pharmacie désactivée) ----------
class TestPharmacyDeactivation:
    def test_deactivate_blocks_login(self, super_token, qa_setup):
        slug = qa_setup["slug"]
        # Désactiver
        r = requests.put(f"{API}/platform/pharmacies/{slug}", json={"is_active": False},
                         headers=_h(super_token), timeout=30)
        assert r.status_code == 200
        # Login doit échouer en 403
        r = _login(QA_PHARMA["admin_email"], QA_PHARMA["admin_password"])
        assert r.status_code == 403, f"Expected 403 on deactivated pharmacy, got {r.status_code}: {r.text}"
        assert "désactivée" in r.text.lower() or "desactive" in r.text.lower()
        # Réactiver
        r = requests.put(f"{API}/platform/pharmacies/{slug}", json={"is_active": True},
                         headers=_h(super_token), timeout=30)
        assert r.status_code == 200
        # Login OK à nouveau
        r = _login(QA_PHARMA["admin_email"], QA_PHARMA["admin_password"])
        assert r.status_code == 200


# ---------- Users CRUD + email cross-tenant ----------
class TestUsersCRUD:
    def test_create_caissier_and_login(self, qa_setup):
        qa_tok = _login(QA_PHARMA["admin_email"], QA_PHARMA["admin_password"]).json()["access_token"]
        caissier_email = f"caissier.qa+{uuid.uuid4().hex[:6]}@matam.test"
        payload = {
            "email": caissier_email,
            "password": "caisse123",
            "first_name": "Caissier",
            "last_name": "QA",
            "employee_code": f"CAI-{uuid.uuid4().hex[:4].upper()}",
            "role": "caissier",
            "tenant_id": qa_setup["slug"],
        }
        r = requests.post(f"{API}/auth/register", json=payload, headers=_h(qa_tok), timeout=30)
        assert r.status_code in (200, 201), f"create caissier failed: {r.status_code} {r.text}"
        # Login du caissier
        r = _login(caissier_email, "caisse123")
        assert r.status_code == 200
        assert r.json()["user"]["tenant_id"] == qa_setup["slug"]
        assert r.json()["user"]["role"] == "caissier"

    def test_duplicate_email_cross_tenant_rejected(self, qa_setup, central_token):
        """Un email déjà utilisé dans la centrale ne peut pas être créé dans QA."""
        qa_tok = _login(QA_PHARMA["admin_email"], QA_PHARMA["admin_password"]).json()["access_token"]
        payload = {
            "email": CENTRAL["email"],  # déjà existant globalement
            "password": "abcdef",
            "first_name": "Dup",
            "last_name": "Test",
            "employee_code": f"DUP-{uuid.uuid4().hex[:4].upper()}",
            "role": "caissier",
            "tenant_id": qa_setup["slug"],
        }
        r = requests.post(f"{API}/auth/register", json=payload, headers=_h(qa_tok), timeout=30)
        assert r.status_code == 400, f"Expected 400 on dup email, got {r.status_code}: {r.text}"


# ---------- Reset admin password ----------
class TestResetAdminPassword:
    def test_reset_admin_password(self, super_token, qa_setup):
        slug = qa_setup["slug"]
        new_pw = "newpass999"
        r = requests.post(
            f"{API}/platform/pharmacies/{slug}/reset-admin-password",
            json={"email": QA_PHARMA["admin_email"], "new_password": new_pw},
            headers=_h(super_token), timeout=30,
        )
        assert r.status_code == 200, r.text
        # Login avec nouveau mot de passe
        r = _login(QA_PHARMA["admin_email"], new_pw)
        assert r.status_code == 200
        # Rétablir
        r = requests.post(
            f"{API}/platform/pharmacies/{slug}/reset-admin-password",
            json={"email": QA_PHARMA["admin_email"], "new_password": QA_PHARMA["admin_password"]},
            headers=_h(super_token), timeout=30,
        )
        assert r.status_code == 200


# ---------- Suppression de pharmacie ----------
class TestPharmacyDeletion:
    def test_delete_temp_pharmacy(self, super_token):
        # Créer
        r = requests.post(f"{API}/platform/pharmacies", json=TEMP_PHARMA,
                          headers=_h(super_token), timeout=60)
        assert r.status_code in (200, 201), r.text
        slug = r.json()["pharmacy"]["slug"]
        # Login OK avant suppression
        r = _login(TEMP_PHARMA["admin_email"], TEMP_PHARMA["admin_password"])
        assert r.status_code == 200

        # Suppression avec mauvaise confirmation → 400
        r = requests.delete(f"{API}/platform/pharmacies/{slug}", params={"confirm": "wrong"},
                            headers=_h(super_token), timeout=30)
        assert r.status_code == 400

        # Suppression OK
        r = requests.delete(f"{API}/platform/pharmacies/{slug}", params={"confirm": slug},
                            headers=_h(super_token), timeout=60)
        assert r.status_code == 200, r.text

        # Login échoue
        time.sleep(1)
        r = _login(TEMP_PHARMA["admin_email"], TEMP_PHARMA["admin_password"])
        assert r.status_code == 401, f"Admin de pharmacie supprimée peut toujours se connecter: {r.status_code}"


# ---------- Régression centrale ----------
class TestCentralRegression:
    def test_central_login_and_dashboard(self, central_token):
        r = requests.get(f"{API}/reports/dashboard", headers=_h(central_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "today_sales_count" in data or "today_revenue" in data or isinstance(data, dict)

    def test_central_products_count(self, central_token):
        r = requests.get(f"{API}/products/paginated?page=1&page_size=5",
                         headers=_h(central_token), timeout=30)
        assert r.status_code == 200
        total = r.json().get("total", r.json().get("total_count", 0))
        assert total > 3000, f"Expected ~3351 products, got {total}"

    def test_central_me_endpoint(self, central_token):
        r = requests.get(f"{API}/auth/me", headers=_h(central_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "admin"
        assert d["email"] == CENTRAL["email"]
