# customer.py — MSSQL Database Version
from fastapi import APIRouter, Query, HTTPException
from config.db_mssql import get_mssql_conn
import logging

router = APIRouter(prefix="/api/customer")
logger = logging.getLogger(__name__)

# =====================================================
# Helpers
# =====================================================
def clean(x):
    if x is None:
        return ""
    return str(x).strip() if x else ""


# =====================================================
# Database Search Functions
# =====================================================

async def search_customer_from_db(
    code: str | None = None,
    phone: str | None = None,
    name: str | None = None,
    product_group: str | None = None
) -> dict:
    """
    Search customer from database table.
    
    Args:
        code: Customer code for exact match
        phone: Phone number for normalized match
        name: Customer name for partial match
        product_group: Product group (G/A/S/Y/C/E) to calculate relevantSales
    
    Returns:
        Customer data with analytics
    """
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # Build WHERE clause
        where_parts = []
        params = []
        
        if code:
            where_parts.append("customer_code = ?")
            params.append(code.strip())
        elif phone:
            # Normalize phone (remove non-digits)
            normalized_phone = "".join(ch for ch in phone if ch.isdigit())
            where_parts.append("REPLACE(REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '(', ''), ')', '') LIKE ?")
            params.append(f"%{normalized_phone}%")
        elif name:
            where_parts.append("LOWER(customer_name) LIKE ?")
            params.append(f"%{name.strip().lower()}%")
        
        if not where_parts:
            raise HTTPException(status_code=400, detail="กรุณาระบุ code, phone หรือ name อย่างน้อย 1 ค่า")
        
        query = f"""
            SELECT TOP 1
                customer_code, customer_name, phone, tax_no, gen_bus,
                payment_terms, customer_date, blocked, accum_6m, frequency,
                sales_g_cust, sales_a_cust, sales_s_cust, sales_y_cust,
                sales_c_cust, sales_e_cust
            FROM Customer
            WHERE {' OR '.join(where_parts)}
        """
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="ไม่พบข้อมูลลูกค้า")
        
        # Build response
        sales_g = float(row.sales_g_cust or 0)
        sales_a = float(row.sales_a_cust or 0)
        sales_s = float(row.sales_s_cust or 0)
        sales_y = float(row.sales_y_cust or 0)
        sales_c = float(row.sales_c_cust or 0)
        sales_e = float(row.sales_e_cust or 0)
        
        # Calculate relevant_sales based on product_group
        sales_map = {
            "G": sales_g,
            "A": sales_a,
            "S": sales_s,
            "Y": sales_y,
            "C": sales_c,
            "E": sales_e,
        }
        
        # If product_group is specified, use that group's sales
        # Otherwise, use max of all groups (backward compatible)
        if product_group and product_group.upper() in sales_map:
            relevant_sales = sales_map[product_group.upper()]
        else:
            relevant_sales = max(sales_g, sales_a, sales_s, sales_y, sales_c, sales_e)
        
        price_level = sales_e
        
        base = {
            "id": row.customer_code or "",
            "name": row.customer_name or "",
            "tax_no": row.tax_no or "",
            "phone": row.phone or "",
            "gen_bus": row.gen_bus or "",
            "customer_date": str(row.customer_date) if row.customer_date else "",
            "payment_terms": row.payment_terms or "",
            "blocked": row.blocked or "",
            
            "accum_6m": float(row.accum_6m or 0),
            "frequency": int(row.frequency or 0),
            
            "sales_g_cust": sales_g,
            "sales_a_cust": sales_a,
            "sales_s_cust": sales_s,
            "sales_y_cust": sales_y,
            "sales_c_cust": sales_c,
            "sales_e_cust": sales_e,
            
            "price_level": price_level,
        }
        
        base["creditTerm"] = base["payment_terms"]
        
        # ⚠️ DEPRECATED: Duplicate data - use sales_*_cust instead
        # base["sales_g"] = base["sales_g_cust"]
        # base["sales_a"] = base["sales_a_cust"]
        # base["sales_s"] = base["sales_s_cust"]
        # base["sales_y"] = base["sales_y_cust"]
        # base["sales_c"] = base["sales_c_cust"]
        # base["sales_e"] = base["sales_e_cust"]
        
        base["relevantSales"] = relevant_sales
        
        # ⭐ คำนวณ Tier โดยใช้ LevelPrice
        try:
            from LevelPrice import LevelPrice
            import pandas as pd
            
            # สร้าง DataFrame จากข้อมูลลูกค้า
            customer_df = pd.DataFrame([{
                "customer_date": row.customer_date,
                "accum_6m": row.accum_6m or 0,
                "frequency": row.frequency or 0,
                "gen_bus": row.gen_bus or "",
            }])
            
            # คำนวณ Tier
            result_df = LevelPrice(customer_df)
            tier = result_df["tier"].iloc[0] if "tier" in result_df.columns else "Unknown"
            base["tier"] = tier
        except Exception as e:
            print(f"Warning: Could not calculate tier for {row.customer_code}: {e}")
            base["tier"] = "Unknown"
        
        # ดึงข้อมูล credit_terms จาก Credit API
        try:
            import httpx
            from config.config_external_api import CREDIT_API_URL, CREDIT_API_HEADERS
            
            credit_url = f"{CREDIT_API_URL}/api/external/credit-status/{row.customer_code}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                credit_response = await client.get(
                    credit_url,
                    headers=CREDIT_API_HEADERS,
                    params={"mock": "false"}
                )
                if credit_response.status_code == 200:
                    credit_data = credit_response.json()
                    base["credit_terms"] = credit_data.get("credit_terms", {})
                else:
                    base["credit_terms"] = {}
        except Exception as e:
            print(f"Warning: Could not fetch credit terms for {row.customer_code}: {e}")
            base["credit_terms"] = {}
        
        cursor.close()
        conn.close()
        
        return base
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error searching customer from database: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ไม่สามารถค้นหาข้อมูลลูกค้าได้: {str(e)}"
        )


