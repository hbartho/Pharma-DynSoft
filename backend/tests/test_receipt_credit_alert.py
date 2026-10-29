# Tests: receipt settings fields, supply->stock setup, customer credit limit & available-credit (iteration 50)
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
CUSTOMER_ID = "95972c73-b17f-4181-ad65-87f2b17b9b68"
PRODUCT_ID = "0839bdd9-083a-4388-aba3-6a6c9d939246"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "admin@pharmaflow.com", "password": "admin123"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


# --- Settings: new receipt fields ---
class TestReceiptSettings:
    def test_defaults_present(self, admin):
        d = admin.get(f"{API}/settings").json()
        for k in ("pharmacy_address", "pharmacy_phone", "receipt_footer", "receipt_print_prompt"):
            assert k in d

    def test_update_and_persist(self, admin):
        orig = admin.get(f"{API}/settings").json()
        payload = {"pharmacy_address": "TEST_Kaloum, Conakry", "pharmacy_phone": "+224 620 11 22 33",
                   "receipt_footer": "TEST_Merci et a bientot", "receipt_print_prompt": False}
        r = admin.put(f"{API}/settings", json=payload)
        assert r.status_code == 200, r.text
        d = admin.get(f"{API}/settings").json()
        assert d["pharmacy_address"] == payload["pharmacy_address"]
        assert d["pharmacy_phone"] == payload["pharmacy_phone"]
        assert d["receipt_footer"] == payload["receipt_footer"]
        assert d["receipt_print_prompt"] is False
        # restore
        admin.put(f"{API}/settings", json={k: orig[k] for k in payload})
        d2 = admin.get(f"{API}/settings").json()
        assert d2["receipt_print_prompt"] is True
        assert d2["pharmacy_address"] == orig["pharmacy_address"]

    def test_non_admin_forbidden(self):
        r = requests.put(f"{API}/settings", json={"receipt_footer": "x"})
        assert r.status_code in (401, 403)


# --- Stock setup through supply (needed for UI sales) ---
class TestStockSetup:
    def test_open_shift_and_supply(self, admin):
        cur = admin.get(f"{API}/shifts/current")
        if cur.status_code != 200 or not cur.json():
            r = admin.post(f"{API}/shifts/open", json={"opening_amount": 0})
            assert r.status_code in (200, 201), r.text
        sup = admin.get(f"{API}/suppliers").json()[0]
        exp = (datetime.now(timezone.utc) + timedelta(days=400)).isoformat()
        r = admin.post(f"{API}/supplies", json={
            "supplier_id": sup["id"], "invoice_number": f"TEST_INV_{uuid.uuid4().hex[:8]}",
            "items": [{"product_id": PRODUCT_ID, "quantity": 100, "unit_price": 1100, "date_peremption": exp, "lot_number": "TESTLOT"}]})
        assert r.status_code in (200, 201), r.text
        sid = r.json().get("id")
        v = admin.post(f"{API}/supplies/{sid}/validate")
        assert v.status_code == 200, v.text
        p = admin.get(f"{API}/products/{PRODUCT_ID}").json()
        assert p["stock"] >= 100


# --- Customer credit limit ---
class TestCreditLimit:
    def test_set_limit_and_available_credit(self, admin):
        c = admin.get(f"{API}/customers/{CUSTOMER_ID}").json()
        r = admin.put(f"{API}/customers/{CUSTOMER_ID}", json={"name": c["name"], "max_debt_limit": 20000})
        assert r.status_code == 200, r.text
        ac = admin.get(f"{API}/debts/customer/{CUSTOMER_ID}/available-credit")
        assert ac.status_code == 200, ac.text
        d = ac.json()
        assert d["max_debt_limit"] == 20000
        assert d["can_use_credit"] is True
        assert d["available_credit"] == 20000 - d["current_debt"]
