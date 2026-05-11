# ============================================
# quotation.py — SQLite Version (Full Feature)
# Compatible with old JSON behavior 100%
# ============================================

from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import logging
from config.db_mssql import get_mssql_conn


from fastapi import APIRouter, HTTPException, Body, Depends
from openpyxl import load_workbook
from auth_dependency import get_branch_code, get_employee_info

router = APIRouter(prefix="/quotation", tags=["quotation"])

logger = logging.getLogger(__name__)


# Excel template directory
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXCEL_FILE = DATA_DIR / "QuoteTemplate.xlsx"


# -----------------------------------------------------
# Helpers
# -----------------------------------------------------
def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _calculate_expire_date(create_date: str = None) -> str:
    """
    คำนวณวันหมดอายุ (1 เดือนหลังจากวันที่สร้าง)
    """
    if create_date:
        base_date = datetime.fromisoformat(create_date)
    else:
        base_date = datetime.now()
    
    # เพิ่ม 1 เดือน (30 วัน)
    expire_date = base_date + timedelta(days=30)
    return expire_date.isoformat(timespec="seconds")


def _generate_quote_no(branch_code: str, ibt_branch: str = None) -> str:
    """
    Format:  BSQT-6902/0001 (normal) - ใช้ พ.ศ.
             BSQT-6902/0001-IBT-00TR (IBT)
    """
    now = datetime.now()
    buddhist_year = now.year + 543  # แปลงเป็น พ.ศ.
    yy = str(buddhist_year)[-2:]  # เอา 2 หลักท้าย
    mm = f"{now.month:02d}"

    prefix = f"{branch_code[-2:].upper()}QT-{yy}{mm}"

    conn = get_mssql_conn()
    cursor = conn.cursor()

    # ถ้าเป็น IBT ให้ค้นหาเลขที่ IBT เท่านั้น
    if ibt_branch:
        cursor.execute("""
            SELECT QuoteNo FROM Quote_Header
            WHERE QuoteNo LIKE ? AND IBT_branch IS NOT NULL
        """, (f"{prefix}%",))
    else:
        cursor.execute("""
            SELECT QuoteNo FROM Quote_Header
            WHERE QuoteNo LIKE ? AND IBT_branch IS NULL
        """, (f"{prefix}%",))

    count = len(cursor.fetchall()) + 1
    seq = f"{count:04d}"

    quote_no = f"{prefix}/{seq}"
    
    # ถ้าเป็น IBT ให้เพิ่มเลขประจำตัว IBT
    if ibt_branch:
        quote_no = f"{quote_no}-IBT-{ibt_branch}"

    return quote_no


def _safe_get_header_row(ws):
    first_row = next(ws.iter_rows(min_row=1, max_row=1))
    return [c.value for c in first_row]


def _append_header_to_excel(header: dict):
    if not EXCEL_FILE.exists():
        return

    wb = load_workbook(EXCEL_FILE)
    if "Quote_Header" not in wb.sheetnames:
        return

    ws = wb["Quote_Header"]
    headers = _safe_get_header_row(ws)
    row = [""] * len(headers)

    def set_col(col, val):
        if col in headers:
            row[headers.index(col)] = val

    for key, val in header.items():
        set_col(key, val)

    ws.append(row)
    wb.save(EXCEL_FILE)


def _append_lines_to_excel(quote_no: str, lines: list):
    if not EXCEL_FILE.exists():
        return

    wb = load_workbook(EXCEL_FILE)
    if "Quote_Line" not in wb.sheetnames:
        return

    ws = wb["Quote_Line"]
    headers = _safe_get_header_row(ws)

    def to_row(line: dict):
        row = [""] * len(headers)

        def set_col(col, val):
            if col in headers:
                row[headers.index(col)] = val

        set_col("QuoteID", quote_no)
        for key, val in line.items():
            set_col(key, val)

        return row

    for ln in lines:
        ws.append(to_row(ln))

    wb.save(EXCEL_FILE)


# -----------------------------------------------------
# Normalize keys
# -----------------------------------------------------
def row_to_dict(cursor, row):
    """แปลง MSSQL row เป็น dict"""
    if row is None:
        return None
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row))


