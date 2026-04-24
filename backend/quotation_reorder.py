# Reorder endpoint for quotation.py
# This file contains the reorder logic that should be added to quotation.py

#ดูว่าเอกสารใบเสนอราคาเวลาซื้อซ้ำหมดอายุหรือยัง

async def reorder_quotation_new(quote_no: str, branch_code: str):
    """
    ซื้อซ้ำจากใบเสนอราคา - คำนวณราคาใหม่ถ้าหมดอายุ
    """
    import httpx
    from config.db_mssql import get_mssql_conn
    from fastapi import HTTPException
    import json
    import logging
    from datetime import datetime
    
    logger = logging.getLogger(__name__)
    
    def row_to_dict(cursor, row):
        if row is None:
            return None
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    
    def normalize_keys(row: dict):
        return {k.strip(): v for k, v in row.items()}
    
    conn = get_mssql_conn()
    cursor = conn.cursor()

    # ดึงข้อมูลใบเสนอราคา
    cursor.execute("SELECT * FROM Quote_Header WHERE QuoteNo=?", (quote_no,))
    header = cursor.fetchone()
    if not header:
        conn.close()
        raise HTTPException(404, f"ไม่พบใบเสนอราคา {quote_no}")

    header = normalize_keys(row_to_dict(cursor, header))
    
    # ⭐ Debug: ดูว่า header มีอะไรบ้าง
    logger.info(f"🔍 [REORDER] Quote {quote_no} header keys: {list(header.keys())}")
    logger.info(f"🔍 [REORDER] project_code value: {header.get('project_code')}")
    logger.info(f"🔍 [REORDER] ProjectCode value: {header.get('ProjectCode')}")

    # ดึงรายการสินค้า
    cursor.execute("SELECT * FROM Quote_Line WHERE QuoteID=?", (quote_no,))
    lines = [normalize_keys(row_to_dict(cursor, r)) for r in cursor.fetchall()]

    # ตรวจสอบวันหมดอายุ
    expire_date_str = header.get("ExpireDate")
    is_expired = False
    days_expired = 0

    if expire_date_str:
        try:
            if isinstance(expire_date_str, str):
                expire_date = datetime.fromisoformat(expire_date_str.replace('Z', '+00:00'))
            else:
                expire_date = expire_date_str
            
            now = datetime.now()
            
            if now > expire_date:
                is_expired = True
                days_expired = (now - expire_date).days
                logger.info(f"Quote {quote_no} expired {days_expired} days ago")
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
        
        if not is_expired:
            item["price"] = ln["UnitPrice"]
            item["Price_System"] = ln.get("Price_System", 0)
            item["lineTotal"] = ln["TotalPrice"]
        
        if ln.get("CutInfoJson"):
            try:
                item["cutInfo"] = json.loads(ln["CutInfoJson"])
            except:
                item["cutInfo"] = ""
        
        cart_items.append(item)

    # ถ้าหมดอายุ ให้คำนวณราคาใหม่
    if is_expired:
        try:
            logger.info(f"🔄 Recalculating prices for expired quote {quote_no}")
            
            customer_code = header["CustomerCode"]
            
            # ดึงข้อมูลลูกค้าแบบเต็ม
            cursor.execute("""
                SELECT 
                    customer_code, customer_name, payment_terms, gen_bus,
                    customer_date, accum_6m, frequency,
                    sales_g_cust, sales_a_cust, sales_s_cust, 
                    sales_y_cust, sales_c_cust, sales_e_cust
                FROM Customer
                WHERE customer_code = ?
            """, (customer_code,))
            
            customer_row = cursor.fetchone()
            
            if customer_row:
                customer_data = {
                    "customerCode": customer_row[0],
                    "customerName": customer_row[1] or header["CustomerName"],
                    "paymentTerm": customer_row[2] or header.get("PaymentTerm", ""),
                    "paymentMethod": header.get("CreditTerm", ""),  # ใช้จาก header
                    "customer_date": str(customer_row[4]) if customer_row[4] else None,
                    "accum_6m": float(customer_row[5] or 0),
                    "frequency": int(customer_row[6] or 0),
                    "gen_bus": customer_row[3],
                    "sales_g_cust": float(customer_row[7] or 0),
                    "sales_a_cust": float(customer_row[8] or 0),
                    "sales_s_cust": float(customer_row[9] or 0),
                    "sales_y_cust": float(customer_row[10] or 0),
                    "sales_c_cust": float(customer_row[11] or 0),
                    "sales_e_cust": float(customer_row[12] or 0),
                }
            else:
                customer_data = {
                    "customerCode": customer_code,
                    "customerName": header["CustomerName"],
                }
            
            conn.close()
            
            # เตรียมข้อมูลสินค้า (ไม่ส่ง priceSource เพื่อให้คำนวณราคาใหม่)
            cart_for_pricing = [{
                "sku": it["sku"],
                "name": it["name"],
                "qty": it["qty"],
                "sqft_sheet": it.get("sqft_sheet", 0),
                "category": it["category"],
                "unit": it["unit"],
                "product_weight": it.get("product_weight", 0),
                "variantCode": it.get("variantCode", ""),
            } for it in cart_items]
            
            # เรียก pricing API
            async with httpx.AsyncClient(timeout=30.0) as client:
                pricing_response = await client.post(
                    "http://localhost:8000/api/pricing/calculate",
                    json={
                        "customerData": customer_data,
                        "deliveryType": header.get("ShippingMethod", "PICKUP"),
                        "needTaxInvoice": header.get("NeedsTax") == "Y",
                        "cart": cart_for_pricing,
                    }
                )
                
                if pricing_response.status_code == 200:
                    pricing_data = pricing_response.json()
                    priced_items = pricing_data.get("items", [])
                    
                    logger.info(f"✅ Pricing API returned {len(priced_items)} items")
                    
                    # อัพเดทราคาใหม่
                    for i, item in enumerate(cart_items):
                        if i < len(priced_items):
                            priced = priced_items[i]
                            
                            # ⭐ ใช้ price_per_sheet สำหรับกระจก (ราคาต่อตารางฟุต)
                            # ⭐ ใช้ UnitPrice สำหรับสินค้าอื่นๆ (อลูมิเนียม = ราคาต่อกิโล, สินค้าอื่น = ราคาต่อหน่วย)
                            category = item.get("category", "")
                            if category == "G" and priced.get("price_per_sheet"):
                                # กระจก: ใช้ price_per_sheet (ราคาต่อตารางฟุต)
                                item["price"] = priced.get("price_per_sheet", 0)
                            else:
                                # อลูมิเนียม (A): UnitPrice = ราคาต่อกิโล
                                # สินค้าอื่นๆ: UnitPrice = ราคาต่อหน่วย
                                item["price"] = priced.get("UnitPrice", 0)
                            
                            item["Price_System"] = priced.get("Price_System", 0)
                            
                            # ⭐ ใช้ _LineTotal จาก API (ถูกคำนวณแล้ว)
                            item["lineTotal"] = priced.get("_LineTotal", 0)
                            
                            logger.info(f"✅ {item['sku']}: price={item['price']}, lineTotal={item['lineTotal']}, cat={category}")
                else:
                    logger.error(f"❌ Pricing API failed: {pricing_response.status_code}")
                    for i, ln in enumerate(lines):
                        if i < len(cart_items):
                            cart_items[i]["price"] = ln["UnitPrice"]
                            cart_items[i]["Price_System"] = ln.get("Price_System", 0)
                            cart_items[i]["lineTotal"] = ln["TotalPrice"]
                    
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            for i, ln in enumerate(lines):
                if i < len(cart_items):
                    cart_items[i]["price"] = ln["UnitPrice"]
                    cart_items[i]["Price_System"] = ln.get("Price_System", 0)
                    cart_items[i]["lineTotal"] = ln["TotalPrice"]
            if conn:
                conn.close()
    else:
        conn.close()

    return {
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
        "daysExpired": days_expired if is_expired else 0,
    }
