import pandas as pd
import pyodbc

DB_CONFIG = {
    "server":   "192.168.0.41",
    "port":     1433,
    "database": "SednaAdakoy",
    "username": "sa",
    "password": "ClubAdakoy2022!",
}

def connect():
    for drv in ["{ODBC Driver 18 for SQL Server}", "{ODBC Driver 17 for SQL Server}", "{SQL Server}"]:
        try:
            cs = f"DRIVER={drv};SERVER={DB_CONFIG['server']},{DB_CONFIG['port']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']};TrustServerCertificate=yes;Encrypt=no;"
            return pyodbc.connect(cs, timeout=5)
        except:
            continue
    return None

def main():
    conn = connect()
    if not conn:
        print("Database connection failed")
        return
    
    # Load Excel June
    df_excel = pd.read_excel("Pos Satis.xlsx", sheet_name=1) # June
    excel_recids = set(df_excel['RecId'].dropna().astype(int).tolist())
    print("Excel Unique RecIds (SummaryIds):", len(excel_recids))
    
    # Query Folio and PosDetail for June 2026
    sql = """
        SELECT 
            f.RecId as FolioRecId,
            f.DepartCode,
            f.RevenueGroupCode,
            f.Amount as FolioAmount,
            f.Remark,
            pd.SummaryId as RecId,
            pd.ProductId,
            pd.Amount as PosAmount,
            pd.Price as PosPrice,
            pd.SaleType
        FROM Folio f
        JOIN PosDetail pd ON 
            f.Remark LIKE '% Pos Selling'
            AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
            AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
        WHERE f.Deleted = 0
          AND f.DepartCode IN ('200', '300', '605')
          AND f.PostDate >= '2026-06-01' AND f.PostDate <= '2026-06-30'
    """
    df_db = pd.read_sql(sql, conn)
    db_recids = set(df_db['RecId'].dropna().astype(int).tolist())
    print("DB Unique RecIds (SummaryIds):", len(db_recids))
    
    # Difference: DB - Excel
    db_only = db_recids - excel_recids
    print(f"SummaryIds in DB but not in Excel: {len(db_only)}")
    
    # Let's inspect some DB-only records
    if len(db_only) > 0:
        db_only_list = list(db_only)[:10]
        print("\n--- Sample DB-only records ---")
        df_sample = df_db[df_db['RecId'].isin(db_only_list)]
        # Get more info from Folio for these
        cur = conn.cursor()
        for rec in db_only_list:
            cur.execute("SELECT RecId, ReservationId, DepartCode, RevenueGroupCode, Amount, LocalAmount, Remark, Deleted FROM Folio WHERE Remark LIKE ?", f"{rec} Pos Selling%")
            f_row = cur.fetchone()
            print(f"SummaryId {rec} in Folio:", f_row)
            
    # Difference: Excel - DB
    excel_only = excel_recids - db_recids
    print(f"\nSummaryIds in Excel but not in DB: {len(excel_only)}")
    if len(excel_only) > 0:
        print("Sample Excel-only RecIds:", list(excel_only)[:10])
        
    conn.close()

if __name__ == "__main__":
    main()
