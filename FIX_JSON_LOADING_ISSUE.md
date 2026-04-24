# แก้ปัญหา: หน้าสร้างรหัสโครงการไม่แสดงสำหรับ role ZM ใน Production Build

## 🔍 สาเหตุของปัญหา

เมื่อ build โปรเจคเป็น executable (.exe) ด้วย PyInstaller หรือเครื่องมือคล้ายๆ กัน:

1. **`__file__` ชี้ไปที่ตำแหน่งที่ไม่ถูกต้อง** - ใน executable, `__file__` อาจชี้ไปที่ temporary directory หรือ internal path ที่ไม่ใช่ตำแหน่งจริงของไฟล์
2. **ไฟล์ JSON ไม่ถูกโหลด** - Backend ไม่สามารถหาไฟล์ `page_access_config.json`, `employees.json`, `custom_roles.json` ได้
3. **ใช้ default config แทน** - เมื่อหาไฟล์ไม่เจอ, backend จะใช้ default configuration ที่ไม่มี ZM ในบางหน้า

## ✅ วิธีแก้ไข

แก้ไขโค้ดให้ลองหาไฟล์ JSON จากหลายๆ ตำแหน่งที่เป็นไปได้:

### ไฟล์ที่แก้ไข:

1. **backend/config_cache.py**
   - `get_page_access_config()` - ลองหาไฟล์จากหลายตำแหน่ง
   - `get_role_approval_scope()` - ลองหาไฟล์จากหลายตำแหน่ง
   - `set_page_access_config()` - บันทึกไฟล์ในตำแหน่งที่ถูกต้อง
   - `set_role_approval_scope()` - บันทึกไฟล์ในตำแหน่งที่ถูกต้อง

2. **backend/role_mapping.py**
   - `load_custom_roles()` - ลองหาไฟล์ custom_roles.json จากหลายตำแหน่ง

3. **backend/login.py**
   - `get_employee_role()` - ลองหาไฟล์ employees.json จากหลายตำแหน่ง

4. **backend/config_router.py**
   - แก้ไขทุกจุดที่โหลด employees.json และ custom_roles.json

### ตำแหน่งที่ลองหา (ตามลำดับ):

```python
possible_paths = [
    os.path.join(os.path.dirname(__file__), "filename.json"),  # ใน directory เดียวกับ script
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "filename.json"),  # Absolute path
    os.path.join(os.getcwd(), "filename.json"),  # Current working directory
    os.path.join(os.getcwd(), "backend", "filename.json"),  # CWD/backend
    "filename.json",  # Relative to CWD
]
```

## 🧪 วิธีทดสอบ

### 1. ทดสอบบน localhost:

```bash
cd backend
python test_json_loading.py
```

สคริปต์นี้จะแสดง:
- ตำแหน่งที่หาไฟล์เจอ
- ข้อมูลที่โหลดได้
- การทำงานของ config_cache module

### 2. ทดสอบหลัง build:

1. Build โปรเจค
2. Copy ไฟล์ JSON ทั้งหมดไปยัง dist folder:
   ```bash
   cp backend/page_access_config.json dist/smart_pricing/
   cp backend/role_approval_scope.json dist/smart_pricing/
   cp backend/custom_roles.json dist/smart_pricing/
   cp backend/employees.json dist/smart_pricing/
   ```
3. รัน executable และตรวจสอบ logs
4. Login ด้วย role ZM และตรวจสอบว่าเห็นหน้าสร้างรหัสโครงการหรือไม่

## 📋 Checklist สำหรับ Production Build

- [ ] แก้ไขโค้ดตามที่ระบุข้างต้น (config_cache.py, role_mapping.py, login.py, config_router.py)
- [ ] เพิ่มไฟล์ JSON ใน smart_pricing.spec (datas section)
- [ ] รัน `create_release.bat` เพื่อ build โปรเจค (จะ copy ไฟล์ JSON อัตโนมัติ)
- [ ] ตรวจสอบว่าไฟล์ JSON ทั้งหมดอยู่ใน dist/smart_pricing/ folder
- [ ] ตรวจสอบ logs ว่า backend หาไฟล์เจอ (ดูข้อความ "✅ Loaded ... from ...")
- [ ] ทดสอบ login ด้วย role ต่างๆ (Sales, ZM, RM, PM, Admin)
- [ ] ตรวจสอบว่าหน้าต่างๆ แสดงตาม role ที่ถูกต้อง

## 🚀 วิธี Build โปรเจค

### วิธีที่ 1: ใช้ create_release.bat (แนะนำ)

```bash
create_release.bat
```

Script นี้จะ:
1. Build frontend
2. Install backend requirements
3. Run PyInstaller
4. **Copy ไฟล์ JSON อัตโนมัติ** ✨
5. Copy ไฟล์อื่นๆ ที่จำเป็น

### วิธีที่ 2: Manual Build

```bash
# 1. Build frontend
cd frontend
npm install
npm run build
cd ..

# 2. Install backend requirements
cd backend
pip install -r requirements.txt
cd ..

# 3. Run PyInstaller
pyinstaller --noconfirm --clean smart_pricing.spec

# 4. Copy JSON files manually
copy_json_to_dist.bat
```

## 📁 โครงสร้างไฟล์หลัง Build

```
dist/smart_pricing/
├── smart_pricing.exe
├── page_access_config.json      ← ไฟล์ config สำหรับสิทธิ์การเข้าถึงหน้า
├── role_approval_scope.json     ← ไฟล์ config สำหรับขอบเขตการอนุมัติ
├── custom_roles.json            ← ไฟล์ custom roles
├── employees.json               ← ไฟล์ข้อมูลพนักงาน
├── start_server.bat
├── DEPLOYMENT.md
└── ... (ไฟล์อื่นๆ)
```

## 🔧 การ Debug

หากยังมีปัญหา:

1. **ตรวจสอบ logs** - ดูว่า backend หาไฟล์จากตำแหน่งไหน
   ```
   ✅ Loaded page access config from /path/to/file
   ⚠️ page_access_config.json not found in any of these locations: [...]
   ```

2. **ตรวจสอบ API response** - เรียก API endpoint:
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

3. **ตรวจสอบ page_access_config.json** - ตรวจสอบว่า ZM อยู่ใน allowed_roles:
   ```json
   {
     "project_price": {
       "allowed_roles": ["Admin", "Sales_Project", "RM", "PM", "CEO", "SDM", "ZM"]
     }
   }
   ```

## 📝 หมายเหตุ

- การแก้ไขนี้รองรับทั้ง development (localhost) และ production (executable)
- ไฟล์ JSON จะถูกโหลดจากตำแหน่งแรกที่เจอ
- หากไม่เจอไฟล์ใดๆ จะใช้ default configuration
- Logs จะแสดงตำแหน่งที่หาไฟล์เจอเพื่อช่วย debug
