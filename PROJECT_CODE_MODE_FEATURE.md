# ฟีเจอร์: เลือกรูปแบบ Project Code (Running Number หรือกรอกเอง)

## สรุปการเปลี่ยนแปลง

เพิ่มฟีเจอร์ให้ผู้ดูแลระบบสามารถเลือกได้ว่า Project Code จะเป็น **Running Number (อัตโนมัติ)** หรือ **กรอกเอง (Manual)** ผ่านหน้า Admin Config

## การทำงาน

### 1. หน้า Admin Config (Frontend)
**ไฟล์:** `frontend/src/pages/AdminConfig.jsx`

เพิ่มการตั้งค่าในแท็บ "การตั้งค่าระบบ" ให้เลือกได้ 2 โหมด:

- **Running Number (อัตโนมัติ)**: ระบบจะสร้างเลขที่อัตโนมัติ เช่น PJ6704001, TR6704002
- **กรอกเอง (Manual)**: ผู้ใช้สามารถกรอก Project Code เองได้

### 2. Backend Configuration (Backend)
**ไฟล์:** `backend/config_router.py`

เพิ่ม field `project_code_mode` ใน `SystemConfig`:
- ค่าเริ่มต้น: `"auto"` (Running Number)
- ค่าที่เป็นไปได้: `"auto"` หรือ `"manual"`
- บันทึกใน environment variable: `PROJECT_CODE_MODE`

### 3. Project Price Creation (Backend)
**ไฟล์:** `backend/project_price_router.py`

แก้ไข function `create_project_price()`:

#### โหมด Auto (Running Number):
- สร้าง Project Code อัตโนมัติตามรูปแบบเดิม:
  - **Project Mode**: `PJ{YY}{MM}{XXX}` เช่น PJ6704001
  - **Branch Mode**: `{BR}{YY}{MM}{XXX}` เช่น TR6704001
  - **Customer Mode**: `{YY}{MM}{CUSTCODE}` เช่น 670408015AY

#### โหมด Manual:
- ใช้ `project_code` ที่ผู้ใช้กรอกมา
- ตรวจสอบว่า Project Code ซ้ำหรือไม่
- ถ้าซ้ำจะแจ้ง error: "Project Code '{code}' มีอยู่ในระบบแล้ว กรุณาใช้รหัสอื่น"

### 4. Project Price Management (Frontend)
**ไฟล์:** `frontend/src/pages/ProjectPriceManagement.jsx`

เพิ่มฟีเจอร์:
- เพิ่ม state `projectCodeMode` เพื่อเก็บโหมดปัจจุบัน
- เพิ่ม function `loadProjectCodeMode()` เพื่อโหลดการตั้งค่าจาก backend
- แสดง input field สำหรับกรอก Project Code เมื่ออยู่ในโหมด Manual
- แสดงข้อความแจ้งเตือนว่าระบบจะสร้างอัตโนมัติเมื่ออยู่ในโหมด Auto
- เพิ่ม validation ตรวจสอบว่ากรอก Project Code ในโหมด Manual

## วิธีใช้งาน

### สำหรับ Admin:
1. เข้าหน้า **Admin Config** (⚙️ การตั้งค่าระบบ)
2. เลือกแท็บ **"การตั้งค่าระบบ"**
3. เลือกรูปแบบ Project Code:
   - ✅ **Running Number (อัตโนมัติ)** - ระบบสร้างเลขที่อัตโนมัติ
   - ✅ **กรอกเอง (Manual)** - ผู้ใช้กรอกเอง
4. กดปุ่ม **"💾 บันทึก"**

### สำหรับผู้ใช้งาน (สร้างโครงการ):

#### โหมด Auto (Running Number):
- ไม่ต้องกรอก Project Code
- ระบบจะสร้างเลขที่อัตโนมัติเมื่อบันทึก
- แสดงข้อความ: "💡 รหัสโครงการจะถูกสร้างอัตโนมัติเมื่อบันทึก"

#### โหมด Manual:
- แสดงช่องกรอก **"รหัสโครงการ"** (required)
- ต้องกรอก Project Code เอง เช่น PJ6704001, CUSTOM001
- แสดงข้อความ: "💡 กรอกรหัสโครงการเอง (ระบบไม่สร้างอัตโนมัติ)"
- ถ้ารหัสซ้ำจะแจ้ง error

## ไฟล์ที่แก้ไข

1. **frontend/src/pages/AdminConfig.jsx**
   - เพิ่มการตั้งค่า Project Code Mode ในแท็บ System Settings

2. **backend/config_router.py**
   - เพิ่ม `project_code_mode` ใน `SystemConfig` model
   - เพิ่มการโหลดและบันทึก `PROJECT_CODE_MODE` environment variable

3. **backend/project_price_router.py**
   - แก้ไข `create_project_price()` ให้รองรับทั้ง auto และ manual mode
   - เพิ่มการตรวจสอบ Project Code ซ้ำในโหมด manual

4. **frontend/src/pages/ProjectPriceManagement.jsx**
   - เพิ่ม state `projectCodeMode`
   - เพิ่ม function `loadProjectCodeMode()`
   - แสดง input field สำหรับ Project Code ในโหมด manual
   - เพิ่ม validation

## ข้อดี

✅ ยืดหยุ่น - เลือกได้ว่าจะใช้ Running Number หรือกรอกเอง
✅ ป้องกันรหัสซ้ำ - ตรวจสอบใน backend
✅ ใช้งานง่าย - แสดงข้อความแจ้งเตือนชัดเจน
✅ Backward Compatible - ค่าเริ่มต้นเป็น auto (ไม่กระทบระบบเดิม)

## ตัวอย่างการใช้งาน

### ตัวอย่าง Auto Mode:
```
ผู้ใช้กรอก: ชื่อโครงการ = "โครงการคอนโด ABC"
ระบบสร้าง: project_code = "PJ6704001" (อัตโนมัติ)
```

### ตัวอย่าง Manual Mode:
```
ผู้ใช้กรอก: 
  - project_code = "CONDO_ABC_2024"
  - ชื่อโครงการ = "โครงการคอนโด ABC"
ระบบใช้: project_code = "CONDO_ABC_2024" (ตามที่กรอก)
```

## Environment Variable

เพิ่ม environment variable ใหม่:
```
PROJECT_CODE_MODE=auto  # หรือ "manual"
```

ค่าเริ่มต้น: `auto` (ถ้าไม่ได้ตั้งค่า)
