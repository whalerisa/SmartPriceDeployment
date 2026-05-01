# Scheduled Price Upload Feature Guide

## 📋 Overview

ฟีเจอร์ **Scheduled Price Upload** ช่วยให้คุณสามารถกำหนดวันที่ที่ต้องการให้ระบบอัปโหลดราคาอัตโนมัติ โดยไม่ต้องอัปโหลดทันที

## ✨ Features

1. **เลือกวันที่อัปโหลด**: กำหนดวันที่ที่ต้องการให้ราคามีผลบังคับใช้
2. **Validation**: ตรวจสอบคอลัมน์ที่จำเป็นก่อนอัปโหลด (SKU, SDM, R2, R1, W2, W1)
3. **File Naming Convention**: ระบบตั้งชื่อไฟล์อัตโนมัติตามรูปแบบ `{Category}{DDMMYYYY}.xlsx`
4. **Automatic Upload**: Job รันทุกวันเพื่อตรวจสอบและอัปโหลดไฟล์ที่ถึงกำหนด
5. **Archive**: ย้ายไฟล์ที่ประมวลผลแล้วไปยัง archive folder

---

## 🎯 How to Use

### 1. Frontend - Upload Price Page

1. ไปที่หน้า **Dashboard → Update Data (Manager) → Tab "อัปเดตราคา"**
2. เลือก **โหมดการอัปโหลด**:
   - **อัปโหลดทันที**: อัปโหลดราคาทันทีเมื่อกดปุ่ม
   - **กำหนดวันที่อัปโหลด**: บันทึกไฟล์และกำหนดวันที่ที่ต้องการอัปโหลด
3. เลือก **วันที่ต้องการให้อัปโหลด** (ถ้าเลือกโหมด "กำหนดวันที่")
4. เลือก **สาขา** ที่ต้องการอัปเดตราคา
5. เลือก **ไฟล์ Excel** (.xlsx)
6. กดปุ่ม **"บันทึกตารางอัปโหลด"**

### 2. File Naming Convention

ระบบจะตั้งชื่อไฟล์อัตโนมัติตามรูปแบบ:

```
{Category}{DDMMYYYY}.xlsx
```

**ตัวอย่าง**:
- `G26092569.xlsx` = กระจก (Glass), วันที่ 26/09/2569
- `A01012570.xlsx` = อลูมิเนียม (Aluminium), วันที่ 01/01/2570
- `Y15032569.xlsx` = ยิปซั่ม (Gypsum), วันที่ 15/03/2569

**Categories**:
- `G` = กระจก (Glass)
- `A` = อลูมิเนียม (Aluminium)
- `Y` = ยิปซั่ม (Gypsum)
- `S` = ซีแลนท์ (Sealant)
- `C` = ซีไลน์ (C-Line)
- `E` = อุปกรณ์ (Equipment)
- `MIXED` = หลายประเภท

### 3. Scheduled Upload Folder

ไฟล์จะถูกบันทึกไปที่ folder ที่กำหนดใน `.env`:

```env
SCHEDULED_UPLOAD_FOLDER=C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads
```

**โครงสร้าง Folder**:
```
ScheduledPriceUploads/
├── G26092569.xlsx
├── G26092569.xlsx.meta.json
├── A01012570.xlsx
├── A01012570.xlsx.meta.json
└── archive/
    ├── G25092569_success_20250925_120000.xlsx
    └── G25092569_success_20250925_120000.xlsx.meta.json
```

---

## 🤖 Standalone Job

### Job Description

**File**: `backend/jobs/scheduled_price_upload_standalone.py`

Job นี้รันทุกวันเพื่อ:
1. ตรวจสอบไฟล์ใน `SCHEDULED_UPLOAD_FOLDER`
2. Parse วันที่จากชื่อไฟล์
3. ถ้าวันที่ตรงกับวันนี้ → อัปโหลดราคาอัตโนมัติ
4. ย้ายไฟล์ที่ประมวลผลแล้วไปยัง `archive/` folder

### Manual Run

```bash
cd backend/jobs
python scheduled_price_upload_standalone.py
```

หรือใช้ batch file:

```bash
cd backend/jobs
run_scheduled_price_upload.bat
```

### Schedule with Windows Task Scheduler

1. เปิด **Task Scheduler**
2. สร้าง **New Task**:
   - **Name**: Scheduled Price Upload
   - **Trigger**: Daily at 00:00 (หรือเวลาที่ต้องการ)
   - **Action**: Start a program
     - **Program**: `C:\path\to\backend\jobs\run_scheduled_price_upload.bat`
   - **Settings**: 
     - ✅ Run whether user is logged on or not
     - ✅ Run with highest privileges

---

## 📊 Metadata File

ระบบจะสร้างไฟล์ metadata (`.meta.json`) สำหรับแต่ละไฟล์:

```json
{
  "filename": "G26092569.xlsx",
  "scheduled_date": "2026-09-26",
  "branch_codes": ["00TR", "05AY"],
  "category": "G",
  "uploaded_by": "90038",
  "uploaded_by_name": "John Doe",
  "uploaded_at": "2026-09-20T10:30:00",
  "status": "pending"
}
```

---

## ✅ Validation Rules

ระบบจะตรวจสอบไฟล์ก่อนอัปโหลด (เฉพาะโหมด "อัปโหลดทันที"):

