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
    
    # 1. Search for UNO in Product table
    print("--- Searching for UNO in Product ---")
    cur.execute("SELECT RecId, Code, Remark, PosRemark, RevenueCode FROM Product WHERE Remark LIKE '%UNO%' OR PosRemark LIKE '%UNO%'")
    rows = cur.fetchall()
    for row in rows:
        print("Product Row:", row)
        
    # 2. Check DailyProductSaleTrans table for RecId = 114323
    print("\n--- Checking DailyProductSaleTrans for RecId = 114323 ---")
    try:
        df_cols = pd.read_sql("SELECT TOP 0 * FROM DailyProductSaleTrans", conn)
        print("DailyProductSaleTrans columns:", df_cols.columns.tolist())
        cur.execute("SELECT * FROM DailyProductSaleTrans WHERE RecId = 114323")
        row = cur.fetchone()
        print("DailyProductSaleTrans Row:", row)
    except Exception as e:
        print("Error checking DailyProductSaleTrans:", e)
        
    # 3. Check DailyProductSaleTrans table for ProductId
    print("\n--- Samples from DailyProductSaleTrans ---")
    try:
        df_samples = pd.read_sql("SELECT TOP 5 * FROM DailyProductSaleTrans ORDER BY RecId DESC", conn)
        print(df_samples.to_string())
    except Exception as e:
        print("Error getting DailyProductSaleTrans samples:", e)
        
    conn.close()

if __name__ == "__main__":
    main()
