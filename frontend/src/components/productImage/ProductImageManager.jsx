// components/productImage/ProductImageManager.jsx
import React, { useState, useEffect } from "react";
import api from "../../services/api.js";

export default function ProductImageManager() {
  const [sku, setSku] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [currentImage, setCurrentImage] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [allImages, setAllImages] = useState([]);
  const [loadingImages, setLoadingImages] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);

  // โหลดรายการรูปภาพทั้งหมด
  useEffect(() => {
    loadAllImages();
  }, []);

  const loadAllImages = async () => {
    try {
      setLoadingImages(true);
      const res = await api.get("/api/product-images/");
      setAllImages(res.data.images || []);
    } catch (err) {
      console.error("Error loading images:", err);
    } finally {
      setLoadingImages(false);
    }
  };

  // ค้นหาสินค้า
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        setSearchLoading(true);
        const res = await api.get("/api/items/search", {
          params: { q: searchQuery },
        });
        const results = res.data || [];
        console.log('Search results:', results); // Debug
        setSearchResults(results);
        setShowDropdown(results.length > 0);
      } catch (err) {
        console.error("Search error:", err);
        setSearchResults([]);
        setShowDropdown(false);
      } finally {
        setSearchLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // ปิด dropdown เมื่อคลิกข้างนอก
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest('.search-container')) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // เลือกสินค้าจาก dropdown
  const handleSelectItem = (item) => {
    setSku(item.sku);
    setSearchQuery(item.sku + " - " + item.name);
    setShowDropdown(false);
    checkExistingImage(item.sku);
  };

  // ตรวจสอบว่ามีรูปภาพสำหรับ SKU นี้หรือไม่
  const checkExistingImage = async (skuCode) => {
    if (!skuCode) {
      setCurrentImage(null);
      return;
    }

    try {
      const response = await fetch(`/api/product-images/${skuCode}`);
      if (response.ok) {
        setCurrentImage(`/api/product-images/${skuCode}?t=${Date.now()}`);
      } else {
        setCurrentImage(null);
      }
    } catch (err) {
      console.error("Error checking image:", err);
      setCurrentImage(null);
    }
  };

  // เมื่อเปลี่ยน SKU
  useEffect(() => {
    checkExistingImage(sku);
  }, [sku]);

  // เมื่อเลือกไฟล์
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      // ตรวจสอบขนาดไฟล์ (1MB = 1024 * 1024 bytes)
      const maxSize = 1024 * 1024; // 1MB
      if (file.size > maxSize) {
        setMessage({ 
          type: "error", 
          text: `ขนาดไฟล์เกิน 1MB (ขนาดปัจจุบัน: ${(file.size / 1024 / 1024).toFixed(2)}MB)` 
        });
        // รีเซ็ต input file
        e.target.value = '';
        return;
      }

      // ตรวจสอบประเภทไฟล์
      const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        setMessage({ 
          type: "error", 
          text: "รองรับเฉพาะไฟล์รูปภาพ (JPG, PNG, GIF, WebP)" 
        });
        e.target.value = '';
        return;
      }

      // ล้างข้อความเก่า
      setMessage({ type: "", text: "" });

      // สร้าง preview
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };


  // อัปโหลดรูปภาพ
  const handleUpload = async () => {
    if (!sku.trim()) {
      setMessage({ type: "error", text: "กรุณาเลือกสินค้า" });
      return;
    }

    if (!selectedFile) {
      setMessage({ type: "error", text: "กรุณาเลือกไฟล์รูปภาพ" });
      return;
    }

    try {
      setUploading(true);
      setMessage({ type: "", text: "" });

      const formData = new FormData();
      formData.append("file", selectedFile);

      const res = await api.post(`/api/product-images/upload/${sku}`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setMessage({ type: "success", text: res.data.message });
      setSelectedFile(null);
      setPreviewUrl(null);
      checkExistingImage(sku);
      loadAllImages();
    } catch (err) {
      console.error("Upload error:", err);
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "เกิดข้อผิดพลาดในการอัปโหลด",
      });
    } finally {
      setUploading(false);
    }
  };

  // ลบรูปภาพ
  const handleDelete = async (skuToDelete) => {
    const targetSku = skuToDelete || sku;
    
    if (!targetSku.trim()) {
      setMessage({ type: "error", text: "กรุณาเลือกสินค้า" });
      return;
    }

    if (!confirm(`ต้องการลบรูปภาพสำหรับ SKU: ${targetSku} หรือไม่?`)) {
      return;
    }

    try {
      setUploading(true);
      setMessage({ type: "", text: "" });

      const res = await api.delete(`/api/product-images/${targetSku}`);

      setMessage({ type: "success", text: res.data.message });
      
      // ถ้าลบรูปที่กำลังแสดงอยู่
      if (targetSku === sku) {
        setCurrentImage(null);
      }
      
      loadAllImages();
    } catch (err) {
      console.error("Delete error:", err);
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "เกิดข้อผิดพลาดในการลบ",
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* ส่วนอัปโหลด */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold mb-6">จัดการรูปภาพสินค้า</h2>

        {/* แสดงข้อความ */}
        {message.text && (
          <div
            className={`mb-4 p-4 rounded ${
              message.type === "success"
                ? "bg-green-100 text-green-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {message.text}
          </div>
        )}

        {/* ฟอร์มอัปโหลด */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* ซ้าย: ฟอร์ม */}
          <div className="space-y-4">
            <div className="relative search-container">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                ค้นหาสินค้า (SKU หรือชื่อสินค้า)
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onFocus={() => {
                  if (searchResults.length > 0) {
                    setShowDropdown(true);
                  }
                }}
                placeholder="พิมพ์อย่างน้อย 2 ตัวอักษร..."
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />

              {/* Dropdown */}
              {(showDropdown || searchLoading) && (
                <div className="absolute z-50 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-96 overflow-y-auto">
                  {searchLoading ? (
                    <div className="p-4 text-center text-gray-500">กำลังค้นหา...</div>
                  ) : searchResults.length === 0 ? (
                    <div className="p-4 text-center text-gray-500">ไม่พบสินค้า</div>
                  ) : (
                    searchResults.map((item) => (
                      <div
                        key={item.sku}
                        onClick={() => handleSelectItem(item)}
                        className="p-3 hover:bg-gray-100 cursor-pointer border-b last:border-b-0"
                      >
                        <div className="font-semibold text-sm">{item.sku}</div>
                        <div className="text-xs text-gray-600">{item.name}</div>
                        {item.category && (
                          <div className="text-xs text-gray-500">หมวด: {item.category}</div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}

              {sku && (
                <div className="mt-2 p-2 bg-blue-50 rounded text-sm">
                  <span className="font-semibold">SKU ที่เลือก:</span> {sku}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                เลือกรูปภาพ
              </label>
              <input
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="w-full px-4 py-2 border rounded-lg"
              />
              <p className="text-sm text-gray-500 mt-1">
                รองรับ: JPG, PNG, GIF, WebP (ขนาดไม่เกิน 1MB)
              </p>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleUpload}
                disabled={uploading || !sku || !selectedFile}
                className="flex-1 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {uploading ? "กำลังอัปโหลด..." : "อัปโหลด"}
              </button>

              {currentImage && (
                <button
                  onClick={handleDelete}
                  disabled={uploading}
                  className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  ลบรูป
                </button>
              )}
            </div>
          </div>

          {/* ขวา: Preview */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ตัวอย่าง
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 h-64 flex items-center justify-center bg-gray-50">
              {previewUrl ? (
                <img
                  src={previewUrl}
                  alt="Preview"
                  className="max-h-full max-w-full object-contain"
                />
              ) : currentImage ? (
                <div className="h-full w-full flex flex-col items-center justify-center">
                  <img
                    src={currentImage}
                    alt="Current"
                    className="max-h-[calc(100%-2rem)] max-w-full object-contain"
                  />
                  <p className="text-sm text-gray-500 mt-2">รูปภาพปัจจุบัน</p>
                </div>
              ) : (
                <p className="text-gray-400">ไม่มีรูปภาพ</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* รายการรูปภาพทั้งหมด */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold">รูปภาพทั้งหมด ({allImages.length})</h3>
          <button
            onClick={loadAllImages}
            className="text-blue-600 hover:text-blue-700"
          >
            🔄 รีเฟรช
          </button>
        </div>

        {loadingImages ? (
          <p className="text-center text-gray-500 py-8">กำลังโหลด...</p>
        ) : allImages.length === 0 ? (
          <p className="text-center text-gray-500 py-8">ยังไม่มีรูปภาพ</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {allImages.map((img) => (
              <div
                key={img.sku}
                className="border rounded-lg p-2 hover:shadow-lg transition-shadow relative group"
              >
                <div
                  className="aspect-square bg-gray-100 rounded mb-2 overflow-hidden cursor-pointer"
                  onClick={() => {
                    setSku(img.sku);
                    setSearchQuery(img.sku);
                    checkExistingImage(img.sku);
                  }}
                >
                  <img
                    src={img.url}
                    alt={img.sku}
                    className="w-full h-full object-contain"
                  />
                </div>
                <p className="text-xs font-mono text-center truncate mb-2">
                  {img.sku}
                </p>
                
                {/* ปุ่มลบ */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(img.sku);
                  }}
                  className="absolute top-1 right-1 bg-red-600 text-white p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-700"
                  title="ลบรูปภาพ"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
