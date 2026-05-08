# customer_analytics.py
# -----------------------------------------------------
# Customer Analytics API
# - ดึงข้อมูลจาก Database Cache (ไม่ต้องเรียก D365 API)
# - ไม่ผูกกับ pricing / quote flow
# -----------------------------------------------------

from fastapi import APIRouter, Query, HTTPException
from config.db_mssql import get_mssql_conn
from config.cache_config import USE_DATABASE_CACHE

router = APIRouter(
    prefix="/api/customer-analytics",
    tags=["customer-analytics"]
)

# =====================================================
# Helpers
# =====================================================

def get_customer_analytics_from_db(tax_no: str) -> dict:
    """
    ดึงข้อมูล analytics ของลูกค้าจาก database โดยใช้ tax_no
    รวมข้อมูลทุก customer_code ที่มี tax_no เดียวกัน
    
    Returns:
        dict with customer analytics data
    """
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # รวมข้อมูลทุก customer_code ที่มี tax_no เดียวกัน
        query = """
            SELECT 
                ? as tax_no,
                MAX(customer_name) as customer_name,
                SUM(ISNULL(accum_6m, 0)) as accum_6m,
                SUM(ISNULL(frequency, 0)) as frequency,
                SUM(ISNULL(sales_g_cust, 0)) as sales_g_cust,
                SUM(ISNULL(sales_a_cust, 0)) as sales_a_cust,
                SUM(ISNULL(sales_s_cust, 0)) as sales_s_cust,
                SUM(ISNULL(sales_y_cust, 0)) as sales_y_cust,
                SUM(ISNULL(sales_c_cust, 0)) as sales_c_cust,
                SUM(ISNULL(sales_e_cust, 0)) as sales_e_cust,
                MAX(calculation_date) as calculation_date
            FROM Customer
            WHERE tax_no = ? AND tax_no IS NOT NULL AND tax_no != ''
        """
        cursor.execute(query, (tax_no, tax_no))
        
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not row or row.accum_6m is None:
            raise HTTPException(status_code=404, detail=f"ไม่พบข้อมูลลูกค้าสำหรับ Tax No.: {tax_no}")
        
        return {
            "tax_no": row.tax_no or "",
            "customer_name": row.customer_name or "",
            "accum_6m": float(row.accum_6m or 0),
            "frequency": int(row.frequency or 0),
            "sales_g_cust": float(row.sales_g_cust or 0),
            "sales_a_cust": float(row.sales_a_cust or 0),
            "sales_s_cust": float(row.sales_s_cust or 0),
            "sales_y_cust": float(row.sales_y_cust or 0),
            "sales_c_cust": float(row.sales_c_cust or 0),
            "sales_e_cust": float(row.sales_e_cust or 0),
            "calculation_date": str(row.calculation_date) if row.calculation_date else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting customer analytics from database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ไม่สามารถดึงข้อมูล analytics ได้: {str(e)}"
        )


