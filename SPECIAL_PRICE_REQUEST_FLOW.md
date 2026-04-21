# 📊 Special Price Request Flow (Step6 → Backend)

## 🎯 ขั้นตอนการขอราคาพิเศษ

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 1: USER CLICKS "ขอราคาพิเศษ" BUTTON                │
│                         (Step6_Summary.jsx)                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Location: Line 2973 in Step6_Summary.jsx
┌─────────────────────────────────────────────────────────────────────────────┐
│ <button onClick={() => setShowSpecialPriceModal(true)}>                     │
│   ขอราคาพิเศษ                                                               │
│ </button>                                                                   │
└─────────────────────────────────────────────────────────────────────────────┘

Condition: ปุ่มนี้จะแสดงเมื่อ:
  ✓ มีสินค้าที่ราคา < R1 (itemsBelowR1.length > 0)
  ✓ ไม่มี rejected items (rejectedItems.length === 0)
  ✓ ไม่มี calculation error


┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 2: MODAL OPENS                                      │
│              (SpecialPriceRequestModal.jsx)                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Modal แสดง:
  1. ⚠️ Warning: "พบสินค้าที่ต้องขออนุมัติราคาพิเศษ"
  
  2. 👤 Approver Information (โหลดจาก API):
     GET /api/special-price-requests/approver-info
     └─ Response: {
        name: "ชื่อพนักงาน",
        employee_id: "EMP001",
        role: "Sales",
        branch_code: "00TR",
        can_approve: false
     }
  
  3. 📋 Approval Flow Info:
     - ขั้นที่ 1: Zone Manager (ZM) อนุมัติ
     - ขั้นที่ 2: Regional Manager (RM) อนุมัติ (ถ้าจำเป็น)
     - ขั้นที่ 3: Sales Development Manager (SDM) อนุมัติ (ถ้าจำเป็น)
     - ขั้นที่ 4: Product Manager (PM) อนุมัติ (ถ้าราคา < SDM)
  
  4. 📦 รายการสินค้าที่ต้องขออนุมัติ:
     ├─ SKU: G001
     ├─ ชื่อ: Glass 5mm
     ├─ จำนวน: 100 แผ่น
     ├─ ราคา R1: 500 บาท
     ├─ ราคาที่ขอ: 450 บาท
     └─ ระดับการอนุมัติ: ZM_ONLY
  
  5. 📅 วันที่เริ่มต้น (default: วันนี้)
  
  6. 📅 วันที่สิ้นสุด (default: 30 วันจากนี้)
  
  7. 📝 เหตุผลในการขอราคาพิเศษ (textarea)


┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 3: USER FILLS FORM & CLICKS "ส่ง"                   │
│              (SpecialPriceRequestModal.jsx → handleSubmit)                  │
└─────────────────────────────────────────────────────────────────────────────┘

Validation:
  ✓ reason.trim() !== ""
  ✓ validFrom && validTo ต้องมีค่า
  ✓ validFrom <= validTo
  ✓ rejectedItems.length === 0

เมื่อ validation ผ่าน:
  └─ เรียก onConfirm(reason, validFrom, validTo)
     └─ ซึ่งคือ handleSpecialPriceRequest() ใน Step6_Summary.jsx


┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 4: SAVE QUOTATION AS DRAFT                          │
│              (Step6_Summary.jsx → handleSpecialPriceRequest)                │
│                         Line 2207-2210                                      │
└─────────────────────────────────────────────────────────────────────────────┘

Code:
┌─────────────────────────────────────────────────────────────────────────────┐
│ const payload = buildQuotationPayload("open");                              │
│ const res = await saveQuotation(payload, state);                            │
│                                                                             │
│ if (res?.data) {                                                            │
│   dispatch({                                                                │
│     type: "SET_QUOTE_META",                                                 │
│     payload: {                                                              │
│       id: res.data.id,                                                      │
│       quoteNo: res.data.quoteNo,  // ⭐ ได้ quote_no ที่ใช้ต่อไป            │
│       status: res.data.status,                                              │
│     },                                                                      │
│   });                                                                       │
│ }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘

