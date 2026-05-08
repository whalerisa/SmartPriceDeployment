# 📋 เอกสารระบบโปรเจค (Project Price System)

## 🎯 ภาพรวม

ระบบโปรเจคเป็นส่วนหนึ่งของ Smart Pricing & Quotation System ที่ใช้สำหรับ:
- **จัดการราคาพิเศษสำหรับโครงการ** - กำหนดราคาสินค้าเฉพาะโครงการ
- **จัดการราคาตามสาขา** - กำหนดราคาสินค้าเฉพาะสาขา
- **จัดการราคาตามลูกค้า** - กำหนดราคาสินค้าเฉพาะลูกค้า (แคมเปญ)
- **อัพโหลดไฟล์โครงการ** - เก็บเอกสารที่เกี่ยวข้องกับโครงการ

---

## 📁 ไฟล์ที่เกี่ยวข้อง

### Backend Files

#### 1. **project_price_router.py** (API Router)
**ตำแหน่ง:** `backend/project_price_router.py`

**หน้าที่:**
- จัดการ API endpoints สำหรับระบบโปรเจค
- CRUD operations (Create, Read, Update, Delete)
- คำนวณและสร้างรหัสโครงการอัตโนมัติ
- กรองข้อมูลตามสิทธิ์ผู้ใช้

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/project-prices/` | สร้างราคาโครงการใหม่ |
| GET | `/api/project-prices/` | ดึงรายการโครงการทั้งหมด |
| GET | `/api/project-prices/next-code/{mode}` | ดึงรหัสโครงการถัดไป |
| GET | `/api/project-prices/active-by-customer-sku` | ดึงราคาโครงการที่ active |
| GET | `/api/project-prices/by-customer` | ดึงโครงการทั้งหมดของลูกค้า |
| GET | `/api/project-prices/project-prices/{project_id}` | ดึงราคาสินค้าในโครงการ |
| GET | `/api/project-prices/customer/{customer_code}/all` | ดึงโครงการทั้งหมดของลูกค้า (ไม่กรอง) |
| GET | `/api/project-prices/branch/{branch_code}/all` | ดึงโครงการทั้งหมดของสาขา |
| PUT | `/api/project-prices/{project_id}` | อัพเดทราคาโครงการ |
| PUT | `/api/project-prices/{project_id}/status` | อัพเดทสถานะโครงการ |
| DELETE | `/api/project-prices/{project_id}` | ลบโครงการ |

#### 2. **project_files_router.py** (File Upload Router)
**ตำแหน่ง:** `backend/project_files_router.py`

**หน้าที่:**
- จัดการการอัพโหลดไฟล์โครงการ
- เก็บไฟล์ในโฟลเดอร์ตามรหัสโครงการ
- รองรับไฟล์หลายประเภท (PDF, DOC, XLS, ZIP, รูปภาพ)

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/project-files/upload/{project_code}` | อัพโหลดไฟล์โครงการ |

**ไฟล์ที่รองรับ:**
- เอกสาร: `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.txt`
- ไฟล์บีบอัด: `.zip`, `.rar`
- รูปภาพ: `.jpg`, `.jpeg`, `.png`

#### 3. **pricing_router.py** (ส่วนที่เกี่ยวข้อง)
**ตำแหน่ง:** `backend/pricing_router.py`

**หน้าที่:**
- ตรวจสอบและใช้ราคาโครงการในการคำนวณราคา
- ราคาโครงการมีลำดับความสำคัญสูงกว่าราคาปกติ

**การทำงาน:**
```python
# ตรวจสอบราคาโครงการก่อน (มีลำดับความสำคัญสูงสุด)
if project_id:
    # ดึงราคาโครงการที่ active
    cursor.execute("""
        SELECT price FROM Project_Price_Line
        WHERE project_id = ? AND sku = ?
    """, [project_id, sku])
    
    if result:
        # ใช้ราคาโครงการ
        price = result['price']
        price_source = "project"
```

### Frontend Files

#### 1. **ProjectPrice.jsx** (หน้าหลัก)
**ตำแหน่ง:** `frontend/src/pages/ProjectPrice.jsx`