# =====================================================
# API 1: Monthly Summary (ยอดซื้อแยกรายเดือน 7 เดือน)
# =====================================================
@router.get("/monthly-summary")
def customer_monthly_summary(
    tax_no: str = Query(..., description="เลขประจำตัวผู้เสียภาษี เช่น 0105536001234"),
):
    """
    ====================================================
    ✅ ดึงยอดขายแยกรายเดือน 7 เดือน (6 เดือนย้อนหลัง + เดือนปัจจุบัน)
    ====================================================
    
    ดึงข้อมูลจาก Invoice API โดยใช้ tax_no
    หา customer_code ทั้งหมดที่มี tax_no เดียวกัน แล้วรวมยอดขาย
    
    JSON Response:
    {
      "tax_no": "0105536001234",
      "customer_name": "บริษัท ทดสอบ จำกัด",
      "anchor_date": "2026-02-24",
      "months": 7,
      "monthly": [
        {"month": "2025-08", "amount": 1832844.36},
        {"month": "2025-09", "amount": 1390871.59},
        ...
        {"month": "2026-02", "amount": 850000.00}
      ],
      "total": 9917398.51
    }
    """
    
    try:
        import requests
        from datetime import datetime, timedelta
        from collections import defaultdict
        from config.config_external_api import INVOICE_API_URL, INVOICE_API_HEADERS
        from config.db_mssql import get_mssql_conn
        
        # ขั้นตอนที่ 1: หา customer_code ทั้งหมดที่มี tax_no นี้
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        query = """
            SELECT customer_code, MAX(customer_name) as customer_name
            FROM Customer
            WHERE tax_no = ? AND tax_no IS NOT NULL AND tax_no != ''
            GROUP BY customer_code
        """
        cursor.execute(query, (tax_no,))
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not rows:
            raise HTTPException(status_code=404, detail=f"ไม่พบข้อมูลลูกค้าสำหรับ Tax No.: {tax_no}")
        
        customer_codes = [row.customer_code for row in rows]
        customer_name = rows[0].customer_name
        
        # ขั้นตอนที่ 2: คำนวณวันที่ (7 เดือน = 6 เดือนย้อนหลัง + เดือนปัจจุบัน)
        today = datetime.today()
        anchor_date = today.date().isoformat()
        start_date = (today - timedelta(days=6 * 31)).date().isoformat()  # 6 เดือนย้อนหลัง
        
        # ขั้นตอนที่ 3: ดึงข้อมูล invoice จาก API สำหรับทุก customer_code
        all_invoices = []
        
        for customer_code in customer_codes:
            page = 1
            max_page = 10
            
            while page <= max_page:
                payload = {
                    "page": page,
                    "size": 200,
                    "customer_code": {"$eq": customer_code},
                    "Posting Date": {"$gte": start_date}
                }
                
                try:
                    resp = requests.post(
                        INVOICE_API_URL,
                        json=payload,
                        headers=INVOICE_API_HEADERS,
                        timeout=30,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    items = data.get("data") or []
                    
                    if not items:
                        break
                    
                    all_invoices.extend(items)
                    
                    if len(items) < 200:
                        break
                        
                    page += 1
                    
                except Exception as e:
                    print(f"❌ Error loading invoices for {customer_code} (page {page}): {e}")
                    break
        
        # ขั้นตอนที่ 4: จัดกลุ่มตามเดือน
        monthly_sales = defaultdict(float)
        
        for inv in all_invoices:
            posting_date = inv.get("Posting Date")
            if not posting_date:
                continue
            
            # แปลงวันที่เป็น YYYY-MM
            try:
                date_obj = datetime.fromisoformat(posting_date.replace("Z", "+00:00"))
                month_key = date_obj.strftime("%Y-%m")
                
                # ใช้ Line_Amount_Include_VAT แทน Amount Including VAT
                amount_value = inv.get("Line_Amount_Include_VAT") or inv.get("Amount Including VAT")
                if amount_value is None or amount_value == "":
                    amount = 0
                else:
                    try:
                        amount = float(amount_value)
                    except (ValueError, TypeError):
                        amount = 0
                
                monthly_sales[month_key] += amount
                    
            except Exception as e:
                print(f"⚠️ Error parsing invoice: {e}")
                continue
        
        # ขั้นตอนที่ 5: สร้าง monthly array (เรียงตามลำดับเดือน)
        monthly = []
        total = 0
        
        for month_key in sorted(monthly_sales.keys()):
            amount = monthly_sales[month_key]
            monthly.append({
                "month": month_key,
                "amount": round(amount, 2)
            })
            total += amount
        
        return {
            "tax_no": tax_no,
            "customer_name": customer_name,
            "anchor_date": anchor_date,
            "months": 7,
            "monthly": monthly,
            "total": round(total, 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting monthly summary: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"ไม่สามารถดึงข้อมูลรายเดือนได้: {str(e)}"
        )


# =====================================================
# API 2: Category Summary (ใช้ข้อมูลจาก DB)
# =====================================================
@router.get("/category-summary")
def customer_category_summary(
    tax_no: str = Query(..., description="เลขประจำตัวผู้เสียภาษี เช่น 0105536001234"),
):
    """
    ====================================================
    ✅ API นี้ใช้ข้อมูลจาก Database Cache
    ====================================================
    
    JSON Response:
    {
      "tax_no": "0105536001234",
      "customer_name": "บริษัท ทดสอบ จำกัด",
      "calculation_date": "2026-02-24",
      "accum_6m": 9917398.51,
      "by_category": {
        "G": 320000.0,
        "A": 185000.0,
        "S": 140000.0,
        "Y": 45000.0,
        "C": 32000.0,
        "E": 22000.0
      },
      "relevant_category": "G",
      "relevant_sales": 320000.0
    }

    Field explanation:
    - accum_6m           : ยอดซื้อสะสม 6 เดือนจากคอลัมน์ accum_6m
    - by_category        : ยอดขายแยกตามประเภทสินค้า (G, A, S, Y, C, E)
    - relevant_category  : กลุ่มสินค้าที่มียอดขายสูงสุด
    - relevant_sales     : ยอดขายของกลุ่มนั้น
    ====================================================
    """
    
    if not USE_DATABASE_CACHE:
        raise HTTPException(
            status_code=503,
            detail="API นี้ต้องการ USE_DATABASE_CACHE=True"
        )
    
    analytics = get_customer_analytics_from_db(tax_no)
    
    # สร้าง by_category dict
    by_category = {
        "G": analytics["sales_g_cust"],
        "A": analytics["sales_a_cust"],
        "S": analytics["sales_s_cust"],
        "Y": analytics["sales_y_cust"],
        "C": analytics["sales_c_cust"],
        "E": analytics["sales_e_cust"],
    }
    
    # หา category ที่มียอดสูงสุด
    relevant_category = max(by_category, key=by_category.get)
    relevant_sales = by_category[relevant_category]
    
    return {
        "tax_no": analytics["tax_no"],
        "customer_name": analytics["customer_name"],
        "calculation_date": analytics["calculation_date"],
        "accum_6m": analytics["accum_6m"],
        "by_category": by_category,
    
    }
