
import time, urllib.request

endpoints = [
    '/api/status',
    '/api/pos-summary?start=2026-09-01&end=2026-09-30',
    '/api/pos-forecast?start=2026-09-01&end=2026-09-30',
    '/api/pos-activities?start=2026-09-01&end=2026-09-30',
    '/api/pos-transactions?start=2026-09-01&end=2026-09-30&page=1&limit=20'
]

for ep in endpoints:
    t0 = time.time()
    try:
        req = urllib.request.Request('http://127.0.0.1:5070' + ep)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            print(f"{ep.split('?')[0]} -> Code: {resp.status}, Time: {time.time()-t0:.3f}s, Bytes: {len(data)}")
    except Exception as e:
        print(f"{ep} -> ERROR: {e}")
