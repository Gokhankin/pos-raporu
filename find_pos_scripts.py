
import os, glob

for root, dirs, files in os.walk('/home/society/Masaüstü'):
    if any(p in root for p in ['venv', '.git', 'backups', 'Yedekler', '.cache']):
        continue
    for f in files:
        if f.endswith('.py') or f.endswith('.sql'):
            fpath = os.path.join(root, f)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    if 'PosDetail' in content or 'PosSummary' in content:
                        print(f"FOUND IN: {fpath}")
            except Exception:
                pass