API Call:
  POST /api/quotation
  └─ Request: {
       customer_code: "CUST001",
       customer_name: "ชื่อลูกค้า",
       cart: [...],
       totals: {...},
       status: "open",
       ...
     }
  └─ Response: {
       id: 123,
       quoteNo: "QT-2024-001",
       status: "open",
       ...
     }


┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 5: CREATE SPECIAL PRICE REQUEST                     │
│              (Step6_Summary.jsx → handleSpecialPriceRequest)                │
│                         Line 2213-2235                                      │
└─────────────────────────────────────────────────────────────────────────────┘

Code:
┌─────────────────────────────────────────────────────────────────────────────┐
│ const specialPricePayload = {                                               │
│   quote_no: res.data.quoteNo,  // ⭐ ใช้ quote_no ที่ได้จากการบันทึก        │
│   customer_code: customerCode,                                              │
│   customer_name: state.customer?.name || "",                                │
│   customer_type: state.customer?.gen_bus || null,                           │
│   items: approvableItems.map(item => ({                                     │
│     sku: item.sku,                                                          │
│     item_name: item.name,                                                   │
│     quantity: Number(item.qty),                                             │
│     unit: item.unit,                                                        │
│     normal_price: item.r1_price,  // ⭐ ราคา R1                            │
│     requested_price: item.requested_price,  // ⭐ ราคาที่ขอ                │
│     approval_level: item.approval_level,  // ⭐ ZM_ONLY, ZM_THEN_RM, etc   │
│   })),                                                                      │
│   request_reason: reason,  // ⭐ เหตุผล                                     │
│   valid_from: validFrom,  // ⭐ วันที่เริ่มต้น                              │
│   valid_to: validTo,  // ⭐ วันที่สิ้นสุด                                   │
│ };                                                                          │
│                                                                             │
│ const specialPriceRes = await api.post(                                     │
│   '/api/special-price-requests',                                            │
│   specialPricePayload                                                       │
│ );                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘

API Call:
  POST /api/special-price-requests
  └─ Request: {
       quote_no: "QT-2024-001",
       customer_code: "CUST001",
       customer_name: "ชื่อลูกค้า",
       customer_type: "Retail",
       items: [
         {
           sku: "G001",
           item_name: "Glass 5mm",
           quantity: 100,
           unit: "แผ่น",
           normal_price: 500,
           requested_price: 450,
           approval_level: "ZM_ONLY"
         },
         ...
       ],
       request_reason: "ลูกค้าประจำ",
       valid_from: "2024-01-15",
       valid_to: "2024-02-15"
     }


┌─────────────────────────────────────────────────────────────────────────────┐
│                    BACKEND: SPECIAL PRICE REQUEST ROUTER                    │
│              (special_price_request_router.py)                              │
└─────────────────────────────────────────────────────────────────────────────┘

Endpoint: POST /api/special-price-requests
Function: create_special_price_request() (Line 485)

