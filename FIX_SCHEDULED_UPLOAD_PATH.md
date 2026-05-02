# Fix Scheduled Upload Path Mismatch

## ปัญหาที่พบ

มีการกำหนด **Scheduled Upload Folder Path** ใน **2 ที่** ที่ไม่ตรงกัน:

### ก่อนแก้ไข:

1. **Backend API** (`backend/admin_router.py` line 303):
   ```python
   scheduled_folder = os.getenv("SCHEDULED_UPLOAD_FOLDER", "data/scheduled_uploads")
   ```
   - อ่านจาก environment variable
   - Default: `"data/scheduled_uploads"` (relative path)

2. **Standalone Job** (`backend/jobs/scheduled_price_upload_standalone.py` line 356):
   ```python
   scheduled_folder = r"C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads"
   ```
   - Hardcoded absolute path

### ผลกระทบ:
- ❌ User อัพโหลดไฟล์ไปที่ `data/scheduled_uploads`
- ❌ Job ไปหาไฟล์ที่ `C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads`
- ❌ **Job ไม่เจอไฟล์ที่ User อัพโหลด!**

---

## การแก้ไข

### ✅ แก้ไข `backend/admin_router.py`

**เปลี่ยนจาก:**
```python
# Get scheduled upload folder from environment
scheduled_folder = os.getenv("SCHEDULED_UPLOAD_FOLDER", "data/scheduled_uploads")
```

**เป็น:**
```python
# ⭐ Hardcoded path - ต้องตรงกับ scheduled_price_upload_standalone.py
scheduled_folder = r"C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads"
```

---

## ผลลัพธ์หลังแก้ไข

### ✅ ตอนนี้ใช้ Path เดียวกันทั้ง 2 ที่:

1. **Backend API** (เมื่อ User อัพโหลด):
   ```python
   scheduled_folder = r"C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads"
   ```

2. **Standalone Job** (เมื่อ Job ประมวลผล):
   ```python
   scheduled_folder = r"C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads"
   ```

### ✅ Flow ที่ถูกต้อง:

```
User อัพโหลดไฟล์ (กำหนดวันที่)
    ↓
Backend API บันทึกไฟล์ไปที่:
C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads\G01052569.xlsx
    ↓
Job รันทุกวัน ตรวจสอบโฟลเดอร์:
C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads\
    ↓
✅ Job เจอไฟล์ → ประมวลผล → ย้ายไปที่ archive/
```

---

## การใช้งาน

### 📁 Scheduled Upload Folder Path (เดียวกันทั้งระบบ):
```
C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads
```

### 📂 โครงสร้างโฟลเดอร์:
```
C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads\
├── G01052569.xlsx                    (ไฟล์รออัพโหลด)
├── G01052569.xlsx.meta.json          (ข้อมูล metadata)
├── A02052569.xlsx                    (ไฟล์รออัพโหลด)
├── A02052569.xlsx.meta.json          (ข้อมูล metadata)
└── archive\                           (ไฟล์ที่ประมวลผลแล้ว)
    ├── G01052569_success_20260501_231332.xlsx
    ├── G01052569_success_20260501_231332.xlsx.meta.json
    ├── A02052569_failed_20260502_120000.xlsx
    └── A02052569_failed_20260502_120000.xlsx.meta.json
```

---

## ถ้าต้องการเปลี่ยน Path

ต้องแก้ไข **2 ที่** ให้ตรงกัน:

### 1. `backend/admin_router.py` (line ~303):
```python
scheduled_folder = r"D:\YourNewPath\ScheduledUploads"
```

### 2. `backend/jobs/scheduled_price_upload_standalone.py` (line 356):
```python
scheduled_folder = r"D:\YourNewPath\ScheduledUploads"
```

⚠️ **สำคัญ:** Path ต้องเหมือนกันทั้ง 2 ที่!

---

## Testing

### ✅ ทดสอบการอัพโหลด:
1. เข้าหน้า UpdatePrice
2. เลือก "กำหนดวันที่อัพโหลด"
3. เลือกวันที่และอัพโหลดไฟล์
4. ตรวจสอบว่าไฟล์ถูกบันทึกที่:
   ```
   C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads\
   ```

### ✅ ทดสอบ Job:
1. รัน `backend/jobs/run_scheduled_price_upload.bat`
2. ตรวจสอบ log ว่า Job หาไฟล์เจอ:
   ```
   📁 Using hardcoded folder path: C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads
   📄 Found X Excel file(s) in folder
   ```

---

## Files Modified

1. ✅ `backend/admin_router.py` - เปลี่ยนจากอ่าน .env เป็น hardcoded path
2. ⚪ `backend/jobs/scheduled_price_upload_standalone.py` - ไม่มีการเปลี่ยนแปลง (ใช้ hardcoded path อยู่แล้ว)

---

## Conclusion

แก้ไขปัญหา **Path Mismatch** เรียบร้อยแล้ว โดย:

1. ✅ Backend API และ Standalone Job ใช้ path เดียวกัน
2. ✅ ไฟล์ที่ User อัพโหลดจะถูกบันทึกที่ path ที่ Job ตรวจสอบ
3. ✅ Job จะเจอไฟล์และประมวลผลได้ถูกต้อง

**Path เดียวที่ใช้ทั้งระบบ:**
```
C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads
```
