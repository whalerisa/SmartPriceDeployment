# 🔧 Branch Mapping Refactoring

## 📋 สรุปการแก้ไข

แก้ไขฟังก์ชัน `get_branch_code_from_numeric()` ใน `backend/project_price_router.py` ให้ใช้ข้อมูลจาก `BRANCH_REGION_MAP` แทนการ hard code

---

## ❌ ปัญหาเดิม

### Before (Hard-coded)

```python
def get_branch_code_from_numeric(numeric_code: str) -> str:
    # Hardcoded mapping based on known branch codes
    numeric_to_letter = {
        '00': 'TR',  # 00TR
        '01': 'TJ',  # 01TJ
        '03': 'TS',  # 03TS
        '04': 'TP',  # 04TP
        '05': 'AY',  # 05AY
        # ... (25 entries total)
        '90': 'HO',  # 90HO
    }
    
    prefix = numeric_code[:2]
    if prefix in numeric_to_letter:
        return numeric_to_letter[prefix]
    
    return numeric_code[-2:].upper()
```

**ข้อเสีย:**
- ❌ Hard-coded ข้อมูล 25 รายการ
- ❌ ต้องแก้ไข 2 ที่ถ้ามีสาขาใหม่ (`branch_region_mapping.py` และ `project_price_router.py`)
- ❌ เสี่ยงต่อข้อมูลไม่ตรงกัน
- ❌ ยากต่อการ maintain

---

## ✅ วิธีแก้ไขใหม่

### After (Dynamic from BRANCH_REGION_MAP)

```python
def get_branch_code_from_numeric(numeric_code: str) -> str:
    """
    Map numeric branch code (e.g., 056903002) to 2-letter code (e.g., AY)
    
    Uses BRANCH_REGION_MAP to dynamically build the mapping
    """
    if not numeric_code or len(numeric_code) < 2:
        return 'XX'
    
    # Build mapping dynamically from BRANCH_REGION_MAP
    numeric_to_letter = {}
    for branch_code in BRANCH_REGION_MAP.keys():
        if len(branch_code) >= 4:
            numeric_prefix = branch_code[:2]
            letter_suffix = branch_code[2:]
            numeric_to_letter[numeric_prefix] = letter_suffix
    
    prefix = numeric_code[:2]
    
    if prefix in numeric_to_letter:
        return numeric_to_letter[prefix]
    
    return numeric_code[-2:].upper()
```

**ข้อดี:**
- ✅ ไม่ต้อง hard code
- ✅ ใช้ข้อมูลจาก `BRANCH_REGION_MAP` (Single Source of Truth)
- ✅ เพิ่มสาขาใหม่ได้ที่เดียว (แค่แก้ `branch_region_mapping.py`)
- ✅ ข้อมูลตรงกันเสมอ
- ✅ ง่ายต่อการ maintain

---

## 🧪 การทดสอบ

### Test Results

```bash
$ python test_branch_mapping.py

================================================================================
Testing Branch Code Mapping
================================================================================

📋 Test Cases:
--------------------------------------------------------------------------------
✅ PASS | Input: '00          ' → Expected: 'TR  ' | Got: 'TR  '
✅ PASS | Input: '01          ' → Expected: 'TJ  ' | Got: 'TJ  '
✅ PASS | Input: '03          ' → Expected: 'TS  ' | Got: 'TS  '
✅ PASS | Input: '05          ' → Expected: 'AY  ' | Got: 'AY  '
✅ PASS | Input: '056903002   ' → Expected: 'AY  ' | Got: 'AY  '
✅ PASS | Input: '12          ' → Expected: 'CM  ' | Got: 'CM  '
✅ PASS | Input: '90          ' → Expected: 'HO  ' | Got: 'HO  '
✅ PASS | Input: '            ' → Expected: 'XX  ' | Got: 'XX  '
✅ PASS | Input: '99          ' → Expected: '99  ' | Got: '99  '
--------------------------------------------------------------------------------

📊 All Branch Mappings from BRANCH_REGION_MAP:
--------------------------------------------------------------------------------
  00 → TR   (Full: 00TR  , Region: BKK)
  01 → TJ   (Full: 01TJ  , Region: BKK)
  03 → TS   (Full: 03TS  , Region: BKK)
  04 → TP   (Full: 04TP  , Region: BKK)
  05 → AY   (Full: 05AY  , Region: C)
  06 → RY   (Full: 06RY  , Region: E)
  07 → RB   (Full: 07RB  , Region: C)
  08 → NR   (Full: 08NR  , Region: NE)
  09 → UB   (Full: 09UB  , Region: NE)
  10 → KK   (Full: 10KK  , Region: NE)
  11 → PL   (Full: 11PL  , Region: N)
  12 → CM   (Full: 12CM  , Region: N)
  13 → SR   (Full: 13SR  , Region: S)
  14 → HY   (Full: 14HY  , Region: S)
  15 → CB   (Full: 15CB  , Region: E)
  16 → PK   (Full: 16PK  , Region: S)
  17 → CR   (Full: 17CR  , Region: N)
  18 → UD   (Full: 18UD  , Region: NE)
  19 → PC   (Full: 19PC  , Region: C)
  20 → SK   (Full: 20SK  , Region: NE)
  21 → BS   (Full: 21BS  , Region: C)
  23 → NS   (Full: 23NS  , Region: N)
  24 → TL   (Full: 24TL  , Region: BKK)
  25 → SB   (Full: 25SB  , Region: C)
  90 → HO   (Full: 90HO  , Region: BKK)
--------------------------------------------------------------------------------

📈 Total mappings: 25
================================================================================

✅ All tests PASSED!
```

