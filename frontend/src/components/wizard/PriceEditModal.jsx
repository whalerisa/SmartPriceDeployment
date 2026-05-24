// src/components/wizard/PriceEditModal.jsx
import { useState } from "react";

// ฟังก์ชันปัดราคาให้ลง .50 หรือ .00
function roundUp050(x) {
  if (x < 1) {
    return Math.round(x * 100) / 100;
  }
  // ⭐ FIX: ใช้ epsilon เพื่อจัดการ floating-point precision error
  // ป้องกันกรณี 478.00000000000006 ถูกปัดเป็น 478.50
  const epsilon = 1e-9;
  return Math.ceil((x - epsilon) * 2) / 2;
}

export default function PriceEditModal({ item, calculatedItem, onClose, onSave, hasPromotion = false }) {
  const cat = (item.category || String(item.sku || "").slice(0, 1)).toUpperCase();
  const isGlass = cat === "G";
  const isAluminium = cat === "A";
  const [isPromotion, setIsPromotion] = useState(false);
  
  // ⭐ ถ้าไม่มีโปรโมชั่นสำหรับ SKU นี้ ให้ disable checkbox
  const canMarkAsPromotion = hasPromotion;

  // สำหรับกระจก
  const currentSqft = Number(item.sqft_sheet ?? item.sqft ?? 0);
  const isProjectPrice = calculatedItem?.priceSource === "project";
  
  // ⭐ เมื่อเป็นราคาโครงการ UnitPrice เป็นราคาต่อตารางฟุตแล้ว ไม่ต้องคูณ sqft
  const currentPricePerSheet =
    item.priceSource === "manual"
      ? Number(item.price_per_sheet ?? Number(item.UnitPrice ?? 0) * currentSqft)
      : isProjectPrice
      ? Number(calculatedItem?.UnitPrice ?? 0)  // ⭐ ราคาโครงการเป็นราคาต่อตารางฟุตแล้ว
      : Number(calculatedItem?.price_per_sheet ?? item.price_per_sheet ?? 0);

  console.log('🔧 [PRICE EDIT MODAL] isProjectPrice:', isProjectPrice);
  console.log('🔧 [PRICE EDIT MODAL] calculatedItem?.priceSource:', calculatedItem?.priceSource);
  console.log('🔧 [PRICE EDIT MODAL] calculatedItem?.UnitPrice:', calculatedItem?.UnitPrice);
  console.log('🔧 [PRICE EDIT MODAL] currentPricePerSheet:', currentPricePerSheet);
  console.log('🔧 [PRICE EDIT MODAL] item.priceSource:', item.priceSource);

  // ⭐ ดึงราคาปกติ (ราคาอ้างอิงจากระบบ) - แยกตามประเภทสินค้า
  let normalPrice = 0;
  if (isGlass) {
    // กระจก: ใช้ priceW1 * sqft_sheet เพื่อได้ราคาต่อแผ่น
    const w1PerSqft = Number(calculatedItem?.priceW1 ?? item.priceW1 ?? 0);
    normalPrice = w1PerSqft * currentSqft;
  } else {
    // สินค้าอื่นๆ: ใช้ priceW1 โดยตรง (หรือคูณน้ำหนักถ้าเป็นอลู)
    const w1Base = Number(calculatedItem?.priceW1 ?? item.priceW1 ?? 0);
    if (isAluminium) {
      const weight = Number(item.weight ?? item.product_weight ?? calculatedItem?.product_weight ?? 0);
      normalPrice = w1Base * weight;
    } else {
      normalPrice = w1Base;
    }
  }

  console.log('💰 PriceEditModal - Normal Price:', normalPrice);
  console.log('💰 PriceEditModal - isGlass:', isGlass, 'isAluminium:', isAluminium);
  console.log('💰 PriceEditModal - calculatedItem:', calculatedItem);
  console.log('💰 PriceEditModal - item:', item);

  // ถ้ามี pricePerSqft เก็บไว้แล้ว ให้ใช้ค่านั้น ไม่งั้นคำนวณจาก pricePerSheet / sqft
  const currentPricePerSqft =
    item.priceSource === "manual" && item.pricePerSqft
      ? Number(item.pricePerSqft)
      : isProjectPrice
      ? currentPricePerSheet  // ⭐ ราคาโครงการเป็นราคาต่อตารางฟุตแล้ว ไม่ต้องหาร
      : currentSqft > 0 
        ? currentPricePerSheet / currentSqft 
        : 0;

  const [pricePerSqft, setPricePerSqft] = useState(currentPricePerSqft);

  // สำหรับอลูมิเนียม
  const currentUnitPrice =
    item.priceSource === "manual"
      ? Number(item.UnitPrice ?? item.price ?? 0)
      : Number(calculatedItem?.UnitPrice ?? item.UnitPrice ?? item.price ?? 0);

  const currentWeight = Number(item.weight ?? item.product_weight ?? calculatedItem?.product_weight ?? 0);

  // คำนวณราคาต่อกิโลกรัมจากราคาต่อเส้น
  // ถ้ามี pricePerKg เก็บไว้แล้ว ให้ใช้ค่านั้น ไม่งั้นคำนวณจาก unitPrice / weight
  const currentPricePerKg = 
    item.priceSource === "manual" && item.pricePerKg
      ? Number(item.pricePerKg)
      : currentWeight > 0 
        ? currentUnitPrice / currentWeight 
        : 0;

  const [pricePerKg, setPricePerKg] = useState(currentPricePerKg);
  const [weight, setWeight] = useState(currentWeight);

  // สำหรับสินค้าอื่นๆ (ไม่ใช่กระจกหรืออลู)
  const otherProductUnitPrice =
    item.priceSource === "manual"
      ? Number(item.UnitPrice ?? item.price ?? 0)
      : Number(calculatedItem?.UnitPrice ?? item.UnitPrice ?? item.price ?? 0);

  const [otherPrice, setOtherPrice] = useState(otherProductUnitPrice);

  // คำนวณราคาใหม่ (อลูมิเนียมไม่ปัด สินค้าอื่นปัด)
  const calculatedPricePerSheet = isGlass ? roundUp050(pricePerSqft * currentSqft) : pricePerSqft * currentSqft;
  const calculatedPricePerLine = isAluminium ? pricePerKg * weight : roundUp050(pricePerKg * weight);

  const handleSave = () => {
    console.log('💾 [PRICE EDIT] Saving manual price:', {
      sku: item.sku,
      category: cat,
      isGlass,
      isAluminium,
      isProjectPrice,
      isPromotion
    });
    
    if (isGlass) {
      // บันทึกราคาต่อแผ่น (จากการคำนวณ)
      const saveData = {
        unitPrice: calculatedPricePerSheet,
        pricePerSqft: pricePerSqft,
        isPromotion,
      };
      console.log('💾 [PRICE EDIT] Glass price data:', saveData);
      onSave(saveData);
    } else if (isAluminium) {
      // บันทึกราคาต่อเส้น (จากการคำนวณ) และน้ำหนัก
      const saveData = {
        unitPrice: calculatedPricePerLine,
        pricePerKg: pricePerKg,
        weight: weight,
        isPromotion,
      };
      console.log('💾 [PRICE EDIT] Aluminium price data:', saveData);
      onSave(saveData);
    } else {
      // สินค้าอื่นๆ
      const saveData = {
        unitPrice: otherPrice,
        isPromotion,
      };
      console.log('💾 [PRICE EDIT] Other product price data:', saveData);
      onSave(saveData);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="px-6 py-4 border-b">
          <h3 className="text-lg font-semibold text-gray-800">แก้ไขราคา</h3>
          <p className="text-sm text-gray-600 mt-1">{item.name}</p>
          <p className="text-xs text-gray-500">{item.sku}</p>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          {isGlass ? (
            // ฟอร์มสำหรับกระจก
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ขนาด (ตารางฟุต)
                </label>
                <input
                  type="number"
                  value={currentSqft}
                  disabled
                  className="w-full px-3 py-2 border rounded-lg bg-gray-50 text-gray-600"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ราคาต่อตารางฟุต (บาท/ตร.ฟุต)
                </label>
                <input
                  type="number"
                  value={pricePerSqft}
                  onChange={(e) => setPricePerSqft(Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  step="0.01"
                  min="0"
                />
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-sm text-gray-700 mb-2">การคำนวณ:</div>
                <div className="text-sm text-gray-600 space-y-1">
                  <div>
                    {currentSqft.toLocaleString("th-TH", { minimumFractionDigits: 2 })} ตร.ฟุต
                    × {pricePerSqft.toLocaleString("th-TH", { minimumFractionDigits: 2 })} บาท/ตร.ฟุต
                  </div>
                  <div className="text-lg font-semibold text-blue-700 mt-2">
                    = {calculatedPricePerSheet.toLocaleString("th-TH", { minimumFractionDigits: 2 })} บาท/แผ่น
                  </div>
                </div>
              </div>
            </>
          ) : isAluminium ? (
            // ฟอร์มสำหรับอลูมิเนียม
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  น้ำหนัก (กก./เส้น)
                </label>
                <input
                  type="number"
                  value={weight}
                  onChange={(e) => setWeight(Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  step="0.01"
                  min="0"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ราคาต่อกิโลกรัม (บาท/กก.)
                </label>
                <input
                  type="number"
                  value={pricePerKg}
                  onChange={(e) => setPricePerKg(Number(e.target.value))}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  step="0.01"
                  min="0"
                />
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-sm text-gray-700 mb-2">การคำนวณ:</div>
                <div className="text-sm text-gray-600 space-y-1">
                  <div>
                    {weight.toLocaleString("th-TH", { minimumFractionDigits: 2 })} กก./เส้น
                    × {pricePerKg.toLocaleString("th-TH", { minimumFractionDigits: 2 })} บาท/กก.
                  </div>
                  <div className="text-lg font-semibold text-blue-700 mt-2">
                    = {calculatedPricePerLine.toLocaleString("th-TH", { minimumFractionDigits: 2 })} บาท/เส้น
                  </div>
                </div>
              </div>
            </>
          ) : (
            // ฟอร์มสำหรับสินค้าอื่นๆ
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                ราคาต่อหน่วย (บาท)
              </label>
              <input
                type="number"
                value={otherPrice}
                onChange={(e) => setOtherPrice(Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                step="0.01"
                min="0"
              />
            </div>
          )}

          {/* ⭐ Checkbox สำหรับระบุว่าเป็นโปรโมชั่น */}
          <div className="border-t pt-4">
            <label className={`flex items-center gap-3 ${canMarkAsPromotion ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}>
              <input
                type="checkbox"
                checked={isPromotion}
                onChange={(e) => setIsPromotion(e.target.checked)}
                disabled={!canMarkAsPromotion}
                className="w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500 disabled:opacity-50"
              />
              <span className={`text-sm font-medium ${canMarkAsPromotion ? 'text-gray-700' : 'text-gray-500'}`}>
                ✓ ราคานี้เป็นโปรโมชั่น (ไม่ต้องขอราคาพิเศษ)
              </span>
            </label>
            {!canMarkAsPromotion && (
              <p className="text-xs text-gray-500 mt-2 ml-7">
                ⚠️ สินค้านี้ไม่มีโปรโมชั่น ไม่สามารถเลือกได้
              </p>
            )}
            {isPromotion && canMarkAsPromotion && (
              <p className="text-xs text-red-600 mt-2 ml-7">
                ระบบจะไม่สร้างคำขอราคาพิเศษสำหรับสินค้านี้
              </p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            ยกเลิก
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
          >
            ยืนยัน
          </button>
        </div>
      </div>
    </div>
  );
}
