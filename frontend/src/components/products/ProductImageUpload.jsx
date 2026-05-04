// components/products/ProductImageUpload.jsx
import { useState } from "react";
import { api } from "../../services/api";

const MAX_FILE_SIZE = 1 * 1024 * 1024; // 1 MB
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];

export default function ProductImageUpload({ sku, onUploadSuccess, onUploadError }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [preview, setPreview] = useState(null);

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // ตรวจสอบประเภทไฟล์
    if (!ALLOWED_TYPES.includes(file.type)) {
      const errorMsg = "ไฟล์ต้องเป็นรูปภาพ (JPG, PNG, GIF, WebP)";
      setError(errorMsg);
      onUploadError?.(errorMsg);
      return;
    }

    // ตรวจสอบขนาดไฟล์
    if (file.size > MAX_FILE_SIZE) {
      const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
      const errorMsg = `ขนาดไฟล์เกินขีดจำกัด (${fileSizeMB} MB > 1 MB)`;
      setError(errorMsg);
      onUploadError?.(errorMsg);
      return;
    }

    // สร้าง preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target.result);
    };
    reader.readAsDataURL(file);

    // อัพโหลดไฟล์
    await uploadFile(file);
  };

  const uploadFile = async (file) => {
    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post(`/api/product-images/upload/${sku}`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      if (response.data.success) {
        const successMsg = `อัพโหลดรูปสำเร็จ (${response.data.file_size_mb} MB)`;
        setSuccess(successMsg);
        onUploadSuccess?.(response.data);
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || "เกิดข้อผิดพลาดในการอัพโหลด";
      setError(errorMsg);
      onUploadError?.(errorMsg);
      setPreview(null);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Input File */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition">
        <input
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          disabled={uploading}
          className="hidden"
          id="product-image-input"
        />
        <label
          htmlFor="product-image-input"
          className={`cursor-pointer block ${uploading ? "opacity-50" : ""}`}
        >
          <div className="text-4xl mb-2">📸</div>
          <p className="text-gray-600 font-medium">
            {uploading ? "กำลังอัพโหลด..." : "คลิกเพื่อเลือกรูปภาพ"}
          </p>
          <p className="text-sm text-gray-400 mt-1">
            JPG, PNG, GIF, WebP (ไม่เกิน 1 MB)
          </p>
        </label>
      </div>

      {/* Preview */}
      {preview && (
        <div className="border rounded-lg p-4 bg-gray-50">
          <p className="text-sm text-gray-600 mb-2">ตัวอย่าง:</p>
          <img
            src={preview}
            alt="Preview"
            className="max-h-48 max-w-full mx-auto rounded"
          />
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700 text-sm">❌ {error}</p>
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-700 text-sm">✅ {success}</p>
        </div>
      )}

      {/* Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-blue-700 text-sm">
          ℹ️ SKU: <span className="font-mono font-bold">{sku}</span>
        </p>
      </div>
    </div>
  );
}
