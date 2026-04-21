# 💵 VAT Rate Configuration Changes

## Overview
ตอนนี้ VAT rate สามารถแก้ไขได้จากหน้า AdminConfig แทนที่จะเป็นค่าตายตัว 7%

## Changes Made

### 1. Backend (config_router.py)

#### Added VAT rate to SystemConfig model
```python
class SystemConfig(BaseModel):
    """System Configuration"""
    base_url: str
    timezone: str = "Asia/Bangkok"
    language: str = "th"
    version: str = "1.0.0"
    vat_rate: float = 0.07  # ⭐ VAT rate (default 7%)
```

#### Updated get_config endpoint
- Load VAT rate from environment variable `VAT_RATE`
- Default to 0.07 if not set
- Return vat_rate in system_config response

#### Updated update_config endpoint
- Handle vat_rate updates
- Save to environment variable `VAT_RATE`

### 2. Backend (pricing_router.py)

#### Added get_vat_rate() helper function
```python
def get_vat_rate() -> float:
    """
    ⭐ Get VAT rate from config (default 0.07 = 7%)
    """
    import os
    try:
        vat_rate_str = os.getenv("VAT_RATE", "0.07")
        vat_rate = float(vat_rate_str)
        return vat_rate
    except:
        return 0.07
```

#### Updated VAT calculations
- Changed from hardcoded `1.07` to `(1 + get_vat_rate())`
- Updated 2 locations in calculate_pricing function:
  - Line ~476: `subtotal = float(round(gross_before_vat / (1 + get_vat_rate()), 2))`
  - Line ~1016: `subtotal = float(round(gross_before_vat / (1 + get_vat_rate()), 2))`

### 3. Frontend (AdminConfig.jsx)

#### Added System Settings Tab
- New tab: "⚙️ การตั้งค่าระบบ"
- Three settings:
  1. **VAT Rate** (💵 อัตราภาษีมูลค่าเพิ่ม)
     - Input: number field (0-1)
     - Display: percentage (e.g., 0.07 = 7%)
     - Default: 0.07
  
  2. **Timezone** (🌍 เขตเวลา)
     - Input: text field
     - Default: Asia/Bangkok
  
  3. **Language** (🗣️ ภาษา)
     - Input: dropdown (Thai/English)
     - Default: th

#### UI Structure
```
Tab Navigation:
├─ 💰 ระดับราคาอนุมัติ
├─ 🔐 สิทธิ์การเข้าถึง
└─ ⚙️ การตั้งค่าระบบ (NEW)

System Settings Tab Content:
├─ VAT Rate Input
│  ├─ Number input (step 0.01, min 0, max 1)
│  ├─ Display percentage
│  └─ Example: 0.07 = 7%, 0.10 = 10%
├─ Timezone Input
│  └─ Text field
└─ Language Dropdown
   ├─ Thai (th)
   └─ English (en)
```

### 4. Frontend (Step6_Summary.jsx)

#### Added VAT rate state
```javascript
const [vatRate, setVatRate] = useState(0.07);

// Load VAT rate from config
useEffect(() => {
  const loadVatRate = async () => {
    try {
      const response = await api.get("/api/config/settings");
      const rate = response.data?.system_config?.vat_rate || 0.07;
      setVatRate(rate);
      console.log('[VAT] Loaded VAT rate:', rate);
    } catch (err) {
      console.log('[VAT] Failed to load VAT rate, using default 0.07');
      setVatRate(0.07);
    }
  };
  
  loadVatRate();
}, []);
```

#### Updated VAT calculations
- Changed from hardcoded `0.07` to `vatRate` state variable
- Updated 3 locations:
  - Line ~534: `const vat = Math.round(grossBeforeVat * vatRate * 100) / 100;`
  - Line ~661: `const vat = Math.round(grossBeforeVat * vatRate * 100) / 100;`
  - Line ~1367: `const vat = _round2(grossBeforeVat * vatRate);`

