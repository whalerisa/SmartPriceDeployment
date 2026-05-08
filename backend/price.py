# price.py (UPDATED - สูตรปลอดภัยขึ้น)
import pandas as pd
import numpy as np
import re
import math

# ===== flexible column picking =====
CAND_QTY      = ["Quantity", "Qty", "จำนวน", "ปริมาณ"]
CAND_E        = ["_RelevantSales"] 
CAND_SHIPMENT = ["DeliveryType", "Shipment Method Code", "shipment", "ขนส่ง", "วิธีรับสินค้า"]
COL_TIER      = "_Tier_Z"  
CAND_SDM      = ["pkg_size", "sdm", "H", "Package Size", "SDM"]

def _pick_col(df: pd.DataFrame, candidates: list[str], default=None):
    for c in candidates:
        if c in df.columns:
            return c
    low_cols = {str(c).strip().lower(): c for c in df.columns}
    for c in candidates:
        key = str(c).strip().lower()
        if key in low_cols:
            return low_cols[key]
    return default

# ===== weights =====
W_QTY   = 0.3382
W_E     = 0.3971
W_SHIP  = 0.2647

# ===== mapping Tier → คอลัมน์ราคาที่ใช้คั่น =====
INTERP_COLS = {
    "R2->R1": ("priceR1", "priceR2"),
    "R1->W2": ("priceW2", "priceR1"),
    "W2->W1": ("priceW1", "priceW2"),
    "W1->P":  ("priceP",  "priceW1"), 
    "P->P":   ("priceP",  "priceP"),
}
DEFAULT_COLS = ("priceR2", "priceR1")

# ---------- 3 score functions (0.0-1.0) ----------

# ❗️ 1. (แก้ไข) เพิ่ม try-except เพื่อดักค่า pkg_size ที่เป็น None/NaN
def _score_qty01(qty: float, pkg_size: float) -> float:
    try:
        qty_f = float(qty)
        pkg_size_f = float(pkg_size)
        
        # (ตรวจสอบ NaN เพิ่มเติม)
        if pd.isna(pkg_size_f) or pkg_size_f == 0:
            return 0.0 
        
        score = qty_f / pkg_size_f
        return min(score, 1.0)
    except (ValueError, TypeError):
        # (ถ้า pkg_size เป็น "" หรือ None แล้ว float() พัง)
        return 0.0 # ❗️❗️ <--- จุดนี้คือจุดที่แก้ Error (คืนค่า 0.0 แทน None)

# ❗️ 2. (แก้ไข) เพิ่ม try-except เพื่อดักค่า e_val ที่เป็น None/NaN
def _score_e01(e_val: float) -> float:
    try:
        e = float(e_val)
        if pd.isna(e):
             return 0.0
        score = np.log1p(e) / 13.0 # 13 คือค่าคงที่
        return min(score, 1.0)
    except (ValueError, TypeError):
        return 0.0 # ❗️❗️ <--- จุดนี้คือจุดที่แก้ Error (คืนค่า 0.0 แทน None)

# ❗️ 3. (แก้ไข) เพิ่ม try-except (เผื่อไว้)
def _score_ship01(ship_val: str) -> float:
    try:
        if str(ship_val).strip() == "1": # 1 = PICKUP
            return 1.0
    except Exception:
        pass # (ไม่เป็นไร เพราะสุดท้ายจะ return 0.0)
    return 0.0 # 0 = DELIVERY (หรือค่า default)

# (ส่ง col_sdm เข้าไป)
def _calc_score01(row, col_qty, col_e, col_ship, col_sdm):
    qty01  = _score_qty01(row.get(col_qty), row.get(col_sdm)) 
    e01    = _score_e01(row.get(col_e))
    ship01 = _score_ship01(row.get(col_ship))
    total  = (qty01 * W_QTY + e01 * W_E + ship01 * W_SHIP) # (ตอนนี้ qty01, e01, ship01 เป็น 0.0)
    return qty01, e01, ship01, total

