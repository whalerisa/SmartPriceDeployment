# Debug Guide: Region Manager ไม่อัพเดท employees.json

## ขั้นตอนการ Debug

### 1. ตรวจสอบ Browser Console
เปิด Browser Console (F12) และดูว่ามี log อะไรบ้าง:

```javascript
// ควรเห็น logs เหล่านี้เมื่อกดบันทึก:
🔍 Region N: 10027 → 20037
📡 Updating region N RM to 20037
📡 Sending 1 region updates...
✅ All region updates completed: [...]
```

### 2. ตรวจสอบ Network Tab
ใน Browser DevTools > Network tab:
- ดูว่ามี request ไป `PUT /api/config/regions/N` หรือไม่
- Status code ควรเป็น 200
- Response ควรมี `{"success": true, ...}`

### 3. ตรวจสอบ Backend Logs
ดู backend console/logs ควรเห็น:

```
🔍 Updating region N with data: {'rm_employee_id': '20037'}
📂 Employees file path: /path/to/backend/employees.json
📊 Loaded X employees from file
🎯 Target: Set 20037 as RM for region N
🔍 Current RM for region N: 10027
⬇️ Demoted old RM 10027 to ZM
⬆️ Promoted 20037 to RM for region N
💾 Saving changes to /path/to/backend/employees.json
✅ Region N RM updated from 10027 to 20037 by admin_user
```

### 4. ตรวจสอบไฟล์ employees.json
```bash
# ดูเวลาแก้ไขล่าสุด
ls -la backend/employees.json

# ดูเนื้อหาไฟล์
cat backend/employees.json | grep -A5 -B5 "20037"
```

## สาเหตุที่เป็นไปได้

### 1. ❌ API ไม่ถูกเรียก
**อาการ:** ไม่เห็น log ใน Browser Console
**แก้ไข:** 
- ตรวจสอบว่าข้อมูลมีการเปลี่ยนแปลงจริงหรือไม่
- ตรวจสอบว่า `editedRegionMapping` และ `regionMapping` มีค่าถูกต้อง

### 2. ❌ Authentication ล้มเหลว
**อาการ:** Status 403 Forbidden
**แก้ไข:**
- ตรวจสอบว่า user มี role "Admin" หรือไม่
- ตรวจสอบ JWT token ใน cookies

### 3. ❌ ไฟล์ Permission
**อาการ:** Status 500, error ใน backend logs
**แก้ไข:**
```bash
# ตรวจสอบ permission
ls -la backend/employees.json

# แก้ไข permission (ถ้าจำเป็น)
chmod 666 backend/employees.json
```

### 4. ❌ Path ไฟล์ผิด
**อาการ:** FileNotFoundError ใน backend logs
**แก้ไข:**
- ตรวจสอบว่า backend/employees.json อยู่ในตำแหน่งที่ถูกต้อง
- ตรวจสอบ working directory ของ backend

### 5. ❌ JSON Format ผิด
**อาการ:** JSON decode error ใน backend logs
**แก้ไข:**
```bash
# ตรวจสอบ JSON syntax
python -m json.tool backend/employees.json
```

## การทดสอบ Manual

### 1. ทดสอบด้วย curl
```bash
# Get regions
curl -X GET "http://localhost:8000/api/config/regions" \
  -H "Cookie: auth_token=YOUR_TOKEN"

# Update region
curl -X PUT "http://localhost:8000/api/config/regions/N" \
  -H "Content-Type: application/json" \
  -H "Cookie: auth_token=YOUR_TOKEN" \
  -d '{"rm_employee_id": "20037"}'
```

### 2. ทดสอบด้วย Python Script
```bash
python test_region_api.py
```

## วิธีแก้ไขทั่วไป

### 1. Restart Backend
```bash
# หยุด backend
Ctrl+C

# เริ่มใหม่
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Clear Browser Cache
- กด Ctrl+Shift+R (hard refresh)
- หรือเปิด Incognito/Private mode

### 3. ตรวจสอบ File Locks
```bash
# Linux/Mac
lsof backend/employees.json

# Windows
# ปิดโปรแกรมที่อาจจะเปิดไฟล์อยู่ (text editor, etc.)
```

## ถ้ายังไม่ได้

1. **เพิ่ม Debug Logs เพิ่มเติม:**
   - เพิ่ม `console.log` ใน frontend
   - เพิ่ม `logger.info` ใน backend

2. **ตรวจสอบ Database/File Locks:**
   - ปิดโปรแกรมอื่นที่อาจเปิดไฟล์อยู่

3. **ทดสอบด้วย Simple API Call:**
   - ใช้ Postman หรือ curl ทดสอบ API โดยตรง

4. **ตรวจสอบ Docker (ถ้าใช้):**
   - Volume mounting ถูกต้องหรือไม่
   - File permissions ใน container