# Remove Price Approval Configuration from AdminConfig

## Summary
ลบ Tab "ระดับราคาอนุมัติ" ออกจากหน้า AdminConfig และกลับไปใช้การกำหนดค่าแบบตายตัวในโค้ด ตามที่ผู้ใช้ร้องขอ

## Changes Made

### 1. Frontend Changes
**File:** `frontend/src/pages/AdminConfig.jsx`

**Removed:**
- ❌ Tab "💰 ระดับราคาอนุมัติ" ทั้งหมด
- ❌ ส่วน UI สำหรับกำหนด role_approval_scope (Sales, ZM, RM, SDM, PM)
- ❌ การแสดงลำดับการอนุมัติ (Approval Logic Reference)

**Changed:**
- ✅ เปลี่ยน default tab จาก "price" เป็น "access"
- ✅ Tab Navigation แสดงเฉพาะ: สิทธิ์การเข้าถึง, จัดการภาค, การตั้งค่าระบบ

**Result:**
- หน้า AdminConfig ไม่มี Tab "ระดับราคาอนุมัติ" อีกต่อไป
- ผู้ใช้ไม่สามารถแก้ไขขอบเขตการอนุมัติราคาผ่าน UI ได้

### 2. Backend Changes

#### File: `backend/config_router.py`

**Removed:**
1. **RoleApprovalScope Model:**
   ```python
   class RoleApprovalScope(BaseModel):
       min_level: str
       max_level: str
   ```

2. **PriceConfig.role_approval_scope field:**
   - ลบ `role_approval_scope: Dict[str, RoleApprovalScope] = {}` ออกจาก PriceConfig

3. **GET /config/settings endpoint:**
   - ลบการโหลด role_approval_scope จาก config_cache
   - ลบการส่งค่า role_approval_scope ใน response

4. **PUT /config/settings endpoint:**
   - ลบการอัปเดต role_approval_scope
   - ลบการบันทึกค่า ROLE_APPROVAL_SCOPE ลง .env file
   - ลบ import `set_role_approval_scope` จาก config_cache

**Result:**
- Backend API ไม่รับ/ส่งค่า role_approval_scope อีกต่อไป
- การตั้งค่า role_approval_scope ไม่ถูกบันทึกลง .env file

#### File: `backend/special_price_request_router.py`

**Changed:**
1. **Removed `get_config_settings()` function:**
   - ลบฟังก์ชันที่อ่านค่าจาก config_cache

2. **Updated `get_default_config()` function:**
   ```python
   def get_default_config() -> Dict[str, Any]:
       """
       Get default config with hardcoded role approval scope.
       
       Logic การอนุมัติ (ตายตัว):
       - ราคา >= R1: ไม่ต้องขออนุมัติ
       - R1 > ราคา >= W2: ZM_ONLY
       - W2 > ราคา >= W1: ZM_THEN_RM
       - W1 > ราคา >= SDM: SDM_APPROVAL
       - ราคา < SDM: PM_APPROVAL
       """
       return {
           "price_config": {
               "role_approval_scope": {
                   "Sales": {"min_level": "R2", "max_level": "R2"},
                   "ZM": {"min_level": "R1", "max_level": "W2"},
                   "RM": {"min_level": "W2", "max_level": "W1"},
                   "SDM": {"min_level": "W1", "max_level": "SDM"},
                   "PM": {"min_level": "R2", "max_level": "SDM"},
                   "CEO": {"min_level": "R2", "max_level": "SDM"}
               }
           }
       }
   ```

3. **Updated approval logic:**
   - เปลี่ยนจาก `config = await get_config_settings()` 
   - เป็น `config = get_default_config()`
   - ไม่อ่านค่าจาก config_cache อีกต่อไป

**Result:**
- ระบบใช้ค่าตายตัวที่กำหนดไว้ในโค้ด
- Logic การอนุมัติยังคงเหมือนเดิม
- ไม่ขึ้นกับการตั้งค่าใน AdminConfig

### 3. Files Not Changed

**File:** `backend/config_cache.py`
- ⚪ ไม่มีการเปลี่ยนแปลง
- ⚪ ฟังก์ชัน `get_role_approval_scope()` และ `set_role_approval_scope()` ยังคงอยู่
- ⚪ แต่ไม่ถูกเรียกใช้งานอีกต่อไป

## Approval Logic (Hardcoded)

### ลำดับการอนุมัติที่ใช้ในระบบ:

```
ราคา >= R1          → ไม่ต้องขออนุมัติ
R1 > ราคา >= W2     → ZM_ONLY (อนุมัติจาก ZM เท่านั้น)
W2 > ราคา >= W1     → ZM_THEN_RM (ต้องผ่าน ZM → RM)
W1 > ราคา >= SDM    → SDM_APPROVAL (ต้องผ่าน ZM → RM → SDM)
ราคา < SDM          → PM_APPROVAL (ต้องผ่าน ZM → RM → SDM → PM)
```

### Role Approval Scope (Hardcoded):

| Role  | Min Level | Max Level | คำอธิบาย |
|-------|-----------|-----------|----------|
| Sales | R2        | R2        | ผู้ขายทั่วไป - ไม่มีสิทธิ์อนุมัติ |
| ZM    | R1        | W2        | อนุมัติราคา R1 ถึง W2 |
| RM    | W2        | W1        | อนุมัติราคา W2 ถึง W1 |
| SDM   | W1        | SDM       | อนุมัติราคา W1 ถึง SDM |
| PM    | R2        | SDM       | อนุมัติราคาต่ำสุด (ทุกระดับ) |
| CEO   | R2        | SDM       | อนุมัติราคาทุกระดับ |

## Verification

