# Step 6 Summary - API Flow Documentation

## 📋 สรุป API Calls ในแต่ละขั้นตอน

### 🔍 ขั้นตอนที่ 1: ใส่รหัสลูกค้า / ค้นหาลูกค้า

#### 1.1 ค้นหาลูกค้า (พิมพ์ในช่องค้นหา)
```javascript
POST /api/customer/search-list?q={searchTerm}
```
**เมื่อไหร่:** พิมพ์ชื่อหรือรหัสลูกค้า (debounce 300ms)

**Request:**
- Query Parameter: `q` (ชื่อหรือรหัสลูกค้า)

**Response:**
```json
[
  {
    "code": "C001",
    "name": "บริษัท ABC จำกัด",
    "gen_bus": "W",
    "paymentTerm": "NET 30",
    ...
  }
]
```

---

#### 1.2 โหลดข้อมูลลูกค้าแบบเต็ม (เลือกลูกค้าจาก dropdown)
```javascript
POST /api/customer/search?code={customerId}
```
**เมื่อไหร่:** คลิกเลือกลูกค้าจาก dropdown หรือใส่รหัสลูกค้าโดยตรง

**Request:**
- Query Parameter: `code` (รหัสลูกค้า)

**Response:**
```json
{
  "code": "C001",
  "name": "บริษัท ABC จำกัด",
  "gen_bus": "W",
  "customer_date": "2020-01-01",
  "accum_6m": 500000,
  "frequency": 12,
  "sales_g_cust": 300000,
  "sales_a_cust": 200000,
  "paymentTerm": "NET 30",
  "creditTerm": "NET 30",
  ...
}
```

---

### 📦 ขั้นตอนที่ 2: โหลดข้อมูลเพิ่มเติม (Auto-load หลังเลือกลูกค้า)

#### 2.1 โหลดประวัติการซื้อ
```javascript
GET /api/quotation?status=complete
```
**เมื่อไหร่:** หลังเลือกลูกค้า (auto-load)

**Response:**
```json
[
  {
    "id": "Q001",
    "customer": { "code": "C001", "name": "..." },
    "cart": [...],
    "total": 50000,
    "createdAt": "2024-01-15",
    ...
  }
]
```

**การกรอง:**
- กรองเฉพาะใบเสนอราคาของลูกค้าที่เลือก
- กรองเฉพาะที่มีสินค้าตรงกับตะกร้าปัจจุบัน (ถ้ามี)
- เรียงตามวันที่ล่าสุด
- แสดงเฉพาะ 5 รายการแรก

---

#### 2.2 โหลดรายการโครงการของลูกค้า
```javascript
GET /api/project-prices/by-customer?customerCode={customerCode}
```
**เมื่อไหร่:** หลังเลือกลูกค้า (auto-load)

**Request:**
- Query Parameter: `customerCode` (รหัสลูกค้า)

**Response:**
```json
[
  {
    "project_id": 1,
    "project_code": "PJ2605",
    "project_name": "โครงการคอนโด ABC",
    "price_start_date": "2026-05-01",
    "price_end_date": "2026-12-31",
    ...
  }
]
```

---

#### 2.3 โหลดโปรโมชั่นที่ใช้ได้ (ถ้ามีสินค้าในตะกร้า)
```javascript
GET /api/promotions/active-by-skus?skus={sku1,sku2,...}
```
**เมื่อไหร่:** หลังเลือกลูกค้า และมีสินค้าในตะกร้า

**Request:**
- Query Parameter: `skus` (รายการ SKU คั่นด้วย comma)

**Response:**
```json
[
  {
    "promotion_code": "PROMO001",
    "promotion_name": "ลดราคากระจกใส",
    "start_date": "2026-05-01",
    "end_date": "2026-05-31",
    "items": [
      {
        "sku": "G010101010101",
        "promotion_message": "โปรโมชั่น: ลดราคากระจกใส"
      }
    ]
  }
]
```

---

### 🛒 ขั้นตอนที่ 3: เพิ่มสินค้าลงตะกร้า

#### 3.1 ค้นหาสินค้า (Full Search)
```javascript
GET /api/items/search?q={searchTerm}
```
**เมื่อไหร่:** พิมพ์ชื่อหรือรหัสสินค้า (debounce 300ms, ขั้นต่ำ 3 ตัวอักษร)

**Request:**
- Query Parameter: `q` (ชื่อหรือรหัสสินค้า)

