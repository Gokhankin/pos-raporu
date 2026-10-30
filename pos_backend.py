import os
import logging
import time
from threading import Lock, Thread
from collections import defaultdict
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pyodbc
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

import sys

DB_CONFIG = {
    "server":   os.getenv("DB_SERVER", "192.168.0.41"),
    "port":     1433,
    "database": os.getenv("DB_NAME", "SednaAdakoy"),
    "username": os.getenv("DB_USER", "gokhan"),
    "password": os.getenv("DB_PASSWORD", "Ad!!2025!!"),
}

def get_db():
    for drv in ["{ODBC Driver 18 for SQL Server}", "{ODBC Driver 17 for SQL Server}", "{SQL Server}"]:
        try:
            cs = f"DRIVER={drv};SERVER={DB_CONFIG['server']},{DB_CONFIG['port']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']};TrustServerCertificate=yes;Encrypt=no;"
            return pyodbc.connect(cs, timeout=10, autocommit=True)
        except Exception:
            continue
    return None

# In-Memory Cache (TTL = 3600s / 60 minutes)
API_CACHE = {}
CACHE_LOCK = Lock()
CACHE_TTL = 3600
LOOKUP_CACHE = {"depts": None, "revs": None, "ts": 0}

def get_from_cache(key):
    now = time.time()
    with CACHE_LOCK:
        if key in API_CACHE:
            ts, val = API_CACHE[key]
            if now - ts < CACHE_TTL:
                return val
            else:
                del API_CACHE[key]
    return None

def set_to_cache(key, val):
    now = time.time()
    with CACHE_LOCK:
        API_CACHE[key] = (now, val)

def get_lookups(cur):
    now = time.time()
    if LOOKUP_CACHE["depts"] is not None and (now - LOOKUP_CACHE["ts"] < 3600):
        return LOOKUP_CACHE["depts"], LOOKUP_CACHE["revs"]
    cur.execute("SELECT DepartCode, DepartName FROM Department")
    depts = {str(r[0]).strip(): r[1] for r in cur.fetchall()}
    cur.execute("SELECT Code, RevenueName FROM RevenueGroup")
    revs = {str(r[0]).strip(): r[1] for r in cur.fetchall()}
    LOOKUP_CACHE["depts"] = depts
    LOOKUP_CACHE["revs"] = revs
    LOOKUP_CACHE["ts"] = now
    return depts, revs

def format_date_sql(date_str, default_val="", is_end=False):
    d_str = date_str if date_str else default_val
    if not d_str:
        return d_str
    try:
        clean_str = d_str.split('T')[0].strip()
        dt = datetime.strptime(clean_str, "%Y-%m-%d")
        if is_end:
            return dt.strftime("%Y%m%d 23:59:59")
        return dt.strftime("%Y%m%d 00:00:00")
    except Exception:
        return d_str.replace('-', '')

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
    server_ip = os.getenv("DB_SERVER", "192.168.0.41")
    return jsonify({
        "status": "connected" if connected else "disconnected", 
        "db": "SednaAdakoy",
        "server": server_ip
    })

@app.route('/api/clear-cache')
def clear_cache():
    with CACHE_LOCK:
        API_CACHE.clear()
    return jsonify({"status": "cache cleared"})

