# Tests: « Crédit » (code credit) payment = debt sale (single + split), credit limit refusal, cleanup (iteration 50)
import os

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"
CUSTOMER_ID = "95972c73-b17f-4181-ad65-87f2b17b9b68"
PRODUCT_ID = "0839bdd9-083a-4388-aba3-6a6c9d939246"
CREATED_SALES = []


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "admin@pharmaflow.com", "password": "admin123"})
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    cur = s.get(f"{API}/shifts/current")
    if cur.status_code != 200 or not cur.json():
        s.post(f"{API}/shifts/open", json={"opening_amount": 0})
    c = s.get(f"{API}/customers/{CUSTOMER_ID}").json()
    s.put(f"{API}/customers/{CUSTOMER_ID}", json={"name": c["name"], "max_debt_limit": 20000})
    yield s
    # cleanup: settle debts created by this module
    for d in s.get(f"{API}/debts/customer/{CUSTOMER_ID}").json():
        if d.get("sale_id") in CREATED_SALES and d.get("remaining_amount", 0) > 0:
            s.post(f"{API}/debts/payment", json={"debt_id": d["id"], "amount": d["remaining_amount"], "payment_method": "cash", "notes": "TEST_cleanup"})


def _current_debt(admin):
    return admin.get(f"{API}/debts/customer/{CUSTOMER_ID}/available-credit").json()["current_debt"]


def _sale(admin, **extra):
    payload = {"customer_id": CUSTOMER_ID, "items": [{"product_id": PRODUCT_ID, "quantity": 1, "unit_price": 1600}],
               "subtotal": 1600, "total": 1600, "payment_method": "credit"}
    payload.update(extra)
    return admin.post(f"{API}/sales", json=payload)


class TestCreditSale:
    def test_single_credit_sale_creates_debt(self, admin):
        before = _current_debt(admin)
        r = _sale(admin)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        CREATED_SALES.append(d["id"])
        assert d["has_debt"] is True
        assert d["debt_amount"] == 1600
        assert d["amount_paid"] == 0
        g = admin.get(f"{API}/sales/{d['id']}").json()
        assert g["has_debt"] is True and g["debt_amount"] == 1600
        debts = [x for x in admin.get(f"{API}/debts/customer/{CUSTOMER_ID}").json() if x.get("sale_id") == d["id"]]
        assert len(debts) == 1 and debts[0]["remaining_amount"] == 1600
        assert _current_debt(admin) == before + 1600

    def test_split_cash_credit(self, admin):
        before = _current_debt(admin)
        r = _sale(admin, payment_method="cash", is_split_payment=True,
                  split_payments=[{"method": "cash", "amount": 1000}, {"method": "credit", "amount": 600}])
        assert r.status_code in (200, 201), r.text
        d = r.json()
        CREATED_SALES.append(d["id"])
        assert d["has_debt"] is True
        assert d["debt_amount"] == 600
        assert d["amount_paid"] == 1000
        assert _current_debt(admin) == before + 600

    def test_credit_over_limit_refused(self, admin):
        r = _sale(admin, items=[{"product_id": PRODUCT_ID, "quantity": 13, "unit_price": 1600}], subtotal=20800, total=20800)
        assert r.status_code == 400, r.text
        assert "Crédit insuffisant" in r.json()["detail"]

    def test_credit_without_customer_refused(self, admin):
        r = _sale(admin, customer_id=None)
        assert r.status_code == 400, r.text
