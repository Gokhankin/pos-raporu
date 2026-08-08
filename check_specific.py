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
    target_ids = [116224, 117770, 117771, 117772, 117778, 115731, 117785, 116251, 115230, 117790]
    
    print("--- Searching for missing RecIds in Folio ---")
    for tid in target_ids:
        cur.execute("SELECT RecId, PostDate, CurrDate, DepartCode, RevenueGroupCode, Amount, LocalAmount, Remark, Deleted FROM Folio WHERE Remark LIKE ?", f"{tid} Pos Selling%")
        row = cur.fetchone()
        if row:
            print(f"ID {tid} found in Folio:", row)
        else:
            # Let's search if the Remark doesn't have "Pos Selling"
            cur.execute("SELECT RecId, PostDate, CurrDate, DepartCode, RevenueGroupCode, Amount, LocalAmount, Remark, Deleted FROM Folio WHERE Remark LIKE ?", f"{tid}%")
            row2 = cur.fetchone()
            if row2:
                print(f"ID {tid} found in Folio with different remark:", row2)
            else:
                print(f"ID {tid} NOT FOUND in Folio at all!")
                
    conn.close()

if __name__ == "__main__":
    main()