def fetch_base_transactions(start_raw, end_raw, force=False):
    base_key = f"base_tx_{start_raw}_{end_raw}"
    if not force:
        cached = get_from_cache(base_key)
        if cached is not None:
            return cached, None

    start_date = format_date_sql(start_raw, "2026-06-01")
    end_date = format_date_sql(end_raw, "2026-06-30", is_end=True)

    conn = get_db()
    if not conn:
        return None, "Database connection failed"

    try:
        cur = conn.cursor()
        dept_map, rev_map = get_lookups(cur)

        # Group Folio by (SummaryId, DepartCode, RevenueGroupCode) to prevent split-folio duplication
        # and allocate exact Folio.NetAmount proportionally across valid PosDetail items (excluding barcode-in-quantity errors > 1000)
        data_sql = """
            ;WITH FolioClean AS (
                SELECT 
                    f.RecId,
                    f.FolioId,
                    f.ReservationId,
                    CAST(f.PostDate AS DATE) as PostDate,
                    f.RecordTime,
                    f.CheckNo,
                    f.DepartCode,
                    f.RevenueGroupCode,
                    CAST(f.Amount AS FLOAT) as FolioAmt,
                    CAST(f.NetAmount AS FLOAT) as FolioNetAmt,
                    CAST(f.NetAmount * f.Rate AS FLOAT) as FolioLocalAmt,
                    CAST(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1) AS INT) as SummaryId
                FROM Folio f
                WHERE f.Deleted = 0
                  AND f.DepartCode IN ('200', '300', '605', '615')
                  AND f.CorrectionMasterId = 0
                  AND f.ActionType != 2
                  AND NOT EXISTS (
                      SELECT 1 FROM Folio corr 
                      WHERE corr.CorrectionMasterId = f.RecId 
                        AND corr.Deleted = 0
                  )
                  AND f.PostDate >= ? AND f.PostDate <= ?
                  AND f.Remark LIKE '%Pos Selling%'
                  AND ISNUMERIC(LEFT(f.Remark, CHARINDEX(' ', f.Remark + ' ') - 1)) = 1
            ),
            FolioGrouped AS (
                SELECT 
                    SummaryId,
                    DepartCode,
                    RevenueGroupCode,
                    MIN(PostDate) as PostDate,
                    MAX(FolioId) as FolioId,
                    MAX(ReservationId) as ReservationId,
                    MAX(RecordTime) as RecordTime,
                    MAX(CheckNo) as CheckNo,
                    SUM(FolioAmt) as GroupFolioAmt,
                    SUM(FolioNetAmt) as GroupFolioNetAmt,
                    SUM(FolioLocalAmt) as GroupFolioLocalAmt
                FROM FolioClean
                GROUP BY SummaryId, DepartCode, RevenueGroupCode
            ),
            ValidPd AS (
                SELECT 
                    pd.RecId as PdRecId,
                    pd.SummaryId,
                    pd.ProductId,
                    p.RevenueCode,
                    p.Remark as ProductName,
                    CAST(pd.Amount AS FLOAT) as PdQty,
                    CAST(pd.Price AS FLOAT) as PdPrice,
                    CAST(ISNULL(pd.DiscountRatio, 0) AS FLOAT) as DiscountRatio,
                    CAST(ISNULL(pd.Discount, 0) AS FLOAT) as DiscountEur,
                    CAST(ISNULL(pd.Total, pd.Amount * pd.Price) AS FLOAT) as PdGross,
                    SUM(CAST(pd.Amount * pd.Price AS FLOAT)) OVER (PARTITION BY pd.SummaryId, p.RevenueCode) as GroupPdGross,
                    COUNT(*) OVER (PARTITION BY pd.SummaryId, p.RevenueCode) as GroupPdCnt
                FROM PosDetail pd
                JOIN Product p ON pd.ProductId = p.RecId
                WHERE pd.Amount <= 1000
            )
            SELECT 
                COALESCE(NULLIF(r.Room, ''), 'Walk-In') as Room,
                fg.FolioId,
                COALESCE(NULLIF(LTRIM(RTRIM(r.FirstName1 + ' ' + r.LastName1)), ''), 'Walk-in Misafir') as GuestName,
                'Credit' as PosSaleType,
                fg.PostDate as SellingDate,
                fg.RecordTime as Time,
                fg.DepartCode,
                fg.RevenueGroupCode,
                vpd.ProductName,
                COALESCE(NULLIF(fg.CheckNo, ''), CAST(vpd.SummaryId AS VARCHAR)) as CheckNo,
                vpd.PdQty as Qty,
                vpd.PdPrice as UnitPriceEur,
                fg.GroupFolioNetAmt * (CASE WHEN vpd.GroupPdGross = 0 THEN (1.0 / vpd.GroupPdCnt) ELSE (vpd.PdGross / vpd.GroupPdGross) END) as PriceEur,
                fg.GroupFolioLocalAmt * (CASE WHEN vpd.GroupPdGross = 0 THEN (1.0 / vpd.GroupPdCnt) ELSE (vpd.PdGross / vpd.GroupPdGross) END) as LocalAmount,
                vpd.SummaryId as RecId,
                vpd.DiscountRatio,
                vpd.DiscountEur,
                vpd.PdGross as GrossEur,
                vpd.PdRecId
            FROM FolioGrouped fg
            LEFT JOIN Reservation r ON fg.ReservationId = r.RecId
            JOIN ValidPd vpd ON fg.SummaryId = vpd.SummaryId AND fg.RevenueGroupCode = vpd.RevenueCode
            ORDER BY fg.PostDate ASC, fg.RecordTime ASC, vpd.PdRecId ASC
            OPTION (RECOMPILE)
        """
        cur.execute(data_sql, start_date, end_date)
        rows = cur.fetchall()
        conn.close()

        transactions = []
        for r in rows:
            d_code = str(r[6] or "").strip()
            r_code = str(r[7] or "").strip()
            d_name = dept_map.get(d_code, d_code)
            c_name = rev_map.get(r_code, r_code)
            room_str = r[0] if r[0] else "Walk-In"
            folio_val = int(r[1]) if r[1] else "-"
            guest_str = r[2] if r[2] else "Walk-in Misafir"
            prod_str = r[8] or ""
            rec_id_val = int(r[14])
            check_str = str(r[9]) if r[9] else str(rec_id_val)
            raw_eur = float(r[12] or 0.0)
            raw_loc = float(r[13] or 0.0)
            gross_eur = float(r[17] or 0.0)
            disc_ratio = float(r[15] or 0.0)
            if disc_ratio == 0.0 and gross_eur > 0 and raw_eur < gross_eur - 0.01:
                disc_ratio = round(((gross_eur - raw_eur) / gross_eur) * 100.0, 2)

            transactions.append({
                "room": room_str,
                "folio_id": folio_val,
                "guest_name": guest_str,
                "sale_type": r[3],
                "date": str(r[4]),
                "time": r[5] if r[5] else "-",
                "department": d_name,
                "category": c_name,
                "product_name": prod_str,
                "check_no": check_str,
                "qty": float(r[10] or 0),
                "unit_price": float(r[11] or 0),
                "price_eur": round(raw_eur, 2),
                "local_amount": round(raw_loc, 2),
                "_raw_eur": raw_eur,
                "_raw_local": raw_loc,
                "rec_id": rec_id_val,
                "discount_ratio": disc_ratio,
                "discount_eur": round(max(0.0, gross_eur - raw_eur), 2),
                "gross_eur": round(gross_eur, 2),
                "_search": f"{room_str} {guest_str} {prod_str} {folio_val} {rec_id_val}".lower()
            })

        set_to_cache(base_key, transactions)
        return transactions, None
    except Exception as e:
        log.error(f"Transactions API Error: {e}")
        if conn: conn.close()
        return None, str(e)

