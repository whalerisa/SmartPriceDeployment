import React, { useState, useEffect } from 'react';
import { ChevronDown, Check, X, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import api from '../services/api';
import { formatDateThai } from '../utils/dateFormatter';

export default function SpecialPriceApproval() {
  const { employee } = useAuth();
  const navigate = useNavigate();
  const [hasAccess, setHasAccess] = useState(false);
  const [loading, setLoading] = useState(true);
  const [requests, setRequests] = useState([]);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [actionType, setActionType] = useState(null); // 'approve' or 'reject'
  const [rejectionReason, setRejectionReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState(null);

  // ⭐ ตรวจสอบสิทธิ์จาก API
  useEffect(() => {
    const checkAccess = async () => {
      try {
        const res = await api.get("/api/config/page-access/check/special_price_approval");
        setHasAccess(res.data.has_access);
        console.log("🔐 Special Price Approval access check:", res.data);
      } catch (err) {
        console.error("Failed to check page access:", err);
        setHasAccess(false);
      } finally {
        setLoading(false);
      }
    };
    
    if (employee) {
      checkAccess();
    }
  }, [employee]);

  // ตรวจสอบสิทธิ์เข้าถึง
  useEffect(() => {
    if (!loading && employee && !hasAccess) {
      // ถ้าไม่มีสิทธิ์ ให้กลับไปที่ Dashboard
      navigate("/dashboard", { replace: true });
    }
  }, [loading, employee, hasAccess, navigate]);

  useEffect(() => {
    if (hasAccess) {
      fetchPendingRequests();
    }
  }, [hasAccess]);

  const fetchPendingRequests = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/special-price-requests/pending/approvals');
      console.log('[DEBUG] Pending requests:', response.data);
      if (response.data && response.data.length > 0) {
        console.log('[DEBUG] First request items:', response.data[0].items);
        if (response.data[0].items && response.data[0].items.length > 0) {
          console.log('[DEBUG] First item approval_level:', response.data[0].items[0].approval_level);
        }
      }
      setRequests(response.data || []);
    } catch (error) {
      setMessage({
        type: 'error',
        text: 'ไม่สามารถโหลดรายการขอราคาพิเศษได้'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedRequest) return;
    
    try {
      setSubmitting(true);
      await api.post(`/api/special-price-requests/${selectedRequest.id}/approve`);
      setMessage({
        type: 'success',
        text: 'อนุมัติราคาพิเศษสำเร็จ'
      });
      setSelectedRequest(null);
      setActionType(null);
      fetchPendingRequests();
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'ไม่สามารถอนุมัติได้'
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!selectedRequest || !rejectionReason.trim()) {
      setMessage({
        type: 'error',
        text: 'กรุณาระบุเหตุผลในการปฏิเสธ'
      });
      return;
    }

    try {
      setSubmitting(true);
      await api.post(`/api/special-price-requests/${selectedRequest.id}/reject`, {
        reason: rejectionReason
      });
      setMessage({
        type: 'success',
        text: 'ปฏิเสธราคาพิเศษสำเร็จ'
      });
      setSelectedRequest(null);
      setActionType(null);
      setRejectionReason('');
      fetchPendingRequests();
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'ไม่สามารถปฏิเสธได้'
      });
    } finally {
      setSubmitting(false);
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('th-TH', {
      style: 'currency',
      currency: 'THB'
    }).format(value);
  };

  // ⭐ ฟังก์ชันคำนวณราคาต่อหน่วยพิเศษ (sqft, kg)
  const getPricePerUnit = (item) => {
    const category = item.category || '';
    const isSoldByPack = item.is_sold_by_pack || false;
    
    // ถ้าขายยกแพค ให้เทียบเหมือนสินค้าปกติ
    if (isSoldByPack) {
      return {
        normal: item.normal_price,
        requested: item.requested_price,
        unit: item.unit || 'หน่วย'
      };
    }
    
    // กระจก: ต่อตารางฟุต
    if (category.toUpperCase() === 'G') {
      const sqft = item.sqft_sheet || 1;
      return {
        normal: sqft > 0 ? item.normal_price / sqft : item.normal_price,
        requested: sqft > 0 ? item.requested_price / sqft : item.requested_price,
        unit: 'ตร.ฟุต'
      };
    }
    
    // อลูมิเนียม: ต่อกิโลกรัม
    if (category.toUpperCase() === 'A') {
      const weight = item.product_weight || 1;
      return {
        normal: weight > 0 ? item.normal_price / weight : item.normal_price,
        requested: weight > 0 ? item.requested_price / weight : item.requested_price,
        unit: 'กิโลกรัม'
      };
    }
    
    // สินค้าอื่น: ต่อหน่วย
    return {
      normal: item.normal_price,
      requested: item.requested_price,
      unit: item.unit || 'หน่วย'
    };
  };

  const formatDate = (dateString) => {
    return formatDateThai(dateString);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">กำลังตรวจสอบสิทธิ์...</p>
        </div>
      </div>
    );
  }

  // ถ้าไม่มีสิทธิ์ ให้แสดงข้อความ
  if (employee && !hasAccess) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center max-w-md">
          <h2 className="text-xl font-bold text-red-800 mb-2">ไม่มีสิทธิ์เข้าถึง</h2>
          <p className="text-red-600">ขออภัย คุณไม่มีสิทธิ์เข้าถึงหน้านี้</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">อนุมัติราคาพิเศษ</h1>
          <p className="text-gray-600 mt-2">จำนวนรายการรอการอนุมัติ: {requests.length}</p>
        </div>

        {/* Message Alert */}
        {message && (
          <div className={`mb-6 p-4 rounded-lg flex items-start gap-3 ${
            message.type === 'success' 
              ? 'bg-green-50 border border-green-200' 
              : 'bg-red-50 border border-red-200'
          }`}>
            {message.type === 'success' ? (
              <Check className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            )}
            <p className={message.type === 'success' ? 'text-green-800' : 'text-red-800'}>
              {message.text}
            </p>
          </div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Requests List */}
          <div className="lg:col-span-2">
            {requests.length === 0 ? (
              <div className="bg-white rounded-lg shadow p-8 text-center">
                <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">ไม่มีรายการรอการอนุมัติ</p>
              </div>
            ) : (
              <div className="space-y-4">
                {requests.map((request) => (
                  <div
                    key={request.id}
                    onClick={() => setSelectedRequest(request)}
                    className={`bg-white rounded-lg shadow cursor-pointer transition-all ${
                      selectedRequest?.id === request.id
                        ? 'ring-2 ring-blue-500 shadow-lg'
                        : 'hover:shadow-md'
                    }`}
                  >
                    <div className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="font-semibold text-gray-900">
                            {request.customer_name}
                          </h3>
                          <p className="text-sm text-gray-600">
                            ใบขอเลขที่: {request.request_number}
                          </p>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                          request.status === 'SUBMITTED'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}>
                          {request.status === 'SUBMITTED' ? 'รอการอนุมัติ' : 'รอการอนุมัติระดับภาค'}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-4 mb-3">
                        <div>
                          <p className="text-xs text-gray-600">ราคาเดิม</p>
                          <p className="font-semibold text-gray-900">
                            {formatCurrency(request.original_total)}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-600">ราคาที่ขอ</p>
                          <p className="font-semibold text-blue-600">
                            {formatCurrency(request.requested_total)}
                          </p>
                        </div>
                      </div>

                      {request.valid_from && request.valid_to && (
                        <div className="mb-3 bg-blue-50 border border-blue-200 rounded p-2">
                          <p className="text-xs text-blue-700 font-medium">ระยะเวลาใช้ราคา</p>
                          <p className="text-sm text-blue-900">
                            {new Date(request.valid_from).toLocaleDateString('th-TH')} - {new Date(request.valid_to).toLocaleDateString('th-TH')}
                          </p>
                        </div>
                      )}

                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">
                          ส่วนลด: {request.discount_percentage?.toFixed(2)}%
                        </span>
                        <span className="text-gray-500">
                          {formatDate(request.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Details Panel */}
          {selectedRequest && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">รายละเอียด</h2>

              {/* Request Info */}
              <div className="space-y-4 mb-6 pb-6 border-b">
                <div>
                  <p className="text-sm text-gray-600">ลูกค้า</p>
                  <p className="font-semibold text-gray-900">{selectedRequest.customer_name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">ผู้ขอ</p>
                  <p className="font-semibold text-gray-900">{selectedRequest.requester_name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">เหตุผล</p>
                  <p className="text-gray-900">{selectedRequest.request_reason || '-'}</p>
                </div>
                {selectedRequest.valid_from && selectedRequest.valid_to && (
                  <div>
                    <p className="text-sm text-gray-600">ระยะเวลาใช้ราคา</p>
                    <p className="text-gray-900">
                      {new Date(selectedRequest.valid_from).toLocaleDateString('th-TH')} - {new Date(selectedRequest.valid_to).toLocaleDateString('th-TH')}
                    </p>
                  </div>
                )}
              </div>

              {/* Items */}
              <div className="mb-6 pb-6 border-b">
                <h3 className="font-semibold text-gray-900 mb-3">รายการสินค้า</h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {selectedRequest.items?.map((item, idx) => {
                    const priceInfo = getPricePerUnit(item);
                    return (
                      <div key={idx} className="text-sm bg-gray-50 p-2 rounded">
                        <p className="font-medium text-gray-900">{item.item_name}</p>
                        <p className="text-gray-600">
                          จำนวน: {item.quantity} {item.unit}
                        </p>
                        <p className="text-gray-600">
                          ราคา (ต่อ{priceInfo.unit}): {formatCurrency(priceInfo.normal)} → {formatCurrency(priceInfo.requested)}
                        </p>
                        {/* แสดงราคารวมด้วย */}
                        <p className="text-gray-500 text-xs">
                          รวม: {formatCurrency(item.normal_price)} → {formatCurrency(item.requested_price)}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Price Summary */}
              <div className="mb-6 pb-6 border-b space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">ราคาเดิม:</span>
                  <span className="font-semibold">{formatCurrency(selectedRequest.original_total)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">ราคาที่ขอ:</span>
                  <span className="font-semibold text-blue-600">{formatCurrency(selectedRequest.requested_total)}</span>
                </div>
                <div className="flex justify-between pt-2 border-t">
                  <span className="text-gray-600">ส่วนลด:</span>
                  <span className="font-semibold text-red-600">{selectedRequest.discount_percentage?.toFixed(2)}%</span>
                </div>
              </div>

              {/* Action Buttons */}
              {!actionType ? (
                <div className="space-y-3">
                  {/* Check approval flow based on status and approval level */}
                  {(() => {
                    // ตรวจสอบว่าต้องผ่าน RM, SDM, หรือ PM หรือไม่
                    const needsPmApproval = selectedRequest.items?.some(item => 
                      item.approval_level === 'PM_APPROVAL'
                    );
                    const needsRmApproval = selectedRequest.items?.some(item => 
                      item.approval_level === 'ZM_THEN_RM' || 
                      item.approval_level === 'RM' ||
                      item.approval_level === 'SDM' ||
                      item.approval_level === 'SDM_APPROVAL' ||
                      item.approval_level === 'ZM_THEN_RM_THEN_SDM' ||
                      item.approval_level === 'PM_APPROVAL'
                    );
                    const isPendingRm = selectedRequest.status === 'PENDING_RM';
                    const isPendingSdm = selectedRequest.status === 'PENDING_SDM' || selectedRequest.status === 'SDM_APPROVAL';
                    const isPendingPm = selectedRequest.status === 'PENDING_PM';
                    
                    // If status is PENDING_PM, this is PM's turn to approve (final for PM)
                    if (isPendingPm) {
                      return (
                        <>
                          <button
                            onClick={() => setActionType('approve')}
                            className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
                          >
                            <Check className="w-5 h-5" />
                            อนุมัติ (PM - ขั้นสุดท้าย)
                          </button>
                          <p className="text-xs text-gray-600 text-center">
                            ขั้นตอนสุดท้าย - อนุมัติโดย Product Manager
                          </p>
                        </>
                      );
                    }
                    
                    // If status is PENDING_SDM or SDM_APPROVAL, this is SDM's turn
                    if (isPendingSdm) {
                      // ตรวจสอบว่าต้องส่งต่อ PM หรือไม่
                      if (needsPmApproval) {
                        return (
                          <>
                            <button
                              onClick={() => setActionType('approve')}
                              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
                            >
                              <Check className="w-5 h-5" />
                              ส่งต่อ PM
                            </button>
                            <p className="text-xs text-gray-600 text-center">
                              ใบนี้ต้องผ่านการอนุมัติจาก Product Manager (เกินอำนาจ SDM)
                            </p>
                          </>
                        );
                      } else {
                        return (
                          <>
                            <button
                              onClick={() => setActionType('approve')}
                              className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
                            >
                              <Check className="w-5 h-5" />
                              อนุมัติ (SDM - ขั้นสุดท้าย)
                            </button>
                            <p className="text-xs text-gray-600 text-center">
                              ขั้นตอนสุดท้าย - อนุมัติโดย Sales Director Manager
                            </p>
                          </>
                        );
                      }
                    }
                    
                    // If status is PENDING_RM, this is RM's turn to approve
                    if (isPendingRm) {
                      // ตรวจสอบว่าต้องส่งต่อ SDM หรือ PM หรือไม่
                      const needsSdmOrPmApproval = selectedRequest.items?.some(item => 
                        item.approval_level === 'SDM' ||
                        item.approval_level === 'SDM_APPROVAL' ||
                        item.approval_level === 'ZM_THEN_RM_THEN_SDM' ||
                        item.approval_level === 'PM_APPROVAL'
                      );
                      
                      if (needsSdmOrPmApproval) {
                        return (
                          <>
                            <button
                              onClick={() => setActionType('approve')}
                              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
                            >
                              <Check className="w-5 h-5" />
                              ส่งต่อ SDM
                            </button>
                            <p className="text-xs text-gray-600 text-center">
                              ใบนี้ต้องผ่านการอนุมัติจาก Sales Director Manager (เกินอำนาจ RM)
                            </p>
                          </>
                        );
                      } else {
                        return (
                          <>
                            <button
                              onClick={() => setActionType('approve')}
                              className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
                            >
                              <Check className="w-5 h-5" />
                              อนุมัติ (RM - ขั้นสุดท้าย)
                            </button>
                          </>
                        );
                      }
                    }
                    
                    // If needs RM/SDM/PM approval but status is PENDING_ZM, this is ZM's turn
                    if (needsRmApproval || needsPmApproval) {
                      return (
                        <>
                          <button
                            onClick={() => setActionType('approve')}
                            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
                          >
                            <Check className="w-5 h-5" />
                            ส่งต่อ RM
                          </button>
                          <p className="text-xs text-gray-600 text-center">
                            ใบนี้ต้องผ่านการอนุมัติจาก Regional Manager (เกินอำนาจ ZM)
                          </p>
                        </>
                      );
                    }
                    
                    // ZM_ONLY - direct approval
                    return (
                      <button
                        onClick={() => setActionType('approve')}
                        className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
                      >
                        <Check className="w-5 h-5" />
                        อนุมัติ (ZM - ขั้นสุดท้าย)
                      </button>
                    );
                  })()}
                  <button
                    onClick={() => setActionType('reject')}
                    className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
                  >
                    <X className="w-5 h-5" />
                    ปฏิเสธ
                  </button>
                </div>
              ) : actionType === 'approve' ? (
                <div className="space-y-3">
                  {(() => {
                    const needsPmApproval = selectedRequest.items?.some(item => 
                      item.approval_level === 'PM_APPROVAL'
                    );
                    const needsRmApproval = selectedRequest.items?.some(item => 
                      item.approval_level === 'ZM_THEN_RM' || 
                      item.approval_level === 'RM' ||
                      item.approval_level === 'SDM' ||
                      item.approval_level === 'SDM_APPROVAL' ||
                      item.approval_level === 'ZM_THEN_RM_THEN_SDM' ||
                      item.approval_level === 'PM_APPROVAL'
                    );
                    const isPendingRm = selectedRequest.status === 'PENDING_RM';
                    const isPendingSdm = selectedRequest.status === 'PENDING_SDM' || selectedRequest.status === 'SDM_APPROVAL';
                    const isPendingPm = selectedRequest.status === 'PENDING_PM';
                    
                    if (isPendingPm) {
                      return <p className="text-sm text-gray-600">ยืนยันการอนุมัติราคาพิเศษนี้? (PM - ขั้นสุดท้าย)</p>;
                    } else if (isPendingSdm) {
                      if (needsPmApproval) {
                        return <p className="text-sm text-gray-600">ยืนยันการส่งต่อไปยัง Product Manager? (เกินอำนาจ SDM)</p>;
                      } else {
                        return <p className="text-sm text-gray-600">ยืนยันการอนุมัติราคาพิเศษนี้? (SDM - ขั้นสุดท้าย)</p>;
                      }
                    } else if (isPendingRm) {
                      const needsSdmOrPmApproval = selectedRequest.items?.some(item => 
                        item.approval_level === 'SDM' ||
                        item.approval_level === 'SDM_APPROVAL' ||
                        item.approval_level === 'ZM_THEN_RM_THEN_SDM' ||
                        item.approval_level === 'PM_APPROVAL'
                      );
                      if (needsSdmOrPmApproval) {
                        return <p className="text-sm text-gray-600">ยืนยันการส่งต่อไปยัง Sales Director Manager? (เกินอำนาจ RM)</p>;
                      } else {
                        return <p className="text-sm text-gray-600">ยืนยันการอนุมัติราคาพิเศษนี้? (RM - ขั้นสุดท้าย)</p>;
                      }
                    } else if (needsRmApproval || needsPmApproval) {
                      return <p className="text-sm text-gray-600">ยืนยันการส่งต่อไปยัง Regional Manager? (เกินอำนาจ ZM)</p>;
                    } else {
                      return <p className="text-sm text-gray-600">ยืนยันการอนุมัติราคาพิเศษนี้? (ZM - ขั้นสุดท้าย)</p>;
                    }
                  })()}
                  <div className="flex gap-2">
                    <button
                      onClick={handleApprove}
                      disabled={submitting}
                      className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                    >
                      {submitting ? 'กำลังประมวลผล...' : 'ยืนยัน'}
                    </button>
                    <button
                      onClick={() => setActionType(null)}
                      disabled={submitting}
                      className="flex-1 bg-gray-300 hover:bg-gray-400 disabled:bg-gray-400 text-gray-900 font-semibold py-2 px-4 rounded-lg transition-colors"
                    >
                      ยกเลิก
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <textarea
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="ระบุเหตุผลในการปฏิเสธ..."
                    className="w-full border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                    rows="3"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={handleReject}
                      disabled={submitting || !rejectionReason.trim()}
                      className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                    >
                      {submitting ? 'กำลังประมวลผล...' : 'ปฏิเสธ'}
                    </button>
                    <button
                      onClick={() => {
                        setActionType(null);
                        setRejectionReason('');
                      }}
                      disabled={submitting}
                      className="flex-1 bg-gray-300 hover:bg-gray-400 disabled:bg-gray-400 text-gray-900 font-semibold py-2 px-4 rounded-lg transition-colors"
                    >
                      ยกเลิก
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
