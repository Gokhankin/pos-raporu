
import sys, os
sys.path.insert(0, '/home/society/Masaüstü/sedna_cloud_backup')
from config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

print("--- 1. Check all Folio records in 2026 that have corrections ---")
cur.execute("""
    SELECT 
        f_orig.RecId as OrigRecId,
        f_orig.FolioId,
        f_orig.PostDate,
        f_orig.Amount as OrigAmount,
        f_orig.Remark as OrigRemark,
        f_corr.RecId as CorrRecId,
        f_corr.Amount as CorrAmount,
        f_corr.Remark as CorrRemark
    FROM Folio f_orig
    JOIN Folio f_corr ON f_corr.CorrectionMasterId = f_orig.RecId
    WHERE f_orig.Deleted = 0 AND f_corr.Deleted = 0
      AND f_orig.PostDate >= '20260101'
    ORDER BY f_orig.PostDate DESC
""")
for r in cur.fetchall()[:30]:
    print(r)

print("\n--- 2. Check how PosDetail is stored: Is PosDetail directly queried or joined with Folio? ---")
cur.execute("""
    SELECT COUNT(*) as PosDetailCount, SUM(NetTotal) as TotalNetEur, SUM(LocalAmount) as TotalLocal
    FROM PosDetail pd
    JOIN PosSummary ps ON pd.SummaryId = ps.RecId
    WHERE ps.SellingDate >= '20260901' AND ps.SellingDate <= '20260910'
""")
print("PosDetail directly for Sep 1-10:", cur.fetchone())

cur.execute("""
    SELECT COUNT(*) as PosDetailCount, SUM(NetTotal) as TotalNetEur, SUM(LocalAmount) as TotalLocal
    FROM PosDetail pd
    JOIN PosSummary ps ON pd.SummaryId = ps.RecId
    WHERE ps.SellingDate >= '20260901' AND ps.SellingDate <= '20260910'
      AND ps.RecId != 131753
""")
print("PosDetail directly without 131753 for Sep 1-10:", cur.fetchone())

conn.close()
