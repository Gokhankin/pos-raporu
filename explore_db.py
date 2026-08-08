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
        print("Could not connect to database")
        return
    
    cur = conn.cursor()
    
    # 1. Let's find tables with 'Folio' or 'POS' or 'Sale' in their names
    print("--- Searching tables ---")
    cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%Folio%' OR TABLE_NAME LIKE '%Pos%' OR TABLE_NAME LIKE '%Sale%'")
    for row in cur.fetchall():
        print("Table:", row[0])
        
    # 2. Check structure of dbo.Folio
    print("\n--- Columns of dbo.Folio ---")
    try:
        cur.execute("SELECT TOP 0 * FROM dbo.Folio")
        col_names = [desc[0] for desc in cur.description]
        print("Folio columns:", col_names)
    except Exception as e:
        print("Error getting Folio columns:", e)
        
    # 3. Check some samples from dbo.Folio where department is not rooms
    print("\n--- Samples from dbo.Folio ---")
    try:
        cur.execute("SELECT TOP 5 * FROM dbo.Folio ORDER BY RecId DESC")
        for row in cur.fetchall():
            print(row)
    except Exception as e:
        print("Error getting Folio samples:", e)
        
    conn.close()

if __name__ == "__main__":
    main()
