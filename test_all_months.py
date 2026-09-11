
import sys, os
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

# Test all queries with the clean correction filter for June, July, August, September 2026
months = [
    ('2026-06-01', '2026-06-30'),
    ('2026-07-01', '2026-07-31'),
    ('2026-08-01', '2026-08-31'),
    ('2026-09-01', '2026-09-30')
]

for start_date, end_date in months:
    start_s = start_date.replace('-', '') + ' 00:00:00'
    end_s = end_date.replace('-', '') + ' 23:59:59'
    
    cur.execute("""
        SELECT 
            SUM(pd.Amount) as TotalQty,
            SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as CleanEur,
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
    print(f"{start_date} -> {end_date}: Qty={row[0]}, CleanEur={row[1]:,.2f} EUR, Checks={row[2]}")

conn.close()
