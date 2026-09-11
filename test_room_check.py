
import sys, os
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

print("--- Check Room and Guest Names in PosSummary vs Reservation ---")
cur.execute("""
    SELECT TOP 30
        f.FolioId,
        f.ReservationId,
        r.Room as ResRoom,
        ps.RoomNummer as PosRoom,
        r.FirstName1 + ' ' + r.LastName1 as ResGuestName,
        pd.SummaryId,
        f.CheckNo,
        ps.CheckNo as PosCheckNo
    FROM Folio f
    JOIN PosDetail pd ON 
        f.Remark LIKE '%Pos Selling%'
        AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
        AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
    JOIN PosSummary ps ON pd.SummaryId = ps.RecId
    LEFT JOIN Reservation r ON f.ReservationId = r.RecId
    WHERE f.Deleted = 0
      AND f.DepartCode IN ('200', '300', '605', '615')
      AND f.PostDate >= '20260901 00:00:00' AND f.PostDate <= '20260902 23:59:59'
    ORDER BY f.PostDate ASC, pd.RecId ASC
""")
for r in cur.fetchall():
    print(r)

conn.close()
