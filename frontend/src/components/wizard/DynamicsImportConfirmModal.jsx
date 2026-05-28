import React from 'react';

const DynamicsImportConfirmModal = ({ open, onCancel, onConfirm }) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-5">
          <h3 className="text-lg font-bold text-gray-900">ก่อนส่งเข้า Dynamics 365</h3>
        </div>

        {/* Warning 1 — Refresh */}
        <div className="flex items-center gap-3 bg-red-50 border-2 border-red-400 rounded-xl px-4 py-3 mb-3">
          <div className="flex-shrink-0 w-7 h-7 bg-red-400 rounded-full flex items-center justify-center">
            <span className="text-white text-xl font-bold">1</span>
          </div>
          <span className="text-2xl">🔄</span>
          <div>
            <p className="text-l font-bold text-red-700">Refresh หน้า D365 ก่อน (F5)</p>
            <p className="text-xs text-red-500">เปิดค้างนาน → session หมด → RPA ล้มเหลว</p>
          </div>
        </div>

        {/* Warning 2 — Sales Quotes */}
        <div className="flex items-center gap-3 bg-yellow-50 border-2 border-yellow-400 rounded-xl px-4 py-3 mb-6">
          <div className="flex-shrink-0 w-7 h-7 bg-yellow-400 rounded-full flex items-center justify-center">
            <span className="text-white text-xl font-bold">2</span>
          </div>
          <span className="text-2xl">📋</span>
          <div>
            <p className="text-l font-bold text-yellow-700">อยู่ที่หน้า Sales Quotes</p>
            <p className="text-xs text-yellow-600">Sales → Sales Quotes ก่อนกดตกลง</p>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
          >
            ยกเลิก
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 px-4 py-3 bg-blue-600 rounded-lg font-semibold text-white hover:bg-blue-700 transition-colors"
          >
            ตกลง เริ่ม RPA
          </button>
        </div>
      </div>
    </div>
  );
};

export default DynamicsImportConfirmModal;
