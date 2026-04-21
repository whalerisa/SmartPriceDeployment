import { createContext, useReducer, useContext } from "react";

export const QuoteContext = createContext(null);
export function useQuote() {
  return useContext(QuoteContext);
}

const initialState = {
  step: 1,

  customer: null,
  deliveryAddress: null,
  vehicle: null,
  deliveryType: "PICKUP",
  ibtBranch: null,

  cart: [],

  shippingDirty: false,

  totals: {
    exVat: 0,
    vat: 0,
    grandTotal: 0,
    shippingRaw: 0,
    shippingCustomerPay: 0,
  },

  needsTax: false,
  remark: "",
  status: "new",
  quoteNo: null,
  expireDate: null,
};

function quoteReducer(state, action) {
  switch (action.type) {
    case "SET_STEP":
      return { ...state, step: action.payload };

    case "SET_CUSTOMER":
      return { ...state, customer: action.payload };

    case "SET_TAX_DELIVERY": {
      const nextDeliveryType = action.payload.deliveryType;

      return {
        ...state,
        needsTax: action.payload.needsTax,
        deliveryType: nextDeliveryType,
        ibtBranch: action.payload.ibtBranch ?? null,

        // ⭐ KEY FIX: ถ้าเป็นรับเอง → ล้างค่าขนส่งทันที
        ...(nextDeliveryType === "PICKUP"
          ? {
              shippingDirty: false,
              shippingCustomerPay: 0,
              shippingCompanyPay: 0,
              shippingCost: 0,
              distance: null,
              vehicleType: null,
              unloadHours: null,
              staffCount: null,
            }
          : {}),
      };
    }
    case "SET_QUOTE_META":
      return {
        ...state,
        id: action.payload.id,
        quoteNo: action.payload.quoteNo,
        status: action.payload.status,
      };

    case "SET_SHIPPING":
      return {
        ...state,
        shippingDirty: false,
        shippingCost: action.payload.cost,
        distance: action.payload.distance,
        shippingCustomerPay: action.payload.customerPay ?? state.shippingCustomerPay,
        shippingCompanyPay: action.payload.companyPay ?? state.shippingCompanyPay,
        vehicleType: action.payload.vehicleType ?? state.vehicleType,
        unloadHours: action.payload.unloadHours ?? state.unloadHours,
        staffCount: action.payload.staffCount ?? state.staffCount,
      };

    case "SET_DELIVERY_ADDRESS":
      return { ...state, deliveryAddress: action.payload };

    case "SET_VEHICLE":
      return { ...state, vehicle: action.payload };

    case "SET_REMARK":  // ⭐ เพิ่ม SET_REMARK case
      return { ...state, remark: action.payload };

    // -------------------------
    //ADD ITEM (รองรับ Variant + preserve meta ของ draft)
    // -------------------------
    case "ADD_ITEM": {
      const newItem = action.payload;

      // 1) normalize ให้มี key ครบ (สำหรับ item ใหม่เท่านั้น)
      const normalizedItem = {
        ...newItem,

        sqft_sheet:
          newItem.sqft_sheet !== undefined && newItem.sqft_sheet !== null
            ? Number(newItem.sqft_sheet)
            : 0,

        unit: newItem.unit ?? null,

        // ✅ ตัวตน - ใช้ค่าที่ส่งมา หรือ default เป็น "ui"
        source: newItem.source ?? "ui",

        // ✅ pricing state - ใช้ค่าที่ส่งมา หรือ default เป็น true
        needsPricing: newItem.needsPricing !== undefined ? newItem.needsPricing : true,

        pkg_size: newItem.pkg_size ?? 1,

        // คงไว้ชั่วคราว (แต่จะไม่ใช้ตัด logic)
        isDraftItem: false,

        product_weight: newItem.product_weight ?? newItem.ProductWeight ?? 0,

        variantCode: newItem.variantCode ?? newItem.VariantCode ?? null,

        product_group: newItem.product_group ?? newItem["Product Group"] ?? null,

        product_sub_group: newItem.product_sub_group ?? newItem["Product Sub Group"] ?? null,
        
        // ✅ เก็บ priceSource ถ้ามี (สำหรับราคาพิเศษ)
        priceSource: newItem.priceSource ?? (newItem.source === "db" ? "manual" : undefined),
        
        // ⭐ เก็บข้อมูล stock
        stock: newItem.stock ?? null,
        
        // ⭐ เก็บ flag isSoldByPack
        isSoldByPack: newItem.isSoldByPack ?? false,
      };

      // 2) หา item ซ้ำ “ต้อง match ด้วย sku + variantCode + sqft”
      // ⭐ normalize เพื่อใช้เทียบ identity เท่านั้น (ไม่แก้ state จริง)
      const normalizeVariant = (v) => (v === "" || v === undefined ? null : v);

      const normalizeSqft = (v) => (v === "" || v === undefined ? 0 : Number(v));

      const newVariant = normalizeVariant(normalizedItem.variantCode);
      const newSqft = normalizeSqft(normalizedItem.sqft_sheet);

      const exists = state.cart.find((it) => {
        const itVariant = normalizeVariant(it.variantCode);
        const itSqft = normalizeSqft(it.sqft_sheet);

        // 1) sku ต้องตรงเสมอ
        if (it.sku !== normalizedItem.sku) return false;

        // 2) ถ้ามี variant อย่างน้อยหนึ่งฝั่ง → ต้องเท่ากัน
        if (itVariant !== null || newVariant !== null) {
          if (itVariant !== newVariant) return false;
        }

        // 3) ถ้ามี sqft อย่างน้อยหนึ่งฝั่ง → ต้องเท่ากัน
        if (itSqft !== 0 || newSqft !== 0) {
          if (itSqft !== newSqft) return false;
        }

        return true;
      });

      // 3) ถ้าไม่ซ้ำ → เพิ่มบรรทัดใหม่ตามปกติ
      if (!exists) {
        return {
          ...state,
          shippingDirty: state.deliveryType === "DELIVERY",
          cart: [...state.cart, normalizedItem],
        };
      }

      // 4) ถ้าซ้ำ → merge qty โดย preserve meta เดิมของ exists
      return {
        ...state,
        shippingDirty: state.deliveryType === "DELIVERY",
        cart: state.cart.map((it) => {
          if (it !== exists) return it;

          return {
            ...it,
            qty: Number(it.qty) + Number(normalizedItem.qty ?? 0),
            sqft_sheet: it.sqft_sheet,
            lineTotal: undefined,
            needsPricing: it.source === "ui" ? true : false,
            product_weight: it.product_weight ?? normalizedItem.product_weight ?? 0,
            variantCode: it.variantCode ?? normalizedItem.variantCode ?? null,
            stock: it.stock ?? normalizedItem.stock ?? null, // ⭐ preserve stock
          };
        }),
      };
    }

    // UPDATE CART QTY
    // -------------------------
    case "UPDATE_CART_QTY": {
      const { sku, qty, variantCode = null, sqft_sheet = 0, from } = action.payload;

      const targetVariant = variantCode ?? null;
      const targetSqft = Number(sqft_sheet ?? 0);

      return {
        ...state,
        shippingDirty: state.deliveryType === "DELIVERY",
        cart: state.cart.map((it) => {
          const itVariant = it.variantCode ?? null;
          const itSqft = Number(it.sqft_sheet ?? it.sqft ?? 0);

          const isTarget = it.sku === sku && itVariant === targetVariant && itSqft === targetSqft;

          if (!isTarget) return it;

          const newQty = Number(qty);
          const cat = (it.category || String(it.sku || "").slice(0, 1)).toUpperCase();
          const isGlass = cat === "G";

          // =================================================
          // ⭐ CASE 1: ปรับ qty จาก CartItemRow
          // =================================================
          if (from === "cart") {
            const isSoldByPack = it.isSoldByPack || false;  // ⭐ เช็ค flag
            
            // ⭐ สำหรับกระจกที่ขายยกแพ็ก ใช้ UnitPrice แทน price_per_sheet
            const displayUnitPrice = isGlass && isSoldByPack
              ? Number(it.UnitPrice ?? it.price ?? 0)
              : isGlass
              ? Number(it.price_per_sheet ?? 0)
              : Number(it.price ?? 0);

            return {
              ...it,
              qty: newQty,
              lineTotal: displayUnitPrice * newQty,
              needsPricing: false,
            };
          }

          // =================================================
          // ⭐ CASE 2: db / draft / repeat
          // =================================================
          const rawUnitPrice = Number(it.UnitPrice ?? it.price ?? 0); // truth
          const sqft = Number(it.sqft_sheet ?? it.sqft ?? 0);

          if (isGlass) {
            const pricePerSheet = rawUnitPrice * sqft;

            return {
              ...it,
              qty: newQty,

              // 🔒 truth
              UnitPrice: rawUnitPrice,

              // ✅ display
              price_per_sheet: pricePerSheet,
              price: undefined,

              lineTotal: pricePerSheet * newQty,
              needsPricing: false,
            };
          }

          // ===== สินค้าอื่น =====
          return {
            ...it,
            qty: newQty,

            UnitPrice: rawUnitPrice,
            price: rawUnitPrice,
            price_per_sheet: undefined,

            lineTotal: rawUnitPrice * newQty,
            needsPricing: it.source === "ui",
          };
        }),
      };
    }
    // -------------------------
    // UPDATE CART PRICE (MANUAL)
    // -------------------------
    case "UPDATE_CART_PRICE": {
      console.log('🔧 [REDUCER] UPDATE_CART_PRICE triggered:', action.payload);
      
      const { 
        sku, 
        variantCode = null, 
        sqft_sheet = 0, 
        unitPrice,
        pricePerSqft,
        pricePerKg,
        weight,
        isPromotion = false
      } = action.payload;

      const targetVariant = variantCode ?? null;
      const targetSqft = Number(sqft_sheet ?? 0);

      return {
        ...state,
        cart: state.cart.map((it) => {
          const itVariant = it.variantCode ?? null;
          const itSqft = Number(it.sqft_sheet ?? it.sqft ?? 0);

          const isTarget =
            it.sku === sku && itVariant === targetVariant && itSqft === targetSqft;

          if (!isTarget) return it;

          const qty = Number(it.qty ?? 0);
          const cat = (it.category || String(it.sku || "").slice(0, 1)).toUpperCase();
          const isGlass = cat === "G";
          const isAluminium = cat === "A";
          
          console.log('🔧 [REDUCER] Updating item:', {
            sku,
            category: cat,
            isGlass,
            isAluminium,
            unitPrice,
            pricePerSqft,
            pricePerKg,
            isPromotion
          });

          // -------------------------
          // 🔒 manual price wins
          // -------------------------
          if (isGlass && itSqft > 0) {
            const pricePerSheet = unitPrice;

            return {
              ...it,
              UnitPrice: unitPrice / itSqft, // truth (บาท/ตรฟ)
              price_per_sheet: pricePerSheet, // display (บาท/แผ่น)
              price: undefined,
              lineTotal: pricePerSheet * qty,
              priceSource: "manual",        // ⭐ สำคัญ
              needsPricing: true,           // ⭐ ต้องส่งไปให้ backend ตรวจสอบ
              unit: it.unit, // ⭐ เก็บ unit ไว้
              isPromotion,                  // ⭐ เก็บ flag โปรโมชั่น
              ...(pricePerSqft && { pricePerSqft }), // เก็บราคาต่อตร.ฟุต
            };
          }

          // ===== aluminium =====
          if (isAluminium) {
            return {
              ...it,
              UnitPrice: unitPrice,
              price: unitPrice,
              price_per_sheet: undefined,
              lineTotal: unitPrice * qty,
              priceSource: "manual",
              needsPricing: true,           // ⭐ ต้องส่งไปให้ backend ตรวจสอบ
              unit: it.unit, // ⭐ เก็บ unit ไว้
              isPromotion,                  // ⭐ เก็บ flag โปรโมชั่น
              ...(pricePerKg && { pricePerKg }), // เก็บราคาต่อกก.
              ...(weight !== undefined && { weight, product_weight: weight }), // เก็บน้ำหนัก
            };
          }

          // ===== non-glass, non-aluminium =====
          return {
            ...it,
            UnitPrice: unitPrice,
            price: unitPrice,
            price_per_sheet: undefined,
            lineTotal: unitPrice * qty,
            priceSource: "manual",          // ⭐ สำคัญ
            needsPricing: true,             // ⭐ ต้องส่งไปให้ backend ตรวจสอบ
            unit: it.unit, // ⭐ เก็บ unit ไว้
            isPromotion,                    // ⭐ เก็บ flag โปรโมชั่น
          };
        }),
      };
    }

    case "REMOVE_ITEM": {
      const raw = String(action.payload ?? "");

      // รองรับ payload ได้ 3 แบบ:
      // 1) uiKey: `${sku}__${variantCode}__${sqft}` (แบบใหม่)
      // 2) pricingKey: `${sku}__${sqft}` (แบบเก่า)
      // 3) sku อย่างเดียว
      const parts = raw.split("__");
      const pSku = parts[0] || "";
      const pSqft = parts.length >= 2 ? Number(parts[parts.length - 1] ?? 0) : null;

      const normalizeSqft = (v) => Number(v ?? 0);

      const newCart = state.cart.filter((it) => {
        // แบบใหม่ (3 ส่วน) → match exact
        if (parts.length >= 3) {
          const itKey = `${it.sku}__${it.variantCode ?? ""}__${Number(
            it.sqft_sheet ?? it.sqft ?? 0
          )}`;
          return itKey !== raw;
        }

        // แบบเก่า (2 ส่วน) → match sku + sqft
        if (parts.length === 2) {
          const itSqft = normalizeSqft(it.sqft_sheet ?? it.sqft ?? 0);
          return !(it.sku === pSku && itSqft === normalizeSqft(pSqft));
        }

        // sku อย่างเดียว
        return it.sku !== raw;
      });

      if (newCart.length === 0) {
        return {
          ...state,
          cart: [],
          shippingDirty: false,
          deliveryType: "PICKUP",
          totals: {
            exVat: 0,
            vat: 0,
            grandTotal: 0,
            shippingRaw: 0,
            shippingCustomerPay: 0,
          },
          shippingCost: 0,
          shippingCustomerPay: 0,
          shippingCompanyPay: 0,
          distance: null,
          vehicleType: null,
          unloadHours: null,
          staffCount: null,
        };
      }

      return {
        ...state,
        // ลบสินค้า = cart เปลี่ยน → mark dirty เพื่อให้ recalc shipping ทำงานถูก
        shippingDirty: state.deliveryType === "DELIVERY",
        cart: newCart,
      };
    }

    // -------------------------
    // SET_CART (ใช้ใน load draft)
    // -------------------------
    case "SET_CART":
      return { ...state, cart: action.payload };

    // -------------------------
    // SET_TOTALS
    // -------------------------
    case "SET_TOTALS":
      return { ...state, totals: { ...state.totals, ...action.payload } };

    // -------------------------
    // LOAD_DRAFT
    // -------------------------
    case "LOAD_DRAFT":
      return {
        ...state,
        status: "open",
        id: action.payload.id,
        quoteNo: action.payload.quoteNo,
        step: 6,
        customer: {
          id: action.payload.customer?.id || "",
          code: action.payload.customer?.code || action.payload.customer?.id || "",
          name: action.payload.customer?.name || "",
          phone: action.payload.customer?.phone || "",
          _needsHydrate: Boolean(action.payload.customer?.code || action.payload.customer?.id),
          // ✅ preserve scoring fields
          gen_bus: action.payload.customer?.gen_bus ?? "",
          customer_date: action.payload.customer?.customer_date ?? "",
          accum_6m: action.payload.customer?.accum_6m ?? 0,
          frequency: action.payload.customer?.frequency ?? 0,

          // ✅ (optional แต่แนะนำ) ให้ชื่อตรงฝั่ง BE/Price
          payment_terms:
            action.payload.customer?.payment_terms ?? action.payload.customer?.paymentTerm ?? "",
        },

        deliveryType: action.payload.deliveryType ?? "PICKUP",
        remark: action.payload.note || "",
        cart: (action.payload.cart || []).map((it) => {
          const cat = (it.category || String(it.sku || "").slice(0, 1)).toUpperCase();
          const isGlass = cat === "G";

          // ⭐ ราคาจาก DB
          // - กระจก: price = บาท/แผ่น (บันทึกไว้แล้ว)
          // - อื่นๆ: price = บาท/หน่วย
          const priceFromDB = Number(it.price ?? it.UnitPrice ?? 0);
          const sqft = Number(it.sqft_sheet ?? it.sqft ?? 0);
          const qty = Number(it.qty ?? 0);

          if (isGlass && sqft > 0) {
            // กระจก: priceFromDB = บาท/แผ่นแล้ว
            const pricePerSheet = priceFromDB;
            const pricePerSqft = sqft > 0 ? pricePerSheet / sqft : 0;

            return {
              ...it,
              source: "db",
              unit: it.unit ?? null,
              UnitPrice: pricePerSqft, // บาท/ตรฟ (สำหรับ internal)
              price_per_sheet: pricePerSheet, // บาท/แผ่น (สำหรับแสดง)
              price: undefined,
              lineTotal: pricePerSheet * qty,
              pricePerSqft: pricePerSqft, // ⭐ เก็บ pricePerSqft สำหรับแก้ไข
              product_weight: it.product_weight ?? 0,
              isDraftItem: true,
              needsPricing: false,
              priceSource: "manual", // ⭐ ถือว่าเป็น manual เพราะมาจาก draft
            };
          } else {
            // สินค้าอื่นๆ: priceFromDB = บาท/หน่วย
            const isAluminium = cat === "A";
            const productWeight = Number(it.product_weight ?? 0);
            
            // ⭐ สำหรับอลู: ถ้ามีน้ำหนักและราคา คำนวณ pricePerKg
            let pricePerKg = undefined;
            if (isAluminium && productWeight > 0 && priceFromDB > 0) {
              pricePerKg = priceFromDB / productWeight;
            }
            
            return {
              ...it,
              source: "db",
              unit: it.unit ?? null,
              UnitPrice: priceFromDB,
              price: priceFromDB,
              price_per_sheet: undefined,
              lineTotal: priceFromDB * qty,
              product_weight: productWeight,
              weight: productWeight, // ⭐ เก็บ weight สำหรับอลู
              ...(pricePerKg && { pricePerKg }), // ⭐ เก็บ pricePerKg ถ้ามี
              isDraftItem: true,
              needsPricing: false,
              priceSource: "manual", // ⭐ ถือว่าเป็น manual เพราะมาจาก draft
            };
          }
        }),

        shippingCost: action.payload.totals?.shippingRaw ?? 0,
        shippingCustomerPay: action.payload.totals?.shippingCustomerPay ?? 0,
        shippingCompanyPay: action.payload.totals?.shippingCompanyPay ?? 0, // ถ้าคุณต้องการ
        totals: {
          ...state.totals,
          exVat: action.payload.totals?.exVat ?? 0,
          vat: action.payload.totals?.vat ?? 0,
          grandTotal: action.payload.totals?.grandTotal ?? 0,
          shippingRaw: action.payload.totals?.shippingRaw ?? 0,
          shippingCustomerPay: action.payload.totals?.shippingCustomerPay ?? 0,
        },
        expireDate: action.payload.expireDate || null,
        project_code: action.payload.project_code || null,  // ⭐ เพิ่ม project_code
      };

    case "UPDATE_ITEM_DESCRIPTION": {
      const { sku, variantCode = null, sqft_sheet = 0, name } = action.payload;

      return {
        ...state,
        cart: state.cart.map((it) => {
          const itVariant = it.variantCode ?? null;
          const itSqft = Number(it.sqft_sheet ?? it.sqft ?? 0);

          const isTarget =
            it.sku === sku && itVariant === variantCode && itSqft === Number(sqft_sheet);

          if (!isTarget) return it;

          return {
            ...it,
            name, // ✅ แก้เฉพาะ description
          };
        }),
      };
    }

    // -------------------------
    // APPLY PRICING RESULT
    // -------------------------
    case "APPLY_PRICING_RESULT": {
      const { key, priced } = action.payload;

      return {
        ...state,
        shippingDirty: state.deliveryType === "DELIVERY",
        cart: state.cart.map((it) => {

          // ⭐ FIX 1: ถ้าเป็นราคาที่ user แก้เอง → ห้าม override
          if (it.priceSource === "manual") {
            return it;
          }

          const sqft = Number(it.sqft_sheet ?? it.sqft ?? 0);
          const itKey = `${it.sku}__${sqft}`;
          if (itKey !== key) return it;

          const rawUnitPrice = Number(priced.UnitPrice ?? 0); // บาท / ตร.ฟ.
          const qty = Number(it.qty ?? 0);

          const cat = (it.category || String(it.sku || "").slice(0, 1)).toUpperCase();
          const isGlass = cat === "G";

          // -------------------------
          // ราคา (แยก truth / display)
          // -------------------------
          let price; // non-glass
          let price_per_sheet; // glass
          let lineTotal;

          if (isGlass && sqft > 0) {
            price_per_sheet = rawUnitPrice * sqft; // บาท / แผ่น
            price = undefined;
            lineTotal = price_per_sheet * qty;
          } else {
            price = rawUnitPrice; // หน่วยปกติ
            price_per_sheet = undefined;
            lineTotal = price * qty;
          }

          // -------------------------
          // metadata
          // -------------------------
          const unitFromPricing = String(priced.unit ?? "").trim();
          const productWeightFromPricing = priced.product_weight;
          const variantCodeFromPricing =
            priced.variantCode ?? priced.VariantCode ?? it.variantCode ?? null;

          return {
            ...it,

            // 🔒 truth
            UnitPrice: rawUnitPrice,

            // ✅ display
            price,
            price_per_sheet,

            lineTotal,

            unit:
              unitFromPricing !== ""
                ? unitFromPricing
                : it.unit && it.unit !== "-"
                  ? it.unit
                  : null,

            product_weight:
              productWeightFromPricing != null
                ? productWeightFromPricing
                : (it.product_weight ?? 0),

            variantCode: variantCodeFromPricing,
            needsPricing: false,
            isPromotion: priced.isPromotion ?? false,  // ⭐ เก็บ flag โปรโมชั่น
          };
        }),
      };
    }

    // -------------------------
    // RESET QUOTE
    // -------------------------
    case "RESET_QUOTE":
      return { ...initialState };

    default:
      return state;
  }
}

export function QuoteProvider({ children }) {
  const [state, dispatch] = useReducer(quoteReducer, initialState);
  return <QuoteContext.Provider value={{ state, dispatch }}>{children}</QuoteContext.Provider>;
}
