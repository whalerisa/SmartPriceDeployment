# PRICING CALCULATION FLOW - ละเอียดจากโค้ดจริง

## 📊 ภาพรวม

```
Frontend: Step6_Summary.jsx
    ↓ (api.post("/api/pricing/calculate"))
Backend: pricing_router.py → calculate_pricing()
    ↓
For each item in cart:
    1. Load Item_Master data (SKU, category, prices)
    2. Check if customer is "ขายสด" (force R2)
    3. Run LevelPrice (calculate customer tier: R2→R1, R1→W2, etc.)
    4. Run Price (interpolate price based on tier & score)
    5. Check special price request (if approved & active)
    6. Check project price (if project_id provided)
    7. Check history price (last 6 months)
    8. Apply promotion (if isPromotion flag)
    9. Calculate tax invoice surcharge (if needTaxInvoice)
    10. Calculate line total & tax
    ↓
Return: { items, totals, price_validations }
```

---

## 🔄 STEP-BY-STEP FLOW

### STEP 1: FRONTEND REQUEST

**File:** `frontend/src/pages/CreateQuote/Step6_Summary.jsx`

```javascript
const res = await api.post("/api/pricing/calculate", {
  customerData: {
    customerCode: "CUST001",
    customerName: "บริษัท ABC",
    paymentTerm: "NET 30",
    accum_6m: 100000,
    frequency: 5,
    gen_bus: "RETAIL",
    sales_g_cust: 50000,  // ยอดขายกระจก 6 เดือน
    sales_a_cust: 30000,  // ยอดขายอลูมิเนียม 6 เดือน
    // ... other fields
    project_id: "PROJ123"  // ถ้ามีโครงการ
  },
  deliveryType: "DELIVERY",  // หรือ "PICKUP"
  needTaxInvoice: true,      // ต้องการใบกำกับภาษี
  cart: [
    {
      sku: "G01010010102014040",
      qty: 5,
      sqft_sheet: 3.89,
      category: "G",
      priceSource: "system",  // หรือ "manual"
      UnitPrice: 150,         // ถ้า manual
      isPromotion: false
    },
    // ... more items
  ]
});
```

---

### STEP 2: BACKEND INITIALIZATION

**File:** `backend/pricing_router.py` → `calculate_pricing()`

```python
@router.post("/calculate")
async def calculate_pricing(req: PricingRequest, branch_code: str = Depends(get_branch_code)):
    # 1. Validate cart
    if not req.cart:
        return {"items": [], "subtotal": 0}
    
    # 2. Load active special prices for customer
    special_prices_dict = {}
    if customer_code:
        # Query: SELECT * FROM special_price_requests 
        # WHERE customer_code = ? AND status = 'APPROVED' AND valid_from <= NOW() <= valid_to
        special_prices_dict = load_special_prices(customer_code)
    
    # 3. Convert cart to DataFrame
    df_calc = pd.DataFrame([item.model_dump() for item in req.cart])
    
    # 4. Load Item_Master data
    cart_skus = df_calc["sku"].unique().tolist()
    df_items = load_items_by_skus(cart_skus)  # Query Item_Master + Item_Price
    
    # 5. Merge cart with item data
    df_calc = df_calc.merge(df_items, on="sku", how="left")
```

---

### STEP 3: NORMALIZE DATA

```python
# 3.1 Calculate Quantity (ต่างกันตามประเภท)
df_calc["Quantity"] = np.where(
    df_calc["category"] == "G",  # กระจก
    np.where(
        df_calc["isSoldByPack"],           # ขายยกแพ็ก
        df_calc["Pieces"],                 # ไม่คูณ sqft
        df_calc["Pieces"] * df_calc["Sqft_Sheet"]  # คูณ sqft
    ),
    df_calc["Pieces"]  # อื่นๆ: ชิ้น/เส้น
)

# 3.2 Set DeliveryType
df_calc["DeliveryType"] = "1" if req.deliveryType == "PICKUP" else "0"

# 3.3 Map relevantSales by category
def get_relevant_sales_for_category(row):
    category = row.get('category')
    if category == 'G':
        return row.get('sales_g_cust', 0)  # ยอดขายกระจก
    elif category == 'A':
        return row.get('sales_a_cust', 0)  # ยอดขายอลูมิเนียม
    # ... etc
    return 0

df_calc["_RelevantSales"] = df_calc.apply(get_relevant_sales_for_category, axis=1)
```