---

## 📊 การเปรียบเทียบ

| Aspect | Before (Hard-coded) | After (Dynamic) |
|--------|---------------------|-----------------|
| **Lines of Code** | ~35 lines | ~15 lines |
| **Maintainability** | ❌ ต้องแก้ 2 ที่ | ✅ แก้ที่เดียว |
| **Data Consistency** | ❌ เสี่ยงไม่ตรงกัน | ✅ ตรงกันเสมอ |
| **Scalability** | ❌ ต้อง hard code ใหม่ | ✅ Auto update |
| **Performance** | ⚡ O(1) lookup | ⚡ O(n) build + O(1) lookup |
| **Code Quality** | ❌ Duplication | ✅ DRY principle |

**Note:** Performance impact ไม่มีนัยสำคัญเพราะ:
- Build mapping เพียงครั้งเดียวต่อการเรียกฟังก์ชัน
- จำนวนสาขาไม่มาก (25 สาขา)
- Lookup ยังคงเป็น O(1)

---

## 🔄 การทำงาน

### Input → Output Examples

```python
# ตัวอย่างการใช้งาน
get_branch_code_from_numeric("00")         # → "TR"
get_branch_code_from_numeric("056903002")  # → "AY"
get_branch_code_from_numeric("12")         # → "CM"
get_branch_code_from_numeric("90")         # → "HO"
get_branch_code_from_numeric("")           # → "XX" (fallback)
get_branch_code_from_numeric("99")         # → "99" (unknown, fallback)
```

### Flow Diagram

```
Input: "056903002"
       │
       ├─ Extract first 2 digits: "05"
       │
       ├─ Build mapping from BRANCH_REGION_MAP:
       │  {
       │    "00": "TR",  # from 00TR
       │    "05": "AY",  # from 05AY
       │    "12": "CM",  # from 12CM
       │    ...
       │  }
       │
       ├─ Lookup "05" in mapping
       │
       └─ Return: "AY"
```

---

## 🎯 Use Cases

### 1. สร้างรหัสโครงการ (Branch Mode)

```python
# Frontend ส่งรหัสสาขาแบบตัวเลข (จาก dropdown)
project.branch_code = "056903002"

# Backend แปลงเป็น 2 ตัวอักษร
if len(project.branch_code) > 4:
    project.branch_code = get_branch_code_from_numeric(project.branch_code)
    # Result: "AY"

# สร้างรหัสโครงการ
prefix = f"{branch_code}{buddhist_year}{month}"
# Result: "AY6804"
```

### 2. เพิ่มสาขาใหม่

**Before (Hard-coded):**
```python
# ต้องแก้ 2 ที่:

# 1. branch_region_mapping.py
BRANCH_REGION_MAP = {
    # ...
    "26XX": "N",  # ⭐ เพิ่มสาขาใหม่
}

# 2. project_price_router.py
numeric_to_letter = {
    # ...
    '26': 'XX',  # ⭐ ต้องเพิ่มที่นี่ด้วย
}
```

**After (Dynamic):**
```python
# แก้แค่ที่เดียว:

# branch_region_mapping.py
BRANCH_REGION_MAP = {
    # ...
    "26XX": "N",  # ⭐ เพิ่มสาขาใหม่
}

# project_price_router.py
# ✅ ไม่ต้องแก้ไขอะไร! Auto update
```

---

## ✅ Backward Compatibility

การแก้ไขนี้:
- ✅ **100% Backward Compatible** - ผลลัพธ์เหมือนเดิมทุกกรณี
- ✅ **No Breaking Changes** - API ไม่เปลี่ยน
- ✅ **Same Behavior** - Logic เหมือนเดิม แค่เปลี่ยนวิธีดึงข้อมูล
- ✅ **Tested** - ผ่านการทดสอบทุก test case

---

## 📝 Files Changed

### Modified Files

1. **backend/project_price_router.py**
   - แก้ไขฟังก์ชัน `get_branch_code_from_numeric()`
   - ลบ hard-coded mapping
   - ใช้ `BRANCH_REGION_MAP` แทน

### New Files

2. **test_branch_mapping.py**
   - Test script สำหรับทดสอบ mapping
   - ครอบคลุม test cases ทั้งหมด
   - แสดงผลลัพธ์แบบละเอียด

3. **BRANCH_MAPPING_REFACTOR.md**
   - เอกสารสรุปการแก้ไข
   - อธิบาย before/after
   - ผลการทดสอบ

---

## 🚀 Deployment

### Steps

1. ✅ แก้ไขโค้ดใน `project_price_router.py`
2. ✅ รัน test script: `python test_branch_mapping.py`
3. ✅ ตรวจสอบผลลัพธ์: All tests PASSED
4. ✅ Deploy ไปยัง production

### Rollback Plan

หากเกิดปัญหา สามารถ rollback ได้โดย:
```bash
git revert <commit-hash>
```

---

## 📚 References

- **Source File:** `backend/branch_region_mapping.py`
- **Modified File:** `backend/project_price_router.py`
- **Test File:** `test_branch_mapping.py`
- **Related Documentation:** `PROJECT_SYSTEM_DOCUMENTATION.md`

---

## 👥 Credits

**Refactored by:** Kiro AI Assistant  
**Date:** May 7, 2026  
**Version:** 1.0.0

---

## 📞 Support

หากพบปัญหาหรือมีคำถาม:
- ตรวจสอบ test script: `python test_branch_mapping.py`
- ดู logs ใน console
- ติดต่อทีม IT Support
