# Prompt สำหรับวาดแผนภาพการเชื่อมต่อระหว่างไฟล์โค้ด

## คำขอ
ช่วยสร้างแผนภาพการเชื่อมต่อระหว่างไฟล์โค้ด Frontend และ Backend ของระบบ Smart Pricing โดยแสดงให้เห็นว่า:
1. ไฟล์ Frontend ไหนเรียก API ไหน
2. API นั้นเชื่อมต่อกับไฟล์ Backend ไหน
3. ข้อมูลไหลไปมาอย่างไร
4. ถ้าไฟล์เดียวมี API หลายตัว ให้เขียนให้ครบทั้งหมด

---

## โครงสร้างโปรเจกต์

### Frontend
- **Main Page**: `frontend/src/pages/CreateQuote/Step6_Summary.jsx`
- **API Service**: `frontend/src/services/api.js`
- **Components**: 
  - `frontend/src/components/wizard/ItemPickerModal.jsx`
  - `frontend/src/components/wizard/CustomerSearchSection.jsx`
  - `frontend/src/components/wizard/GlassPickerModal.jsx`
  - `frontend/src/components/products/ProductList.jsx`
  - `frontend/src/components/cross-sell/CrossSellPanel.jsx`

### Backend
- **Main Entry**: `backend/main.py`
- **Router Files**:
  - `backend/items.py` - จัดการสินค้า
  - `backend/customer.py` - จัดการลูกค้า
  - `backend/pricing_router.py` - คำนวณราคา
  - `backend/quotation.py` - จัดการใบเสนอราคา
  - `backend/products_router.py` - จัดการสินค้า
  - `backend/project_price_router.py` - จัดการราคาโครงการ

---

## API Endpoints ที่ใช้ใน Step6_Summary.jsx

### 1. **API: `/api/items/search`**
- **ไฟล์ Frontend**: `frontend/src/pages/CreateQuote/Step6_Summary.jsx` (Line ~1100)
- **ไฟล์ Backend**: `backend/items.py` → `full_text_search_items()`
- **วิธีการ**: GET
- **Parameters**: 
  - `q` (string): คำค้นหาสินค้า
- **Response**: 
  - Array ของสินค้าที่ค้นหาได้
  - ข้อมูล: sku, name, price, category, inventory
- **ใช้ใน Component**: 
  - `ItemPickerModal.jsx`
  - `GlassPickerModal.jsx`
  - Product search dropdown

### 2. **API: `/api/items/{sku}/stock`**
- **ไฟล์ Frontend**: `frontend/src/services/api.js` → `getItemStock()`
- **ไฟล์ Backend**: `backend/items.py` → `get_item_stock()`
- **วิธีการ**: GET
- **Parameters**: 
  - `sku` (string): รหัสสินค้า
  - `branch_code` (string): รหัสสาขา (จาก dependency)
- **Response**: 
  - Stock information
  - ข้อมูล: sku, available_qty, reserved_qty, total_qty
- **ใช้ใน**: 
  - `useStep6Stock` hook
  - Stock display in cart

### 3. **API: `/api/items/categories/list`**
- **ไฟล์ Frontend**: `frontend/src/pages/CreateQuote/Step6_Summary.jsx` (Line ~800)
- **ไฟล์ Backend**: `backend/items.py` → `get_item_categories()`
- **วิธีการ**: GET
- **Parameters**: ไม่มี
- **Response**: 
  - Array ของหมวดหมู่สินค้า
  - ข้อมูล: name (G, A, C, Y, S, E), count
- **ใช้ใน**: 
  - `CategoryCard.jsx`
  - Category selector

### 4. **API: `/api/items/categories/{category_name}/list`**
- **ไฟล์ Frontend**: `frontend/src/pages/CreateQuote/Step6_Summary.jsx` (Line ~850)
- **ไฟล์ Backend**: `backend/items.py` → `get_items_list_light()`
- **วิธีการ**: GET
- **Parameters**: 
  - `category_name` (string): ชื่อหมวดหมู่ (G, A, C, Y, S, E)
  - `branch_code` (string): รหัสสาขา (จาก dependency)
- **Response**: 
  - Array ของสินค้าในหมวดหมู่
  - ข้อมูล: sku, name, price, unit, category
- **ใช้ใน**: 
  - `ProductList.jsx`
  - Category product listing

### 5. **API: `/api/items/{sku}`**
- **ไฟล์ Frontend**: `frontend/src/pages/CreateQuote/Step6_Summary.jsx` (Line ~900)
- **ไฟล์ Backend**: `backend/items.py` → `get_item_detail()`
- **วิธีการ**: GET
- **Parameters**: 
  - `sku` (string): รหัสสินค้า
  - `branch_code` (string): รหัสสาขา (จาก dependency)
