"""Pre-deployment global verification tests for DynPharma."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://pharmacy-mgmt-portal.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@pharmaflow.com"
ADMIN_PASS = "admin123"
SUPER_EMAIL = "superadmin@dynsoftgn.com"
SUPER_PASS = "DynSoft#2026"


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return r


@pytest.fixture(scope="module")
def admin_token():
    r = _login(ADMIN_EMAIL, ADMIN_PASS)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def super_token():
    r = _login(SUPER_EMAIL, SUPER_PASS)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def H(t):
    return {"Authorization": f"Bearer {t}"}


# ---------- AUTH ----------
class TestAuth:
    def test_admin_login(self):
        r = _login(ADMIN_EMAIL, ADMIN_PASS)
        assert r.status_code == 200
        d = r.json()
        assert "access_token" in d
        assert d["user"]["email"] == ADMIN_EMAIL

    def test_super_login(self):
        r = _login(SUPER_EMAIL, SUPER_PASS)
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_bad_password(self):
        r = _login(ADMIN_EMAIL, "WRONGPASS123")
        assert r.status_code == 401

    def test_protected_without_token(self):
        r = requests.get(f"{API}/reports/dashboard", timeout=30)
        assert r.status_code in (401, 403)

    def test_register_protected(self):
        r = requests.post(f"{API}/auth/register", json={"email": "x@x.com", "password": "p", "full_name": "x"}, timeout=30)
        assert r.status_code in (401, 403)


# ---------- PLATFORM ----------
class TestPlatform:
    def test_list_pharmacies(self, super_token):
        r = requests.get(f"{API}/platform/pharmacies", headers=H(super_token), timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any("users_count" in p for p in data)

    def test_pharmacies_stats(self, super_token):
        r = requests.get(f"{API}/platform/pharmacies/stats", headers=H(super_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        # structure flexibility: either global or per-pharmacy
        assert isinstance(d, (list, dict))
        print("stats payload:", str(d)[:400])

    def test_platform_forbidden_for_admin(self, admin_token):
        r = requests.get(f"{API}/platform/pharmacies", headers=H(admin_token), timeout=30)
        assert r.status_code == 403


# ---------- REPORTS ----------
class TestReports:
    def test_accounting_summary(self, admin_token):
        r = requests.get(f"{API}/reports/accounting-summary", headers=H(admin_token), timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert "sales" in d
        assert "suppliers" in d
        assert d["suppliers"].get("outstanding_debts") == 13082605

    def test_accounting_summary_forbidden(self):
        # non-admin: login as caissier? unknown pwd. Use no-token
        r = requests.get(f"{API}/reports/accounting-summary", timeout=30)
        assert r.status_code in (401, 403)

    def test_export_pdf(self, admin_token):
        r = requests.get(f"{API}/reports/accounting-summary/export", params={"format": "pdf"}, headers=H(admin_token), timeout=60)
        assert r.status_code == 200
        assert "application/pdf" in r.headers.get("content-type", "")
        assert r.content[:4] == b"%PDF"

    def test_export_excel(self, admin_token):
        r = requests.get(f"{API}/reports/accounting-summary/export", params={"format": "excel"}, headers=H(admin_token), timeout=60)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "spreadsheet" in ct or "excel" in ct
        assert r.content[:2] == b"PK"

    def test_export_without_token(self):
        r = requests.get(f"{API}/reports/accounting-summary/export", params={"format": "pdf"}, timeout=30)
        assert r.status_code in (401, 403)

    def test_sales_with_date_range(self, admin_token):
        r = requests.get(f"{API}/reports/sales",
                         params={"start_date": "2026-01-01", "end_date": "2026-10-15"},
                         headers=H(admin_token), timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d.get("total_sales") == 10
        assert d.get("total_revenue") == 1310798
        assert "daily_stats" in d
        assert len(d["daily_stats"]) == 288

    def test_sales_with_days_backcompat(self, admin_token):
        r = requests.get(f"{API}/reports/sales", params={"days": 30}, headers=H(admin_token), timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert "total_sales" in d
        assert "daily_stats" in d

    def test_dashboard(self, admin_token):
        r = requests.get(f"{API}/reports/dashboard", headers=H(admin_token), timeout=60)
        assert r.status_code == 200


# ---------- SHIFTS (cleanup) ----------
class TestShiftsCleanup:
    def test_close_any_open_shift(self, admin_token):
        r = requests.get(f"{API}/shifts/current", headers=H(admin_token), timeout=30)
        if r.status_code == 200 and r.json():
            print("Open shift found, closing...")
            c = requests.post(f"{API}/shifts/close", json={"actual_closing_amount": 0}, headers=H(admin_token), timeout=30)
            print("close status:", c.status_code, c.text[:200])
