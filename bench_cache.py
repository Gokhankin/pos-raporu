
import time, urllib.request

endpoints = [
    '/api/pos-summary?start=2026-08-01&end=2026-08-31',
    '/api/pos-summary?start=2026-08-01&end=2026-08-31', # Cache hit!
    '/api/pos-summary?start=2026-07-01&end=2026-07-31',
    '/api/pos-summary?start=2026-07-01&end=2026-07-31', # Cache hit!
    '/api/pos-activities?start=2026-08-01&end=2026-08-31',
    '/api/pos-activities?start=2026-08-01&end=2026-08-31', # Cache hit!
]

for ep in endpoints:
    t0 = time.time()
    try:
        req = urllib.request.Request('http://127.0.0.1:5070' + ep)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = resp.read()
            print(f"{ep[:35]}... -> Time: {time.time()-t0:.4f}s")
    except Exception as e:
        print(f"{ep} -> ERROR: {e}")
