import os, sys, requests, json
API = os.environ['API'] + '/api'
H = {'Authorization': 'Bearer ' + os.environ['TOKEN']}
def g(u): return requests.get(f"{API}{u}", headers=H).json()
def items(d): return d.get('items', d) if isinstance(d, dict) else d

prods = [p for p in items(g("/products?limit=20")) if (p.get('stock') or 0) >= 0][:2]
pA, pB = prods[0], prods[1]
sup = items(g("/suppliers"))[0]
print("A:", pA['name'], "stock", pA['stock'], "prix", pA['price'], "| B:", pB['name'], "stock", pB['stock'])

# 1. créer + valider un appro : A x10 @1000 -> public 1500 ; B x4 @500 -> 800
r = requests.post(f"{API}/supplies", headers=H, json={
    "supply_date": "2026-10-24", "supplier_id": sup['id'], "invoice_number": "F-CORR-TEST",
    "items": [
        {"product_id": pA['id'], "quantity": 10, "unit_price": 1000, "selling_price": 1500, "date_peremption": "2028-06-30", "lot_number": "LA"},
        {"product_id": pB['id'], "quantity": 4, "unit_price": 500, "selling_price": 800, "date_peremption": "2028-06-30"},
    ]})
assert r.status_code == 200, r.text
sid = r.json()['id']; print("appro créé", sid)
r = requests.post(f"{API}/supplies/{sid}/validate", headers=H); assert r.status_code == 200, r.text
det = g(f"/supplies/{sid}")
a_after = g(f"/products/{pA['id']}"); b_after = g(f"/products/{pB['id']}")
print("après validation: A stock", a_after['stock'], "prix", a_after['price'], "cession", a_after['purchase_price'], "| B stock", b_after['stock'], "| total", det['total_amount'])
debt = [d for d in items(g("/supplier-debts")) if d.get('supply_id') == sid]
print("dette:", debt[0]['original_amount'] if debt else None)

# 2. correction sans motif -> 400
r = requests.put(f"{API}/supplies/{sid}/correct", headers=H, json={"items": det['items']})
print("sans motif:", r.status_code, r.json().get('detail'))

# 3. correction : A 10 -> 7 (prix 1000->1100, public 1500->1600), B supprimé, nouvelle ligne A x2 lot LB
itA = [i for i in det['items'] if i['product_id'] == pA['id']][0]
body = {"correction_reason": "Erreur de saisie BL", "supplier_id": sup['id'], "invoice_number": "F-CORR-TEST",
        "items": [
            {"id": itA['id'], "product_id": pA['id'], "quantity": 7, "unit_price": 1100, "selling_price": 1600, "date_peremption": "2028-06-30", "lot_number": "LA"},
            {"product_id": pA['id'], "quantity": 2, "unit_price": 1100, "selling_price": 1600, "date_peremption": "2029-01-31", "lot_number": "LB"},
        ]}
r = requests.put(f"{API}/supplies/{sid}/correct", headers=H, json=body)
print("correction:", r.status_code, r.json().get('detail') or {k: r.json()[k] for k in ('total_amount', 'stock_adjustments', 'price_updates')})
a2 = g(f"/products/{pA['id']}"); b2 = g(f"/products/{pB['id']}")
print("A stock attendu", a_after['stock'] - 1, "obtenu", a2['stock'], "| prix", a2['price'], "cession", a2['purchase_price'])
print("B stock attendu", b_after['stock'] - 4, "obtenu", b2['stock'])
det2 = g(f"/supplies/{sid}")
print("lignes:", [(i['lot_number'], i['quantity'], i['purchase_price'], i['selling_price']) for i in det2['items']], "total", det2['total_amount'])
print("notes:", det2['notes'])
debt = [d for d in items(g("/supplier-debts")) if d.get('supply_id') == sid]
print("dette:", debt[0]['original_amount'], debt[0]['remaining_amount'], debt[0]['status'])
mv = items(g("/stock/movements/paginated?limit=5"))
print("mouvements:", [(m.get('product_name'), m.get('quantity'), m.get('reason')) for m in mv if 'Correction' in (m.get('reason') or '')][:3])

# 4. refus : réduire A en dessous du stock disponible -> mettre quantité 0 impossible, simuler : A total 9 -> 1 alors que stock = ? 
stock_now = a2['stock']
r = requests.put(f"{API}/supplies/{sid}/correct", headers=H, json={**body, "correction_reason": "test refus",
    "items": [{"id": itA['id'], "product_id": pA['id'], "quantity": 1, "unit_price": 1100, "selling_price": 1600, "date_peremption": "2028-06-30"}]})
print("réduction 9->1 (stock", stock_now, "):", r.status_code, r.json().get('detail'))

# 5. remettre l'état initial : A 10 lignes? -> restaurer stocks via correction inverse: A total -> (stock A initial) ; simplest : corriger vers A x10 @1000/1500 + B x4 @500/800, puis on laisse l'appro (validé, non supprimable)
r = requests.put(f"{API}/supplies/{sid}/correct", headers=H, json={"correction_reason": "retour état initial test", "supplier_id": sup['id'], "invoice_number": "F-CORR-TEST",
    "items": [{"id": itA['id'], "product_id": pA['id'], "quantity": 10, "unit_price": pA.get('purchase_price') or 1000, "selling_price": pA['price'], "date_peremption": "2028-06-30", "lot_number": "LA"},
              {"product_id": pB['id'], "quantity": 4, "unit_price": pB.get('purchase_price') or 500, "selling_price": pB['price'], "date_peremption": "2028-06-30"}]})
print("restauration:", r.status_code)
a3 = g(f"/products/{pA['id']}"); print("A final stock", a3['stock'], "(initial", pA['stock'], "+10) prix", a3['price'], "(initial", pA['price'], ")")
print("SUPPLY_ID", sid)
