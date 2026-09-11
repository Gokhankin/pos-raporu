
import time, urllib.request

endpoints = [
    '/api/pos-summary?start=2026-09-01&end=2026-09-30',
    '/api/pos-summary?start=2026-08-01&end=2026-08-31',
    '/api/pos-summary?start=2026-07-01&end=2026-07-31',
    '/api/pos-summary?start=2026-06-01&end=2026-06-30',
    # Second pass - all cache hits:
    '/api/pos-summary?start=2026-09-01&end=2026-09-30',
    '/api/pos-summary?start=2026-08-01&end=2026-08-31',
    '/api/pos-summary?start=2026-07-01&end=2026-07-31',
    '/api/pos-summary?start=2026-06-01&end=2026-06-30',
]

for idx, ep in enumerate(endpoints):
    t0 = time.time()
    try:
        req = urllib.request.Request('http://127.0.0.1:5070' + ep)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            pass_str = "Cache Hit" if idx >= 4 else "First Fetch"
            print(f"[{pass_str}] {ep[:35]}... -> Time: {time.time()-t0:.4f}s")
    except Exception as e:
        print(f"{ep} -> ERROR: {e}")
