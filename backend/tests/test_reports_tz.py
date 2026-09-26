"""Tests for timezone-aware reports endpoints (fix for date consistency bug)"""
import os
import requests
import pytest
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://pharmacy-mgmt-portal.preview.emergentagent.com').rstrip('/')
TARGET_DATE = "2026-09-21"
EXPECTED_AMOUNT = 56168


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "admin@pharmaflow.com", "password": "admin123"})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json().get("access_token") or r.json().get("token")
    assert token
    return {"Authorization": f"Bearer {token}"}


# --- /reports/weekly ---
def test_weekly_contains_target_sale(auth_headers):
    r = requests.get(f"{BASE_URL}/api/reports/weekly", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "daily_stats" in data
    day = next((d for d in data["daily_stats"] if d["date"] == TARGET_DATE), None)
    assert day is not None, f"No entry for {TARGET_DATE} in weekly. Got: {[d['date'] for d in data['daily_stats']]}"
    assert day["revenue"] >= EXPECTED_AMOUNT, f"Expected revenue >= {EXPECTED_AMOUNT} on {TARGET_DATE}, got {day['revenue']}"
    assert day["sales_count"] >= 1


# --- /reports/today-sales-by-payment ---
def test_today_sales_by_payment_specific_date(auth_headers):
    r = requests.get(f"{BASE_URL}/api/reports/today-sales-by-payment",
                     params={"date": TARGET_DATE}, headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["date"] == TARGET_DATE
    assert data["total_revenue"] >= EXPECTED_AMOUNT
    assert data["total_sales"] >= 1
    cash = next((m for m in data["by_payment_method"] if m["method"] == "cash"), None)
    assert cash is not None, "cash payment missing"
    assert cash["total"] >= EXPECTED_AMOUNT


def test_today_sales_by_payment_no_date(auth_headers):
    r = requests.get(f"{BASE_URL}/api/reports/today-sales-by-payment", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    # date should be YYYY-MM-DD (len 10)
    assert isinstance(data["date"], str)
    assert len(data["date"]) == 10
    datetime.strptime(data["date"], "%Y-%m-%d")  # valid format


# --- /reports/dashboard ---
def test_dashboard(auth_headers):
    r = requests.get(f"{BASE_URL}/api/reports/dashboard", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "today_sales_count" in data
    assert "today_revenue" in data


# --- /reports/sales ---
def test_sales_report_30_days(auth_headers):
    r = requests.get(f"{BASE_URL}/api/reports/sales", params={"days": 30}, headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    ds = data["daily_stats"]
    assert isinstance(ds, dict)
    assert TARGET_DATE in ds, f"{TARGET_DATE} missing from daily_stats keys"
    assert ds[TARGET_DATE]["revenue"] >= EXPECTED_AMOUNT


# --- /reports/sales-summary ---
def test_sales_summary_target_day(auth_headers):
    r = requests.get(f"{BASE_URL}/api/reports/sales-summary",
                     params={"start_date": TARGET_DATE, "end_date": TARGET_DATE},
                     headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["start_date"] == TARGET_DATE
    assert data["end_date"] == TARGET_DATE
    assert data["total_revenue"] >= EXPECTED_AMOUNT
    assert data["total_sales"] >= 1


# --- /sales/paginated ---
def test_sales_paginated_date_filter(auth_headers):
    r = requests.get(f"{BASE_URL}/api/sales",
                     params={"date_from": TARGET_DATE, "date_to": TARGET_DATE, "limit": 100},
                     headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("items") or data.get("data") or data.get("sales") or []
    assert len(items) >= 1, f"No sales returned for {TARGET_DATE}: {data}"
    totals = [it.get("total") for it in items]
    assert any(t and t >= EXPECTED_AMOUNT for t in totals), f"Expected sale of {EXPECTED_AMOUNT} not found. Totals: {totals}"