def normalize_keys(row: dict):
    return {k.strip(): v for k, v in row.items()}


def _build_line_from_payload(item: dict) -> dict:
    sku = item["sku"]
    name = item.get("name", "")
    category = (
        item.get("category")
        or str(item.get("sku", "")).strip()[:1].upper()
    )

    unit = item.get("unit", "")
    price_system = float(item.get("Price_System", 0) or 0)

    qty = float(item.get("qty", 0) or 0)
    price = float(item.get("price", 0) or 0)
    sqft_sheet = float(item.get("sqft_sheet", 0) or 0)

    if qty < 0:
        qty = 0

    if item.get("lineTotal") is not None:
        line_total = float(item.get("lineTotal") or 0)
    else:
        if str(category).upper() == "G":
            line_total = round(price * sqft_sheet * qty, 2)
        else:
            line_total = round(price * qty, 2)

    return {
        "ItemCode": sku,
        "ItemName": name,
        "Category": category,
        "Unit": unit,
        "Quantity": qty,
        "Price_System": price_system,
        "UnitPrice": price,
        "TotalPrice": line_total,
        "IsGlassCut": "Y" if item.get("isGlassCut") else "N",
        "Sqft_Sheet": sqft_sheet,
        "VariantCode": item.get("variantCode", ""),
        "ProductWeight": float(item.get("product_weight", 0) or 0),
        "CutInfoJson": json.dumps(item.get("cutInfo", "")),
        "Remark": item.get("remark", "")
    }


# -----------------------------------------------------
# CREATE QUOTATION
# -----------------------------------------------------
@router.post("", summary="สร้างใบเสนอราคาใหม่")
def create_quotation(payload: dict = Body(...)):
    conn = get_mssql_conn()
    cursor = conn.cursor()

    employee = payload.get("employee") or {}
    customer = payload.get("customer") or {}
    branch = employee.get("branchId", "")
    ibt_branch = payload.get("ibtBranch")  # ⭐ ดึง IBT branch

    raw_code = (customer.get("code") or "").strip()
    raw_name = (customer.get("name") or "").strip()

    # ลูกค้าใหม่: ไม่มี code แต่มีชื่อ
    cust_code = raw_code or "N/A"

    if raw_name:
        cust_name = raw_name
    else:
        cust_name = "ลูกค้าใหม่"


    quote_no = _generate_quote_no(branch, ibt_branch)  # ⭐ ส่ง ibt_branch
    now = _now_iso()
    expire_date = _calculate_expire_date(now)  # ⭐ คำนวณวันหมดอายุอัตโนมัติ

    header = {
        "QuoteNo": quote_no,
        "Status": payload.get("status", "draft"),
        "CustomerCode": cust_code,
        "SalesID": employee.get("id", ""),
        "SalesName": employee.get("name", ""),
        "CreateDate": now,
        "ExpireDate": expire_date,  # ⭐ ใช้วันหมดอายุที่คำนวณ
        "ApproveDate": now,
        "BranchCode": branch,
        "PaymentTerm": payload.get("paymentTerm", ""),
        "CreditTerm": payload.get("creditTerm", ""),
        "ShippingMethod": payload.get("deliveryType", ""),
        "ShippingCost": payload.get("totals", {}).get("shippingRaw", 0),
        "DiscountAmount": payload.get("discount", 0),
        "SubtotalAmount": payload.get("totals", {}).get("exVat", 0),
        "TotalAmount": payload.get("totals", {}).get("grandTotal", 0),
        "NeedsTax": "Y" if payload.get("needTaxInvoice") else "N",
        "Remark": (payload.get("remark", "") or "")[:255],  # ⭐ หมายเหตุทั่วไป
        "Remark_Shipping": (payload.get("note", "") or "")[:255],  # ⭐ เหตุผลการแก้ค่าขนส่ง
        "LastUpdate": now,
        "CustomerName": cust_name,
        "Tel": customer.get("phone", ""),
        "tax_no": customer.get("tax_no", ""),
        "ShippingCustomerPay": payload.get("totals", {}).get("shippingCustomerPay", 0),
        "Pre_Order": payload.get("pre_order", 0),  # ⭐ เพิ่ม Pre_Order field
        "Required_Delivery_Date": payload.get("required_delivery_date") or None,  # ⭐ เพิ่ม Required_Delivery_Date field
        "project_code": payload.get("project_code") or None,  # ⭐ เพิ่ม project_code field
        "IBT_branch": ibt_branch,  # ⭐ เพิ่ม IBT_branch field
    }

    cursor.execute("""
        INSERT INTO Quote_Header (
            QuoteNo, Status, CustomerCode, SalesID, SalesName,
            CreateDate, ExpireDate, ApproveDate, BranchCode,
            PaymentTerm, CreditTerm, ShippingMethod, ShippingCost,
            DiscountAmount, SubtotalAmount, TotalAmount,
            NeedsTax, Remark, Remark_Shipping, LastUpdate,
            CustomerName, Tel, tax_no, ShippingCustomerPay, Pre_Order, Required_Delivery_Date, project_code, IBT_branch
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, tuple(header.values()))

    cart = payload.get("cart", [])
    if not cart:
        raise HTTPException(400, "ต้องมีสินค้าอย่างน้อย 1 รายการ")

    lines_to_excel = []

    for item in cart:
        line = _build_line_from_payload(item)

        cursor.execute("""
            INSERT INTO Quote_Line (
                QuoteID, ItemCode, ItemName, Category,
                Unit, Quantity, Price_System, UnitPrice, TotalPrice,
                IsGlassCut, CutInfoJson, Remark,
                Sqft_Sheet, VariantCode, ProductWeight
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            quote_no,
            line["ItemCode"], line["ItemName"], line["Category"],
            line["Unit"], line["Quantity"], line["Price_System"], line["UnitPrice"],
            line["TotalPrice"], line["IsGlassCut"],
            line["CutInfoJson"], line["Remark"],
            line["Sqft_Sheet"], line["VariantCode"], line["ProductWeight"],
        ))

        lines_to_excel.append(line)

    conn.commit()
    conn.close()

    _append_header_to_excel(header)
    _append_lines_to_excel(quote_no, lines_to_excel)

    return {
        "id": quote_no,              # ใช้ quoteNo เป็น id
        "quoteNo": quote_no,
        "status": payload.get("status", "draft")
    }