# =====================================================
# GET /customer/search (รองรับทั้ง GET และ POST)
# =====================================================
@router.get("/search")
@router.post("/search")
async def search_customer(
    code: str | None = Query(None),
    phone: str | None = Query(None),
    name: str | None = Query(None),
    product_group: str | None = Query(None, description="Product group (G/A/S/Y/C/E) for relevantSales calculation"),
):
    """
    ค้นหาลูกค้าจาก MSSQL Database
    
    Parameters:
        - code: รหัสลูกค้า (exact match)
        - phone: เบอร์โทรศัพท์ (partial match)
        - name: ชื่อลูกค้า (partial match)
        - product_group: กลุ่มสินค้า (G/A/S/Y/C/E) สำหรับคำนวณ relevantSales
    
    Returns:
        Customer data with analytics from database
        
    Examples:
        - /api/customer/search?code=08015AY
        - /api/customer/search?code=08015AY&product_group=E
        - /api/customer/search?name=จำรัส&product_group=G
    """
    if not code and not phone and not name:
        raise HTTPException(
            status_code=400,
            detail="กรุณาระบุ code, phone หรือ name อย่างน้อย 1 ค่า",
        )
    
  
    try:
        return await search_customer_from_db(code=code, phone=phone, name=name, product_group=product_group)
    except HTTPException as e:
        # ถ้าไม่พบลูกค้า และมี code ให้ return ข้อมูลลูกค้าใหม่ (temp customer)
        if e.status_code == 404 and code:
            return {
                "id": code,
                "name": "",
                "phone": "",
                "tax_no": "",
                "gen_bus": "",
                "customer_date": "",
                "payment_terms": "",
                "blocked": 0,
                "accum_6m": 0,
                "frequency": 0,
                "sales_g_cust": 0,
                "sales_a_cust": 0,
                "sales_s_cust": 0,
                "sales_y_cust": 0,
                "sales_c_cust": 0,
                "sales_e_cust": 0,
                "price_level": 0,
                "creditTerm": "",
                # "sales_g": 0,
                # "sales_a": 0,
                # "sales_s": 0,
                # "sales_y": 0,
                # "sales_c": 0,
                # "sales_e": 0,
                "relevantSales": 0,
                "tier": "Unknown",
                "credit_terms": {},
                "isTempCustomer": True,
            }
        raise

