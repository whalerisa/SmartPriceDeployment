import { useState, useEffect } from "react";
import api from "../../services/api";

export default function UploadPriceExcel({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [regions, setRegions] = useState([]);
  const [branches, setBranches] = useState([]);
  const [selectedBranches, setSelectedBranches] = useState([]);
  const [loadingRegions, setLoadingRegions] = useState(true);
  const [loadingBranches, setLoadingBranches] = useState(false);
  const [scheduledDate, setScheduledDate] = useState(""); // วันที่ต้องการให้อัปโหลด
  const [uploadMode, setUploadMode] = useState(""); // "" | "immediate" | "scheduled" - เริ่มต้นไม่เลือก
  const [selectionMode, setSelectionMode] = useState(""); // "" | "branch" | "region" - วิธีการเลือก
  const [selectedRegion, setSelectedRegion] = useState(""); // เลือกภูมิภาค

  // Fetch regions on component mount
  useEffect(() => {
    const fetchRegions = async () => {
      try {
        console.log("Fetching regions from /api/branches/regions");
        const res = await api.get("/api/branches/regions");
        console.log("Regions response:", res.data);
        
        setRegions(res.data.regions || []);
      } catch (error) {
        console.error("Failed to fetch regions:", error);
        console.error("Error response:", error.response?.data);
      } finally {
        setLoadingRegions(false);
      }
    };

    fetchRegions();
  }, []);

  // Fetch all branches on component mount
  useEffect(() => {
    const fetchAllBranches = async () => {
      try {
        console.log("Fetching all branches from /api/branches");
        const res = await api.get("/api/branches");
        console.log("All branches response:", res.data);
        
        setBranches(res.data.branches || []);
      } catch (error) {
        console.error("Failed to fetch branches:", error);
        console.error("Error response:", error.response?.data);
      }
    };

    fetchAllBranches();
  }, []);

  // Fetch branches when region is selected (for region selection mode)
  useEffect(() => {
    if (selectionMode !== "region" || !selectedRegion) {
      return;
    }

    const fetchBranchesByRegion = async () => {
      setLoadingBranches(true);
      try {
        console.log(`Fetching branches for region: ${selectedRegion}`);
        const res = await api.get(`/api/branches/regions/${selectedRegion}`);
        console.log("Branches response:", res.data);
        
        // Auto-select all branches in the region
        const branchCodes = res.data.branches.map(b => b.Code);
        setSelectedBranches(branchCodes);
      } catch (error) {
        console.error("Failed to fetch branches:", error);
        console.error("Error response:", error.response?.data);
        setSelectedBranches([]);
      } finally {
        setLoadingBranches(false);
      }
    };

    fetchBranchesByRegion();
  }, [selectionMode, selectedRegion]);

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
    if (!file || selectedBranches.length === 0 || !selectionMode) return;

    // ⭐ ตรวจสอบว่าเลือกโหมดการอัปโหลดหรือยัง
    if (!uploadMode) {
      alert("❌ กรุณาเลือกโหมดการอัปโหลด");
      return;
    }

    // ⭐ ตรวจสอบว่าเลือก scheduled แต่ไม่ได้เลือกวันที่
    if (uploadMode === "scheduled" && !scheduledDate) {
      alert("❌ กรุณาเลือกวันที่ต้องการอัปโหลด");
      return;
    }

    // ⭐ Validate Excel file before upload
    if (uploadMode === "immediate") {
      const validationResult = await validateExcelFile(file);
      if (!validationResult.valid) {
        alert(`❌ ไฟล์มีข้อผิดพลาด!\n\n${validationResult.errors.join('\n')}`);
        return;
      }
    }

    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);

      // Send branch_codes as query parameter (comma-separated)
      const branchCodes = selectedBranches.join(",");
      
      // ⭐ เลือก endpoint ตามโหมด
      let endpoint;
      if (uploadMode === "immediate") {
        endpoint = `/api/admin/prices/upload?branch_code=${branchCodes}`;
      } else {
        // Scheduled upload
        endpoint = `/api/admin/prices/schedule?branch_code=${branchCodes}&scheduled_date=${scheduledDate}`;
      }
      
      const res = await api.post(endpoint, form);
      
      // ⭐ แสดงข้อความสำเร็จ
      if (uploadMode === "immediate") {
        let message = `✅ อัปโหลดเสร็จสิ้น!\n\n`;
        message += `อัปเดตราคาสำเร็จ: ${res.data.successful_updates} รายการ\n`;
        message += `ข้อผิดพลาด: ${res.data.errors} รายการ`;
        
        // ⭐ แสดงรายละเอียด errors (ถ้ามี)
        if (res.data.errors > 0 && res.data.error_details && res.data.error_details.length > 0) {
          message += `\n\n📋 รายละเอียดข้อผิดพลาด:\n`;
          const maxErrors = 10; // แสดงสูงสุด 10 รายการ
          const errorsToShow = res.data.error_details.slice(0, maxErrors);
          message += errorsToShow.join('\n');
          
          if (res.data.error_details.length > maxErrors) {
            message += `\n... และอีก ${res.data.error_details.length - maxErrors} รายการ`;
          }
        }
        
        alert(message);
        onUploaded(res.data);
      } else {
        alert(`✅ บันทึกตารางอัปโหลดสำเร็จ!\n\nไฟล์จะถูกอัปโหลดอัตโนมัติในวันที่: ${scheduledDate}`);
      }
      
      // ⭐ รีเซ็ตฟอร์ม
      setFile(null);
      setSelectedBranches([]);
      setSelectedRegion("");
      setSelectionMode("");
      setScheduledDate("");
      setUploadMode(""); // รีเซ็ตเป็นไม่เลือก
    } catch (error) {
      // แสดงข้อความ error
      const errorMsg = error.response?.data?.detail || error.message || "เกิดข้อผิดพลาดในการอัปโหลด";
      alert(`❌ เกิดข้อผิดพลาด!\n\n${errorMsg}`);
    } finally {
      setLoading(false);
    }
  };

  // ⭐ Validate Excel file for NULL values in required columns
  const validateExcelFile = async (file) => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      
      reader.onload = async (e) => {
        try {
          // Dynamically import xlsx
          const XLSX = await import('xlsx');
          const data = new Uint8Array(e.target.result);
          const workbook = XLSX.read(data, { type: 'array' });
          
          // Get first sheet
          const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
          const rows = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });
          
          if (rows.length < 2) {
            resolve({ valid: false, errors: ['ไฟล์ว่างเปล่าหรือไม่มีข้อมูล'] });
            return;
          }
          
          // Get headers (first row)
          const headers = rows[0];
          
          // Find required columns
          const requiredColumns = ['SDM', 'R2', 'R1', 'W2', 'W1'];
          const skuColumns = ['SKU', 'No_', 'Item_No', 'No', 'ItemNo'];
          
          // Find SKU column index
          let skuIndex = -1;
          for (const col of skuColumns) {
            skuIndex = headers.findIndex(h => h === col);
            if (skuIndex !== -1) break;
          }
          
          if (skuIndex === -1) {
            resolve({ valid: false, errors: ['ไม่พบคอลัมน์ SKU (ต้องมี SKU, No_, Item_No, No, หรือ ItemNo)'] });
            return;
          }
          
          // Find required column indices
          const columnIndices = {};
          const missingColumns = [];
          
          for (const col of requiredColumns) {
            const index = headers.findIndex(h => h === col);
            if (index === -1) {
              missingColumns.push(col);
            } else {
              columnIndices[col] = index;
            }
          }
          
          if (missingColumns.length > 0) {
            resolve({ 
              valid: false, 
              errors: [`ไม่พบคอลัมน์ที่จำเป็น: ${missingColumns.join(', ')}`] 
            });
            return;
          }
          
          // Check for NULL values in required columns
          const errors = [];
          const maxRowsToCheck = Math.min(rows.length, 1000); // Check first 1000 rows
          
          for (let i = 1; i < maxRowsToCheck; i++) {
            const row = rows[i];
            const sku = row[skuIndex];
            
            // Skip empty rows
            if (!sku || sku.toString().trim() === '') continue;
            
            // Check each required column
            for (const col of requiredColumns) {
              const value = row[columnIndices[col]];
              
              if (value === null || value === undefined || value === '') {
                errors.push(`แถวที่ ${i + 1} (SKU: ${sku}): คอลัมน์ ${col} เป็นค่าว่าง`);
              }
            }
            
            // Limit error messages
            if (errors.length >= 10) {
              errors.push('... และอื่นๆ (แสดงเฉพาะ 10 รายการแรก)');
              break;
            }
          }
          
          if (errors.length > 0) {
            resolve({ valid: false, errors });
          } else {
            resolve({ valid: true, errors: [] });
          }
          
        } catch (error) {
          console.error('Validation error:', error);
          resolve({ valid: false, errors: ['ไม่สามารถอ่านไฟล์ได้ กรุณาตรวจสอบรูปแบบไฟล์'] });
        }
      };
      
      reader.onerror = () => {
        resolve({ valid: false, errors: ['ไม่สามารถอ่านไฟล์ได้'] });
      };
      
      reader.readAsArrayBuffer(file);
    });
  };

  const clearFile = () => {
    setFile(null);
  };

  return (
    <div className="mt-4 p-6 border rounded-xl bg-white shadow-sm">
      <div className="flex flex-col gap-4">
        {/* Upload Mode Selection */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700">
            โหมดการอัปโหลด <span className="text-red-500">*</span>
          </label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="uploadMode"
                value="immediate"
                checked={uploadMode === "immediate"}
                onChange={(e) => setUploadMode(e.target.value)}
                className="w-4 h-4 text-blue-600"
              />
              <span className="text-sm text-gray-700">อัปโหลดทันที</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="uploadMode"
                value="scheduled"
                checked={uploadMode === "scheduled"}
                onChange={(e) => setUploadMode(e.target.value)}
                className="w-4 h-4 text-blue-600"
              />
              <span className="text-sm text-gray-700">กำหนดวันที่อัปโหลด</span>
            </label>
          </div>
          {!uploadMode && (
            <div className="text-xs text-amber-600 mt-1">
              ⚠️ กรุณาเลือกโหมดการอัปโหลด
            </div>
          )}
        </div>

        {/* Scheduled Date Picker (แสดงเฉพาะเมื่อเลือก scheduled) */}
        {uploadMode === "scheduled" && (
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-700">
              วันที่ต้องการให้อัปโหลด <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={scheduledDate}
              onChange={(e) => setScheduledDate(e.target.value)}
              min={new Date().toISOString().split('T')[0]} // ไม่ให้เลือกวันที่ย้อนหลัง
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <div className="text-xs text-gray-500">
              ระบบจะอัปโหลดไฟล์อัตโนมัติในวันที่ที่เลือก
            </div>
          </div>
        )}

        {/* Selection Mode Toggle */}
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-gray-700">
            วิธีการเลือกสาขา <span className="text-red-500">*</span>
          </label>
          <div className="flex gap-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
            <label className="flex items-center gap-2 cursor-pointer flex-1">
              <input
                type="radio"
                name="selectionMode"
                value="branch"
                checked={selectionMode === "branch"}
                onChange={(e) => {
                  setSelectionMode(e.target.value);
                  setSelectedBranches([]);
                  setSelectedRegion("");
                }}
                className="w-4 h-4 text-blue-600"
              />
              <div className="flex-1">
                <span className="text-sm font-medium text-gray-700">เลือกรายสาขา</span>
                <p className="text-xs text-gray-500">เลือกได้หลายสาขา</p>
              </div>
            </label>
            <label className="flex items-center gap-2 cursor-pointer flex-1">
              <input
                type="radio"
                name="selectionMode"
                value="region"
                checked={selectionMode === "region"}
                onChange={(e) => {
                  setSelectionMode(e.target.value);
                  setSelectedBranches([]);
                  setSelectedRegion("");
                }}
                className="w-4 h-4 text-blue-600"
              />
              <div className="flex-1">
                <span className="text-sm font-medium text-gray-700">เลือกตามภาค</span>
                <p className="text-xs text-gray-500">เลือกภาคเดียว</p>
              </div>
            </label>
          </div>
          {!selectionMode && (
            <div className="text-xs text-amber-600 mt-1">
              ⚠️ กรุณาเลือกวิธีการเลือกสาขา
            </div>
          )}
        </div>

        {/* Region Selection (แสดงเฉพาะเมื่อเลือก region mode) */}
        {selectionMode === "region" && (
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-700">
              เลือกภูมิภาค <span className="text-red-500">*</span>
            </label>
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              disabled={loadingRegions}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              <option value="">-- เลือกภูมิภาค --</option>
              {loadingRegions ? (
                <option disabled>กำลังโหลดภูมิภาค...</option>
              ) : (
                regions.map((region) => (
                  <option key={region.code} value={region.code}>
                    {region.name} ({region.branches.length} สาขา)
                  </option>
                ))
              )}
            </select>
            
            {/* Show selected region info and branches */}
            {selectedRegion && !loadingBranches && (
              <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="text-sm font-semibold text-blue-900 mb-2">
                  ✓ ภูมิภาค: {regions.find(r => r.code === selectedRegion)?.name}
                </div>
                <div className="text-xs text-blue-800 mb-2">
                  สาขาที่จะอัปโหลด ({selectedBranches.length} สาขา):
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedBranches.map((branchCode) => {
                    const branch = regions
                      .find(r => r.code === selectedRegion)
                      ?.branches.find(b => b.Code === branchCode);
                    return (
                      <span
                        key={branchCode}
                        className="inline-block px-2 py-1 bg-blue-200 text-blue-900 rounded text-xs font-medium"
                      >
                        {branchCode} - {branch?.Name}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
            
            {loadingBranches && (
              <div className="text-xs text-gray-500">
                กำลังโหลดสาขา...
              </div>
            )}
          </div>
        )}

        {/* Branch Selection - Multi Select (แสดงเฉพาะเมื่อเลือก branch mode) */}
        {selectionMode === "branch" && (
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-gray-700">
              เลือกสาขา <span className="text-red-500">*</span>
            </label>
            <div className="border border-gray-300 rounded-lg p-3 bg-white max-h-96 overflow-y-auto">
              {branches.length === 0 ? (
                <div className="text-sm text-gray-500">กำลังโหลดสาขา...</div>
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
        )}

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
            disabled={!file || selectedBranches.length === 0 || !uploadMode || !selectionMode || loading || (uploadMode === "scheduled" && !scheduledDate)}
            className={`
              px-6 py-2 rounded-lg text-sm font-semibold text-white
              transition-all
              ${
                loading || !file || selectedBranches.length === 0 || !uploadMode || !selectionMode || (uploadMode === "scheduled" && !scheduledDate)
                  ? "bg-gray-300 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 active:scale-95"
              }
            `}
          >
            {loading 
              ? "กำลังประมวลผล..." 
              : !selectionMode
                ? "เลือกวิธีการเลือกสาขา"
                : !uploadMode
                  ? "เลือกโหมดการอัปโหลด"
                  : uploadMode === "immediate" 
                    ? "อัปโหลดทันที" 
                    : "บันทึกตารางอัปโหลด"
            }
          </button>
        </div>

        {/* Hint */}
        <div className="mt-1 text-xs text-gray-400">
          รองรับเฉพาะไฟล์ .xlsx • เลือกวิธีการเลือกสาขา (รายสาขาหรือตามภาค) • เลือกสาขาอย่างน้อย 1 สาขาก่อนอัปโหลด
          {uploadMode === "scheduled" && " • ระบบจะอัปโหลดอัตโนมัติในวันที่กำหนด"}
        </div>
      </div>
    </div>
  );
}
