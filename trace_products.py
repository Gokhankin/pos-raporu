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
    
    xls = pd.ExcelFile("Pos Satis.xlsx")
    df_excel = pd.read_excel(xls, 1) # June sheet
    
    # Let's pick 5 rows from Excel that have product descriptions and check their RecId in DB
    sample_rows = df_excel.head(5)
    
    print("--- Matching Excel rows to DB ---")
    for idx, row in sample_rows.iterrows():
        rec_id = int(row['RecId'])
        excel_remark = row['Remark']
        excel_name = row['Name']
        excel_price = row['Price']
        
        print(f"\nExcel Row {idx}: RecId={rec_id}, ProductDescription='{excel_remark}', Price={excel_price}, Name='{excel_name}'")
        
        # Let's query DB for PosDetail
        cur = conn.cursor()
        cur.execute("SELECT ProductId, Amount, Price, ProductDescription, ProRemark, RecordDate FROM PosDetail WHERE RecId = ?", rec_id)
        pos_detail = cur.fetchone()
        
        if pos_detail:
            p_id, amt, prc, p_desc, pro_rem, rec_date = pos_detail
            print(f"  DB PosDetail: ProductId={p_id}, Amount={amt}, Price={prc}, ProductDescription='{p_desc}', ProRemark='{pro_rem}', RecordDate={rec_date}")
            
            # Let's get the product name from Product table
            cur.execute("SELECT Code, Remark, PosRemark FROM Product WHERE RecId = ?", p_id)
            prod = cur.fetchone()
            if prod:
                p_code, p_rem, p_posrem = prod
                print(f"  DB Product: Code='{p_code}', Remark='{p_rem}', PosRemark='{p_posrem}'")
            else:
                print("  DB Product: NOT FOUND")
        else:
            print("  DB PosDetail: NOT FOUND")
            
    conn.close()

if __name__ == "__main__":
    main()