# ---------- ฟังก์ชันหลัก ----------
def Price(df: pd.DataFrame) -> pd.DataFrame:
    col_qty  = _pick_col(df, CAND_QTY) or CAND_QTY[0]
    col_e    = _pick_col(df, CAND_E) or CAND_E[0]
    col_ship = _pick_col(df, CAND_SHIPMENT) or CAND_SHIPMENT[0]
    col_sdm  = _pick_col(df, CAND_SDM) 

    scores = df.apply(
        lambda r: _calc_score01(r, col_qty, col_e, col_ship, col_sdm),
        axis=1, result_type="expand"
    )
    scores.columns = ["_QtyScore", "_EScore", "_ShipScore", "_Score01"]
    out = pd.concat([df.reset_index(drop=True), scores], axis=1)

    def _interp_price(row):
        # ⭐ ถ้าลูกค้า "ขายสด" → ใช้ priceR2 โดยตรง
        if row.get("_ForceR2", False):
            try:
                r2_price = float(row.get("priceR2", 0))
                if pd.isna(r2_price):
                    return row.get("price", 0)
                return r2_price
            except Exception:
                return row.get("price", 0)
        
        score = row["_Score01"]
        
        # normalize tier first
        raw = str(row.get(COL_TIER, ""))

        tier = (
        raw.replace("→", "->")
            .replace("–", "-")
            .replace("—", "-")
            .replace(" ", "")
            .replace("\n", "")
            .replace("\r", "")
            .strip()
            .upper()
        )

        col_low, col_high = INTERP_COLS.get(tier, DEFAULT_COLS)
        try:
            low_price = float(row.get(col_low))
            high_price = float(row.get(col_high))
            if pd.isna(low_price) or pd.isna(high_price):
                return row.get("price") 
        except Exception:
            return row.get("price") 
            
        new_price = low_price + (high_price - low_price) * (1-score)
        
        if pd.isna(new_price):
            return row.get("price")
            
        return new_price

    out["NewPrice"] = out.apply(_interp_price, axis=1)
    
    def _apply_payment_term_markup(row):
        term = str(row.get("payment_terms") or "").strip().lower()
        category = str(row.get("category") or "").strip().upper()
        credit_terms = row.get("credit_terms") or {}
        
        # FIX: Handle NoneType for NewPrice if row.get returns None explicitly
        val = row.get("NewPrice")
        if val is None:
            val = 0
        base_price = float(val)

        # mapping markup %
        term_markup = {
            0:   0.000,  # 0 วัน
            15:  0.003,  # 0.30%
            30:  0.006,  # 0.60%
            45:  0.009,  # 0.90%
            60:  0.012,  # 1.20%
            90:  0.015,  # 1.50%
        }

        # ถ้ามี credit_terms จาก API ให้ใช้ตาม category
        days = None
        if isinstance(credit_terms, dict) and credit_terms:
            # Map category to credit term key
            category_map = {
                "G": "gs",  # กระจก/กาว
                "A": "ae",  # อลูมิเนียม/อุปกรณ์
                "S": "ae",  # ซิลิโคน → ใช้เหมือน A
                "Y": "yc",  # ยิปซัม/โครงคร่าว
                "C": "yc",  # C-Line → ใช้เหมือน Y
                "E": "ae",  # อื่นๆ → ใช้เหมือน A
            }
            
            credit_key = category_map.get(category, "ae")
            days = credit_terms.get(credit_key, None)
        
        # ถ้าไม่มี credit_terms หรือไม่เจอ ให้ใช้วิธีเดิม (parse จาก payment_terms string)
        if days is None:
            # 1) ดึงตัวเลขทั้งหมดในสตริง เช่น "NET 30 DAYS", "30.0", "CREDIT60" → [30], [30,0], [60]
            nums = re.findall(r"\d+", term)
            if nums:
                # ใช้ค่ามากสุดเผื่อเคส "30.0" จะได้ 30 แทน 0
                days = max(int(n) for n in nums)
            else:
                # เผื่อเคสที่เขียนว่า "cash", "cod" ให้ถือเป็น 0 วัน
                if any(k in term for k in ["cash", "cod"]):
                    days = 0

        pct = term_markup.get(days, 0.0)

        return base_price * (1 + pct)
    
    

    
       


    out["NewPrice"] = out.apply(_apply_payment_term_markup, axis=1)
    # ปัดราคาต่อหน่วยลง 2 ทศนิยม (ราคาขายจริง)
    def _safe_ceil(x):
        try:
            val = float(x or 0)
            if math.isnan(val) or math.isinf(val):
                return 0.0
            return math.ceil(val * 100) / 100
        except Exception:
            return 0.0

    out["NewPrice"] = out["NewPrice"].apply(_safe_ceil)

    return out