- **Response**: 
  - ข้อมูลสินค้าแบบละเอียด
  - ข้อมูล: sku, name, prices (R1, R2, W1, W2), category, isVariant, sqft_sheet, product_weight
- **ใช้ใน**: 
  - `ProductDetail.jsx`
  - Item detail modal

### 6. **API: `/api/pricing/calculate`**
- **ไฟล์ Frontend**: `frontend/src/pages/CreateQuote/Step6_Summary.jsx` (Line ~200-400)
- **ไฟล์ Backend**: `backend/pricing_router.py` → `calculate_pricing()`
- **วิธีการ**: POST
- **Request Body**: 
  ```json
  {
    "customerData": {
      "customerCode": "string",
      "customerName": "string",
      "paymentTerm": "string",
      "paymentMethod": "string",
      "customer_date": "date",
      "accum_6m": "number",
      "frequency": "number",
      "gen_bus": "string",
      "sales_g_cust": "number",
      "sales_a_cust": "number",
      "sales_s_cust": "number",
      "sales_y_cust": "number",
      "sales_c_cust": "number",
      "sales_e_cust": "number",
      "shippingCustomerPay": "number",
      "project_id": "string or null"
    },
    "deliveryType": "string",
    "needTaxInvoice": "boolean",
    "cart": [
      {
        "sku": "string",
        "name": "string",
        "qty": "number",
        "sqft_sheet": "number",
        "cost": "number",
        "pkg_size": "number",
        "category": "string",
        "unit": "string",
        "product_weight": "number",
        "isSoldByPack": "boolean",
        "priceSource": "string (system or manual)",
        "UnitPrice": "number (if manual)",
        "pricePerSqft": "number (if manual)",
        "pricePerKg": "number (if manual)",
        "weight": "number (if manual)",
        "isPromotion": "boolean"
      }
    ]
  }
  ```
- **Response**: 
  ```json
  {
    "items": [
      {
        "sku": "string",
        "UnitPrice": "number",
        "price_source": "string",
        "priceR1": "number",
        "priceW2": "number",
        "priceW1": "number"
      }
    ],
    "totals": {
      "subtotal": "number",
      "vat": "number",
      "total": "number",
      "product_total": "number",
      "shippingCustomerPay": "number",
      "profit": "number"
    },
    "price_validations": [
      {
        "sku": "string",
        "status": "string",
        "message": "string"
      }
    ]
  }
  ```
- **ใช้ใน**: 
  - `useStep6Pricing` hook
  - Price calculation on cart change
- **เรียกใน 4 กรณี**:
  1. Draft + ไม่มีสินค้าใหม่ (คำนวณค่าใบกำกับภาษี)
  2. Draft + มีสินค้าใหม่ (คำนวณราคาสินค้าใหม่)
  3. ไม่มีสินค้าในตะกร้า (ไม่เรียก)
  4. ใบใหม่ทั้งหมด (คำนวณราคาใหม่ทั้งหมด)

### 7. **API: `/api/quotation?status=complete`**
- **ไฟล์ Frontend**: `frontend/src/pages/CreateQuote/Step6_Summary.jsx` (Line ~1200)
- **ไฟล์ Backend**: `backend/quotation.py` → `get_quotations()`
- **วิธีการ**: GET
- **Parameters**: 
  - `status` (string): สถานะใบเสนอราคา (complete)
- **Response**: 
  - Array ของใบเสนอราคาที่เสร็จสิ้น
  - ข้อมูล: id, customer, cart, createdAt, updatedAt
- **ใช้ใน**: 
  - `useStep6History` hook
  - Order history display
- **Logic**: 
  - Filter ตามรหัสลูกค้า
  - Filter ตามสินค้าในตะกร้าปัจจุบัน
  - Sort ตามวันที่ (ล่าสุดก่อน)
  - แสดงเฉพาะ 5 รายการล่าสุด

### 8. **API: `/api/project-prices/by-customer`**
- **ไฟล์ Frontend**: `frontend/src/pages/CreateQuote/Step6_Summary.jsx` (Line ~1300)
- **ไฟล์ Backend**: `backend/project_price_router.py` → `get_projects_by_customer()`
- **วิธีการ**: GET
- **Parameters**: 
  - `customerCode` (string): รหัสลูกค้า
- **Response**: 
  - Array ของโครงการของลูกค้า
  - ข้อมูล: project_id, project_code, project_name, customer_code
