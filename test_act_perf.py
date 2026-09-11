
import time
import sys
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

# Test 1: With OR
t0 = time.time()
cur.execute("""
    SELECT COUNT(*)
    FROM Folio f
    JOIN PosDetail pd ON 
        f.Remark LIKE '%Pos Selling%'
        AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
        AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
    JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
    WHERE f.Deleted = 0
      AND (f.DepartCode = '615' OR f.RevenueGroupCode = 'A08')
      AND f.CorrectionMasterId = 0
      AND f.ActionType != 2
      AND NOT EXISTS (
          SELECT 1 FROM Folio corr 
          WHERE corr.CorrectionMasterId = f.RecId 
            AND corr.Deleted = 0
      )
      AND f.PostDate >= '20260801 00:00:00' AND f.PostDate <= '20260831 23:59:59'
""")
print("With OR:", cur.fetchone()[0], "Time:", time.time() - t0)

# Test 2: With DepartCode = '615'
t0 = time.time()
cur.execute("""
    SELECT COUNT(*)
    FROM Folio f
    JOIN PosDetail pd ON 
        f.Remark LIKE '%Pos Selling%'
        AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
        AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
    JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
    WHERE f.Deleted = 0
      AND f.DepartCode = '615'
      AND f.CorrectionMasterId = 0
      AND f.ActionType != 2
      AND NOT EXISTS (
          SELECT 1 FROM Folio corr 
          WHERE corr.CorrectionMasterId = f.RecId 
            AND corr.Deleted = 0
      )
      AND f.PostDate >= '20260801 00:00:00' AND f.PostDate <= '20260831 23:59:59'
""")
print("DepartCode 615:", cur.fetchone()[0], "Time:", time.time() - t0)

# Test 3: Check if there are any DepartCode != '615' that have RevenueGroupCode = 'A08'
cur.execute("""
    SELECT DepartCode, RevenueGroupCode, COUNT(*)
    FROM Folio
    WHERE Deleted = 0 AND (DepartCode = '615' OR RevenueGroupCode = 'A08')
    GROUP BY DepartCode, RevenueGroupCode
""")
print("Breakdown of 615 vs A08:", cur.fetchall())

conn.close()
