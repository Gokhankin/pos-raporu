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
    
    # Let's check where RecId = 114323 is in PosDetail or other tables
    # First search for columns of PosDetail
    print("--- Columns of PosDetail ---")
    try:
        df_cols = pd.read_sql("SELECT TOP 0 * FROM PosDetail", conn)
        print(df_cols.columns.tolist())
        
        # Let's query where RecId = 114323
        print("\n--- PosDetail for RecId = 114323 ---")
        df_val = pd.read_sql("SELECT * FROM PosDetail WHERE RecId = 114323", conn)
        print(df_val.to_string())
        
        if len(df_val) == 0:
            # Let's search if there are other columns or tables containing 114323
            print("\nRecId 114323 not found in PosDetail. Let's check tables like PosWaiterAdisionNo, etc.")
    except Exception as e:
        print("Error checking PosDetail:", e)
        
    conn.close()

if __name__ == "__main__":
    main()
