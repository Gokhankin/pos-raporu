
import sys, os
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

print("--- Daily POS summary with exclusion of corrected / reversed Folio transactions ---")
cur.execute("""
    SELECT 
        CAST(f.PostDate AS DATE) as PostDate,
        SUM(pd.Amount) as Qty,
        SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as RevenueEur,
        SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) * f.Rate) as RevenueLocal,
        COUNT(DISTINCT pd.SummaryId) as TotalChecks
    FROM Folio f
    JOIN PosDetail pd ON 
        f.Remark LIKE '%Pos Selling%'
        AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
        AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
    JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
    WHERE f.Deleted = 0
      AND f.DepartCode IN ('200', '300', '605', '615')
      AND f.CorrectionMasterId = 0
      AND f.ActionType != 2
      AND NOT EXISTS (
          SELECT 1 FROM Folio corr 
          WHERE corr.CorrectionMasterId = f.RecId 
            AND corr.Deleted = 0
      )
      AND f.PostDate >= '20260901 00:00:00' AND f.PostDate <= '20260930 23:59:59'
    GROUP BY CAST(f.PostDate AS DATE)
    ORDER BY PostDate
""")
rows = cur.fetchall()
total_qty = 0
total_eur = 0
for r in rows:
    print(r)
    total_qty += r[1]
    total_eur += r[2]
print(f"\nTOTAL SEP 2026 -> Qty: {total_qty}, EUR: {total_eur}")

conn.close()