**Response:**
```json
[
  {
    "sku": "G010101010101",
    "name": "กระจกใส 5mm",
    "category": "G",
    "unit": "ตารางฟุต",
    "sqft_sheet": 12.5,
    ...
  }
]
```

---

#### 3.2 โหลดหมวดหมู่สินค้า (เปิด Item Picker Modal)
```javascript
GET /api/items/categories/list
```
**เมื่อไหร่:** เปิด Item Picker Modal

**Response:**
```json
[
  {
    "category": "G",
    "category_name": "กระจก",
    "count": 150
  },
  {
    "category": "A",
    "category_name": "อลูมิเนียม",
    "count": 200
  }
]
```

---

#### 3.3 โหลดรายการสินค้าตามหมวดหมู่ (Product Browser)
```javascript
GET /api/products/list?category={category}&offset={offset}&limit={limit}
```
**เมื่อไหร่:** เลือกหมวดหมู่ใน Product Browser

**Request:**
- Query Parameters:
  - `category`: หมวดหมู่สินค้า (G, A, C, Y, S, E)
  - `offset`: เริ่มต้นที่รายการที่ (pagination)
  - `limit`: จำนวนรายการต่อหน้า (default: 20)
  - `filters`: ตัวกรอง (brand, color, thickness, etc.)

**Response:**
```json
{
  "items": [
    {
      "sku": "G010101010101",
      "name": "กระจกใส 5mm",
      "category": "G",
      ...
    }
  ],
  "total": 150,
  "offset": 0,
  "limit": 20
}
```

---

### 💰 ขั้นตอนที่ 4: คำนวณราคา (Auto-calculate)

#### 4.1 คำนวณราคาสินค้าใหม่
```javascript
POST /api/pricing/calculate
```
**เมื่อไหร่:** 
- เพิ่ม/ลบ/แก้ไขสินค้าในตะกร้า
- เปลี่ยนลูกค้า
- เปลี่ยนประเภทการจัดส่ง (PICKUP/DELIVERY)
- เปลี่ยนค่าขนส่ง
- เลือก/เปลี่ยนโครงการ
- เปิด/ปิดใบกำกับภาษี

**Request:**
```json
{
  "customerData": {
    "customerCode": "C001",
    "customerName": "บริษัท ABC จำกัด",
    "paymentTerm": "NET 30",
    "paymentMethod": "CREDIT",
    "customer_date": "2020-01-01",
    "accum_6m": 500000,
    "frequency": 12,
    "gen_bus": "W",
    "sales_g_cust": 300000,
    "sales_a_cust": 200000,
    "sales_s_cust": 0,
    "sales_y_cust": 0,
    "sales_c_cust": 0,
    "sales_e_cust": 0,
    "shippingCustomerPay": 500,
    "project_id": 1
  },
  "deliveryType": "DELIVERY",
  "needTaxInvoice": false,
  "cart": [
    {
      "sku": "G010101010101",
      "name": "กระจกใส 5mm",
      "qty": 10,
      "sqft_sheet": 12.5,
      "cost": 80,
      "pkg_size": 1,
      "category": "G",
      "unit": "ตารางฟุต",
      "product_weight": 0,
      "isSoldByPack": false,
      "priceSource": "system",
      "UnitPrice": null,
      "isPromotion": false
    }
  ]
}
```

**Response:**
```json
{
  "items": [
    {
      "sku": "G010101010101",
      "name": "กระจกใส 5mm",
      "qty": 10,
      "sqft_sheet": 12.5,
      "unit": "ตารางฟุต",
      "UnitPrice": 125.50,
      "price_per_sheet": 1568.75,
      "_LineTotal": 15687.50,
      "_Tier_Z": "W2->W1",
      "product_weight": 0,
      "price_source": "system",
      "priceR2": 110,
      "priceR1": 120,
      "priceW2": 130,
      "priceW1": 140,
      "priceSDM": 150,
      "project_code": "",
      "project_name": "",
      "project_valid_until": ""
    }
  ],
  "totals": {
    "subtotal": 14660.75,
    "vat": 1026.25,
    "product_total": 15687.00,
    "shippingCustomerPay": 500,
    "total": 16187.00,
    "profit": 2500.00
  },
  "customer_tier": "W2->W1"
}
```

---

### 🚚 ขั้นตอนที่ 5: คำนวณค่าขนส่ง

#### 5.1 คำนวณค่าขนส่งจากตะกร้า
```javascript
POST /api/shipping/calculate_from_cart
```
**เมื่อไหร่:** 
- เปลี่ยนประเภทรถ
- เปลี่ยนระยะทาง
- เปลี่ยนเวลาขนของ
- เปลี่ยนจำนวนพนักงาน