### Required Columns
- **SKU** (หรือ No_, Item_No, No, ItemNo)
- **SDM**
- **R2**
- **R1**
- **W2**
- **W1**

### Validation Checks
1. ✅ ตรวจสอบว่ามีคอลัมน์ที่จำเป็นครบถ้วน
2. ✅ ตรวจสอบว่าคอลัมน์ที่จำเป็นไม่เป็นค่าว่าง (NULL)
3. ✅ แสดง popup เตือนถ้าพบข้อผิดพลาด

**ตัวอย่าง Error Message**:
```
❌ ไฟล์มีข้อผิดพลาด!

แถวที่ 5 (SKU: G001): คอลัมน์ R1 เป็นค่าว่าง
แถวที่ 12 (SKU: G015): คอลัมน์ W2 เป็นค่าว่าง
แถวที่ 23 (SKU: G032): คอลัมน์ SDM เป็นค่าว่าง
```

---

## 📝 Logs

### Job Logs

**Location**: `backend/jobs/logs/scheduled_price_upload.log`

**Log Rotation**: Daily, keep 30 days

**Example Log**:
```
2026-09-26 00:00:01 - scheduled_price_upload - INFO - ================================================================================
2026-09-26 00:00:01 - scheduled_price_upload - INFO - 🕐 Scheduled Price Upload Job Started
2026-09-26 00:00:01 - scheduled_price_upload - INFO -    Triggered at: 2026-09-26 00:00:01
2026-09-26 00:00:01 - scheduled_price_upload - INFO - ================================================================================
2026-09-26 00:00:01 - scheduled_price_upload - INFO - 📁 Checking folder: C:\...\ScheduledPriceUploads
2026-09-26 00:00:01 - scheduled_price_upload - INFO - 📅 Today's date: 2026-09-26
2026-09-26 00:00:01 - scheduled_price_upload - INFO - 📄 Found 2 Excel file(s) in folder
2026-09-26 00:00:02 - scheduled_price_upload - INFO - 📄 File: G26092569.xlsx, Date: 2026-09-26
2026-09-26 00:00:02 - scheduled_price_upload - INFO - ✅ File date matches today, processing...
2026-09-26 00:00:15 - scheduled_price_upload - INFO - ✅ File processed successfully: 1250 items
2026-09-26 00:00:15 - scheduled_price_upload - INFO - ================================================================================
2026-09-26 00:00:15 - scheduled_price_upload - INFO - ✅ Scheduled Price Upload Job Completed
2026-09-26 00:00:15 - scheduled_price_upload - INFO -    Duration: 14.23 seconds
2026-09-26 00:00:15 - scheduled_price_upload - INFO -    Files Found: 2
2026-09-26 00:00:15 - scheduled_price_upload - INFO -    Files Processed: 1
2026-09-26 00:00:15 - scheduled_price_upload - INFO -    Files Failed: 0
2026-09-26 00:00:15 - scheduled_price_upload - INFO -    Total Items Uploaded: 1250
2026-09-26 00:00:15 - scheduled_price_upload - INFO - ================================================================================
```

---

## 🔧 Configuration

### Environment Variables

**File**: `backend/.env`

```env
# Scheduled Upload Folder
SCHEDULED_UPLOAD_FOLDER=C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads

# Database Configuration
MSSQL_SERVER=192.192.0.220,50681
MSSQL_DATABASE=SP681
MSSQL_USERNAME=sp681_user
MSSQL_PASSWORD=Tng#kmitl2
```

---

## 🚨 Troubleshooting

### Problem: Job ไม่รัน

**Solution**:
1. ตรวจสอบ Task Scheduler ว่า task ถูกสร้างและ enabled
2. ตรวจสอบ log file: `backend/jobs/logs/scheduled_price_upload.log`
3. รัน job manually เพื่อดู error: `python scheduled_price_upload_standalone.py`

### Problem: ไฟล์ไม่ถูกประมวลผล

**Solution**:
1. ตรวจสอบชื่อไฟล์ว่าตรงตามรูปแบบ `{Category}{DDMMYYYY}.xlsx`
2. ตรวจสอบวันที่ในชื่อไฟล์ว่าถูกต้อง (ใช้ปี พ.ศ.)
3. ตรวจสอบว่าไฟล์อยู่ใน `SCHEDULED_UPLOAD_FOLDER`

### Problem: Validation ไม่ทำงาน

**Solution**:
1. ตรวจสอบว่าติดตั้ง `xlsx` library แล้ว: `npm install xlsx`
2. ตรวจสอบ browser console สำหรับ error messages
3. ลองใช้ไฟล์ Excel ใหม่ที่มีคอลัมน์ครบถ้วน

---

## 📦 Installation

### Frontend

```bash
cd frontend
npm install xlsx
npm install
```

### Backend

```bash
cd backend
pip install pandas openpyxl
```

---

## 🎉 Summary

ฟีเจอร์ **Scheduled Price Upload** ช่วยให้คุณ:
- ✅ กำหนดวันที่อัปโหลดราคาล่วงหน้า
- ✅ ตรวจสอบความถูกต้องของไฟล์ก่อนอัปโหลด
- ✅ อัปโหลดราคาอัตโนมัติตามกำหนดเวลา
- ✅ ติดตามประวัติการอัปโหลดผ่าน logs และ archive

**Happy Scheduling! 🚀**
