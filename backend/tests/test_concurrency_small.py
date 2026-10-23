"""Small-scale concurrency check (4 parallel sales on stock=2) - safe for shared prod DB."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
import requests

API = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/") + "/api"


def test_parallel_sales_no_oversell():
    tok = requests.post(f"{API}/auth/login", json={"email": "admin@pharmaflow.com", "password": "admin123"}, timeout=30).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    pid = requests.post(f"{API}/products", json={"name": f"TEST-REGRESSION Concurrence {int(time.time())}"}, headers=H, timeout=30).json()["id"]
    r = requests.post(f"{API}/stock/movement", json={"product_id": pid, "movement_type": "supply", "movement_quantity": 2, "notes": "TEST-REGRESSION"}, headers=H, timeout=30)
    assert r.status_code == 200, r.text

    def sell(_):
        return requests.post(f"{API}/sales", json={"items": [{"product_id": pid, "quantity": 1, "unit_price": 100}], "total": 100, "payment_method": "cash"}, headers=H, timeout=60).status_code

    with ThreadPoolExecutor(max_workers=4) as ex:
        codes = list(ex.map(sell, range(4)))
    print("codes", codes)
    stock = requests.get(f"{API}/products/{pid}", headers=H, timeout=30).json()["stock"]
    assert codes.count(200) == 2, codes
    assert codes.count(409) == 2, codes
    assert stock == 0
