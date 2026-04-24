# การอัปโหลดไฟล์โครงการ (แบบง่าย)

## สรุป
ระบบอัปโหลดไฟล์โครงการทำงานโดยเก็บไฟล์ไปที่ folder ที่กำหนดไว้ใน Config เท่านั้น **ไม่มีการบันทึก path ใน database และไม่แสดงผลในหน้าจอ**

## การทำงาน

### 1. ผู้ใช้เลือกไฟล์
- ในหน้า Project Price Management
- ช่อง "แนบไฟล์ภาพ"
- รองรับไฟล์: รูปภาพ, PDF, DOC, DOCX, XLS, XLSX

### 2. กดบันทึกโครงการ
- ระบบจะสร้างโครงการก่อน
- จากนั้นอัปโหลดไฟล์ไปยัง API `/api/project-files/upload/{project_id}`
- ไฟล์จะถูกเก็บที่: `{project_files_folder}/{project_id}/`

### 3. ไฟล์ถูกเก็บที่ไหน
- ดูค่า `project_files_folder` ได้จากหน้า Admin Config
- Default: `./uploads/project_files`
- โครงสร้าง: `project_files_folder/project_id/timestamp_filename.ext`

## API ที่ใช้

### อัปโหลดไฟล์
```
POST /api/project-files/upload/{project_id}
Content-Type: multipart/form-data
Body: file
```

### ดาวน์โหลดไฟล์ (ถ้าต้องการ)
```
GET /api/project-files/download/{project_id}/{filename}
```

### แสดงรายการไฟล์ (ถ้าต้องการ)
```
GET /api/project-files/list/{project_id}
```

## ไฟล์ที่แก้ไข

### Frontend
- `frontend/src/pages/ProjectPriceManagement.jsx`
  - เพิ่ม state: `selectedFile`, `uploadingFile`
  - เพิ่มฟังก์ชัน: `handleFileUpload()`
  - แก้ไข: `handleSubmit()` ให้อัปโหลดไฟล์หลังสร้างโครงการ
  - แก้ไข: input file ให้รองรับหลายประเภทไฟล์

### Backend
- `backend/project_files_router.py` (มีอยู่แล้ว ไม่ต้องแก้ไข)
  - API สำหรับอัปโหลด/ดาวน์โหลด/ลบไฟล์

## การใช้งาน

1. เปิดหน้า Project Price Management
2. สร้างโครงการใหม่
3. คลิก "แนบไฟล์ภาพ" เพื่อเลือกไฟล์
4. กรอกข้อมูลโครงการ
5. กดบันทึก → ไฟล์จะถูกอัปโหลดอัตโนมัติ

## หมายเหตุ

- ไฟล์จะถูกเก็บตาม project_id
- ไม่มีการแสดงผลไฟล์ในหน้าจอ
- ไม่มีการบันทึก path ใน database
- ถ้าต้องการดูไฟล์ ต้องเข้าไปดูที่ folder โดยตรง
- ถ้าต้องการดาวน์โหลด ใช้ API `/api/project-files/download/{project_id}/{filename}`

## Troubleshooting

### ปัญหา: อัปโหลดไม่สำเร็จ
- ตรวจสอบว่าโฟลเดอร์ `project_files` มีสิทธิ์เขียนไฟล์
- ตรวจสอบ backend logs
- ตรวจสอบ browser console

### ปัญหา: ไม่รู้ว่าไฟล์อัปโหลดสำเร็จหรือไม่
- ดู browser console (F12) จะมีข้อความ "✅ File uploaded successfully"
- หรือเข้าไปดูที่ folder `project_files/{project_id}/`
