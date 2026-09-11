
import sys, os
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

print("--- 1. Check all Folio records where f.RecId IN (SELECT CorrectionMasterId) or f.ActionType = 2 ---")
cur.execute("""
    SELECT 
        f.RecId, f.FolioId, f.PostDate, f.DepartCode, f.RevenueGroupCode, f.Amount, f.NetAmount, f.Remark, f.ActionType, f.CorrectionMasterId
    FROM Folio f
    WHERE f.Deleted = 0 
      AND (
          f.RecId IN (SELECT CorrectionMasterId FROM Folio WHERE CorrectionMasterId > 0 AND Deleted = 0)
          OR f.CorrectionMasterId > 0
          OR f.ActionType = 2
      )
      AND f.PostDate >= '20260901'
    ORDER BY f.PostDate ASC
""")
rows = cur.fetchall()
for r in rows:
    print(r)

print(f"Total corrected folio records in Sep 2026: {len(rows)}")

print("\n--- 2. How many POS items are affected by corrections in Sep 2026? ---")
cur.execute("""
    SELECT 
        f.PostDate,
        SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as WithCorrectedEur,
        SUM(CASE WHEN f.RecId NOT IN (SELECT CorrectionMasterId FROM Folio WHERE CorrectionMasterId > 0 AND Deleted = 0) 
                 AND f.CorrectionMasterId = 0 
                 AND f.ActionType != 2 
            THEN pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) ELSE 0 END) as CleanEur
    FROM Folio f
    JOIN PosDetail pd ON 
        f.Remark LIKE '%Pos Selling%'
        AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
        AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
    JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
    WHERE f.Deleted = 0
      AND f.DepartCode IN ('200', '300', '605', '615')
      AND f.PostDate >= '20260901 00:00:00' AND f.PostDate <= '20260930 23:59:59'
    GROUP BY f.PostDate
    ORDER BY f.PostDate
""")
for r in cur.fetchall():
    print(r)

conn.close()
