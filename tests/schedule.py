import sys, requests
BASE = "https://pharmacy-mgmt-portal.preview.emergentagent.com"
s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) Chrome/120"
tok = s.post(f"{BASE}/api/auth/login", json={"email": "admin@pharmaflow.com", "password": "admin123"}).json()["access_token"]
s.headers["Authorization"] = f"Bearer {tok}"
if sys.argv[1] == "create":
    users = s.get(f"{BASE}/api/users").json()
    u = [x for x in users if x.get("email") == "caissier@pharmaflow.com"][0]
    r = s.post(f"{BASE}/api/shift-schedules", json={"user_id": u["id"], "scheduled_date": sys.argv[2], "start_time": "00:00", "end_time": "23:59", "max_duration_hours": 8, "notes": "TEST_schedule"})
    print(r.status_code, r.text[:300])
else:
    r = s.delete(f"{BASE}/api/shift-schedules/{sys.argv[2]}")
    print(r.status_code, r.text[:200])
