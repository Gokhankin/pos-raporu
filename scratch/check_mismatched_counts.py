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
    
    # Load Excel June
    df_excel = pd.read_excel("Pos Satis.xlsx", sheet_name=1) # June
    
    # We will query the DB for the same query as test_pos_join_v2
    sql = """
        SELECT 
            f.Remark,
            pd.SummaryId as RecId,
            pd.RecId as PosDetailRecId,
            pd.ProductId,
            p.Remark as ProductName,
            pd.Amount,
            pd.Price
        FROM Folio f
        JOIN PosDetail pd ON 
            f.Remark LIKE '%Pos Selling%'
            AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
            AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
        LEFT JOIN Product p ON pd.ProductId = p.RecId
        WHERE f.Deleted = 0
          AND f.DepartCode IN ('200', '300', '605')
          AND f.PostDate >= '2026-06-01' AND f.PostDate <= '2026-06-30'
    """
    df_db = pd.read_sql(sql, conn)
    
    # Group by RecId and compare sizes
    db_counts = df_db.groupby('RecId').size().to_frame('db_count')
    excel_counts = df_excel.groupby('RecId').size().to_frame('excel_count')
    
    diff = db_counts.join(excel_counts, how='inner')
    diff_mismatch = diff[diff['db_count'] != diff['excel_count']]
    
    print("Number of RecIds with mismatched row count:", len(diff_mismatch))
    print("\n--- Sample mismatches ---")
    print(diff_mismatch.head(10))
    
    # Let's inspect one specific mismatched RecId, e.g. the first one
    if len(diff_mismatch) > 0:
        mismatched_id = diff_mismatch.index[0]
        print(f"\nDetails for mismatched RecId {mismatched_id}:")
        print("\n--- DB Rows ---")
        print(df_db[df_db['RecId'] == mismatched_id].to_string())
        print("\n--- Excel Rows ---")
        print(df_excel[df_excel['RecId'] == mismatched_id].to_string())
        
    conn.close()

if __name__ == "__main__":
    main()
