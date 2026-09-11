
import time
import sys
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

# Test with f.PostDate ASC in ORDER BY
t0 = time.time()
cur.execute("""
    SELECT 
        COALESCE(NULLIF(r.Room, ''), 'Walk-In') as Room,
        f.FolioId,
        COALESCE(NULLIF(LTRIM(RTRIM(r.FirstName1 + ' ' + r.LastName1)), ''), 'Walk-in Misafir') as GuestName,
        'Credit' as PosSaleType,
        CAST(f.PostDate AS DATE) as SellingDate,
        f.RecordTime as Time,
        d.DepartName,
        rg.RevenueName,
        p.Remark as ProductName,
        COALESCE(NULLIF(f.CheckNo, ''), CAST(pd.SummaryId AS VARCHAR)) as CheckNo,
        pd.Amount as Qty,
        pd.Price as UnitPriceEur,
        pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) as PriceEur,
        pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) * f.Rate as LocalAmount,
        pd.SummaryId as RecId,
        ISNULL(pd.DiscountRatio, 0) as DiscountRatio,
        ISNULL(pd.Discount, 0) as DiscountEur,
        ISNULL(pd.Total, pd.Amount * pd.Price) as GrossEur
    FROM Folio f
    JOIN Department d ON f.DepartCode = d.DepartCode
    JOIN RevenueGroup rg ON f.RevenueGroupCode = rg.Code
    LEFT JOIN Reservation r ON f.ReservationId = r.RecId
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
    ORDER BY f.PostDate ASC, f.RecordTime ASC, pd.RecId ASC
    OFFSET 0 ROWS
    FETCH NEXT 100 ROWS ONLY
""")
rows = cur.fetchall()
print(f"Fetched {len(rows)} rows in {time.time() - t0:.3f}s")

conn.close()
