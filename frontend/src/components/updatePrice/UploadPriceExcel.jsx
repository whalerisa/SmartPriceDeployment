import React, { useState, useEffect } from "react";
import api from "../../services/api";

export default function UploadPriceExcel({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [branches, setBranches] = useState([]);
  const [selectedBranches, setSelectedBranches] = useState([]);
  const [loadingBranches, setLoadingBranches] = useState(true);

  // Fetch branches on component mount
  useEffect(() => {
    const fetchBranches = async () => {
      try {
        console.log("Fetching branches from /api/branches");
        const res = await api.get("/api/branches");
        console.log("Branches response:", res.data);
        
        setBranches(res.data.branches || []);
      } catch (error) {
        console.error("Failed to fetch branches:", error);
        console.error("Error response:", error.response?.data);
      } finally {
        setLoadingBranches(false);
      }
    };

    fetchBranches();
  }, []);

  const handleBranchToggle = (branchCode) => {
    setSelectedBranches((prev) =>
      prev.includes(branchCode)
        ? prev.filter((code) => code !== branchCode)
        : [...prev, branchCode]
    );
  };

  const handleSelectAll = () => {
    if (selectedBranches.length === branches.length) {
      // Deselect all
      setSelectedBranches([]);
    } else {
      // Select all
      setSelectedBranches(branches.map((b) => b.Code));
    }
  };

  const handleUpload = async () => {
    if (!file || selectedBranches.length === 0) return;

    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);

      // Send branch_codes as query parameter (comma-separated)
      const branchCodes = selectedBranches.join(",");
      const res = await api.post(`/api/admin/prices/upload?branch_code=${branchCodes}`, form);
      
      // ⭐ แสดงข้อความสำเร็จ
      alert(`✅ อัปโหลดเสร็จสิ้น!\n\nอัปเดตราคาสำเร็จ: ${res.data.successful_updates} รายการ\nข้อผิดพลาด: ${res.data.errors} รายการ`);
      
      onUploaded(res.data);
      
      // ⭐ รีเซ็ตฟอร์ม
      setFile(null);
      setSelectedBranches([]);
    } catch (error) {
      // แสดงข้อความ error
      const errorMsg = error.response?.data?.detail || error.message || "เกิดข้อผิดพลาดในการอัปโหลด";
      alert(`❌ เกิดข้อผิดพลาด!\n\n${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  const clearFile = () => {
    setFile(null);
  };

  return (
    <div className="mt-4 p-6 border rounded-xl bg-white shadow-sm">
      <div className="flex flex-col gap-4">
        {/* Branch Selection - Multi Select */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700">
            เลือกสาขา <span className="text-red-500">*</span>
          </label>
          <div className="border border-gray-300 rounded-lg p-3 bg-white max-h-48 overflow-y-auto">
            {loadingBranches ? (
              <div className="text-sm text-gray-500">กำลังโหลดสาขา...</div>
            ) : branches.length === 0 ? (
              <div className="text-sm text-gray-500">ไม่พบข้อมูลสาขา</div>
            ) : (
              <div className="space-y-2">
                {/* Select All Checkbox */}
                <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-2 rounded border-b border-gray-200 pb-3 mb-2">
                  <input
                    type="checkbox"
                    checked={selectedBranches.length === branches.length && branches.length > 0}
                    onChange={handleSelectAll}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-sm font-semibold text-gray-800">
                    เลือกทั้งหมด
                  </span>
                </label>

                {/* Individual Branch Checkboxes */}
                {branches.map((branch) => (
                  <label key={branch.Code} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-2 rounded">
                    <input
                      type="checkbox"
                      checked={selectedBranches.includes(branch.Code)}
                      onChange={() => handleBranchToggle(branch.Code)}
                      className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">
                      {branch.Code} - {branch.Name}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>
          {selectedBranches.length > 0 && (
            <div className="text-xs text-blue-600">
              เลือกแล้ว {selectedBranches.length} สาขา
            </div>
          )}
        </div>

        {/* File Upload Section */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-6">
          {/* File Picker */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={(e) => setFile(e.target.files[0])}
            />

            <span className="px-4 py-2 rounded-lg border border-gray-300 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700">
              เลือกไฟล์ Excel
            </span>
          </label>

          {/* Selected file + clear */}
          {file && (
            <div className="items-center gap-2 bg-gray-100 px-3 py-2 rounded-lg">
              <span className="text-sm text-gray-700 truncate max-w-xs">{file.name}</span>

              {/* ❌ Clear file */}
              <button
                onClick={clearFile}
                className="text-gray-400 hover:text-red-500 font-bold"
                title="เปลี่ยนไฟล์"
              >
                ✕
              </button>
            </div>
          )}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={!file || selectedBranches.length === 0 || loading}
            className={`
              px-6 py-2 rounded-lg text-sm font-semibold text-white
              transition-all
              ${
                loading || !file || selectedBranches.length === 0
                  ? "bg-gray-300 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 active:scale-95"
              }
            `}
          >
            {loading ? "กำลังอัปโหลด..." : "อัปโหลดไฟล์"}
          </button>
        </div>

        {/* Hint */}
        <div className="mt-1 text-xs text-gray-400">
          รองรับเฉพาะไฟล์ .xlsx • เลือกสาขาได้หลายสาขา • กรุณาเลือกสาขาอย่างน้อย 1 สาขาก่อนอัปโหลด
        </div>
      </div>
    </div>
  );
}
