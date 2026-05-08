// src/components/wizard/CustomerInfoTab.jsx
import React, { useState, useEffect } from "react";
import api from "../../services/api.js";
import { formatDateThai } from "../../utils/dateFormatter.js";
import PurchaseHistory from "./PurchaseHistory.jsx";

const CustomerInfoTab = ({ customer, customerCode }) => {
  const [customerData, setCustomerData] = useState(null);
  const [creditData, setCreditData] = useState(null);
  const [remainingCreditData, setRemainingCreditData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [creditLoading, setCreditLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // ⭐ State สำหรับราคาโครงการ
  const [projectPrices, setProjectPrices] = useState([]);
  const [projectLoading, setProjectLoading] = useState(false);

  console.log("📋 [CustomerInfoTab] Received props:", { customer, customerCode });
  console.log("📋 [CustomerInfoTab] Current creditData:", creditData);

  // ⭐ Debug: Log เมื่อ creditData เปลี่ยน
  useEffect(() => {
    console.log("🔄 [CREDIT STATE] creditData changed:", creditData);
    console.log("🔄 [CREDIT STATE] status:", creditData?.status);
  }, [creditData]);

  // โหลดข้อมูลลูกค้า
  useEffect(() => {
    console.log("🔄 [CustomerInfoTab] Component mounted/updated");
    
    return () => {
      console.log("🔄 [CustomerInfoTab] Component will unmount");
    };
  }, []);

  // โหลดข้อมูลลูกค้า
  useEffect(() => {
    const fetchCustomerData = async () => {
      if (!customerCode || customerCode.toUpperCase() === "N/A") {
        setCustomerData(null);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const res = await api.get(`/api/customer/search`, {
          params: { code: customerCode }
        });
        setCustomerData(res.data);
      } catch (err) {
        console.error("Error loading customer data:", err);
        setError("ไม่สามารถโหลดข้อมูลลูกค้าได้");
      } finally {
        setLoading(false);
      }
    };

    fetchCustomerData();
  }, [customerCode]);

  // โหลดข้อมูลเครดิต
  useEffect(() => {
    // ⭐ Clear credit data ทันทีเมื่อ customerCode เปลี่ยน
    setCreditData(null);
    setRemainingCreditData(null);
    
    const loadCreditData = async () => {
      if (!customerCode || customerCode.toUpperCase() === "N/A") {
        console.log("⏭️ [CREDIT] Skipping: no customerCode or N/A");
        return;
      }

      console.log("🔄 [CREDIT] Loading credit data for:", customerCode);
      setCreditLoading(true);
      try {
        // เพิ่ม timestamp เพื่อป้องกัน cache
        const timestamp = new Date().getTime();
        const res = await api.get(`/api/credit-status/${customerCode}?_t=${timestamp}`);
        console.log("✅ [CREDIT] API response:", res.data);
        console.log("✅ [CREDIT] Status:", res.data?.status);
        console.log("✅ [CREDIT] Credit terms:", res.data?.credit_terms);
        
        // ⭐ Set credit data
        setCreditData(res.data);
        console.log("✅ [CREDIT] creditData updated to:", res.data);
        
        // ⭐ โหลด Remaining Credit
        try {
          const remainingRes = await api.get(`/api/remaining-credit/${customerCode}?_t=${timestamp}`);
          console.log("✅ [REMAINING CREDIT] API response:", remainingRes.data);
          setRemainingCreditData(remainingRes.data);
        } catch (remainingErr) {
          console.error("❌ [REMAINING CREDIT] Error:", remainingErr);
          // ไม่ต้อง set null เพราะจะใช้ข้อมูลจาก credit API แทน
        }
        
        // ⭐ Force re-render check
        setTimeout(() => {
          console.log("✅ [CREDIT] creditData after setState:", creditData);
        }, 100);
      } catch (err) {
        console.error("❌ [CREDIT] Load credit data error:", err);
        console.error("❌ [CREDIT] Error details:", err.response?.data || err.message);
        setCreditData(null);
      } finally {
        setCreditLoading(false);
      }
    };

    loadCreditData();
  }, [customerCode]);

  // ⭐ โหลดราคาโครงการของลูกค้า
  useEffect(() => {
    const loadProjectPrices = async () => {
      if (!customerCode || customerCode.toUpperCase() === "N/A") {
        setProjectPrices([]);
        return;
      }

      try {
        setProjectLoading(true);
        const res = await api.get('/api/project-prices/by-customer', {
          params: { customerCode }
        });
        
        // กรองเฉพาะโครงการที่ active และมีสินค้า
        const activeProjects = (res.data || []).filter(
          p => p.status === 'active' && p.items && p.items.length > 0
        );
        
        setProjectPrices(activeProjects);
        console.log('📦 [PROJECT PRICES] Loaded:', activeProjects);
      } catch (err) {
        console.error('❌ [PROJECT PRICES] Error loading:', err);
        setProjectPrices([]);
      } finally {
        setProjectLoading(false);
      }
    };

    loadProjectPrices();
  }, [customerCode]);

  if (loading || creditLoading) {
    return (
      <div className="flex items-center justify-center h-64 border-t-4 border-gray-200">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-gray-500">กำลังโหลดข้อมูลลูกค้า...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 border-t-4 border-gray-200">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  if (!customerData) {
    return (
      <div className="flex items-center justify-center h-64 border-t-4 border-gray-200">
        <p className="text-gray-500">กรุณาเลือกลูกค้าก่อน</p>
      </div>
    );
  }


  const formatCurrency = (amount) => {
    return Number(amount || 0).toLocaleString("th-TH", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    });
  };

  // ⭐ Helper functions สำหรับ status styling
  const getStatusStyle = (status) => {
    const statusMap = {
      'N': { 
        bgColor: 'bg-green-100 border-green-300', 
        textColor: 'text-green-800',
        iconColor: 'text-green-600'
      },
      'P': { 
        bgColor: 'bg-yellow-100 border-yellow-300', 
        textColor: 'text-yellow-800',
        iconColor: 'text-yellow-600'
      },
      'NPL': { 
        bgColor: 'bg-red-100 border-red-300', 
        textColor: 'text-red-800',
        iconColor: 'text-red-600'
      },
      'L': { 
        bgColor: 'bg-red-200 border-red-400', 
        textColor: 'text-red-900',
        iconColor: 'text-red-700'
      },
    };
    
    return statusMap[status] || { 
      bgColor: 'bg-gray-100 border-gray-300', 
      textColor: 'text-gray-800',
      iconColor: 'text-gray-600'
    };
  };

  const getStatusLabel = (status) => {
    const labelMap = {
      'N': '✓ หนี้ปกติ (ชำระตรงเวลา)',
      'P': '⚠️ จับตามองพิเศษ (ผิดนัดเริ่มต้น)',
      'NPL': '🔴 หนี้เสีย (ค้างเกิน 90 วัน)',
      'L': '❌ หนี้สูญ (ไม่สามารถเรียกคืน)',
    };
    
    return labelMap[status] || status;
  };

  const getStatusIcon = (status) => {
    if (status === 'N') {
      // Check icon for good status
      return <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />;
    } else if (status === 'P') {
      // Exclamation icon for warning
      return <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />;
    } else if (status === 'NPL' || status === 'L') {
      // X icon for error/critical
      return <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />;
    }
    return <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />;
  };

  // ใช้ข้อมูลจาก API ถ้ามี ไม่งั้นใส่ 0 (สำหรับลูกค้าเงินสด)
  const displayCredit = creditData ? {
    creditLimit: creditData.credit_limit || 0,
    creditUsed: remainingCreditData?.data?.[0]?.["Remaining Credit"] 
      ? (creditData.credit_limit || 0) - parseFloat(remainingCreditData.data[0]["Remaining Credit"])
      : (creditData.credit_limit || 0) - (creditData.credit_available || 0),
    creditAvailable: remainingCreditData?.data?.[0]?.["Remaining Credit"]
      ? parseFloat(remainingCreditData.data[0]["Remaining Credit"])
      : (creditData.credit_available || 0),
    paymentTerm: creditData.status || "-",
    creditDaysGA: creditData.credit_terms?.gs || 0,
    creditDaysYC: creditData.credit_terms?.yc || 0,
    creditDaysAL: creditData.credit_terms?.ae || 0,
    lastUpdate: creditData.updated_at || null,
  } : {
    creditLimit: 0,
    creditUsed: 0,
    creditAvailable: 0,
    paymentTerm: "เงินสด",
    creditDaysGA: 0,
    creditDaysYC: 0,
    creditDaysAL: 0,
    lastUpdate: null,
  };

  // ⭐ คำนวณเปอร์เซ็นต์การใช้วงเงิน (ต้องอยู่หลัง displayCredit)
  const creditPercentage = creditData 
    ? ((displayCredit.creditUsed) / displayCredit.creditLimit) * 100
    : 0;

  return (
    <div className="border-t-4 border-gray-200 pt-6">
      <div className="grid grid-cols-3 gap-6">
        {/* คอลัมน์ซ้าย: ข้อมูลลูกค้า */}
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-base font-bold text-gray-700 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
            </svg>
            ข้อมูลลูกค้า
          </h3>
          <div className="space-y-3">
            <InfoField 
              label="รหัสลูกค้า" 
              value={customerData?.id || customerData?.code || customerCode} 
              bold 
            />
            <InfoField 
              label="ประเภทลูกค้า" 
              value={customerData?.gen_bus || customerData?.GenBus || "-"} 
            />
            <InfoField 
              label="วันที่เริ่มเป็นลูกค้า" 
              value={customerData?.customer_date ? formatDateThai(customerData.customer_date) : "-"} 
            />
            <InfoField 
              label="ชื่อบริษัท/ร้านค้า/ลูกค้า" 
              value={customerData?.name || "-"} 
            />
            <InfoField 
              label="เลขที่ผู้เสียภาษี" 
              value={customerData?.tax_no || customerData?.tax_number || "-"} 
            />
            <InfoField 
              label="ผู้ติดต่อ" 
              value={customerData?.contact_person || customerData?.name || "-"} 
            />
            <InfoField 
              label="เบอร์โทรศัพท์" 
              value={customerData?.phone || "-"} 
            />
          </div>
        </div>

        {/* คอลัมน์กลาง: ประวัติการซื้อ */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-base font-bold text-gray-700 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
              <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
            </svg>
            ประวัติการซื้อ 
          </h3>
          
          <div className="text-center">
            <p className="text-xs text-gray-500 mb-1">ยอดซื้อเฉลี่ย 6 เดือน</p>
            <p className="text-3xl font-bold text-gray-800">
              {formatCurrency(customerData?.accum_6m/6 || 0)} บาท
            </p>
          </div>
        </div>

        {/* คอลัมน์ขวา: ข้อมูลเครดิต */}
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-base font-bold text-gray-700 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z" />
              <path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clipRule="evenodd" />
            </svg>
            ข้อมูลเครดิตและวงเงิน
            {creditLoading && (
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            )}
          </h3>

          <div className={`grid ${displayCredit.creditLimit > 0 ? 'grid-cols-2' : 'grid-cols-1'} gap-3 mb-4`}>
            {/* Credit Limit */}
            <div className="bg-blue-50 rounded-lg p-3">
              <p className="text-xs text-gray-600 mb-1">วงเงินเครดิตทั้งหมด</p>
              <p className="text-xl font-bold text-blue-600">
                ฿ {formatCurrency(displayCredit.creditLimit)}
              </p>
              {displayCredit.creditLimit > 0 && (
                <p className="text-xs text-gray-500 mt-1">
                  เหลือวงเงิน: ฿ {formatCurrency(displayCredit.creditAvailable)}
                </p>
              )}
            </div>

            {/* Credit Used - แสดงเฉพาะลูกค้าที่มี credit_limit > 0 */}
            {displayCredit.creditLimit > 0 && (
              <div className="bg-red-50 rounded-lg p-3">
                <p className="text-xs text-gray-600 mb-1">ยอดที่ใช้ไป:</p>
                <p className="text-xl font-bold text-red-600">
                  ฿ {formatCurrency(displayCredit.creditUsed)}
                </p>
                {displayCredit.lastUpdate && (
                  <p className="text-xs text-gray-500 mt-1">
                    อัปเดต: {formatDateThai(displayCredit.lastUpdate)}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Credit Progress Bar - แสดงเฉพาะลูกค้าที่มี credit_limit > 0 */}
          {displayCredit.creditLimit > 0 && (
            <div className="mb-4">
              <div className="flex justify-between text-xs mb-2">
                <span className="text-gray-600">การใช้วงเงิน</span>
                <span className="font-semibold">{creditPercentage.toFixed(0)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    creditPercentage > 80 ? "bg-red-500" : "bg-blue-500"
                  }`}
                  style={{ width: `${Math.min(creditPercentage, 100)}%` }}
                ></div>
              </div>
            </div>
          )}

          <div className="border-t pt-3 space-y-2 mb-3">
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-600">สถานะเครดิต:</span>
              <span className={`font-semibold px-2 py-1 rounded-full text-xs ${getStatusStyle(creditData?.status).bgColor}`}>
                {getStatusLabel(creditData?.status)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-xs text-gray-600">ระยะเวลาเครดิต กระจก/กาว:</span>
              <span className="text-sm font-semibold">{displayCredit.creditDaysGA || 0} วัน</span>
            </div>
            <div className="flex justify-between">
              <span className="text-xs text-gray-600">ระยะเวลาเครดิต อลูมิเนียม/อุปกรณ์:</span>
              <span className="text-sm font-semibold">{displayCredit.creditDaysAL || 0} วัน</span>
            </div>
            <div className="flex justify-between">
              <span className="text-xs text-gray-600">ระยะเวลาเครดิต ยิปซัม/โครงคร่าว:</span>
              <span className="text-sm font-semibold">{displayCredit.creditDaysYC || 0} วัน</span>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Purchase History Section (Requirements 1.1-1.4, 2.1-2.4) */}
      <div className="mt-6">
        <PurchaseHistory customerCode={customerCode} />
      </div>

      {/* ⭐ Project Price Section */}
      {projectLoading ? (
        <div className="mt-6 bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-center">
            <div className="w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mr-2"></div>
            <p className="text-gray-500">กำลังโหลดข้อมูลราคาโครงการ...</p>
          </div>
        </div>
      ) : projectPrices.length > 0 ? (
        <div className="mt-6 bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-base font-bold text-gray-700 mb-4 flex items-center gap-2">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
              <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm9.707 5.707a1 1 0 00-1.414-1.414L9 12.586l-1.293-1.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            ราคาโครงการของลูกค้า
          </h3>
          
          <div className="space-y-4">
            {projectPrices.map((project) => (
              <div key={project.project_id} className="border border-blue-200 rounded-lg p-4 bg-blue-50">
                {/* Project Header */}
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h4 className="font-bold text-blue-900 text-lg">{project.project_code}</h4>
                    {project.project_name && (
                      <p className="text-sm text-blue-700">{project.project_name}</p>
                    )}
                  </div>
                  <div className="text-right text-xs text-blue-600">
                    <p>ใช้ได้ถึง: {formatDateThai(project.price_end_date)}</p>
                  </div>
                </div>

                {/* Project Items */}
                <div className="bg-white rounded-lg p-3 border border-blue-100">
                  <p className="text-xs font-semibold text-gray-700 mb-2">
                    📦 รายการสินค้าในโครงการ:
                  </p>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {(() => {
                      // ฟังก์ชันตัดขนาดและสีออกจากชื่อสินค้า
                      const cleanProductName = (name) => {
                        if (!name) return name;
                        
                        let cleaned = name;
                        
                        // ตัดส่วนที่เป็นตัวเลข x ตัวเลข (เช่น 120x168, 60x60)
                        cleaned = cleaned.replace(/\s*\d+x\d+\s*/g, ' ');
                        
                        // ตัดสีออก (คำที่ขึ้นต้นด้วย "สี" เช่น สีแดง, สีเขียว, สีน้ำเงิน)
                        cleaned = cleaned.replace(/\s*สี[ก-๙]+\s*/g, ' ');
                        
                        // ตัดชื่อสีภาษาอังกฤษที่อยู่ท้ายชื่อ (เช่น Red, Green, Blue, White, Black, Clear)
                        cleaned = cleaned.replace(/\s+(Red|Green|Blue|White|Black|Clear|Yellow|Orange|Purple|Pink|Brown|Grey|Gray)\s*$/gi, ' ');
                        
                        // ลบช่องว่างซ้ำซ้อน
                        cleaned = cleaned.replace(/\s+/g, ' ').trim();
                        
                        return cleaned;
                      };
                      
                      // จัดกลุ่มสินค้าที่มีราคา หน่วย และจำนวนเหมือนกัน (ไม่สนใจขนาดและสี)
                      const groupedItems = {};
                      
                      project.items.forEach(item => {
                        const cleanName = cleanProductName(item.product_name);
                        const groupKey = `${cleanName}_${item.price}_${item.unit}_${item.quantity || ''}`;
                        
                        if (!groupedItems[groupKey]) {
                          groupedItems[groupKey] = {
                            product_name: cleanName,
                            unit: item.unit,
                            price: item.price,
                            quantity: item.quantity,
                            skus: []
                          };
                        }
                        
                        groupedItems[groupKey].skus.push(item.sku);
                      });
                      
                      return Object.values(groupedItems).map((group, idx) => (
                        <div key={idx} className="flex justify-between items-start text-xs bg-gray-50 p-2 rounded border border-gray-100">
                          <div className="flex-1">
                            <p className="font-medium text-gray-800">
                              {group.product_name || '-'}
                              {group.skus.length > 1 && (
                                <span className="ml-2 text-blue-600 font-semibold">
                                  ({group.skus.length} SKUs)
                                </span>
                              )}
                            </p>
                          </div>
                          <div className="text-right ml-3">
                            {group.quantity && (
                              <p className="font-semibold text-blue-600">
                                จำนวน: {parseFloat(group.quantity).toLocaleString()} {group.unit || ''}
                              </p>
                            )}
                          </div>
                        </div>
                      ));
                    })()}
                  </div>
                  <p className="text-xs text-gray-500 mt-2 text-right">
                    รวม {project.items.length} SKU
                  </p>
                </div>

                {/* Project Remark */}
                {project.remark && (
                  <div className="mt-2 bg-yellow-50 border-l-4 border-yellow-400 p-2 rounded">
                    <p className="text-xs font-semibold text-yellow-800">หมายเหตุ:</p>
                    <p className="text-xs text-yellow-700">{project.remark}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
};

const InfoField = ({ label, value, bold = false }) => (
  <div className="space-y-1">
    <p className="text-xs text-gray-500">{label}</p>
    <p className={`text-sm ${bold ? "font-bold" : "font-semibold"} text-gray-800`}>
      {value || "-"}
    </p>
  </div>
);

const CreditRow = ({ label, value, color = "text-gray-800", percentage }) => (
  <div>
    <div className="flex justify-between items-center mb-1">
      <span className="text-xs text-gray-600">{label}</span>
      <span className={`text-sm font-bold ${color}`}>{value}</span>
    </div>
    {percentage !== undefined && (
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${
            percentage > 80 ? "bg-red-500" : "bg-blue-500"
          }`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        ></div>
      </div>
    )}
  </div>
);

const InfoRow = ({ label, value, highlight = false, valueClass = "" }) => (
  <div className="flex justify-between items-center">
    <span className="text-sm text-gray-600">{label}:</span>
    <span className={`text-sm font-semibold ${
      highlight 
        ? "text-blue-600 bg-blue-50 px-3 py-1 rounded-md" 
        : valueClass || "text-gray-800"
    }`}>
      {value || "-"}
    </span>
  </div>
);

export default CustomerInfoTab;
