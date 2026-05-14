# items_mssql.py
from fastapi import APIRouter, Query, HTTPException, Depends
from services.sku_enricher import enrich_by_category, load_mapping
from config.db_mssql import get_mssql_conn
from auth_dependency import get_branch_code

router = APIRouter(prefix="/items", tags=["items"])


# ======================================================
# Helper: Convert DB row → API item (🔥 SHAPE เดิม)
# ======================================================
def row_to_item(row, branch_code: str, inventory_service=None) -> dict:
    # Inventory set to 0 (BC API/Database not available)
    inventory = 0
    
    # Log for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"row_to_item: SKU={row.SKU}, branch_code={branch_code}, R1={row.R1}, R2={row.R2}")
    
    # ⭐ ดึง category จากอักษรตัวแรกของ SKU แทน Inventory_Posting_Group
    category = row.SKU[0].upper() if row.SKU and len(row.SKU) > 0 else ""
    
    # ⭐ ดึง Product_Weight จาก database ถ้ามี
    product_weight = getattr(row, 'Product_Weight', 0) or 0
    
    # ⭐ คำนวณ sqft_sheet สำหรับกระจก (category G)
    sqft_sheet = 0  # ⭐ default เป็น 0 สำหรับ non-glass หรือ parse ไม่ได้
    if category == "G":
        # Parse glass SKU to get dimensions
        # ขนาดอยู่ใน 6 หลักท้ายของ SKU
        # Width: 3 หลักแรกของ 6 หลักท้าย
        # Length: 3 หลักหลังของ 6 หลักท้าย
        # ตัวอย่าง: G01010010102014040 → width=014 (14"), length=040 (40")
        try:
            sku = row.SKU
            if len(sku) >= 6:
                # ดึง 6 หลักท้าย
                last_6 = sku[-6:]
                width = int(last_6[0:3])  # 3 หลักแรก = width (นิ้ว)
                length = int(last_6[3:6])  # 3 หลักหลัง = length (นิ้ว)
                sqft_sheet = (width * length) / 144.0  # แปลงเป็นตารางฟุต
                logger.info(f"Glass SKU {sku}: last_6={last_6}, width={width}, length={length}, sqft_sheet={sqft_sheet}")
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to parse glass SKU {row.SKU}: {e}")
            sqft_sheet = 0
    
    return {
        "sku": row.SKU,
        "sku2": row.No_2 or "",
        "name": row.Description or "",
        "inventory": inventory,
        "unit": row.Base_Unit_of_Measure or "",
        "category": category,
        "isVariant": bool(row.Variant_Mandatory == 2),  # 2 = มี variant, 1 = ไม่มี variant
        "prices": {
            "R1": row.R1 or 0,
            "R2": row.R2 or 0,
            "W1": row.W1 or 0,
            "W2": row.W2 or 0,
        },
        "pkg_size": row.PackageSize or 1,
        "product_weight": product_weight,
        "sqft_sheet": sqft_sheet,
        "product_group": row.Product_Group or "",
        "product_sub_group": row.Product_Sub_Group or "",
        "alternate_names": row.AlternateName or "",
    }



@router.get("/categories/list") #ดึงหมวดหมู่สินค้า
def get_item_categories():
    conn = get_mssql_conn()
    cursor = conn.cursor()

    # ⭐ แบ่งประเภทตามอักษรตัวแรกของ SKU แทน Inventory_Posting_Group
    cursor.execute("""
        SELECT
            LEFT(SKU, 1) AS name,
            COUNT(*) AS count
        FROM Item_Master
        WHERE LEFT(SKU, 1) IN ('G', 'A', 'C', 'Y', 'S', 'E')
          AND Blocked = 0
        GROUP BY LEFT(SKU, 1)
        ORDER BY LEFT(SKU, 1)
    """)

    rows = cursor.fetchall()
    conn.close()

    return [{"name": r[0], "count": r[1]} for r in rows]



