import os
import logging
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pyodbc
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DB_CONFIG = {
    "server":   "192.168.0.41",
    "port":     1433,
    "database": "SednaAdakoy",
    "username": "sa",
    "password": "ClubAdakoy2022!",
}

def get_db():
    for drv in ["{ODBC Driver 18 for SQL Server}", "{ODBC Driver 17 for SQL Server}", "{SQL Server}"]:
        try:
            cs = f"DRIVER={drv};SERVER={DB_CONFIG['server']},{DB_CONFIG['port']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']};TrustServerCertificate=yes;Encrypt=no;"
            return pyodbc.connect(cs, timeout=5)
        except Exception:
            continue
    return None

def check_db_connection():
    try:
        conn = get_db()
        if conn:
            conn.close()
            return True
        return False
    except Exception:
        return False

@app.route('/api/status')
def get_status():
    connected = check_db_connection()
    return jsonify({
        "status": "connected" if connected else "disconnected", 
        "db": "SednaAdakoy",
        "server": DB_CONFIG["server"]
    })

@app.route('/api/pos-summary')
def get_pos_summary():
    start_date = request.args.get("start", "2026-06-01")
    end_date = request.args.get("end", "2026-06-30")
    
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        cur = conn.cursor()
        
        # 1. Total KPI Metrics (Sum of Qty, Price EUR, Local Amount)
        sql_kpis = """
            SELECT 
                SUM(pd.Amount) as TotalQty,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as TotalEur,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) * f.Rate) as TotalLocal,
                COUNT(DISTINCT pd.SummaryId) as TotalChecks
            FROM Folio f
            JOIN PosDetail pd ON 
                f.Remark LIKE '%Pos Selling%'
                AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
                AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
            JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
            WHERE f.Deleted = 0
              AND f.DepartCode IN ('200', '300', '605', '615')
              AND f.PostDate >= ? AND f.PostDate <= ?
        """
        cur.execute(sql_kpis, start_date, end_date)
        kpi_row = cur.fetchone()
        
        kpis = {
            "total_qty": float(kpi_row[0] or 0.0),
            "total_eur": round(float(kpi_row[1] or 0.0), 2),
            "total_local": round(float(kpi_row[2] or 0.0), 2),
            "total_checks": int(kpi_row[3] or 0)
        }
        
        # 2. Department Breakdown
        sql_depart = """
            SELECT 
                d.DepartName,
                SUM(pd.Amount) as DepartQty,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as DepartEur
            FROM Folio f
            JOIN Department d ON f.DepartCode = d.DepartCode
            JOIN PosDetail pd ON 
                f.Remark LIKE '%Pos Selling%'
                AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
                AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
            JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
            WHERE f.Deleted = 0
              AND f.DepartCode IN ('200', '300', '605', '615')
              AND f.PostDate >= ? AND f.PostDate <= ?
            GROUP BY d.DepartName
        """
        cur.execute(sql_depart, start_date, end_date)
        departs = [{"department": r[0], "qty": float(r[1] or 0), "revenue": round(float(r[2] or 0), 2)} for r in cur.fetchall()]
        
        # 3. Revenue Group Breakdown (Categories)
        sql_revenue = """
            SELECT 
                rg.RevenueName,
                SUM(pd.Amount) as CategoryQty,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as CategoryEur
            FROM Folio f
            JOIN RevenueGroup rg ON f.RevenueGroupCode = rg.Code
            JOIN PosDetail pd ON 
                f.Remark LIKE '%Pos Selling%'
                AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
                AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
            JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
            WHERE f.Deleted = 0
              AND f.DepartCode IN ('200', '300', '605', '615')
              AND f.PostDate >= ? AND f.PostDate <= ?
            GROUP BY rg.RevenueName
        """
        cur.execute(sql_revenue, start_date, end_date)
        categories = [{"category": r[0], "qty": float(r[1] or 0), "revenue": round(float(r[2] or 0), 2)} for r in cur.fetchall()]
        
        # 4. Daily Sales Trend
        sql_trend = """
            SELECT 
                CAST(f.PostDate AS DATE) as TrendDate,
                SUM(pd.Amount) as DailyQty,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as DailyEur
            FROM Folio f
            JOIN PosDetail pd ON 
                f.Remark LIKE '%Pos Selling%'
                AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
                AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
            JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
            WHERE f.Deleted = 0
              AND f.DepartCode IN ('200', '300', '605', '615')
              AND f.PostDate >= ? AND f.PostDate <= ?
            GROUP BY CAST(f.PostDate AS DATE)
            ORDER BY TrendDate ASC
        """
        cur.execute(sql_trend, start_date, end_date)
        trend = [{"date": str(r[0]), "qty": float(r[1] or 0), "revenue": round(float(r[2] or 0), 2)} for r in cur.fetchall()]
        
        conn.close()
        return jsonify({
            "kpis": kpis,
            "departments": departs,
            "categories": categories,
            "trend": trend
        })
        
    except Exception as e:
        log.error(f"Summary API Error: {e}")
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/pos-transactions')
def get_pos_transactions():
    start_date = request.args.get("start", "2026-06-01")
    end_date = request.args.get("end", "2026-06-30")
    depart = request.args.get("department", "")
    category = request.args.get("category", "")
    search_val = request.args.get("search", "").strip()
    
    # Pagination
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 100))
    except ValueError:
        page, limit = 1, 100
        
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        cur = conn.cursor()
        
        # Build SQL dynamically with filters
        params = [start_date, end_date]
        filter_sql = ""
        
        if depart:
            filter_sql += " AND d.DepartName = ?"
            params.append(depart)
            
        if category:
            filter_sql += " AND rg.RevenueName = ?"
            params.append(category)
            
        if search_val:
            # Match room, name, remark (product description), check number or FolioId
            filter_sql += " AND (r.Room LIKE ? OR r.FirstName1 LIKE ? OR r.LastName1 LIKE ? OR p.Remark LIKE ? OR CAST(f.FolioId AS VARCHAR) LIKE ?)"
            search_param = f"%{search_val}%"
            params.extend([search_param, search_param, search_param, search_param, search_param])
            
        # Count Query
        count_sql = f"""
            SELECT COUNT(*)
            FROM Folio f
            JOIN Department d ON f.DepartCode = d.DepartCode
            JOIN RevenueGroup rg ON f.RevenueGroupCode = rg.Code
            LEFT JOIN Reservation r ON f.ReservationId = r.RecId
            JOIN PosDetail pd ON 
                f.Remark LIKE '%Pos Selling%'
                AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
                AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
            JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
            WHERE f.Deleted = 0
              AND f.DepartCode IN ('200', '300', '605', '615')
              AND f.PostDate >= ? AND f.PostDate <= ?
              {filter_sql}
        """
        cur.execute(count_sql, *params)
        total_records = cur.fetchone()[0]
        
        # Data Query with pagination (SQL Server 2012+ OFFSET FETCH)
        offset = (page - 1) * limit
        data_sql = f"""
            SELECT 
                r.Room,
                f.FolioId,
                r.FirstName1 + ' ' + r.LastName1 as GuestName,
                'Credit' as PosSaleType,
                CAST(f.PostDate AS DATE) as SellingDate,
                f.RecordTime as Time,
                d.DepartName,
                rg.RevenueName,
                p.Remark as ProductName,
                f.CheckNo,
                pd.Amount as Qty,
                pd.Price as UnitPriceEur,
                pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) as PriceEur,
                pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) * f.Rate as LocalAmount,
                pd.SummaryId as RecId
            FROM Folio f
            JOIN Department d ON f.DepartCode = d.DepartCode
            JOIN RevenueGroup rg ON f.RevenueGroupCode = rg.Code
            LEFT JOIN Reservation r ON f.ReservationId = r.RecId
            JOIN PosDetail pd ON 
                f.Remark LIKE '%Pos Selling%'
                AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
                AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
            JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
            WHERE f.Deleted = 0
              AND f.DepartCode IN ('200', '300', '605', '615')
              AND f.PostDate >= ? AND f.PostDate <= ?
              {filter_sql}
            ORDER BY SellingDate ASC, Time ASC, pd.RecId ASC
            OFFSET {offset} ROWS
            FETCH NEXT {limit} ROWS ONLY
        """
        cur.execute(data_sql, *params)
        rows = cur.fetchall()
        
        transactions = []
        for r in rows:
            transactions.append({
                "room": r[0] if r[0] else "-",
                "folio_id": int(r[1]) if r[1] else "-",
                "guest_name": r[2] if r[2] else "Walk-in Guest",
                "sale_type": r[3],
                "date": str(r[4]),
                "time": r[5] if r[5] else "-",
                "department": r[6],
                "category": r[7],
                "product_name": r[8],
                "check_no": r[9] if r[9] else "-",
                "qty": float(r[10] or 0),
                "unit_price": float(r[11] or 0),
                "price_eur": round(float(r[12] or 0), 2),
                "local_amount": round(float(r[13] or 0), 2),
                "rec_id": int(r[14])
            })
            
        conn.close()
        return jsonify({
            "total": total_records,
            "page": page,
            "limit": limit,
            "pages": (total_records + limit - 1) // limit,
            "transactions": transactions
        })
        
    except Exception as e:
        log.error(f"Transactions API Error: {e}")
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/pos-forecast')
def get_pos_forecast():
    start_date = request.args.get("start", "2026-06-01")
    end_date = request.args.get("end", "2026-06-30")
    
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        cur = conn.cursor()
        
        # 1. Fetch Occupancy Forecast by Day
        # Using Capacity = 111
        sql_occ = """
            SELECT 
                CAST(dd.StayDate AS DATE) as StayDate,
                COUNT(dd.RecId) as SoldRooms,
                SUM(ISNULL(dd.Pax, 0)) as Adults,
                SUM(ISNULL(dd.PaidChild, 0)) as PaidChild,
                SUM(ISNULL(dd.FreeChild, 0)) as FreeChild,
                SUM(ISNULL(dd.Baby, 0)) as Baby
            FROM DailyDetail dd
            JOIN Reservation r ON dd.ReservationId = r.RecId
            WHERE dd.Status IN (0,1,2,3) AND r.Status IN (1,3)
              AND dd.StayDate >= ? AND dd.StayDate <= ?
            GROUP BY CAST(dd.StayDate AS DATE)
            ORDER BY StayDate ASC
        """
        cur.execute(sql_occ, start_date, end_date)
        occ_rows = cur.fetchall()
        
        occupancy_dict = {}
        for r in occ_rows:
            s_date = str(r[0])
            sold = int(r[1] or 0)
            adults = int(r[2] or 0)
            paid_kid = int(r[3] or 0)
            free_kid = int(r[4] or 0)
            baby = int(r[5] or 0)
            total_pax = adults + paid_kid + free_kid + baby
            
            occupancy_dict[s_date] = {
                "date": s_date,
                "capacity": 111,
                "sold": sold,
                "difference": max(0, 111 - sold),
                "adult": adults,
                "paid_child": paid_kid,
                "free_child": free_kid,
                "baby": baby,
                "total_pax": total_pax,
                "occ_percent": round((sold / 111.0) * 100.0, 2) if sold > 0 else 0.0,
                "cin_room": 0, # We will fill this next
                "cout_room": 0,
                "pos_revenue": 0.0, # We will merge POS sales
                "pos_qty": 0.0
            }
            
        # 2. Fetch Checkin/Checkout details
        sql_cinout = """
            SELECT 
                CAST(CheckinDate AS DATE) as Date,
                COUNT(*) as CinCount
            FROM Reservation
            WHERE Status IN (1,3)
              AND CheckinDate >= ? AND CheckinDate <= ?
            GROUP BY CAST(CheckinDate AS DATE)
        """
        cur.execute(sql_cinout, start_date, end_date)
        for r in cur.fetchall():
            s_date = str(r[0])
            if s_date in occupancy_dict:
                occupancy_dict[s_date]["cin_room"] = int(r[1] or 0)
                
        sql_cout = """
            SELECT 
                CAST(CheckOutDate AS DATE) as Date,
                COUNT(*) as CoutCount
            FROM Reservation
            WHERE Status IN (1,3)
              AND CheckOutDate >= ? AND CheckOutDate <= ?
            GROUP BY CAST(CheckOutDate AS DATE)
        """
        cur.execute(sql_cout, start_date, end_date)
        for r in cur.fetchall():
            s_date = str(r[0])
            if s_date in occupancy_dict:
                occupancy_dict[s_date]["cout_room"] = int(r[1] or 0)
                
        # 3. Fetch POS revenue by day and merge
        sql_pos = """
            SELECT 
                CAST(f.PostDate AS DATE) as SalesDate,
                SUM(pd.Amount) as DailyQty,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as DailyEur
            FROM Folio f
            JOIN PosDetail pd ON 
                f.Remark LIKE '%Pos Selling%'
                AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
                AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
            JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
            WHERE f.Deleted = 0
              AND f.DepartCode IN ('200', '300', '605', '615')
              AND f.PostDate >= ? AND f.PostDate <= ?
            GROUP BY CAST(f.PostDate AS DATE)
        """
        cur.execute(sql_pos, start_date, end_date)
        for r in cur.fetchall():
            s_date = str(r[0])
            qty = float(r[1] or 0)
            eur = float(r[2] or 0)
            if s_date in occupancy_dict:
                occupancy_dict[s_date]["pos_revenue"] = round(eur, 2)
                occupancy_dict[s_date]["pos_qty"] = float(qty)
            else:
                # If there are POS sales on days without occupancy records (unlikely, but possible)
                occupancy_dict[s_date] = {
                    "date": s_date,
                    "capacity": 111,
                    "sold": 0,
                    "difference": 111,
                    "adult": 0,
                    "paid_child": 0,
                    "free_child": 0,
                    "baby": 0,
                    "total_pax": 0,
                    "occ_percent": 0.0,
                    "cin_room": 0,
                    "cout_room": 0,
                    "pos_revenue": round(eur, 2),
                    "pos_qty": float(qty)
                }
                
        # Sort by date
        sorted_forecast = sorted(occupancy_dict.values(), key=lambda x: x["date"])
        
        conn.close()
        return jsonify(sorted_forecast)
        
    except Exception as e:
        log.error(f"Forecast API Error: {e}")
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/pos-activities')
def get_pos_activities():
    start_date = request.args.get("start", "")
    end_date = request.args.get("end", "")
    
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        cur = conn.cursor()
        
        date_cond = ""
        params = []
        if start_date and end_date:
            date_cond = " AND f.PostDate >= ? AND f.PostDate <= ?"
            params = [start_date, end_date]
            
        # 1. Total KPIs for Activities
        sql_kpi = f"""
            SELECT 
                SUM(pd.Amount) as TotalQty,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as TotalEur,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) * f.Rate) as TotalLocal,
                COUNT(DISTINCT pd.SummaryId) as TotalChecks
            FROM Folio f
            JOIN PosDetail pd ON 
                f.Remark LIKE '%Pos Selling%'
                AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
                AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
            JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
            WHERE f.Deleted = 0
              AND (f.DepartCode = '615' OR f.RevenueGroupCode = 'A08')
              {date_cond}
        """
        cur.execute(sql_kpi, *params)
        kpi_row = cur.fetchone()
        
        kpis = {
            "total_qty": float(kpi_row[0] or 0.0),
            "total_eur": round(float(kpi_row[1] or 0.0), 2),
            "total_local": round(float(kpi_row[2] or 0.0), 2),
            "total_checks": int(kpi_row[3] or 0)
        }
        
        # 2. Monthly Activity Breakdown
        sql_monthly = f"""
            SELECT 
                FORMAT(f.PostDate, 'yyyy-MM') as MonthStr,
                COUNT(DISTINCT pd.SummaryId) as TotalChecks,
                SUM(pd.Amount) as TotalQty,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as TotalEur,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) * f.Rate) as TotalLocal
            FROM Folio f
            JOIN PosDetail pd ON 
                f.Remark LIKE '%Pos Selling%'
                AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
                AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
            JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
            WHERE f.Deleted = 0
              AND (f.DepartCode = '615' OR f.RevenueGroupCode = 'A08')
              {date_cond}
            GROUP BY FORMAT(f.PostDate, 'yyyy-MM')
            ORDER BY MonthStr ASC
        """
        cur.execute(sql_monthly, *params)
        monthly = []
        for r in cur.fetchall():
            m_str = str(r[0])
            monthly.append({
                "month": m_str,
                "checks": int(r[1] or 0),
                "qty": float(r[2] or 0),
                "revenue_eur": round(float(r[3] or 0), 2),
                "revenue_local": round(float(r[4] or 0), 2)
            })
            
        # 3. Product Breakdown
        sql_products = f"""
            SELECT 
                p.Remark as ProductName,
                COUNT(DISTINCT pd.SummaryId) as TotalChecks,
                SUM(pd.Amount) as TotalQty,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END)) as TotalEur,
                SUM(pd.Amount * pd.Price * (CASE WHEN f.Amount = 0 THEN 0 ELSE f.NetAmount / f.Amount END) * f.Rate) as TotalLocal
            FROM Folio f
            JOIN PosDetail pd ON 
                f.Remark LIKE '%Pos Selling%'
                AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
                AND CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) = pd.SummaryId
            JOIN Product p ON pd.ProductId = p.RecId AND f.RevenueGroupCode = p.RevenueCode
            WHERE f.Deleted = 0
              AND (f.DepartCode = '615' OR f.RevenueGroupCode = 'A08')
              {date_cond}
            GROUP BY p.Remark
            ORDER BY TotalEur DESC
        """
        cur.execute(sql_products, *params)
        products = []
        for r in cur.fetchall():
            products.append({
                "product_name": r[0],
                "checks": int(r[1] or 0),
                "qty": float(r[2] or 0),
                "revenue_eur": round(float(r[3] or 0), 2),
                "revenue_local": round(float(r[4] or 0), 2)
            })
            
        conn.close()
        return jsonify({
            "kpis": kpis,
            "monthly": monthly,
            "products": products
        })
        
    except Exception as e:
        log.error(f"Activities API Error: {e}")
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index(): 
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5070, debug=True)