**Request:**
```json
{
  "vehicle_type": "6W",
  "distance_km": 50,
  "unload_hours": 2,
  "staff_count": 2,
  "cart": [
    {
      "sku": "G010101010101",
      "qty": 10,
      "sqft_sheet": 12.5,
      "category": "G",
      "product_weight": 0
    }
  ]
}
```

**Response:**
```json
{
  "total_cost": 1500,
  "breakdown": {
    "base_cost": 1000,
    "distance_cost": 300,
    "unload_cost": 100,
    "staff_cost": 100
  },
  "vehicle_type": "6W",
  "distance_km": 50
}
```

---

### 💾 ขั้นตอนที่ 6: บันทึกใบเสนอราคา

#### 6.1 บันทึกเป็น Draft
```javascript
POST /api/quotation
```
**เมื่อไหร่:** คลิกปุ่ม "บันทึกแบบร่าง"

**Request:**
```json
{
  "status": "draft",
  "customer": {
    "code": "C001",
    "name": "บริษัท ABC จำกัด",
    ...
  },
  "cart": [...],
  "deliveryType": "DELIVERY",
  "shippingCustomerPay": 500,
  "needsTax": false,
  "project_code": "PJ2605",
  "project_name": "โครงการคอนโด ABC",
  "isPreOrder": false,
  "requiredDeliveryDate": null,
  "totals": {
    "subtotal": 14660.75,
    "vat": 1026.25,
    "total": 16187.00
  }
}
```

**Response:**
```json
{
  "id": "Q2026050001",
  "status": "draft",
  "createdAt": "2026-05-09T10:30:00Z",
  ...
}
```

---

#### 6.2 อัปเดต Draft ที่มีอยู่
```javascript
PUT /api/quotation/{id}
```
**เมื่อไหร่:** บันทึก Draft ที่เคยสร้างไว้แล้ว

**Request:** เหมือนกับ POST แต่ส่งไปที่ `/api/quotation/{id}`

---

#### 6.3 ส่งใบเสนอราคาไป Business Central
```javascript
POST /api/quotation
```
**เมื่อไหร่:** คลิกปุ่ม "ส่งไป Business Central"

**Request:**
```json
{
  "status": "open",
  "sendToBC": true,
  "customer": {...},
  "cart": [...],
  ...
}
```

**Response:**
```json
{
  "id": "Q2026050001",
  "status": "open",
  "bcQuoteNo": "SQ-2026-0001",
  "createdAt": "2026-05-09T10:30:00Z",
  ...
}
```

---

### 💵 ขั้นตอนที่ 7: ขอราคาพิเศษ (ถ้าแก้ไขราคาด้วยตนเอง)

#### 7.1 สร้างคำขอราคาพิเศษ
```javascript
POST /api/special-price-requests
```
**เมื่อไหร่:** แก้ไขราคาด้วยตนเอง และไม่ใช่โปรโมชั่น

**Request:**
```json
{
  "quote_no": "Q2026050001",
  "customer_code": "C001",
  "customer_name": "บริษัท ABC จำกัด",
  "items": [
    {
      "sku": "G010101010101",
      "item_name": "กระจกใส 5mm",
      "quantity": 10,
      "unit": "แผ่น",
      "normal_price": 150,
      "requested_price": 120,
      "approval_level": "ZM_THEN_RM"
    }
  ],
  "request_reason": "ลูกค้าขอส่วนลด",
  "valid_from": "2026-05-01",
  "valid_to": "2026-05-31"
}
```

**Response:**
```json
{
  "id": 1,
  "request_code": "SPR-2026-0001",
  "status": "PENDING_ZM",
  "approver_employee_id": "ZM_03TS",
  "created_at": "2026-05-09T10:30:00Z",
  ...
}
```

---

## 📊 สรุป API Endpoints ทั้งหมด

