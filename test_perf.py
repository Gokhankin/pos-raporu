
import sys, time
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

# Test 1: NOT EXISTS
t0 = time.time()
cur.execute("""
    SELECT COUNT(*)
    FROM Folio f
    JOIN Department d ON f.DepartCode = d.DepartCode
    JOIN RevenueGroup rg ON f.RevenueGroupCode = rg.Code
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
""")
print("NOT EXISTS count:", cur.fetchone()[0], "Time:", time.time() - t0)

# Test 2: CTE / pre-filtered subquery
t0 = time.time()
cur.execute("""
    WITH Corrected AS (
        SELECT DISTINCT CorrectionMasterId
        FROM Folio
        WHERE CorrectionMasterId > 0 AND Deleted = 0
    )
    SELECT COUNT(*)
    FROM Folio f
    JOIN Department d ON f.DepartCode = d.DepartCode
    JOIN RevenueGroup rg ON f.RevenueGroupCode = rg.Code
    JOIN PosDetail pd ON 
        f.Remark LIKE '%Pos Selling%'
        AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
        AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
    JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
    LEFT JOIN Corrected c ON f.RecId = c.CorrectionMasterId
    WHERE f.Deleted = 0
      AND f.DepartCode IN ('200', '300', '605', '615')
      AND f.CorrectionMasterId = 0
      AND f.ActionType != 2
      AND c.CorrectionMasterId IS NULL
      AND f.PostDate >= '20260901 00:00:00' AND f.PostDate <= '20260930 23:59:59'
""")
print("WITH Corrected count:", cur.fetchone()[0], "Time:", time.time() - t0)

conn.close()