### ✅ Frontend Verification
```bash
# Search for price tab in AdminConfig.jsx
grep -n "activeTab === \"price\"" frontend/src/pages/AdminConfig.jsx
# Result: No matches found

# Search for role_approval_scope in AdminConfig.jsx
grep -n "role_approval_scope" frontend/src/pages/AdminConfig.jsx
# Result: No matches found
```

### ✅ Backend Verification
```bash
# Search for RoleApprovalScope in config_router.py
grep -n "RoleApprovalScope" backend/config_router.py
# Result: No matches found

# Search for get_config_settings in special_price_request_router.py
grep -n "get_config_settings" backend/special_price_request_router.py
# Result: No matches found
```

### ✅ Logic Verification
```bash
# Verify hardcoded config in special_price_request_router.py
grep -A 10 "def get_default_config" backend/special_price_request_router.py
# Result: Shows hardcoded role_approval_scope
```

## Impact Analysis

### What Changed:
1. ❌ ผู้ใช้ไม่สามารถแก้ไขขอบเขตการอนุมัติราคาผ่าน UI ได้อีก
2. ❌ ค่า ROLE_APPROVAL_SCOPE ใน .env file จะไม่ถูกใช้งาน
3. ❌ ไฟล์ role_approval_scope.json จะไม่ถูกอ่าน/เขียน
4. ✅ ระบบใช้ค่าตายตัวที่กำหนดไว้ในโค้ด

### What Didn't Change:
1. ✅ Logic การอนุมัติยังคงเหมือนเดิม
2. ✅ ลำดับการอนุมัติ (ZM → RM → SDM → PM) ยังคงเหมือนเดิม
3. ✅ ระบบอนุมัติราคาพิเศษยังคงทำงานได้ปกติ
4. ✅ ไม่กระทบกับ Tab อื่นๆ ใน AdminConfig (สิทธิ์การเข้าถึง, จัดการภาค, การตั้งค่าระบบ)

## Testing Recommendations

### 1. Test AdminConfig UI
- [ ] เปิดหน้า AdminConfig
- [ ] ตรวจสอบว่าไม่มี Tab "ระดับราคาอนุมัติ" แสดงอยู่
- [ ] ตรวจสอบว่า Tab แรกที่แสดงคือ "สิทธิ์การเข้าถึง"
- [ ] ตรวจสอบว่า Tab อื่นๆ ยังทำงานได้ปกติ

### 2. Test Backend API
- [ ] เรียก GET `/api/config/settings` และตรวจสอบว่า response ไม่มี `role_approval_scope`
- [ ] ลอง PUT `/api/config/settings` พร้อม `role_approval_scope` และตรวจสอบว่าไม่มี error

### 3. Test Special Price Approval
- [ ] สร้างคำขออนุมัติราคาพิเศษใหม่
- [ ] ตรวจสอบว่า Logic การอนุมัติยังคงเหมือนเดิม
- [ ] ตรวจสอบว่าลำดับการอนุมัติ (ZM → RM → SDM → PM) ยังคงถูกต้อง
- [ ] ทดสอบการอนุมัติในแต่ละระดับ (ZM, RM, SDM, PM)

### 4. Test Edge Cases
- [ ] ทดสอบราคาที่ >= R1 (ไม่ต้องขออนุมัติ)
- [ ] ทดสอบราคาที่ R1 > ราคา >= W2 (ZM_ONLY)
- [ ] ทดสอบราคาที่ W2 > ราคา >= W1 (ZM_THEN_RM)
- [ ] ทดสอบราคาที่ W1 > ราคา >= SDM (SDM_APPROVAL)
- [ ] ทดสอบราคาที่ < SDM (PM_APPROVAL)

## Files Modified

1. ✅ `frontend/src/pages/AdminConfig.jsx` - ลบ Price Approval Tab
2. ✅ `backend/config_router.py` - ลบ role_approval_scope จาก API
3. ✅ `backend/special_price_request_router.py` - ใช้ค่าตายตัวแทนการอ่านจาก config
4. ⚪ `backend/config_cache.py` - ไม่มีการเปลี่ยนแปลง (แต่ไม่ถูกใช้งาน)

## Migration Notes

### สำหรับผู้ใช้ที่มีการตั้งค่า role_approval_scope อยู่แล้ว:

1. **ค่าเก่าจะไม่ถูกใช้งาน:**
   - ค่าที่บันทึกไว้ใน .env file จะไม่ถูกอ่าน
   - ค่าที่บันทึกไว้ใน role_approval_scope.json จะไม่ถูกอ่าน

2. **ระบบจะใช้ค่าตายตัว:**
   - ค่าที่กำหนดไว้ใน `get_default_config()` ใน special_price_request_router.py

3. **ถ้าต้องการเปลี่ยนแปลง Logic:**
   - ต้องแก้ไขโค้ดใน `get_default_config()` โดยตรง
   - ไม่สามารถเปลี่ยนแปลงผ่าน UI ได้

## Conclusion

การลบ Tab "ระดับราคาอนุมัติ" ออกจาก AdminConfig เสร็จสมบูรณ์แล้ว โดย:

1. **Frontend:** ไม่แสดง Tab และ UI สำหรับกำหนด role_approval_scope
2. **Backend:** ไม่รับ/ส่งค่า role_approval_scope ผ่าน API
3. **Approval Logic:** ใช้ค่าตายตัวที่กำหนดไว้ในโค้ด

ระบบอนุมัติราคาพิเศษยังคงทำงานได้ตามปกติโดยไม่ได้รับผลกระทบจากการเปลี่ยนแปลงนี้ เนื่องจาก Logic การอนุมัติยังคงเหมือนเดิม เพียงแต่เปลี่ยนจากการอ่านค่าจาก config เป็นการใช้ค่าตายตัวในโค้ด
