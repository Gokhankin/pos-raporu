
import sys, os
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

print("--- 1. Check all Folio records for FolioId 51193 and 51249 on 07.09.2026 ---")
cur.execute("""
    SELECT RecId, FolioId, DepartCode, RevenueGroupCode, Amount, NetAmount, Rate, Remark, ActionType, CorrectionMasterId, OperationType
    FROM Folio 
    WHERE FolioId IN (51193, 51249) OR Remark LIKE '%131753%'
""")
for r in cur.fetchall():
    print(r)

print("\n--- 2. Check PosSummary status / billstatus values ---")
cur.execute("""
    SELECT BillStatus, Transferred, PosSaleType, COUNT(*) 
    FROM PosSummary 
    GROUP BY BillStatus, Transferred, PosSaleType
""")
for r in cur.fetchall():
    print(r)

print("\n--- 3. Check other Folio corrections across 2026 ---")
cur.execute("""
    SELECT ActionType, OperationType, COUNT(*), SUM(Amount)
    FROM Folio
    WHERE DepartCode IN ('200', '300', '605', '615')
      AND PostDate >= '20260101'
    GROUP BY ActionType, OperationType
""")
for r in cur.fetchall():
    print(r)

print("\n--- 4. How does Folio relate to PosDetail / PosSummary in Sedna? ---")
cur.execute("""
    SELECT TOP 10 f.RecId, f.FolioId, f.DepartCode, f.RevenueGroupCode, f.Amount, f.NetAmount, f.Remark, f.ActionType
    FROM Folio f
    WHERE f.DepartCode IN ('200', '300', '605', '615')
      AND (f.ActionType = 2 OR f.CorrectionMasterId > 0 OR f.Amount < 0)
      AND f.PostDate >= '20260601'
""")
for r in cur.fetchall():
    print(r)

conn.close()
