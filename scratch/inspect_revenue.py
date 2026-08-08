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
    
    # Let's inspect unique DepartCode and DepartName in the DB
    print("--- Departments in DB ---")
    df_dept = pd.read_sql("SELECT DepartCode, DepartName, DepartType FROM Department", conn)
    print(df_dept.to_string())
    
    # Let's check the unique RevenueGroups in DB
    print("\n--- RevenueGroups in DB ---")
    try:
        # Let's see if RevenueGroup table exists
        df_rev = pd.read_sql("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%Revenue%'", conn)
        print("Revenue tables:", df_rev['TABLE_NAME'].tolist())
        
        # Let's query RevenueGroup table columns or names
        for t in df_rev['TABLE_NAME'].tolist():
            print(f"\nColumns of {t}:")
            try:
                df_cols = pd.read_sql(f"SELECT TOP 0 * FROM {t}", conn)
                print(df_cols.columns.tolist())
                # If there are rows, let's see them
                df_data = pd.read_sql(f"SELECT TOP 10 * FROM {t}", conn)
                print(df_data)
            except Exception as e:
                print(f"Error checking {t}:", e)
    except Exception as e:
        print("Error checking RevenueGroup:", e)
        
    conn.close()

if __name__ == "__main__":
    main()
