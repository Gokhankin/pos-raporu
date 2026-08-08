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
    
    cur = conn.cursor()
    # Query Folio records for Source = 114331
    print("--- Folio records for Source = 114331 ---")
    cur.execute("SELECT RecId, DepartCode, RevenueGroupCode, NetAmount, LocalAmount, Amount, Count, Source, CheckNo FROM Folio WHERE Source = 114331")
    for r in cur.fetchall():
        print(r)
        
    # Query PosDetail records for SummaryId = 114331
    print("\n--- PosDetail records for SummaryId = 114331 ---")
    cur.execute("SELECT RecId, ProductId, Amount, Price, Total, LocalAmount, ProductDescription FROM PosDetail WHERE SummaryId = 114331")
    for r in cur.fetchall():
        print(r)
        
    conn.close()

if __name__ == "__main__":
    main()