@router.get("/categories/{category_name}/list") #ดึงสินค้าตามหมวดหมู่
def get_items_list_light(
    category_name: str,
    branch_code: str = Depends(get_branch_code),
    limit: int = 10,
    offset: int = 0,
    # filter parameters
    brand: str = None,
    group: str = None,
    subGroup: str = None,
    color: str = None,
    thickness: str = None,
    character: str = None,
    search: str = None,  # search parameter
):
    conn = get_mssql_conn()
    cursor = conn.cursor()

    # สร้าง WHERE clause สำหรับ filter - ใช้อักษรตัวแรกของ SKU แทน Inventory_Posting_Group
    where_clauses = ["LEFT(im.SKU, 1) = ?", "im.Blocked = 0"]
    params = [category_name.upper()]  # category first

    # ⭐ Filter by SKU pattern (Aluminium: ABBGGSSSCCTT)
    if category_name.upper() == "A":
        if brand:
            where_clauses.append("SUBSTRING(im.SKU, 2, 2) = ?")
            params.append(brand.zfill(2))
        if group:
            where_clauses.append("SUBSTRING(im.SKU, 4, 2) = ?")
            params.append(group.zfill(2))
        if subGroup:
            where_clauses.append("SUBSTRING(im.SKU, 6, 3) = ?")
            params.append(subGroup.zfill(3))
        if color:
            where_clauses.append("SUBSTRING(im.SKU, 9, 2) = ?")
            params.append(color.zfill(2))
        if thickness:
            where_clauses.append("SUBSTRING(im.SKU, 11, 2) = ?")
            params.append(thickness.zfill(2))

    # ⭐ Filter by SKU pattern (C-Line: CBBGGSSSCCTT)
    elif category_name.upper() == "C":
        if brand:
            where_clauses.append("SUBSTRING(im.SKU, 2, 2) = ?")
            params.append(brand.zfill(2))
        if group:
            where_clauses.append("SUBSTRING(im.SKU, 4, 2) = ?")
            params.append(group.zfill(2))
        if subGroup:
            where_clauses.append("SUBSTRING(im.SKU, 6, 3) = ?")
            params.append(subGroup.zfill(3))
        if color:
            where_clauses.append("SUBSTRING(im.SKU, 9, 2) = ?")
            params.append(color.zfill(2))
        if thickness:
            where_clauses.append("SUBSTRING(im.SKU, 11, 2) = ?")
            params.append(thickness.zfill(2))

    # ⭐ Filter by SKU pattern (Accessories: EBBBGGSSCCX)
    elif category_name.upper() == "E":
        if brand:
            where_clauses.append("SUBSTRING(im.SKU, 2, 3) = ?")
            params.append(brand.zfill(3))
        if group:
            where_clauses.append("SUBSTRING(im.SKU, 5, 2) = ?")
            params.append(group.zfill(2))
        if subGroup:
            where_clauses.append("SUBSTRING(im.SKU, 7, 2) = ?")
            params.append(subGroup.zfill(2))
        if color:
            where_clauses.append("SUBSTRING(im.SKU, 9, 2) = ?")
            params.append(color.zfill(2))
        if character:
            where_clauses.append("SUBSTRING(im.SKU, 11, 1) = ?")
            params.append(character)

    # Filter by SKU pattern (Sealant: SBBGGGCC)
    elif category_name.upper() == "S":
        if brand:
            where_clauses.append("SUBSTRING(im.SKU, 2, 2) = ?")
            params.append(brand.zfill(2))
        if group:
            where_clauses.append("SUBSTRING(im.SKU, 4, 2) = ?")
            params.append(group.zfill(2))
        if subGroup:
            where_clauses.append("SUBSTRING(im.SKU, 6, 3) = ?")
            params.append(subGroup.zfill(3))
        if color:
            where_clauses.append("SUBSTRING(im.SKU, 9, 2) = ?")
            params.append(color.zfill(2))

    # Filter by SKU pattern (Gypsum: YBBGGSCCCTT...)
    elif category_name.upper() == "Y":
        if brand:
            where_clauses.append("SUBSTRING(im.SKU, 2, 2) = ?")
            params.append(brand.zfill(2))
        if group:
            where_clauses.append("SUBSTRING(im.SKU, 4, 2) = ?")
            params.append(group.zfill(2))
        if subGroup:
            where_clauses.append("SUBSTRING(im.SKU, 6, 2) = ?")
            params.append(subGroup.zfill(2))
        if color:
            where_clauses.append("SUBSTRING(im.SKU, 8, 3) = ?")
            params.append(color.zfill(3))
        if thickness:
            where_clauses.append("SUBSTRING(im.SKU, 11, 2) = ?")
            params.append(thickness.zfill(2))

    # ⭐ เพิ่ม search filter (ค้นหาใน SKU, SKU2, Description, AlternateName)
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        where_clauses.append("(im.SKU LIKE ? OR im.No_2 LIKE ? OR im.Description LIKE ? OR ip.AlternateName LIKE ?)")
        params.extend([search_term, search_term, search_term, search_term])

    where_sql = " AND ".join(where_clauses)

    # ⭐ นับจำนวนทั้งหมดตาม filter
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM Item_Master im
        LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
        WHERE {where_sql} AND im.Blocked = 0
    """
    cursor.execute(count_sql, branch_code, *params)
    total = cursor.fetchone()[0]

    # ⭐ ดึงข้อมูลตาม limit/offset + filter
    sql = f"""
        SELECT
            im.SKU,
            im.No_2,
            im.Description,
            im.Base_Unit_of_Measure,
            im.Product_Group,
            im.Product_Sub_Group,
            ip.AlternateName
        FROM Item_Master im
        LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
        WHERE {where_sql} AND im.Blocked = 0
        ORDER BY im.SKU
        OFFSET ? ROWS
        FETCH NEXT ? ROWS ONLY
    """

    cursor.execute(sql, branch_code, *params, offset, limit)
    rows = cursor.fetchall()
    conn.close()

    return {
        "items": [
            {
                "sku": r[0],
                "SKU": r[0],  # ⭐ เพิ่ม uppercase version สำหรับ compatibility
                "sku2": r[1] or "",
                "name": r[2] or "",
                "inventory": 0,  # Not fetched in light list for performance
                "unit": r[3] or "",
                "product_group": r[4] or "",
                "product_sub_group": r[5] or "",
                "alternate_names": r[6] or "",
            }
            for r in rows
        ],
        "limit": limit,
        "offset": offset,
        "count": len(rows),
        "total": total,
    }


@router.get("/list") #ดึงสินค้าแบบ pagination
def get_items_paginated(
    branch_code: str = Depends(get_branch_code),
    limit: int = 50,
    offset: int = 0,
    search: str = None,
    productType: str = None,
    brand: str = None,
    category: str = None,
    subCategory: str = None,
    color: str = None,
    thickness: str = None,
    size: str = None,
):
    conn = get_mssql_conn()
    cursor = conn.cursor()

    # ⭐ สร้าง WHERE clause
    where_clauses = []
    params = []

    # ⭐ Filter by product type (first letter of SKU)
    if productType and productType.strip():
        where_clauses.append("LEFT(im.SKU, 1) = ?")
        params.append(productType.strip().upper())

    # ⭐ Search filter (SKU, No_2, Description, AlternateName)
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        where_clauses.append("(im.SKU LIKE ? OR im.No_2 LIKE ? OR im.Description LIKE ? OR ip.AlternateName LIKE ?)")
        params.extend([search_term, search_term, search_term, search_term])

    # ⭐ Generic filters (ใช้ LIKE เพื่อความยืดหยุ่น)
    if brand and brand.strip():
        where_clauses.append("im.Description LIKE ?")
        params.append(f"%{brand.strip()}%")
    
    if category and category.strip():
        where_clauses.append("im.Product_Group LIKE ?")
        params.append(f"%{category.strip()}%")
    
    if subCategory and subCategory.strip():
        where_clauses.append("im.Product_Sub_Group LIKE ?")
        params.append(f"%{subCategory.strip()}%")
    
    if color and color.strip():
        where_clauses.append("im.Description LIKE ?")
        params.append(f"%{color.strip()}%")
    
    if thickness and thickness.strip():
        where_clauses.append("im.Description LIKE ?")
        params.append(f"%{thickness.strip()}%")
    
    if size and size.strip():
        where_clauses.append("im.Description LIKE ?")
        params.append(f"%{size.strip()}%")

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # ⭐ นับจำนวนทั้งหมด
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM Item_Master im
        LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
        WHERE {where_sql} AND im.Blocked = 0
    """
    cursor.execute(count_sql, branch_code, *params)
    total = cursor.fetchone()[0]

    # ⭐ ดึงข้อมูลตาม limit/offset
    sql = f"""
        SELECT
            im.SKU,
            im.No_2,
            im.Description,
            im.Base_Unit_of_Measure,
            im.Product_Group,
            im.Product_Sub_Group,
            ip.AlternateName,
            LEFT(im.SKU, 1) AS category
        FROM Item_Master im
        LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
        WHERE {where_sql} AND im.Blocked = 0
        ORDER BY im.SKU
        OFFSET ? ROWS
        FETCH NEXT ? ROWS ONLY
    """

    cursor.execute(sql, branch_code, *params, offset, limit)
    rows = cursor.fetchall()
    conn.close()

    return {
        "items": [
            {
                "sku": r[0],
                "sku2": r[1] or "",
                "name": r[2] or "",
                "unit": r[3] or "",
                "unit2": r[3] or "",  # ⭐ ใช้ unit เดียวกัน
                "category": r[7] or "",
                "product_group": r[4] or "",
                "product_sub_group": r[5] or "",
                "alternate_names": r[6] or "",
            }
            for r in rows
        ],
        "limit": limit,
        "offset": offset,
        "count": len(rows),
        "total": total,
    }