- **ใช้ใน**: 
  - Project selector dropdown
  - Auto-select project from draft
- **Logic**: 
  - Load projects เมื่อมีลูกค้า
  - Auto-select ถ้ามี project_code ใน state
  - Clear selection ถ้าไม่มี project_code

### 9. **API: `/api/customer/search`**
- **ไฟล์ Frontend**: `frontend/src/components/wizard/CustomerSearchSection.jsx`
- **ไฟล์ Backend**: `backend/customer.py` → `search_customer_from_db()`
- **วิธีการ**: GET
- **Parameters**: 
  - `code` (string): รหัสลูกค้า (optional)
  - `phone` (string): เบอร์โทรศัพท์ (optional)
  - `name` (string): ชื่อลูกค้า (optional)
  - `product_group` (string): กลุ่มสินค้า (optional)
- **Response**: 
  - Customer data with analytics
  - ข้อมูล: code, name, phone, paymentTerm, creditTerm, sales_g_cust, sales_a_cust, etc.
- **ใช้ใน**: 
  - `CustomerSearchSection.jsx`
  - Customer selection

### 10. **API: `/api/cross-sell/rules`**
- **ไฟล์ Frontend**: `frontend/src/components/cross-sell/CrossSellPanel.jsx`
- **ไฟล์ Backend**: `backend/cross_sell_router.py` → `get_cross_sell_rules()`
- **วิธีการ**: GET
- **Parameters**: 
  - `sku` (string): รหัสสินค้า
- **Response**: 
  - Array ของสินค้าที่แนะนำ
  - ข้อมูล: sku, name, category, displayName, ruleGroup
- **ใช้ใน**: 
  - Cross-sell recommendations
  - Related products

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                             │
│                                                                 │
│  Step6_Summary.jsx (Main Component)                            │
│  ├─ CustomerSearchSection.jsx                                  │
│  │  └─ API: /api/customer/search                              │
│  │                                                              │
│  ├─ ItemPickerModal.jsx                                        │
│  │  └─ API: /api/items/search                                 │
│  │                                                              │
│  ├─ GlassPickerModal.jsx                                       │
│  │  └─ API: /api/items/search                                 │
│  │                                                              │
│  ├─ ProductList.jsx                                            │
│  │  ├─ API: /api/items/categories/list                        │
│  │  └─ API: /api/items/categories/{category}/list             │
│  │                                                              │
│  ├─ ProductDetail.jsx                                          │
│  │  └─ API: /api/items/{sku}                                  │
│  │                                                              │
│  ├─ CrossSellPanel.jsx                                         │
│  │  └─ API: /api/cross-sell/rules                             │
│  │                                                              │
│  ├─ useStep6Stock Hook                                         │
│  │  └─ API: /api/items/{sku}/stock                            │
│  │                                                              │
│  ├─ useStep6Pricing Hook                                       │
│  │  └─ API: /api/pricing/calculate (POST)                     │
│  │                                                              │
│  ├─ useStep6History Hook                                       │
│  │  └─ API: /api/quotation?status=complete                    │
│  │                                                              │
│  └─ Project Selection                                          │
│     └─ API: /api/project-prices/by-customer                   │
│                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    (HTTP Requests)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│                                                                 │
│  main.py (Entry Point)                                         │
│  ├─ app.include_router(items_router, prefix="/api")           │
│  │  └─ items.py                                               │
│  │     ├─ GET /items/search                                   │
│  │     │  └─ full_text_search_items()                         │
│  │     ├─ GET /items/{sku}/stock                              │
│  │     │  └─ get_item_stock()                                 │
│  │     ├─ GET /items/categories/list                          │
│  │     │  └─ get_item_categories()                            │
│  │     ├─ GET /items/categories/{category}/list               │
│  │     │  └─ get_items_list_light()                           │
│  │     └─ GET /items/{sku}                                    │
│  │        └─ get_item_detail()                                │
│  │                                                              │
│  ├─ app.include_router(customer_router)                        │
│  │  └─ customer.py                                            │
│  │     └─ GET /api/customer/search                            │
│  │        └─ search_customer_from_db()                        │
│  │                                                              │
│  ├─ app.include_router(pricing_router)                         │
│  │  └─ pricing_router.py                                      │
│  │     └─ POST /api/pricing/calculate                         │
│  │        └─ calculate_pricing()                              │
│  │                                                              │
│  ├─ app.include_router(quotation_router, prefix="/api")       │
│  │  └─ quotation.py                                           │
│  │     └─ GET /api/quotation?status=complete                  │
│  │        └─ get_quotations()                                 │
│  │                                                              │
│  ├─ app.include_router(project_price_router)                  │
│  │  └─ project_price_router.py                                │
│  │     └─ GET /api/project-prices/by-customer                 │
│  │        └─ get_projects_by_customer()                       │
│  │                                                              │
│  └─ app.include_router(cross_sell_router, prefix="/api")      │
│     └─ cross_sell_router.py                                   │
│        └─ GET /api/cross-sell/rules                           │
│           └─ get_cross_sell_rules()                           │
│                                                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    (Database Queries)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE (MSSQL)                             │
│                                                                 │
│  Tables:                                                        │
│  ├─ Item_Master (สินค้า)                                       │
│  │  └─ SKU, Description, Price (R1, R2, W1, W2), Category     │
│  ├─ Customer (ลูกค้า)                                          │
│  │  └─ Code, Name, Phone, PaymentTerm, CreditTerm            │
│  ├─ Quotation (ใบเสนอราคา)                                    │
│  │  └─ ID, CustomerCode, Cart, Status, CreatedAt             │
│  ├─ ProjectPrice (ราคาโครงการ)                                │
│  │  └─ ProjectID, ProjectCode, CustomerCode, Prices          │
│  └─ CrossSellRules (กฎการขายเพิ่มเติม)                        │
│     └─ SKU, RelatedSKU, Category, DisplayName                 │
│                                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## ตัวอย่างการไหลของข้อมูล

