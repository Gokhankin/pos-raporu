
import sys, os
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

print("--- 1. Check September 2026 Folio rows with Pos Selling ---")
cur.execute("""
    SELECT TOP 20 f.FolioId, f.PostDate, f.DepartCode, f.RevenueGroupCode, f.Amount, f.NetAmount, f.Rate, f.Remark, f.CheckNo, f.ReservationId
    FROM Folio f
    WHERE f.Deleted = 0 
      AND f.PostDate >= '20260901 00:00:00' AND f.PostDate <= '20260910 23:59:59'
      AND f.Remark LIKE '%Pos Selling%'
    ORDER BY f.PostDate ASC
""")
for r in cur.fetchall():
    print(r)

print("\n--- 2. Check 07.09.2026 why €273,201.75 happened ---")
cur.execute("""
    SELECT f.FolioId, f.PostDate, f.DepartCode, f.RevenueGroupCode, f.Amount, f.NetAmount, f.Rate, f.Remark, COUNT(pd.RecId) as pd_count, SUM(pd.Amount) as sum_qty, SUM(pd.Price) as sum_price
    FROM Folio f
    JOIN PosDetail pd ON 
        f.Remark LIKE '%Pos Selling%'
        AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
        AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
    WHERE f.Deleted = 0 
      AND f.PostDate >= '20260907 00:00:00' AND f.PostDate <= '20260907 23:59:59'
    GROUP BY f.FolioId, f.PostDate, f.DepartCode, f.RevenueGroupCode, f.Amount, f.NetAmount, f.Rate, f.Remark
    ORDER BY sum_qty DESC
""")
for r in cur.fetchall()[:20]:
    print(r)

print("\n--- 3. Check PosSummary and PosDetail for 07.09.2026 ---")
cur.execute("""
    SELECT TOP 10 * FROM PosSummary WHERE Date >= '20260907' AND Date <= '20260908'
""")
columns = [column[0] for column in cur.description]
print("PosSummary cols:", columns)
for r in cur.fetchall():
    print(dict(zip(columns, r)))

conn.close()