# -----------------------------------------------------
# UPDATE QUOTATION
# -----------------------------------------------------
@router.put("/{quote_no:path}", summary="อัปเดตใบเสนอราคา")
def update_quotation(quote_no: str, payload: dict = Body(...)):
    conn = get_mssql_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Quote_Header WHERE QuoteNo=?", (quote_no,))
    original_row = cursor.fetchone()
    if not original_row:
        raise HTTPException(404, f"ไม่พบใบเสนอราคา {quote_no}")
    
    # แปลง row เป็น dict
    columns = [column[0] for column in cursor.description]
    original = dict(zip(columns, original_row))

    employee = payload.get("employee") or {}
    customer = payload.get("customer") or {}
    ibt_branch = payload.get("ibtBranch")  # ⭐ ดึง IBT branch
    now = _now_iso()
    raw_code = (customer.get("code") or "").strip()
    raw_name = (customer.get("name") or "").strip()

    cust_code = raw_code or "N/A"

    if raw_name:
        cust_name = raw_name
    else:
        cust_name = "ลูกค้าใหม่"


    header = {
        "Status": payload.get("status", "draft"),
        "CustomerCode": cust_code,
        "SalesID": employee.get("id", ""),
        "SalesName": employee.get("name", ""),
        "ExpireDate": payload.get("expireDate") or _calculate_expire_date(now),  # ⭐ ถ้าไม่มี ให้คำนวณใหม่
        "ApproveDate": now,
        "BranchCode": employee.get("branchId", ""),
        "PaymentTerm": payload.get("paymentTerm", ""),
        "CreditTerm": payload.get("creditTerm", ""),
        "ShippingMethod": payload.get("deliveryType", ""),
        "ShippingCost": payload.get("totals", {}).get("shippingRaw", 0),
        "DiscountAmount": payload.get("discount", 0),
        "SubtotalAmount": payload.get("totals", {}).get("exVat", 0),
        "TotalAmount": payload.get("totals", {}).get("grandTotal", 0),
        "NeedsTax": "Y" if payload.get("needTaxInvoice") else "N",
        "Remark": payload.get("remark", ""),  # ⭐ หมายเหตุทั่วไป
        "Remark_Shipping": payload.get("note", ""),  # ⭐ เหตุผลการแก้ค่าขนส่ง
        "LastUpdate": now,
        "CustomerName": cust_name,
        "Tel": customer.get("phone", ""),
        "tax_no": customer.get("tax_no", ""),
        "ShippingCustomerPay": payload.get("totals", {}).get("shippingCustomerPay", 0),
        "Pre_Order": payload.get("pre_order", 0),  # ⭐ เพิ่ม Pre_Order field
        "Required_Delivery_Date": payload.get("required_delivery_date") or None,  # ⭐ เพิ่ม Required_Delivery_Date field
        "project_code": payload.get("project_code") or None,  # ⭐ เพิ่ม project_code field
        "IBT_branch": ibt_branch,  # ⭐ เพิ่ม IBT_branch field
    }

    cursor.execute("""
        UPDATE Quote_Header SET
            Status=?, CustomerCode=?, SalesID=?, SalesName=?,
            ExpireDate=?, ApproveDate=?, BranchCode=?,
            PaymentTerm=?, CreditTerm=?, ShippingMethod=?, ShippingCost=?,
            DiscountAmount=?, SubtotalAmount=?, TotalAmount=?,
            NeedsTax=?, Remark=?, Remark_Shipping=?, LastUpdate=?,
            CustomerName=?, Tel=?, tax_no=?, ShippingCustomerPay=?, Pre_Order=?, Required_Delivery_Date=?, project_code=?, IBT_branch=?
        WHERE QuoteNo=?
    """, (
        header["Status"],
        header["CustomerCode"],
        header["SalesID"],
        header["SalesName"],
        header["ExpireDate"],
        header["ApproveDate"],
        header["BranchCode"],
        header["PaymentTerm"],
        header["CreditTerm"],
        header["ShippingMethod"],
        header["ShippingCost"],
        header["DiscountAmount"],
        header["SubtotalAmount"],
        header["TotalAmount"],
        header["NeedsTax"],
        header["Remark"],
        header["Remark_Shipping"],
        header["LastUpdate"],
        header["CustomerName"],
        header["Tel"],
        header["tax_no"],
        header["ShippingCustomerPay"],
        header["Pre_Order"],
        header["Required_Delivery_Date"],
        header["project_code"],
        header["IBT_branch"],
        quote_no
    ))

    cursor.execute("DELETE FROM Quote_Line WHERE QuoteID=?", (quote_no,))

    cart = payload.get("cart", [])
    if not cart:
        raise HTTPException(400, "ต้องมีสินค้าอย่างน้อย 1 รายการ")

    lines_to_excel = []
    for item in cart:
        line = _build_line_from_payload(item)

        cursor.execute("""
            INSERT INTO Quote_Line (
                QuoteID, ItemCode, ItemName, Category,
                Unit, Quantity, Price_System, UnitPrice, TotalPrice,
                IsGlassCut, CutInfoJson, Remark,
                Sqft_Sheet, VariantCode, ProductWeight
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            quote_no,
            line["ItemCode"], line["ItemName"], line["Category"],
            line["Unit"], line["Quantity"], line["Price_System"], line["UnitPrice"],
            line["TotalPrice"], line["IsGlassCut"],
            line["CutInfoJson"], line["Remark"],
            line["Sqft_Sheet"], line["VariantCode"], line["ProductWeight"],
        ))

        lines_to_excel.append(line)

    conn.commit()
    conn.close()

    updated_header = dict(original)
    updated_header.update(header)
    updated_header["QuoteNo"] = quote_no
    updated_header["CreateDate"] = original["CreateDate"]

    _append_header_to_excel(updated_header)
    _append_lines_to_excel(quote_no, lines_to_excel)

    return {
        "id": quote_no,
        "quoteNo": quote_no,
        "status": header["Status"]
    }



# -----------------------------------------------------
# LIST / HISTORY
# -----------------------------------------------------
@router.get("", summary="โหลดรายการใบเสนอราคาแบบทั้งหมด")
def list_quotations(
    status: str = None,
    branch_code: str = Depends(get_branch_code),
    employee_info: dict = Depends(get_employee_info)
):
    """
    โหลดรายการใบเสนอราคา กรองตามสาขาของพนักงาน
    รวมถึงใบเสนอราคา IBT ที่ส่งไปยังสาขานี้
    
    สำหรับ RM (ผู้จัดการภาค): จะเห็นข้อมูลทุกสาขาในภาคของตนเอง
    
    Args:
        status: กรองตาม status (draft, complete, cancelled)
        branch_code: รหัสสาขาจาก JWT token
        employee_info: ข้อมูลพนักงานจาก JWT token (role, region)
    """
    from branch_region_mapping import get_all_branches_by_region
    
    conn = get_mssql_conn()
    cursor = conn.cursor()

    # ถ้าเป็น RM ให้ดึงทุกสาขาในภาค 
    role = employee_info.get("role", "Sales")
    region = employee_info.get("region", "BKK")
    
    if role == "RM":
        # RM เห็นทุกสาขาในภาค
        branches_in_region = get_all_branches_by_region(region)
        
        # ⭐ ถ้า RM อยู่ใน E ให้เพิ่ม BKK branches ด้วย (BKK และ E เป็นภูมิภาคเดียวกัน)
        if region == "E":
            branches_in_region.extend(get_all_branches_by_region("BKK"))
        elif region == "BKK":
            # ⭐ ถ้า RM อยู่ใน BKK ให้เพิ่ม E branches ด้วย
            branches_in_region.extend(get_all_branches_by_region("E"))
        
        logger.info(f"RM viewing quotes for region {region}: {branches_in_region}")
        
        # สร้าง placeholders สำหรับ SQL IN clause
        placeholders = ",".join(["?" for _ in branches_in_region])
        
        if status:
            query = f"""
                SELECT * FROM Quote_Header
                WHERE Status = ? AND (BranchCode IN ({placeholders}) OR IBT_branch IN ({placeholders}))
                ORDER BY LastUpdate DESC
            """
            params = [status] + branches_in_region + branches_in_region
            cursor.execute(query, params)
        else:
            query = f"""
                SELECT * FROM Quote_Header
                WHERE BranchCode IN ({placeholders}) OR IBT_branch IN ({placeholders})
                ORDER BY LastUpdate DESC
            """
            params = branches_in_region + branches_in_region
            cursor.execute(query, params)
    else:
        # พนักงานทั่วไป (Sales, ZM) เห็นเฉพาะสาขาของตนเอง
        if status:
            cursor.execute("""
                SELECT * FROM Quote_Header
                WHERE Status = ? AND (BranchCode = ? OR IBT_branch = ?)
                ORDER BY LastUpdate DESC
            """, (status, branch_code, branch_code))
        else:
            cursor.execute("""
                SELECT * FROM Quote_Header
                WHERE BranchCode = ? OR IBT_branch = ?
                ORDER BY LastUpdate DESC
            """, (branch_code, branch_code))

    headers = [normalize_keys(row_to_dict(cursor, r)) for r in cursor.fetchall()]
    result = []

    for h in headers:
        quote_no = h["QuoteNo"]

        cursor.execute("SELECT * FROM Quote_Line WHERE QuoteID=?", (quote_no,))
        lines = [normalize_keys(row_to_dict(cursor, r)) for r in cursor.fetchall()]

        cart_items = [
            {
                "sku": ln["ItemCode"],
                "name": ln["ItemName"],
                "qty": ln["Quantity"],
                "price": ln["UnitPrice"],
                "Price_System": ln.get("Price_System", 0),
                "lineTotal": ln["TotalPrice"],
                "category": ln["Category"],
                "unit": ln["Unit"],
                "sqft_sheet": ln.get("Sqft_Sheet") or 0,
                "product_weight": ln.get("ProductWeight") or 0,
                "variantCode": ln.get("VariantCode", ""),
            }
            for ln in lines
        ]

        result.append({
            "quoteNo": quote_no,
            "id": quote_no,
            "status": h.get("Status", "draft"),  # ⭐ เพิ่ม status
            "customer": {
                "id": h["CustomerCode"],
                "code": h["CustomerCode"],
                "name": h["CustomerName"],
                "phone": h.get("Tel", "")
            },
            "employee": {
                "id": h["SalesID"],
                "name": h["SalesName"]
            },
            "createdAt": h["CreateDate"],
            "updatedAt": h["LastUpdate"],
            "totals": {
                "grandTotal": h["TotalAmount"],
                "exVat": h["SubtotalAmount"],
                "shippingRaw": h["ShippingCost"],
            },
            "cart": cart_items,
            "items": cart_items,  # ⭐ alias สำหรับ frontend
            "ibtBranch": h.get("IBT_branch"),  # ⭐ เพิ่ม IBT_branch
        })

    conn.close()
    return result


# -----------------------------------------------------
# =====================================================
# GET PRE-ORDER QUOTES BY BRANCH CODE
# =====================================================
@router.get("/pre-order/{branch_code}", summary="ดึงใบเสนอราคา Pre-Order ตามสาขา")
def get_preorder_quotes(branch_code: str):
    """
    ดึงรายการใบเสนอราคาที่เป็น Pre-Order ตามรหัสสาขา
    
    Args:
        branch_code: รหัสสาขา (เช่น BKK, CNX)
    
    Returns:
        List of Quote_Header records where Pre_Order = 1
    """
    conn = None
    
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        print(f"🔍 [GET PRE-ORDER QUOTES] Branch: {branch_code}")
        
        # ดึงใบเสนอราคาที่เป็น Pre-Order ของสาขานี้
        cursor.execute("""
            SELECT 
                QuoteNo, Status, CustomerCode, CustomerName, SalesID, SalesName,
                CreateDate, ExpireDate, ApproveDate, BranchCode,
                ShippingCost, DiscountAmount, SubtotalAmount, TotalAmount,
                NeedsTax, Remark, Remark_Shipping, LastUpdate,
                Tel, tax_no, ShippingCustomerPay, Pre_Order, Required_Delivery_Date, project_code
            FROM Quote_Header
            WHERE Pre_Order = 1 AND BranchCode = ?
            ORDER BY CreateDate DESC
        """, (branch_code,))
        
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # แปลง datetime เป็น string
        for r in results:
            for key in ['CreateDate', 'ExpireDate', 'ApproveDate', 'LastUpdate', 'Required_Delivery_Date']:
                if r.get(key):
                    r[key] = str(r[key])
        
        print(f"📦 [GET PRE-ORDER QUOTES] Found {len(results)} pre-order quotes for branch {branch_code}")
        
        return results
    
    except Exception as e:
        print(f"❌ [GET PRE-ORDER QUOTES] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if conn:
            conn.close()


# GET SINGLE QUOTATION
# -----------------------------------------------------
@router.get("/{quote_no:path}", summary="โหลดใบเสนอราคาแบบเต็ม")
def get_quotation(quote_no: str):
    conn = get_mssql_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Quote_Header WHERE QuoteNo=?", (quote_no,))
    header = cursor.fetchone()
    if not header:
        raise HTTPException(404, f"ไม่พบใบเสนอราคา {quote_no}")

    header = normalize_keys(row_to_dict(cursor, header))  # ⭐ MSSQL: แปลง row เป็น dict

    cursor.execute("SELECT * FROM Quote_Line WHERE QuoteID=?", (quote_no,))
    lines = [normalize_keys(row_to_dict(cursor, r)) for r in cursor.fetchall()]

    conn.close()

    return {
        "header": header,
        "lines": [
            {
                **ln,
                "Price_System": ln.get("Price_System", 0),
                "product_weight": ln.get("ProductWeight", 0),
                "variantCode": ln.get("VariantCode", ""),
            }
            for ln in lines
        ]
    }


# -----------------------------------------------------
# DELETE
# -----------------------------------------------------
@router.delete("/{quote_no:path}", summary="ยกเลิกใบเสนอราคา")
def cancel_quotation(quote_no: str):
    conn = get_mssql_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Quote_Header WHERE QuoteNo=?", (quote_no,))
    if not cursor.fetchone():
        raise HTTPException(404, "ไม่พบใบเสนอราคา")

    cursor.execute("""
        UPDATE Quote_Header
        SET Status = 'canceled', LastUpdate = ?
        WHERE QuoteNo = ?
    """, (_now_iso(), quote_no))

    conn.commit()
    conn.close()

    return {"cancelled": quote_no}


# -----------------------------------------------------
# REORDER / ซื้อซ้ำ
# -----------------------------------------------------
@router.post("/{quote_no:path}/reorder", summary="ซื้อซ้ำจากใบเสนอราคา")
async def reorder_quotation(quote_no: str, branch_code: str = Depends(get_branch_code)):
    """ซื้อซ้ำจากใบเสนอราคา - คำนวณราคาใหม่ถ้าหมดอายุ"""
    from quotation_reorder import reorder_quotation_new
    return await reorder_quotation_new(quote_no, branch_code)
    """
    ซื้อซ้ำจากใบเสนอราคา
    - ตรวจสอบว่าใบเสนอราคาหมดอายุหรือไม่
    - ถ้าหมดอายุ (เกิน 1 เดือน) จะคำนวณราคาใหม่จาก Backend
    - Frontend จะได้รับราคาใหม่พร้อมใช้งาน
    
    Returns:
        {
            "quote": {...},
            "isExpired": bool,
            "expireDate": str,
            "daysExpired": int (ถ้าหมดอายุ)
        }
    """
    import httpx
    
    conn = get_mssql_conn()
    cursor = conn.cursor()

    # ดึงข้อมูลใบเสนอราคา
    cursor.execute("SELECT * FROM Quote_Header WHERE QuoteNo=?", (quote_no,))
    header = cursor.fetchone()
    if not header:
        raise HTTPException(404, f"ไม่พบใบเสนอราคา {quote_no}")

    header = normalize_keys(row_to_dict(cursor, header))

    # ดึงรายการสินค้า
    cursor.execute("SELECT * FROM Quote_Line WHERE QuoteID=?", (quote_no,))
    lines = [normalize_keys(row_to_dict(cursor, r)) for r in cursor.fetchall()]

    conn.close()

    # ตรวจสอบวันหมดอายุ
    expire_date_str = header.get("ExpireDate")
    is_expired = False
    days_expired = 0

    if expire_date_str:
        try:
            # แปลง string เป็น datetime
            if isinstance(expire_date_str, str):
                expire_date = datetime.fromisoformat(expire_date_str.replace('Z', '+00:00'))
            else:
                expire_date = expire_date_str
            
            now = datetime.now()
            
            # ตรวจสอบว่าหมดอายุหรือไม่
            if now > expire_date:
                is_expired = True
                days_expired = (now - expire_date).days
                logger.info(f"Quote {quote_no} expired {days_expired} days ago - recalculating prices")
        except Exception as e:
            logger.error(f"Error parsing expire date: {e}")

    # สร้าง cart items
    cart_items = []
    for ln in lines:
        item = {
            "sku": ln["ItemCode"],
            "name": ln["ItemName"],
            "qty": ln["Quantity"],
            "category": ln["Category"],
            "unit": ln["Unit"],
            "sqft_sheet": ln.get("Sqft_Sheet") or 0,
            "product_weight": ln.get("ProductWeight") or 0,
            "variantCode": ln.get("VariantCode", ""),
            "isGlassCut": ln.get("IsGlassCut") == "Y",
            "remark": ln.get("Remark", ""),
        }
        
        # ⭐ ถ้าไม่หมดอายุ ให้ใช้ราคาเดิม
        if not is_expired:
            item["price"] = ln["UnitPrice"]
            item["Price_System"] = ln.get("Price_System", 0)
            item["lineTotal"] = ln["TotalPrice"]
        
        # ถ้ามี CutInfoJson ให้แปลงกลับเป็น object
        if ln.get("CutInfoJson"):
            try:
                item["cutInfo"] = json.loads(ln["CutInfoJson"])
            except:
                item["cutInfo"] = ""
        
        cart_items.append(item)

    # ⭐ ถ้าหมดอายุ ให้เรียก pricing API คำนวณราคาใหม่
    if is_expired:
        try:
            logger.info(f"Recalculating prices for expired quote {quote_no}")
            
            # เตรียมข้อมูลลูกค้า
            customer_code = header["CustomerCode"]
            
            # ดึงข้อมูลลูกค้าเพิ่มเติมจาก customer API
            customer_data = {
                "customerCode": customer_code,
                "customerName": header["CustomerName"],
                "paymentTerm": header.get("PaymentTerm", ""),
                "paymentMethod": header.get("CreditTerm", ""),
            }
            
            # เรียก pricing API
            async with httpx.AsyncClient(timeout=30.0) as client:
                pricing_response = await client.post(
                    "http://localhost:8000/api/pricing/calculate",
                    json={
                        "customerData": customer_data,
                        "items": [
                            {
                                "sku": it["sku"],
                                "qty": it["qty"],
                                "category": it["category"],
                                "variantCode": it.get("variantCode", ""),
                                "sqft_sheet": it.get("sqft_sheet", 0),
                            }
                            for it in cart_items
                        ],
                    }
                )
                
                if pricing_response.status_code == 200:
                    pricing_data = pricing_response.json()
                    priced_items = pricing_data.get("items", [])
                    
                    # อัพเดทราคาใหม่
                    for i, item in enumerate(cart_items):
                        if i < len(priced_items):
                            priced = priced_items[i]
                            item["price"] = priced.get("UnitPrice", 0)
                            item["Price_System"] = priced.get("Price_System", 0)
                            
                            # คำนวณ lineTotal
                            if item["category"] == "G" and item.get("sqft_sheet", 0) > 0:
                                item["lineTotal"] = item["price"] * item["sqft_sheet"] * item["qty"]
                            else:
                                item["lineTotal"] = item["price"] * item["qty"]
                            
                            logger.info(f"Updated price for {item['sku']}: {item['price']}")
                else:
                    logger.error(f"Pricing API failed: {pricing_response.status_code}")
                    raise HTTPException(500, "ไม่สามารถคำนวณราคาใหม่ได้")
                    
        except Exception as e:
            logger.error(f"Error recalculating prices: {e}")
            raise HTTPException(500, f"เกิดข้อผิดพลาดในการคำนวณราคาใหม่: {str(e)}")

    # สร้าง response
    result = {
        "quote": {
            "quoteNo": quote_no,
            "id": quote_no,
            "status": header.get("Status", "draft"),
            "customer": {
                "id": header["CustomerCode"],
                "code": header["CustomerCode"],
                "name": header["CustomerName"],
                "phone": header.get("Tel", ""),
                "tax_no": header.get("tax_no", "")
            },
            "employee": {
                "id": header["SalesID"],
                "name": header["SalesName"],
                "branchId": header["BranchCode"]
            },
            "createdAt": header["CreateDate"],
            "expireDate": header.get("ExpireDate"),
            "totals": {
                "grandTotal": header["TotalAmount"],
                "exVat": header["SubtotalAmount"],
                "shippingRaw": header["ShippingCost"],
                "shippingCustomerPay": header.get("ShippingCustomerPay", 0)
            },
            "cart": cart_items,
            "items": cart_items,
            "remark": header.get("Remark", ""),
            "note": header.get("Remark_Shipping", ""),
            "paymentTerm": header.get("PaymentTerm", ""),
            "creditTerm": header.get("CreditTerm", ""),
            "deliveryType": header.get("ShippingMethod", ""),
            "needTaxInvoice": header.get("NeedsTax") == "Y",
            "discount": header.get("DiscountAmount", 0),
            "pre_order": header.get("Pre_Order", 0),
            "required_delivery_date": header.get("Required_Delivery_Date"),
            "project_code": header.get("project_code") or header.get("ProjectCode"),  # ⭐ fallback to PascalCase
            "ibtBranch": header.get("IBT_branch"),
        },
        "isExpired": is_expired,
        "expireDate": expire_date_str,
    }

    if is_expired:
        result["daysExpired"] = days_expired

    return result

