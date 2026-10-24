# Tests: correction d'un approvisionnement validé (PUT /api/supplies/{id}/correct) + régression update/validate
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
API = f"{BASE_URL}/api"


def _login(email, pwd):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd})
    if r.status_code != 200:
        pytest.skip(f"login failed {email}: {r.status_code}")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def items(d):
    return d.get('items', d) if isinstance(d, dict) else d


@pytest.fixture(scope="module")
def admin():
    return _login("admin@pharmaflow.com", "admin123")


@pytest.fixture(scope="module")
def pharma():
    return _login("pharmacien@pharmaflow.com", "Pharma#2026")


def g(h, u):
    r = requests.get(f"{API}{u}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def ctx(admin):
    prods = [p for p in items(g(admin, "/products?limit=40")) if (p.get('stock') or 0) >= 0]
    pA, pB = prods[0], prods[1]
    sup = items(g(admin, "/suppliers"))[0]
    inv = f"TEST_CORR_{uuid.uuid4().hex[:8]}"
    r = requests.post(f"{API}/supplies", headers=admin, json={
        "supply_date": "2026-01-10", "supplier_id": sup['id'], "invoice_number": inv,
        "items": [
            {"product_id": pA['id'], "quantity": 10, "unit_price": 1000, "selling_price": 1500, "date_peremption": "2028-06-30", "lot_number": "LA"},
            {"product_id": pB['id'], "quantity": 4, "unit_price": 500, "selling_price": 800, "date_peremption": "2028-06-30"},
        ]})
    assert r.status_code == 200, r.text
    sid = r.json()['id']
    c = {"pA": pA, "pB": pB, "sup": sup, "inv": inv, "sid": sid, "number": r.json().get('supply_number')}
    yield c
    # Teardown : restore prices via correction, then stock via manual movements (validated supply can't be deleted)
    try:
        det = g(admin, f"/supplies/{sid}")
        if det.get('is_validated'):
            itA = [i for i in det['items'] if i['product_id'] == pA['id']][0]
            requests.put(f"{API}/supplies/{sid}/correct", headers=admin, json={
                "correction_reason": "TEST restore", "supplier_id": sup['id'], "invoice_number": inv,
                "items": [{"id": itA['id'], "product_id": pA['id'], "quantity": 10, "unit_price": pA.get('purchase_price') or 1000, "selling_price": pA['price'], "date_peremption": "2028-06-30", "lot_number": "LA"},
                          {"product_id": pB['id'], "quantity": 4, "unit_price": pB.get('purchase_price') or 500, "selling_price": pB['price'], "date_peremption": "2028-06-30"}]})
            for p, q in ((pA, 10), (pB, 4)):
                cur = g(admin, f"/products/{p['id']}")['stock']
                diff = cur - (p['stock'] or 0)
                if diff > 0:
                    requests.post(f"{API}/stock/movement", headers=admin, json={"product_id": p['id'], "movement_type": "adjustment", "movement_quantity": diff, "notes": "TEST restore"})
                elif diff < 0:
                    requests.post(f"{API}/stock/movement", headers=admin, json={"product_id": p['id'], "movement_type": "return", "movement_quantity": -diff, "notes": "TEST restore"})
        print("TEST SUPPLY ID (validated, not deletable):", sid)
    except Exception as e:
        print("teardown error", e)


class TestSupplyCorrection:
    def test_01_correct_non_validated_400(self, admin, ctx):
        det = g(admin, f"/supplies/{ctx['sid']}")
        r = requests.put(f"{API}/supplies/{ctx['sid']}/correct", headers=admin, json={"correction_reason": "x", "items": det['items']})
        assert r.status_code == 400
        assert "pas validé" in r.json()['detail']

    def test_02_regression_normal_update_and_required_fields(self, admin, ctx):
        det = g(admin, f"/supplies/{ctx['sid']}")
        body = {"supplier_id": ctx['sup']['id'], "invoice_number": ctx['inv'], "items": [
            {"product_id": ctx['pA']['id'], "quantity": 10, "unit_price": 1000, "selling_price": 1500, "date_peremption": "2028-06-30", "lot_number": "LA"},
            {"product_id": ctx['pB']['id'], "quantity": 4, "unit_price": 500, "selling_price": 800, "date_peremption": "2028-06-30"}],
            "notes": "TEST note"}
        r = requests.put(f"{API}/supplies/{ctx['sid']}", headers=admin, json=body)
        assert r.status_code == 200, r.text
        assert r.json()['total_amount'] == 12000
        # required invoice
        r = requests.put(f"{API}/supplies/{ctx['sid']}", headers=admin, json={**body, "invoice_number": ""})
        assert r.status_code == 400 and "facture" in r.json()['detail']
        # restore invoice (failed request may have committed nothing)
        assert g(admin, f"/supplies/{ctx['sid']}")['invoice_number'] == ctx['inv']
        # required expiration
        bad = {**body, "items": [{**body['items'][0], "date_peremption": None}]}
        r = requests.put(f"{API}/supplies/{ctx['sid']}", headers=admin, json=bad)
        assert r.status_code == 400 and "péremption" in r.json()['detail']
        # create without supplier
        r = requests.post(f"{API}/supplies", headers=admin, json={"supply_date": "2026-01-10", "invoice_number": "TEST_X", "items": body['items']})
        assert r.status_code in (400, 422), r.text

    def test_03_validate(self, admin, ctx):
        r = requests.post(f"{API}/supplies/{ctx['sid']}/validate", headers=admin)
        assert r.status_code == 200, r.text
        a = g(admin, f"/products/{ctx['pA']['id']}")
        b = g(admin, f"/products/{ctx['pB']['id']}")
        assert a['stock'] == (ctx['pA']['stock'] or 0) + 10
        assert b['stock'] == (ctx['pB']['stock'] or 0) + 4
        ctx['a_after'], ctx['b_after'] = a['stock'], b['stock']
        debts = [d for d in items(g(admin, "/supplier-debts")) if d.get('supply_id') == ctx['sid']]
        assert debts and debts[0]['original_amount'] == 12000
        # normal update now refused
        r = requests.put(f"{API}/supplies/{ctx['sid']}", headers=admin, json={"notes": "x"})
        assert r.status_code == 400

    def test_04_missing_reason_400(self, admin, ctx):
        det = g(admin, f"/supplies/{ctx['sid']}")
        r = requests.put(f"{API}/supplies/{ctx['sid']}/correct", headers=admin, json={"items": det['items']})
        assert r.status_code == 400
        assert r.json()['detail'] == "Le motif de correction est obligatoire"
        r = requests.put(f"{API}/supplies/{ctx['sid']}/correct", headers=admin, json={"items": det['items'], "correction_reason": "   "})
        assert r.status_code == 400

    def test_05_pharmacien_403(self, pharma, admin, ctx):
        det = g(admin, f"/supplies/{ctx['sid']}")
        r = requests.put(f"{API}/supplies/{ctx['sid']}/correct", headers=pharma, json={"items": det['items'], "correction_reason": "x"})
        assert r.status_code == 403

    def test_06_valid_correction(self, admin, ctx):
        det = g(admin, f"/supplies/{ctx['sid']}")
        itA = [i for i in det['items'] if i['product_id'] == ctx['pA']['id']][0]
        ctx['itA'] = itA['id']
        reason = "TEST Erreur de saisie BL"
        body = {"correction_reason": reason, "supplier_id": ctx['sup']['id'], "invoice_number": ctx['inv'], "items": [
            {"id": itA['id'], "product_id": ctx['pA']['id'], "quantity": 7, "unit_price": 1100, "selling_price": 1600, "date_peremption": "2028-06-30", "lot_number": "LA"},
            {"product_id": ctx['pA']['id'], "quantity": 2, "unit_price": 1100, "selling_price": 1600, "date_peremption": "2029-01-31", "lot_number": "LB"}]}
        r = requests.put(f"{API}/supplies/{ctx['sid']}/correct", headers=admin, json=body)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['total_amount'] == 9900
        assert len(d['stock_adjustments']) == 2
        assert d['price_updates'] >= 1
        a = g(admin, f"/products/{ctx['pA']['id']}")
        b = g(admin, f"/products/{ctx['pB']['id']}")
        assert a['stock'] == ctx['a_after'] - 1
        assert b['stock'] == ctx['b_after'] - 4
        assert a['price'] == 1600 and a['purchase_price'] == 1100
        det2 = g(admin, f"/supplies/{ctx['sid']}")
        assert len(det2['items']) == 2
        assert any(i['id'] == itA['id'] and i['quantity'] == 7 for i in det2['items'])
        assert reason in det2['notes'] and "[Correction" in det2['notes'] and " par " in det2['notes']
        debts = [x for x in items(g(admin, "/supplier-debts")) if x.get('supply_id') == ctx['sid']]
        assert debts[0]['original_amount'] == 9900
        mv = items(g(admin, "/stock/movements/paginated?limit=20"))
        corr = [m for m in mv if f"Correction appro {det2['supply_number']} : {reason}" in (m.get('reason') or m.get('notes') or '')]
        assert len(corr) == 2, [m.get('reason') for m in mv[:5]]
        ctx['body'] = body

    def test_07_refusal_below_available_stock(self, admin, ctx):
        cur = g(admin, f"/products/{ctx['pA']['id']}")['stock']
        out = cur - 2
        if out > 0:
            r = requests.post(f"{API}/stock/movement", headers=admin, json={"product_id": ctx['pA']['id'], "movement_type": "adjustment", "movement_quantity": out, "notes": "TEST sortie"})
            assert r.status_code == 200, r.text
        assert g(admin, f"/products/{ctx['pA']['id']}")['stock'] == min(cur, 2)
        try:
            body = {**ctx['body'], "correction_reason": "TEST refus", "items": [
                {"id": ctx['itA'], "product_id": ctx['pA']['id'], "quantity": 1, "unit_price": 1100, "selling_price": 1600, "date_peremption": "2028-06-30"}]}
            r = requests.put(f"{API}/supplies/{ctx['sid']}/correct", headers=admin, json=body)
            assert r.status_code == 400, r.text
            det = r.json()['detail']
            print("REFUS:", det)
            assert "stock actuel 2" in det and "impossible de retirer 8 unité(s)" in det and "Quantité totale minimale" in det and ": 7" in det
            # nothing changed
            assert g(admin, f"/products/{ctx['pA']['id']}")['stock'] == 2
            assert g(admin, f"/supplies/{ctx['sid']}")['total_amount'] == 9900
        finally:
            if out > 0:
                requests.post(f"{API}/stock/movement", headers=admin, json={"product_id": ctx['pA']['id'], "movement_type": "return", "movement_quantity": out, "notes": "TEST remise"})
        assert g(admin, f"/products/{ctx['pA']['id']}")['stock'] == cur

    def test_08_correction_requires_invoice(self, admin, ctx):
        r = requests.put(f"{API}/supplies/{ctx['sid']}/correct", headers=admin, json={**ctx['body'], "invoice_number": ""})
        assert r.status_code == 400 and "facture" in r.json()['detail']

    def test_09_correction_invalid_qty(self, admin, ctx):
        bad = {**ctx['body'], "items": [{**ctx['body']['items'][0], "quantity": 0}]}
        r = requests.put(f"{API}/supplies/{ctx['sid']}/correct", headers=admin, json=bad)
        assert r.status_code == 400
