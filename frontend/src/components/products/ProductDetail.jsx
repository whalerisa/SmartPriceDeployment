// components/products/ProductDetail.jsx
import { useEffect, useState } from "react";
import api, { getItemStock } from "../../services/api";

export default function ProductDetail({ item }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stock, setStock] = useState(null);
  const [loadingStock, setLoadingStock] = useState(false);

  useEffect(() => {
    if (!item) {
      setDetail(null);
      setStock(null);
      return;
    }

    const loadDetail = async () => {
      try {
        setLoading(true);
        const sku = item.sku || item.SKU;
        
        // ตรวจสอบว่าเป็นกระจกหรือไม่
        const isGlass = sku && sku[0] === 'G';
        
        // ใช้ endpoint ที่เหมาะสม
        const endpoint = isGlass ? `/api/items/glass/${sku}` : `/api/items/${sku}`;
        const res = await api.get(endpoint);
        setDetail(res.data);
      } catch (err) {
        console.error("Load product detail error:", err);
        setDetail(null);
      } finally {
        setLoading(false);
      }
    };

    const loadStock = async () => {
      try {
        setLoadingStock(true);
        const sku = item.sku || item.SKU;
        const stockData = await getItemStock(sku);
        setStock(stockData);
      } catch (err) {
        console.error("Load stock error:", err);
        setStock(null);
      } finally {
        setLoadingStock(false);
      }
    };

    loadDetail();
    loadStock();
  }, [item]);

  if (!item) {
    return (
      <div className="text-gray-500 p-4 bg-white rounded shadow h-[600px] flex items-center justify-center">
        เลือกรายการสินค้าเพื่อดูรายละเอียด
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-white p-6 rounded shadow h-[600px] flex items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <div className="text-sm text-gray-500">กำลังโหลดรายละเอียด...</div>
        </div>
      </div>
    );
  }

  const displayItem = detail || item;

  return (
    <div className="space-y-4 bg-white p-6 rounded shadow h-[600px] overflow-y-auto">
      {/* ข้อมูลสินค้า */}
      <div>
        <h2 className="text-2xl font-bold">{displayItem.name || displayItem.description}</h2>
        {displayItem.alternate_names && (
          <div className="text-sm font-semibold text-gray-500 mt-1">
            ชื่ออื่น: {displayItem.alternate_names}
          </div>
        )}

        <div className="mt-4 space-y-2 text-sm">
          <p className="text-gray-600">
            <span className="font-semibold">SKU:</span> {displayItem.sku}
          </p>
          {displayItem.sku2 && (
            <p className="text-gray-600">
              <span className="font-semibold">SKU 2:</span> {displayItem.sku2}
            </p>
          )}
          {displayItem.brandName && (
            <p>
              <span className="font-semibold">Brand:</span> {displayItem.brandName}
            </p>
          )}
          {displayItem.groupName && (
            <p>
              <span className="font-semibold">Group:</span> {displayItem.groupName}
            </p>
          )}
          {displayItem.subGroupName && (
            <p>
              <span className="font-semibold">SubGroup:</span> {displayItem.subGroupName}
            </p>
          )}
          {displayItem.colorName && (
            <p>
              <span className="font-semibold">Color:</span> {displayItem.colorName}
            </p>
          )}
          {displayItem.thickness && (
            <p>
              <span className="font-semibold">Thickness:</span> {displayItem.thickness}
            </p>
          )}
          {displayItem.unit && (
            <p>
              <span className="font-semibold">Unit:</span> {displayItem.unit}
            </p>
          )}
          
          {/* แสดง Stock */}
          {loadingStock ? (
            <p className="text-gray-500">
              <span className="font-semibold">Stock:</span> กำลังโหลด...
            </p>
          ) : stock && stock.quantity !== undefined ? (
            <div className="p-3 bg-green-50 rounded-lg border border-green-200">
              <p className="text-green-700 font-semibold">
                คงเหลือในสต๊อก (สาขา {stock['Location_Code']}): {stock.quantity.toLocaleString()} {displayItem.unit || 'หน่วย'}
              </p>
            </div>
          ) : (
            <p className="text-gray-500">
              <span className="font-semibold">Stock:</span> ไม่มีข้อมูล
            </p>
          )}
        </div>

        {/* ข้อมูลเพิ่มเติมสำหรับกระจก */}
        {displayItem.width && displayItem.height && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <h3 className="font-semibold mb-2">ขนาด</h3>
            <p className="text-sm">
              {displayItem.width} × {displayItem.height} นิ้ว
            </p>
            <p className="text-sm font-semibold text-blue-700 mt-1">
              พื้นที่: {((displayItem.width * displayItem.height) / 144).toFixed(2)} ตารางฟุต
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
