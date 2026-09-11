
import requests, time

base_url = 'http://127.0.0.1:5070'
endpoints = [
    '/api/status',
    '/api/pos-summary?start=2026-09-01&end=2026-09-30',
    '/api/pos-forecast?start=2026-09-01&end=2026-09-30',
    '/api/pos-activities?start=2026-09-01&end=2026-09-30',
    '/api/pos-transactions?start=2026-09-01&end=2026-09-30&page=1&limit=100'
]

for ep in endpoints:
    t0 = time.time()
    try:
        r = requests.get(base_url + ep, timeout=30)
        print(f"{ep} -> Status: {r.status_code}, Time: {time.time()-t0:.2f}s, Response Keys: {list(r.json().keys()) if isinstance(r.json(), dict) else len(r.json())}")
    except Exception as e:
        print(f"{ep} -> ERROR: {e}")
