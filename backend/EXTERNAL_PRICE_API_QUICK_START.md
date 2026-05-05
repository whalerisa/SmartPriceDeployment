# External Price API - Quick Start Guide

## 🚀 เริ่มต้นใช้งานง่ายๆ

API สำหรับอัปเดตราคาสินค้า **ไม่ต้องใช้ API Key** เรียกใช้ได้เลย!

---

## 📡 Endpoints

Base URL: `http://your-server:8000/api/external/prices`

### 1. อัปเดตราคาเดี่ยว

```bash
curl -X POST "http://localhost:8000/api/external/prices/update" \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "G001234",
    "branch_code": "00TR",
    "r1": 120.00,
    "r2": 110.00,
    "w1": 140.00,
    "w2": 130.00
  }'
```

### 2. อัปเดตราคาแบบกลุ่ม (สูงสุด 10,000 รายการ)

```bash
curl -X POST "http://localhost:8000/api/external/prices/bulk-update" \
  -H "Content-Type: application/json" \
  -d '{
    "prices": [
      {"sku": "G001234", "branch_code": "00TR", "r1": 120.00, "r2": 110.00},
      {"sku": "G001235", "branch_code": "00TR", "r1": 240.00, "r2": 220.00}
    ],
    "uploaded_by": "my_system",
    "update_type": "G"
  }'
```

### 3. ตรวจสอบสถานะ

```bash
curl -X GET "http://localhost:8000/api/external/prices/status/123"
```

---

## 📝 ตัวอย่าง Python

```python
import requests

API_URL = "http://localhost:8000/api/external/prices"

# อัปเดตราคาเดี่ยว
response = requests.post(
    f"{API_URL}/update",
    json={
        "sku": "G001234",
        "branch_code": "00TR",
        "r1": 120.00,
        "r2": 110.00,
        "w1": 140.00,
        "w2": 130.00
    }
)

print(response.json())
# Output: {"success": true, "version_id": 123, ...}
```

---

## 📝 ตัวอย่าง JavaScript

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8000/api/external/prices';

// อัปเดตราคาเดี่ยว
const response = await axios.post(`${API_URL}/update`, {
  sku: 'G001234',
  branch_code: '00TR',
  r1: 120.00,
  r2: 110.00,
  w1: 140.00,
  w2: 130.00
});

console.log(response.data);
// Output: {success: true, version_id: 123, ...}
```

---

## 📋 Request Body Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| sku | string | ✅ | รหัส SKU |
| branch_code | string | ✅ | รหัสสาขา (เช่น "00TR") |
| r1 | float | ❌ | ราคาระดับ R1 |
| r2 | float | ❌ | ราคาระดับ R2 |
| w1 | float | ❌ | ราคาระดับ W1 |
| w2 | float | ❌ | ราคาระดับ W2 |
| sdm | float | ❌ | ราคาระดับ SDM |
| package_size | float | ❌ | ขนาดแพ็ค (default: 1) |
| alternate_name | string | ❌ | ชื่อสินค้าทางเลือก |

---

## ✅ Response Format

**Success:**
```json
{
  "success": true,
  "message": "Price updated successfully",
  "version_id": 123,
  "total_records": 1,
  "successful_updates": 1,
  "failed_updates": 0,
  "errors": []
}
```

**Error:**
```json
{
  "success": false,
  "message": "Bulk update completed: 1 successful, 1 failed",
  "version_id": 124,
  "total_records": 2,
  "successful_updates": 1,
  "failed_updates": 1,
  "errors": [
    "Record 2: SKU 'G999999' not found in Item_Master"
  ]
}
```

---

## 🧪 ทดสอบ API

รัน test script:
```bash
cd backend
python test_external_price_api.py
```

---

## ⚠️ ข้อควรระวัง

1. **SKU ต้องมีอยู่ใน Item_Master** - ถ้าไม่มีจะ skip และบันทึกใน errors
2. **Bulk update สูงสุด 10,000 รายการ** - ถ้ามากกว่าให้แบ่งเป็นหลาย request
3. **ใช้ใน internal network** - API ไม่มี authentication แนะนำให้ใช้ภายในเท่านั้น

---

## 📚 เอกสารเพิ่มเติม

อ่านคู่มือฉบับเต็มได้ที่: `EXTERNAL_PRICE_API_GUIDE.md`

---

## 🆘 Support

หากมีปัญหาหรือข้อสงสัย กรุณาติดต่อทีมพัฒนาระบบ
