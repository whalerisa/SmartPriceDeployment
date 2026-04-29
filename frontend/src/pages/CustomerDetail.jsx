import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";
import { useQuote } from "../hooks/useQuote";
import { formatDateThai, formatDateThaiShort } from "../utils/dateFormatter";

function CustomerDetail() {
  const { customerId } = useParams();
  const navigate = useNavigate();
  const { dispatch } = useQuote();
  
  const [loading, setLoading] = useState(false);
  const [customer, setCustomer] = useState(null);
  const [quotations, setQuotations] = useState([]);
  const [orders, setOrders] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [creditData, setCreditData] = useState(null);
  const [creditLoading, setCreditLoading] = useState(false);
  const [remainingCreditData, setRemainingCreditData] = useState(null);

  useEffect(() => {
    loadCustomerData();
    loadCreditData();
    loadRemainingCredit();
  }, [customerId]);

  const loadRemainingCredit = async () => {
    try {
      // เรียก backend proxy endpoint สำหรับ remaining credit
      const res = await api.get(`/api/remaining-credit/${customerId}`);
      
      console.log("✅ Remaining Credit API response:", res.data);
      setRemainingCreditData(res.data);
    } catch (err) {
      console.error("❌ Load remaining credit error:", err);
      console.error("❌ Error details:", err.response?.data);
      // ⭐ ไม่ต้อง set null เพราะจะใช้ข้อมูลจาก credit API แทน
      // setRemainingCreditData(null);
    }
  };

  const loadCreditData = async () => {
    setCreditLoading(true);
    try {
      // เรียก backend proxy endpoint
      const res = await api.get(`/api/credit-status/${customerId}`);
      
      console.log("✅ Credit API response:", res.data);
      console.log("✅ Credit terms:", res.data?.credit_terms);
      setCreditData(res.data);
    } catch (err) {
      console.error("❌ Load credit data error:", err);
      console.error("❌ Error details:", err.response?.data);
      // ถ้า API ไม่ตอบ ใช้ mock data
      setCreditData(null);
    } finally {
      setCreditLoading(false);
    }
  };

  const loadCustomerData = async () => {
    setLoading(true);
    try {
      // โหลดข้อมูลลูกค้า
      const customerRes = await api.get(`/api/customer/${customerId}`);
      setCustomer(customerRes.data);

      // โหลดใบเสนอราคาทั้งหมด
      const [completeRes, draftRes, pendingRes, openRes] = await Promise.all([
        api.get("/api/quotation", { params: { status: "complete" } }),
        api.get("/api/quotation", { params: { status: "draft" } }),
        api.get("/api/quotation", { params: { status: "pending_approval" } }),
        api.get("/api/quotation", { params: { status: "open" } }),
      ]);

      const allComplete = completeRes.data || [];
      const allDrafts = [
        ...(draftRes.data || []), 
        ...(pendingRes.data || []),
        ...(openRes.data || [])  // ⭐ เพิ่ม open
      ];
      
      // กรองเฉพาะของลูกค้านี้
      const customerComplete = allComplete.filter(
        (q) => q.customer?.id === customerId
      );
      const customerDrafts = allDrafts.filter(
        (q) => q.customer?.id === customerId
      );

      // ประวัติการซื้อ = ใบเสนอราคาที่ complete เท่านั้น
      setOrders(customerComplete);
      
      // ใบเสนอราคาแบบร่าง = draft + pending_approval + open
      setQuotations(customerDrafts);
    } catch (err) {
      console.error("Load customer data error:", err);
    } finally {
      setLoading(false);
    }
  };

  // ฟังก์ชันสำหรับแก้ไขใบเสนอราคา (เหมือน handleEditDraft)
  const handleEditQuote = async (quote) => {
    try {
      // โหลดข้อมูลเต็มจาก API
      const res = await api.get(`/api/quotation/${encodeURIComponent(quote.quoteNo || quote.id)}`);
      const h = res.data.header || {};
      const lines = res.data.lines || [];

      // แปลง lines เป็น cart
      const cart = lines.map((ln) => ({
        sku: ln.ItemCode,
        name: ln.ItemName,
        qty: Number(ln.Quantity ?? 0),
        price: Number(ln.UnitPrice ?? 0),
        lineTotal: Number(ln.TotalPrice ?? ln.UnitPrice * ln.Quantity ?? 0),
        category: ln.Category,
        unit: ln.Unit || "-",
        variantCode: String(ln.VariantCode ?? ""),
        sqft_sheet: Number(ln.Sqft_Sheet ?? 0),
        product_weight: Number(ln.ProductWeight ?? 0),
        source: "db",
        needsPricing: false,
        isDraftItem: true,
      }));

      // โหลดข้อมูลลูกค้า
      dispatch({
        type: "LOAD_DRAFT",
        payload: {
          id: h.QuoteNo,
          quoteNo: h.QuoteNo,
          customer: {
            id: h.CustomerCode || "",
            code: h.CustomerCode || "",
            name: h.CustomerName || "",
            phone: h.Tel || "",
            _needsHydrate: true,
          },
          deliveryType: h.ShippingMethod,
          billTaxName: h.BillTaxName,
          note: h.Remark,
          needTaxInvoice: h.NeedsTax === "Y",
          expireDate: h.ExpireDate || null,
          project_code: h.project_code || h.ProjectCode || null,  // ⭐ เพิ่ม project_code
          cart,
          shippingCost: h.ShippingCost ?? 0,
          shippingCustomerPay: h.ShippingCustomerPay ?? 0,
          shippingCompanyPay: h.ShippingCompanyPay ?? 0,
          totals: {
            exVat: h.SubtotalAmount,
            vat: h.SubtotalAmount * 0.07,
            grandTotal: h.TotalAmount,
            shippingRaw: h.ShippingCost ?? 0,
            shippingCustomerPay: h.ShippingCustomerPay ?? 0,
            shippingCompanyPay: h.ShippingCompanyPay ?? 0,
          },
        },
      });

      navigate("/create?step=6");
    } catch (err) {
      console.error("Edit quote error:", err);
      alert("ไม่สามารถโหลดข้อมูลใบเสนอราคาได้");
    }
  };

  // ฟังก์ชันสำหรับพิมพ์ใบเสนอราคา
  const handlePrintQuote = async (quote) => {
    try {
      // โหลดข้อมูลเต็มจาก API
      const res = await api.get(`/api/quotation/${encodeURIComponent(quote.quoteNo || quote.id)}`);
      const h = res.data.header || {};
      const lines = res.data.lines || [];

      const payload = {
        quoteNo: h.QuoteNo || "",
        date: new Date(h.CreateDate).toLocaleDateString("th-TH"),
        sales: h.SalesName || "",
        salesId: h.SalesID || "",  // ⭐ เพิ่ม salesId เพื่อให้ backend ดึงชื่อพนักงานได้
        projectCode: h.ProjectCode || null,  // ⭐ เพิ่ม projectCode
        customer: {
          code: h.CustomerCode || "",
          name: h.CustomerName || "ผู้ไม่ประสงค์ออกนาม",
          phone: h.Tel || "",
        },
        items: lines.map((ln) => {
          const isGlass = ln.Category === "G" || Number(ln.Sqft_Sheet || 0) > 0;
          const pricePerSheet =
            isGlass && ln.Quantity > 0
              ? Number(ln.TotalPrice || 0) / Number(ln.Quantity || 1)
              : Number(ln.UnitPrice || 0);

          return {
            code: ln.ItemCode,
            name: ln.ItemName,
            qty: ln.Quantity,
            unit: ln.Unit && ln.Unit.trim() !== "" ? ln.Unit : "-",
            price: Math.round(pricePerSheet * 100) / 100,
            amount: Number(ln.TotalPrice || 0),
          };
        }),
        comment: h.Remark || "",
        shipping: Number(h.ShippingCustomerPay || 0),
        amountText: "",
        total: h.TotalAmount,
        discount: 0,
        afterDiscount: h.TotalAmount,
        exVat: h.SubtotalAmount,
        vat: h.SubtotalAmount ? h.TotalAmount - h.SubtotalAmount : 0,
        netTotal: h.TotalAmount,
      };

      const printRes = await fetch("/api/print/quotation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const blob = await printRes.blob();
      const url = URL.createObjectURL(blob);
      window.open(url);
    } catch (err) {
      console.error("Print error:", err);
      alert("ไม่สามารถพิมพ์ใบเสนอราคาได้");
    }
  };

  // ฟังก์ชันสำหรับลบใบเสนอราคา
  const handleDeleteQuote = async (quote) => {
    const ok = window.confirm(`ต้องการลบใบเสนอราคาเลขที่ ${quote.quoteNo || quote.id}?`);
    if (!ok) return;

    try {
      await api.delete(`/api/quotation/${encodeURIComponent(quote.quoteNo || quote.id)}`);
      
      // อัปเดต state โดยลบรายการที่ถูกลบออก
      setQuotations((prev) => prev.filter((q) => q.quoteNo !== quote.quoteNo && q.id !== quote.id));
      
      alert("ลบใบเสนอราคาสำเร็จ");
    } catch (err) {
      console.error("Delete quote error:", err);
      alert("ไม่สามารถลบใบเสนอราคาได้");
    }
  };

  // ฟังก์ชันสำหรับค้นหาลูกค้าแบบ autocomplete
  const handleSearchInput = async (value) => {
    setSearchQuery(value);
    
    if (!value || value.trim().length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    try {
      const res = await api.get("/api/customer/list", {
        params: { q: value.trim() },
      });
      
      const results = res.data || [];
      setSearchResults(results);
      setShowDropdown(results.length > 0);
    } catch (err) {
      console.error("Search error:", err);
      setSearchResults([]);
      setShowDropdown(false);
    }
  };

  // เลือกลูกค้าจาก dropdown
  const handleSelectCustomer = (customerId) => {
    setShowDropdown(false);
    setSearchQuery("");
    setSearchResults([]);
    navigate(`/customer/${customerId}`);
  };

  const formatDate = (dateStr) => {
    return formatDateThai(dateStr);
  };

  const formatCurrency = (amount) => {
    return Number(amount || 0).toLocaleString("th-TH", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      draft: { label: "แบบร่าง", color: "bg-yellow-100 text-yellow-800" },
      open: { label: "เปิด", color: "bg-blue-100 text-blue-800" },
      pending_approval: { label: "รออนุมัติ", color: "bg-orange-100 text-orange-800" },
      complete: { label: "สำเร็จ", color: "bg-green-100 text-green-800" },
    };
    const s = statusMap[status] || { label: status, color: "bg-gray-100 text-gray-800" };
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${s.color}`}>
        {s.label}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen w-full bg-[#F5F5F5] flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="min-h-screen w-full bg-[#F5F5F5] p-6">
        <div className="text-center py-20">
          <p className="text-lg text-gray-500">ไม่พบข้อมูลลูกค้า</p>
          <button
            onClick={() => navigate(-1)}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            กลับ
          </button>
        </div>
      </div>
    );
  }

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

  // ใช้ข้อมูลจาก API ถ้ามี ไม่งั้นใส่ 0 (สำหรับลูกค้าเงินสด)
  const displayCredit = creditData ? {
    creditLimit: creditData.credit_limit || 0,
    // ⭐ ยอดที่ใช้ไป = Total utilization จาก API (เอาค่าตรงๆ)
    creditUsed: remainingCreditData?.data?.[0]?.["Total Utilization"]
      ? parseFloat(remainingCreditData.data[0]["Total Utilization"])
      : (creditData.credit_limit || 0) - (creditData.credit_available || 0),
    // ⭐ เหลือวงเงิน = Remaining Credit จาก API (เอาค่าตรงๆ)
    creditAvailable: remainingCreditData?.data?.[0]?.["Remaining Credit"]
      ? parseFloat(remainingCreditData.data[0]["Remaining Credit"])
      : (creditData.credit_available || 0),
    paymentTerm: creditData.status || "-",
    creditDaysGA: creditData.credit_terms?.gs || 0,  // gs = กระจก/กาว
    creditDaysYC: creditData.credit_terms?.yc || 0,  // yc = ยิปซัม/โครงคร่าว
    creditDaysAL: creditData.credit_terms?.ae || 0,  // ae = อลูมิเนียม/อุปกรณ์
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
    <div className="min-h-screen w-full bg-[#F5F5F5] p-6">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <button
          onClick={() => navigate(-1)}
          className="text-blue-600 hover:text-blue-800 mb-4 flex items-center gap-2"
        >
          ← กลับ
        </button>

        {/* Search Bar */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <img src="/assets/magnifier.png" alt="Search" className="w-6 h-6" />
            ค้นหารายละเอียดลูกค้า
          </h2>
          <div className="relative">
            <input
              type="text"
              placeholder="ค้นหาด้วย รหัสลูกค้า, ชื่อ หรือ เบอร์โทร เลขบัตรภาษี....."
              value={searchQuery}
              onChange={(e) => handleSearchInput(e.target.value)}
              onFocus={() => searchResults.length > 0 && setShowDropdown(true)}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
            
            {/* Dropdown */}
            {showDropdown && searchResults.length > 0 && (
              <div className="absolute z-50 w-full mt-2 bg-white border border-gray-300 rounded-xl shadow-lg max-h-80 overflow-y-auto">
                {searchResults.map((result) => (
                  <div
                    key={result.id}
                    onClick={() => handleSelectCustomer(result.id)}
                    className="px-4 py-3 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                  >
                    <div className="font-semibold text-gray-800">{result.name}</div>
                    <div className="text-sm text-gray-600">
                      รหัส: {result.id} {result.phone && `• โทร: ${result.phone}`}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column */}
          <div className="space-y-6">
            {/* Customer Info Card */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white font-bold">
                  <img src="/assets/user.png" alt="Customer" className="w-6 h-6" />
                </div>
                ข้อมูลลูกค้า
              </h3>

              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-blue-500 rounded-full flex items-center justify-center text-white text-2xl font-bold">
                    {customer.name?.substring(0, 1).toUpperCase() || "??"}
                  </div>
                  <div>
                    <h4 className="text-xl font-bold">{customer.name || "-"}</h4>
                    <p className="text-sm text-gray-600">รหัส: {customer.id || customerId}</p>
                    <span className={`inline-block mt-1 px-3 py-1 rounded-full text-xs font-semibold ${
                      customer.payment_terms && 
                      customer.payment_terms !== "0" && 
                      customer.payment_terms.toUpperCase() !== "CASH"
                        ? "bg-green-100 text-green-800" 
                        : "bg-blue-100 text-blue-800"
                    }`}>
                      {customer.payment_terms && 
                       customer.payment_terms !== "0" && 
                       customer.payment_terms.toUpperCase() !== "CASH"
                        ? "ลูกค้าเครดิต" 
                        : "ลูกค้าเงินสด"}
                    </span>
                  </div>
                </div>

                <div className="border-t pt-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600">รหัสลูกค้า:</span>
                    <span className="font-semibold">{customer.id || customerId}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">ชื่อลูกค้า:</span>
                    <span className="font-semibold">{customer.name || "-"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">เบอร์โทรศัพท์:</span>
                    <span className="font-semibold">{customer.phone || "-"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">วันที่เป็นลูกค้า:</span>
                    <span className="font-semibold">{customer.customer_date ? formatDate(customer.customer_date) : "-"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">ประเภทลูกค้า:</span>
                    <span className="font-semibold">{customer.gen_bus || "-"}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Order History */}
            {!(customer?.name || "").trim().startsWith("ขายสด") && (
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                  <img src="/assets/time-svgrepo-com.svg" alt="History" className="w-6 h-6" />
                </div>
                ประวัติการซื้อ
              </h3>

              <div className="space-y-3">
                {orders.length === 0 ? (
                  <p className="text-center text-gray-500 py-4">ไม่มีประวัติการซื้อ</p>
                ) : (
                  orders.slice(0, 3).map((order) => (
                    <div
                      key={order.id}
                      className="border rounded-lg p-4 hover:bg-gray-50"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <p className="text-sm text-gray-500">
                            {formatDate(order.createdAt)}
                          </p>
                          <p className="font-semibold">{order.quoteNumber || `#ORD-${order.id}`}</p>
                        </div>
                        <button 
                          onClick={() => navigate(`/order/${encodeURIComponent(order.quoteNo || order.id)}`)}
                          className="px-4 py-1 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
                        >
                          ดูข้อมูล
                        </button>
                      </div>
                      <p className="text-green-600 font-semibold">
                        ฿ {formatCurrency(order.totals?.grandTotal || 0)}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
            )}
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Credit Info Card */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                  <img src="/assets/creditcard.png" alt="Credit" className="w-6 h-6" />
                </div>
                ข้อมูลเครดิตและวงเงิน
                {creditLoading && (
                  <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin ml-2"></div>
                )}
              </h3>

              <div className={`grid ${displayCredit.creditLimit > 0 ? 'grid-cols-2' : 'grid-cols-1'} gap-4 mb-4`}>
                {/* Credit Limit */}
                <div className="bg-blue-50 rounded-xl p-4">
                  <p className="text-sm text-gray-600 mb-1">วงเงินเครดิตทั้งหมด</p>
                  <p className="text-2xl font-bold text-blue-600">
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
                  <div className="bg-red-50 rounded-xl p-4">
                    <p className="text-sm text-gray-600 mb-1">ยอดที่ใช้ไป:</p>
                    <p className="text-2xl font-bold text-red-600">
                      ฿ {formatCurrency(displayCredit.creditUsed)}
                    </p>
                    {displayCredit.lastUpdate && (
                      <p className="text-xs text-gray-500 mt-1">
                        อัปเดต: {formatDate(displayCredit.lastUpdate)}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Credit Progress Bar - แสดงเฉพาะลูกค้าที่มี credit_limit > 0 */}
              {displayCredit.creditLimit > 0 && (
                <div className="mb-4">
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-600">การใช้วงเงิน</span>
                    <span className="font-semibold">{creditPercentage.toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full ${
                        creditPercentage > 80 ? "bg-red-500" : "bg-blue-500"
                      }`}
                      style={{ width: `${creditPercentage}%` }}
                    ></div>
                  </div>
                </div>
              )}

              <div className="border-t pt-4 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">สถานะเครดิต:</span>
                  <span className={`font-semibold px-3 py-1 rounded-full text-sm ${getStatusStyle(creditData?.status).bgColor}`}>
                    {creditData?.status || "-"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">ระยะเวลาเครดิต กระจก/กาว:</span>
                  <span className="font-semibold">{displayCredit.creditDaysGA || displayCredit.creditDays || 0} วัน</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">ระยะเวลาเครดิต อลูมิเนียม/อุปกรณ์:</span>
                  <span className="font-semibold">{displayCredit.creditDaysAL || displayCredit.creditDays || 0} วัน</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">ระยะเวลาเครดิต ยิปซัม/โครงคร่าว:</span>
                  <span className="font-semibold">{displayCredit.creditDaysYC || displayCredit.creditDays || 0} วัน</span>
                </div>
              </div>
            </div>

            {/* Quotations */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                  <img src="/assets/cart.png" alt="Quote" className="w-6 h-6" />
                </div>
                รอดำเนินการ - ใบเสนอราคาแบบร่าง
              </h3>

              <div className="space-y-4">
                {quotations.length === 0 ? (
                  <p className="text-center text-gray-500 py-4">ไม่มีใบเสนอราคาแบบร่าง</p>
                ) : (
                  quotations.map((quote) => (
                    <div key={quote.id} className="border rounded-xl p-4">
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <p className="font-semibold text-lg">
                            {quote.quoteNumber || `${String(quote.id).padStart(3, "0")}`}
                          </p>
                          <p className="text-sm text-gray-600">
                            {customer.name} รหัสลูกค้า: {customerId}
                          </p>
                        </div>
                        {getStatusBadge(quote.status)}
                      </div>

                      <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
                        <div>
                          <p className="text-gray-600">จำนวนรายการ</p>
                          <p className="font-semibold">{quote.items?.length || 0} รายการ</p>
                        </div>
                        <div>
                          <p className="text-gray-600">มูลค่ารวม</p>
                          <p className="font-semibold text-green-600">
                            ฿ {formatCurrency(quote.totals?.grandTotal || 0)}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-600">แก้ไขล่าสุด</p>
                          <p className="font-semibold">{formatDate(quote.updatedAt || quote.createdAt)}</p>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => handleEditQuote(quote)}
                          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
                        >
                          แก้ไข
                        </button>
                        <button 
                          onClick={() => handlePrintQuote(quote)}
                          className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm font-medium"
                        >
                          พิมพ์ใบเสนอราคา
                        </button>
                        <button 
                          onClick={() => handleDeleteQuote(quote)}
                          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm font-medium"
                        >
                          ลบ
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CustomerDetail;
