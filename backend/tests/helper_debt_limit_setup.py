# Helper: state check / schedule create / cleanup for customer debt-limit UI retest
import os, sys, requests, datetime
BASE = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') + '/api'
CID = '95972c73-b17f-4181-ad65-87f2b17b9b68'
PH_ID = 'a99017af-c55c-42f1-8088-3f6a9e3ab5b1'

def login(e, p):
    r = requests.post(f'{BASE}/auth/login', json={'email': e, 'password': p})
    r.raise_for_status()
    j = r.json()
    return {'Authorization': f"Bearer {j.get('access_token') or j.get('token')}"}

a = login('admin@pharmaflow.com', 'admin123')
ph = login('pharmacien@pharmaflow.com', 'Pharma#2026')
cmd = sys.argv[1]
if cmd == 'state':
    r = requests.get(f'{BASE}/customers/{CID}', headers=a); print(r.status_code, r.json())
    r = requests.get(f'{BASE}/customers/paginated', headers=a, params={'search': 'Matam'})
    print(r.status_code, r.text[:600])
    print('ph shift', requests.get(f'{BASE}/shifts/current', headers=ph).text[:300])
    print('elig', requests.get(f'{BASE}/shift-schedules/check-eligibility', headers=ph).text[:300])
elif cmd == 'schedule':
    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    r = requests.post(f'{BASE}/shift-schedules', headers=a, json={'user_id': PH_ID, 'scheduled_date': today, 'start_time': '00:00', 'end_time': '23:59'})
    print(r.status_code, r.text[:400])
elif cmd == 'cleanup':
    today = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    r = requests.get(f'{BASE}/shift-schedules', headers=a, params={'start_date': today, 'end_date': today, 'user_id': PH_ID})
    print(r.status_code, r.text[:300])
    data = r.json()
    items = data if isinstance(data, list) else data.get('schedules', data.get('items', []))
    for s in items:
        if s.get('user_id') == PH_ID:
            print('delete', s['id'], requests.delete(f"{BASE}/shift-schedules/{s['id']}", headers=a).status_code)
elif cmd == 'closeshift':
    print(requests.post(f'{BASE}/shifts/close', headers=ph, json={'actual_closing_amount': 0}).text[:300])
elif cmd == 'restore':
    r = requests.put(f'{BASE}/customers/{CID}', headers=a, json={'phone': sys.argv[2], 'max_debt_limit': 123456})
    print(r.status_code, r.text[:300])