def compute_pos_summary(start_raw, end_raw, force=False):
    cache_key = f"summary_{start_raw}_{end_raw}"
    if not force:
        cached = get_from_cache(cache_key)
        if cached:
            return cached, 200

    all_tx, err = fetch_base_transactions(start_raw, end_raw, force)
    if err or all_tx is None:
        return {"error": err or "Database connection failed"}, 500

    total_qty = 0.0
    total_eur = 0.0
    total_local = 0.0
    checks_set = set()

    depart_agg = defaultdict(lambda: {"qty": 0.0, "eur": 0.0})
    cat_agg = defaultdict(lambda: {"qty": 0.0, "eur": 0.0})
    trend_agg = defaultdict(lambda: {"qty": 0.0, "eur": 0.0})

    for t in all_tx:
        t_date = t["date"]
        d_name = t["department"]
        c_name = t["category"]
        summary_id = t["rec_id"]
        qty = t["qty"]
        eur = t["_raw_eur"]
        loc = t["_raw_local"]

        total_qty += qty
        total_eur += eur
        total_local += loc
        if summary_id is not None:
            checks_set.add(summary_id)

        depart_agg[d_name]["qty"] += qty
        depart_agg[d_name]["eur"] += eur

        cat_agg[c_name]["qty"] += qty
        cat_agg[c_name]["eur"] += eur

        trend_agg[t_date]["qty"] += qty
        trend_agg[t_date]["eur"] += eur

    kpis = {
        "total_qty": round(total_qty, 2),
        "total_eur": round(total_eur, 2),
        "total_local": round(total_local, 2),
        "total_checks": len(checks_set)
    }

    departs = [
        {"department": k, "qty": round(v["qty"], 2), "revenue": round(v["eur"], 2)}
        for k, v in depart_agg.items()
    ]
    categories = [
        {"category": k, "qty": round(v["qty"], 2), "revenue": round(v["eur"], 2)}
        for k, v in cat_agg.items()
    ]
    trend = [
        {"date": k, "qty": round(v["qty"], 2), "revenue": round(v["eur"], 2)}
        for k, v in sorted(trend_agg.items(), key=lambda x: x[0])
    ]
    
    res = {
        "kpis": kpis,
        "departments": departs,
        "categories": categories,
        "trend": trend
    }
    set_to_cache(cache_key, res)
    return res, 200