---

### STEP 4: CHECK DEFAULT MODE (ลูกค้า "ขายสด")

```python
customer_code = _normalize_customer_code(req.customerData)
customer_name = str(req.customerData.get("customerName", "")).strip()
is_khaai_sod = customer_name.startswith("ขายสด")

if not customer_code or is_khaai_sod:
    # ✅ DEFAULT MODE: ใช้ R2 โดยตรง (ไม่คำนวณ tier)
    df_calc["_Tier_Z"] = 0  # 0 = R2
    df_calc["NewPrice"] = df_calc["priceR2"]  # ใช้ R2 ตรงๆ
    df_calc["UnitPrice"] = df_calc.apply(_compute_unit_price_helper, axis=1)
    
    # ⭐ ตรวจสอบ manual price
    for idx, row in df_calc.iterrows():
        if row.get("priceSource") == "manual" and row.get("UnitPrice"):
            # ตรวจสอบว่าต้องขออนุมัติหรือไม่
            if manual_price < r1_price:
                price_validations.append({
                    "sku": sku,
                    "is_below_r1": True,
                    "approval_level": "ZM_ONLY"
                })
    
    return {
        "items": results,
        "totals": totals,
        "customer_tier": "R2",
        "price_validations": price_validations
    }
```

---

### STEP 5: NORMAL MODE - RUN LEVELPRICE

**File:** `backend/LevelPrice.py`

```python
df_lp = LevelPrice(df_calc)
```

**LevelPrice ทำอะไร:**

1. **Calculate Customer Tier Score** (0-100)
   - Tenure Score: อายุลูกค้า (วันที่เป็นลูกค้า)
   - Accumulation Score: ยอดซื้อสะสม 6 เดือน
   - Frequency Score: ความถี่ในการซื้อ
   - Gen Bus Score: ประเภทลูกค้า (RETAIL, WHOLESALE, etc.)

2. **Map Score to Tier**
   ```
   Score 0-20   → R2 (ราคาสูงสุด)
   Score 20-40  → R1
   Score 40-60  → W2
   Score 60-80  → W1
   Score 80-100 → P (ราคาต่ำสุด)
   ```

3. **Output Columns**
   ```
   _Tier_Z: "R2->R1"  (tier range)
   _Score: 45.5       (customer score)
   priceR1, priceR2, priceW1, priceW2, priceP: (price thresholds)
   ```

**ตัวอย่าง:**
```
Customer: บริษัท ABC
- Tenure: 2 years → Score 75
- Accum_6m: 500,000 → Score 85
- Frequency: 20 times → Score 80
- Gen_Bus: RETAIL → Score 60

Average Score = (75 + 85 + 80 + 60) / 4 = 75
→ Tier = W1 (ราคาต่ำ)
```

---

### STEP 6: NORMAL MODE - RUN PRICE

**File:** `backend/price.py`

```python
df_price = Price(df_lp)
```

**Price ทำอะไร:**

1. **Calculate 3 Scores (0.0-1.0)**
   ```python
   qty_score = qty / pkg_size  # ปริมาณ vs แพ็ก
   e_score = log(relevant_sales) / 13  # ยอดขายตามประเภท
   ship_score = 1.0 if PICKUP else 0.0  # วิธีรับสินค้า
   
   total_score = (qty_score * 0.3382 + e_score * 0.3971 + ship_score * 0.2647)
   ```

2. **Interpolate Price**
   ```python
   # ตามที่ LevelPrice คำนวณ tier
   if tier == "R2->R1":
       low_price = priceR1
       high_price = priceR2
   elif tier == "R1->W2":
       low_price = priceW2
       high_price = priceR1
   # ... etc
   
   # Interpolate ตามคะแนน
   new_price = low_price + (high_price - low_price) * (1 - score)
   ```

3. **Apply Payment Term Markup**
   ```python
   term_markup = {
       0: 0.000,    # Cash: 0%
       15: 0.003,   # NET 15: +0.30%
       30: 0.006,   # NET 30: +0.60%
       45: 0.009,   # NET 45: +0.90%
       60: 0.012,   # NET 60: +1.20%
       90: 0.015,   # NET 90: +1.50%
   }
   
   new_price = new_price * (1 + term_markup[days])
   ```