### Scenario 1: ค้นหาสินค้า
```
User types "กระจก" in search box
    ↓
Step6_Summary.jsx: productSearch state updated
    ↓
useEffect triggers (debounce 300ms)
    ↓
api.get("/api/items/search", { params: { q: "กระจก" } })
    ↓
Backend: items.py → full_text_search_items("กระจก")
    ↓
Query: SELECT * FROM Item_Master WHERE Description LIKE '%กระจก%'
    ↓
Return: Array of matching items
    ↓
Frontend: setSearchResults(items)
    ↓
Display dropdown with results
```

### Scenario 2: คำนวณราคา
```
User adds item to cart or changes quantity
    ↓
state.cart updated
    ↓
useStep6Pricing hook detects change
    ↓
api.post("/api/pricing/calculate", { customerData, cart })
    ↓
Backend: pricing_router.py → calculate_pricing()
    ↓
For each item:
  - Get base price from Item_Master
  - Apply customer discount rules
  - Calculate tax if needed
  - Validate against project prices
    ↓
Return: { items, totals, price_validations }
    ↓
Frontend: setCalculation(result)
    ↓
Update cart with calculated prices
    ↓
Display totals (subtotal, VAT, total)
```

### Scenario 3: โหลดประวัติการซื้อ
```
Customer selected
    ↓
useStep6History hook triggers
    ↓
api.get("/api/quotation?status=complete")
    ↓
Backend: quotation.py → get_quotations()
    ↓
Query: SELECT * FROM Quotation WHERE Status = 'complete'
    ↓
Frontend: Filter by customer code
    ↓
Filter by items in current cart
    ↓
Sort by date (newest first)
    ↓
Take top 5
    ↓
Display in OrderHistoryCard
```

---

## สรุป API ตามไฟล์ Backend

### items.py (5 APIs)
1. `GET /items/search` - ค้นหาสินค้า
2. `GET /items/{sku}/stock` - ดึงสต็อก
3. `GET /items/categories/list` - ดึงหมวดหมู่
4. `GET /items/categories/{category}/list` - ดึงสินค้าตามหมวดหมู่
5. `GET /items/{sku}` - ดึงรายละเอียดสินค้า

### customer.py (1 API)
1. `GET /api/customer/search` - ค้นหาลูกค้า

### pricing_router.py (1 API)
1. `POST /api/pricing/calculate` - คำนวณราคา

### quotation.py (1 API)
1. `GET /api/quotation?status=complete` - ดึงใบเสนอราคา

### project_price_router.py (1 API)
1. `GET /api/project-prices/by-customer` - ดึงโครงการของลูกค้า

### cross_sell_router.py (1 API)
1. `GET /api/cross-sell/rules` - ดึงกฎการขายเพิ่มเติม

**รวมทั้งหมด: 10 APIs**

---

## หมายเหตุ
- ทุก API ใช้ authentication ผ่าน Bearer token ใน Authorization header
- ทุก API ใช้ branch_code จาก auth_dependency.get_branch_code()
- ทุก request ส่ง withCredentials: true เพื่อรับ Cookie
- Error handling ทั้ง Frontend และ Backend
