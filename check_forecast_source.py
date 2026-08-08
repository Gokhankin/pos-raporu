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
    
    # 1. Let's see columns of DailyDetail
    print("--- Columns of DailyDetail ---")
    try:
        df_cols = pd.read_sql("SELECT TOP 0 * FROM DailyDetail", conn)
        print(df_cols.columns.tolist())
    except Exception as e:
        print("DailyDetail check failed:", e)
        
    # 2. Compare computed occupancy with Excel Forecast_Haziran for 2026-06-01
    print("\n--- Compare Occupancy for 2026-06-01 ---")
    try:
        # Load Excel Forecast June
        df_excel = pd.read_excel("Pos Satis.xlsx", sheet_name="Forecast_Haziran")
        excel_row_01 = df_excel[df_excel['Date'].astype(str).str.startswith('2026-06-01')]
        print("Excel values for 2026-06-01:")
        print(excel_row_01.to_string())
        
        # Query DB for 2026-06-01 stay date
        sql = """
            SELECT 
                COUNT(dd.RecId) as Sold,
                SUM(ISNULL(dd.Pax, 0)) as TotalPax,
                SUM(ISNULL(dd.Adult, 0)) as Adult,
                SUM(ISNULL(dd.Child, 0)) as Child1,
                SUM(ISNULL(dd.Child2, 0)) as Child2,
                SUM(ISNULL(dd.FreeChild, 0)) as FreeChild,
                SUM(ISNULL(dd.Baby, 0)) as Baby
            FROM DailyDetail dd
            JOIN Reservation r ON dd.ReservationId = r.RecId
            WHERE CAST(dd.StayDate AS DATE) = '2026-06-01'
              AND dd.Status IN (0,1,2,3) AND r.Status IN (0,1,2,3)
        """
        df_db = pd.read_sql(sql, conn)
        print("\nDB Query values for 2026-06-01:")
        print(df_db.to_string())
        
        # Let's check checkin and checkout rooms for 2026-06-01
        sql_c = """
            SELECT 
                SUM(CASE WHEN CAST(CheckinDate AS DATE) = '2026-06-01' THEN 1 ELSE 0 END) as Cin_Room,
                SUM(CASE WHEN CAST(CheckOutDate AS DATE) = '2026-06-01' THEN 1 ELSE 0 END) as Cout_Room
            FROM Reservation
            WHERE Status IN (0,1,2,3)
        """
        df_c = pd.read_sql(sql_c, conn)
        print("\nDB Checkin/Checkout values for 2026-06-01:")
        print(df_c.to_string())
        
    except Exception as e:
        print("Forecast check failed:", e)
        
    conn.close()

if __name__ == "__main__":
    main()
