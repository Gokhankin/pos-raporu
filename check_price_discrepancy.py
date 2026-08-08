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
    
    # Run our query
    sql = """
        SELECT 
            f.RecId as FolioRecId,
            f.Amount as FolioAmount,
            f.LocalAmount as FolioLocalAmount,
            f.Rate as FolioRate,
            f.CurrencyCode as FolioCurrencyCode,
            f.NetAmount as FolioNetAmount,
            pd.SummaryId as RecId,
            pd.ProductId,
            p.Remark as Remark, -- product name
            pd.Amount as PosAmount,
            pd.Price as PosPrice,
            pd.LocalAmount as PosLocalAmount,
            pd.CurrCode as PosCurrCode,
            pd.Curr as PosCurrRate
        FROM Folio f
        JOIN PosDetail pd ON 
            f.Remark LIKE '%Pos Selling%'
            AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
            AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
        JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
        WHERE f.Deleted = 0
          AND f.DepartCode IN ('200', '300', '605')
          AND f.PostDate >= '2026-06-01' AND f.PostDate <= '2026-06-30'
    """
    df_db = pd.read_sql(sql, conn)
    
    # Strip whitespace in product name before merging
    df_db['Remark'] = df_db['Remark'].str.strip()
    df_excel['Remark'] = df_excel['Remark'].str.strip()
    
    # Merge DB and Excel to find price mismatches
    merged = pd.merge(df_db, df_excel, on=['RecId', 'Remark'], suffixes=('_db', '_excel'))
    
    # Let's find rows where the Excel Price does not match pd.PosAmount * pd.PosPrice
    merged['Price_diff'] = (merged['Price'] - (merged['PosAmount'] * merged['PosPrice'])).abs()
    mismatches = merged[merged['Price_diff'] > 0.01]
    
    print(f"Total rows matched between DB and Excel: {len(merged)}")
    print(f"Number of rows with price mismatches: {len(mismatches)}")
    
    if len(mismatches) > 0:
        print("\n--- Sample price mismatches details ---")
        cols_to_print = ['RecId', 'Remark', 'PosAmount', 'PosPrice', 'Price', 'FolioAmount', 'FolioLocalAmount', 'FolioRate', 'FolioCurrencyCode', 'FolioNetAmount', 'PosLocalAmount', 'PosCurrCode', 'PosCurrRate', 'LocalAmount']
        print(mismatches[cols_to_print].head(15).to_string())
        
    conn.close()

if __name__ == "__main__":
    main()
