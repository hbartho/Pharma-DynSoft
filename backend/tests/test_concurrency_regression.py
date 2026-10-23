"""Regression tests after async->def conversion & atomic sale/return transactions (Pharmacie Centrale only)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = "admin@pharmaflow.com"
ADMIN_PASS = "admin123"
SUFFIX = str(int(time.time()))[-6:]
STATE = {}


@pytest.fixture(scope="module")
def s():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, r.text
    sess = requests.Session()
    sess.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return sess


def stock_of(s, pid):
    r = s.get(f"{API}/products/{pid}", timeout=30)
    assert r.status_code == 200, r.text
    return r.json().get("stock")


# ---------- Auth ----------
def test_login_and_me(s):
    r = s.get(f"{API}/auth/me", timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["email"] == ADMIN_EMAIL


# ---------- Main GETs after async->def ----------
GETS = [
    "/products/paginated", "/sales", "/customers", "/debts/paginated", "/debts/dashboard",
    "/stock/movements/paginated", "/stock/losses/paginated", "/shifts/current", "/shifts/paginated",
    "/discounts/promo-codes", "/discounts/rules", "/settings", "/users", "/suppliers",
    "/supplies/paginated", "/supplier-debts", "/reports/dashboard", "/reports/accounting-summary",
    "/reports/weekly", "/categories", "/units", "/prices/history/paginated", "/inventory/sessions/history",
    "/returns/history", "/pending-sales", "/shift-schedules",
]


@pytest.mark.parametrize("path", GETS)
def test_get_endpoints(s, path):
    r = s.get(f"{API}{path}", timeout=60)
    assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:300]}"
    r.json()


# ---------- Product + stock + price + atomic sale ----------
def test_create_product_stock_price(s):
    r = s.post(f"{API}/products", json={"name": f"TEST-REGRESSION Produit {SUFFIX}"}, timeout=30)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    STATE["pid"] = pid
    r = s.post(f"{API}/stock/movement", json={"product_id": pid, "movement_type": "supply",
                                              "movement_quantity": 5, "notes": "TEST-REGRESSION"}, timeout=30)
    assert r.status_code == 200, r.text
    r = s.post(f"{API}/prices/update", json={"product_id": pid, "prix_appro": 1000, "prix_vente_prod": 1500, "change_type": "manual"}, timeout=30)
    assert r.status_code == 200, r.text
    assert stock_of(s, pid) == 5


def test_cash_sale_decrements_stock(s):
    pid = STATE["pid"]
    r = s.post(f"{API}/sales", json={"items": [{"product_id": pid, "quantity": 2, "unit_price": 1500}],
                                     "total": 3000, "payment_method": "cash"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["total"] == 3000
    STATE["sale_id"] = d["id"]
    assert stock_of(s, pid) == 3
    # persisted
    g = s.get(f"{API}/sales/{d['id']}", timeout=30)
    assert g.status_code == 200 and g.json()["id"] == d["id"]


def test_sale_insufficient_stock_409(s):
    pid = STATE["pid"]
    r = s.post(f"{API}/sales", json={"items": [{"product_id": pid, "quantity": 10, "unit_price": 1500}],
                                     "total": 15000, "payment_method": "cash"}, timeout=30)
    assert r.status_code == 409, r.text
    assert "Stock insuffisant" in r.json().get("detail", "")
    assert stock_of(s, pid) == 3


def test_sale_unknown_product_rollback(s):
    pid = STATE["pid"]
    r = s.post(f"{API}/sales", json={"items": [{"product_id": pid, "quantity": 1, "unit_price": 1500},
                                               {"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1, "unit_price": 100}],
                                     "total": 1600, "payment_method": "cash"}, timeout=30)
    assert r.status_code == 404, r.text
    assert stock_of(s, pid) == 3


# ---------- Customer + debt sale ----------
def test_customer_max_debt_limit(s):
    r = s.post(f"{API}/customers", json={"name": f"TEST-REGRESSION Client {SUFFIX}", "max_debt_limit": 5000}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json()["max_debt_limit"] == 5000
    STATE["cid"] = r.json()["id"]


def test_debt_sale_creates_debt(s):
    pid, cid = STATE["pid"], STATE["cid"]
    payload = {"items": [{"product_id": pid, "quantity": 2, "unit_price": 1500}], "total": 3000,
               "payment_method": "debt", "amount_paid": 0, "debt_amount": 3000, "customer_id": cid}
    r = s.post(f"{API}/sales", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    assert stock_of(s, pid) == 1
    r = s.get(f"{API}/debts/paginated", params={"customer_id": cid, "status": "all"}, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    items = d.get("items") or d.get("data") or d.get("debts") or []
    assert len(items) == 1, d
    amt = items[0].get("original_amount") or items[0].get("amount")
    assert float(amt) == 3000
    # second identical -> credit insufficient
    r = s.post(f"{API}/sales", json=payload, timeout=30)
    assert r.status_code == 400, r.text
    assert "Crédit insuffisant" in r.json().get("detail", "")
    assert stock_of(s, pid) == 1


# ---------- Returns ----------
def test_return_and_over_return(s):
    pid, sid = STATE["pid"], STATE["sale_id"]
    before = stock_of(s, pid)
    r = s.post(f"{API}/returns", json={"sale_id": sid, "reason": "TEST-REGRESSION",
                                       "items": [{"product_id": pid, "quantity": 1}]}, timeout=30)
    assert r.status_code == 200, r.text
    assert stock_of(s, pid) == before + 1
    r = s.post(f"{API}/returns", json={"sale_id": sid, "reason": "TEST-REGRESSION",
                                       "items": [{"product_id": pid, "quantity": 2}]}, timeout=30)
    assert r.status_code == 400, r.text
    assert stock_of(s, pid) == before + 1
