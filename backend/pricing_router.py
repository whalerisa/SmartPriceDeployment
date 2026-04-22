import pandas as pd
import numpy as np
import math
import requests
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import List, Dict, Any

from LevelPrice import LevelPrice
from price import Price
from config.db_mssql import get_mssql_conn
from auth_dependency import get_branch_code


router = APIRouter(prefix="/api/pricing", tags=["pricing"])


# -------------------------------
#  MODELS
# -------------------------------
class CartItem(BaseModel):
    sku: str
    qty: float
    name: str
    price: float | None = None
    sqft_sheet: float | None = None
    isSoldByPack: bool = False  # ⭐ flag เพื่อบอก backend ว่าต้องคิดราคาแบบสินค้าปกติ
    
    pkg_size: float | None = None
    cost: float | None = None
    category: str | None = None
    unit: str | None = None
    product_weight: float | None = None
    relevantSales: float | None = None
    # ⭐ Manual price fields for special price requests
    priceSource: str | None = None  # "system", "manual", "project", "history"
    UnitPrice: float | None = None  # Manual unit price
    pricePerSqft: float | None = None  # Manual price per sqft (for glass)
    pricePerKg: float | None = None  # Manual price per kg (for aluminium)
    weight: float | None = None  # Manual weight (for aluminium)
    isPromotion: bool = False  # ⭐ Flag to indicate if price is promotion (no special price request needed)


class PricingRequest(BaseModel):
    customerData: Dict[str, Any]
    deliveryType: str
    cart: List[CartItem]
    needTaxInvoice: bool = False  # ⭐ เพิ่ม flag สำหรับใบกำกับภาษี


# -------------------------------
#  CATEGORY SALES MAPPING
# -------------------------------
def _num(x):
    try:
        v = pd.to_numeric(x, errors="coerce")
        return 0 if pd.isna(v) else float(v)
    except Exception:
        return 0



# -------------------------------
#  SAFE DEBUG
# -------------------------------
def _safe_print_df(df, cols, title):
    try:
        print("\n=== " + title)
        existing = [c for c in cols if c in df.columns]
        print(df[existing].head().to_string(index=False))
        print("===")
    except Exception:
        pass

def round_up_050(x: float) -> float:
    if x < 1:
        return round(x, 2)
    return math.ceil(x * 2) / 2


def calculate_tax_invoice_surcharge(item_count: int) -> float:
    """
    คำนวณค่าใบกำกับภาษี โดยแฝงเข้าไปในราคาต่อชิ้น
    
    ตรรมชาติ: บวก 10 บาท แต่แฝงเข้าไปในราคาต่อชิ้น
    - นำ 10 ÷ จำนวนสินค้า = ค่าต่อชิ้น
    - ถ้าหารไม่ลงตัว ให้ปัดขึ้นให้ลง .50 หรือ .00 เท่านั้น
    
    ตัวอย่าง:
    - 3 ชิ้น: 10 ÷ 3 = 3.33... → ปัดขึ้นเป็น 3.50
    - 4 ชิ้น: 10 ÷ 4 = 2.50 → ลงตัว ใช้ 2.50
    - 5 ชิ้น: 10 ÷ 5 = 2.00 → ลงตัว ใช้ 2.00
    - 6 ชิ้น: 10 ÷ 6 = 1.67... → ปัดขึ้นเป็น 2.00
    """
    if item_count <= 0:
        return 0.0
    
    # คำนวณค่าต่อชิ้น
    surcharge_per_item = 10.0 / item_count
    
    # ปัดขึ้นให้ลง .50 หรือ .00 เท่านั้น
    # วิธี: คูณ 2 → ปัดขึ้น → หาร 2
    rounded = math.ceil(surcharge_per_item * 2) / 2
    
    return rounded


def get_vat_rate() -> float:
    """
    ⭐ Get VAT rate from config (default 0.07 = 7%)
    """
    import os
    try:
        vat_rate_str = os.getenv("VAT_RATE", "0.07")
        vat_rate = float(vat_rate_str)
        return vat_rate
    except:
        return 0.07