@router.get("/search") #FullTextSearch
def full_text_search_items(
    q: str = Query(..., min_length=1),
    branch_code: str = Depends(get_branch_code)
):
    conn = get_mssql_conn()
    cursor = conn.cursor()

    q_clean = q.strip()
    
    # ⭐ ตรวจสอบว่ามี Full-Text Index หรือไม่
    cursor.execute("""
        SELECT COUNT(*) as has_fulltext
        FROM sys.fulltext_indexes 
        WHERE object_id = OBJECT_ID('Item_Master')
    """)
    has_fulltext = cursor.fetchone()[0] > 0

    if has_fulltext:
        # ✅ ใช้ Full-Text Search (เร็วกว่า LIKE มาก)
        if q_clean.replace('-', '').replace('.', '').isalnum():
            # SKU search (prefix)
            search_term = f'"{q_clean}*"'
            sql = """
                SELECT TOP 50
                    im.SKU, im.No_2, im.Description, im.Base_Unit_of_Measure,
                    im.Inventory_Posting_Group, im.Variant_Mandatory,
                    ip.R1, ip.R2, ip.W1, ip.W2, ip.PackageSize,
                    im.Product_Group, im.Product_Sub_Group, ip.AlternateName,
                    im.Product_Weight
                FROM Item_Master im
                LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
                WHERE (CONTAINS((im.SKU, im.No_2, im.Description), ?)
                   OR CONTAINS((ip.AlternateName), ?))
                   AND im.Blocked = 0
                ORDER BY 
                    CASE 
                        WHEN im.SKU LIKE ? THEN 1
                        WHEN im.No_2 LIKE ? THEN 2
                        WHEN im.Description LIKE ? THEN 3
                        ELSE 4
                    END,
                    im.SKU
            """
            q_like = f"{q_clean}%"
            cursor.execute(sql, branch_code, search_term, search_term, q_like, q_like, q_like)
        else:
            # Text search (fuzzy)
            sql = """
                SELECT TOP 50
                    im.SKU, im.No_2, im.Description, im.Base_Unit_of_Measure,
                    im.Inventory_Posting_Group, im.Variant_Mandatory,
                    ip.R1, ip.R2, ip.W1, ip.W2, ip.PackageSize,
                    im.Product_Group, im.Product_Sub_Group, ip.AlternateName,
                    im.Product_Weight
                FROM Item_Master im
                LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
                WHERE (FREETEXT((im.Description), ?)
                   OR FREETEXT((ip.AlternateName), ?)
                   OR CONTAINS((im.SKU, im.No_2), ?))
                   AND im.Blocked = 0
                ORDER BY im.SKU
            """
            search_term = f'"{q_clean}*"'
            cursor.execute(sql, branch_code, q_clean, q_clean, search_term)
    else:
        # ❌ ไม่มี Full-Text Index → ใช้ LIKE (ช้ากว่า)
        q_like = f"%{q_clean}%"
        sql = """
            SELECT TOP 50
                im.SKU, im.No_2, im.Description, im.Base_Unit_of_Measure,
                im.Inventory_Posting_Group, im.Variant_Mandatory,
                ip.R1, ip.R2, ip.W1, ip.W2, ip.PackageSize,
                im.Product_Group, im.Product_Sub_Group, ip.AlternateName,
                im.Product_Weight
            FROM Item_Master im
            LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
            WHERE (im.SKU LIKE ?
                OR im.No_2 LIKE ?
                OR im.Description LIKE ?
                OR ip.AlternateName LIKE ?)
                AND im.Blocked = 0
            ORDER BY 
                CASE 
                    WHEN im.SKU LIKE ? THEN 1
                    WHEN im.No_2 LIKE ? THEN 2
                    WHEN im.Description LIKE ? THEN 3
                    ELSE 4
                END,
                im.SKU
        """
        q_start = f"{q_clean}%"
        cursor.execute(sql, branch_code, q_like, q_like, q_like, q_like, q_start, q_start, q_start)

    rows = cursor.fetchall()
    conn.close()

    # Convert rows to dict-like objects
    class Row:
        def __init__(self, data):
            self.SKU = data[0]
            self.No_2 = data[1]
            self.Description = data[2]
            self.Base_Unit_of_Measure = data[3]
            self.Inventory_Posting_Group = data[4]
            self.Variant_Mandatory = data[5]
            self.R1 = data[6]
            self.R2 = data[7]
            self.W1 = data[8]
            self.W2 = data[9]
            self.PackageSize = data[10]
            self.Product_Group = data[11]
            self.Product_Sub_Group = data[12]
            self.AlternateName = data[13]
            self.Product_Weight = data[14] if len(data) > 14 else 0

    return [row_to_item(Row(r), branch_code, None) for r in rows]



