"""Test de concurrence : 20 ventes simultanées sur un produit à stock 10 → exactement 10 réussites.
Usage: python tests/concurrency_sales_test.py <API_BASE> <email> <password>
"""
import sys
import uuid
import requests
from concurrent.futures import ThreadPoolExecutor

API, EMAIL, PWD = sys.argv[1], sys.argv[2], sys.argv[3]
tok = requests.post(f"{API}/auth/login", json={"email": EMAIL, "password": PWD}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

# Produit de test avec stock 10 (le stock n'est modifiable que via un approvisionnement ou un mouvement)
name = f"ConcTest {uuid.uuid4().hex[:6]}"
prod = requests.post(f"{API}/products", json={"name": name}, headers=H).json()
pid = prod["id"]
def add_stock(q):
    return requests.post(f"{API}/stock/movement", json={"product_id": pid, "movement_type": "supply", "movement_quantity": q, "notes": "test"}, headers=H)
r = add_stock(10)
print("stock init:", r.status_code, r.text[:120])
requests.post(f"{API}/prices/update", json={"product_id": pid, "prix_appro": 1000, "prix_vente_prod": 1500}, headers=H)
stock = requests.get(f"{API}/products/{pid}", headers=H).json().get("stock")
print("stock avant:", stock)


def sell(_):
    body = {"items": [{"product_id": pid, "quantity": 1, "unit_price": 1500}], "total": 1500, "payment_method": "cash"}
    r = requests.post(f"{API}/sales", json=body, headers=H)
    return r.status_code


with ThreadPoolExecutor(max_workers=20) as ex:
    codes = list(ex.map(sell, range(20)))
ok = codes.count(200) + codes.count(201)
conflicts = codes.count(409)
after = requests.get(f"{API}/products/{pid}", headers=H).json().get("stock")
print(f"réussites={ok} refus_stock(409)={conflicts} autres={[c for c in codes if c not in (200,201,409)]} stock après={after}")
assert ok == 10 and conflicts == 10 and after == 0, "CONCURRENCE KO"

# Rollback : panier avec un produit inexistant → le stock du produit valide ne bouge pas
add_stock(5)
before = requests.get(f"{API}/products/{pid}", headers=H).json().get("stock")
r = requests.post(f"{API}/sales", json={"items": [{"product_id": pid, "quantity": 1, "unit_price": 1500}, {"product_id": str(uuid.uuid4()), "quantity": 1, "unit_price": 1}], "total": 1501, "payment_method": "cash"}, headers=H)
after2 = requests.get(f"{API}/products/{pid}", headers=H).json().get("stock")
print(f"rollback: status={r.status_code} stock {before} -> {after2}")
assert r.status_code == 404 and before == after2, "ROLLBACK KO"

# Dette client : limite 5000, vente à crédit 3000 OK, seconde 3000 refusée, dette enregistrée
cust = requests.post(f"{API}/customers", json={"name": f"Client {uuid.uuid4().hex[:4]}", "max_debt_limit": 5000}, headers=H).json()
body = {"customer_id": cust["id"], "items": [{"product_id": pid, "quantity": 2, "unit_price": 1500}], "total": 3000, "payment_method": "debt", "amount_paid": 0, "debt_amount": 3000}
r1 = requests.post(f"{API}/sales", json=body, headers=H)
r2 = requests.post(f"{API}/sales", json=body, headers=H)
debts = requests.get(f"{API}/debts/paginated", params={"customer_id": cust["id"], "status": "all"}, headers=H).json()
n_debts = debts.get("total") if isinstance(debts, dict) else len(debts)
print(f"crédit: 1ère={r1.status_code} 2ème={r2.status_code} ({r2.json().get('detail','')[:60]}) dettes={n_debts}")
assert r1.status_code in (200, 201) and r2.status_code == 400 and n_debts == 1, "DETTE KO"
print("TOUS LES TESTS DE CONCURRENCE OK")

# Approvisionnement : 5 validations simultanées → stock +10 une seule fois
before = requests.get(f"{API}/products/{pid}", headers=H).json().get("stock")
sup = requests.post(f"{API}/supplies", json={"items": [{"product_id": pid, "quantity": 10, "unit_price": 1000}]}, headers=H).json()
with ThreadPoolExecutor(max_workers=5) as ex:
    vcodes = list(ex.map(lambda _: requests.post(f"{API}/supplies/{sup['id']}/validate", headers=H).status_code, range(5)))
after3 = requests.get(f"{API}/products/{pid}", headers=H).json().get("stock")
print(f"appro: validations={vcodes} stock {before} -> {after3}")
assert vcodes.count(200) == 1 and after3 == before + 10, "APPRO KO"

# Retours : 2 retours simultanés de la totalité d'une vente → un seul accepté
sale = requests.post(f"{API}/sales", json={"items": [{"product_id": pid, "quantity": 3, "unit_price": 1500}], "total": 4500, "payment_method": "cash"}, headers=H).json()
before = requests.get(f"{API}/products/{pid}", headers=H).json().get("stock")
ret_body = {"sale_id": sale["id"], "reason": "test concurrence", "items": [{"product_id": pid, "quantity": 3}]}
with ThreadPoolExecutor(max_workers=2) as ex:
    rcodes = list(ex.map(lambda _: requests.post(f"{API}/returns", json=ret_body, headers=H).status_code, range(2)))
after4 = requests.get(f"{API}/products/{pid}", headers=H).json().get("stock")
print(f"retours: {rcodes} stock {before} -> {after4}")
assert rcodes.count(200) == 1 and after4 == before + 3, "RETOUR KO"
print("TESTS APPRO/RETOURS OK")
