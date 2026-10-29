# Customer credit-limit (max_debt_limit) admin-only permission tests
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
CID = "95972c73-b17f-4181-ad65-87f2b17b9b68"


def login(email, pwd):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd})
    if r.status_code != 200:
        pytest.skip(f"login failed {email}: {r.status_code} {r.text[:200]}")
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers["Authorization"] = f"Bearer {tok}"
    return s


@pytest.fixture(scope="module")
def admin():
    return login("admin@pharmaflow.com", "admin123")


@pytest.fixture(scope="module")
def pharma():
    return login("pharmacien@pharmaflow.com", "Pharma#2026")


@pytest.fixture(scope="module")
def original(admin):
    r = admin.get(f"{BASE_URL}/api/customers/{CID}")
    assert r.status_code == 200, r.text
    orig = r.json()
    yield orig
    admin.put(f"{BASE_URL}/api/customers/{CID}", json={"max_debt_limit": orig.get("max_debt_limit") or 0,
                                                       "phone": orig.get("phone") or ""})


def test_pharmacien_cannot_set_limit(pharma, original):
    r = pharma.put(f"{BASE_URL}/api/customers/{CID}", json={"max_debt_limit": 1000})
    assert r.status_code == 403
    assert "Seul un administrateur" in r.json()["detail"]


def test_admin_can_set_limit(admin, original):
    r = admin.put(f"{BASE_URL}/api/customers/{CID}", json={"max_debt_limit": 1000})
    assert r.status_code == 200, r.text
    assert r.json()["max_debt_limit"] == 1000
    g = admin.get(f"{BASE_URL}/api/customers/{CID}")
    assert g.json()["max_debt_limit"] == 1000


def test_pharmacien_phone_only(pharma, admin, original):
    r = pharma.put(f"{BASE_URL}/api/customers/{CID}", json={"phone": "620000001"})
    assert r.status_code == 200, r.text
    g = admin.get(f"{BASE_URL}/api/customers/{CID}").json()
    assert g["phone"] == "620000001"
    assert g["max_debt_limit"] == 1000


def test_paginated_contains_limit(admin, original):
    r = admin.get(f"{BASE_URL}/api/customers/paginated", params={"limit": 100})
    assert r.status_code == 200
    item = next((c for c in r.json()["items"] if c["id"] == CID), None)
    assert item is not None
    assert "max_debt_limit" in item, f"paginated item lacks max_debt_limit: {list(item.keys())}"


def test_pharmacien_create_forces_zero(pharma, admin):
    cur = pharma.get(f"{BASE_URL}/api/shifts/current")
    print("current shift:", cur.status_code, cur.text[:150])
    o = pharma.post(f"{BASE_URL}/api/shifts/open", json={"opening_amount": 0})
    print("open shift:", o.status_code, o.text[:200])
    r = pharma.post(f"{BASE_URL}/api/customers", json={"name": "TEST_seuil_client", "phone": "620999999",
                                                       "max_debt_limit": 50000})
    if r.status_code == 403 and "shift" in r.text.lower() or r.status_code == 400 and "shift" in r.text.lower():
        pytest.skip(f"shift required: {r.text}")
    assert r.status_code == 200, r.text
    data = r.json()
    try:
        assert data["max_debt_limit"] == 0
        g = admin.get(f"{BASE_URL}/api/customers/{data['id']}").json()
        assert g["max_debt_limit"] == 0
    finally:
        d = admin.delete(f"{BASE_URL}/api/customers/{data['id']}")
        assert d.status_code == 200
        assert admin.get(f"{BASE_URL}/api/customers/{data['id']}").status_code == 404


def test_put_undefined_id_matches_frontend_bug(admin):
    # Simulates what Customers.js now sends via useOfflineMutation: PUT /customers/undefined
    r = admin.put(f"{BASE_URL}/api/customers/undefined", json={"customerId": CID, "data": {"phone": "1"}})
    print("PUT /customers/undefined ->", r.status_code, r.text[:200])
    assert r.status_code in (404, 422, 500)
