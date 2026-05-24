// src/components/wizard/CartItemRow.jsx
import { useState, useEffect } from "react";
import { useItemPriceHistory } from "../../hooks/useItemPriceHistory";
import PriceEditModal from "./PriceEditModal";
import api from "../../services/api";
import { Megaphone } from "lucide-react";

function formatThaiDate(dt) {
  if (!dt) return "";
  const d = new Date(dt);
  return d.toLocaleString("th-TH", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const TrashIcon = () => (
  <img src="/assets/delete.png" alt="delete" className="h-5 w-5 mr-4 mt-1 object-contain" />
);

export default function CartItemRow({ item, index, calculatedItem, dispatch, customerCode, activeSpecialPrices, onItemClick }) {
  
  // 🔍 Log เมื่อ calculatedItem เปลี่ยน
  useEffect(() => {
    console.log(`🔍 [CartItemRow ${index}] calculatedItem changed:`, {
      sku: item.sku,
      hasCalculatedItem: !!calculatedItem,
      calculatedItem: calculatedItem ? {
        UnitPrice: calculatedItem.UnitPrice,
        price_per_sheet: calculatedItem.price_per_sheet,
        priceSource: calculatedItem.priceSource,
        _LineTotal: calculatedItem._LineTotal
      } : null
    });
  }, [calculatedItem, item.sku, index]);
  
  const cat = (item.category || String(item.sku || "").slice(0, 1)).toUpperCase();
  const isGlass = cat === "G";

  // ⭐ ตรวจสอบว่ามีราคาพิเศษที่ใช้ได้หรือไม่
  const activePrice = activeSpecialPrices?.items?.find(p => p.item_code === item.sku);
  const hasActiveSpecialPrice = !!activePrice;

  // 🔍 Debug log
  if (activeSpecialPrices?.items?.length > 0) {
    console.log(`🔍 [CartItemRow ${item.sku}] activeSpecialPrices:`, {
      hasItems: activeSpecialPrices.items.length,
      itemCodes: activeSpecialPrices.items.map(p => p.item_code),
      currentSku: item.sku,
      foundPrice: activePrice,
      hasActiveSpecialPrice
    });
  }

  // ⭐ ตรวจสอบว่าใช้ราคาโครงการหรือไม่
  const isProjectPrice = calculatedItem?.priceSource === 'project' || calculatedItem?.price_source === 'project';

  // ✅ unit price to display
  // - glass: show บาท/แผ่น (price_per_sheet)
  // - others: show บาท/หน่วย (UnitPrice/price)
  // ⭐ ถ้าขายยกแพ็ก ไม่คูณ sqft
  // ⭐ ถ้ามีราคาพิเศษที่ใช้ได้ ให้แสดงราคาพิเศษแทน
  let displayUnitPrice;
  
  if (hasActiveSpecialPrice && item.priceSource !== "manual") {
    // ใช้ราคาพิเศษที่อนุมัติแล้ว
    displayUnitPrice = Number(activePrice.special_price);
    console.log(`💰 [CartItemRow] ใช้ราคาพิเศษ: ${displayUnitPrice} สำหรับ ${item.sku}`);
  } else if (item.priceSource === "manual") {
    displayUnitPrice = isGlass
      ? item.isSoldByPack
        ? Number(item.UnitPrice ?? item.price ?? 0) // ⭐ ขายยกแพ็ก: ใช้ราคาต่อหน่วยตรงๆ
        : Number(
            item.price_per_sheet ??
              Number(item.UnitPrice ?? 0) * Number(item.sqft_sheet ?? item.sqft ?? 0)
          )
      : Number(item.UnitPrice ?? item.price ?? 0);
  } else {
    // ⭐ FIX: ต้องเช็คว่า calculatedItem มีค่าหรือไม่ ไม่ใช่เช็คว่า UnitPrice เป็น 0
    // เพราะ 0 เป็น falsy จะทำให้ข้ามไปใช้ item.price แทน
    displayUnitPrice = Number(
      (isGlass
        ? item.isSoldByPack
          ? (calculatedItem ? calculatedItem.UnitPrice : (item.UnitPrice ?? item.price ?? 0)) // ⭐ ขายยกแพ็ก: ใช้ราคาต่อหน่วยตรงๆ
          : calculatedItem?.price_per_sheet ?? item.price_per_sheet
        : (calculatedItem ? calculatedItem.UnitPrice : (item.UnitPrice ?? item.price))) ?? 0
    );
  }

  // 🔍 Debug log สำหรับราคาที่แสดง
  console.log(`💰 [CartItemRow ${item.sku}] displayUnitPrice:`, {
    displayUnitPrice,
    hasActiveSpecialPrice,
    priceSource: item.priceSource,
    calculatedUnitPrice: calculatedItem?.UnitPrice,
    itemPrice: item.price,
    itemUnitPrice: item.UnitPrice
  });
  // ✅ line total
  // - manual: trust item.lineTotal (set by reducer) else fallback compute
  // - non-manual: prefer pricing _LineTotal
  // ⭐ สำหรับกระจกขายยกแพ็ก: คำนวณใหม่เพื่อให้แน่ใจว่าถูกต้อง
  // ⭐ ถ้ามีราคาพิเศษ: คำนวณจากราคาพิเศษ
  const displayLineTotal = hasActiveSpecialPrice && item.priceSource !== "manual"
    ? displayUnitPrice * Number(item.qty || 0)  // ใช้ราคาพิเศษคำนวณ
    : item.priceSource === "manual"
    ? Number(item.lineTotal ?? displayUnitPrice * Number(item.qty || 0))
    : isGlass && item.isSoldByPack
    ? displayUnitPrice * Number(item.qty || 0)  // ⭐ ขายยกแพ็ก: คำนวณใหม่
    : Number(
        calculatedItem?._LineTotal ??
          item.lineTotal ??
          displayUnitPrice * Number(item.qty || 0)
      );



  const [editingDesc, setEditingDesc] = useState(false);
  const [descDraft, setDescDraft] = useState(item.name || "");
  const [openPriceHistory, setOpenPriceHistory] = useState(false);
  const [showPriceModal, setShowPriceModal] = useState(false);
  const [promotions, setPromotions] = useState([]);


  const { prices, loading } = useItemPriceHistory({
    sku: item.sku,
    customerCode,
    enabled: openPriceHistory,
  });

  // ดึงโปรโมชั่นที่ active สำหรับ SKU นี้
  useEffect(() => {
    const fetchPromotions = async () => {
      try {
        const response = await api.get(`/api/promotions/active-by-skus?skus=${item.sku}`);
        const promoData = response.data?.[item.sku] || [];
        setPromotions(promoData);
      } catch (error) {
        console.error('Error fetching promotions:', error);
        setPromotions([]);
      }
    };

    if (item.sku) {
      fetchPromotions();
    }
  }, [item.sku]);


  const handleQtyChange = (e) => {
    dispatch({
      type: "UPDATE_CART_QTY",
      payload: {
        sku: item.sku,
        qty: Math.max(1, Number(e.target.value)),
        variantCode: item.variantCode ?? null,
        sqft_sheet: item.sqft_sheet ?? item.sqft ?? 0,
        from: "cart",
      },
    });
  };

  const handleRemove = () => {
    const key = `${item.sku}__${item.variantCode ?? ""}__${Number(
      item.sqft_sheet ?? item.sqft ?? 0
    )}`;
    dispatch({ type: "REMOVE_ITEM", payload: key });
  };

  const commitDescription = () => {
    dispatch({
      type: "UPDATE_ITEM_DESCRIPTION",
      payload: {
        sku: item.sku,
        variantCode: item.variantCode ?? null,
        sqft_sheet: Number(item.sqft_sheet ?? item.sqft ?? 0),
        name: descDraft.trim(),
      },
    });
    setEditingDesc(false);
  };

  const handlePriceSave = (data) => {
    const cat = (item.category || String(item.sku || "").slice(0, 1)).toUpperCase();
    const isAluminium = cat === "A";

    console.log('🔄 [CART ITEM] Dispatching price update:', {
      sku: item.sku,
      category: cat,
      isAluminium,
      data
    });

    dispatch({
      type: "UPDATE_CART_PRICE",
      payload: {
        sku: item.sku,
        variantCode: item.variantCode ?? null,
        sqft_sheet: Number(item.sqft_sheet ?? item.sqft ?? 0),
        unitPrice: data.unitPrice,
        from: "manual",
        isPromotion: data.isPromotion ?? false,
        ...(data.pricePerSqft && { pricePerSqft: data.pricePerSqft }),
        ...(data.pricePerKg && { pricePerKg: data.pricePerKg }),
        ...(isAluminium && data.weight !== undefined && { weight: data.weight }),
      },
    });

    setShowPriceModal(false);
  };

  return (
    <>
              {/* ===== MAIN ROW ===== */}
              <tr className="border-b bg-white hover:bg-gray-50 cursor-pointer" onClick={onItemClick}>
                <td className="w-[40px] px-4 py-3 text-sm text-gray-600">{index + 1}</td>

                <td className="px-4 py-3 w-[240px]">
                  {editingDesc ? (
                    <input
                      autoFocus
                      value={descDraft}
                      onChange={(e) => setDescDraft(e.target.value)}
                      onBlur={commitDescription}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitDescription();
                        if (e.key === "Escape") {
                          setDescDraft(item.name || "");
                          setEditingDesc(false);
                        }
                      }}
                      className="w-full rounded border px-2 py-1 text-xs"
                    />
                  ) : (
                    <div>
                      <p
                        className="font-semibold text-xs cursor-pointer hover:underline"
                        onDoubleClick={() => setEditingDesc(true)}
                        title="ดับเบิลคลิกเพื่อแก้ไขชื่อสินค้า"
                      >
                        {item.name}
                      </p>
                      <p className="text-xs text-gray-500">{item.sku}</p>
                      
                      {/* ⭐ แสดง flag ขายยกแพ็ก */}
                      {item.isSoldByPack && item.category === "G" && (
                        <div className="mt-1 text-xs bg-orange-50 border border-orange-200 rounded px-2 py-1 text-orange-700 font-medium">
                          📦 ขายยกแพ็ก/แผ่น
                        </div>
                      )}
                      
                      {/* แสดงสต๊อก */}
                      {item.stock && (
                        <div className="mt-1 text-xs">
                          <p className="text-green-700 font-semibold">
                            สต๊อก: {item.stock.total_quantity}
                          </p>
                          {item.stock.branches && item.stock.branches.length > 0 && (
                            <div className="text-gray-600 text-[10px] space-y-0.5">
                              {item.stock.branches.map((branch) => (
                                <div key={branch['Location_Code']}>
                                  {branch['Location_Code']}: {branch.quantity}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                      
                      {/* แสดงโปรโมชั่น */}
                      {promotions.length > 0 && (
                        <div className="mt-1 space-y-1">
                          {promotions.map((promo, idx) => (
                            <div
                              key={idx}
                              className="flex items-start gap-1 bg-red-50 border border-red-200 rounded px-2 py-1"
                            >
                              <Megaphone className="w-3 h-3 text-red-600 mt-0.5 flex-shrink-0" />
                              <div className="flex-1 min-w-0">
                                <p className="text-[10px] font-semibold text-red-700 truncate">
                                  {promo.promotion_name}
                                </p>
                                {promo.promotion_text && (
                                  <p className="text-[9px] text-red-600">
                                    {promo.promotion_text}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </td>

                <td className="px-2 py-3 w-[100px] ">
                  <input
                    type="number"
                    value={item.qty}
                    min="1"
                    onChange={handleQtyChange}
                    className="w-14 rounded border p-1 text-center"
                  />
                </td>

                <td className="px-2 py-3 text-sm w-[100px]">
          <div className="relative flex items-center">
            
            {/* ราคาอยู่กลาง */}
            <div className="mx-auto flex flex-col items-center">
              <span
                className="font-semibold cursor-pointer hover:underline text-blue-700 text-center"
                onClick={() => setShowPriceModal(true)}
              >
                {Number(displayUnitPrice).toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              
              {/* ⭐ แสดงว่าเป็นโปรโมชั่น */}
              {item.isPromotion && (
                <div className="text-[9px] text-red-600 font-semibold bg-red-50 border border-red-200 px-2 py-0.5 rounded mt-1">
                  🎁 โปรโมชั่น
                </div>
              )}
              
              {/* ⭐ แสดงว่าใช้ราคาพิเศษที่อนุมัติแล้ว */}
              {hasActiveSpecialPrice && item.priceSource !== "manual" && (
                <div className="text-[9px] text-green-600 font-semibold bg-green-50 border border-green-200 px-2 py-0.5 rounded mt-1">
                  ✓ ราคาพิเศษ (ถึง {new Date(activePrice.valid_to).toLocaleDateString('th-TH', { day: 'numeric', month: 'short' })})
                </div>
              )}
              
              {/* ⭐ แสดงว่าแก้ไขราคาด้วยตนเอง */}
              {hasActiveSpecialPrice && item.priceSource === "manual" && (
                <div className="text-[9px] text-orange-600 font-semibold bg-orange-50 border border-orange-200 px-2 py-0.5 rounded mt-1">
                  ✏️ แก้ไขแล้ว
                </div>
              )}
              
              {/* ⭐ แสดงว่าใช้ราคาโครงการ */}
              {!hasActiveSpecialPrice && isProjectPrice && (
                <span className="text-[9px] text-green-600 font-semibold bg-green-50 px-1 py-0.5 rounded">
                  ราคาโครงการ
                </span>
              )}
  
             
            </div>

            {/* ปุ่มดูประวัติ ชิดขวา */}
            <button
              onClick={() => setOpenPriceHistory((v) => !v)}
              className="absolute right-0 text-gray-400 hover:text-gray-600"
            >
              ❯
            </button>

          </div>
        </td>



        <td className="px-2 text-sm py-3 font-semibold text-center ">
          {Number(displayLineTotal).toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </td>

        <td className="text-start w-[60px] ">
          <button onClick={handleRemove}>
            <TrashIcon />
          </button>
        </td>
      </tr>

      {/* ===== PRICE EDIT MODAL ===== */}
      {showPriceModal && (
        <PriceEditModal
          item={item}
          calculatedItem={calculatedItem}
          onClose={() => setShowPriceModal(false)}
          onSave={handlePriceSave}
          hasPromotion={promotions.length > 0}
        />
      )}

      {/* ===== EXPAND ROW ===== */}
      {openPriceHistory && (
        <tr className="bg-gray-100">
          <td colSpan={6} className="px-6 py-3">
            {loading && <div className="text-sm text-gray-500">กำลังโหลดประวัติราคา...</div>}

            {!loading && prices.length === 0 && (
              <div className="text-sm text-gray-500">ไม่พบประวัติราคา</div>
            )}

            {!loading && prices.length > 0 && (
              <div className="rounded-b-xl border bg-white ">
                <div className="px-4 py-2 font-semibold text-sm bg-gray-50 flex justify-between items-center">
                  <span>ประวัติราคา</span>
                  {calculatedItem?.priceSource === "history" || calculatedItem?.price_source === "history" && (
                    <span className="text-xs text-orange-600 font-medium bg-orange-50 px-2 py-1 rounded">
                      ✓ ใช้ราคาครั้งก่อน 
                    </span>
                  )}
                </div>

                <div className="divide-y">
                  {prices.slice(0, 2).map((p, i) => (
                    <div key={i} className="flex justify-between px-4 py-2 text-sm">
                      <div>
                        <div className="text-gray-600">{formatThaiDate(p.date)}</div>
                        <div className="text-xs text-gray-500">#{p.invoiceNo}</div>
                      </div>

                      <div className="text-right">
                        <div className="font-semibold text-emerald-600">
                          ฿{" "}
                          {Number(p.price).toLocaleString("th-TH", {
                            minimumFractionDigits: 2,
                          })}
                        </div>

                        <div className="text-xs text-gray-500">
                          จำนวน {Number(p.qty || 0).toLocaleString("th-TH")} {p.unit || ""}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* ⭐ แสดงราคาระบบปัจจุบันเพื่อเปรียบเทียบ */}
                {calculatedItem && (
                  <div className="px-4 py-2 bg-blue-50 border-t text-xs text-gray-600">
                    <span className="font-medium">ราคาระบบปัจจุบัน:</span>{" "}
                    <span className="font-semibold text-blue-700">
                      ฿{Number(displayUnitPrice).toLocaleString("th-TH", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                )}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
