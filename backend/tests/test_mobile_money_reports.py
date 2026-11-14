# Regression: Mobile Money payments (no OTP) + accounting consistency of reports
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    with open('/app/frontend/.env') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                BASE_URL = line.split('=', 1)[1].strip().rstrip('/')


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@pharmaflow.com", "password": "admin123"})
    if r.status_code != 200:
        pytest.skip("login failed")
    s.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return s


def today():
    return datetime.now(ZoneInfo("Africa/Conakry")).strftime("%Y-%m-%d")


# today-sales-by-payment: sum of methods == total_revenue
def test_today_sales_by_payment_consistent(client):
    r = client.get(f"{BASE_URL}/api/reports/today-sales-by-payment")
    assert r.status_code == 200
    d = r.json()
    s = sum(m["total"] for m in d["by_payment_method"])
    assert abs(s - d["total_revenue"]) < 0.01
    labels = {m["method"] for m in d["by_payment_method"]}
    assert labels  # at least one method


# accounting-summary: cash_collected formula
def test_accounting_summary_cash_formula(client):
    t = today()
    r = client.get(f"{BASE_URL}/api/reports/accounting-summary", params={"start_date": t, "end_date": t})
    assert r.status_code == 200
    d = r.json()
    expected = d["sales"]["net_revenue"] - d["credit_sales"] + d["debt_payments"]["total"] - d["returns"]["total_refunded"]
    assert abs(d["cash_collected"] - expected) < 0.01


# accounting-summary vs today-sales-by-payment revenue agree
def test_reports_agree(client):
    t = today()
    a = client.get(f"{BASE_URL}/api/reports/accounting-summary", params={"start_date": t, "end_date": t}).json()
    b = client.get(f"{BASE_URL}/api/reports/today-sales-by-payment").json()
    assert abs(a["sales"]["gross_revenue"] - b["total_revenue"]) < 0.01


# mobile money sales store payment_details (sender_number + ticket_ref)
def test_mobile_money_sales_have_details(client):
    r = client.get(f"{BASE_URL}/api/sales", params={"limit": 50})
    assert r.status_code == 200
    sales = r.json() if isinstance(r.json(), list) else r.json().get("sales", [])
    mm = [s for s in sales if s.get("payment_method") in ("orange_money", "mtn_money") and not s.get("is_split_payment")]
    for s in mm[:5]:
        pd = s.get("payment_details") or {}
        assert pd.get("ticket_ref"), f"{s['sale_number']} missing ticket_ref"
        assert pd.get("sender_number"), f"{s['sale_number']} missing sender_number"


# debt payment history exposes payment_details for mobile money
def test_debt_payment_history_details(client):
    r = client.get(f"{BASE_URL}/api/debts/payments/history")
    assert r.status_code == 200
    mm = [p for p in r.json() if p.get("payment_method") in ("orange_money", "mtn_money")]
    if not mm:
        pytest.skip("no mobile money debt payments")
    assert (mm[0].get("payment_details") or {}).get("ticket_ref")