@router.get("/{sku}") #ดึงข้อมูลสินค้าจาก Item_Master
def get_item_detail(sku: str, branch_code: str = Depends(get_branch_code)):
    conn = get_mssql_conn()
    cursor = conn.cursor()

    # ⭐ ลองหาจาก SKU ก่อน
    sql = """
        SELECT
            im.SKU, im.No_2, im.Description, im.Base_Unit_of_Measure,
            im.Inventory_Posting_Group, im.Variant_Mandatory,
            ip.R1, ip.R2, ip.W1, ip.W2, ip.PackageSize,
            im.Product_Group, im.Product_Sub_Group, ip.AlternateName,
            im.Product_Weight
        FROM Item_Master im
        LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
        WHERE im.SKU = ? AND im.Blocked = 0
    """

    cursor.execute(sql, branch_code, sku)
    row = cursor.fetchone()
    
    # ⭐ ถ้าไม่เจอ ลองหาจาก No_2
    if not row:
        sql = """
            SELECT
                im.SKU, im.No_2, im.Description, im.Base_Unit_of_Measure,
                im.Inventory_Posting_Group, im.Variant_Mandatory,
                ip.R1, ip.R2, ip.W1, ip.W2, ip.PackageSize,
                im.Product_Group, im.Product_Sub_Group, ip.AlternateName,
                im.Product_Weight
            FROM Item_Master im
            LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
            WHERE im.No_2 = ? AND im.Blocked = 0
        """
        cursor.execute(sql, branch_code, sku)
        row = cursor.fetchone()

    conn.close()

    if not row:
        raise HTTPException(404, "Item not found")

    # Convert row to dict-like object
    class Row:
        def __init__(self, data):
            self.SKU = data[0]
            self.No_2 = data[1]
            self.Description = data[2]
            self.Base_Unit_of_Measure = data[3]
            self.Inventory_Posting_Group = data[4]
            self.Variant_Mandatory = data[5]
            self.R1 = data[6]
            self.R2 = data[7]
            self.W1 = data[8]
            self.W2 = data[9]
            self.PackageSize = data[10]
            self.Product_Group = data[11]
            self.Product_Sub_Group = data[12]
            self.AlternateName = data[13]
            self.Product_Weight = data[14] if len(data) > 14 else 0

    item = row_to_item(Row(row), branch_code, None)

    # ⭐ enrich เฉพาะตอนนี้
    extra = enrich_by_category(item["category"], item["sku"]) or {}
    item.update(extra)

    # ⭐ ดึงข้อมูล stock จาก Item_Ledger API (เฉพาะสาขาของพนักงาน)
    try:
        from api.bc_item_client import BCAPIClient
        import logging
        logger = logging.getLogger(__name__)
        
        client = BCAPIClient()
        ledger_entries = client.fetch_inventory(item["sku"], branch_code)
        
        # Debug: ดูว่า API ส่ง field ไหนมา
        if ledger_entries:
            logger.info(f"First ledger entry: {ledger_entries[0]}")
        
        # Sum quantity จากทุก entries ของสาขานี้
        branch_qty = 0
        for entry in ledger_entries:
            qty = entry.get("Quantity", 0)
            branch_qty += qty
        
        # เพิ่มข้อมูล stock ลงใน item (format เดิม แต่แสดงเฉพาะสาขาของพนักงาน)
        item["stock"] = {
            "branches": [
                {
                    "Location_Code": branch_code,
                    "quantity": branch_qty
                }
            ],
            "total_quantity": branch_qty
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching stock for SKU {item['sku']}: {str(e)}")
        item["stock"] = {
            "branches": [],
            "total_quantity": 0,
            "error": str(e)
        }

    return item



@router.get("/related/{sku}") #ดึงสินค้าที่Group เดียวกัน
def get_related_items(
    sku: str,
    category: str = None,  # ⭐ เพิ่ม category parameter
    limit: int = 50,
    brand: str = None,
    group: str = None,
    subGroup: str = None,
    color: str = None,
    thickness: str = None,
    character: str = None,
    branch_code: str = Depends(get_branch_code)
):
    conn = get_mssql_conn()
    cursor = conn.cursor()

    # หา product_group ของ SKU นี้ก่อน (เร็ว)
    sql = """
        SELECT Product_Group
        FROM Item_Master
        WHERE (SKU = ? OR No_2 = ?) AND Blocked = 0
    """
    cursor.execute(sql, sku, sku)
    row = cursor.fetchone()

    if not row or not row[0]:
        conn.close()
        return {"items": [], "total": 0}

    product_group = row[0]

    # ดึงสินค้าใน Product Group เดียวกัน พร้อม filter
    sql = f"""
        SELECT TOP {limit}
            im.SKU,
            im.No_2,
            im.Description,
            im.Base_Unit_of_Measure,
            im.Product_Group,
            im.Product_Sub_Group
        FROM Item_Master im
        WHERE im.Product_Group = ?
          AND im.SKU != ?
          AND (im.No_2 IS NULL OR im.No_2 != ?)
          AND im.Blocked = 0
    """
    
    params = [product_group, sku, sku]
    
    # ⭐ เพิ่ม filter conditions ตามหมวดหมู่ (ใช้ position ที่ถูก)
    # SKU Format:
    # A: ABBGGSSSCCDD (Aluminium)
    # C: CBBGGSSSCCDD (C-Line)
    # E: EBBGGSSCCX (Accessories)
    # S: SBBGGSSSCC (Sealant)
    # Y: YBBGGSSCCCDD (Gypsum)
    
    if category == "A":  # Aluminium: ABBGGSSSCCDD
        if brand:
            sql += " AND SUBSTRING(im.SKU, 2, 2) = ?"
            params.append(brand)
        if group:
            sql += " AND SUBSTRING(im.SKU, 4, 2) = ?"
            params.append(group)
        if subGroup:
            sql += " AND SUBSTRING(im.SKU, 6, 3) = ?"
            params.append(subGroup)
        if color:
            sql += " AND SUBSTRING(im.SKU, 9, 2) = ?"
            params.append(color)
        if thickness:
            sql += " AND SUBSTRING(im.SKU, 11, 2) = ?"
            params.append(thickness)
    
    elif category == "C":  # C-Line: CBBGGSSSCCDD
        if brand:
            sql += " AND SUBSTRING(im.SKU, 2, 2) = ?"
            params.append(brand)
        if group:
            sql += " AND SUBSTRING(im.SKU, 4, 2) = ?"
            params.append(group)
        if subGroup:
            sql += " AND SUBSTRING(im.SKU, 6, 3) = ?"
            params.append(subGroup)
        if color:
            sql += " AND SUBSTRING(im.SKU, 9, 2) = ?"
            params.append(color)
        if thickness:
            sql += " AND SUBSTRING(im.SKU, 11, 2) = ?"
            params.append(thickness)
    
    elif category == "E":  # Accessories: EBBGGSSCCX
        if brand:
            sql += " AND SUBSTRING(im.SKU, 2, 2) = ?"
            params.append(brand)
        if group:
            sql += " AND SUBSTRING(im.SKU, 4, 2) = ?"
            params.append(group)
        if subGroup:
            sql += " AND SUBSTRING(im.SKU, 6, 2) = ?"
            params.append(subGroup)
        if color:
            sql += " AND SUBSTRING(im.SKU, 8, 2) = ?"
            params.append(color)
        if character:
            sql += " AND SUBSTRING(im.SKU, 10, 1) = ?"
            params.append(character)
    
    elif category == "S":  # Sealant: SBBGGSSSCC
        if brand:
            sql += " AND SUBSTRING(im.SKU, 2, 2) = ?"
            params.append(brand)
        if group:
            sql += " AND SUBSTRING(im.SKU, 4, 2) = ?"
            params.append(group)
        if subGroup:
            sql += " AND SUBSTRING(im.SKU, 6, 3) = ?"
            params.append(subGroup)
        if color:
            sql += " AND SUBSTRING(im.SKU, 9, 2) = ?"
            params.append(color)
    
    elif category == "Y":  # Gypsum: YBBGGSSCCCDD
        if brand:
            sql += " AND SUBSTRING(im.SKU, 2, 2) = ?"
            params.append(brand)
        if group:
            sql += " AND SUBSTRING(im.SKU, 4, 2) = ?"
            params.append(group)
        if subGroup:
            sql += " AND SUBSTRING(im.SKU, 6, 2) = ?"
            params.append(subGroup)
        if color:
            sql += " AND SUBSTRING(im.SKU, 8, 3) = ?"
            params.append(color)
        if thickness:
            sql += " AND SUBSTRING(im.SKU, 11, 2) = ?"
            params.append(thickness)
    
    sql += " ORDER BY im.SKU"
    
    cursor.execute(sql, *params)
    rows = cursor.fetchall()
    conn.close()

    return {
        "items": [
            {
                "sku": r[0],
                "SKU": r[0],
                "sku2": r[1] or "",
                "name": r[2] or "",
                "inventory": 0,  # Not fetched for performance
                "unit": r[3] or "",
                "product_group": r[4] or "",
                "product_sub_group": r[5] or "",
            }
            for r in rows
        ],
        "total": len(rows),
        "product_group": product_group,
    }



@router.get("/categories/{category_name}/filter-options") #ดึง filter options ที่ปรับตาม filter ที่เลือกแล้ว (cascading)
def get_filter_options(
    category_name: str,
    branch_code: str = Depends(get_branch_code),
    brand: str = None,
    group: str = None,
    subGroup: str = None,
    color: str = None,
    thickness: str = None,
    character: str = None,
):
    """ดึง filter options ที่ถูกกรองแล้วตามเงื่อนไขปัจจุบัน
    
    รองรับ multiple values (comma-separated) เช่น brand=01,02
    """
    
    # แปลง comma-separated values เป็น list
    brand_list = brand.split(',') if brand else []
    group_list = group.split(',') if group else []
    subGroup_list = subGroup.split(',') if subGroup else []
    color_list = color.split(',') if color else []
    thickness_list = thickness.split(',') if thickness else []
    character_list = character.split(',') if character else []
    
    conn = get_mssql_conn()
    cursor = conn.cursor()

    # ⭐ สร้าง WHERE clause สำหรับ filter (เหมือนกับ list endpoint) - ใช้อักษรตัวแรกของ SKU
    where_clauses = ["LEFT(im.SKU, 1) = ?", "im.Blocked = 0"]
    params = [category_name.upper()]

    # Helper function สำหรับเพิ่ม filter (รองรับ multiple values)
    def add_filter(field_slice, value_list, pad_len):
        if value_list:
            placeholders = ','.join(['?'] * len(value_list))
            where_clauses.append(f"SUBSTRING(im.SKU, {field_slice[0]}, {field_slice[1]}) IN ({placeholders})")
            params.extend([v.zfill(pad_len) for v in value_list])

    # ⭐ Filter by SKU pattern ตาม category
    if category_name.upper() == "A":
        add_filter((2, 2), brand_list, 2)
        add_filter((4, 2), group_list, 2)
        add_filter((6, 3), subGroup_list, 3)
        add_filter((9, 2), color_list, 2)
        add_filter((11, 2), thickness_list, 2)
        
        # Define extraction for each field
        field_extracts = {
            "brand": "SUBSTRING(im.SKU, 2, 2)",
            "group": "SUBSTRING(im.SKU, 4, 2)",
            "subGroup": "SUBSTRING(im.SKU, 6, 3)",
            "color": "SUBSTRING(im.SKU, 9, 2)",
            "thickness": "SUBSTRING(im.SKU, 11, 2)",
        }

    elif category_name.upper() == "C":
        add_filter((2, 2), brand_list, 2)
        add_filter((4, 2), group_list, 2)
        add_filter((6, 3), subGroup_list, 3)
        add_filter((9, 2), color_list, 2)
        add_filter((11, 2), thickness_list, 2)
        
        field_extracts = {
            "brand": "SUBSTRING(im.SKU, 2, 2)",
            "group": "SUBSTRING(im.SKU, 4, 2)",
            "subGroup": "SUBSTRING(im.SKU, 6, 3)",
            "color": "SUBSTRING(im.SKU, 9, 2)",
            "thickness": "SUBSTRING(im.SKU, 11, 2)",
        }

    elif category_name.upper() == "E":
        add_filter((2, 3), brand_list, 3)
        add_filter((5, 2), group_list, 2)
        add_filter((7, 2), subGroup_list, 2)
        add_filter((9, 2), color_list, 2)
        if character_list:
            placeholders = ','.join(['?'] * len(character_list))
            where_clauses.append(f"SUBSTRING(im.SKU, 11, 1) IN ({placeholders})")
            params.extend(character_list)
        
        field_extracts = {
            "brand": "SUBSTRING(im.SKU, 2, 3)",
            "group": "SUBSTRING(im.SKU, 5, 2)",
            "subGroup": "SUBSTRING(im.SKU, 7, 2)",
            "color": "SUBSTRING(im.SKU, 9, 2)",
            "character": "SUBSTRING(im.SKU, 11, 1)",
        }

    elif category_name.upper() == "S":
        add_filter((2, 2), brand_list, 2)
        add_filter((4, 2), group_list, 2)
        add_filter((6, 3), subGroup_list, 3)
        add_filter((9, 2), color_list, 2)
        
        field_extracts = {
            "brand": "SUBSTRING(im.SKU, 2, 2)",
            "group": "SUBSTRING(im.SKU, 4, 2)",
            "subGroup": "SUBSTRING(im.SKU, 6, 3)",
            "color": "SUBSTRING(im.SKU, 9, 2)",
        }

    elif category_name.upper() == "Y":
        add_filter((2, 2), brand_list, 2)
        add_filter((4, 2), group_list, 2)
        add_filter((6, 2), subGroup_list, 2)
        add_filter((8, 3), color_list, 3)
        add_filter((11, 2), thickness_list, 2)
        
        field_extracts = {
            "brand": "SUBSTRING(im.SKU, 2, 2)",
            "group": "SUBSTRING(im.SKU, 4, 2)",
            "subGroup": "SUBSTRING(im.SKU, 6, 2)",
            "color": "SUBSTRING(im.SKU, 8, 3)",
            "thickness": "SUBSTRING(im.SKU, 11, 2)",
        }
    else:
        return {}

    where_sql = " AND ".join(where_clauses)

    # ⭐ โหลด mapping tables
    mapping_tables = {
        "A": {
            "brand": "Aluminium_Brand",
            "group": "Aluminium_Group",
            "subGroup": "Aluminium_SubGroup",
            "color": "Aluminium_Color",
            "thickness": "Aluminium_Thickness",
        },
        "C": {
            "brand": "CLine_Brand",
            "group": "CLine_Group",
            "subGroup": "CLine_SubGroup",
            "color": "CLine_Color",
            "thickness": "CLine_Thickness",
        },
        "E": {
            "brand": "Accessories_Brand",
            "group": "Accessories_Group",
            "subGroup": "Accessories_SubGroup",
            "color": "Accessories_Color",
            "character": "Character",
        },
        "S": {
            "brand": "Sealant_Brand",
            "group": "Sealant_Group",
            "subGroup": "Sealant_SubGroup",
            "color": "Sealant_Color",
        },
        "Y": {
            "brand": "Gypsum_Brand",
            "group": "Gypsum_Group",
            "subGroup": "Gypsum_SubGroup",
            "color": "Gypsum_Color",
            "thickness": "Gypsum_Thickness",
        },
    }

    mappings = {}
    if category_name.upper() in mapping_tables:
        for field, table in mapping_tables[category_name.upper()].items():
            try:
                mappings[field] = load_mapping(table)
            except:
                mappings[field] = {}

    # ⭐ ดึง distinct values สำหรับแต่ละ field
    result = {}
    for field_name, extract_sql in field_extracts.items():
        sql = f"""
            SELECT DISTINCT {extract_sql} AS value
            FROM Item_Master im
            WHERE {where_sql}
            ORDER BY value
        """
        cursor.execute(sql, *params)
        rows = cursor.fetchall()
        
        # ⭐ แปลงเป็น {code, name} พร้อม code ขึ้นหน้า
        codes = [r[0] for r in rows if r[0]]
        mapping = mappings.get(field_name, {})
        result[field_name] = [
            {
                "code": code, 
                "name": f"{code} - {mapping.get(code, code)}" if mapping.get(code) else code
            }
            for code in codes
        ]

    conn.close()
    return result



@router.get("/{sku}/stock") #ดึงข้อมูล stock จาก Item_Ledger API แยกตามสาขา
def get_item_stock(sku: str, branch_code: str = Depends(get_branch_code)):
    """
    ดึงข้อมูล stock สำหรับ item เฉพาะสาขาของพนักงาน
    โดยดึงจาก API แล้วบวก Quantity จากทุก records
    
    Response:
    {
        "sku": "A01010101010101",
        "Location Code": "BKK",
        "quantity": 100
    }
    """
    try:
        from api.bc_item_client import BCAPIClient
        
        # สร้าง client
        client = BCAPIClient()
        
        # ดึงข้อมูล inventory ledger entries สำหรับ item และ branch นี้
        ledger_entries = client.fetch_inventory(sku, branch_code)
        
        # บวก Quantity จากทุก records
        total_quantity = 0
        for entry in ledger_entries:
            qty = entry.get("Quantity", 0)
            total_quantity += qty
        
        return {
            "sku": sku,
            "Location_Code": branch_code,
            "quantity": float(total_quantity)
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching stock for SKU {sku} at branch {branch_code}: {str(e)}")
        
        # Return default response ถ้า API error
        return {
            "sku": sku,
            "Location_Code": branch_code,
            "quantity": 0,
            "error": str(e)
        }


# ==========================================================
# GLASS ENDPOINTS (ย้ายมาจาก glass_router.py)
# ==========================================================

from pydantic import BaseModel
from typing import Optional
import time

# ⚡ Cache สำหรับ glass list (10 นาที) - ยังไม่ใช้
# _glass_cache = {
#     "data": None,
#     "timestamp": 0,
#     "ttl": 600,  # 10 minutes
# }


def parse_glass_sku(sku: str):
    """
    Parse glass SKU with validation.
    Expected format: GBBTTSSSCCTTWWWHHH (18 characters)
    G = Glass category
    BB = Brand (2 digits)
    TT = Type (2 digits)
    SSS = SubGroup (3 digits)
    CC = Color (2 digits)
    TT = Thickness (2 digits)
    WWW = Width (3 digits, can be 000 for template SKU)
    HHH = Height (3 digits, can be 000 for template SKU)
    """
    # Validate SKU length
    if not sku or len(sku) != 18:
        return None
    
    # Skip non-glass SKU
    if not sku.startswith('G'):
        return None
    
    try:
        width_str = sku[12:15]
        height_str = sku[15:18]
        
        # Convert to int (allow 0 for template SKUs)
        width = int(width_str) if width_str.strip() else 0
        height = int(height_str) if height_str.strip() else 0
        
        return {
            "brand": sku[1:3],
            "type": sku[3:5],
            "subGroup": sku[5:8],
            "color": sku[8:10],
            "thickness": sku[10:12],
            "width": width,
            "height": height,
        }
    except (ValueError, IndexError) as e:
        # Return None for invalid SKU format
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"⚠️ Failed to parse SKU {sku}: {e}")
        return None


@router.get("/glass/list")
def get_glass_list(
    branch_code: str = Depends(get_branch_code),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    brand: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    subGroup: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    thickness: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    isVariant: Optional[bool] = Query(None),
):
    """⚡ ดึงรายการกระจก (รองรับ Full-Text Search + กรองตาม branch_code)"""
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Glass search request: branch={branch_code}, search='{search}', brand={brand}, type={type}, subGroup={subGroup}, color={color}, thickness={thickness}, isVariant={isVariant}")
    
    # ⚡ Query จาก database พร้อมกรองตาม branch_code
    conn = get_mssql_conn()
    cur = conn.cursor()
    
    # สร้าง WHERE clause สำหรับ filter
    where_clauses = ["im.SKU LIKE 'G%'", "im.Blocked = 0"]
    params = []
    
    if brand:
        where_clauses.append("SUBSTRING(im.SKU, 2, 2) = ?")
        params.append(brand)
    if type:
        where_clauses.append("SUBSTRING(im.SKU, 4, 2) = ?")
        params.append(type)
    if subGroup:
        where_clauses.append("SUBSTRING(im.SKU, 6, 3) = ?")
        params.append(subGroup)
    if color:
        where_clauses.append("SUBSTRING(im.SKU, 9, 2) = ?")
        params.append(color)
    if thickness:
        where_clauses.append("SUBSTRING(im.SKU, 11, 2) = ?")
        params.append(thickness)
    if isVariant is not None:
        where_clauses.append("im.Variant_Mandatory = ?")
        params.append(2 if isVariant else 1)
    
    # เพิ่ม search condition
    if search and search.strip():
        search_term = search.strip()
        
        # ตรวจสอบว่ามี Full-Text Index หรือไม่
        cur.execute("""
            SELECT COUNT(*) as has_fulltext
            FROM sys.fulltext_indexes 
            WHERE object_id = OBJECT_ID('Item_Master')
        """)
        has_fulltext = cur.fetchone()[0] > 0
        
        if has_fulltext:
            # ใช้ Full-Text Search
            search_pattern = f'"{search_term}*"'
            where_clauses.append("(CONTAINS((im.SKU, im.No_2, im.Description), ?) OR im.SKU LIKE ? OR im.No_2 LIKE ?)")
            params.extend([search_pattern, f"%{search_term}%", f"%{search_term}%"])
        else:
            # ใช้ LIKE
            where_clauses.append("(im.SKU LIKE ? OR im.No_2 LIKE ? OR im.Description LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
    
    where_sql = " AND ".join(where_clauses)
    
    logger.info(f"📊 SQL WHERE: {where_sql}")
    logger.info(f"📊 SQL PARAMS: {params}")
    
    # นับจำนวนทั้งหมด
    count_sql = f"""
        SELECT COUNT(*) as total
        FROM Item_Master im
        WHERE {where_sql}
    """
    cur.execute(count_sql, *params)
    total = cur.fetchone()[0]
    
    logger.info(f"✅ Found {total} items matching search")
    
    # ดึงข้อมูล พร้อมราคา
    sql = f"""
        SELECT
            im.SKU,
            im.No_2,
            im.Description,
            im.Variant_Mandatory,
            im.Product_Group,
            im.Product_Sub_Group,
            im.Base_Unit_of_Measure,
            ip.R1,
            ip.R2,
            ip.W1,
            ip.W2
        FROM Item_Master im
        LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
        WHERE {where_sql}
        ORDER BY im.SKU
        OFFSET ? ROWS
        FETCH NEXT ? ROWS ONLY
    """
    # เพิ่ม branch_code เป็น parameter แรก
    cur.execute(sql, branch_code, *params, offset, limit)
    rows = cur.fetchall()
    
    logger.info(f"📦 Retrieved {len(rows)} items")
    
    # โหลด mapping tables
    cur.execute("SELECT Code, Name FROM Glass_Brand")
    brand_map = {str(c).zfill(2): n for c, n in cur.fetchall()}
    
    cur.execute("SELECT Code, Name FROM Glass_Color")
    color_map = {str(c).zfill(2): n for c, n in cur.fetchall()}
    
    cur.execute("SELECT Code, Name FROM Glass_Group")
    type_map = {str(r[0]).zfill(2): r[1] for r in cur.fetchall()}
    
    cur.execute("SELECT Type, Code, Name FROM Glass_SubGroup")
    subgroup_map = {(str(t).zfill(2), str(c).zfill(3)): n for t, c, n in cur.fetchall()}
    
    conn.close()
    
    # แปลงผลลัพธ์
    items = []
    for row in rows:
        sku = row[0]
        parsed = parse_glass_sku(sku)
        if not parsed:
            continue
        
        is_variant = int(row[3]) == 2 if row[3] else False
        
        items.append({
            "sku": sku,
            "sku2": row[1] or "",
            "description": row[2] or "",
            "isVariant": is_variant,
            "inventory": 0,
            "brand": parsed["brand"],
            "brandName": brand_map.get(parsed["brand"], ""),
            "type": parsed["type"],
            "typeName": type_map.get(parsed["type"], ""),
            "group": parsed["type"],
            "groupName": type_map.get(parsed["type"], ""),
            "subGroup": parsed["subGroup"],
            "subGroupName": subgroup_map.get((parsed["type"], parsed["subGroup"]), ""),
            "color": parsed["color"],
            "colorName": color_map.get(parsed["color"], ""),
            "thickness": parsed["thickness"],
            "width": parsed["width"],
            "height": parsed["height"],
            "product_group": row[4],
            "product_sub_group": row[5],
            "unit": row[6] or "แผ่น",
            "prices": {
                "R1": float(row[7]) if row[7] is not None else 0,
                "R2": float(row[8]) if row[8] is not None else 0,
                "W1": float(row[9]) if row[9] is not None else 0,
                "W2": float(row[10]) if row[10] is not None else 0,
            }
        })
    
    return {
        "items": items,
        "limit": limit,
        "offset": offset,
        "count": len(items),
        "total": total,
    }


class GlassCalcRequest(BaseModel):
    sku: str
    widthRaw: float
    heightRaw: float
    widthRounded: float
    heightRounded: float
    sqftRaw: float
    sqftRounded: float
    qty: int


@router.post("/glass/calc")
def calc_glass(req: GlassCalcRequest, branch_code: str = Depends(get_branch_code)):
    parsed = parse_glass_sku(req.sku)

    # ใช้ MSSQL สำหรับ mapping tables
    conn = get_mssql_conn()
    cur = conn.cursor()

    cur.execute("SELECT Name FROM Glass_Brand WHERE Code=?", (parsed["brand"],))
    row = cur.fetchone()
    brandName = row[0] if row else ""

    cur.execute("SELECT Name FROM Glass_Color WHERE Code=?", (parsed["color"],))
    row = cur.fetchone()
    colorName = row[0] if row else ""

    cur.execute("SELECT Code, Name FROM Glass_Group")
    type_map = {str(r[0]).zfill(2): r[1] for r in cur.fetchall()}

    cur.execute("""
        SELECT Name
        FROM Glass_SubGroup
        WHERE Type=? AND Code=?
    """, (parsed["type"], parsed["subGroup"]))
    row = cur.fetchone()
    subGroupName = row[0] if row else ""

    typeName = type_map.get(parsed["type"], "")

    # R2 จาก Item_Price ตาม branch_code
    cur.execute("""
        SELECT R2 
        FROM Item_Price WITH (NOLOCK)
        WHERE SKU = ? AND BranchCode = ?
    """, (req.sku, branch_code))
    row = cur.fetchone()
    price_r2 = float(row[0]) if row and row[0] else 0.0
    
    conn.close()

    total_price_r2 = price_r2 * req.sqftRounded

    return {
        "sku": req.sku,
        "brand": parsed["brand"],
        "brandName": brandName,
        "type": parsed["type"],
        "typeName": typeName,
        "subGroup": parsed["subGroup"],
        "subGroupName": subGroupName,
        "color": parsed["color"],
        "colorName": colorName,
        "thickness": parsed["thickness"],
        "width": req.widthRounded,
        "height": req.heightRounded,
        "sqft": req.sqftRounded,
        "qty": req.qty,
        "totalSqft": req.sqftRounded * req.qty,
        "priceR2": price_r2,
        "totalPriceR2": total_price_r2,
        "widthRaw": req.widthRaw,
        "heightRaw": req.heightRaw,
        "widthRounded": req.widthRounded,
        "heightRounded": req.heightRounded,
    }


@router.get("/glass/filter-options")
def get_glass_filter_options(
    brand: Optional[str] = None,
    type: Optional[str] = None,
    subGroup: Optional[str] = None,
    color: Optional[str] = None,
    thickness: Optional[str] = None,
    branch_code: Optional[str] = None  # ทำให้เป็น optional สำหรับ Promotion
):
    """ดึง filter options ที่ถูกกรองแล้วตามเงื่อนไขปัจจุบัน
    
    ส่งกลับ options สำหรับแต่ละฟิลเตอร์ที่ยังไม่ได้เลือก
    เช่น ถ้าเลือก brand แล้ว ให้ส่ง type/subGroup/color/thickness ที่มีอยู่ใน brand นั้น
    
    รองรับ multiple values (comma-separated) เช่น brand=01,02
    """
    
    # แปลง comma-separated values เป็น list
    brand_list = brand.split(',') if brand else []
    type_list = type.split(',') if type else []
    subGroup_list = subGroup.split(',') if subGroup else []
    color_list = color.split(',') if color else []
    thickness_list = thickness.split(',') if thickness else []
    
    # Query จาก database
    conn = get_mssql_conn()
    cur = conn.cursor()
    
    # ดึงกระจกทั้งหมด (ถ้าไม่ระบุ branch_code)
    if branch_code:
        # ดึงเฉพาะกระจกที่มีราคาในสาขานี้
        cur.execute("""
            SELECT DISTINCT
                im.SKU
            FROM Item_Master im
            LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
            WHERE im.SKU LIKE 'G%' AND im.Blocked = 0
        """, (branch_code,))
    else:
        # ดึงกระจกทั้งหมด (สำหรับ Promotion)
        cur.execute("""
            SELECT DISTINCT SKU
            FROM Item_Master
            WHERE SKU LIKE 'G%' AND Blocked = 0
        """)
    
    skus = [row[0] for row in cur.fetchall()]
    
    # โหลด mapping tables
    cur.execute("SELECT Code, Name FROM Glass_Brand")
    brand_map = {str(c).zfill(2): n for c, n in cur.fetchall()}
    
    cur.execute("SELECT Code, Name FROM Glass_Color")
    color_map = {str(c).zfill(2): n for c, n in cur.fetchall()}
    
    cur.execute("SELECT Code, Name FROM Glass_Group")
    type_map = {str(r[0]).zfill(2): r[1] for r in cur.fetchall()}
    
    cur.execute("SELECT Type, Code, Name FROM Glass_SubGroup")
    subgroup_rows = cur.fetchall()
    subgroup_map = {(str(t).zfill(2), str(c).zfill(3)): n for t, c, n in subgroup_rows}
    
    conn.close()
    
    # กรอง SKU ตามเงื่อนไขปัจจุบัน (รองรับ multiple values)
    filtered_skus = []
    for sku in skus:
        parsed = parse_glass_sku(sku)
        if not parsed:
            continue
        
        # ตรวจสอบว่า SKU ตรงกับ filter ทั้งหมด
        if brand_list and parsed["brand"] not in brand_list:
            continue
        if type_list and parsed["type"] not in type_list:
            continue
        if subGroup_list and parsed["subGroup"] not in subGroup_list:
            continue
        if color_list and parsed["color"] not in color_list:
            continue
        if thickness_list and parsed["thickness"] not in thickness_list:
            continue
        
        filtered_skus.append(sku)
    
    # สร้าง options สำหรับแต่ละฟิลเตอร์ โดยกรองตามเงื่อนไขปัจจุบัน
    brands = {}
    types = {}
    subGroups = {}
    colors = {}
    thicknesses = {}
    
    for sku in filtered_skus:
        parsed = parse_glass_sku(sku)
        if not parsed:
            continue
            
        brands[parsed["brand"]] = brand_map.get(parsed["brand"], parsed["brand"])
        types[parsed["type"]] = type_map.get(parsed["type"], parsed["type"])
        subGroups[parsed["subGroup"]] = subgroup_map.get((parsed["type"], parsed["subGroup"]), parsed["subGroup"])
        colors[parsed["color"]] = color_map.get(parsed["color"], parsed["color"])
        thicknesses[parsed["thickness"]] = parsed["thickness"]
    
    return {
        "brands": [{"value": k, "label": f"{k} - {v}"} for k, v in sorted(brands.items())],
        "types": [{"value": k, "label": f"{k} - {v}"} for k, v in sorted(types.items())],
        "subGroups": [{"value": k, "label": f"{k} - {v}"} for k, v in sorted(subGroups.items())],
        "colors": [{"value": k, "label": f"{k} - {v}"} for k, v in sorted(colors.items())],
        "thicknesses": [{"value": k, "label": f"{k} - {v} มม."} for k, v in sorted(thicknesses.items())],
    }


@router.get("/glass/{sku}/stock")
def get_glass_stock(sku: str, branch_code: str = Depends(get_branch_code)):
    """
    ดึงข้อมูล stock สำหรับกระจกเฉพาะสาขาของพนักงาน
    
    Response:
    {
        "sku": "G00080010000000000",
        "branch_code": "BKK",
        "quantity": 100
    }
    """
    try:
        from api.bc_item_client import BCAPIClient
        
        # สร้าง client
        client = BCAPIClient()
        
        # ดึงข้อมูล inventory ledger entries สำหรับ item และ branch นี้
        ledger_entries = client.fetch_inventory(sku, branch_code)
        
        # บวก Quantity จากทุก records
        total_quantity = 0
        for entry in ledger_entries:
            qty = entry.get("Quantity", 0)
            total_quantity += qty
        
        return {
            "sku": sku,
            "branch_code": branch_code,
            "quantity": float(total_quantity)
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching stock for SKU {sku} at branch {branch_code}: {str(e)}")
        
        # Return default response ถ้า API error
        return {
            "sku": sku,
            "branch_code": branch_code,
            "quantity": 0,
            "error": str(e)
        }