**หน้าที่:**
- หน้าหลักของระบบโปรเจค
- ตรวจสอบสิทธิ์การเข้าถึง
- แสดง ProjectPriceManagement component

**การตรวจสอบสิทธิ์:**
```javascript
// ตรวจสอบสิทธิ์จาก API
const res = await api.get("/api/config/page-access/check/project_price");
setHasAccess(res.data.has_access);
```

#### 2. **ProjectPriceManagement.jsx** (Component หลัก)
**ตำแหน่ง:** `frontend/src/pages/ProjectPriceManagement.jsx`

**หน้าที่:**
- จัดการ UI สำหรับสร้าง/แก้ไข/ลบโครงการ
- เลือกโหมดการสร้างโครงการ (Project/Branch/Customer)
- ค้นหาและเลือกสินค้าด้วย Filter
- อัพโหลดไฟล์โครงการ
- แสดงรายการโครงการทั้งหมด

**Features:**
- Multi-mode support (Project/Branch/Customer)
- Product filter (Category, Brand, Group, SubGroup, Color, Thickness)
- Bulk item addition (เพิ่มสินค้าหลาย SKU พร้อมกัน)
- File upload per project
- Auto/Manual project code generation
- Employee search and selection
- Date range validation

---

## 🔄 Flow การทำงาน

### 1. สร้างโครงการใหม่

```
┌─────────────────────────────────────────────────────────────┐
│ 1. เลือกโหมด (Project/Branch/Customer)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 2. กรอกข้อมูลโครงการ                                        │
│    - รหัสโครงการ (Auto/Manual)                              │
│    - ชื่อโครงการ/แคมเปญ                                     │
│    - รหัสลูกค้า (ถ้าเป็นโหมด Customer)                      │
│    - สาขา (ถ้าเป็นโหมด Branch)                              │
│    - วันที่เริ่มต้น - สิ้นสุด                               │
│    - ผู้ขอ (ค้นหาจากระบบ)                                   │
│    - หมายเหตุ                                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 3. เพิ่มสินค้า (2 วิธี)                                     │
│    A. เพิ่มทีละรายการ                                       │
│       - กรอก SKU, ชื่อสินค้า, หน่วย, ราคา, จำนวน          │
│    B. เพิ่มจาก Filter (Bulk)                                │
│       - เลือก Category, Brand, Group, etc.                  │
│       - ระบบแสดง SKU ที่ตรงเงื่อนไข                         │
│       - กรอกราคาและจำนวนเดียวสำหรับทุก SKU                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 4. อัพโหลดไฟล์ (Optional)                                   │
│    - เลือกไฟล์เอกสาร/รูปภาพ                                 │
│    - ระบบจะเก็บในโฟลเดอร์ตามรหัสโครงการ                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 5. บันทึก                                                    │
│    - Backend สร้างรหัสโครงการ (ถ้าเป็น Auto mode)          │
│    - บันทึกข้อมูลลง Database                                │
│    - อัพโหลดไฟล์ (ถ้ามี)                                    │
│    - แสดงเลขที่ใบคำขอ                                        │
└─────────────────────────────────────────────────────────────┘
```

### 2. การสร้างรหัสโครงการ

#### โหมด Auto (อัตโนมัติ)

**Project Mode:**
```
Format: PJYYMMXXX
- PJ = Project
- YY = ปี พ.ศ. 2 หลัก (เช่น 68 = 2568)
- MM = เดือน 2 หลัก (เช่น 04 = เมษายน)
- XXX = Running number 3 หลัก (001, 002, ...)

ตัวอย่าง: PJ6804001, PJ6804002
```

**Branch Mode:**
```
Format: BRYYMMXXX
- BR = Branch code 2 ตัวอักษร (เช่น TR, AY, CM)
- YY = ปี พ.ศ. 2 หลัก
- MM = เดือน 2 หลัก
- XXX = Running number 3 หลัก

ตัวอย่าง: TR6804001, AY6804002
```

