import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";
import { useQuote } from "../hooks/useQuote";

export default function OrderDetailPage() {
  const { id } = useParams();
  const { dispatch } = useQuote();
  const navigate = useNavigate();

  const [order, setOrder] = useState(null);
  const [printing, setPrinting] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.get(`/api/quotation/${id}`);
        const h = res.data.header || {};
        const lines = res.data.lines || [];

        const formatted = {
          quoteNo: h.QuoteNo,
          createdAt: h.CreateDate,
          sales: h.SalesName || "",
          customer: {
            id: h.CustomerCode,
            name: h.CustomerName,
            phone: h.Tel,
          },

          needTaxInvoice: h.NeedsTax === "Y",
          billTaxName: h.BillTaxName || "",
          deliveryType: h.ShippingMethod || "PICKUP",
          note: h.Remark || "",

          totals: {
            exVat: h.SubtotalAmount,
            vat: h.SubtotalAmount ? h.TotalAmount - h.SubtotalAmount : 0,
            grandTotal: h.TotalAmount,
            shippingRaw: h.ShippingCost || 0,
            shippingCustomerPay: h.ShippingCustomerPay || 0,
          },

          cart: lines.map((ln) => ({
            sku: ln.ItemCode,
            name: ln.ItemName,
            qty: ln.Quantity,
            price: ln.UnitPrice,
            lineTotal: ln.TotalPrice,
            category: ln.Category,
            unit: ln.Unit || "-",
            sqft_sheet: ln.Sqft_Sheet ?? ln.sqft ?? ln.GlassSqft ?? 0,
            product_weight: ln.ProductWeight ?? 0,
            variantCode: ln.VariantCode ?? "",
          })),
        };

        setOrder(formatted);
      } catch (err) {
        console.error("Error loading order:", err);
      }
    };

    load();
  }, [id]);

  if (!order) return <div className="p-6">กำลังโหลด...</div>;

  const fmt = (n) => Number(n || 0).toLocaleString("th-TH");

  // =========================
  // PRINT (เหมือน Step6)
  // =========================
  const handlePrint = async () => {
    if (printing) return;
    try {
      setPrinting(true);

      const payload = {
        quoteNo: order.quoteNo || "",
        date: new Date(order.createdAt).toLocaleDateString("th-TH"),
        sales: order.sales || "",
        salesId: order.employee?.id || "",  // ⭐ เพิ่ม salesId เพื่อให้ backend ดึงชื่อพนักงานได้
        projectCode: order.projectCode || null,  // ⭐ เพิ่ม projectCode
        customer: {
          code: order.customer?.id || "",
          name: order.customer?.name || "ผู้ไม่ประสงค์ออกนาม",
          phone: order.customer?.phone || "",
        },
        items: order.cart.map((it) => {
          const isGlass = it.category === "G" || Number(it.sqft_sheet || 0) > 0;

          const pricePerSheet =
            isGlass && it.qty > 0
              ? Number(it.lineTotal || 0) / Number(it.qty || 1)
              : Number(it.price || 0);

          return {
            code: it.sku,
            name: it.name,
            qty: it.qty,
            unit: it.unit && it.unit.trim() !== "" ? it.unit : "-",

            // ✅ ถ้าเป็นกระจก → แสดงราคาต่อแผ่น
            price: Math.round(pricePerSheet * 100) / 100,

            // ✅ ยอดรวมยังใช้ของจริงจาก DB
            amount: Number(it.lineTotal || 0),
          };
        }),

        comment: order.note || "",
        shipping: Number(order.totals.shippingCustomerPay || 0),
        amountText: "", // backend เติม
        total: order.totals.grandTotal,
        discount: 0,
        afterDiscount: order.totals.grandTotal,
        exVat: order.totals.exVat,
        vat: order.totals.vat,
        netTotal: order.totals.grandTotal,
      };

      // Use relative path for print endpoint to work in both Docker (Nginx proxy) and Native (Backend serve)
      // Use api.post for consistent base URL handling, OR ensure path includes /api
      // Here we keep fetch but update path to /api/print/quotation
      const res = await fetch("/api/print/quotation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url);
    } catch (err) {
      console.error("Print error:", err);
      alert("ไม่สามารถพิมพ์ใบเสนอราคาได้");
    } finally {
      setPrinting(false);
    }
  };

  return (
    <div className="p-6">
      <button
        onClick={() => navigate(-1)}
        className="mb-4 px-4 py-2 rounded-lg bg-gray-200 hover:bg-gray-300"
      >
        ย้อนกลับ
      </button>

      {/* รายการสินค้า */}
      <div className="bg-white rounded-xl p-6 shadow mb-6">
        <h2 className="text-xl font-bold mb-4">รายละเอียดรายการสินค้า</h2>

        <div className="grid grid-cols-4 gap-4 mb-4">
          <div>
            <p className="text-gray-600">เลขที่ใบเสนอราคา</p>
            <p className="font-semibold">{order.quoteNo}</p>
          </div>
          <div>
            <p className="text-gray-600">วันที่</p>
            <p className="font-semibold">{new Date(order.createdAt).toLocaleDateString("th-TH")}</p>
          </div>
          <div>
            <p className="text-gray-600">รหัสลูกค้า</p>
            <p className="font-semibold">{order.customer?.id}</p>
          </div>
          <div>
            <p className="text-gray-600">ชื่อลูกค้า</p>
            <p className="font-semibold">{order.customer?.name}</p>
          </div>
        </div>

        <table className="min-w-full mt-4">
          <thead>
            <tr className="border-b bg-gray-100">
              <th className="p-3 text-left">#</th>
              <th className="p-3 text-left">สินค้า</th>
              <th className="p-3 text-center">จำนวน</th>
              <th className="p-3 text-right">ราคา/หน่วย</th>
              <th className="p-3 text-right">ยอดรวม</th>
            </tr>
          </thead>
          <tbody>
            {order.cart.map((item, idx) => (
              <tr key={idx} className="border-b">
                <td className="p-3">{idx + 1}</td>
                <td className="p-3">
                  {item.name}
                  <br />
                  <span className="text-gray-500 text-sm">{item.sku}</span>
                </td>
                <td className="p-3 text-center">{item.qty}</td>
                <td className="p-3 text-right">
                  {(() => {
                    const isGlass =
                      (item.category || String(item.sku || "").slice(0, 1)).toUpperCase() === "G";

                    // ✅ ถ้าเป็นกระจก → แสดงราคาต่อแผ่น (lineTotal / qty)
                    // ✅ ถ้าไม่ใช่กระจก → แสดงราคาต่อหน่วย (price)
                    const displayPrice =
                      isGlass && item.qty > 0
                        ? item.lineTotal / item.qty // ราคาต่อแผ่น
                        : item.price; // ราคาต่อหน่วยปกติ

                    return fmt(displayPrice);
                  })()}
                </td>

                <td className="p-3 text-right">{fmt(item.lineTotal)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* สรุปยอด */}
      <div className="bg-white rounded-xl p-6 shadow">
        <h2 className="text-xl font-bold mb-4">สรุปยอด</h2>

        <div className="flex justify-between">
          <span>ค่าขนส่ง</span>
          <span className="font-semibold">฿{fmt(order.totals.shippingCustomerPay)}</span>
        </div>

        <div className="flex justify-between mt-2">
          <span>ราคารวมก่อน VAT</span>
          <span className="font-semibold">฿{fmt(order.totals.exVat)}</span>
        </div>

        <div className="flex justify-between mt-2">
          <span>ภาษีมูลค่าเพิ่ม (7%)</span>
          <span className="font-semibold">฿{fmt(order.totals.vat)}</span>
        </div>

        <hr className="my-4" />

        <div className="flex justify-between text-xl font-bold text-blue-600">
          <span>ราคารวมสุทธิ</span>
          <span>฿{fmt(order.totals.grandTotal)}</span>
        </div>

        <div className="mt-6 flex gap-4">
          <button
            onClick={handlePrint}
            disabled={printing}
            className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold disabled:opacity-50"
          >
            พิมพ์ใบเสนอราคา
          </button>

          <button
            className="px-6 py-2 rounded-lg bg-blue-600 text-white  shadow hover:bg-blue-700 font-semibold"
            onClick={async () => {
              try {
                // ⭐ เรียก API เพื่อตรวจสอบวันหมดอายุ
                const response = await api.post(`/api/quotation/${order.quoteNo}/reorder`);
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
                      _needsHydrate: true,
                    },
                    deliveryType: quote.deliveryType ?? "PICKUP",
                    billTaxName: quote.billTaxName ?? "",
                    note: quote.note ?? "",
                    expireDate: quote.expireDate || null,
                    project_code: quote.project_code || null,  // ⭐ เพิ่ม project_code
                    cart: (quote.cart || []).map((it) => ({
                      sku: it.sku,
                      name: it.name,
                      qty: Number(it.qty ?? 0),
                      price: Number(it.price ?? 0),
                      lineTotal: Number(it.lineTotal ?? 0),
                      Price_System: Number(it.Price_System ?? 0),
                      category: it.category,
                      unit: it.unit || "-",

                      // ⭐ normalize key fields
                      variantCode: String(it.variantCode ?? ""),
                      sqft_sheet: Number(it.sqft_sheet ?? 0),

                      product_weight: Number(it.product_weight ?? 0),

                      // ⭐ flags - ใช้ราคาที่ Backend คำนวณมาแล้ว
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

                navigate("/create?step=6");
              } catch (error) {
                console.error("Error checking quote expiration:", error);
                
                // ถ้า API ล้มเหลว ให้ใช้วิธีเดิม
                dispatch({
                  type: "LOAD_DRAFT",
                  payload: {
                    id: null,
                    quoteNo: null,
                    customer: {
                      id: order.customer?.id || "",
                      code: order.customer?.id || "",
                      name: order.customer?.name || "",
                      phone: order.customer?.phone || "",
                      _needsHydrate: true,
                    },
                    deliveryType: order.deliveryType ?? "PICKUP",
                    project_code: order.project_code || order.ProjectCode || null,  // ⭐ เพิ่ม project_code
                    billTaxName: order.billTaxName ?? "",
                    note: order.note ?? "",
                    expireDate: order.expireDate || null,
                    cart: (order.cart || []).map((it) => ({
                      sku: it.sku,
                      name: it.name,
                      qty: Number(it.qty ?? 0),
                      price: Number(it.price ?? 0),
                      lineTotal: Number(it.lineTotal ?? it.price * it.qty ?? 0),
                      category: it.category,
                      unit: it.unit || "-",

                      // ⭐ normalize key fields
                      variantCode: String(it.variantCode ?? ""),
                      sqft_sheet: Number(it.sqft_sheet ?? 0),

                      product_weight: Number(it.product_weight ?? 0),

                      // ⭐ flags เหมือน draft
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
                navigate("/create?step=6");
              }
            }}
          >
            สั่งซื้อซ้ำ
          </button>
        </div>
      </div>
    </div>
  );
}