def search_customer_list_from_db(query: str) -> list:
    """
    Search customer list from database for autocomplete.
    Uses Full-Text Search if available, otherwise falls back to LIKE.
    Smart ranking: exact match first, then starts-with, then contains
    
    Args:
        query: Search query string
    
    Returns:
        List of customer summaries (max 15 results)
    """
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        q_clean = query.strip()
        q_lower = q_clean.lower()
        
        # Normalize phone query
        q_phone = "".join(ch for ch in query if ch.isdigit())
        
        #ตรวจสอบว่ามี Full-Text Index หรือไม่
        cursor.execute("""
            SELECT COUNT(*) as has_fulltext
            FROM sys.fulltext_indexes 
            WHERE object_id = OBJECT_ID('Customer')
        """)
        has_fulltext = cursor.fetchone().has_fulltext > 0
        
        # ตรวจสอบว่าเป็นภาษาไทยหรือไม่
        has_thai = any(ord(c) > 127 for c in q_clean)
        
        if has_fulltext and not has_thai:
            # ใช้ Full-Text Search สำหรับภาษาอังกฤษ/ตัวเลข
            if q_clean.replace('-', '').replace('.', '').isalnum():
                # Code/Phone search (prefix)
                search_term = f'"{q_clean}*"'
                sql = """
                    SELECT TOP 15
                        customer_code, 
                        customer_name, 
                        phone, 
                        tax_no,
                        blocked,
                        CASE
                            WHEN LOWER(customer_code) = ? THEN 1
                            WHEN LOWER(customer_code) LIKE ? THEN 2
                            WHEN CONTAINS(customer_code, ?) THEN 3
                            WHEN CONTAINS(phone, ?) THEN 4
                            ELSE 5
                        END AS rank
                    FROM Customer
                    WHERE 
                        CONTAINS((customer_code, phone), ?)
                        OR LOWER(customer_code) LIKE ?
                        OR REPLACE(REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '(', ''), ')', '') LIKE ?
                    ORDER BY 
                        rank ASC,
                        LEN(customer_code) ASC,
                        customer_name ASC
                """
                q_start = f"{q_lower}%"
                q_contains = f"%{q_phone}%"
                cursor.execute(sql, (
                    q_lower,        # exact match
                    q_start,        # starts with
                    search_term,    # fulltext contains code
                    search_term,    # fulltext contains phone
                    search_term,    # fulltext search
                    q_start,        # like starts with
                    q_contains      # phone contains
                ))
            else:
                # Name search (fuzzy + exact) - English
                sql = """
                    SELECT TOP 15
                        customer_code, 
                        customer_name, 
                        phone, 
                        tax_no,
                        blocked,
                        CASE
                            WHEN LOWER(customer_name) = ? THEN 1
                            WHEN LOWER(customer_name) LIKE ? THEN 2
                            WHEN FREETEXT(customer_name, ?) THEN 3
                            ELSE 4
                        END AS rank
                    FROM Customer
                    WHERE 
                        FREETEXT(customer_name, ?)
                        OR LOWER(customer_name) LIKE ?
                        OR LOWER(customer_code) LIKE ?
                    ORDER BY 
                        rank ASC,
                        LEN(customer_code) ASC,
                        customer_name ASC
                """
                q_start = f"{q_lower}%"
                q_contains = f"%{q_lower}%"
                cursor.execute(sql, (
                    q_lower,        # exact match
                    q_start,        # starts with
                    q_clean,        # freetext check
                    q_clean,        # freetext search
                    q_contains,     # like contains name
                    q_contains      # like contains code
                ))
        else:
            # ❌ ไม่มี Full-Text Index หรือเป็นภาษาไทย → ใช้ LIKE
            # ⭐ ปรับปรุง: ค้นหาทั้งชื่อ, รหัส, เบอร์โทร
            sql = """
                SELECT TOP 15
                    customer_code, 
                    customer_name, 
                    phone, 
                    tax_no,
                    blocked,
                    CASE
                        -- Exact match (highest priority)
                        WHEN LOWER(customer_code) = ? THEN 1
                        WHEN LOWER(customer_name) = ? THEN 1
                        -- Starts with (medium priority)
                        WHEN LOWER(customer_code) LIKE ? THEN 2
                        WHEN LOWER(customer_name) LIKE ? THEN 2
                        -- Contains (lowest priority)
                        WHEN LOWER(customer_name) LIKE ? THEN 3
                        WHEN LOWER(customer_code) LIKE ? THEN 3
                        ELSE 4
                    END AS rank
                FROM Customer
                WHERE 
                    LOWER(customer_code) LIKE ?
                    OR LOWER(customer_name) LIKE ?
                    OR REPLACE(REPLACE(REPLACE(REPLACE(phone, '-', ''), ' ', ''), '(', ''), ')', '') LIKE ?
                ORDER BY 
                    rank ASC,
                    LEN(customer_code) ASC,
                    customer_name ASC
            """
            
            q_start = f"{q_lower}%"
            q_contains = f"%{q_lower}%"
            cursor.execute(sql, (
                q_lower,                    # exact match code
                q_lower,                    # exact match name
                q_start,                    # starts with code
                q_start,                    # starts with name
                q_contains,                 # contains name
                q_contains,                 # contains code
                q_contains,                 # WHERE: contains code
                q_contains,                 # WHERE: contains name
                f"%{q_phone}%"              # WHERE: contains phone
            ))
        
        rows = cursor.fetchall()
        
        result = [
            {
                "id": row.customer_code or "",
                "name": row.customer_name or "",
                "phone": row.phone or "",
                "tax_no": row.tax_no or "",
                "blocked": row.blocked if hasattr(row, 'blocked') else 0,
            }
            for row in rows
        ]
        
        cursor.close()
        conn.close()
        
        logger.info(f"Search '{query}' returned {len(result)} results")
        
        return result
        
    except Exception as e:
        logger.error(f"Error searching customer list from database: {e}", exc_info=True)
        return []