@app.route('/api/pos-summary')
def get_pos_summary():
    start_raw = request.args.get("start", "2026-06-01")
    end_raw = request.args.get("end", "2026-06-30")
    force = request.args.get("force", "0") == "1"
    res, code = compute_pos_summary(start_raw, end_raw, force)
    return jsonify(res), code

@app.route('/api/pos-transactions')
def get_pos_transactions():
    start_raw = request.args.get("start", "2026-06-01")
    end_raw = request.args.get("end", "2026-06-30")
    depart = request.args.get("department", "")
    category = request.args.get("category", "")
    search_val = request.args.get("search", "").strip().lower()
    force = request.args.get("force", "0") == "1"
    
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 100))
    except ValueError:
        page, limit = 1, 100

    all_tx, err = fetch_base_transactions(start_raw, end_raw, force)
    if err:
        return jsonify({"error": err}), 500

    filtered = all_tx
    if depart:
        filtered = [t for t in filtered if t["department"] == depart]
    if category:
        filtered = [t for t in filtered if t["category"] == category]
    if search_val:
        filtered = [t for t in filtered if search_val in t["_search"]]

    total_records = len(filtered)
    offset = (page - 1) * limit
    page_items = [
        {k: v for k, v in t.items() if not k.startswith("_")}
        for t in filtered[offset:offset + limit]
    ]

    res = {
        "total": total_records,
        "page": page,
        "limit": limit,
        "pages": (total_records + limit - 1) // limit if limit > 0 else 1,
        "transactions": page_items
    }
    return jsonify(res)

@app.route('/api/pos-forecast')
def get_pos_forecast():
    start_raw = request.args.get("start", "2026-06-01")
    end_raw = request.args.get("end", "2026-06-30")
    force = request.args.get("force", "0") == "1"
    
    cache_key = f"forecast_{start_raw}_{end_raw}"
    if not force:
        cached = get_from_cache(cache_key)
        if cached:
            return jsonify(cached)
            
    start_date = format_date_sql(start_raw, "2026-06-01")
    end_date = format_date_sql(end_raw, "2026-06-30", is_end=True)
    
    conn = get_db()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    try:
        cur = conn.cursor()
        
        # 1. Fetch Occupancy Forecast by Day (Capacity = 111)
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
                "cin_room": 0,
                "cout_room": 0,
                "pos_revenue": 0.0,
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
        conn.close()

        # 3. Merge clean POS revenue and qty by day from compute_pos_summary
        summary_data, _ = compute_pos_summary(start_raw, end_raw, force)
        for t_row in summary_data.get("trend", []):
            s_date = t_row["date"]
            qty = float(t_row["qty"] or 0)
            eur = float(t_row["revenue"] or 0)
            if s_date in occupancy_dict:
                occupancy_dict[s_date]["pos_revenue"] = round(eur, 2)
                occupancy_dict[s_date]["pos_qty"] = float(qty)
            else:
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
                
        sorted_forecast = sorted(occupancy_dict.values(), key=lambda x: x["date"])
        set_to_cache(cache_key, sorted_forecast)
        return jsonify(sorted_forecast)
        
    except Exception as e:
        log.error(f"Forecast API Error: {e}")
        if conn: conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/pos-activities')
