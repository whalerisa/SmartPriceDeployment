import api from "../../../services/api.js";
import { getCustomerCode } from "../utils/customer";

/**
 * Hook สำหรับจัดการการซื้อซ้ำจากประวัติ
 * @param {Function} dispatch - Redux dispatch function
 * @returns {Object} { handleRepeatFromHistory }
 */
export function useStep6History(dispatch) {
  const handleRepeatFromHistory = async (order) => {
    if (!order) return;

    console.log("=== REPEAT CLICKED ===");
    console.log("order.id:", order?.id);
    console.log("order.cart (raw from API):", order?.cart);

    try {
      // ⭐ เรียก API เพื่อตรวจสอบวันหมดอายุ
      const quoteNo = order.quoteNo || order.id;
      const response = await api.post(`/api/quotation/${quoteNo}/reorder`);
      const { quote, isExpired, daysExpired } = response.data;

      // ⭐ แจ้งเตือนถ้าหมดอายุ
      if (isExpired) {
        const confirmReorder = window.confirm(
          `ใบเสนอราคานี้หมดอายุแล้ว ${daysExpired} วัน\n` +
          `ระบบได้คำนวณราคาใหม่ตามราคาปัจจุบันแล้ว\n\n` +
          `คุณต้องการดำเนินการต่อหรือไม่?`
        );
        
        if (!confirmReorder) {
          return; // ยกเลิกการซื้อซ้ำ
        }
      }

      (quote?.cart || []).forEach((it, i) => {
        console.log(`[order.cart][${i}]`, {
          sku: it.sku,
          qty: it.qty,
          price: it.price,
          lineTotal: it.lineTotal,
          sqft_sheet: it.sqft_sheet,
          Sqft_Sheet: it.Sqft_Sheet,
          variantCode: it.variantCode,
          VariantCode: it.VariantCode,
        });
      });

      console.log('🔍 [DRAFT] Quote object:', {
        project_code: quote.project_code,
        ProjectCode: quote.ProjectCode,
        all_keys: Object.keys(quote),
        customer: quote.customer,
        deliveryType: quote.deliveryType,
      });

      dispatch({
        type: "LOAD_DRAFT",
        payload: {
          id: null,
          quoteNo: null,

          customer: {
            id: quote.customer?.id || quote.customer?.code || "",
            code: quote.customer?.id || quote.customer?.code || "",
            name: quote.customer?.name || "",
            phone: quote.customer?.phone || "",
            _needsHydrate: true, // ⭐ ให้ Step6 auto search
          },

          deliveryType: quote.deliveryType ?? "PICKUP",
          note: quote.note ?? "",
          expireDate: quote.expireDate || null,
          project_code: quote.project_code || null,  // ⭐ เพิ่ม project_code

          cart: (quote.cart || []).map((it) => ({
            ...it,
            // ⭐ normalize สำคัญมาก
            sqft_sheet: Number(it.sqft_sheet ?? it.Sqft_Sheet ?? it.sqft ?? 0),
            variantCode: it.variantCode ?? it.VariantCode ?? "",
            price: Number(it.price ?? 0),
            lineTotal: Number(it.lineTotal ?? 0),
            Price_System: Number(it.Price_System ?? 0),
            
            source: "db", // ⭐ ใช้ราคาที่ Backend คำนวณมาแล้ว
            needsPricing: false, // ⭐ ไม่ต้องคำนวณอีก
            isDraftItem: true,
          })),

          totals: {
            exVat: 0,
            vat: 0,
            grandTotal: 0,
            shippingRaw: 0,
            shippingCustomerPay: 0,
            shippingCompanyPay: 0,
          },
        },
      });
    } catch (error) {
      console.error("Error checking quote expiration:", error);
      
      // ถ้า API ล้มเหลว ให้ใช้วิธีเดิม
      dispatch({
        type: "LOAD_DRAFT",
        payload: {
          id: null,
          quoteNo: null,

          customer: {
            id: order.customer?.id || order.customer?.code || "",
            code: order.customer?.id || order.customer?.code || "",
            name: order.customer?.name || "",
            phone: order.customer?.phone || "",
            _needsHydrate: true,
          },

          deliveryType: order.deliveryType ?? "PICKUP",
          note: order.note ?? "",
          expireDate: order.expireDate || null,

          cart: (order.cart || []).map((it) => ({
            ...it,
            sqft_sheet: Number(it.sqft_sheet ?? it.Sqft_Sheet ?? it.sqft ?? 0),
            variantCode: it.variantCode ?? it.VariantCode ?? "",
            source: "db",
            needsPricing: false,
            isDraftItem: true,
          })),

          totals: {
            exVat: 0,
            vat: 0,
            grandTotal: 0,
            shippingRaw: 0,
            shippingCustomerPay: 0,
            shippingCompanyPay: 0,
          },
        },
      });
    }
  };

  return {
    handleRepeatFromHistory,
  };
}
