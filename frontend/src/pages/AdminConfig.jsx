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

  const handleSave = async () => {
    try {
      setSaving(true);
      await api.put("/api/config/settings", editedConfig);
      
      // โหลดข้อมูล config ใหม่จาก server เพื่อให้แน่ใจว่าข้อมูลตรงกัน
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

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">⚙️ การตั้งค่าระบบ</h1>
          <p className="text-gray-600 mt-2">จัดการการตั้งค่าและการเชื่อมต่อ API</p>
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
        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-gray-200">
          {[
            { id: "price", label: "💰 ราคา", icon: "💰" },
            { id: "access", label: "🔐 สิทธิ์การเข้าถึง", icon: "🔐" },
            { id: "system", label: "⚙️ ระบบ", icon: "⚙️" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-lg shadow">
          {/* API Tab */}
          {activeTab === "api" && (
            <div className="p-6">
              <h2 className="text-xl font-bold mb-6">สถานะการเชื่อมต่อ API</h2>

              {/* API Status Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Array.isArray(apiStatus) && apiStatus.map((api) => (
                  <div
                    key={api.api_name}
                    className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">
                          {api.api_name}
                        </h3>
                        <p className="text-sm text-gray-600 mt-1 break-all">
                          {api.url}
                        </p>
                      </div>
                      <div
                        className={`px-3 py-1 rounded-full text-sm font-medium whitespace-nowrap ml-2 ${
                          api.status === "connected"
                            ? "bg-green-100 text-green-800"
                            : "bg-red-100 text-red-800"
                        }`}
                      >
                        {api.status === "connected" ? "✓ เชื่อมต่อ" : "✗ ไม่เชื่อมต่อ"}
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">{api.message}</p>
                  </div>
                ))}
                {(!Array.isArray(apiStatus) || apiStatus.length === 0) && (
                  <div className="col-span-2 text-center text-gray-500 py-8">
                    ไม่มีข้อมูลสถานะ API
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Price Tab */}
          {activeTab === "price" && (
            <div className="p-6">
              <h2 className="text-xl font-bold mb-6">ขอบเขตการอนุมัติราคาตาม Role</h2>
              <p className="text-sm text-gray-600 mb-6">
                กำหนดขอบเขตการอนุมัติราคาสำหรับแต่ละ Role โดยใช้ระดับราคา (Price Levels)
              </p>

              <div className="space-y-4">
                {/* Sales Role */}
                <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center gap-4">
                    <label className="w-32 font-medium text-gray-700">Sales:</label>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.Sales?.min_level || "R2"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              Sales: {
                                ...editedConfig.price_config.role_approval_scope?.Sales,
                                min_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                    <span className="text-gray-600">&gt;= ราคา &gt;=</span>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.Sales?.max_level || "R2"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              Sales: {
                                ...editedConfig.price_config.role_approval_scope?.Sales,
                                max_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                  </div>
                </div>

                {/* ZM Role */}
                <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center gap-4">
                    <label className="w-32 font-medium text-gray-700">ZM:</label>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.ZM?.min_level || "R1"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              ZM: {
                                ...editedConfig.price_config.role_approval_scope?.ZM,
                                min_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                    <span className="text-gray-600">&gt;= ราคา &gt;=</span>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.ZM?.max_level || "W2"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              ZM: {
                                ...editedConfig.price_config.role_approval_scope?.ZM,
                                max_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                  </div>
                </div>

                {/* RM Role */}
                <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center gap-4">
                    <label className="w-32 font-medium text-gray-700">RM:</label>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.RM?.min_level || "W2"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              RM: {
                                ...editedConfig.price_config.role_approval_scope?.RM,
                                min_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                    <span className="text-gray-600">&gt;= ราคา &gt;=</span>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.RM?.max_level || "W1"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              RM: {
                                ...editedConfig.price_config.role_approval_scope?.RM,
                                max_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                  </div>
                </div>

                {/* SDM Role */}
                <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center gap-4">
                    <label className="w-32 font-medium text-gray-700">SDM:</label>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.SDM?.min_level || "W1"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              SDM: {
                                ...editedConfig.price_config.role_approval_scope?.SDM,
                                min_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                    <span className="text-gray-600">&gt;= ราคา &gt;=</span>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.SDM?.max_level || "SDM"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              SDM: {
                                ...editedConfig.price_config.role_approval_scope?.SDM,
                                max_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                  </div>
                </div>

                {/* PM Role */}
                <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center gap-4">
                    <label className="w-32 font-medium text-gray-700">PM:</label>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.PM?.min_level || "R2"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              PM: {
                                ...editedConfig.price_config.role_approval_scope?.PM,
                                min_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                    <span className="text-gray-600">&gt;= ราคา &gt;=</span>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.PM?.max_level || "SDM"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              PM: {
                                ...editedConfig.price_config.role_approval_scope?.PM,
                                max_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                  </div>
                </div>

                {/* CEO Role */}
                <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center gap-4">
                    <label className="w-32 font-medium text-gray-700">CEO:</label>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.CEO?.min_level || "R2"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              CEO: {
                                ...editedConfig.price_config.role_approval_scope?.CEO,
                                min_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                    <span className="text-gray-600">&gt;= ราคา &gt;=</span>
                    <select
                      value={editedConfig?.price_config?.role_approval_scope?.CEO?.max_level || "SDM"}
                      onChange={(e) =>
                        setEditedConfig({
                          ...editedConfig,
                          price_config: {
                            ...editedConfig.price_config,
                            role_approval_scope: {
                              ...editedConfig.price_config.role_approval_scope,
                              CEO: {
                                ...editedConfig.price_config.role_approval_scope?.CEO,
                                max_level: e.target.value,
                              },
                            },
                          },
                        })
                      }
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="R2">R2</option>
                      <option value="R1">R1</option>
                      <option value="W2">W2</option>
                      <option value="W1">W1</option>
                      <option value="SDM">SDM</option>
                    </select>
                  </div>
                </div>

                {/* Info Box */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-6">
                  <h3 className="font-semibold text-blue-900 mb-2">
                    📋 คำอธิบายระดับราคา
                  </h3>
                  <p className="text-sm text-blue-800">
                    ลำดับระดับราคา (จากสูงไปต่ำ): <strong>R2 &gt; R1 &gt; W2 &gt; W1 &gt; SDM</strong>
                  </p>
                  <p className="text-sm text-blue-800 mt-2">
                    ตัวอย่าง: ZM: R1 &gt;= ราคา &gt;= W2 หมายความว่า ZM มีสิทธิ์อนุมัติราคาที่อยู่ระหว่าง R1 (สูง) ถึง W2 (ต่ำ)
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Access Control Tab */}
          {activeTab === "access" && (
            <div className="p-6">
              <h2 className="text-xl font-bold mb-6">🔐 สิทธิ์การเข้าถึงหน้าตาม Role</h2>
              <p className="text-sm text-gray-600 mb-6">
                กำหนดว่า Role ไหนสามารถเข้าถึงหน้าไหนได้บ้าง
              </p>

              <div className="space-y-4">
                {/* สร้างใบเสนอราคา */}
                <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                  <div className="mb-3">
                    <h4 className="font-medium text-gray-900">📝 สร้างใบเสนอราคา</h4>
                    <p className="text-xs text-gray-500">Create Quote</p>
                  </div>
                  
                  <div className="flex flex-wrap gap-3">
                    {["Sales", "Sales_Project", "ZM", "RM", "SDM", "PM", "CEO", "Admin"].map((role) => (
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
                    {["Sales", "Sales_Project", "ZM", "RM", "SDM", "PM", "CEO", "Admin"].map((role) => (
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
                    {["Sales", "Sales_Project", "ZM", "RM", "SDM", "PM", "CEO", "Admin"].map((role) => (
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
                    {["Sales", "Sales_Project", "ZM", "RM", "SDM", "PM", "CEO", "Admin"].map((role) => (
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

          {/* System Tab */}
          {activeTab === "system" && (
            <div className="p-6">
              <h2 className="text-xl font-bold mb-6">ข้อมูลระบบ</h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Base URL
                  </label>
                  <input
                    type="text"
                    value={editedConfig?.system_config?.base_url || ""}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        system_config: {
                          ...editedConfig.system_config,
                          base_url: e.target.value,
                        },
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Timezone
                  </label>
                  <select
                    value={editedConfig?.system_config?.timezone || "Asia/Bangkok"}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        system_config: {
                          ...editedConfig.system_config,
                          timezone: e.target.value,
                        },
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="Asia/Bangkok">Asia/Bangkok (ไทย)</option>
                    <option value="UTC">UTC</option>
                    <option value="Asia/Singapore">Asia/Singapore</option>
                    <option value="Asia/Tokyo">Asia/Tokyo</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    ภาษา
                  </label>
                  <select
                    value={editedConfig?.system_config?.language || "th"}
                    onChange={(e) =>
                      setEditedConfig({
                        ...editedConfig,
                        system_config: {
                          ...editedConfig.system_config,
                          language: e.target.value,
                        },
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="th">ไทย</option>
                    <option value="en">English</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Version
                  </label>
                  <input
                    type="text"
                    value={editedConfig?.system_config?.version || ""}
                    disabled
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-600"
                  />
                </div>
              </div>
            </div>
          )}
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
