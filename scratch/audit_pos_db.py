import os
from dotenv import load_dotenv
env_file_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file_path):
    load_dotenv(env_file_path)
else:
    load_dotenv()

import os
import pyodbc
import json
import decimal
from datetime import datetime

# Connection config
DB_CONFIG = {
    "server":   os.getenv("DB_HOST", "192.168.0.41"),
    "port":     1433,
    "database": "SednaAdakoy",
    "username": "sa",
    "password": "ClubAdakoy2022!",
}

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

def connect(db_name):
    for drv in ["{ODBC Driver 18 for SQL Server}", "{ODBC Driver 17 for SQL Server}", "{SQL Server}"]:
        try:
            cs = (
                f"DRIVER={drv};"
                f"SERVER={DB_CONFIG['server']},{DB_CONFIG['port']};"
                f"DATABASE={db_name};"
                f"UID={DB_CONFIG['username']};"
                f"PWD={DB_CONFIG['password']};"
                "TrustServerCertificate=yes;"
                "Encrypt=no;"
            )
            conn = pyodbc.connect(cs, timeout=5)
            return conn
        except:
            continue
    return None

def run_audit(db_name="SednaAdakoy"):
    print(f"Starting audit for database: {db_name}")
    
    conn = connect(db_name)
    if not conn:
        print(f"Connection error: Could not connect to {db_name} with any available driver.")
        return {"connection_error": f"Could not connect to {db_name} with any available driver."}
        
    try:
        cursor = conn.cursor()
    except Exception as e:
        print(f"Cursor error: {e}")
        conn.close()
        return {"connection_error": str(e)}
        
    audit_results = {
        "database": db_name,
        "timestamp": datetime.now().isoformat(),
        "orphaned_details_count": 0,
        "invalid_prices_count": 0,
        "mismatched_totals_count": 0,
        "null_values_count": 0,
        "mismatched_currencies_count": 0,
        "negative_deposits_count": 0,
        "invalid_folio_links_count": 0,
        "issues": []
    }
    
    # Check 1: Orphaned PosDetail rows
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM PosDetail d
            LEFT JOIN PosSummary s ON d.SummaryId = s.RecId
            WHERE s.RecId IS NULL
        """)
        count = cursor.fetchone()[0]
        audit_results["orphaned_details_count"] = count
        if count > 0:
            audit_results["issues"].append({
                "type": "Orphaned PosDetail",
                "severity": "High",
                "count": count,
                "description": "PosDetail rows where linked PosSummary does not exist."
            })
    except Exception as e:
        print(f"Error Check 1: {e}")
        
    # Check 2: Invalid Price or Amount in PosDetail
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM PosDetail
            WHERE Amount <= 0 OR Price < 0
        """)
        count = cursor.fetchone()[0]
        audit_results["invalid_prices_count"] = count
        if count > 0:
            cursor.execute("SELECT TOP 5 RecId, SummaryId, ProductId, Amount, Price FROM PosDetail WHERE Amount <= 0 OR Price < 0")
            samples = [list(r) for r in cursor.fetchall()]
            audit_results["issues"].append({
                "type": "Invalid Quantity or Price",
                "severity": "Medium",
                "count": count,
                "description": "Transactions with amount <= 0 or price < 0.",
                "samples": samples
            })
    except Exception as e:
        print(f"Error Check 2: {e}")

    # Check 3: Mismatched Header and Details Totals
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT s.RecId, s.PriceTotal, SUM(d.Total) as DetailTotal
                FROM PosSummary s
                JOIN PosDetail d ON d.SummaryId = s.RecId
                GROUP BY s.RecId, s.PriceTotal
                HAVING ABS(s.PriceTotal - SUM(d.Total)) > 0.05
            ) x
        """)
        count = cursor.fetchone()[0]
        audit_results["mismatched_totals_count"] = count
        if count > 0:
            cursor.execute("""
                SELECT TOP 5 s.RecId, s.PriceTotal, SUM(d.Total) as DetailTotal
                FROM PosSummary s
                JOIN PosDetail d ON d.SummaryId = s.RecId
                GROUP BY s.RecId, s.PriceTotal
                HAVING ABS(s.PriceTotal - SUM(d.Total)) > 0.05
            """)
            samples = [list(r) for r in cursor.fetchall()]
            audit_results["issues"].append({
                "type": "Mismatched Totals",
                "severity": "Medium",
                "count": count,
                "description": "PosSummary.PriceTotal is different from sum of details.",
                "samples": samples
            })
    except Exception as e:
        print(f"Error Check 3: {e}")

    # Check 4: Critical NULL fields in PosDetail
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM PosDetail
            WHERE SummaryId IS NULL OR ProductId IS NULL
        """)
        count = cursor.fetchone()[0]
        audit_results["null_values_count"] = count
        if count > 0:
            audit_results["issues"].append({
                "type": "NULL Values in PosDetail",
                "severity": "High",
                "count": count,
                "description": "PosDetail rows missing critical SummaryId or ProductId linkage."
            })
    except Exception as e:
        print(f"Error Check 4: {e}")

    # Check 5: Mismatched Currencies
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM PosDetail d
            JOIN PosSummary s ON d.SummaryId = s.RecId
            WHERE d.CurrCode <> s.CurrencyCode AND d.CurrCode IS NOT NULL AND s.CurrencyCode IS NOT NULL
        """)
        count = cursor.fetchone()[0]
        audit_results["mismatched_currencies_count"] = count
        if count > 0:
            audit_results["issues"].append({
                "type": "Mismatched Currencies",
                "severity": "Medium",
                "count": count,
                "description": "Header currency differs from item detail currency code."
            })
    except Exception as e:
        print(f"Error Check 5: {e}")

    # Check 6: Cashier Deposits check
    try:
        cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'ChashierDeposit'")
        deposit_cols = [r[0] for r in cursor.fetchall()]
        amount_col = next((c for c in deposit_cols if 'AMOUNT' in c.upper() or 'TUTAR' in c.upper() or 'DEPOSIT' in c.upper()), None)
        if amount_col:
            cursor.execute(f"SELECT COUNT(*) FROM ChashierDeposit WHERE [{amount_col}] < 0")
            count = cursor.fetchone()[0]
            audit_results["negative_deposits_count"] = count
            if count > 0:
                audit_results["issues"].append({
                    "type": "Negative Cashier Deposits",
                    "severity": "Low",
                    "count": count,
                    "description": f"Cashier deposit records with negative amounts in column {amount_col}."
                })
    except Exception as e:
        print(f"Error Check 6: {e}")

    # Check 7: Invalid Transferred Folio Links
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM PosSummary
            WHERE Transferred = 1 AND (FolioId IS NULL OR FolioId <= 0)
        """)
        count = cursor.fetchone()[0]
        audit_results["invalid_folio_links_count"] = count
        if count > 0:
            audit_results["issues"].append({
                "type": "Invalid Transferred Folio link",
                "severity": "Medium",
                "count": count,
                "description": "Bills marked as transferred to guest folios but lacking valid FolioId."
            })
    except Exception as e:
        print(f"Error Check 7: {e}")

    conn.close()
    return audit_results

if __name__ == "__main__":
    report_data = run_audit("SednaAdakoy")
    
    # Save the report JSON
    script_dir = os.path.dirname(os.path.abspath(__file__))
    report_file = os.path.join(script_dir, "pos_audit_latest.json")
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4, ensure_ascii=False, cls=DecimalEncoder)
        
    print(f"Audit completed. Report written to {report_file}")