**ตัวอย่าง:**
```
Item: G01010010102014040
- priceR2 = 200 (ราคาสูง)
- priceR1 = 180
- priceW2 = 160
- priceW1 = 140

Customer tier = W1 (score 75)
Interpolate: 140 + (160 - 140) * (1 - 0.75) = 140 + 5 = 145

Payment term = NET 30 (+0.60%)
Final price = 145 * 1.006 = 145.87
```

---

### STEP 7: CHECK SPECIAL PRICE REQUEST

```python
if project_id:
    for idx, row in df_price.iterrows():
        sku = row["sku"]
        
        # Query: SELECT * FROM special_price_requests 
        # WHERE customer_code = ? AND status = 'APPROVED' AND valid_from <= NOW() <= valid_to
        
        if special_price_found:
            df_price.at[idx, "NewPrice"] = special_price
            df_price.at[idx, "price_source"] = "special"
```

---

### STEP 8: CHECK PROJECT PRICE

```python
if project_id:
    for idx, row in df_price.iterrows():
        sku = row["sku"]
        
        # Query: SELECT * FROM Project_Price_Header ph
        # JOIN Project_Price_Line pl ON ph.project_id = pl.project_id
        # WHERE ph.project_id = ? AND pl.sku = ?
        
        if project_price_found:
            df_price.at[idx, "NewPrice"] = project_price
            df_price.at[idx, "price_source"] = "project"
            df_price.at[idx, "project_code"] = project_code
```

---

### STEP 9: CHECK HISTORY PRICE

```python
for idx, row in df_price.iterrows():
    if row.get("price_source") == "project":
        continue  # ข้ามถ้ามีราคาโครงการแล้ว
    
    sku = row["sku"]
    system_price = float(row["NewPrice"])
    
    # Query: SELECT TOP 1 * FROM Invoice_Line
    # WHERE sku = ? AND invoice_date >= DATEADD(day, -180, GETDATE())
    # ORDER BY invoice_date DESC
    
    if history_price_found and history_price > system_price:
        # ใช้ราคาประวัติถ้าสูงกว่าราคาระบบ
        df_price.at[idx, "NewPrice"] = history_price
        df_price.at[idx, "price_source"] = "history"
        df_price.at[idx, "last_purchase_date"] = invoice_date
```

---

### STEP 10: APPLY PROMOTION

```python
for idx, row in df_price.iterrows():
    if row.get("isPromotion"):
        # ใช้ราคา manual โดยตรง (ไม่ต้องขออนุมัติ)
        df_price.at[idx, "NewPrice"] = row.get("UnitPrice")
        df_price.at[idx, "price_source"] = "promotion"
```

---

### STEP 11: CALCULATE TAX INVOICE SURCHARGE

```python
if req.needTaxInvoice:
    item_count = len(df_price)
    
    # คำนวณค่าใบกำกับภาษี (10 บาท แฝงเข้าไปในราคา)
    surcharge_per_item = 10.0 / item_count
    
    # ปัดขึ้นให้ลง .50 หรือ .00 เท่านั้น
    rounded = math.ceil(surcharge_per_item * 2) / 2
    
    # ตัวอย่าง:
    # 3 items: 10 / 3 = 3.33 → ปัดขึ้นเป็น 3.50
    # 4 items: 10 / 4 = 2.50 → ลงตัว 2.50
    # 5 items: 10 / 5 = 2.00 → ลงตัว 2.00
    
    df_price["UnitPrice"] = df_price["UnitPrice"] + rounded
```

---

### STEP 12: CALCULATE LINE TOTAL & TAX

```python
# 12.1 Calculate LineTotal
def _compute_line_total_helper(row):
    category = str(row.get("category", "")).upper()
    line_total = row["UnitPrice"] * row["Quantity"]
    
    if category == "A":
        return line_total  # อลูมิเนียมไม่ปัดเศษ
    else:
        return round_up_050(line_total)  # ปัดทีละ 0.50

df_price["LineTotal"] = df_price.apply(_compute_line_total_helper, axis=1)

# 12.2 Calculate Totals
subtotal_gross = df_price["LineTotal"].sum()
gross_before_vat = subtotal_gross + shipping_customer_pay

vat_rate = 0.07  # 7%
subtotal = round(gross_before_vat / (1 + vat_rate), 2)
vat = round(gross_before_vat - subtotal, 2)
total = gross_before_vat

# 12.3 Calculate Profit
profit = sum((row["UnitPrice"] - row["cost"]) * row["Quantity"] for _, row in df_price.iterrows())
```

