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
    
    # Let's search for table names with Product or Item or Service
    print("--- Searching tables ---")
    df = pd.read_sql("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%Product%' OR TABLE_NAME LIKE '%Item%'", conn)
    print(df.to_string())
    
    # Check if there is a table called Product
    print("\n--- Columns of Product if exists ---")
    try:
        df_prod = pd.read_sql("SELECT TOP 0 * FROM Product", conn)
        print("Product table exists! Columns:", df_prod.columns.tolist())
        # Let's get Product with RecId = 332
        df_row = pd.read_sql("SELECT * FROM Product WHERE RecId = 332", conn)
        print(df_row.to_string())
    except Exception as e:
        print("Product table check error:", e)
        
    conn.close()

if __name__ == "__main__":
    main()