**Customer Mode:**
```
Format: YYMMCUSTCODE
- YY = ปี พ.ศ. 2 หลัก
- MM = เดือน 2 หลัก
- CUSTCODE = รหัสลูกค้า (ไม่มี running number)

ตัวอย่าง: 680408015AY
```

#### โหมด Manual (กรอกเอง)

ผู้ใช้สามารถกรอกรหัสโครงการเองได้ ระบบจะตรวจสอบว่าซ้ำหรือไม่

### 3. การใช้ราคาโครงการในใบเสนอราคา

```
┌─────────────────────────────────────────────────────────────┐
│ 1. พนักงานสร้างใบเสนอราคา                                   │
│    - เลือกลูกค้า                                             │
│    - เลือกโครงการ (ถ้ามี)                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 2. เลือกสินค้า                                               │
│    - ระบบตรวจสอบว่ามีราคาโครงการหรือไม่                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 3. Backend คำนวณราคา (ลำดับความสำคัญ)                       │
│    1. ราคาโครงการ (ถ้ามี project_id)                        │
│    2. ราคาพิเศษที่อนุมัติแล้ว                                │
│    3. ราคาโปรโมชั่น                                          │
│    4. ราคาตามระดับลูกค้า (R2, R1, W2, W1, SDM)             │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 4. แสดงราคาและ price_source                                 │
│    - price_source = "project" → ราคาโครงการ                │
│    - แสดงชื่อโครงการและวันหมดอายุ                           │
└─────────────────────────────────────────────────────────────┘
```

### 4. การอัพโหลดไฟล์

```
┌─────────────────────────────────────────────────────────────┐
│ 1. เลือกไฟล์จากเครื่อง                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 2. ตรวจสอบนามสกุลไฟล์                                       │
│    - รองรับ: PDF, DOC, XLS, ZIP, รูปภาพ                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 3. อัพโหลดไปยัง Backend                                     │
│    POST /api/project-files/upload/{project_code}            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 4. Backend บันทึกไฟล์                                        │
│    - สร้างโฟลเดอร์: uploads/project_files/{project_code}/  │
│    - บันทึกไฟล์ด้วยชื่อเดิม                                 │
│    - Return file_path                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│ 5. แสดงผลลัพธ์                                               │
│    - แสดง path ที่บันทึก                                    │
│    - แสดงขนาดไฟล์                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗄️ Database Schema

### ตาราง Project_Price_Header

| Column | Type | Description |
|--------|------|-------------|
| project_id | INT | Primary Key (Auto increment) |
| project_code | VARCHAR(50) | รหัสโครงการ (Unique) |
| project_name | VARCHAR(255) | ชื่อโครงการ/แคมเปญ |
| customer_code | VARCHAR(50) | รหัสลูกค้า (Optional) |
| customer_name | VARCHAR(255) | ชื่อลูกค้า (Optional) |
| branch_code | VARCHAR(10) | รหัสสาขา (Optional) |
| price_start_date | DATE | วันที่เริ่มใช้ราคา |
| price_end_date | DATE | วันที่สิ้นสุด |
| request_by | VARCHAR(100) | ผู้ขอ |
| request_date | DATE | วันที่ขอ |
| status | VARCHAR(20) | สถานะ (active/expired/canceled) |
| remark | TEXT | หมายเหตุ |
| created_at | DATETIME | วันที่สร้าง |
| updated_at | DATETIME | วันที่อัพเดท |
| CreatedByEmployeeCode | VARCHAR(50) | รหัสพนักงานผู้สร้าง |

### ตาราง Project_Price_Line

| Column | Type | Description |
|--------|------|-------------|
| line_id | INT | Primary Key (Auto increment) |
| project_id | INT | Foreign Key → Project_Price_Header |
| sku | VARCHAR(50) | รหัสสินค้า |
| product_name | VARCHAR(255) | ชื่อสินค้า |
| unit | VARCHAR(50) | หน่วย |
| price | DECIMAL(18,2) | ราคา |
| quantity | DECIMAL(18,2) | จำนวน (Optional) |

---

## 🔐 สิทธิ์การเข้าถึง

### Role-Based Access Control

| Role | สิทธิ์ |
|------|--------|
| **Sales_Project** | สร้าง/แก้ไข/ดูโครงการของตนเอง |
| **PM** (Product Manager) | สร้าง/แก้ไข/ดู/อนุมัติโครงการทั้งหมด |
| **SDM** (Sales Director) | สร้าง/แก้ไข/ดู/อนุมัติโครงการทั้งหมด |
| **CEO** | เข้าถึงได้ทั้งหมด |
| **Admin** | เข้าถึงได้ทั้งหมด |

### การกรองข้อมูล

```python
# Backend กรองข้อมูลตาม employee_code
if employee_code:
    query += " AND CreatedByEmployeeCode = ?"
    params.append(employee_code)
