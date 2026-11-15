import requests, json
BASE = "https://pharmacy-mgmt-portal.preview.emergentagent.com"
s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) Chrome/120"
r = s.post(f"{BASE}/api/auth/login", json={"email": "admin@pharmaflow.com", "password": "admin123"})
print(r.status_code, list(r.json().keys()))
tok = r.json().get("access_token") or r.json().get("token")
if tok:
    s.headers["Authorization"] = f"Bearer {tok}"
r = s.get(f"{BASE}/api/supplies/import/template", params={"format": "csv"})
print("template", r.status_code, r.text[:500])
r = s.get(f"{BASE}/api/products", params={"search": "para"})
d = r.json()
items = d if isinstance(d, list) else d.get("items") or d.get("products") or d
print(type(d), (list(d.keys()) if isinstance(d, dict) else len(d)))
for p in (items[:5] if isinstance(items, list) else []):
    print({k: p.get(k) for k in ("id", "name", "price", "selling_price", "stock", "is_active")})
r = s.get(f"{BASE}/api/suppliers")
print("suppliers", r.status_code, str(r.json())[:300])
r = s.get(f"{BASE}/api/shifts/current")
print("shift", r.status_code, str(r.text)[:300])
print("----")
r = s.get(f"{BASE}/api/products")
ps=r.json()
c=[p for p in ps if p.get('stock',0)>5 and (p.get('price') or 0)>=2000 and p.get('is_active')]
for p in c[:8]: print(p['id'],p['name'],p['price'],p['stock'],p.get('reference'),p.get('barcode'))
print([p['name'] for p in ps if 'PARACETAMOL' in p['name'].upper()][:5])
