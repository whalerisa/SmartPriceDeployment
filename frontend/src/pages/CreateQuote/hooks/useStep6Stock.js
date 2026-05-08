import { useState, useEffect } from "react";
import api from "../../../services/api.js";

/**
 * Hook สำหรับจัดการสต๊อกสินค้า
 * @param {Array} cart - ตะกร้าสินค้า
 * @returns {Object} { selectedItemStock, stockLoading, selectedItemForStock, fetchItemStock }
 */
export function useStep6Stock(cart) {
  const [selectedItemStock, setSelectedItemStock] = useState(null);
  const [stockLoading, setStockLoading] = useState(false);
  const [selectedItemForStock, setSelectedItemForStock] = useState(null);

  // ⭐ ฟังก์ชันดึงสต๊อกสินค้า
  const fetchItemStock = async (sku) => {
    if (!sku) return;
    
    setStockLoading(true);
    try {
      const res = await api.get(`/api/items/${sku}/stock`);
      setSelectedItemStock(res.data);
      setSelectedItemForStock(sku);
    } catch (err) {
      console.error("Error fetching stock:", err);
      setSelectedItemStock(null);
    } finally {
      setStockLoading(false);
    }
  };
  
  // ⭐ Auto-fetch สต๊อกเมื่อมีสินค้าในตะกร้า
  useEffect(() => {
    if (cart && cart.length > 0) {
      // ถ้ายังไม่เคยเลือกสินค้า หรือสินค้าที่เลือกไว้ไม่อยู่ในตะกร้าแล้ว
      const currentItemExists = cart.some(item => item.sku === selectedItemForStock);
      
      if (!selectedItemForStock || !currentItemExists) {
        // ดึงสต๊อกของสินค้าตัวแรก หรือสินค้าตัวล่าสุดที่เพิ่มเข้ามา
        const latestItem = cart[cart.length - 1];
        fetchItemStock(latestItem.sku);
      }
    } else {
      // ถ้าไม่มีสินค้าในตะกร้า ให้ clear สต๊อก
      setSelectedItemStock(null);
      setSelectedItemForStock(null);
    }
  }, [cart]);

  return {
    selectedItemStock,
    stockLoading,
    selectedItemForStock,
    fetchItemStock,
  };
}