# -------------------------------
#  MAIN ENDPOINT
# -------------------------------
@router.post("/calculate")
async def calculate_pricing(req: PricingRequest = Body(...), branch_code: str = Depends(get_branch_code)):

    # No items
    if not req.cart:
        return {"items": [], "subtotal": 0, "customer_tier": "N/A"}
    
    # ⭐ ไม่ต้องดึง product_group จาก SKU ตัวแรกแล้ว
    # จะใช้ category (อักษรตัวแรกของ SKU) ของแต่ละสินค้าแทน
    
    print(f"🔍 DEBUG: Branch Code from JWT: '{branch_code}'")
    print(f"🔍 DEBUG: All SKUs in cart: {[item.sku for item in req.cart]}")
    print(f"🔍 DEBUG: Customer Data keys: {list(req.customerData.keys())}")

    # ⭐ Load active special prices for customer
    special_prices_dict = {}
    customer_code = req.customerData.get('customerCode')
    if customer_code:
        try:
            conn = get_mssql_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    spri.item_code,
                    spri.requested_price
                FROM special_price_requests spr
                INNER JOIN special_price_request_items spri ON spr.id = spri.request_id
                WHERE spr.customer_code = ?
                    AND spr.status = 'APPROVED'
                    AND spr.valid_from IS NOT NULL
                    AND spr.valid_to IS NOT NULL
                    AND CAST(GETDATE() AS DATE) BETWEEN CAST(spr.valid_from AS DATE) AND CAST(spr.valid_to AS DATE)
                ORDER BY spr.approved_at DESC
            """, [customer_code])
            
            rows = cursor.fetchall()
            for row in rows:
                item_code = row[0]
                special_price = float(row[1])
                # เก็บเฉพาะรายการแรก (ล่าสุด) ของแต่ละ SKU
                if item_code not in special_prices_dict:
                    special_prices_dict[item_code] = special_price
                    print(f"💰 [SPECIAL PRICE] {item_code}: {special_price}")
            
            cursor.close()
            conn.close()
            
            if special_prices_dict:
                print(f"✅ [SPECIAL PRICE] Found {len(special_prices_dict)} active special prices for customer {customer_code}")
        except Exception as e:
            print(f"⚠️ [SPECIAL PRICE] Error loading special prices: {e}")

    # Load Items DB
    def load_items_by_skus(skus: list[str]) -> pd.DataFrame:
        if not skus:
            return pd.DataFrame()

        conn = get_mssql_conn()
        placeholders = ",".join(["?"] * len(skus))

        # Updated to use Item_Master + Item_Price with branch filtering
        sql = f"""
            SELECT
                im.SKU AS sku,
                im.No_2 AS sku2,
                LEFT(im.SKU, 1) AS category,
                im.Base_Unit_of_Measure,
                ip.PackageSize AS pkg_size,
                im.Product_Weight,
                0 AS Sqft_Sheet,
                ip.R1, ip.R2, ip.W1, ip.W2, ip.SDM,
                im.Product_Group,
                im.Product_Sub_Group,
                ip.AlternateName,
                0 AS RE
            FROM Item_Master im
            LEFT JOIN Item_Price ip ON im.SKU = ip.SKU AND ip.BranchCode = ?
            WHERE im.SKU IN ({placeholders})
        """

        # Add branch_code as first parameter, then SKUs
        params = [branch_code] + skus
        print(f"🔍 DEBUG SQL: branch_code='{branch_code}', skus={skus[:3]}...")  # Show first 3 SKUs
        df = pd.read_sql(sql, conn, params=params)
        conn.close()

        if df.empty:
            return df

        # normalize price columns (เหมือนของเดิม)
        for c in ["R1", "R2", "W1", "W2", "SDM"]:
            df[f"price{c}"] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        
        print(f"🔍 DEBUG: Loaded {len(df)} items, sample prices:")
        if not df.empty:
            print(df[["sku", "R2", "R1", "W2", "W1", "SDM", "priceR2", "priceR1", "priceW2", "priceW1", "priceSDM"]].head(3).to_string(index=False))

        df["pkg_size"] = pd.to_numeric(df.get("pkg_size"), errors="coerce").fillna(1)
        df["product_weight"] = pd.to_numeric(df.get("Product_Weight"), errors="coerce").fillna(0)

        return df


    # Cart → DataFrame
    df_calc = pd.DataFrame([item.model_dump() for item in req.cart])
    
    # ⭐ Debug: แสดงข้อมูลที่ได้รับจาก frontend
    print("\n" + "="*80)
    print("🔍 DEBUG: Cart items received from frontend")
    print("="*80)
    for idx, item in enumerate(req.cart):
        if item.priceSource == "manual":
            print(f"Item {idx}: SKU={item.sku}, priceSource=manual, UnitPrice={item.UnitPrice}")
        if item.category == "G":
            print(f"Item {idx}: SKU={item.sku}, isSoldByPack={item.isSoldByPack}, sqft_sheet={item.sqft_sheet}")
    print("="*80 + "\n")

    df_calc["Pieces"] = pd.to_numeric(df_calc["qty"], errors="coerce").fillna(0)

    # sqft_sheet (จาก FE) = ตารางฟุตต่อแผ่น (ถ้าไม่มีให้เป็น 0)
    df_calc["Sqft_Sheet"] = pd.to_numeric(df_calc.get("sqft_sheet", 0), errors="coerce").fillna(0)
    
    # isSoldByPack flag
    df_calc["isSoldByPack"] = df_calc.get("isSoldByPack", False).fillna(False).astype(bool)
    
    # ⭐ เก็บข้อมูล manual price ที่ได้รับจาก frontend
    df_calc["_manual_price"] = pd.to_numeric(df_calc.get("UnitPrice"), errors="coerce")
    df_calc["_manual_pricePerSqft"] = pd.to_numeric(df_calc.get("pricePerSqft"), errors="coerce")
    df_calc["_manual_pricePerKg"] = pd.to_numeric(df_calc.get("pricePerKg"), errors="coerce")
    df_calc["_manual_weight"] = pd.to_numeric(df_calc.get("weight"), errors="coerce")
    df_calc["_priceSource"] = df_calc.get("priceSource", "system")
    
    # ⭐ Debug log
    print("\n=== DEBUG: DataFrame after processing ===")
    print(df_calc[["sku", "isSoldByPack", "Pieces", "Sqft_Sheet", "_priceSource", "_manual_price"]])
    print("=== END DEBUG ===\n")


    # Category from SKU
    df_calc["category"] = (
        df_calc["category"]
        if "category" in df_calc.columns
        else df_calc["sku"].astype(str).str[0].str.upper()
    )
    
    df_calc["Quantity"] = np.where(
        df_calc["category"].astype(str).str.upper() == "G",
        np.where(
            df_calc["isSoldByPack"],              # ⭐ ถ้าขายยกแพ็ก
            df_calc["Pieces"],                    # ⭐ ไม่คูณ sqft
            df_calc["Pieces"] * df_calc["Sqft_Sheet"]  # ⭐ ปกติคูณ sqft
        ),
        df_calc["Pieces"]                        # ✅ อื่น ๆ: ชิ้น/เส้น
    )
    
    # ⭐ Debug: แสดง Quantity ที่คำนวณได้
    print("\n=== DEBUG: Quantity calculation ===")
    print(df_calc[["sku", "category", "isSoldByPack", "Pieces", "Sqft_Sheet", "Quantity"]])
    print("=== END DEBUG ===\n")


    # Attach customer data
    for k, v in req.customerData.items():
        df_calc[k] = v
    
    # ⭐ ไม่ต้องเพิ่ม product_group แบบเดิมแล้ว
    # จะใช้ category ของแต่ละสินค้าแทน

    df_calc["payment_terms"] = (
        req.customerData.get("payment_terms")
        or req.customerData.get("paymentTerm")   # ⭐ ต้องเพิ่มบรรทัดนี้
        or req.customerData.get("creditTerm")
        or req.customerData.get("CreditTerm")
        or ""
    )
    
    # ส่ง credit_terms ไปด้วย (ถ้ามี)
    df_calc["credit_terms"] = req.customerData.get("credit_terms", {})

    # ✅ FIX: โหลด items เฉพาะ SKU ใน cart
    cart_skus = df_calc["sku"].dropna().astype(str).unique().tolist()
    df_items = load_items_by_skus(cart_skus)

    if df_items.empty:
        raise HTTPException(500, "ไม่สามารถโหลด Item_Master ตาม SKU ใน cart")

    print("ITEMS COLUMNS =", df_items.columns.tolist())
    # Merge item data
    merge_cols = [
        "sku",
        "category",
        "RE",
        "product_weight",
        "priceR1", "priceR2", "priceW1", "priceW2", "priceSDM",
        "pkg_size",
        "Base_Unit_of_Measure",
    ]
    safe_merge_cols = [c for c in merge_cols if c in df_items.columns]


    # ✅ Ensure pkg_size exists and usable (priority: FE > master > 1)
    df_calc["pkg_size"] = pd.to_numeric(df_calc.get("pkg_size", 1), errors="coerce")

    if "pkg_size_y" in df_calc.columns:
        # ถ้า merge แล้วเกิดซ้ำชื่อ (มีทั้งจาก FE และ master)
        master_pkg = pd.to_numeric(df_calc["pkg_size_y"], errors="coerce")
        df_calc["pkg_size"] = df_calc["pkg_size"].fillna(master_pkg)

    df_calc["pkg_size"] = df_calc["pkg_size"].fillna(1)
    df_calc.loc[df_calc["pkg_size"] <= 0, "pkg_size"] = 1

    
    df_calc = df_calc.merge(df_items[safe_merge_cols], on="sku", how="left")
    if "Base Unit of Measure" in df_calc.columns:
        df_calc["unit"] = df_calc["Base Unit of Measure"]
    else:
        df_calc["unit"] = ""

    # ✅ FIX: normalize cost column ให้เป็น cost (ตามที่โค้ดด้านล่างใช้)
    if "Cost" in df_calc.columns and "cost" not in df_calc.columns:
        df_calc["cost"] = pd.to_numeric(df_calc["Cost"], errors="coerce").fillna(0)
    else:
        df_calc["cost"] = pd.to_numeric(df_calc.get("cost", 0), errors="coerce").fillna(0)



    print("\n=== AFTER MERGE UNIT CHECK ===")
    print(df_calc[["sku", "unit"]].head(10).to_string(index=False))
    print("=== END AFTER MERGE UNIT CHECK ===\n")



    # Normalize category
    if "category" not in df_calc.columns or df_calc["category"].isna().all():
        df_calc["category"] = df_calc["sku"].astype(str).str[0].str.upper()


    # Normal qty / Aluminium Weight
    # ensure product_weight exists and is numeric
    df_calc["product_weight"] = (
        pd.to_numeric(df_calc.get("product_weight_x"), errors="coerce")
        .fillna(pd.to_numeric(df_calc.get("product_weight_y"), errors="coerce"))
        .fillna(0)
    )
    # FIX: Aluminium ต้องมีน้ำหนักอย่างน้อย 1
    df_calc.loc[
        (df_calc["category"].astype(str).str.upper() == "A") &
        (df_calc["product_weight"] <= 0),
        "product_weight"
    ] = 1



    # DeliveryType
    df_calc["DeliveryType"] = "1" if req.deliveryType.upper() == "PICKUP" else "0"

    # -----------------------------
    # MAP relevantSales FROM CUSTOMER DATA (ตาม category ของแต่ละสินค้า)
    # -----------------------------
    # ⭐ คำนวณ relevantSales ตาม category (อักษรตัวแรกของ SKU) ของแต่ละสินค้า
    print(f"🔍 DEBUG: Calculating relevantSales per item based on category")
    
    def get_relevant_sales_for_category(row):
        """คำนวณ relevantSales ตาม category ของสินค้า"""
        category = row.get('category', None)
        
        if not category or category not in ['G', 'A', 'S', 'Y', 'C', 'E']:
            # Fallback: ใช้ relevantSales จาก FE ถ้ามี
            return row.get('relevantSales', 0)
        
        sales_key = f"sales_{category.lower()}_cust"
        sales_value = row.get(sales_key, 0)
        
        print(f"  SKU {row.get('sku', 'N/A')}: category={category} → {sales_key}={sales_value}")
        
        return sales_value
    
    # Apply ให้แต่ละแถว
    df_calc["_RelevantSales"] = df_calc.apply(get_relevant_sales_for_category, axis=1)
    df_calc["_RelevantSales"] = pd.to_numeric(df_calc["_RelevantSales"], errors="coerce").fillna(0)




    # -------------------------------------------------------------
    # DEFAULT MODE NORMALIZATION
    # -------------------------------------------------------------
    customer_code = str(
        req.customerData.get("customerCode")
        or req.customerData.get("code")
        or req.customerData.get("CustomerCode")
        or ""
    ).strip()

    customer_code_norm = customer_code.upper()

    IS_DEFAULT_MODE = (
        customer_code_norm == ""
        or customer_code_norm in ["N/A", "NA", "NONE", "NULL", "-"]
    )

    # ✅ ถ้าเป็น Default Mode → บังคับให้ customer_code ว่าง
    # เพื่อให้เข้า block pricing R2 ด้านล่าง
    if IS_DEFAULT_MODE:
        print("\n>>> DEFAULT PRICE MODE: NO CUSTOMER CODE → USE R2\n")
        customer_code = ""




    if not customer_code:
        print("\n>>> DEFAULT PRICE MODE: NO CUSTOMER CODE → USE R2\n")

        # Tier_Z = 0 means R2
        df_calc["_Tier_Z"] = 0

        # ใช้ราคา R2 โดยตรง
        df_calc["NewPrice"] = pd.to_numeric(df_calc["priceR2"], errors="coerce").fillna(0)

        # ราคาต่อเส้น (Aluminium) / ราคาต่อหน่วย (อื่นๆ)
        def _compute_unit_price_default(r):
            category = str(r.get("category", "")).upper()
            is_sold_by_pack = bool(r.get("isSoldByPack", False))
            
            if category == "A":
                # อลูมิเนียม: คูณน้ำหนัก (ไม่ปัดเศษ)
                raw = float(r["NewPrice"]) * float(r.get("product_weight", 0) or 0)
                return raw  # ⭐ อลูมิเนียมไม่ปัดเศษ
            elif category == "G" and is_sold_by_pack:
                # ⭐ กระจกขายยกแพ็ก: ใช้ NewPrice โดยตรง
                raw = float(r["NewPrice"])
            else:
                # อื่นๆ: ใช้ NewPrice โดยตรง
                raw = float(r["NewPrice"])
            
            return round_up_050(raw)  # ⭐ สินค้าอื่นๆปัดเศษ
        
        df_calc["UnitPrice"] = df_calc.apply(_compute_unit_price_default, axis=1)

        # ⭐ คำนวณ LineTotal (ปัดเศษ ยกเว้นอลูมิเนียม)
        def _compute_line_total_default(row):
            category = str(row.get("category", "")).upper()
            line_total = row["UnitPrice"] * row["Quantity"]
            
            if category == "A":
                return line_total  # อลูมิเนียมไม่ปัดเศษ
            else:
                return round_up_050(line_total)
        
        df_calc["LineTotal"] = df_calc.apply(_compute_line_total_default, axis=1)
        # ===== TOTAL CALC (MATCH NORMAL MODE) =====

        subtotal_gross = float(df_calc["LineTotal"].sum())

        shipping_customer_pay = float(
            req.customerData.get("shippingCustomerPay", 0) or 0
        )

        gross_before_vat = subtotal_gross + shipping_customer_pay

        # ⭐ คำนวณค่าใบกำกับภาษี (ถ้าลูกค้าต้องการ)
        tax_invoice_surcharge = 0.0
        if req.needTaxInvoice:
            item_count = len(df_calc)
            tax_invoice_surcharge = calculate_tax_invoice_surcharge(item_count)
            print(f"\n💰 [TAX INVOICE] Item count: {item_count}, Surcharge per item: {tax_invoice_surcharge} บาท")
            print(f"💰 [TAX INVOICE] Total surcharge: {tax_invoice_surcharge * item_count} บาท\n")
            
            # บวกค่าใบกำกับภาษีเข้าไปในราคา (แฝงเข้าไปในแต่ละชิ้น)
            df_calc["UnitPrice"] = df_calc["UnitPrice"] + tax_invoice_surcharge
            
            # ⭐ คำนวณ LineTotal ใหม่ (ปัดเศษ ยกเว้นอลูมิเนียม)
            def _compute_line_total_with_tax(row):
                category = str(row.get("category", "")).upper()
                line_total = row["UnitPrice"] * row["Quantity"]
                
                if category == "A":
                    return line_total  # อลูมิเนียมไม่ปัดเศษ
                else:
                    return round_up_050(line_total)
            
            df_calc["LineTotal"] = df_calc.apply(_compute_line_total_with_tax, axis=1)
            subtotal_gross = float(df_calc["LineTotal"].sum())
            gross_before_vat = subtotal_gross + shipping_customer_pay

        subtotal = float(round(gross_before_vat / (1 + get_vat_rate()), 2))
        vat = float(round(gross_before_vat - subtotal, 2))

        product_total = gross_before_vat
        total_final = product_total


        # -----------------------------
        # Profit (DEFAULT MODE)
        # -----------------------------
        if "cost" in df_calc.columns:
            df_calc["cost"] = pd.to_numeric(df_calc["cost"], errors="coerce").fillna(0)

            def _compute_profit_default(row):
                if str(row.get("category", "")).upper() == "A":
                    unit_cost = float(row["cost"]) * float(row.get("product_weight", 0) or 0)
                    return (row["UnitPrice"] - unit_cost) * row["Quantity"]
                return (row["NewPrice"] - row["cost"]) * row["Quantity"]

            profit = float(df_calc.apply(_compute_profit_default, axis=1).sum())
        else:
            profit = 0



        results = []
        for _, row in df_calc.iterrows():
            is_glass = str(row.get("category", "")).upper() == "G"
            is_sold_by_pack = bool(row.get("isSoldByPack", False))  # ⭐ เช็ค flag
            
            # ⭐ สำหรับกระจก:
            # - ถ้าขายยกแพ็ก: ใช้ UnitPrice โดยตรง
            # - ถ้าปกติ: คูณ sqft และปัดเศษ
            price_per_sheet = (
                row["UnitPrice"]  # ⭐ ขายยกแพ็ก
                if is_glass and is_sold_by_pack
                else round_up_050(row["UnitPrice"] * row.get("Sqft_Sheet", 0))
                if is_glass
                else row["UnitPrice"]
            )
            
            results.append({
                "sku": row["sku"],
                "name": row.get("name"),
                "qty": row.get("Pieces", row["Quantity"]),
                "sqft_sheet": row.get("Sqft_Sheet", 0),
                "unit": row.get("unit", ""),
                "UnitPrice": row["UnitPrice"],
                "price_per_sheet": price_per_sheet,
                "_LineTotal": row["LineTotal"],
                "_Tier_Z": 0,
                "product_weight": float(row.get("product_weight", 0) or 0),
                "priceR2": float(row.get("priceR2", 0) or 0),
                "priceR1": float(row.get("priceR1", 0) or 0),
                "priceW2": float(row.get("priceW2", 0) or 0),
                "priceW1": float(row.get("priceW1", 0) or 0),
                "priceSDM": float(row.get("priceSDM", 0) or 0),
                "priceSource": row.get("price_source", "system"),
                "isSoldByPack": is_sold_by_pack,  # ⭐ เพิ่ม flag
                "project_code": row.get("project_code", ""),  # ⭐ เพิ่ม project_code
                "project_name": row.get("project_name", ""),  # ⭐ เพิ่ม project_name
                "project_valid_until": row.get("project_valid_until", ""),  # ⭐ เพิ่ม project_valid_until
            })


        return {
            "items": results,
            "totals": {
                "subtotal": subtotal,
                "vat": vat,
                "product_total": product_total,
                "shippingCustomerPay": shipping_customer_pay,
                "total": total_final,
                "profit": profit,
            },
            "customer_tier": "R2",
        }


    # ⭐ HANDLE MANUAL PRICES (before normal pricing flow)
    # If user manually edited a price, use that instead of calculating
    print("\n" + "="*80)
    print("🔍 Checking for manually edited prices...")
    print("="*80)
    
    manual_price_items = []
    for idx, row in df_calc.iterrows():
        if row.get("priceSource") == "manual" and row.get("UnitPrice"):
            # ⭐ ถ้าเป็นโปรโมชั่น ไม่ต้องสร้าง special price request
            if row.get("isPromotion"):
                print(f"🎁 [PROMOTION] Skipping special price request for {row['sku']} (marked as promotion)")
                continue
            
            manual_price_items.append({
                "sku": row["sku"],
                "manual_price": row.get("UnitPrice"),
                "pricePerSqft": row.get("pricePerSqft"),
                "pricePerKg": row.get("pricePerKg"),
                "weight": row.get("weight"),
            })
            print(f"✅ Found manual price for {row['sku']}: {row.get('UnitPrice')} บาท")
    
    if manual_price_items:
        print(f"📝 Total items with manual prices: {len(manual_price_items)}")
    print("="*80 + "\n")

    # Store manual prices for later use
    df_calc["_manual_price"] = df_calc.apply(
        lambda row: row.get("UnitPrice") if row.get("priceSource") == "manual" else None,
        axis=1
    )
    df_calc["_manual_pricePerSqft"] = df_calc.apply(
        lambda row: row.get("pricePerSqft") if row.get("priceSource") == "manual" else None,
        axis=1
    )
    df_calc["_manual_pricePerKg"] = df_calc.apply(
        lambda row: row.get("pricePerKg") if row.get("priceSource") == "manual" else None,
        axis=1
    )
    df_calc["_manual_weight"] = df_calc.apply(
        lambda row: row.get("weight") if row.get("priceSource") == "manual" else None,
        axis=1
    )
    df_calc["_isPromotion"] = df_calc.apply(
        lambda row: row.get("isPromotion", False),
        axis=1
    )

    # =====================================================================
    # NORMAL FLOW (มี customer code → คำนวณด้วย LevelPrice, Price)
    # =====================================================================

    _safe_print_df(df_calc,
                   ["sku", "name", "Quantity", "priceR2", "priceR1", "priceW2", "priceW1", "priceSDM", "category"],
                   "AFTER MERGE ITEM DATA")
    
    # ⭐ ตรวจสอบว่าลูกค้าชื่อขึ้นต้นด้วย "ขายสด" → ใช้ R2 ตลอด
    customer_name = str(req.customerData.get("customerName", "")).strip()
    is_khaai_sod = customer_name.startswith("ขายสด")
    
    if is_khaai_sod:
        print(f"\n>>> SPECIAL CUSTOMER: '{customer_name}' starts with 'ขายสด' → FORCE R2 PRICING\n")

    
    # Run LevelPrice
    df_lp = LevelPrice(df_calc)
    
    df_lp["payment_terms"] = df_calc.get("payment_terms", "")
    df_lp["credit_terms"] = df_calc.get("credit_terms", {})

    # ⭐ ถ้าลูกค้าชื่อขึ้นต้นด้วย "ขายสด" → บังคับให้ใช้ R2 โดยตรง
    if is_khaai_sod:
        # ตั้งค่า NewPrice เป็น priceR2 โดยตรง (ข้าม Price function)
        df_lp["_ForceR2"] = True
        df_lp["_Tier_Z"] = "R2->R1"  # ตั้งค่า tier เป็น R2
        df_lp["tier"] = "R2->R1"
    else:
        df_lp["_ForceR2"] = False

    # 🔥 FIX: ส่ง column ที่ Price ต้องใช้ "ตั้งแต่ตรงนี้"
    price_input_cols = [
        "sku",
        "Quantity",
        "pkg_size",
        "_RelevantSales",
        "DeliveryType",
        "_ForceR2",  # ⭐ เพิ่ม flag สำหรับลูกค้า "ขายสด"
    ]

    # กันพลาด: ถ้า col ไหนไม่มี ให้สร้าง default
    for c in price_input_cols:
        if c not in df_lp.columns:
            if c == "pkg_size":
                df_lp[c] = 1
            elif c == "Quantity":
                df_lp[c] = 0
            elif c == "DeliveryType":
                df_lp[c] = "0"
            elif c == "_ForceR2":
                df_lp[c] = False

    # 👉 ตอนนี้ df_lp schema ตรงกับที่ Price.py ต้องการแล้ว
    df_price = Price(df_lp)
    
    # ⭐ Preserve manual price columns from df_calc
    if "_manual_price" in df_calc.columns:
        df_price["_manual_price"] = df_calc["_manual_price"].values
    if "_manual_pricePerSqft" in df_calc.columns:
        df_price["_manual_pricePerSqft"] = df_calc["_manual_pricePerSqft"].values
    if "_manual_pricePerKg" in df_calc.columns:
        df_price["_manual_pricePerKg"] = df_calc["_manual_pricePerKg"].values
    if "_manual_weight" in df_calc.columns:
        df_price["_manual_weight"] = df_calc["_manual_weight"].values
    
    # คำนวณ UnitPrice ก่อน (เพื่อใช้เปรียบเทียบกับราคาประวัติ)
    def _compute_unit_price_temp(row):
        category = str(row.get("category", "")).upper()
        
        if category == "A":
            # อลูมิเนียม: คูณน้ำหนัก (ไม่ปัดเศษ)
            raw = float(row["NewPrice"]) * float(row.get("product_weight", 0) or 0)
            return raw  # ⭐ อลูมิเนียมไม่ปัดเศษ
        else:
            raw = float(row["NewPrice"])
            return round_up_050(raw)  # ⭐ สินค้าอื่นๆปัดเศษ

    df_price["UnitPrice_temp"] = df_price.apply(_compute_unit_price_temp, axis=1)
    
    # ⭐ เพิ่ม: ตรวจสอบราคาโครงการก่อน (มีลำดับความสำคัญสูงสุด)
    # ดึง project_id จาก customerData (ถ้ามี)
    project_id = req.customerData.get("project_id")
    
    print(f"\n{'='*80}")
    if project_id:
        print(f"🏗️ เริ่มตรวจสอบราคาโครงการ ID: {project_id}")
    else:
        print(f"ℹ️ ไม่ได้เลือกโครงการ → ข้ามการตรวจสอบราคาโครงการ")
    print(f"{'='*80}")
    
    # Initialize price_source column
    df_price["price_source"] = "system"
    
    # 🔥 เฉพาะเมื่อมี project_id ถึงจะค้นหาราคาโครงการ
    if project_id:
        for idx, row in df_price.iterrows():
            sku = row["sku"]
            category = str(row.get("category", "")).upper()
            
            try:
                # ดึงราคาโครงการที่ active
                conn = get_mssql_conn()
                cursor = conn.cursor()
                
                sql = """
                SELECT TOP (1)
                    ph.project_code,
                    ph.project_name,
                    ph.price_start_date,
                    ph.price_end_date,
                    pl.price,
                    pl.unit,
                    pl.sku
                FROM Project_Price_Header ph
                JOIN Project_Price_Line pl ON ph.project_id = pl.project_id
                WHERE ph.project_id = ?
                    AND pl.sku = ?
                """
                cursor.execute(sql, [project_id, sku])
                
                result = cursor.fetchone()
                
                cursor.close()
                conn.close()
                
                if result:
                    project_code = result[0]
                    project_name = result[1] or ""
                    start_date = result[2].isoformat() if result[2] else "N/A"
                    end_date = result[3].isoformat() if result[3] else "N/A"
                    price = float(result[4]) if result[4] else 0
                    project_unit = result[5] or ""
                    sku_code = result[6] or ""
                    
                    # ตัดสินใจว่าใช้ราคาไหนตามประเภทสินค้า
                    category = sku_code[0].upper() if sku_code else ""
                    if category == "G":
                        project_price = price
                        price_type = "price_per_sqft"
                    elif category == "A":
                        project_price = price
                        price_type = "price_per_kg"
                    else:
                        project_price = price
                        price_type = "price"
                    
                    print(f"\n🏗️ SKU: {sku}")
                    print(f"   ✅ พบราคาโครงการ: {project_code} - {project_name}")
                    print(f"   💰 ราคา: {project_price:.2f} บาท/{project_unit} ({price_type})")
                    print(f"   📅 ระยะเวลา: {start_date} ถึง {end_date}")
                    
                    # ใช้ราคาโครงการทันที (ไม่ต้องเปรียบเทียบ)
                    df_price.at[idx, "NewPrice"] = project_price
                    df_price.at[idx, "price_source"] = "project"
                    df_price.at[idx, "project_code"] = project_code
                    df_price.at[idx, "project_name"] = project_name
                    df_price.at[idx, "project_valid_until"] = end_date
                else:
                    print(f"\n📦 SKU: {sku}")
                    print(f"   ℹ️ ไม่พบในโครงการนี้ → ใช้ราคาระบบ/ประวัติ")
                    
            except Exception as e:
                print(f"⚠️ ไม่สามารถตรวจสอบราคาโครงการสำหรับ SKU {sku}: {e}")
    
    print(f"{'='*80}")
    print(f"✅ ตรวจสอบราคาโครงการเสร็จสิ้น")
    print(f"{'='*80}\n")
    
    # ⭐ เพิ่ม: ตรวจสอบประวัติราคาและใช้ราคาครั้งก่อนถ้าสูงกว่าราคาระบบ (เฉพาะที่ไม่มีราคาโครงการ)
    print(f"\n{'='*80}")
    print(f"🔍 เริ่มตรวจสอบประวัติราคาสำหรับลูกค้า: {customer_code}")
    print(f"{'='*80}")
    
    for idx, row in df_price.iterrows():
        # ถ้ามีราคาโครงการแล้ว ข้ามไป
        if row.get("price_source") == "project":
            continue
            
        sku = row["sku"]
        category = str(row.get("category", "")).upper()
        system_price_base = float(row["NewPrice"])  # ราคาต่อหน่วยพื้นฐาน (กก./ตร.ฟุต/ชิ้น)
        system_price_display = float(row["UnitPrice_temp"])  # สำหรับแสดงผล
        
        # แสดงข้อมูลราคาระบบ
        if category == "A":
            product_weight = float(row.get("product_weight", 0) or 0)
            print(f"\n📦 SKU: {sku} (อลูมิเนียม)")
            print(f"   ราคาระบบ: {system_price_base:.2f} บาท/กก. (× {product_weight:.2f} กก./เส้น = {system_price_display:.2f} บาท/เส้น)")
        elif category == "G":
            sqft_sheet = float(row.get("Sqft_Sheet", 0) or 0)
            print(f"\n📦 SKU: {sku} (กระจก)")
            print(f"   ราคาระบบ: {system_price_base:.2f} บาท/ตร.ฟุต (× {sqft_sheet:.2f} ตร.ฟุต/แผ่น = {system_price_display:.2f} บาท/แผ่น)")
        else:
            print(f"\n📦 SKU: {sku} (หมวด {category})")
            print(f"   ราคาระบบ: {system_price_base:.2f} บาท/ชิ้น")
        
        try:
            # ดึงราคาล่าสุดจาก Database โดยตรง
            conn = get_mssql_conn()
            cursor = conn.cursor()
            
            # ดึงข้อมูล 6 เดือนย้อนหลัง
            today = datetime.today()
            date_from = (today - timedelta(days=180)).date()
            
            sql = """
            SELECT TOP (1)
                Posting_Date,
                Unit_Price,
                Quantity
            FROM dbo.Invoice
            WHERE sku = ? 
                AND customer_code = ?
                AND Posting_Date >= ?
                AND Unit_Price > 0
            ORDER BY Posting_Date DESC
            """
            
            cursor.execute(sql, [sku, customer_code, date_from])
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                last_date = result[0].isoformat() if result[0] else "N/A"
                last_price_invoice = float(result[1]) if result[1] else 0  # Unit_Price จาก Invoice (ราคาต่อเส้น/แผ่น/ชิ้น)
                last_qty = int(result[2]) if result[2] else 0
                
                # แปลงราคาจาก Invoice เป็นราคาต่อหน่วยพื้นฐาน (เพื่อเปรียบเทียบกับ NewPrice)
                if category == "A":
                    # อลูมิเนียม: หารด้วยน้ำหนักเพื่อได้ราคาต่อกิโลกรัม
                    product_weight = float(row.get("product_weight", 0) or 1)
                    if product_weight > 0:
                        last_price_base = last_price_invoice / product_weight
                        print(f"   📋 ประวัติการซื้อ: {last_price_invoice:.2f} บาท/เส้น = {last_price_base:.2f} บาท/กก. (วันที่ {last_date}, จำนวน {last_qty})")
                    else:
                        last_price_base = last_price_invoice
                        print(f"   📋 ประวัติการซื้อ: {last_price_invoice:.2f} บาท (วันที่ {last_date}, จำนวน {last_qty})")
                elif category == "G":
                    # กระจก: หารด้วย sqft_sheet เพื่อได้ราคาต่อตารางฟุต
                    sqft_sheet = float(row.get("Sqft_Sheet", 0) or 1)
                    if sqft_sheet > 0:
                        last_price_base = last_price_invoice / sqft_sheet
                        print(f"   📋 ประวัติการซื้อ: {last_price_invoice:.2f} บาท/แผ่น = {last_price_base:.2f} บาท/ตร.ฟุต (วันที่ {last_date}, จำนวน {last_qty})")
                    else:
                        last_price_base = last_price_invoice
                        print(f"   📋 ประวัติการซื้อ: {last_price_invoice:.2f} บาท (วันที่ {last_date}, จำนวน {last_qty})")
                else:
                    # สินค้าอื่นๆ: ใช้ราคาตรงๆ
                    last_price_base = last_price_invoice
                    print(f"   📋 ประวัติการซื้อ: {last_price_invoice:.2f} บาท/ชิ้น (วันที่ {last_date}, จำนวน {last_qty})")
                
                # ⭐ เปรียบเทียบราคาต่อหน่วยพื้นฐาน (กก./ตร.ฟุต/ชิ้น)
                if last_price_base > system_price_base:
                    print(f"   ✅ ใช้ราคาประวัติ {last_price_base:.2f} บาท (สูงกว่าราคาระบบ {system_price_base:.2f} บาท)")
                    df_price.at[idx, "NewPrice"] = last_price_base
                    df_price.at[idx, "price_source"] = "history"
                    df_price.at[idx, "last_purchase_date"] = last_date
                    df_price.at[idx, "last_purchase_qty"] = last_qty
                else:
                    print(f"   ℹ️ ใช้ราคาระบบ {system_price_base:.2f} บาท (ราคาประวัติ {last_price_base:.2f} บาท ต่ำกว่า)")
                    df_price.at[idx, "price_source"] = "system"
                    df_price.at[idx, "last_purchase_date"] = last_date
                    df_price.at[idx, "last_purchase_qty"] = last_qty
            else:
                print(f"   ℹ️ ไม่พบประวัติการซื้อ → ใช้ราคาระบบ {system_price_base:.2f} บาท")
                df_price.at[idx, "price_source"] = "system"
                df_price.at[idx, "last_purchase_date"] = None
                df_price.at[idx, "last_purchase_qty"] = None
                
        except Exception as e:
            print(f"⚠️ ไม่สามารถตรวจสอบประวัติราคาสำหรับ SKU {sku}: {e}")
            df_price.at[idx, "price_source"] = "system"
            df_price.at[idx, "last_purchase_date"] = None
            df_price.at[idx, "last_purchase_qty"] = None
    
    print(f"{'='*80}")
    print(f"✅ ตรวจสอบประวัติราคาเสร็จสิ้น")
    print(f"{'='*80}\n")


    # ⭐ FIX UNIT (Normal Mode)
    if "Base_Unit_of_Measure" in df_calc.columns:
        df_calc["unit"] = df_calc["Base_Unit_of_Measure"]
    else:
        df_calc["unit"] = ""



    print("\n=== AFTER PRICE UNIT CHECK ===")
    if "unit" in df_price.columns:
        print(df_price[["sku", "unit"]].head(10).to_string(index=False))
    else:
        print("⚠️ unit column NOT FOUND in df_price")
        print("columns =", list(df_price.columns))
    print("=== END AFTER PRICE UNIT CHECK ===\n")





    def _compute_unit_price(row):
        category = str(row.get("category", "")).upper()
        is_project_price = row.get("price_source") == "project"
        is_sold_by_pack = bool(row.get("isSoldByPack", False))  # ⭐ เช็ค flag
        
        if category == "A":
            # อลูมิเนียม: คูณน้ำหนัก (ไม่ปัดเศษ)
            raw = float(row["NewPrice"]) * float(row.get("product_weight", 0) or 0)
            return raw  # ⭐ อลูมิเนียมไม่ปัดเศษเลย
        elif category == "G" and is_sold_by_pack:
            # ⭐ กระจกขายยกแพ็ก: ใช้ NewPrice โดยตรง (ไม่คูณ sqft)
            raw = float(row["NewPrice"])
        else:
            # อื่นๆ (รวมกระจกปกติ): ใช้ NewPrice โดยตรง
            raw = float(row["NewPrice"])
        
        # ราคาโครงการไม่ต้องปัดเศษ ใช้ราคาเป๊ะๆ
        if is_project_price:
            return raw  # ⭐ ใช้ราคาเป๊ะๆ ไม่ปัดเศษเลย
        else:
            return round_up_050(raw)  # ⭐ ราคาระบบ/ประวัติ ปัดทีละ 0.50

    df_price["UnitPrice"] = df_price.apply(_compute_unit_price, axis=1)

    # ⭐ OVERRIDE WITH SPECIAL PRICES (highest priority)
    print("\n" + "="*80)
    print("💰 Applying special price overrides...")
    print("="*80)
    
    for idx, row in df_price.iterrows():
        sku = row["sku"]
        
        # ตรวจสอบราคาพิเศษก่อน
        if sku in special_prices_dict:
            special_price = special_prices_dict[sku]
            print(f"✅ [SPECIAL PRICE] Overriding price for {sku}: {row['UnitPrice']:.2f} → {special_price:.2f} บาท")
            df_price.at[idx, "UnitPrice"] = special_price
            df_price.at[idx, "price_source"] = "special"
            df_price.at[idx, "NewPrice"] = special_price
            df_price.at[idx, "priceSource"] = "special"  # เพิ่ม flag สำหรับ frontend
            continue  # ข้ามการตรวจสอบ manual price
    
    print("="*80 + "\n")

    # ⭐ OVERRIDE WITH MANUAL PRICES if provided (second priority)
    print("\n" + "="*80)
    print("🔍 Applying manual price overrides...")
    print("="*80)
    
    for idx, row in df_price.iterrows():
        sku = row["sku"]
        
        # ถ้ามีราคาพิเศษแล้ว ข้าม
        if row.get("price_source") == "special":
            continue
            
        manual_price = row.get("_manual_price")
        
        if manual_price and manual_price > 0:
            print(f"✅ Overriding price for {sku}: {row['UnitPrice']:.2f} → {manual_price:.2f} บาท")
            df_price.at[idx, "UnitPrice"] = manual_price
            df_price.at[idx, "price_source"] = "manual"
            df_price.at[idx, "NewPrice"] = manual_price  # Also update NewPrice for consistency
    
    print("="*80 + "\n")

    # ⭐ คำนวณ _LineTotal (ปัดเศษ ยกเว้นอลูมิเนียม)
    def _compute_line_total(row):
        category = str(row.get("category", "")).upper()
        line_total = row["UnitPrice"] * row["Quantity"]
        
        if category == "A":
            return line_total  # อลูมิเนียมไม่ปัดเศษ
        else:
            return round_up_050(line_total)
    
    df_price["_LineTotal"] = df_price.apply(_compute_line_total, axis=1)

    # ⭐ Debug: แสดง Quantity, UnitPrice, _LineTotal
    print("\n=== DEBUG: LineTotal calculation ===")
    print(df_price[["sku", "isSoldByPack", "Quantity", "UnitPrice", "_LineTotal"]])
    print("=== END DEBUG ===\n")

    _safe_print_df(df_price, ["sku", "NewPrice", "_LineTotal"], "AFTER PRICE CALC")

    # Prepare return values


# ยอดรวมสินค้า (ราคาขายรวม VAT แล้ว)
    subtotal_gross = float(df_price["_LineTotal"].sum())
    shipping_customer_pay = float(
        req.customerData.get("shippingCustomerPay", 0) or 0
    )

    # ⭐ คำนวณค่าใบกำกับภาษี (ถ้าลูกค้าต้องการ)
    tax_invoice_surcharge = 0.0
    if req.needTaxInvoice:
        item_count = len(df_price)
        tax_invoice_surcharge = calculate_tax_invoice_surcharge(item_count)
        print(f"\n💰 [TAX INVOICE] Item count: {item_count}, Surcharge per item: {tax_invoice_surcharge} บาท")
        print(f"💰 [TAX INVOICE] Total surcharge: {tax_invoice_surcharge * item_count} บาท\n")
        
        # บวกค่าใบกำกับภาษีเข้าไปในราคา (แฝงเข้าไปในแต่ละชิ้น)
        df_price["UnitPrice"] = df_price["UnitPrice"] + tax_invoice_surcharge
        
        # ⭐ คำนวณ _LineTotal ใหม่ (ปัดเศษ ยกเว้นอลูมิเนียม)
        def _compute_line_total_with_tax(row):
            category = str(row.get("category", "")).upper()
            line_total = row["UnitPrice"] * row["Quantity"]
            
            if category == "A":
                return line_total  # อลูมิเนียมไม่ปัดเศษ
            else:
                return round_up_050(line_total)
        
        df_price["_LineTotal"] = df_price.apply(_compute_line_total_with_tax, axis=1)
        subtotal_gross = float(df_price["_LineTotal"].sum())

    # 👉 รวมสินค้า + ค่าขนส่ง
    gross_before_vat = subtotal_gross + shipping_customer_pay

    # 👉 คิด VAT จากยอดรวม
    subtotal = float(round(gross_before_vat / (1 + get_vat_rate()), 2))
    vat = float(round(gross_before_vat - subtotal, 2))

    # 👉 ยอดสุทธิ
    product_total = gross_before_vat
    total_final = product_total


    # Profit
    if "cost" in df_price.columns:
        df_price["cost"] = pd.to_numeric(df_price["cost"], errors="coerce").fillna(0)
        def _compute_profit(row):
            if str(row.get("category", "")).upper() == "A":
                unit_cost = float(row.get("cost", 0)) * float(row.get("product_weight", 0) or 0)
                return (row["UnitPrice"] - unit_cost) * row["Quantity"]
            return (row["NewPrice"] - float(row.get("cost", 0))) * row["Quantity"]

        profit = float(df_price.apply(_compute_profit, axis=1).sum())

    else:
        profit = 0

    results = []
    for _, row in df_price.iterrows():
        
        is_glass = str(row.get("category", "")).upper() == "G"
        is_sold_by_pack = bool(row.get("isSoldByPack", False))  # ⭐ เช็ค flag

        # สำหรับกระจก: 
        # - ถ้าขายยกแพ็ก: ใช้ UnitPrice โดยตรง (ไม่คูณ sqft)
        # - ถ้าปกติ: UnitPrice เป็นราคาต่อตารางฟุต ต้องคูณ sqft เพื่อได้ราคาต่อแผ่น และปัดเศษ
        # สำหรับสินค้าอื่นๆ: ใช้ UnitPrice โดยตรง
        price_per_sheet = (
            row["UnitPrice"]  # ⭐ ขายยกแพ็ก: ใช้ราคาต่อหน่วยตรงๆ
            if is_glass and is_sold_by_pack
            else round_up_050(row["UnitPrice"] * row.get("Sqft_Sheet", 0))
            if is_glass
            else row["UnitPrice"]
        )

        results.append({
            "sku": row["sku"],
            "name": row.get("name"),
            "qty": row.get("Pieces", row["Quantity"]),
            "sqft_sheet": row.get("Sqft_Sheet", 0),
            "unit": row.get("unit", ""),
            "UnitPrice": row["UnitPrice"],
            "price_per_sheet": price_per_sheet,
            "_LineTotal": row["_LineTotal"],
            "_Tier_Z": row["_Tier_Z"],
            "product_weight": float(row.get("product_weight", 0) or 0),
            "price_source": row.get("price_source", "system"),
            "last_purchase_date": row.get("last_purchase_date"),
            "last_purchase_qty": row.get("last_purchase_qty"),
            "priceR2": float(row.get("priceR2", 0) or 0),
            "priceR1": float(row.get("priceR1", 0) or 0),
            "priceW2": float(row.get("priceW2", 0) or 0),
            "priceW1": float(row.get("priceW1", 0) or 0),
            "priceSDM": float(row.get("priceSDM", 0) or 0),
            "isSoldByPack": bool(row.get("isSoldByPack", False)),  # ⭐ เพิ่ม flag
            "isPromotion": bool(row.get("_isPromotion", False)),  # ⭐ เพิ่ม flag โปรโมชั่น
            "project_code": row.get("project_code", ""),  # ⭐ เพิ่ม project_code
            "project_name": row.get("project_name", ""),  # ⭐ เพิ่ม project_name
            "project_valid_until": row.get("project_valid_until", ""),  # ⭐ เพิ่ม project_valid_until
        })

    print(
    "\n=== PRODUCT WEIGHT CHECK ===\n",
    df_price[["sku", "product_weight"]].head().to_string(index=False)
)

    print("\n=== PRICING RESPONSE ITEMS (BACKEND) ===")
    for r in results:
        print(r["sku"], r.get("unit"))
    print("=== END PRICING RESPONSE ITEMS ===\n")
    
    # ⭐ Debug: แสดง project_code ที่ส่งกลับ
    project_items = [r for r in results if r.get("project_code")]
    if project_items:
        print("\n🏗️ [PRICING DEBUG] Items with project_code:")
        for r in project_items:
            print(f"  - SKU: {r['sku']}, Project Code: {r.get('project_code')}, Project Name: {r.get('project_name')}")
    else:
        print("\n⚠️ [PRICING DEBUG] No items with project_code found in response")
    print()

    # FIX: Sanitize NaNs for JSON compliance
    def sanitize(val):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return 0.0 # or None
        return val

    sanitized_results = [
        {k: sanitize(v) for k, v in item.items()}
        for item in results
    ]

    sanitized_totals = {
        "subtotal": sanitize(subtotal),
        "vat": sanitize(vat),
        "product_total": sanitize(product_total),
        "shippingCustomerPay": sanitize(shipping_customer_pay),
        "total": sanitize(total_final),
        "profit": sanitize(profit),
    }

    return {
        "items": sanitized_results,
        "totals": sanitized_totals,
        "customer_tier": results[0]["_Tier_Z"] if results else "N/A",
    }