---

## 📋 PRICE PRIORITY ORDER

```
1. ✅ Manual Price (if priceSource == "manual" && not isPromotion)
   → ต้องขออนุมัติถ้าต่ำกว่า R1

2. ✅ Promotion Price (if isPromotion == true)
   → ใช้ได้เลย ไม่ต้องขออนุมัติ

3. ✅ Project Price (if project_id provided && found)
   → ใช้ราคาโครงการ

4. ✅ History Price (if found && higher than system price)
   → ใช้ราคาประวัติถ้าสูงกว่า

5. ✅ Special Price Request (if approved && active)
   → ใช้ราคาพิเศษที่อนุมัติแล้ว

6. ✅ System Price (LevelPrice + Price calculation)
   → ราคาเริ่มต้น
```

---

## 🎯 RETURN RESPONSE

```python
return {
    "items": [
        {
            "sku": "G01010010102014040",
            "name": "กระจก 14x40",
            "qty": 5,
            "sqft_sheet": 3.89,
            "UnitPrice": 145.87,
            "price_per_sheet": 567.50,
            "_LineTotal": 2837.50,
            "_Tier_Z": "W1->P",
            "price_source": "system",
            "priceR1": 180,
            "priceR2": 200,
            "priceW1": 140,
            "priceW2": 160,
            "project_code": "PROJ123",
            "project_name": "โครงการ ABC",
            "isPromotion": False,
        },
        # ... more items
    ],
    "totals": {
        "subtotal": 5000,
        "vat": 350,
        "total": 5350,
        "product_total": 5350,
        "shippingCustomerPay": 0,
        "profit": 1500,
    },
    "customer_tier": "W1",
    "price_validations": [
        {
            "sku": "A00123456789",
            "is_below_r1": True,
            "approval_level": "ZM_ONLY",
            "requested_price": 50,
            "r1_price": 100,
        }
    ]
}
```

---

## 🔍 KEY POINTS

### 1. Category-Specific Calculations
- **Glass (G)**: Quantity = Pieces × Sqft_Sheet (ยกเว้นขายยกแพ็ก)
- **Aluminium (A)**: Price = Price_per_kg × Weight (ไม่ปัดเศษ)
- **Others**: Quantity = Pieces (ชิ้น/เส้น)

### 2. Tier Calculation
- LevelPrice คำนวณ tier ตามคะแนนลูกค้า
- Price interpolate ราคาตามช่วง tier

### 3. Price Priority
- Manual > Promotion > Project > History > Special > System

### 4. Tax Invoice Surcharge
- 10 บาท แฝงเข้าไปในราคาต่อชิ้น
- ปัดขึ้นให้ลง .50 หรือ .00 เท่านั้น

### 5. Payment Term Markup
- NET 30 = +0.60%
- NET 60 = +1.20%
- NET 90 = +1.50%

---

## 📊 EXAMPLE CALCULATION

**Input:**
```
Customer: บริษัท ABC (tier W1)
Item: G01010010102014040
- Qty: 5 pieces
- Sqft_sheet: 3.89
- priceR2: 200
- priceR1: 180
- priceW2: 160
- priceW1: 140
- Payment term: NET 30
- Delivery: DELIVERY
```

**Calculation:**
```
1. LevelPrice: tier = W1 (score 75)
2. Price: interpolate = 140 + (160-140) * (1-0.75) = 145
3. Payment term: 145 * 1.006 = 145.87
4. Quantity: 5 * 3.89 = 19.45 sqft
5. LineTotal: 145.87 * 19.45 = 2,836.17 → ปัดขึ้น 2,837.50
6. Tax (7%): 2,837.50 / 1.07 = 2,650.47 (ex-vat)
7. VAT: 2,837.50 - 2,650.47 = 187.03
```

**Output:**
```
{
  "sku": "G01010010102014040",
  "UnitPrice": 145.87,
  "price_per_sheet": 567.50,
  "_LineTotal": 2837.50,
  "price_source": "system",
  "_Tier_Z": "W1->P"
}
```