Flow:
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. VALIDATE INPUT                                                           │
│    ├─ Check: quote_no exists                                               │
│    ├─ Check: customer_code exists                                          │
│    ├─ Check: items not empty                                               │
│    └─ Check: valid_from <= valid_to                                        │
│                                                                             │
│ 2. LOAD CONFIG (⭐ ใช้ Config ที่ Admin ตั้งค่า)                            │
│    ├─ config = await get_config_settings()                                 │
│    │  └─ Query: SELECT config_value FROM system_config                     │
│    │     WHERE config_key = 'price_approval_config'                        │
│    │  └─ Fallback: get_default_config() (Sales: R1)                        │
│    │                                                                       │
│    └─ Extract: role_approval_scope from config                             │
│       ├─ Sales: { min_level: "R1" }                                        │
│       ├─ ZM: { min_level: "R1", max_level: "W2" }                          │
│       ├─ RM: { min_level: "W2", max_level: "W1" }                          │
│       ├─ SDM: { min_level: "W1", max_level: "SDM" }                        │
│       └─ PM: { min_level: "SDM" }                                          │
│                                                                             │
│ 3. DETERMINE APPROVAL LEVEL FOR EACH ITEM                                  │
│    ├─ For each item:                                                       │
│    │  ├─ Get: r1_price, w2_price, w1_price, sdm_price from Item_Price     │
│    │  ├─ Compare: requested_price กับ price thresholds                     │
│    │  └─ Determine: approval_level                                         │
│    │     ├─ ราคา >= R1 → ไม่ต้องขออนุมัติ (SKIP)                          │
│    │     ├─ R1 > ราคา >= W2 → ZM_ONLY                                      │
│    │     ├─ W2 > ราคา >= W1 → ZM_THEN_RM                                   │
│    │     ├─ W1 > ราคา >= SDM → SDM_APPROVAL                                │
│    │     └─ ราคา < SDM → PM_APPROVAL                                       │
│    │                                                                       │
│    └─ ⭐ ใช้ determine_approval_level() function (Line 103)                 │
│       ├─ Input: requested_price, r1_price, w2_price, w1_price, sdm_price  │
│       └─ Output: approval_level (string)                                   │
│                                                                             │
│ 4. CREATE SPECIAL PRICE REQUEST RECORD                                     │
│    ├─ INSERT INTO special_price_requests:                                  │
│    │  ├─ quote_no                                                          │
│    │  ├─ customer_code                                                     │
│    │  ├─ customer_name                                                     │
│    │  ├─ customer_type                                                     │
│    │  ├─ request_reason                                                    │
│    │  ├─ valid_from                                                        │
│    │  ├─ valid_to                                                          │
│    │  ├─ status: "PENDING_ZM" (เริ่มต้นรอ ZM อนุมัติ)                      │
│    │  ├─ created_by: current_employee_id                                   │
│    │  ├─ created_at: NOW()                                                 │
│    │  └─ approver_employee_id: ZM_position (เช่น "ZM_00TR")                │
│    │                                                                       │
│    └─ Get: request_id (auto-generated)                                     │
│                                                                             │
│ 5. CREATE SPECIAL PRICE REQUEST ITEMS                                      │
│    ├─ For each item:                                                       │
│    │  └─ INSERT INTO special_price_request_items:                          │
│    │     ├─ request_id                                                     │
│    │     ├─ sku                                                            │
│    │     ├─ item_name                                                      │
│    │     ├─ quantity                                                       │
│    │     ├─ unit                                                           │
│    │     ├─ normal_price (R1)                                              │
│    │     ├─ requested_price                                                │
│    │     ├─ approval_level (ZM_ONLY, ZM_THEN_RM, etc)                      │
│    │     └─ status: "PENDING"                                              │
│    │                                                                       │
│    └─ ⭐ approval_level ถูกบันทึกลงใน DB เพื่อใช้ในการอนุมัติ               │
│                                                                             │
│ 6. AUTO-SUBMIT REQUEST                                                     │
│    ├─ Call: await submit_request(request_id)                               │
│    │  └─ Update: status = "PENDING_ZM"                                     │
│    │  └─ Notify: ZM ว่ามีคำขอรอการอนุมัติ                                  │
│    │                                                                       │
│    └─ ⭐ ไม่ต้องให้ user กดปุ่ม submit อีก                                  │
│                                                                             │
│ 7. RETURN RESPONSE                                                          │
│    └─ {                                                                    │
│         "success": true,                                                   │
│         "request_id": 123,                                                 │
│         "quote_no": "QT-2024-001",                                          │
│         "status": "PENDING_ZM",                                             │
│         "message": "ส่งใบขอราคาพิเศษเรียบร้อยแล้ว"                         │
│       }                                                                    │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 6: FRONTEND HANDLES RESPONSE                        │
│              (Step6_Summary.jsx → handleSpecialPriceRequest)                │
│                         Line 2237-2240                                      │
└─────────────────────────────────────────────────────────────────────────────┘

Code:
┌─────────────────────────────────────────────────────────────────────────────┐
│ setShowSpecialPriceModal(false);  // ปิด modal                              │
│ alert('ส่งใบขอราคาพิเศษเรียบร้อยแล้ว\n' +                                  │
│       'ใบเสนอราคาถูกบันทึกเป็น Draft และรอการอนุมัติ');                     │
│ navigate("/quote-drafts");  // ไปหน้า Quote Drafts                          │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 7: APPROVAL FLOW                                    │
│              (SpecialPriceApproval.jsx)                                     │
└─────────────────────────────────────────────────────────────────────────────┘

