import { useState, useEffect } from "react";
import api from "../../services/api";

export default function UploadPriceExcel({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [scheduledDate, setScheduledDate] = useState(""); // วันที่ต้องการให้อัปโหลด
  const [uploadMode, setUploadMode] = useState(""); // "" | "immediate" | "scheduled" - เริ่มต้นไม่เลือก

  // No need to fetch regions and branches anymore since we read from file

  const handleUpload = async () => {
    if (!file || !uploadMode) return;

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

    // ⭐ ตรวจสอบ pattern ชื่อไฟล์: ต้องลงท้ายด้วย _G0000 (ตัวอักษรประเภท + เลข 4 หลัก)
    const filenameKeyPattern = /_[GAYSCE]\d{4}\.(xlsx|xls|csv)$/i;
    if (!filenameKeyPattern.test(file.name)) {
      alert(
        "⚠️ รูปแบบชื่อไฟล์ไม่ถูกต้อง\n\n" +
        "ชื่อไฟล์ต้องลงท้ายด้วย key รูปแบบ _G0000 (ตัวอักษรประเภท + เลข 4 หลัก)\n" +
        "ตัวอย่าง: Glass_690518_G0001.xlsx"
      );
      return;
    }

    // ⭐ Validate Excel file before upload (immediate mode only)
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

      // ⭐ เลือก endpoint ตามโหมด (ไม่ต้องส่ง branch_code แล้ว)
      let endpoint;
      if (uploadMode === "immediate") {
        endpoint = `/api/admin/prices/upload`;
      } else {
        // Scheduled upload - still needs branch_code for scheduled jobs
        endpoint = `/api/admin/prices/schedule?scheduled_date=${scheduledDate}`;
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

  // ⭐ Validate Excel file for NULL values and Branch column
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
          const requiredColumns = ['SDM', 'R2', 'R1', 'W2', 'W1', 'Branch'];
          const skuColumns = ['SKU', 'No_', 'Item_No', 'No', 'ItemNo'];
          const branchColumns = ['Branch', 'BranchCode', 'Branch_Code', 'สาขา'];
          
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
          
          // Find Branch column index
          let branchIndex = -1;
          for (const col of branchColumns) {
            branchIndex = headers.findIndex(h => h === col);
            if (branchIndex !== -1) break;
          }
          
          if (branchIndex === -1) {
            resolve({ valid: false, errors: ['ไม่พบคอลัมน์ Branch (ต้องมี Branch, BranchCode, Branch_Code, หรือ สาขา)'] });
            return;
          }
          
          // Find required column indices (excluding Branch since we already checked it)
          const columnIndices = {};
          const missingColumns = [];
          
          for (const col of requiredColumns) {
            if (col === 'Branch') continue; // Already checked
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
            const branch = row[branchIndex];
            
            // Skip empty rows
            if (!sku || sku.toString().trim() === '') continue;
            
            // Check Branch column
            if (!branch || branch.toString().trim() === '') {
              errors.push(`แถวที่ ${i + 1} (SKU: ${sku}): คอลัมน์ Branch เป็นค่าว่าง`);
            }
            
            // Check each required column
            for (const col of Object.keys(columnIndices)) {
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

        {/* Info Box - Branch from File */}
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start gap-2">
            <span className="text-blue-600 text-lg">ℹ️</span>
            <div className="flex-1">
              <div className="text-sm font-semibold text-blue-900 mb-1">
                รหัสสาขาจะถูกอ่านจากไฟล์ Excel
              </div>
              <div className="text-xs text-blue-800">
                ไฟล์ Excel ต้องมีคอลัมน์ <span className="font-mono font-semibold">Branch</span> (หรือ BranchCode, Branch_Code, สาขา) 
                ระบบจะบันทึกราคาลงสาขาที่ระบุในแต่ละแถวโดยอัตโนมัติ
              </div>
            </div>
          </div>
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
            disabled={!file || !uploadMode || loading || (uploadMode === "scheduled" && !scheduledDate)}
            className={`
              px-6 py-2 rounded-lg text-sm font-semibold text-white
              transition-all
              ${
                loading || !file || !uploadMode || (uploadMode === "scheduled" && !scheduledDate)
                  ? "bg-gray-300 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 active:scale-95"
              }
            `}
          >
            {loading 
              ? "กำลังประมวลผล..." 
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
          รองรับเฉพาะไฟล์ .xlsx • ชื่อไฟล์ต้องลงท้ายด้วย _G0000 เช่น <span className="font-mono">Glass_690518_G0001.xlsx</span> • ไฟล์ต้องมีคอลัมน์ Branch (หรือ BranchCode, Branch_Code, สาขา)
          {uploadMode === "scheduled" && " • ระบบจะอัปโหลดอัตโนมัติในวันที่กำหนด"}
        </div>
      </div>
    </div>
  );
}
