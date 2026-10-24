"""Iteration 46: pricing fallbacks (DEFAULT_MARKUP 1.4) + supply validations + summary endpoints."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
PRODUCT_ID = "0839bdd9-083a-4388-aba3-6a6c9d939246"


@pytest.fixture(scope="module")
def s():
    r = requests.post(f"{API}/auth/login", json={"email": "admin@pharmaflow.com", "password": "admin123"}, timeout=30)
    assert r.status_code == 200, r.text
    sess = requests.Session()
    sess.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return sess


@pytest.fixture(scope="module")
def supplier_id(s):
    r = s.get(f"{API}/suppliers", timeout=30)
    assert r.status_code == 200
    data = r.json()
    data = data.get("items", data) if isinstance(data, dict) else data
    assert len(data) > 0
    return data[0]["id"]


@pytest.fixture(scope="module")
def product(s):
    r = s.get(f"{API}/products/{PRODUCT_ID}", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


created = []


@pytest.fixture(scope="module", autouse=True)
def cleanup(s):
    yield
    for sid in created:
        s.delete(f"{API}/supplies/{sid}", timeout=30)


def _payload(supplier_id, **item_over):
    item = {"product_id": PRODUCT_ID, "quantity": 1, "unit_price": 777,
            "date_peremption": "2028-12-31T00:00:00"}
    item.update(item_over)
    return {"supplier_id": supplier_id, "invoice_number": f"TEST_INV_{uuid.uuid4().hex[:8]}", "items": [item]}


# Supply create: selling_price fallback
class TestSupplyFallback:
    def test_no_selling_price_uses_product_price(self, s, supplier_id, product):
        r = s.post(f"{API}/supplies", json=_payload(supplier_id), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        created.append(d["id"])
        it = d["items"][0]
        assert it["selling_price"] == product["price"], it
        assert it["selling_price"] != round(777 * 1.3)
        # product price must not change before validation
        p = s.get(f"{API}/products/{PRODUCT_ID}", timeout=30).json()
        assert p["price"] == product["price"]
        assert p.get("purchase_price") == product.get("purchase_price")
        assert p["stock"] == product["stock"]

    def test_explicit_selling_price_kept(self, s, supplier_id):
        r = s.post(f"{API}/supplies", json=_payload(supplier_id, selling_price=1234), timeout=30)
        assert r.status_code == 200, r.text
        created.append(r.json()["id"])
        assert r.json()["items"][0]["selling_price"] == 1234

    def test_get_supply_persisted(self, s):
        r = s.get(f"{API}/supplies/{created[0]}", timeout=30)
        assert r.status_code == 200
        assert r.json()["is_validated"] is False


# Supply create: mandatory fields
class TestSupplyValidation:
    def test_missing_supplier(self, s, supplier_id):
        p = _payload(supplier_id); p.pop("supplier_id")
        r = s.post(f"{API}/supplies", json=p, timeout=30)
        assert r.status_code == 400
        assert "fournisseur est obligatoire" in r.json()["detail"]

    def test_missing_invoice(self, s, supplier_id):
        p = _payload(supplier_id); p["invoice_number"] = "  "
        r = s.post(f"{API}/supplies", json=p, timeout=30)
        assert r.status_code == 400
        assert "facture" in r.json()["detail"].lower()

    def test_missing_expiry(self, s, supplier_id):
        p = _payload(supplier_id); p["items"][0].pop("date_peremption")
        r = s.post(f"{API}/supplies", json=p, timeout=30)
        assert r.status_code == 400
        assert "péremption" in r.json()["detail"]


# Summary endpoints
class TestSummaries:
    @pytest.mark.parametrize("path", ["/reports/dashboard", "/stock/valuation", "/prices/summary", "/stock/summary"])
    def test_ok(self, s, path):
        r = s.get(f"{API}{path}", timeout=60)
        assert r.status_code == 200, r.text
        assert r.json() is not None