def get_pos_activities():
    start_raw = request.args.get("start", "2026-05-01") or "2026-05-01"
    end_raw = request.args.get("end", "2026-10-31") or "2026-10-31"
    force = request.args.get("force", "0") == "1"
    
    cache_key = f"activities_{start_raw}_{end_raw}"
    if not force:
        cached = get_from_cache(cache_key)
        if cached:
            return jsonify(cached)

    all_tx, err = fetch_base_transactions(start_raw, end_raw, force)
    if err or all_tx is None:
        return jsonify({"error": err or "Database connection failed"}), 500

    total_qty = 0.0
    total_eur = 0.0
    total_local = 0.0
    all_checks = set()
    monthly_map = defaultdict(lambda: {"checks": set(), "qty": 0.0, "eur": 0.0, "local": 0.0})
    products_map = defaultdict(lambda: {"checks": set(), "qty": 0.0, "eur": 0.0, "local": 0.0})

    for t in all_tx:
        if t["department"] == "Activity Department" or t["category"] == "Activity Revenue %20":
            m_str = t["date"][:7]
            p_name = t["product_name"] or "Bilinmeyen Aktivite"
            summary_id = t["rec_id"]
            qty = t["qty"]
            eur = t["_raw_eur"]
            local = t["_raw_local"]

            total_qty += qty
            total_eur += eur
            total_local += local
            all_checks.add(summary_id)

            monthly_map[m_str]["checks"].add(summary_id)
            monthly_map[m_str]["qty"] += qty
            monthly_map[m_str]["eur"] += eur
            monthly_map[m_str]["local"] += local

            products_map[p_name]["checks"].add(summary_id)
            products_map[p_name]["qty"] += qty
            products_map[p_name]["eur"] += eur
            products_map[p_name]["local"] += local

    kpis = {
        "total_qty": round(total_qty, 2),
        "total_eur": round(total_eur, 2),
        "total_local": round(total_local, 2),
        "total_checks": len(all_checks)
    }
    monthly = [
        {
            "month": m_str,
            "checks": len(m_data["checks"]),
            "qty": round(m_data["qty"], 2),
            "revenue_eur": round(m_data["eur"], 2),
            "revenue_local": round(m_data["local"], 2)
        }
        for m_str, m_data in sorted(monthly_map.items())
    ]
    products = sorted(
        [
            {
                "product_name": p_name,
                "checks": len(p_data["checks"]),
                "qty": round(p_data["qty"], 2),
                "revenue_eur": round(p_data["eur"], 2),
                "revenue_local": round(p_data["local"], 2)
            }
            for p_name, p_data in products_map.items()
        ],
        key=lambda x: x["revenue_eur"],
        reverse=True
    )
    res = {"kpis": kpis, "monthly": monthly, "products": products}
    set_to_cache(cache_key, res)
    return jsonify(res)

@app.route("/")
def index(): 
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)

def warm_default_caches():
    time.sleep(0.5)
    ranges = [
        ("2026-10-01", "2026-10-31"),
        ("2026-09-01", "2026-09-30"),
        ("2026-08-01", "2026-08-31"),
        ("2026-07-01", "2026-07-31"),
        ("2026-06-01", "2026-06-30"),
        ("2026-05-01", "2026-05-31"),
        ("2026-05-01", "2026-10-31"),
    ]
    for s, e in ranges:
        try:
            compute_pos_summary(s, e, force=False)
            log.info(f"Pre-warmed POS cache for {s}..{e}")
        except Exception as ex:
            log.warning(f"Cache warm failed for {s}..{e}: {ex}")

Thread(target=warm_default_caches, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5070, threaded=True)