# =====================================================
# GET /customer/list → dropdown (autocomplete)
# =====================================================
@router.get("/list")
@router.post("/list")
def search_customer_list_v2(
    q: str = Query(..., min_length=1),
):
    """
    ค้นหารายชื่อลูกค้าจาก MSSQL Database (สำหรับ autocomplete)
    
    Parameters:
        - q: คำค้นหา (ค้นหาจาก code, name, phone)
    
    Returns:
        List of customers (max 15 results)
    """
    # ใช้ MSSQL Database เท่านั้น
    return search_customer_list_from_db(q)


# =====================================================
# GET /customer/search-list → dropdown (autocomplete) - DEPRECATED
# =====================================================
@router.get("/search-list")
@router.post("/search-list")
def search_customer_list(
    q: str = Query(..., min_length=1),
):
    """
    ค้นหารายชื่อลูกค้าจาก MSSQL Database (สำหรับ autocomplete)
    [DEPRECATED: ใช้ /list แทน]
    
    Parameters:
        - q: คำค้นหา (ค้นหาจาก code, name, phone)
    
    Returns:
        List of customers (max 15 results)
    """

    return search_customer_list_from_db(q)


# =====================================================
# GET /customer/{customer_id} → ดึงข้อมูลลูกค้าตาม ID
# =====================================================
@router.get("/{customer_id}")
async def get_customer_by_id(customer_id: str):
    """
    ดึงข้อมูลลูกค้าตาม customer_id (รหัสลูกค้า)
    
    Parameters:
        - customer_id: รหัสลูกค้า
    
    Returns:
        Customer data with analytics
    """
    return await search_customer_from_db(code=customer_id)


# =====================================================
# GET /customer/all → ดึงรายการลูกค้าทั้งหมดแบบ pagination
# =====================================================
@router.get("/all/customers")
def get_all_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """
    ดึงรายการลูกค้าทั้งหมดแบบ pagination
    
    Parameters:
        - page: หน้าที่ต้องการ (เริ่มจาก 1)
        - limit: จำนวนรายการต่อหน้า (default 50, max 100)
    
    Returns:
        {
            "customers": [...],
            "total": total_count,
            "page": current_page,
            "limit": items_per_page,
            "total_pages": total_pages
        }
    """
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        offset = (page - 1) * limit
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM Customer")
        total = cursor.fetchone().total
        
        # Get paginated data
        data_sql = """
            SELECT 
                customer_code,
                customer_name,
                phone,
                tax_no,
                payment_terms,
                gen_bus
            FROM Customer
            ORDER BY customer_code
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """
        
        cursor.execute(data_sql, [offset, limit])
        rows = cursor.fetchall()
        
        customers = []
        for row in rows:
            customers.append({
                "id": row.customer_code,
                "code": row.customer_code,
                "name": row.customer_name,
                "phone": row.phone,
                "tax_no": row.tax_no,
                "payment_terms": row.payment_terms,
                "gen_bus": row.gen_bus,
            })
        
        cursor.close()
        conn.close()
        
        total_pages = (total + limit - 1) // limit
        
        return {
            "customers": customers,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch customers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch customers: {str(e)}"
        )
