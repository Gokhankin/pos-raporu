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
    
    # Updated SQL query with JOIN instead of LEFT JOIN for Product and Revenue code mapping
    sql = """
        SELECT 
            r.Room,
            f.FolioId,
            r.FirstName1 + ' ' + r.LastName1 as Name,
            'Credit' as PosSaleType,
            f.PostDate as SellingDate,
            f.RecordTime as Time,
            d.DepartName,
            rg.RevenueName,
            p.Remark as Remark,
            f.CheckNo,
            pd.Amount, -- Quantity in PosDetail
            pd.Price,  -- Unit price in PosDetail
            (pd.Amount * pd.Price) as PriceEur,
            -- Calculate local amount proportionally based on product share
            CASE 
                WHEN f.Amount = 0 THEN 0
                ELSE (pd.Amount * pd.Price) / f.Amount * f.LocalAmount
            END as LocalAmount,
            pd.SummaryId as RecId
        FROM Folio f
        JOIN Department d ON f.DepartCode = d.DepartCode
        JOIN RevenueGroup rg ON f.RevenueGroupCode = rg.Code
        LEFT JOIN Reservation r ON f.ReservationId = r.RecId
        -- Parse SummaryId from f.Remark
        JOIN PosDetail pd ON 
            f.Remark LIKE '%Pos Selling%'
            AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
            AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
        -- Inner join on Product and align with Folio's RevenueGroupCode
        JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
        WHERE f.Deleted = 0
          AND f.DepartCode IN ('200', '300', '605')
          AND f.PostDate >= '2026-06-01' AND f.PostDate <= '2026-06-30'
        ORDER BY f.PostDate ASC, f.RecordTime ASC, pd.RecId ASC
    """
    
    try:
        df_db = pd.read_sql(sql, conn)
        print("--- Query executed successfully ---")
        print("Row count:", len(df_db))
        print("Sum of Quantity (Amount):", df_db['Amount'].sum())
        print("Sum of Price EUR:", df_db['PriceEur'].sum())
        print("Sum of LocalAmount:", df_db['LocalAmount'].sum())
        
        # Load Excel Haziran to compare
        df_excel = pd.read_excel("Pos Satis.xlsx", sheet_name=1) # June
        print("\n--- Excel Haziran ---")
        print("Row count:", len(df_excel))
        print("Sum of Quantity (Amount):", df_excel['Amount'].sum())
        print("Sum of Price EUR:", df_excel['Price'].sum())
        print("Sum of LocalAmount:", df_excel['LocalAmount'].sum())
        
        # Check mismatch
        excel_recids = set(df_excel['RecId'].dropna().astype(int).tolist())
        db_recids = set(df_db['RecId'].dropna().astype(int).tolist())
        print(f"\nExcel Unique RecIds: {len(excel_recids)}")
        print(f"DB Unique RecIds: {len(db_recids)}")
        print(f"DB only: {len(db_recids - excel_recids)}")
        print(f"Excel only: {len(excel_recids - db_recids)}")
        
    except Exception as e:
        print("Query failed:", e)
        
    conn.close()

if __name__ == "__main__":
    main()
