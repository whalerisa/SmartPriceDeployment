# 🚀 คำแนะนำในการ Rebuild Backend เพื่อใช้ Performance Optimization

## ปัญหา
การ upload ไฟล์ราคา 30,000+ rows ยังช้าอยู่เพราะ Docker container ยังรันโค้ดเก่า

## การแก้ไข
โค้ดถูกปรับปรุงให้เร็วขึ้นแล้วด้วย:
- ✅ Bulk query operations (ลด DB round-trips จาก ~120,000 เหลือ ~10 ครั้ง)
- ✅ `fast_executemany = True` (เร็วขึ้น 10-100 เท่าสำหรับ batch operations)
- ✅ Single commit per operation (แทนที่จะ commit ทุก batch)
- ✅ Progress streaming ด้วย Server-Sent Events

## วิธี Apply การเปลี่ยนแปลง

### Option 1: Rebuild ทั้ง stack (แนะนำ)
```bash
# หยุด containers ที่รันอยู่
docker-compose down

# Rebuild backend image และเริ่มต้นใหม่
docker-compose up -d --build backend

# หรือ rebuild ทุกอย่าง
docker-compose up -d --build
```

### Option 2: Rebuild เฉพาะ backend
```bash
# Rebuild backend image
docker-compose build backend

# Restart backend container
docker-compose restart backend
```

### Option 3: ไม่ใช้ Docker (รันตรงจาก source)
ถ้าคุณรันโดยไม่ใช้ Docker (เช่น `python main.py` หรือ `uvicorn main:app`):
```bash
# หยุด process ที่รันอยู่ (Ctrl+C)

# เริ่มใหม่
cd backend
python main.py
# หรือ
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## ตรวจสอบว่า Rebuild สำเร็จ

### 1. ตรวจสอบ Backend Logs
```bash
# ดู logs ของ backend
docker-compose logs -f backend
```

คุณควรเห็น log ประมาณ:
```
INFO: Started server process
INFO: Waiting for application startup.
INFO: Application startup complete.
```

### 2. ทดสอบ Upload ไฟล์
1. เปิด Update Price page
2. เลือก "อัปโหลดทันที"
3. เลือกไฟล์ Excel (30k+ rows)
4. กด "อัปโหลดทันที"
5. **ควรเห็น progress bar** แสดงเปอร์เซ็นต์และ status
6. **ควรเสร็จภายใน 30-60 วินาที** (แทนที่จะนานหลายนาที)

### 3. ตรวจสอบ Performance
ใน backend logs ควรเห็น:
```
INFO: Bulk UPDATE: 25000 rows...
INFO:   UPDATE batch 1 done (1000 rows)
INFO:   UPDATE batch 2 done (1000 rows)
...
INFO: Bulk INSERT: 5000 rows...
INFO:   INSERT batch 1 done (1000 rows)
...
```

## Expected Performance

### ก่อนแก้ไข:
- ⏱️ เวลาประมวลผล: **5-10 นาที** สำหรับ 30k rows
- 🔄 DB queries: ~120,000 ครั้ง (4 queries x 30k rows)
- 💾 Commits: ~30 ครั้ง (ทุก batch)

### หลังแก้ไข:
- ⚡ เวลาประมวลผล: **30-60 วินาที** สำหรับ 30k rows
- 🔄 DB queries: ~10 ครั้ง (bulk operations)
- 💾 Commits: 3 ครั้ง (UPDATE, INSERT, detail log)

**ประสิทธิภาพดีขึ้น ~10 เท่า** 🚀

## Troubleshooting

### ถ้ายังช้าอยู่:
1. ตรวจสอบว่า rebuild สำเร็จ:
   ```bash
   docker-compose ps
   docker-compose logs backend | grep "fast_executemany"
   ```

2. ตรวจสอบว่า frontend เรียก endpoint ที่ถูกต้อง:
   - เปิด Developer Console (F12)
   - ดู Network tab
   - ควรเห็น request ไปยัง `/api/admin/prices/upload/stream`

3. ตรวจสอบ SQL Server connection:
   - Connection timeout อาจทำให้ช้า
   - ตรวจสอบ network latency ระหว่าง backend <-> SQL Server

4. ตรวจสอบขนาดไฟล์:
   - ไฟล์ Excel > 10MB อาจช้าตอนอ่าน (pandas `read_excel()`)
   - ลองแปลงเป็น CSV แล้วทดสอบ

### ถ้า Frontend ไม่แสดง Progress Bar:
```bash
# Rebuild frontend ด้วย
docker-compose build frontend
docker-compose restart frontend

# Clear browser cache และ refresh
```

### ถ้ามี Error:
```bash
# ดู full logs
docker-compose logs backend --tail=100

# เข้า container เพื่อ debug
docker exec -it smart_pricing_backend bash
```

## Files ที่ถูกแก้ไข
1. `backend/services/price_upload_service.py` — เพิ่ม bulk operations + fast_executemany
2. `backend/admin_router.py` — เพิ่ม streaming endpoint `/upload/stream`
3. `frontend/src/components/updatePrice/UploadPriceExcel.jsx` — เพิ่ม progress bar + SSE handler

## หมายเหตุ
- **Scheduled upload** ไม่ได้แก้ไข (ไม่มี progress bar)
- Progress bar แสดงเฉพาะ **"อัปโหลดทันที"** เท่านั้น
- การเปลี่ยนแปลงไม่กระทบต่อข้อมูลหรือ logic การทำงาน (เร็วขึ้นเท่านั้น)