```

---

## 📊 การใช้งานจริง

### Use Case 1: โครงการคอนโด

**สถานการณ์:**
- บริษัทรับเหมาต้องการราคาพิเศษสำหรับโครงการคอนโด
- มีสินค้าหลายประเภท (กระจก, อลูมิเนียม, ซีลแลนท์)
- ราคาใช้ได้ 3 เดือน

**ขั้นตอน:**
1. เลือกโหมด "Project"
2. กรอกชื่อโครงการ: "คอนโด ABC Tower"
3. เลือกลูกค้า: "บริษัท XYZ จำกัด"
4. กำหนดวันที่: 01/04/2568 - 30/06/2568
5. เพิ่มสินค้าด้วย Filter:
   - Category: Glass → Brand: Guardian → Type: Clear
   - กำหนดราคา: 180 บาท/ตร.ฟุต
6. อัพโหลดไฟล์: แบบโครงการ.pdf
7. บันทึก → ได้รหัส: PJ6804001

### Use Case 2: ราคาพิเศษสาขา

**สถานการณ์:**
- สาขาเชียงใหม่ต้องการราคาพิเศษสำหรับสินค้าบางรายการ
- ใช้ได้กับลูกค้าทุกรายในสาขา
- ราคาใช้ได้ 1 เดือน

**ขั้นตอน:**
1. เลือกโหมด "Branch"
2. กรอกชื่อ: "โปรโมชั่นสาขาเชียงใหม่ เมษายน 2568"
3. เลือกสาขา: เชียงใหม่ (CM)
4. กำหนดวันที่: 01/04/2568 - 30/04/2568
5. เพิ่มสินค้า: กระจกเทมเปอร์ 8mm
6. บันทึก → ได้รหัส: CM6804001

### Use Case 3: แคมเปญลูกค้า

**สถานการณ์:**
- ลูกค้า VIP ได้รับราคาพิเศษสำหรับแคมเปญ
- ใช้ได้เฉพาะลูกค้ารายนี้
- ราคาใช้ได้ 6 เดือน

**ขั้นตอน:**
1. เลือกโหมด "Customer"
2. กรอกชื่อแคมเปญ: "VIP Discount 2568"
3. เลือกลูกค้า: 08015AY
4. กำหนดวันที่: 01/04/2568 - 30/09/2568
5. เพิ่มสินค้าหลาย SKU ด้วย Filter
6. บันทึก → ได้รหัส: 680408015AY

---

## 🔧 Configuration

### Environment Variables

```bash
# Project Code Mode
PROJECT_CODE_MODE=auto  # auto | manual

# File Storage
PROJECT_FILES_FOLDER=./uploads/project_files

# Access Control
ALLOWED_PROJECT_PRICE_EMPLOYEES=EMP001,EMP002,EMP003
```

### Page Access Configuration

```json
{
  "project_price": {
    "page_name": "project_price",
    "page_label": "สร้างรหัสโครงการ",
    "allowed_roles": ["Sales_Project", "PM", "SDM", "CEO", "Admin"]
  }
}
```

---

## 🐛 Troubleshooting

### ปัญหาที่พบบ่อย

#### 1. ไม่สามารถสร้างโครงการได้

**สาเหตุ:**
- ไม่มีสิทธิ์เข้าถึง
- รหัสโครงการซ้ำ (Manual mode)
- วันที่สิ้นสุดน้อยกว่าวันที่เริ่มต้น

**วิธีแก้:**
```javascript
// ตรวจสอบสิทธิ์
const res = await api.get("/api/config/page-access/check/project_price");
console.log("Has access:", res.data.has_access);

