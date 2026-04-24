import React, { useState, useEffect } from "react";
import { useAuth } from "../hooks/useAuth.js";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

function AdminConfig() {
  const { employee } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("price");
  const [config, setConfig] = useState(null);
  const [editedConfig, setEditedConfig] = useState(null);
  const [message, setMessage] = useState(null);
  const [availableRoles, setAvailableRoles] = useState([]);
  const [newRoleName, setNewRoleName] = useState("");
  const [regionMapping, setRegionMapping] = useState(null);
  const [editedRegionMapping, setEditedRegionMapping] = useState(null);

  // ตรวจสอบสิทธิ์ admin
  useEffect(() => {
    const isAdmin = employee?.role && 
      typeof employee.role === "string" && 
      employee.role.toLowerCase() === "admin";
    
    if (!isAdmin) {
      navigate("/");
    }
  }, [employee, navigate]);

  // โหลดข้อมูล config
  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const configRes = await api.get("/api/config/settings");
      setConfig(configRes.data);
      setEditedConfig(JSON.parse(JSON.stringify(configRes.data)));
      
      // Load available roles
      try {
        const rolesRes = await api.get("/api/config/roles");
        setAvailableRoles(rolesRes.data || []);
      } catch (err) {
        console.error("Failed to load roles:", err);
        setAvailableRoles(["Sales", "Sales_Project", "ZM", "RM", "SDM", "PM", "CEO", "Admin"]);
      }

      // Load region mapping
      try {
        const regionRes = await api.get("/api/config/regions");
        setRegionMapping(regionRes.data);
        setEditedRegionMapping(JSON.parse(JSON.stringify(regionRes.data)));
      } catch (err) {
        console.error("Failed to load region mapping:", err);
      }
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "ไม่สามารถโหลดข้อมูล Config ได้",
      });
      console.error("Config load error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddRole = async () => {
    const roleCode = newRoleName.trim();
    
    if (!roleCode) {
      setMessage({
        type: "error",
        text: "กรุณากรอกชื่อ Role",
      });
      return;
    }
    
    try {
      await api.post("/api/config/roles", {
        role_code: roleCode,
        role_name_thai: roleCode,
        role_display_name: roleCode,
      });
      
      setMessage({
        type: "success",
        text: `เพิ่ม Role "${roleCode}" สำเร็จ - สามารถกำหนดสิทธิ์ด้านล่างได้เลย`,
      });
      
      setNewRoleName("");
      await loadConfig();
      
      setTimeout(() => setMessage(null), 5000);
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "เกิดข้อผิดพลาดในการเพิ่ม Role",
      });
    }
  };

  const handleDeleteRole = async (role) => {
    if (!confirm(`ต้องการลบ Role "${role}" หรือไม่?\n\n⚠️ การลบจะทำให้ Role นี้หายจากการกำหนดสิทธิ์ทั้งหมด`)) return;
    
    try {
      await api.delete(`/api/config/roles/${role}`);
      setMessage({
        type: "success",
        text: `ลบ Role "${role}" สำเร็จ`,
      });
      await loadConfig();
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "เกิดข้อผิดพลาดในการลบ Role",
      });
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      
      // Save main config
      await api.put("/api/config/settings", editedConfig);
      
      // Save region mapping changes
      if (editedRegionMapping && regionMapping) {
        const regionUpdates = [];
        
        Object.keys(editedRegionMapping.regions).forEach((regionCode) => {
          const originalRM = regionMapping.regions[regionCode]?.rm_employee_id;
          const editedRM = editedRegionMapping.regions[regionCode]?.rm_employee_id;
          
          console.log(`🔍 Region ${regionCode}: ${originalRM} → ${editedRM}`);
          
          if (originalRM !== editedRM) {
            console.log(`📡 Updating region ${regionCode} RM to ${editedRM}`);
            regionUpdates.push(
              api.put(`/api/config/regions/${regionCode}`, {
                rm_employee_id: editedRM,
              })
            );
          }
        });
        
        if (regionUpdates.length > 0) {
          console.log(`📡 Sending ${regionUpdates.length} region updates...`);
          try {
            const results = await Promise.all(regionUpdates);
            console.log("✅ All region updates completed:", results);
          } catch (regionError) {
            console.error("❌ Region update failed:", regionError);
            throw new Error(`Failed to update regions: ${regionError.response?.data?.detail || regionError.message}`);
          }
        } else {
          console.log("ℹ️ No region changes to save");
        }
      }
      
      await loadConfig();
      
      setMessage({
        type: "success",
        text: "บันทึกการตั้งค่าสำเร็จ",
      });
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage({
        type: "error",
        text: err.response?.data?.detail || "เกิดข้อผิดพลาดในการบันทึก",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setEditedConfig(JSON.parse(JSON.stringify(config)));
    setEditedRegionMapping(JSON.parse(JSON.stringify(regionMapping)));
    setMessage(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">กำลังโหลด...</p>
        </div>
      </div>
    );
  }

  const isAdmin = employee?.role && 
    typeof employee.role === "string" && 
    employee.role.toLowerCase() === "admin";

  if (!isAdmin) {
    return null;
  }

  const builtInRoles = ["Sales", "Sales_Project", "ZM", "RM", "SDM", "PM", "CEO", "Admin"];

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">⚙️ การตั้งค่าระบบ</h1>
          <p className="text-gray-600 mt-2">จัดการสิทธิ์การเข้าถึงตาม Role</p>
        </div>
      </div>

      {/* Message Alert */}
      {message && (
        <div
          className={`max-w-7xl mx-auto mt-4 px-4 py-3 rounded-lg ${
            message.type === "success"
              ? "bg-green-100 text-green-800"
              : "bg-red-100 text-red-800"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow">
          {/* Tab Navigation */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab("price")}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === "price"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              💰 ระดับราคาอนุมัติ
            </button>
            <button
              onClick={() => setActiveTab("access")}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === "access"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              🔐 สิทธิ์การเข้าถึง
            </button>
            <button
              onClick={() => setActiveTab("regions")}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === "regions"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              🗺️ จัดการภาค
            </button>
            <button
              onClick={() => setActiveTab("system")}
              className={`px-6 py-4 font-medium transition-colors ${
                activeTab === "system"
                  ? "text-blue-600 border-b-2 border-blue-600"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              ⚙️ การตั้งค่าระบบ
            </button>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {/* Price Approval Tab */}
            {activeTab === "price" && (
              <div>

          {/* Price Approval Levels Configuration */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">ขอบเขตการอนุมัติราคาตาม Role</h3>
            <p className="text-sm text-gray-600 mb-6">
              กำหนดขอบเขตการอนุมัติราคาสำหรับแต่ละ Role โดยใช้ระดับราคา (Price Levels)
            </p>

            {/* Approval Logic Reference */}
            <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-semibold text-blue-900 mb-2">📋 ลำดับการอนุมัติ</h4>
              <div className="text-xs text-gray-700 space-y-1">
                <p>• <strong>ราคา ≥ R1</strong>: ไม่ต้องขออนุมัติ</p>
                <p>• <strong>R1 &gt; ราคา ≥ W2</strong>: ZM_ONLY (อนุมัติจาก ZM เท่านั้น)</p>
                <p>• <strong>W2 &gt; ราคา ≥ W1</strong>: ZM_THEN_RM (ต้องผ่าน ZM → RM)</p>
                <p>• <strong>W1 &gt; ราคา ≥ SDM</strong>: SDM_APPROVAL (ต้องผ่าน ZM → RM → SDM)</p>
                <p>• <strong>ราคา &lt; SDM</strong>: PM_APPROVAL (ต้องผ่าน ZM → RM → SDM → PM)</p>
              </div>
            </div>
            
            <div className="space-y-4">
              {/* Sales */}
              <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                <div className="mb-4">
                  <h4 className="font-semibold text-gray-900">Sales</h4>
                  <p className="text-xs text-gray-500">ผู้ขายทั่วไป - ไม่ต้องขออนุมัติ</p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm text-gray-600">อนุมัติราคา:</span>
                  <select
                    value={editedConfig?.price_config?.role_approval_scope?.Sales?.min_level || "R1"}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        price_config: {
                          ...editedConfig.price_config,
                          role_approval_scope: {
                            ...editedConfig.price_config?.role_approval_scope,
                            Sales: {
                              ...editedConfig.price_config?.role_approval_scope?.Sales,
                              min_level: e.target.value,
                            },
                          },
                        },
                      })
                    }
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                  >
                    <option value="R1">R1</option>
                    <option value="W2">W2</option>
                    <option value="W1">W1</option>
                    <option value="SDM">SDM</option>
                  </select>
                  <span className="text-sm text-gray-600">ขึ้นไป</span>
                </div>
              </div>

              {/* ZM */}
              <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                <div className="mb-4">
                  <h4 className="font-semibold text-gray-900">ZM (Zone Manager)</h4>
                  <p className="text-xs text-gray-500">ผู้จัดการเขต</p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm text-gray-600">อนุมัติราคา:</span>
                  <select
                    value={editedConfig?.price_config?.role_approval_scope?.ZM?.min_level || "R1"}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        price_config: {
                          ...editedConfig.price_config,
                          role_approval_scope: {
                            ...editedConfig.price_config?.role_approval_scope,
                            ZM: {
                              ...editedConfig.price_config?.role_approval_scope?.ZM,
                              min_level: e.target.value,
                            },
                          },
                        },
                      })
                    }
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                  >
                    <option value="R2">R2</option>
                    <option value="R1">R1</option>
                    <option value="W2">W2</option>
                    <option value="W1">W1</option>
                    <option value="SDM">SDM</option>
                  </select>
                  <span className="text-sm text-gray-600">ถึง</span>
                  <select
                    value={editedConfig?.price_config?.role_approval_scope?.ZM?.max_level || "W2"}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        price_config: {
                          ...editedConfig.price_config,
                          role_approval_scope: {
                            ...editedConfig.price_config?.role_approval_scope,
                            ZM: {
                              ...editedConfig.price_config?.role_approval_scope?.ZM,
                              max_level: e.target.value,
                            },
                          },
                        },
                      })
                    }
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                  >
                    <option value="R2">R2</option>
                    <option value="R1">R1</option>
                    <option value="W2">W2</option>
                    <option value="W1">W1</option>
                    <option value="SDM">SDM</option>
                  </select>
                </div>
              </div>

              {/* RM */}
              <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                <div className="mb-4">
                  <h4 className="font-semibold text-gray-900">RM (Regional Manager)</h4>
                  <p className="text-xs text-gray-500">ผู้จัดการภูมิภาค</p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm text-gray-600">อนุมัติราคา:</span>
                  <select
                    value={editedConfig?.price_config?.role_approval_scope?.RM?.min_level || "W2"}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        price_config: {
                          ...editedConfig.price_config,
                          role_approval_scope: {
                            ...editedConfig.price_config?.role_approval_scope,
                            RM: {
                              ...editedConfig.price_config?.role_approval_scope?.RM,
                              min_level: e.target.value,
                            },
                          },
                        },
                      })
                    }
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                  >
                    <option value="R2">R2</option>
                    <option value="R1">R1</option>
                    <option value="W2">W2</option>
                    <option value="W1">W1</option>
                    <option value="SDM">SDM</option>
                  </select>
                  <span className="text-sm text-gray-600">ถึง</span>
                  <select
                    value={editedConfig?.price_config?.role_approval_scope?.RM?.max_level || "W1"}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        price_config: {
                          ...editedConfig.price_config,
                          role_approval_scope: {
                            ...editedConfig.price_config?.role_approval_scope,
                            RM: {
                              ...editedConfig.price_config?.role_approval_scope?.RM,
                              max_level: e.target.value,
                            },
                          },
                        },
                      })
                    }
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                  >
                    <option value="R2">R2</option>
                    <option value="R1">R1</option>
                    <option value="W2">W2</option>
                    <option value="W1">W1</option>
                    <option value="SDM">SDM</option>
                  </select>
                </div>
              </div>

              {/* SDM */}
              <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                <div className="mb-4">
                  <h4 className="font-semibold text-gray-900">SDM (Sales Director Manager)</h4>
                  <p className="text-xs text-gray-500">ผู้บริหารฝ่ายขาย</p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm text-gray-600">อนุมัติราคา:</span>
                  <select
                    value={editedConfig?.price_config?.role_approval_scope?.SDM?.min_level || "W1"}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        price_config: {
                          ...editedConfig.price_config,
                          role_approval_scope: {
                            ...editedConfig.price_config?.role_approval_scope,
                            SDM: {
                              ...editedConfig.price_config?.role_approval_scope?.SDM,
                              min_level: e.target.value,
                            },
                          },
                        },
                      })
                    }
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                  >
                    <option value="R2">R2</option>
                    <option value="R1">R1</option>
                    <option value="W2">W2</option>
                    <option value="W1">W1</option>
                    <option value="SDM">SDM</option>
                  </select>
                  <span className="text-sm text-gray-600">ถึง</span>
                  <select
                    value={editedConfig?.price_config?.role_approval_scope?.SDM?.max_level || "SDM"}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        price_config: {
                          ...editedConfig.price_config,
                          role_approval_scope: {
                            ...editedConfig.price_config?.role_approval_scope,
                            SDM: {
                              ...editedConfig.price_config?.role_approval_scope?.SDM,
                              max_level: e.target.value,
                            },
                          },
                        },
                      })
                    }
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                  >
                    <option value="R2">R2</option>
                    <option value="R1">R1</option>
                    <option value="W2">W2</option>
                    <option value="W1">W1</option>
                    <option value="SDM">SDM</option>
                  </select>
                </div>
              </div>

              {/* PM */}
              <div className="border border-gray-300 rounded-lg p-4 bg-blue-50 ">
                <div className="mb-4">
                  <h4 className="font-semibold text-gray-900">PM (Product Manager)</h4>
                  <p className="text-xs text-gray-500">ผู้จัดการสินค้า - อนุมัติราคาต่ำสุด</p>
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-sm text-gray-600">อนุมัติราคา:</span>
                  <select
                    value={editedConfig?.price_config?.role_approval_scope?.PM?.min_level || "SDM"}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        price_config: {
                          ...editedConfig.price_config,
                          role_approval_scope: {
                            ...editedConfig.price_config?.role_approval_scope,
                            PM: {
                              ...editedConfig.price_config?.role_approval_scope?.PM,
                              min_level: e.target.value,
                            },
                          },
                        },
                      })
                    }
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                  >
                    <option value="R2">R2</option>
                    <option value="R1">R1</option>
                    <option value="W2">W2</option>
                    <option value="W1">W1</option>
                    <option value="SDM">SDM</option>
                  </select>
                  <span className="text-sm text-gray-600">ลงมา</span>
                </div>
              </div>
            </div>
          </div>

              </div>
            )}

            {/* Access Control Tab */}
            {activeTab === "access" && (
              <div>
                {/* Role Management Section */}
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h3 className="font-semibold text-blue-900 mb-3">➕ เพิ่ม Role ใหม่</h3>
                  <p className="text-xs text-gray-600 mb-3">
                    💡 Role หลักถูกสร้างที่เว็บ UX แล้ว ที่นี่เพียงเพิ่ม Role เข้ามาเพื่อกำหนดสิทธิ์การเข้าถึงหน้าต่างๆ
                  </p>
                  
                  <div className="flex gap-3 items-end">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        ชื่อ Role (ตรงกับที่สร้างในเว็บ UX)
                      </label>
                      <input
                        type="text"
                        placeholder="เช่น Sales_Manager, Marketing_Head"
                        value={newRoleName}
                        onChange={(e) => setNewRoleName(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleAddRole()}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <button
                      onClick={handleAddRole}
                      className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium whitespace-nowrap"
                    >
                      ➕ เพิ่ม
                    </button>
                  </div>
                </div>

                {/* Current Roles Display */}
                <div className="mb-6">
                  <h3 className="font-semibold text-gray-900 mb-2">Role ที่มีในระบบ ({availableRoles.length})</h3>
                  <div className="flex flex-wrap gap-2">
                    {availableRoles.map((role) => {
                      const isBuiltIn = builtInRoles.includes(role);
                      return (
                        <div
                          key={role}
                          className={`inline-flex items-center gap-2 px-3 py-1 rounded-md text-sm font-medium ${
                            isBuiltIn
                              ? "bg-gray-200 text-gray-700"
                              : "bg-green-100 text-green-800"
                          }`}
                        >
                          <span>{role}</span>
                          {!isBuiltIn && (
                            <button
                              onClick={() => handleDeleteRole(role)}
                              className="text-red-600 hover:text-red-800 font-bold text-base leading-none"
                              title="ลบ Role"
                            >
                              ×
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    สีเทา = Role ในระบบ | สีเขียว = Role ที่เพิ่มเอง (คลิก × เพื่อลบ)
                  </p>
                </div>

                <hr className="my-6 border-gray-300" />
                <h3 className="text-lg font-semibold text-gray-900 mb-4">กำหนดสิทธิ์การเข้าถึงหน้าต่างๆ</h3>
                <p className="text-sm text-gray-600 mb-4">
                  เลือก Role ที่สามารถเข้าถึงแต่ละหน้าได้
                </p>

                <div className="space-y-4">
                  {/* สร้างใบเสนอราคา */}
                  <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                    <div className="mb-3">
                      <h4 className="font-medium text-gray-900">📝 สร้างใบเสนอราคา</h4>
                      <p className="text-xs text-gray-500">Create Quote</p>
                    </div>
                    
                    <div className="flex flex-wrap gap-3">
                      {availableRoles.map((role) => (
                        <label key={role} className="inline-flex items-center px-3 py-2 bg-white border border-gray-200 rounded-md hover:bg-gray-50 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={editedConfig?.access_control?.page_access?.create_quote?.allowed_roles?.includes(role) || false}
                            onChange={(e) => {
                              const currentRoles = editedConfig?.access_control?.page_access?.create_quote?.allowed_roles || [];
                              const newAllowedRoles = e.target.checked
                                ? [...currentRoles, role]
                                : currentRoles.filter(r => r !== role);
                              
                              setEditedConfig({
                                ...editedConfig,
                                access_control: {
                                  ...editedConfig.access_control,
                                  page_access: {
                                    ...editedConfig.access_control?.page_access,
                                    create_quote: {
                                      page_name: "create_quote",
                                      page_label: "สร้างใบเสนอราคา",
                                      allowed_roles: newAllowedRoles,
                                    },
                                  },
                                },
                              });
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="ml-2 text-sm font-medium text-gray-700">{role}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* สร้างรหัสโครงการ */}
                  <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                    <div className="mb-3">
                      <h4 className="font-medium text-gray-900">🏗️ สร้างรหัสโครงการ</h4>
                      <p className="text-xs text-gray-500">Project Price Management</p>
                    </div>
                    
                    <div className="flex flex-wrap gap-3">
                      {availableRoles.map((role) => (
                        <label key={role} className="inline-flex items-center px-3 py-2 bg-white border border-gray-200 rounded-md hover:bg-gray-50 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={editedConfig?.access_control?.page_access?.project_price?.allowed_roles?.includes(role) || false}
                            onChange={(e) => {
                              const currentRoles = editedConfig?.access_control?.page_access?.project_price?.allowed_roles || [];
                              const newAllowedRoles = e.target.checked
                                ? [...currentRoles, role]
                                : currentRoles.filter(r => r !== role);
                              
                              setEditedConfig({
                                ...editedConfig,
                                access_control: {
                                  ...editedConfig.access_control,
                                  page_access: {
                                    ...editedConfig.access_control?.page_access,
                                    project_price: {
                                      page_name: "project_price",
                                      page_label: "สร้างรหัสโครงการ",
                                      allowed_roles: newAllowedRoles,
                                    },
                                  },
                                },
                              });
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="ml-2 text-sm font-medium text-gray-700">{role}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* หน้าอนุมัติราคา */}
                  <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                    <div className="mb-3">
                      <h4 className="font-medium text-gray-900">✅ หน้าอนุมัติราคา</h4>
                      <p className="text-xs text-gray-500">Special Price Approval</p>
                    </div>
                    
                    <div className="flex flex-wrap gap-3">
                      {availableRoles.map((role) => (
                        <label key={role} className="inline-flex items-center px-3 py-2 bg-white border border-gray-200 rounded-md hover:bg-gray-50 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={editedConfig?.access_control?.page_access?.special_price_approval?.allowed_roles?.includes(role) || false}
                            onChange={(e) => {
                              const currentRoles = editedConfig?.access_control?.page_access?.special_price_approval?.allowed_roles || [];
                              const newAllowedRoles = e.target.checked
                                ? [...currentRoles, role]
                                : currentRoles.filter(r => r !== role);
                              
                              setEditedConfig({
                                ...editedConfig,
                                access_control: {
                                  ...editedConfig.access_control,
                                  page_access: {
                                    ...editedConfig.access_control?.page_access,
                                    special_price_approval: {
                                      page_name: "special_price_approval",
                                      page_label: "หน้าอนุมัติราคา",
                                      allowed_roles: newAllowedRoles,
                                    },
                                  },
                                },
                              });
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="ml-2 text-sm font-medium text-gray-700">{role}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* เพิ่มราคา */}
                  <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                    <div className="mb-3">
                      <h4 className="font-medium text-gray-900">💰 เพิ่มราคา</h4>
                      <p className="text-xs text-gray-500">Update Price</p>
                    </div>
                    
                    <div className="flex flex-wrap gap-3">
                      {availableRoles.map((role) => (
                        <label key={role} className="inline-flex items-center px-3 py-2 bg-white border border-gray-200 rounded-md hover:bg-gray-50 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={editedConfig?.access_control?.page_access?.update_price?.allowed_roles?.includes(role) || false}
                            onChange={(e) => {
                              const currentRoles = editedConfig?.access_control?.page_access?.update_price?.allowed_roles || [];
                              const newAllowedRoles = e.target.checked
                                ? [...currentRoles, role]
                                : currentRoles.filter(r => r !== role);
                              
                              setEditedConfig({
                                ...editedConfig,
                                access_control: {
                                  ...editedConfig.access_control,
                                  page_access: {
                                    ...editedConfig.access_control?.page_access,
                                    update_price: {
                                      page_name: "update_price",
                                      page_label: "เพิ่มราคา",
                                      allowed_roles: newAllowedRoles,
                                    },
                                  },
                                },
                              });
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="ml-2 text-sm font-medium text-gray-700">{role}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Region Management Tab */}
            {activeTab === "regions" && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">🗺️ จัดการผู้ดูแลภาค (Regional Manager)</h3>
                <p className="text-sm text-gray-600 mb-6">
                  กำหนดรหัสพนักงานที่เป็น Regional Manager (RM) ของแต่ละภาค
                </p>

                {editedRegionMapping && editedRegionMapping.regions ? (
                  <div className="space-y-4">
                    {Object.entries(editedRegionMapping.regions).map(([regionCode, regionData]) => (
                      <div key={regionCode} className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                        <div className="flex items-start justify-between mb-4">
                          <div>
                            <h4 className="font-semibold text-gray-900 text-lg">
                              {regionData.region_name_thai} ({regionData.region_name})
                            </h4>
                            <p className="text-xs text-gray-500 mt-1">
                              รหัสภาค: {regionCode}
                            </p>
                            <p className="text-xs text-gray-500">
                              สาขาในภาค: {regionData.branches.join(", ")}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-3">
                          <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
                            รหัสพนักงาน RM:
                          </label>
                          <input
                            type="text"
                            value={regionData.rm_employee_id || ""}
                            onChange={(e) => {
                              const newValue = e.target.value;
                              setEditedRegionMapping({
                                ...editedRegionMapping,
                                regions: {
                                  ...editedRegionMapping.regions,
                                  [regionCode]: {
                                    ...regionData,
                                    rm_employee_id: newValue,
                                  },
                                },
                              });
                            }}
                            placeholder="เช่น 10027"
                            className="flex-1 max-w-xs px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                          />
                        </div>

                        {regionMapping && 
                         regionMapping.regions[regionCode]?.rm_employee_id !== regionData.rm_employee_id && (
                          <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                            ⚠️ มีการเปลี่ยนแปลง: {regionMapping.regions[regionCode]?.rm_employee_id} → {regionData.rm_employee_id}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <p>ไม่พบข้อมูลการจัดการภาค</p>
                  </div>
                )}

                <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <h4 className="font-semibold text-blue-900 mb-2">💡 คำแนะนำ</h4>
                  <ul className="text-xs text-gray-700 space-y-1 list-disc list-inside">
                    <li>กรอกรหัสพนักงานที่เป็น Regional Manager ของแต่ละภาค</li>
                    <li>ระบบจะใช้ข้อมูลนี้ในการกำหนดสิทธิ์การอนุมัติและการเข้าถึงข้อมูล</li>
                    <li>หากมีการเปลี่ยนตัว RM ให้แก้ไขรหัสพนักงานที่นี่</li>
                    <li>อย่าลืมกดปุ่ม "บันทึก" ด้านล่างเพื่อบันทึกการเปลี่ยนแปลง</li>
                  </ul>
                </div>
              </div>
            )}

            {/* System Settings Tab */}
            {activeTab === "system" && (
              <div>
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">⚙️ การตั้งค่าระบบ</h3>
                  <p className="text-sm text-gray-600 mb-6">
                    ตั้งค่าพารามิเตอร์ระบบต่างๆ เช่น อัตราภาษี เขตเวลา ภาษา รูปแบบ Project Code
                  </p>

                  {/* Project Code Mode */}
                  <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 mb-4">
                    <div className="mb-4">
                      <h4 className="font-semibold text-gray-900">🔢 รูปแบบ Project Code</h4>
                      <p className="text-xs text-gray-500">เลือกวิธีการสร้าง Project Code</p>
                    </div>
                    <div className="space-y-3">
                      <label className="flex items-start gap-3 cursor-pointer">
                        <input
                          type="radio"
                          name="project_code_mode"
                          value="auto"
                          checked={editedConfig?.system_config?.project_code_mode !== "manual"}
                          onChange={(e) =>
                            setEditedConfig({
                              ...editedConfig,
                              system_config: {
                                ...editedConfig.system_config,
                                project_code_mode: "auto",
                              },
                            })
                          }
                          className="mt-1 text-blue-600 focus:ring-blue-500"
                        />
                        <div>
                          <div className="font-medium text-gray-900">Running Number (อัตโนมัติ)</div>
                          <div className="text-xs text-gray-500">
                            ระบบจะสร้างเลขที่อัตโนมัติ เช่น PJ6704001, TR6704002
                          </div>
                        </div>
                      </label>
                      <label className="flex items-start gap-3 cursor-pointer">
                        <input
                          type="radio"
                          name="project_code_mode"
                          value="manual"
                          checked={editedConfig?.system_config?.project_code_mode === "manual"}
                          onChange={(e) =>
                            setEditedConfig({
                              ...editedConfig,
                              system_config: {
                                ...editedConfig.system_config,
                                project_code_mode: "manual",
                              },
                            })
                          }
                          className="mt-1 text-blue-600 focus:ring-blue-500"
                        />
                        <div>
                          <div className="font-medium text-gray-900">กรอกเอง (Manual)</div>
                          <div className="text-xs text-gray-500">
                            ผู้ใช้สามารถกรอก Project Code เองได้
                          </div>
                        </div>
                      </label>
                    </div>
                  </div>

                  {/* VAT Rate */}
                  <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 mb-4">
                    <div className="mb-4">
                      <h4 className="font-semibold text-gray-900">💵 อัตราภาษีมูลค่าเพิ่ม (VAT)</h4>
                      <p className="text-xs text-gray-500">ใช้ในการคำนวณภาษีของใบเสนอราคา</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        max="1"
                        value={editedConfig?.system_config?.vat_rate || 0.07}
                        onChange={(e) =>
                          setEditedConfig({
                            ...editedConfig,
                            system_config: {
                              ...editedConfig.system_config,
                              vat_rate: parseFloat(e.target.value) || 0.07,
                            },
                          })
                        }
                        className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium w-32"
                      />
                      <span className="text-sm text-gray-600">
                        ({((editedConfig?.system_config?.vat_rate || 0.07) * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      ตัวอย่าง: 0.07 = 7%, 0.10 = 10%
                    </p>
                  </div>

                  {/* File Storage Settings */}
                  <div className="border-t border-gray-300 pt-6 mt-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">📁 การจัดเก็บไฟล์</h3>
                    <p className="text-sm text-gray-600 mb-6">
                      กำหนดตำแหน่งโฟลเดอร์สำหรับเก็บไฟล์ต่างๆ ในระบบ
                    </p>

                    {/* Project Files Folder */}
                    <div className="border border-gray-300 rounded-lg p-4 bg-gray-50 mb-4">
                      <div className="mb-4">
                        <h4 className="font-semibold text-gray-900">📂 โฟลเดอร์ไฟล์โครงการ</h4>
                        <p className="text-xs text-gray-500">ที่เก็บไฟล์แนบของโครงการ (Project Files)</p>
                      </div>
                      <input
                        type="text"
                        value={editedConfig?.system_config?.project_files_folder || "./uploads/project_files"}
                        onChange={(e) =>
                          setEditedConfig({
                            ...editedConfig,
                            system_config: {
                              ...editedConfig.system_config,
                              project_files_folder: e.target.value,
                            },
                          })
                        }
                        placeholder="เช่น ./uploads/project_files หรือ C:/data/projects"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      />
                      <p className="text-xs text-gray-500 mt-2">
                        💡 ใช้ path แบบ relative (./) หรือ absolute (C:/) ก็ได้
                      </p>
                    </div>

                    {/* Product Images Folder */}
                    <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                      <div className="mb-4">
                        <h4 className="font-semibold text-gray-900">🖼️ โฟลเดอร์รูปภาพสินค้า</h4>
                        <p className="text-xs text-gray-500">ที่เก็บรูปภาพของสินค้า (Product Images)</p>
                      </div>
                      <input
                        type="text"
                        value={editedConfig?.system_config?.product_images_folder || "./uploads/product_images"}
                        onChange={(e) =>
                          setEditedConfig({
                            ...editedConfig,
                            system_config: {
                              ...editedConfig.system_config,
                              product_images_folder: e.target.value,
                            },
                          })
                        }
                        placeholder="เช่น ./uploads/product_images หรือ C:/data/images"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                      />
                      <p className="text-xs text-gray-500 mt-2">
                        💡 ใช้ path แบบ relative (./) หรือ absolute (C:/) ก็ได้
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4 mt-6">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
          >
            {saving ? "กำลังบันทึก..." : "💾 บันทึก"}
          </button>
          <button
            onClick={handleReset}
            disabled={saving}
            className="px-6 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 disabled:bg-gray-200 transition-colors font-medium"
          >
            ยกเลิก
          </button>
        </div>
      </div>
    </div>
  );
}

export default AdminConfig;
