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
    
    # Query DB for 2026-06-01 stay date using correct DailyDetail columns
    try:
        sql = """
            SELECT 
                COUNT(dd.RecId) as Sold,
                SUM(ISNULL(dd.Pax, 0)) as DDPax,
                SUM(ISNULL(dd.PaidChild, 0)) as PaidChild,
                SUM(ISNULL(dd.FreeChild, 0)) as FreeChild,
                SUM(ISNULL(dd.Baby, 0)) as Baby,
                SUM(ISNULL(dd.Childs, 0)) as Childs,
                SUM(ISNULL(dd.Child1, 0)) as Child1,
                SUM(ISNULL(dd.Child2, 0)) as Child2
            FROM DailyDetail dd
            JOIN Reservation r ON dd.ReservationId = r.RecId
            WHERE CAST(dd.StayDate AS DATE) = '2026-06-01'
              AND dd.Status IN (0,1,2,3) AND r.Status IN (0,1,2,3)
        """
        df_db = pd.read_sql(sql, conn)
        print("DB Query values for 2026-06-01:")
        print(df_db.to_string())
        
        # Query checkin and checkout rooms from DailyDetail or Reservation
        # Let's count reservations with CheckinDate = '2026-06-01'
        sql_c = """
            SELECT 
                COUNT(CASE WHEN CAST(CheckinDate AS DATE) = '2026-06-01' THEN 1 END) as Cin_Room,
                COUNT(CASE WHEN CAST(CheckOutDate AS DATE) = '2026-06-01' THEN 1 END) as Cout_Room
            FROM Reservation
            WHERE Status IN (0,1,2,3)
        """
        df_c = pd.read_sql(sql_c, conn)
        print("\nDB Checkin/Checkout values for 2026-06-01:")
        print(df_c.to_string())
        
    except Exception as e:
        print("Error:", e)
        
    conn.close()

if __name__ == "__main__":
    main()
