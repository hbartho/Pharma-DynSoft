# Stock lots remaining quantity (FIFO) & stock coherence tests - read-only
import os
import pytest
import requests
from collections import defaultdict

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@pharmaflow.com", "password": "admin123"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def lots(client):
    r = client.get(f"{BASE_URL}/api/stock-lots")
    assert r.status_code == 200, r.text[:300]
    return r.json()


@pytest.fixture(scope="module")
def products(client):
    r = client.get(f"{BASE_URL}/api/products")
    assert r.status_code == 200
    d = r.json()
    return d if isinstance(d, list) else d.get("items") or d.get("products") or []


def find_product(products, name):
    return next((p for p in products if p.get("name", "").upper().startswith(name)), None)


# Lots fields
def test_lot_fields(lots):
    assert len(lots) > 0
    for l in lots:
        for k in ("initial_quantity", "current_quantity", "product_stock"):
            assert k in l and isinstance(l[k], int)
        assert 0 <= l["current_quantity"]


def test_current_le_initial_and_sum_equals_stock(lots):
    by = defaultdict(list)
    for l in lots:
        by[l["product_id"]].append(l)
    bad = []
    for pid, g in by.items():
        received = sum(x["initial_quantity"] for x in g)
        stock = g[0]["product_stock"]
        if stock <= received:
            for x in g:
                if x["current_quantity"] > x["initial_quantity"]:
                    bad.append((x["product_name"], "cur>init"))
            s = sum(x["current_quantity"] for x in g)
            if s != stock:
                bad.append((g[0]["product_name"], s, stock))
    assert not bad, bad


def test_paracetamol_lot(lots):
    p = [l for l in lots if l["product_name"].upper().startswith("PARACETAMOL 500")]
    assert p, "no paracetamol lot"
    assert sum(l["initial_quantity"] for l in p) == 20
    assert sum(l["current_quantity"] for l in p) == 18
    assert p[0]["product_stock"] == 18


def test_ibuprofene_lots(lots):
    p = [l for l in lots if l["product_name"].upper().startswith("IBUPROFENE 400")]
    m = {l["initial_quantity"]: l["current_quantity"] for l in p}
    assert m.get(12) == 6 and m.get(8) == 8, p
    assert p[0]["product_stock"] == 14


def test_product_lots_endpoint_and_by_supply(client, lots):
    p = next(l for l in lots if l["product_name"].upper().startswith("IBUPROFENE 400"))
    r = client.get(f"{BASE_URL}/api/stock-lots/product/{p['product_id']}/lots")
    assert r.status_code == 200
    assert sum(x["current_quantity"] for x in r.json()) == 14
    r2 = client.get(f"{BASE_URL}/api/stock-lots/by-supply/{p['supply_id']}")
    assert r2.status_code == 200
    mine = [x for x in r2.json() if x["id"] == p["id"]]
    assert mine and mine[0]["current_quantity"] == p["current_quantity"]


def test_paracetamol_stock_vs_movements(client, products):
    p = find_product(products, "PARACETAMOL 500")
    assert p and p["stock"] == 18
    r = client.get(f"{BASE_URL}/api/stock/movements/paginated", params={"product_id": p["id"], "limit": 100})
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    items = d if isinstance(d, list) else d.get("items") or d.get("movements") or d.get("data") or []
    total = 0
    for m in items:
        q = m.get("quantity", 0)
        t = (m.get("type") or m.get("movement_type") or "").lower()
        if t in ("out", "sortie", "sale") and q > 0:
            q = -q
        total += q
    print("movements", [(m.get("type") or m.get("movement_type"), m.get("quantity")) for m in items])
    assert total == p["stock"]


def test_invalid_lot_ids(client):
    assert client.get(f"{BASE_URL}/api/stock-lots/product/abc/lots").json() == []
    assert client.get(f"{BASE_URL}/api/stock-lots/not-a-uuid").status_code == 404
