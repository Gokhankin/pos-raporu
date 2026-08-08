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
    
    # Let's search for records in PosDetail with RecordDate on 2026-06-01
    print("--- Searching PosDetail on 2026-06-01 ---")
    df = pd.read_sql("""
        SELECT TOP 20 
            pd.RecId, pd.SummaryId, pd.ProductId, pd.Amount, pd.Price, pd.RecordDate, p.Remark as ProductName
        FROM PosDetail pd
        LEFT JOIN Product p ON pd.ProductId = p.RecId
        WHERE pd.RecordDate >= '2026-06-01 00:00:00' AND pd.RecordDate <= '2026-06-01 23:59:59'
    """, conn)
    print(df.to_string())
    
    # Let's search if there are any records of ProductId = 3980 (UNO KAĞIT) in PosDetail
    print("\n--- Searching for UNO KAĞIT in PosDetail ---")
    df_uno = pd.read_sql("""
        SELECT TOP 10 pd.RecId, pd.SummaryId, pd.ProductId, pd.Amount, pd.Price, pd.RecordDate
        FROM PosDetail pd
        WHERE pd.ProductId = 3980
        ORDER BY pd.RecordDate DESC
    """, conn)
    print(df_uno.to_string())
    
    conn.close()

if __name__ == "__main__":
    main()
