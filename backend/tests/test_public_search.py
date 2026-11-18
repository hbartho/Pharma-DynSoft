# Public pharmacy search + platform public_search_enabled toggle
import os
import time
import pytest
import requests

def _base():
    url = os.environ.get('REACT_APP_BACKEND_URL')
    if not url:
        for line in open('/app/frontend/.env'):
            if line.startswith('REACT_APP_BACKEND_URL='):
                url = line.split('=', 1)[1].strip()
    return url.rstrip('/')

BASE_URL = _base()
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
SEARCH = f"{BASE_URL}/api/public/pharmacies/search"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update(UA)
    return sess


@pytest.fixture(scope="module")
def admin(s):
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "superadmin@dynsoftgn.com", "password": "DynSoft#2026"})
    if r.status_code != 200:
        pytest.skip(f"superadmin login failed {r.status_code}")
    h = dict(UA)
    h["Authorization"] = f"Bearer {r.json()['access_token']}"
    return h


def _names(data):
    return [p["name"].lower() for p in data["pharmacies"]]


class TestPublicSearch:
    def test_no_token_paracetamol(self, s):
        r = s.get(SEARCH, params={"product": "paracetamol"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["count"] >= 1 and d["count"] == len(d["pharmacies"])
        p = d["pharmacies"][0]
        for k in ("name", "address", "phone", "products", "total_matches"):
            assert k in p
        assert any("paracetamol" in n.lower() for n in p["products"])
        print(d)

    def test_short_product_422(self, s):
        assert s.get(SEARCH, params={"product": "pa"}).status_code == 422

    def test_missing_product_422(self, s):
        assert s.get(SEARCH).status_code == 422

    def test_no_result(self, s):
        d = s.get(SEARCH, params={"product": "zzzzqqq"}).json()
        assert d["count"] == 0 and d["pharmacies"] == []

    def test_location_conakry(self, s):
        d = s.get(SEARCH, params={"product": "paracetamol", "location": "conakry"}).json()
        print(d)
        assert d["count"] >= 1
        assert all("conakry" in p["address"].lower() for p in d["pharmacies"])

    def test_location_ratoma(self, s):
        d = s.get(SEARCH, params={"product": "paracetamol", "location": "ratoma"}).json()
        print(d)
        assert d["count"] >= 1
        assert any("test" in n for n in _names(d))
        assert all("ratoma" in p["address"].lower() for p in d["pharmacies"])

    def test_location_unknown(self, s):
        d = s.get(SEARCH, params={"product": "paracetamol", "location": "nowherevillezz"}).json()
        assert d["count"] == 0


class TestToggle:
    def test_toggle_hides_and_restores(self, s, admin):
        lst = s.get(f"{BASE_URL}/api/platform/pharmacies", headers=admin)
        assert lst.status_code == 200
        data = lst.json()
        items = data if isinstance(data, list) else data.get("pharmacies", data.get("items", []))
        test = next((p for p in items if p["slug"] == "test" or p["name"].lower() == "test"), None)
        assert test, [p["slug"] for p in items]
        assert "public_search_enabled" in test
        slug = test["slug"]
        try:
            r = s.put(f"{BASE_URL}/api/platform/pharmacies/{slug}", json={"public_search_enabled": False}, headers=admin)
            assert r.status_code == 200 and r.json()["public_search_enabled"] is False
            d = s.get(SEARCH, params={"product": "para"}).json()
            assert "test" not in _names(d), d
        finally:
            r = s.put(f"{BASE_URL}/api/platform/pharmacies/{slug}", json={"public_search_enabled": True}, headers=admin)
            assert r.status_code == 200 and r.json()["public_search_enabled"] is True
        d = s.get(SEARCH, params={"product": "para"}).json()
        assert "test" in _names(d)

    def test_non_admin_cannot_toggle(self, s):
        r = s.put(f"{BASE_URL}/api/platform/pharmacies/test", json={"public_search_enabled": False}, headers=UA)
        assert r.status_code in (401, 403)
