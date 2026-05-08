import { useState, useMemo } from "react";
import { pricingKeyOf } from "../utils/quoteKeys";

/**
 * Hook สำหรับจัดการ pricing calculation logic
 * @param {Array} cart - ตะกร้าสินค้า
 * @returns {Object} { calculation, setCalculation, cartItemsKey }
 */
export function useStep6Pricing(cart) {
  // ราคาที่ได้จาก backend
  const [calculation, setCalculation] = useState({
    cart: [],
    totals: {},
    loading: true,
    error: null,
  });

  // ⭐ Track cart items ที่ต้องคำนวณ (ป้องกัน infinite loop)
  const cartItemsKey = useMemo(() => {
    if (!cart || cart.length === 0) return 'empty';
    
    // สร้าง key จาก SKU + qty + needsPricing เท่านั้น
    return cart
      .map(it => `${it.sku}:${it.qty}:${it.needsPricing ? '1' : '0'}:${it.priceSource || 'system'}`)
      .sort()
      .join('|');
  }, [cart]);

  return {
    calculation,
    setCalculation,
    cartItemsKey,
  };
}