Status Flow:
  PENDING_ZM
    ↓ (ZM approves)
  PENDING_RM (ถ้า approval_level = ZM_THEN_RM)
    ↓ (RM approves)
  PENDING_SDM (ถ้า approval_level = SDM_APPROVAL)
    ↓ (SDM approves)
  PENDING_PM (ถ้า approval_level = PM_APPROVAL)
    ↓ (PM approves)
  APPROVED
    ↓
  User สามารถยืนยันใบเสนอราคาได้


┌─────────────────────────────────────────────────────────────────────────────┐
│                    KEY POINTS                                               │
└─────────────────────────────────────────────────────────────────────────────┘

✅ Config ถูกอ่านจาก AdminConfig.jsx:
   - Sales: min_level = "R1" (ไม่ใช่ R2)
   - ZM: min_level = "R1", max_level = "W2"
   - RM: min_level = "W2", max_level = "W1"
   - SDM: min_level = "W1", max_level = "SDM"
   - PM: min_level = "SDM"

✅ approval_level ถูกคำนวณใน Backend:
   - ใช้ determine_approval_level() function
   - เปรียบเทียบ requested_price กับ price thresholds
   - บันทึกลงใน special_price_request_items.approval_level

✅ approval_level ถูกใช้ในการอนุมัติ:
   - ZM_ONLY: ต้องอนุมัติจาก ZM เท่านั้น
   - ZM_THEN_RM: ต้องผ่าน ZM → RM
   - SDM_APPROVAL: ต้องผ่าน ZM → RM → SDM
   - PM_APPROVAL: ต้องผ่าน ZM → RM → SDM → PM

✅ ไม่ต้องให้ user กดปุ่ม submit:
   - Backend auto-submit เมื่อสร้าง request
   - Status เปลี่ยนเป็น PENDING_ZM อัตโนมัติ

✅ Quote ถูกบันทึกเป็น Draft:
   - ก่อนส่งใบขอราคาพิเศษ
   - ใช้ quote_no ที่ได้จากการบันทึก
   - ไม่สามารถยืนยันจนกว่าได้รับการอนุมัติ
```

## 📝 Data Structure

### Request Payload (FE → BE)
```json
{
  "quote_no": "QT-2024-001",
  "customer_code": "CUST001",
  "customer_name": "ชื่อลูกค้า",
  "customer_type": "Retail",
  "items": [
    {
      "sku": "G001",
      "item_name": "Glass 5mm",
      "quantity": 100,
      "unit": "แผ่น",
      "normal_price": 500,
      "requested_price": 450,
      "approval_level": "ZM_ONLY"
    }
  ],
  "request_reason": "ลูกค้าประจำ",
  "valid_from": "2024-01-15",
  "valid_to": "2024-02-15"
}
```

### Database Records Created

**special_price_requests**
```
id: 123
quote_no: "QT-2024-001"
customer_code: "CUST001"
customer_name: "ชื่อลูกค้า"
customer_type: "Retail"
request_reason: "ลูกค้าประจำ"
valid_from: "2024-01-15"
valid_to: "2024-02-15"
status: "PENDING_ZM"
approver_employee_id: "ZM_00TR"
created_by: "EMP001"
created_at: NOW()
```

**special_price_request_items**
```
id: 456
request_id: 123
sku: "G001"
item_name: "Glass 5mm"
quantity: 100
unit: "แผ่น"
normal_price: 500
requested_price: 450
approval_level: "ZM_ONLY"
status: "PENDING"
```

## 🔄 Approval Logic (Backend)

```python
def determine_approval_level(
    requested_price: float,
    r1_price: float,
    w2_price: float,
    w1_price: float,
    sdm_price: float
) -> Optional[str]:
    """
    ราคา >= R1 → ไม่ต้องขออนุมัติ (None)
    R1 > ราคา >= W2 → ZM_ONLY
    W2 > ราคา >= W1 → ZM_THEN_RM
    W1 > ราคา >= SDM → SDM_APPROVAL
    ราคา < SDM → PM_APPROVAL
    """
    if requested_price >= r1_price:
        return None
    elif requested_price >= w2_price:
        return 'ZM_ONLY'
    elif requested_price >= w1_price:
        return 'ZM_THEN_RM'
    elif requested_price >= sdm_price:
        return 'SDM_APPROVAL'
    else:
        return 'PM_APPROVAL'
```
