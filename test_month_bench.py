
import time
import sys
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

# Test August 2026 (Peak month with 11k+ items)
months = [
    ('2026-07-01', '2026-07-31'),
    ('2026-08-01', '2026-08-31'),
    ('2026-09-01', '2026-09-30')
]

for start_raw, end_raw in months:
    start_s = start_raw.replace('-', '') + ' 00:00:00'
    end_s = end_raw.replace('-', '') + ' 23:59:59'
    
    t0 = time.time()
    # 1. Summary
    cur.execute("""
        SELECT 
            SUM(pd.Amount) as TotalQty,
            SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as TotalEur,
            SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) * f.Rate) as TotalLocal,
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
          AND f.PostDate >= ? AND f.PostDate <= ?
    """, start_s, end_s)
    row = cur.fetchone()
    dt = time.time() - t0
    print(f"Summary for {start_raw}: {row[1]:,.2f} EUR in {dt:.3f}s")

conn.close()