// ตรวจสอบวันที่
if (formData.price_end_date <= formData.price_start_date) {
  alert('วันที่สิ้นสุดต้องมากกว่าวันที่เริ่มใช้ราคา');
}
```

#### 2. ไม่พบราคาโครงการในใบเสนอราคา

**สาเหตุ:**
- โครงการหมดอายุ
- ไม่ได้เลือก project_id
- SKU ไม่อยู่ในโครงการ

**วิธีแก้:**
```python
# ตรวจสอบว่าโครงการ active หรือไม่
today = datetime.now().date().isoformat()
cursor.execute("""
    SELECT * FROM Project_Price_Header
    WHERE project_id = ?
    AND status = 'active'
    AND price_start_date <= ?
    AND price_end_date >= ?
""", [project_id, today, today])
```

#### 3. อัพโหลดไฟล์ไม่สำเร็จ

**สาเหตุ:**
- ไฟล์ใหญ่เกินไป
- นามสกุลไฟล์ไม่รองรับ
- ไม่มีสิทธิ์เขียนไฟล์

**วิธีแก้:**
```python
# ตรวจสอบนามสกุลไฟล์
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ...}
file_ext = Path(file.filename).suffix.lower()
if file_ext not in ALLOWED_EXTENSIONS:
    raise HTTPException(400, "ไฟล์ต้องเป็นประเภท: ...")

# ตรวจสอบสิทธิ์โฟลเดอร์
logger.info(f"Is writable: {os.access(FILES_DIR, os.W_OK)}")
```

---

## 📈 Performance Optimization

### 1. Database Indexing

```sql
-- Index สำหรับการค้นหาโครงการ
CREATE INDEX idx_project_customer ON Project_Price_Header(customer_code, status);
CREATE INDEX idx_project_branch ON Project_Price_Header(branch_code, status);
CREATE INDEX idx_project_dates ON Project_Price_Header(price_start_date, price_end_date);
CREATE INDEX idx_project_employee ON Project_Price_Header(CreatedByEmployeeCode);

-- Index สำหรับการค้นหาสินค้า
CREATE INDEX idx_line_project ON Project_Price_Line(project_id);
CREATE INDEX idx_line_sku ON Project_Price_Line(sku);
```

### 2. Caching

```python
# Cache โครงการที่ active
from cachetools import TTLCache
project_cache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes

def get_active_project_price(customer_code, sku):
    cache_key = f"{customer_code}:{sku}"
    if cache_key in project_cache:
        return project_cache[cache_key]
    
    # Query database
    result = query_database(customer_code, sku)
    project_cache[cache_key] = result
    return result
```

### 3. Bulk Operations

```python
# เพิ่มสินค้าหลาย SKU พร้อมกัน
cursor.executemany("""
    INSERT INTO Project_Price_Line 
    (project_id, sku, product_name, unit, price, quantity)
    VALUES (?, ?, ?, ?, ?, ?)
""", items_data)
```

---

## 🔮 Future Enhancements

### 1. Approval Workflow
- เพิ่มระบบอนุมัติโครงการ
- Workflow หลายขั้นตอน (Request → Approve → Active)
- Email notification

### 2. Project Templates
- บันทึกโครงการเป็น template
- Copy จาก template เพื่อสร้างโครงการใหม่
- แก้ไขเฉพาะราคาและวันที่

### 3. Reporting
- รายงานโครงการที่ใกล้หมดอายุ
- รายงานยอดขายตามโครงการ
- รายงานกำไรตามโครงการ

### 4. Integration
- Sync กับ Business Central
- Export ข้อมูลเป็น Excel
- Import ราคาจาก Excel

---

## 📞 Support

หากพบปัญหาหรือต้องการความช่วยเหลือ:
- ติดต่อทีม IT Support
- Email: support@company.com
- Line: @company-support

---

**เอกสารนี้อัพเดทล่าสุด:** พฤษภาคม 2568  
**เวอร์ชัน:** 1.0.0
