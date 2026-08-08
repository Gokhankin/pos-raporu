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
    
    # Query Folio records from 2026-06-01 to 2026-06-30 for departments 200, 300, 605
    # Wait, we want to know what conditions they used. Let's select some columns.
    sql = """
        SELECT TOP 10 
            f.RecId,
            r.Room,
            f.FolioId,
            r.FirstName1 + ' ' + r.LastName1 as Name,
            f.PostDate,
            f.RecordTime,
            f.DepartCode,
            f.RevenueGroupCode,
            f.Remark,
            f.CheckNo,
            f.Count, -- is this quantity?
            f.Amount, -- is this price in EUR?
            f.NetAmount,
            f.LocalAmount
        FROM Folio f
        LEFT JOIN Reservation r ON f.ReservationId = r.RecId
        WHERE f.Deleted = 0
          AND f.DepartCode IN ('200', '300', '605')
          AND f.PostDate >= '2026-06-01' AND f.PostDate <= '2026-06-30'
        ORDER BY f.RecId ASC
    """
    df_db = pd.read_sql(sql, conn)
    print("--- Database sample (June 2026) ---")
    print(df_db.to_string())
    
    # Load first 10 rows of June sheet
    xls = pd.ExcelFile("Pos Satis.xlsx")
    df_excel = pd.read_excel(xls, 1)
    print("\n--- Excel sample (June 2026) ---")
    print(df_excel.head(10).to_string())
    
    conn.close()

if __name__ == "__main__":
    main()
