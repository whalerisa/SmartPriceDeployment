import { useState, useEffect } from "react";
import api from "../../../services/api.js";
import { getCustomerCode } from "../utils/customer";

/**
 * Hook สำหรับดึงข้อมูล Step6 (VAT rate, special prices, branches, pre-order status)
 * @param {Object} state - Redux state
 * @returns {Object} { vatRate, specialPriceRequest, activeSpecialPrices, branches, isPreOrder, requiredDeliveryDate, branchesLoading }
 */
export function useStep6Data(state) {
  // ⭐ VAT Rate state
  const [vatRate, setVatRate] = useState(0.07);
  
  // Special Price Request state
  const [specialPriceRequest, setSpecialPriceRequest] = useState(null);
  const [loadingSPR, setLoadingSPR] = useState(false);
  
  // Active special prices for customer
  const [activeSpecialPrices, setActiveSpecialPrices] = useState(null);
  
  // Branches for IBT
  const [branches, setBranches] = useState([]);
  const [branchesLoading, setBranchesLoading] = useState(false);
  
  // Pre-order state
  const [isPreOrder, setIsPreOrder] = useState(false);
  const [requiredDeliveryDate, setRequiredDeliveryDate] = useState("");

  // Load VAT rate — ใช้ endpoint สาธารณะที่ทุก role เรียกได้
  useEffect(() => {
    const loadVatRate = async () => {
      try {
        const response = await api.get("/api/config/vat-rate");
        const rate = response.data?.vat_rate || 0.07;
        setVatRate(rate);
        console.log('[VAT] Loaded VAT rate:', rate);
      } catch (err) {
        console.log('[VAT] Failed to load VAT rate, using default 0.07');
        setVatRate(0.07);
      }
    };
    
    loadVatRate();
  }, []);
  
  // Load special price request when quote is loaded
  useEffect(() => {
    const loadSpecialPriceRequest = async () => {
      if (!state.quoteNo) return;
      
      try {
        setLoadingSPR(true);
        const response = await api.get(`/api/special-price-requests/quote/${encodeURIComponent(state.quoteNo)}`);
        const spr = response.data;
        setSpecialPriceRequest(spr);
        console.log('[SPR] Loaded special price request:', spr);
      } catch (err) {
        console.log('[SPR] No special price request found for this quote');
        setSpecialPriceRequest(null);
      } finally {
        setLoadingSPR(false);
      }
    };
    
    loadSpecialPriceRequest();
  }, [state.quoteNo]);

  // Load active special prices for customer
  useEffect(() => {
    const loadActiveSpecialPrices = async () => {
      const customerCode = getCustomerCode(state.customer);
      if (!customerCode) return;
      
      try {
        console.log('[ACTIVE PRICES] Loading for customer:', customerCode);
        const response = await api.get(`/api/special-price-requests/active-prices/${customerCode}`);
        setActiveSpecialPrices(response.data);
        console.log('[ACTIVE PRICES] Loaded:', response.data);
        console.log('[ACTIVE PRICES] Items:', response.data?.items);
        if (response.data?.items) {
          console.log('[ACTIVE PRICES] Item codes:', response.data.items.map(i => i.item_code));
        }
      } catch (err) {
        console.log('[ACTIVE PRICES] No active prices found:', err);
        setActiveSpecialPrices(null);
      }
    };
    
    loadActiveSpecialPrices();
  }, [state.customer]);

  // Load branches for IBT
  useEffect(() => {
    const loadBranches = async () => {
      try {
        setBranchesLoading(true);
        const res = await api.get('/api/branches');
        setBranches(res.data.branches || []);
      } catch (err) {
        console.error('Error loading branches:', err);
        setBranches([]);
      } finally {
        setBranchesLoading(false);
      }
    };
    
    loadBranches();
  }, []);

  // โหลด pre_order และ required_delivery_date จาก quote header เมื่อเป็น draft
  useEffect(() => {
    const loadPreOrderStatus = async () => {
      if (!state.quoteNo) {
        setIsPreOrder(false);
        setRequiredDeliveryDate("");
        return;
      }

      try {
        const res = await api.get(`/api/quotation/${state.quoteNo}`);
        const preOrderValue = res.data?.header?.Pre_Order ?? res.data?.header?.pre_order ?? 0;
        const requiredDate = res.data?.header?.Required_Delivery_Date ?? res.data?.header?.required_delivery_date ?? "";
        setIsPreOrder(preOrderValue === 1);
        setRequiredDeliveryDate(requiredDate ? requiredDate.split("T")[0] : "");
      } catch (err) {
        console.error('Error loading pre-order status:', err);
        setIsPreOrder(false);
        setRequiredDeliveryDate("");
      }
    };

    loadPreOrderStatus();
  }, [state.quoteNo]);

  return {
    vatRate,
    specialPriceRequest,
    activeSpecialPrices,
    branches,
    isPreOrder,
    setIsPreOrder,
    requiredDeliveryDate,
    setRequiredDeliveryDate,
    branchesLoading,
  };
}
