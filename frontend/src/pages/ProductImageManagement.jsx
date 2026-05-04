// pages/ProductImageManagement.jsx
import { useState, useEffect } from "react";
import { api } from "../services/api";
import ProductImageUpload from "../components/products/ProductImageUpload";

export default function ProductImageManagement() {
  const [sku, setSku] = useState("");
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  // โหลดรายการรูปภาพ
  useEffect(() => {
    loadImages();
  }, []);

  const loadImages = async () => {
    setLoading(true);
    try {
      const response = await api.get("/api/product-images/");
      setImages(response.data.images || []);
    } catch (err) {
      console.error("Error loading images:", err);
      setMessage({
        type: "error",
        text: "ไม่สามารถโหลดรายการรูปภาพ",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSuccess = (data) => {
    setMessage({
      type: "success",
      text: data.message,
    });
    setSku("");
    loadImages();
  };

  const handleUploadError = (error) => {
    setMessage({
      type: "error",
      text: error,
    });
  };

  const handleDelete = async (imageSku) => {
    if (!window.confirm(`ต้องการลบรูปภาพสำหรับ SKU: ${imageSku} หรือไม่?`)) {
      return;
    }

    try {
      await api.delete(`/api/product-images/${imageSku}`);
      setMessage({
        type: "success",
        text: `ลบรูปภาพสำหรับ SKU: ${imageSku} สำเร็จ`,
      });
      loadImages();
    } catch (err) {
      setMessage({
        type: "error",
        text: "ไม่สามารถลบรูปภาพ",
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            จัดการรูปภาพสินค้า
          </h1>
          <p className="text-gray-600">
            อัพโหลดและจัดการรูปภาพสินค้า (ขนาดไม่เกิน 1 MB)
          </p>
        </div>

        {/* Message */}
        {message && (
          <div
            className={`mb-6 p-4 rounded-lg border ${
              message.type === "success"
                ? "bg-green-50 border-green-200 text-green-700"
                : "bg-red-50 border-red-200 text-red-700"
            }`}
          >
            {message.type === "success" ? "✅" : "❌"} {message.text}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Upload Section */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                อัพโหลดรูปภาพ
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    รหัสสินค้า (SKU)
                  </label>
                  <input
                    type="text"
                    value={sku}
                    onChange={(e) => setSku(e.target.value.toUpperCase())}
                    placeholder="เช่น SKU001"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {sku && (
                  <ProductImageUpload
                    sku={sku}
                    onUploadSuccess={handleUploadSuccess}
                    onUploadError={handleUploadError}
                  />
                )}

                {!sku && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-center">
                    <p className="text-gray-500 text-sm">
                      กรุณากรอก SKU เพื่อเริ่มอัพโหลด
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Images List */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">
                รูปภาพสินค้า ({images.length})
              </h2>

              {loading ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">กำลังโหลด...</p>
                </div>
              ) : images.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">ยังไม่มีรูปภาพ</p>
                </div>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  {images.map((image) => (
                    <div
                      key={image.sku}
                      className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-lg transition"
                    >
                      {/* Image */}
                      <div className="bg-gray-100 h-32 flex items-center justify-center overflow-hidden">
                        <img
                          src={image.url}
                          alt={image.sku}
                          className="max-h-full max-w-full object-contain"
                          onError={(e) => {
                            e.target.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%23f0f0f0' width='100' height='100'/%3E%3Ctext x='50' y='50' text-anchor='middle' dy='.3em' fill='%23999' font-size='12'%3ENo Image%3C/text%3E%3C/svg%3E";
                          }}
                        />
                      </div>

                      {/* Info */}
                      <div className="p-3 border-t border-gray-200">
                        <p className="text-sm font-mono font-bold text-gray-900 truncate">
                          {image.sku}
                        </p>
                        <p className="text-xs text-gray-500 truncate">
                          {image.filename}
                        </p>
                      </div>

                      {/* Actions */}
                      <div className="px-3 pb-3 flex gap-2">
                        <a
                          href={image.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-1 text-center px-2 py-1 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100 transition"
                        >
                          ดู
                        </a>
                        <button
                          onClick={() => handleDelete(image.sku)}
                          className="flex-1 text-center px-2 py-1 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100 transition"
                        >
                          ลบ
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
