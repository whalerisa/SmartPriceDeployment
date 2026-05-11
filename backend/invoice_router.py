# backend/invoice_router.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta

from config.db_mssql import get_mssql_conn


# ✅ ประกาศ prefix ที่ router เลย (เหมือน pricing / shipping)
router = APIRouter(
    prefix="/api/invoice",
    tags=["invoice"]
)


# -------------------------------------------------------
# Load invoice from Database
# -------------------------------------------------------
def load_invoice_from_db(
    document_no: Optional[str] = None,
    customer_no: Optional[str] = None,
    posting_date: Optional[str] = None,
    limit: int = 200,
    project_only: bool = False,  # ⭐ เพิ่มพารามิเตอร์กรองเฉพาะ Invoice ที่มี Project_No
):
    """
    ดึงข้อมูล Invoice จาก MSSQL Database
    """
    conn = get_mssql_conn()
    cursor = conn.cursor()
    
    try:
        # สร้าง SQL query
        sql = "SELECT TOP (?) Document_No, Order_No, customer_code, Sell_to_Customer_Name, "
        sql += "Posting_Date, sku, Description, Variant_Code, Quantity, Unit_of_Measure, "
        sql += "Unit_Price, Line_Amount, Line_Amount_Include_VAT, Project_No "  # ⭐ เพิ่ม Project_No
        sql += "FROM dbo.Invoice WHERE 1=1"
        
        params = [limit]
        
        # ⭐ กรองเฉพาะ Invoice ที่มี Project_No (ไม่ใช่ NULL)
        if project_only:
            sql += " AND Project_No IS NOT NULL"
        
        # เพิ่ม filter ถ้ามี
        if customer_no:
            sql += " AND customer_code = ?"
            params.append(customer_no)
        
        if document_no:
            sql += " AND Document_No = ?"
            params.append(document_no)
        
        if posting_date:
            sql += " AND Posting_Date = ?"
            params.append(posting_date)
        
        sql += " ORDER BY Posting_Date DESC"
        
        cursor.execute(sql, params)
        columns = [column[0] for column in cursor.description]
        rows = []
        
        for row in cursor.fetchall():
            row_dict = {}
            for i, value in enumerate(row):
                col_name = columns[i]
                # แปลง column name ให้ตรงกับ format เดิมที่ API ส่งมา
                if col_name == "Document_No":
                    row_dict["Document No."] = value
                elif col_name == "Order_No":
                    row_dict["Order No."] = value
                elif col_name == "Sell_to_Customer_Name":
                    row_dict["Sell-to Customer Name"] = value
                elif col_name == "Posting_Date":
                    row_dict["Posting Date"] = value.isoformat() if value else None
                elif col_name == "Variant_Code":
                    row_dict["Variant Code"] = value
                elif col_name == "Unit_of_Measure":
                    row_dict["Unit of Measure"] = value
                elif col_name == "Unit_Price":
                    row_dict["Unit Price"] = float(value) if value else 0
                elif col_name == "Line_Amount":
                    row_dict["Amount"] = float(value) if value else 0
                elif col_name == "Line_Amount_Include_VAT":
                    row_dict["Amount Including VAT"] = float(value) if value else 0
                elif col_name == "Project_No":  # ⭐ เพิ่ม Project_No
                    row_dict["Project No."] = value
                else:
                    row_dict[col_name] = value
            
            rows.append(row_dict)
        
        return rows
        
    except Exception as e:
        print(f"❌ Error loading invoice from database: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


# -------------------------------------------------------
# GET /api/invoice/list
# -------------------------------------------------------
@router.get("/list")
def list_invoice(
    document_no: Optional[str] = Query(None),
    customer_no: Optional[str] = Query(None),
    posting_date: Optional[str] = Query(None),
    limit: int = 200,
    return_line_items: bool = Query(False),
    project_only: bool = Query(False),  
):
    """
    ดึงรายการ Invoice จาก MSSQL Database
    
    Query Parameters:
    - customer_no: Filter by customer code (Requirement 1.1, 1.2)
    - document_no: Filter by specific invoice number
    - posting_date: Filter by posting date
    - limit: Maximum number of invoices to return (default: 200)
    - return_line_items: If True, return line items with calculated quantities
    - project_only: If True, return only invoices with Project_No (not NULL)
    
    Returns:
    - If return_line_items=False: List of invoices sorted by posting date descending (Requirement 1.3)
      Each invoice includes: Document No., Posting Date, Total Amount (Requirement 1.2)
    - If return_line_items=True: List of all line items with product type and calculated quantities
      Each line includes: Document No., Posting Date, SKU, Description, Quantity, Unit of Measure, product_type, calculated quantities
    """
    rows = load_invoice_from_db(
        document_no=document_no,
        customer_no=customer_no,
        posting_date=posting_date,
        limit=limit,
        project_only=project_only,  # ⭐ ส่งพารามิเตอร์ไปยัง load_invoice_from_db
    )
    
    # If return_line_items is True, enrich with product type and calculated quantities
    if return_line_items:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        try:
            # Get all unique SKUs from invoice lines
            skus = list(set([row.get("sku") for row in rows if row.get("sku")]))
            
            if not skus:
                return rows
            
            # Fetch product info from Item_Master
            placeholders = ",".join(["?" for _ in skus])
            sql = f"""
                SELECT SKU, Product_Group, Variant_Mandatory, Product_Weight
                FROM Item_Master
                WHERE SKU IN ({placeholders})
            """
            cursor.execute(sql, skus)
            
            # Build SKU lookup map
            sku_info = {}
            for row in cursor.fetchall():
                sku_info[row[0]] = {
                    "product_group": row[1],
                    "variant_mandatory": row[2],
                    "product_weight": row[3] or 0,
                }
            
            # Enrich invoice lines with product type and calculated quantities
            from utils.invoice_quantity_calculator import calculate_line_item_quantity
            
            enriched_rows = []
            for row in rows:
                sku = row.get("sku")
                info = sku_info.get(sku, {})
                
                # Determine product type from SKU first character
                product_type = "Other"
                if sku and len(sku) > 0:
                    first_char = sku[0].upper()
                    if first_char == "G":
                        product_type = "Glass"
                    elif first_char == "A":
                        product_type = "Aluminum"
                
                # Calculate quantities
                quantity = int(row.get("Quantity") or 0)
                variant_mandatory = info.get("variant_mandatory", 1)
                description = row.get("Description", "")
                
                calculated = calculate_line_item_quantity(
                    product_type=product_type,
                    variant_mandatory=variant_mandatory,
                    sku=sku,
                    description=description,
                    quantity=quantity,
                )
                
                # Add calculated data to row
                row["product_type"] = product_type
                row["variant_mandatory"] = variant_mandatory
                row["product_weight"] = info.get("product_weight", 0)
                row["calculated_quantity"] = calculated
                
                enriched_rows.append(row)
            
            return enriched_rows
            
        except Exception as e:
            print(f"❌ Error enriching line items: {e}")
            import traceback
            traceback.print_exc()
            return rows
        finally:
            cursor.close()
            conn.close()
    
    # Transform to match frontend expectations (Requirement 1.2)
    result = []
    for row in rows:
        result.append({
            "document_no": row.get("Document No."),
            "posting_date": row.get("Posting Date"),
            "total_amount": row.get("Amount Including VAT", 0),
            "customer_code": row.get("customer_code"),
            "customer_name": row.get("Sell-to Customer Name"),
        })
    
    return result


# -------------------------------------------------------
# GET /api/invoice/item-price-history
# -------------------------------------------------------
@router.get("/item-price-history")
def item_price_history(
    sku: str = Query(...),
    customerCode: str = Query(...),
    limit: int = Query(10),
):
    """
    ดึงประวัติราคาสินค้าจาก MSSQL Database
    """
    conn = get_mssql_conn()
    cursor = conn.cursor()
    
    try:
        # ดึงข้อมูล 6 เดือนย้อนหลัง
        today = datetime.today()
        date_from = (today - timedelta(days=180)).date()
        
        sql = """
        SELECT TOP (?)
            Document_No,
            Posting_Date,
            Unit_Price,
            Quantity,
            Unit_of_Measure
        FROM dbo.Invoice
        WHERE sku = ? 
            AND customer_code = ?
            AND Posting_Date >= ?
        ORDER BY Posting_Date DESC
        """
        
        cursor.execute(sql, [limit, sku, customerCode, date_from])
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "invoiceNo": row[0],
                "date": row[1].isoformat() if row[1] else None,
                "price": float(row[2]) if row[2] else 0,
                "qty": int(row[3]) if row[3] else 0,
                "unit": row[4],
            })
        
        return results
        
    except Exception as e:
        print(f"❌ Error loading price history from database: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


# -------------------------------------------------------
# GET /api/invoice/{document_no}
# -------------------------------------------------------
@router.get("/{document_no}")
def get_invoice(document_no: str):
    """
    ดึงรายละเอียด Invoice จาก MSSQL Database
    
    Returns:
    - Invoice header with: document_no, posting_date, customer info, total amount
    - Line items with: SKU, product name, quantity, unit price, total price, description, variant code
    (Requirements: 2.1, 2.2, 7.2)
    """
    rows = load_invoice_from_db(document_no=document_no, limit=1000)

    if not rows:
        raise HTTPException(status_code=404, detail="Invoice not found")

    df = pd.DataFrame(rows)

    # สร้าง header จากแถวแรก
    first_row = df.iloc[0]
    header = {
        "document_no": document_no,
        "order_no": first_row.get("Order No."),
        "customer_no": first_row.get("customer_code"),
        "customer_name": first_row.get("Sell-to Customer Name"),
        "posting_date": first_row.get("Posting Date"),
        "amount_including_vat": float(df["Amount Including VAT"].fillna(0).sum()),
    }

    # สร้าง lines with all required fields (Requirement 2.1, 2.2)
    lines = []
    for _, r in df.iterrows():
        lines.append({
            "sku": r.get("sku"),
            "product_name": r.get("Description"),  # Product name from description
            "description": r.get("Description"),
            "unit": r.get("Unit of Measure"),
            "quantity": int(r.get("Quantity") or 0),
            "unit_price": float(r.get("Unit Price") or 0),
            "total_price": float(r.get("Amount") or 0),
            "variant_code": r.get("Variant Code"),
        })

    return {
        "header": header,
        "lines": lines,
    }
