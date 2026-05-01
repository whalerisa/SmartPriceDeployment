# Scheduled Upload Folder Configuration Removal

## Summary
ลบการกำหนดค่า `scheduled_upload_folder` ออกจากหน้า AdminConfig UI ตามที่ผู้ใช้ร้องขอ เนื่องจาก Job ใช้ path ที่ hardcode ไว้แล้ว

## Changes Made

### 1. Frontend Changes
**File:** `frontend/src/pages/AdminConfig.jsx`

**Removed:**
- ส่วน "📅 โฟลเดอร์ราคาตามกำหนดการ" (Scheduled Upload Folder) ทั้งหมด (lines ~1102-1130)
- Input field สำหรับกำหนด scheduled_upload_folder
- Display ค่าปัจจุบันของ scheduled_upload_folder

**Result:**
- หน้า AdminConfig ไม่แสดงการตั้งค่า scheduled_upload_folder อีกต่อไป
- ผู้ใช้ไม่สามารถแก้ไข path ของ scheduled upload folder ผ่าน UI ได้

### 2. Backend Changes
**File:** `backend/config_router.py`

**Removed:**
1. **SystemConfig Model:**
   - ลบ field `scheduled_upload_folder` ออกจาก SystemConfig class

2. **GET /config/settings endpoint:**
   - ลบการอ่านค่า `SCHEDULED_UPLOAD_FOLDER` จาก environment variables
   - ลบการส่งค่า `scheduled_upload_folder` ใน response

3. **PUT /config/settings endpoint:**
   - ลบการอัปเดตค่า `SCHEDULED_UPLOAD_FOLDER` ใน environment variables
   - ลบการบันทึกค่า `scheduled_upload_folder` ลง .env file

**Result:**
- Backend API ไม่รับ/ส่งค่า scheduled_upload_folder อีกต่อไป
- การตั้งค่า scheduled_upload_folder ไม่ถูกบันทึกลง .env file

### 3. Standalone Job (No Changes)
**File:** `backend/jobs/scheduled_price_upload_standalone.py`

**Current Implementation:**
```python
# ⭐ Hardcoded path - ไม่อ่านจาก .env
scheduled_folder = r"C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads"
```

**Status:** ✅ ไม่มีการเปลี่ยนแปลง
- Job ยังคงใช้ hardcoded path เหมือนเดิม
- ไม่อ่านค่าจาก environment variables
- ทำงานได้ปกติโดยไม่ขึ้นกับการตั้งค่าใน AdminConfig

## Verification

### ✅ Frontend Verification
```bash
# Search for scheduled_upload in AdminConfig.jsx
grep -n "scheduled_upload" frontend/src/pages/AdminConfig.jsx
# Result: No matches found
```

### ✅ Backend Verification
```bash
# Search for scheduled_upload in config_router.py
grep -n "scheduled_upload" backend/config_router.py
# Result: No matches found
```

### ✅ Job Verification
```bash
# Verify hardcoded path in standalone job
grep -n "scheduled_folder" backend/jobs/scheduled_price_upload_standalone.py
# Result: Found hardcoded path at line 356
```

## Impact Analysis

### What Changed:
1. ❌ ผู้ใช้ไม่สามารถกำหนด scheduled upload folder path ผ่าน UI ได้อีก
2. ❌ ค่า SCHEDULED_UPLOAD_FOLDER ใน .env file จะไม่ถูกใช้งาน
3. ✅ Job ยังคงทำงานได้ปกติด้วย hardcoded path

### What Didn't Change:
1. ✅ Scheduled price upload feature ยังคงทำงานได้ปกติ
2. ✅ Job ยังคงตรวจสอบไฟล์ที่ `C:\Users\HP\Desktop\Quetung\SmartPriceDeployment\ScheduledPriceUploads`
3. ✅ การอัปโหลดราคาแบบกำหนดวันที่ยังคงใช้งานได้

## Testing Recommendations

### 1. Test AdminConfig UI
- [ ] เปิดหน้า AdminConfig
- [ ] ตรวจสอบว่าไม่มีส่วน "โฟลเดอร์ราคาตามกำหนดการ" แสดงอยู่
- [ ] ตรวจสอบว่าส่วนอื่นๆ ยังทำงานได้ปกติ (Project Files, Product Images)

### 2. Test Backend API
- [ ] เรียก GET `/api/config/settings` และตรวจสอบว่า response ไม่มี `scheduled_upload_folder`
- [ ] ลอง PUT `/api/config/settings` พร้อม `scheduled_upload_folder` และตรวจสอบว่าไม่มี error

### 3. Test Scheduled Upload Job
- [ ] รัน `backend/jobs/run_scheduled_price_upload.bat`
- [ ] ตรวจสอบ log ว่า Job ยังคงใช้ hardcoded path
- [ ] ตรวจสอบว่า Job ยังคงประมวลผลไฟล์ได้ปกติ

## Files Modified

1. ✅ `frontend/src/pages/AdminConfig.jsx` - ลบ UI section
2. ✅ `backend/config_router.py` - ลบ model field และ API logic
3. ⚪ `backend/jobs/scheduled_price_upload_standalone.py` - ไม่มีการเปลี่ยนแปลง (ใช้ hardcoded path)

## Conclusion

การลบการตั้งค่า scheduled_upload_folder ออกจาก AdminConfig UI เสร็จสมบูรณ์แล้ว โดย:

1. **Frontend:** ไม่แสดง UI สำหรับกำหนด path อีกต่อไป
2. **Backend:** ไม่รับ/ส่งค่า scheduled_upload_folder ผ่าน API
3. **Job:** ยังคงใช้ hardcoded path และทำงานได้ปกติ

ระบบ Scheduled Price Upload ยังคงทำงานได้ตามปกติโดยไม่ได้รับผลกระทบจากการเปลี่ยนแปลงนี้ เนื่องจาก Job ใช้ path ที่ hardcode ไว้ในโค้ดโดยตรง ไม่ได้อ่านจาก configuration
