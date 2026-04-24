# 🔧 แก้ไขปัญหา: หน้าสร้างรหัสโครงการไม่แสดงใน Production

## 📌 สรุปปัญหา

เมื่อ build โปรเจคเป็น executable และรันบน production:
- ✅ หน้าอนุมัติราคาแสดงปกติสำหรับ role ZM
- ❌ หน้าสร้างรหัสโครงการไม่แสดงสำหรับ role ZM
- ✅ บน localhost ทุกอย่างทำงานปกติ

**สาเหตุ:** Backend ไม่สามารถหาไฟล์ `page_access_config.json` ได้ใน production build

## ✅ การแก้ไข

### 1. แก้ไขโค้ด Backend (เสร็จแล้ว ✓)

ไฟล์ที่แก้ไข:
- ✓ `backend/config_cache.py` - ลองหาไฟล์จากหลายตำแหน่ง
- ✓ `backend/role_mapping.py` - แก้การโหลด custom_roles.json
- ✓ `backend/login.py` - แก้การโหลด employees.json
- ✓ `backend/config_router.py` - แก้การโหลดไฟล์ JSON ทั้งหมด

### 2. แก้ไข Build Configuration (เสร็จแล้ว ✓)

- ✓ `smart_pricing.spec` - เพิ่มไฟล์ JSON ใน datas section
- ✓ `create_release.bat` - เพิ่มคำสั่ง copy ไฟล์ JSON

## 🚀 วิธีใช้งาน

### สำหรับ Developer

#### 1. ทดสอบบน localhost:

```bash
# ทดสอบการโหลดไฟล์ JSON
cd backend
python test_json_loading.py

# ทดสอบ API
python test_page_access_api.py
```

#### 2. Build โปรเจค:

```bash
# วิธีที่ 1: ใช้ script (แนะนำ)
create_release.bat

# วิธีที่ 2: Manual
pyinstaller --noconfirm --clean smart_pricing.spec
copy_json_to_dist.bat
```

#### 3. ตรวจสอบไฟล์ใน dist folder:

```bash
dir dist\smart_pricing\*.json
```

ควรเห็นไฟล์:
- page_access_config.json
- role_approval_scope.json
- custom_roles.json
- employees.json

### สำหรับ User (Production)

1. **รับไฟล์ build ใหม่** จาก developer
2. **ตรวจสอบว่ามีไฟล์ JSON** ใน folder เดียวกับ smart_pricing.exe
3. **รัน smart_pricing.exe** ตามปกติ
4. **ตรวจสอบ logs** ว่ามีข้อความ:
   ```
   ✅ Loaded page access config from ...
   ```

## 🧪 การทดสอบ

### Test Case 1: Login ด้วย role ZM

1. Login ด้วย employee code ที่มี role = ZM
2. ตรวจสอบว่าเห็นเมนู:
   - ✅ สร้างใบเสนอราคา
   - ✅ สร้างรหัสโครงการ ← **ควรเห็นหน้านี้**
   - ✅ หน้าอนุมัติราคา

### Test Case 2: ตรวจสอบ API

เรียก API:
```bash
curl http://localhost:8000/api/config/page-access/check/project_price
```

Response ควรเป็น:
```json
{
  "has_access": true,
  "page_id": "project_price",
  "user_role": "ZM"
}
```

### Test Case 3: ตรวจสอบ Logs

ดู logs ของ backend ควรเห็น:
```
✅ Loaded page access config from C:\path\to\page_access_config.json
```

ถ้าเห็น:
```
⚠️ page_access_config.json not found in any of these locations: [...]
```
แสดงว่าไฟล์ไม่ถูก copy หรืออยู่ในตำแหน่งที่ผิด

## 🔍 Troubleshooting

### ปัญหา: หน้ายังไม่แสดง

1. **ตรวจสอบไฟล์ JSON อยู่ใน dist folder หรือไม่**
   ```bash
   dir dist\smart_pricing\*.json
   ```

2. **ตรวจสอบเนื้อหาของ page_access_config.json**
   - เปิดไฟล์ `dist\smart_pricing\page_access_config.json`
   - ตรวจสอบว่า `project_price` มี `"ZM"` ใน `allowed_roles`

3. **ตรวจสอบ logs**
   - รัน smart_pricing.exe
   - ดู console output หรือ log file
   - หาข้อความที่เกี่ยวกับ "page_access_config"

4. **ลอง build ใหม่**
   ```bash
   create_release.bat
   ```

### ปัญหา: Build ไม่สำเร็จ

1. **ตรวจสอบว่าไฟล์ JSON อยู่ใน backend folder**
   ```bash
   dir backend\*.json
   ```

2. **ตรวจสอบ smart_pricing.spec**
   - เปิดไฟล์และหา `datas = [`
   - ตรวจสอบว่ามีบรรทัดเหล่านี้:
     ```python
     (backend_path + '/page_access_config.json', '.'),
     (backend_path + '/role_approval_scope.json', '.'),
     (backend_path + '/custom_roles.json', '.'),
     (backend_path + '/employees.json', '.'),
     ```

## 📞 ติดต่อ

หากยังมีปัญหา กรุณาติดต่อ developer พร้อมแนบ:
1. Screenshot ของหน้าที่มีปัญหา
2. Log files
3. ผลลัพธ์จากคำสั่ง `dir dist\smart_pricing\*.json`

---

**หมายเหตุ:** การแก้ไขนี้ใช้ได้กับทุก role และทุกหน้า ไม่ใช่แค่ ZM และหน้าสร้างรหัสโครงการเท่านั้น
