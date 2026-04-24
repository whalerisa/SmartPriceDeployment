# การปรับปรุงการคำนวณ Mean และ Standard Deviation

## สรุปการเปลี่ยนแปลง

ระบบได้ปรับปรุงให้คำนวณค่า mean และ sd จากข้อมูล Customer table ในฐานข้อมูลแบบ real-time แทนการใช้ค่าคงที่ใน JSON file

## ไฟล์ที่มีการเปลี่ยนแปลง

### 1. `backend/LevelPrice.py`
- **ลบฟังก์ชัน:** `load_statistics_from_file()` (ไม่ใช้ JSON file แล้ว)
- **เปลี่ยนชื่อฟังก์ชัน:** `calculate_statistics_from_invoices()` → `calculate_statistics_from_database()`
- **ปรับปรุงฟังก์ชัน:** `load_statistics()` - คำนวณจาก database เท่านั้น (ไม่มี fallback)
- **เพิ่ม Error Handling:** หากคำนวณไม่ได้จะ throw Exception แทนการใช้ fallback

### 2. `backend/statistics_router.py`
- **อัปเดต API responses:** เปลี่ยน source จาก "calculated_from_invoices" เป็น "calculated_from_database"
- **ปรับปรุง error handling:** ใช้ HTTPException แทนการ fallback

### 3. **ไฟล์ที่ลบออก:**
- `backend/mean_sd.json` ❌
- `dist/smart_pricing/mean_sd.json` ❌  
- `dist/smart_pricing/_internal/mean_sd.json` ❌

## การทำงานของระบบใหม่

### SQL Query ที่ใช้คำนวณ
```sql
SELECT 
    CAST(accum_6m AS FLOAT) as accum_6m,
    CAST(frequency AS FLOAT) as frequency,
    CAST(DATEDIFF(YEAR, customer_date, GETDATE()) AS FLOAT) as tenure_years
FROM dbo.Customer
WHERE accum_6m > 0 
    AND frequency > 0
    AND customer_date IS NOT NULL
```

**หมายเหตุ:** ระบบใช้ข้อมูลจาก `Customer` table ซึ่งมีค่า `accum_6m` และ `frequency` ที่คำนวณไว้แล้ว (อัปเดตโดย cache refresh job)

### ค่าที่คำนวณ
1. **accum_6m_ln_mean/sd**: ค่าเฉลี่ย/ส่วนเบี่ยงเบนของ ln(ยอดซื้อสะสม 6 เดือน + 1)
2. **frequency_mean/sd**: ค่าเฉลี่ย/ส่วนเบี่ยงเบนของความถี่การซื้อ (จำนวน Invoice)
3. **tenure_mean/sd**: ค่าเฉลี่ย/ส่วนเบี่ยงเบนของอายุลูกค้า (ปี)

### Cache System
- **ระยะเวลา Cache:** 1 ชั่วโมง
- **การทำงาน:** คำนวณครั้งแรก → เก็บใน memory → ใช้ค่า cache จนกว่าจะหมดอายุ
- **ประโยชน์:** ลดการ query database และการคำนวณซ้ำ

## การใช้งาน API ใหม่

### ดูค่า Statistics ปัจจุบัน
```bash
GET /api/statistics/current
```

**Response:**
```json
{
  "statistics": {
    "accum_6m_ln_mean": 12.63,
    "accum_6m_ln_sd": 2.20,
    "frequency_mean": 133.42,
    "frequency_sd": 149.51,
    "tenure_mean": 6.90,
    "tenure_sd": 6.58
  },
  "cache_info": {
    "cached": true,
    "cache_age_minutes": 15.5,
    "cache_valid": true,
    "cache_duration_minutes": 60
  },
  "source": "calculated_from_invoices"
}
```

### บังคับคำนวณใหม่
```bash
POST /api/statistics/refresh
```

### ล้าง Cache
```bash
DELETE /api/statistics/cache
```

## ข้อดีของระบบใหม่

1. **ข้อมูลเป็นปัจจุบัน:** ใช้ข้อมูล Customer table จริงแทนค่าคงที่
2. **อัตโนมัติ:** คำนวณใหม่ทุก 1 ชั่วโมง
3. **มีประสิทธิภาพ:** ใช้ cache เพื่อลดการคำนวณซ้ำ
4. **ยืดหยุ่น:** สามารถบังคับ refresh ได้ตามต้องการ
5. **ไม่พึ่งพาไฟล์ภายนอก:** คำนวณจาก database เท่านั้น
6. **Error Handling ที่ดีขึ้น:** แจ้งข้อผิดพลาดชัดเจนหากคำนวณไม่ได้

## การ Monitor และ Debug

- ใช้ `GET /api/statistics/cache-info` เพื่อดูสถานะ cache
- ดู log ใน console เพื่อติดตามการคำนวณ
- ใช้ `POST /api/statistics/refresh` เพื่อทดสอบการคำนวณใหม่

## Breaking Changes

⚠️ **สำคัญ:** ระบบไม่ใช้ไฟล์ `mean_sd.json` อีกต่อไป หากฐานข้อมูลไม่สามารถเข้าถึงได้ ระบบจะ error แทนการใช้ค่าเก่า

## การ Rollback (หากจำเป็น)

หากต้องการกลับไปใช้ค่าคงที่ สามารถ:
1. สร้างไฟล์ `backend/mean_sd.json` ใหม่
2. เพิ่มฟังก์ชัน `load_statistics_from_file()` กลับมา
3. แก้ไข `load_statistics()` ให้มี fallback