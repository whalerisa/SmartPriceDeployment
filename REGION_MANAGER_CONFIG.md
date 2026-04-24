# การจัดการผู้ดูแลภาค (Regional Manager Configuration)

## ภาพรวม
ระบบนี้ช่วยให้ Admin สามารถจัดการการกำหนดว่าพนักงานคนไหนเป็น Regional Manager (RM) ของแต่ละภาคผ่านหน้า Admin Config โดยข้อมูลจะถูกบันทึกใน `employees.json`

## ไฟล์ที่เกี่ยวข้อง

### Backend
1. **`backend/employees.json`** (แก้ไข)
   - เก็บข้อมูลพนักงานทั้งหมด รวมถึง role และ region
   - เมื่อแก้ไข RM ของภาค ระบบจะอัพเดทไฟล์นี้โดยตรง
   - โครงสร้าง:
   ```json
   {
     "employees": [
       {
         "employee_id": "10027",
         "branch": "12CM",
         "region": "N",
         "role": "RM"
       },
       ...
     ]
   }
   ```

2. **`backend/config_router.py`** (แก้ไข)
   - เพิ่ม API endpoints:
     - `GET /api/config/regions` - ดึงข้อมูล RM ของแต่ละภาคจาก employees.json
     - `PUT /api/config/regions/{region_code}` - อัพเดท RM ของภาคที่ระบุใน employees.json
   - ลบ API configuration endpoints เพื่อความปลอดภัย:
     - ลบการแก้ไข API URLs และ keys ผ่าน UI
     - ลบ API status checking endpoint

### Frontend
3. **`frontend/src/pages/AdminConfig.jsx`** (แก้ไข)
   - เพิ่ม Tab "🗺️ จัดการภาค"
   - แสดงรายการภาคทั้งหมดพร้อมช่องกรอกรหัสพนักงาน RM
   - แสดงการเปลี่ยนแปลงก่อนบันทึก

## วิธีใช้งาน

### สำหรับ Admin
1. เข้าหน้า **Admin Config** จาก Dashboard
2. คลิกที่ Tab **"🗺️ จัดการภาค"**
3. จะเห็นรายการภาคทั้งหมด (BE, N, S, NE, C) พร้อมรหัสพนักงาน RM ปัจจุบัน
4. แก้ไขรหัสพนักงาน RM ในช่องที่ต้องการ
5. กดปุ่ม **"💾 บันทึก"** ด้านล่าง
6. ระบบจะอัพเดท `employees.json` ทันที

### ตัวอย่างการใช้งาน
**สถานการณ์:** ภาคเหนือ (N) เปลี่ยน RM จาก `10027` เป็น `20037`

**ขั้นตอน:**
1. Admin เข้าหน้า Admin Config → Tab จัดการภาค
2. ที่ภาค N แก้ไขรหัสพนักงาน RM จาก `10027` เป็น `20037`
3. กดบันทึก

**ผลลัพธ์ใน employees.json:**
- พนักงาน `10027` จะถูกเปลี่ยน role จาก `RM` เป็น `ZM` (ลดตำแหน่ง)
- พนักงาน `20037` จะถูกเปลี่ยน role เป็น `RM` และ region เป็น `N`
- หากพนักงาน `20037` ยังไม่มีในไฟล์ ระบบจะเพิ่มเข้าไปใหม่

## ข้อมูลภาคในระบบ

| รหัสภาค | ชื่อภาค | RM เริ่มต้น | สาขา |
|---------|---------|-------------|------|
| BE | กรุงเทพตะวันออก | 20054 | 00TR, 01TJ, 03TS, 04TP, 06RY, 15CB, 24TL, 90HO |
| N | ภาคเหนือ | 10027 | 11PL, 12CM, 17CR, 23NS |
| S | ภาคใต้ | 15487 | 13SR, 14HY, 16PK |
| NE | ภาคตะวันออกเฉียงเหนือ | 21560 | 08NR, 09UB, 10KK, 18UD, 20SK |
| C | ภาคกลาง | 21751 | 05AY, 07RB, 19PC, 21BS, 25SB |

## API Endpoints

### GET /api/config/regions
ดึงข้อมูล RM ของแต่ละภาคจาก employees.json

**Response:**
```json
{
  "regions": {
    "BE": {
      "region_code": "BE",
      "region_name": "Bangkok East",
      "region_name_thai": "กรุงเทพตะวันออก",
      "rm_employee_id": "20054",
      "branches": ["00TR", "01TJ", ...]
    },
    "N": {
      "region_code": "N",
      "region_name": "North",
      "region_name_thai": "ภาคเหนือ",
      "rm_employee_id": "10027",
      "branches": ["11PL", "12CM", "17CR", "23NS"]
    },
    ...
  }
}
```

### PUT /api/config/regions/{region_code}
อัพเดท Regional Manager ของภาคที่ระบุใน employees.json

**Request Body:**
```json
{
  "rm_employee_id": "20037"
}
```

**Response:**
```json
{
  "success": true,
  "message": "อัพเดท RM สำหรับภาค N สำเร็จ",
  "region_code": "N",
  "old_rm_id": "10027",
  "new_rm_id": "20037"
}
```

## การทำงานของระบบ

### เมื่อแก้ไข RM
1. **ค้นหา RM เดิม:** ระบบจะค้นหาพนักงานที่มี `role: "RM"` และ `region: "{region_code}"` ใน employees.json
2. **ลดตำแหน่ง RM เดิม:** เปลี่ยน role จาก `RM` เป็น `ZM`
3. **เลื่อนตำแหน่ง RM ใหม่:** 
   - หากพนักงานมีอยู่แล้ว: เปลี่ยน role เป็น `RM` และ region เป็นภาคที่เลือก
   - หากพนักงานยังไม่มี: เพิ่มพนักงานใหม่เข้าไปใน employees.json
4. **บันทึกไฟล์:** บันทึก employees.json ด้วยข้อมูลที่อัพเดทแล้ว

## การปรับปรุงความปลอดภัย

### ลบ API Configuration Management
เพื่อความปลอดภัย ระบบได้ลบฟีเจอร์การแก้ไข API configuration ผ่าน UI:

**ที่ลบออก:**
- การแก้ไข API URLs และ API keys ผ่านหน้า Admin Config
- API status checking endpoint (`/api/config/api-status`)
- การแสดง API configuration ใน response

**เหตุผล:**
- API URLs และ keys เป็นข้อมูลสำคัญที่ไม่ควรแก้ไขผ่าน UI
- ควรจัดการผ่าน environment variables หรือ .env file เท่านั้น
- ลดความเสี่ยงจากการเข้าถึงโดยไม่ได้รับอนุญาต

**วิธีจัดการ API Configuration:**
- แก้ไขใน `.env` file หรือ environment variables
- Restart application เพื่อให้การเปลี่ยนแปลงมีผล

## หมายเหตุ
- เฉพาะ Admin เท่านั้นที่สามารถเข้าถึงและแก้ไขข้อมูลนี้ได้
- การเปลี่ยนแปลงจะมีผลทันทีหลังจากบันทึก
- ระบบจะแสดงการเปลี่ยนแปลงก่อนบันทึกเพื่อให้ Admin ตรวจสอบได้
- ข้อมูลถูกเก็บใน employees.json เพื่อความสอดคล้องกับระบบเดิม
- RM เดิมจะถูกลดตำแหน่งเป็น ZM อัตโนมัติ
- API configuration ไม่สามารถแก้ไขผ่าน UI ได้เพื่อความปลอดภัย