#### Updated VAT label
- Changed from static "ภาษีมูลค่าเพิ่ม (7%)" to dynamic
- New label: `` `ภาษีมูลค่าเพิ่ม (${(vatRate * 100).toFixed(1)}%)` ``
- Example: If VAT rate is 0.10, label shows "ภาษีมูลค่าเพิ่ม (10%)"

## How to Use

### Admin: Change VAT Rate
1. Go to AdminConfig page (⚙️ การตั้งค่าระบบ)
2. Click "⚙️ การตั้งค่าระบบ" tab
3. Update "อัตราภาษีมูลค่าเพิ่ม" field
   - Example: 0.07 for 7%, 0.10 for 10%
4. Click "💾 บันทึก" button
5. Changes take effect immediately

### System: How VAT is Applied
1. **Frontend (Step6_Summary.jsx)**
   - Loads VAT rate from `/api/config/settings`
   - Uses it to calculate VAT on quote summary
   - Displays dynamic VAT percentage in label

2. **Backend (pricing_router.py)**
   - Loads VAT rate from environment variable `VAT_RATE`
   - Uses it to calculate VAT in pricing calculations
   - Formula: `subtotal = gross_before_vat / (1 + vat_rate)`

## Environment Variables

### VAT_RATE
- **Type**: float
- **Default**: 0.07 (7%)
- **Range**: 0 to 1
- **Example**: 
  - 0.07 = 7%
  - 0.10 = 10%
  - 0.15 = 15%

### How to Set
1. **Via AdminConfig UI** (Recommended)
   - Go to AdminConfig → ⚙️ การตั้งค่าระบบ
   - Update VAT Rate field
   - Click Save

2. **Via .env file** (For initial setup)
   ```
   VAT_RATE=0.07
   ```

3. **Via Docker environment**
   ```bash
   docker run -e VAT_RATE=0.10 ...
   ```

## Backward Compatibility

✅ **Fully backward compatible**
- Default VAT rate is 0.07 (7%) - same as before
- If VAT_RATE environment variable is not set, defaults to 0.07
- Existing quotes and orders are not affected
- Only new quotes will use the updated VAT rate

## Testing

### Test Case 1: Change VAT Rate to 10%
1. Go to AdminConfig
2. Set VAT Rate to 0.10
3. Click Save
4. Create a new quote
5. Verify: VAT label shows "ภาษีมูลค่าเพิ่ม (10%)"
6. Verify: VAT calculation is correct (10% instead of 7%)

### Test Case 2: Revert to 7%
1. Go to AdminConfig
2. Set VAT Rate to 0.07
3. Click Save
4. Create a new quote
5. Verify: VAT label shows "ภาษีมูลค่าเพิ่ม (7%)"

### Test Case 3: Default Behavior
1. Don't change VAT Rate in AdminConfig
2. Create a new quote
3. Verify: VAT label shows "ภาษีมูลค่าเพิ่ม (7%)"
4. Verify: VAT calculation uses 7%

## Files Modified

### Backend
- `backend/config_router.py`
  - Added `vat_rate` to `SystemConfig` model
  - Updated `get_config()` endpoint
  - Updated `update_config()` endpoint

- `backend/pricing_router.py`
  - Added `get_vat_rate()` function
  - Updated VAT calculations (2 locations)

### Frontend
- `frontend/src/pages/AdminConfig.jsx`
  - Added System Settings tab
  - Added VAT Rate input field

- `frontend/src/pages/CreateQuote/Step6_Summary.jsx`
  - Added `vatRate` state
  - Added `useEffect` to load VAT rate from config
  - Updated VAT calculations (3 locations)
  - Updated VAT label to show dynamic percentage

## Future Enhancements

Possible future improvements:
1. Add VAT rate history/audit log
2. Support multiple VAT rates for different product categories
3. Add VAT rate effective date (e.g., "VAT 7% until 2024-12-31, then 10%")
4. Add VAT rate by customer type (e.g., different VAT for wholesale vs retail)
5. Add VAT rate by region/country