| ลำดับ | Endpoint | Method | เมื่อไหร่ | จุดประสงค์ |
|------|----------|--------|----------|-----------|
| 1 | `/api/customer/search-list` | POST | พิมพ์ค้นหาลูกค้า | ค้นหาลูกค้าจากชื่อหรือรหัส |
| 2 | `/api/customer/search` | POST | เลือกลูกค้า | โหลดข้อมูลลูกค้าแบบเต็ม |
| 3 | `/api/quotation` | GET | หลังเลือกลูกค้า | โหลดประวัติการซื้อ |
| 4 | `/api/project-prices/by-customer` | GET | หลังเลือกลูกค้า | โหลดรายการโครงการ |
| 5 | `/api/promotions/active-by-skus` | GET | หลังเลือกลูกค้า + มีสินค้า | โหลดโปรโมชั่น |
| 6 | `/api/items/search` | GET | พิมพ์ค้นหาสินค้า | ค้นหาสินค้า (Full Search) |
| 7 | `/api/items/categories/list` | GET | เปิด Item Picker | โหลดหมวดหมู่สินค้า |
| 8 | `/api/products/list` | GET | เลือกหมวดหมู่ | โหลดรายการสินค้า |
| 9 | `/api/pricing/calculate` | POST | เปลี่ยนแปลงตะกร้า/ลูกค้า | คำนวณราคา |
| 10 | `/api/shipping/calculate_from_cart` | POST | เปลี่ยนค่าขนส่ง | คำนวณค่าขนส่ง |
| 11 | `/api/quotation` | POST | บันทึก Draft | สร้างใบเสนอราคาใหม่ |
| 12 | `/api/quotation/{id}` | PUT | บันทึก Draft ที่มีอยู่ | อัปเดตใบเสนอราคา |
| 13 | `/api/special-price-requests` | POST | แก้ไขราคาด้วยตนเอง | สร้างคำขอราคาพิเศษ |

---

## 🔄 Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ใส่รหัสลูกค้า / ค้นหาลูกค้า                              │
│    ↓ POST /api/customer/search-list (ค้นหา)                │
│    ↓ POST /api/customer/search (โหลดข้อมูลเต็ม)             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Auto-load ข้อมูลเพิ่มเติม                                │
│    ↓ GET /api/quotation (ประวัติการซื้อ)                   │
│    ↓ GET /api/project-prices/by-customer (โครงการ)         │
│    ↓ GET /api/promotions/active-by-skus (โปรโมชั่น)        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. เพิ่มสินค้าลงตะกร้า                                      │
│    ↓ GET /api/items/search (ค้นหาสินค้า)                   │
│    ↓ GET /api/items/categories/list (หมวดหมู่)             │
│    ↓ GET /api/products/list (รายการสินค้า)                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. คำนวณราคา (Auto)                                         │
│    ↓ POST /api/pricing/calculate                           │
│    ← Response: ราคา, tier, totals                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. คำนวณค่าขนส่ง (ถ้าเป็น DELIVERY)                        │
│    ↓ POST /api/shipping/calculate_from_cart                │
│    ← Response: ค่าขนส่ง                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. บันทึกใบเสนอราคา                                         │
│    ↓ POST /api/quotation (Draft ใหม่)                      │
│    ↓ PUT /api/quotation/{id} (อัปเดต Draft)                │
│    ↓ POST /api/quotation (ส่งไป BC)                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. ขอราคาพิเศษ (ถ้าแก้ไขราคา)                              │
│    ↓ POST /api/special-price-requests                      │
│    ← Response: request_code, status                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Points

### 1. **Auto-calculate Pricing**
- ระบบจะคำนวณราคาอัตโนมัติทุกครั้งที่:
  - เพิ่ม/ลบ/แก้ไขสินค้า
  - เปลี่ยนลูกค้า
  - เปลี่ยนประเภทการจัดส่ง
  - เปลี่ยนค่าขนส่ง
  - เลือก/เปลี่ยนโครงการ

### 2. **Debounce**
- การค้นหาลูกค้า: 300ms
- การค้นหาสินค้า: 300ms

### 3. **Lazy Loading**
- รายการสินค้าใน Product Browser: โหลดทีละ 20 รายการ
- Infinite scroll สำหรับโหลดเพิ่ม

### 4. **Caching**
- ข้อมูลลูกค้าถูก cache ใน state
- ข้อมูลโครงการถูก cache ใน state
- ข้อมูลโปรโมชั่นถูก cache ใน state

### 5. **Error Handling**
- ทุก API call มี try-catch
- แสดง error message ให้ผู้ใช้เห็น
- Fallback เป็นค่าเริ่มต้นถ้า API ล้มเหลว

---

## 📝 หมายเหตุ

- เอกสารนี้สรุป API calls ใน Step 6 (Summary) เท่านั้น
- สำหรับ API endpoints อื่นๆ ดูที่ `backend/main.py`
- สำหรับรายละเอียดการคำนวณราคา ดูที่ `PRICING_EXECUTION_ORDER.md`
