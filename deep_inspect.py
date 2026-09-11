
import sys, os
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

print("--- 1. Examine Folio columns and records for SummaryId 130558 (0.00 row) ---")
cur.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Folio'")
cols = [r[0] for r in cur.fetchall()]
print("Folio columns:", cols)

cur.execute("SELECT * FROM Folio WHERE Remark LIKE '130558%'")
rows = cur.fetchall()
for r in rows:
    print(dict(zip(cols, r)))

print("\n--- 2. Examine PosSummary and PosDetail for 130558 ---")
cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'PosSummary'")
pos_sum_cols = [r[0] for r in cur.fetchall()]
print("PosSummary cols:", pos_sum_cols)

cur.execute("SELECT * FROM PosSummary WHERE RecId = 130558")
for r in cur.fetchall():
    print(dict(zip(pos_sum_cols, r)))

cur.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'PosDetail'")
pos_det_cols = [r[0] for r in cur.fetchall()]
print("PosDetail cols:", pos_det_cols)

cur.execute("SELECT * FROM PosDetail WHERE SummaryId = 130558")
for r in cur.fetchall():
    print(dict(zip(pos_det_cols, r)))

print("\n--- 3. Examine 131753 (The 271k EUR HATALI İŞLEM) ---")
cur.execute("SELECT * FROM Folio WHERE Remark LIKE '131753%' OR FolioId = 51249")
for r in cur.fetchall():
    print(dict(zip(cols, r)))

cur.execute("SELECT * FROM PosSummary WHERE RecId = 131753")
for r in cur.fetchall():
    print(dict(zip(pos_sum_cols, r)))

cur.execute("SELECT * FROM PosDetail WHERE SummaryId = 131753")
for r in cur.fetchall():
    print(dict(zip(pos_det_cols, r)))

conn.close()
