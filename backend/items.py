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
        LEFT JOIN Item_Price ip ON im.SKU = ip.SKU AND ip.BranchCode = ?
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
        LEFT JOIN Item_Price ip ON im.SKU = ip.SKU AND ip.BranchCode = ?
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
        LEFT JOIN Item_Price ip ON im.SKU = ip.SKU AND ip.BranchCode = ?
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
        LEFT JOIN Item_Price ip ON im.SKU = ip.SKU AND ip.BranchCode = ?
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
                LEFT JOIN Item_Price ip ON im.SKU = ip.SKU AND ip.BranchCode = ?
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
                LEFT JOIN Item_Price ip ON im.SKU = ip.SKU AND ip.BranchCode = ?
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
            LEFT JOIN Item_Price ip ON im.SKU = ip.SKU AND ip.BranchCode = ?
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
        LEFT JOIN Item_Price ip ON im.SKU = ip.SKU AND ip.BranchCode = ?
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
            LEFT JOIN Item_Price ip ON im.SKU = ip.SKU AND ip.BranchCode = ?
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
def get_related_items(sku: str, limit: int = 50, branch_code: str = Depends(get_branch_code)):
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

    # ดึงสินค้าใน Product Group เดียวกัน (LIGHT - เฉพาะข้อมูลที่จำเป็น)
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
        ORDER BY im.SKU
    """
    cursor.execute(sql, product_group, sku, sku)
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
