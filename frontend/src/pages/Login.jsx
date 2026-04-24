// src/pages/Login.jsx
import { useState, useEffect } from "react";
import api from "../services/api";

function Login() {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [loginMode, setLoginMode] = useState("uxp"); // "uxp", "manual", หรือ "selectBranch"
  const [formData, setFormData] = useState({
    employeeCode: "",
    role: "",
    branchId: "",
    password: "",
    branches: [],
    selectedBranch: "",
  });
  const [roles, setRoles] = useState([]);
  const [branches, setBranches] = useState([]);

  // ดึงข้อมูล roles และ branches เมื่อเปลี่ยนเป็น manual mode
  useEffect(() => {
    if (loginMode === "manual") {
      fetchRolesAndBranches();
    }
  }, [loginMode]);

  const fetchRolesAndBranches = async () => {
    try {
      const [rolesRes, branchesRes] = await Promise.all([
        api.get("/api/login/roles"),
        api.get("/api/login/branches"),
      ]);
      setRoles(rolesRes.data.roles || []);
      setBranches(branchesRes.data.branches || []);
    } catch (err) {
      console.error("Error fetching roles/branches:", err);
    }
  };

  const handleStartUsing = async () => {
    setError("");
    setLoading(true);

    try {
      // เรียก Backend ให้อ่าน UXP cookie และสร้าง auth_token
      const response = await api.post("/api/login/init");
      console.log("Login response:", response.data);

      // ถ้าพนักงานมีหลายสาขา ให้เลือกสาขา
      if (response.data.employee?.branches && response.data.employee.branches.length > 1) {
        setFormData(prev => ({
          ...prev,
          employeeCode: response.data.employee.id,
          branches: response.data.employee.branches,
          selectedBranch: response.data.employee.branchId,
        }));
        setLoginMode("selectBranch");
        setLoading(false);
        return;
      }

      // ถ้ามีเพียงสาขาเดียว ให้เข้าสู่ระบบเลย
      window.location.href = "/dashboard";
    } catch (err) {
      console.error("Login error:", err);
      setError(err.response?.data?.detail || "ไม่สามารถเข้าสู่ระบบได้ - กรุณา login ผ่าน UXP Portal ก่อน");
      setLoading(false);
    }
  };

  const handleManualLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    // Validate
    if (!formData.employeeCode || !formData.role || !formData.branchId || !formData.password) {
      setError("กรุณากรอกข้อมูลให้ครบถ้วน");
      setLoading(false);
      return;
    }

    try {
      const response = await api.post("/api/login/manual", formData);
      console.log("Manual login success:", response.data);

      // Reload หน้าเพื่อให้ AuthContext อ่าน cookie ใหม่
      window.location.href = "/dashboard";
    } catch (err) {
      console.error("Manual login error:", err);
      setError(err.response?.data?.detail || "ไม่สามารถเข้าสู่ระบบได้");
      setLoading(false);
    }
  };

  const handleSelectBranch = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    if (!formData.selectedBranch) {
      setError("กรุณาเลือกสาขา");
      setLoading(false);
      return;
    }

    try {
      // เรียก Backend เพื่อสร้าง auth_token ด้วยสาขาที่เลือก
      const response = await api.post("/api/login/select-branch", {
        employeeCode: formData.employeeCode,
        branchId: formData.selectedBranch,
      });
      console.log("Branch selection success:", response.data);

      // Reload หน้าเพื่อให้ AuthContext อ่าน cookie ใหม่
      window.location.href = "/dashboard";
    } catch (err) {
      console.error("Branch selection error:", err);
      setError(err.response?.data?.detail || "ไม่สามารถเลือกสาขาได้");
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100">
      <div className="w-full max-w-md rounded-3xl bg-white p-10 shadow-2xl">
        <div className="flex justify-center mb-8">
          <img src="/assets/favicon.png" alt="Smart Pricing Logo" className="h-32" />
        </div>

        <h1 className="mb-3 text-center text-4xl font-bold text-blue-600">
          Smart Pricing
        </h1>
        <p className="mb-8 text-center text-gray-600 font-semibold text-xl">
          ระบบจัดการใบเสนอราคา
        </p>

        {/* Toggle Login Mode */}
        <div className="mb-6 flex gap-2">
          <button
            onClick={() => setLoginMode("uxp")}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all ${
              loginMode === "uxp"
                ? "bg-blue-500 text-white shadow-md"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            UXP Login
          </button>
          {/* ปุ่ม Manual Login */}
       
            <button
              onClick={() => setLoginMode("manual")}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition-all ${
                loginMode === "manual"
                  ? "bg-blue-500 text-white shadow-md"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              Manual Login
            </button> 
  
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
            <p className="text-sm text-red-700 text-center">{error}</p>
          </div>
        )}

        {loginMode === "uxp" ? (
          // UXP Login Mode
          <>
            <button
              onClick={handleStartUsing}
              disabled={loading}
              className="w-full rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 py-4 font-bold text-white text-lg shadow-lg transition-all duration-300 hover:from-blue-600 hover:to-blue-700 hover:shadow-xl hover:scale-[1.02] focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  กำลังเข้าสู่ระบบ...
                </span>
              ) : (
                "เริ่มใช้งาน"
              )}
            </button>
            <p className="mt-8 text-center text-sm text-gray-500">
              กดปุ่มเริ่มใช้งานเพื่อเข้าสู่ระบบ
            </p>
          </>
        ) : loginMode === "selectBranch" ? (
          // Select Branch Mode
          <form onSubmit={handleSelectBranch} className="space-y-4">
            <div>
              <label htmlFor="selectedBranch" className="block text-sm font-medium text-gray-700 mb-2">
                เลือกสาขา
              </label>
              <select
                id="selectedBranch"
                value={formData.selectedBranch}
                onChange={(e) => setFormData(prev => ({ ...prev, selectedBranch: e.target.value }))}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                disabled={loading}
              >
                <option value="">เลือกสาขา</option>
                {formData.branches?.map((branch) => (
                  <option key={branch} value={branch}>
                    {branch}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 py-4 font-bold text-white text-lg shadow-lg transition-all duration-300 hover:from-blue-600 hover:to-blue-700 hover:shadow-xl hover:scale-[1.02] focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  กำลังเข้าสู่ระบบ...
                </span>
              ) : (
                "ยืนยัน"
              )}
            </button>

            <button
              type="button"
              onClick={() => {
                setLoginMode("uxp");
                setFormData(prev => ({ ...prev, branches: [], selectedBranch: "" }));
              }}
              className="w-full mt-2 py-2 px-4 text-gray-600 hover:text-gray-800 font-medium"
              disabled={loading}
            >
              ย้อนกลับ
            </button>
          </form>
        ) : (
          // Manual Login Mode
          <form onSubmit={handleManualLogin} className="space-y-4">
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                รหัสผ่าน
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                placeholder="กรอกรหัสผ่าน"
                disabled={loading}
              />
            </div>

            <div>
              <label htmlFor="employeeCode" className="block text-sm font-medium text-gray-700 mb-2">
                รหัสพนักงาน
              </label>
              <input
                type="text"
                id="employeeCode"
                name="employeeCode"
                value={formData.employeeCode}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                placeholder="กรอกรหัสพนักงาน"
                disabled={loading}
              />
            </div>

            <div>
              <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-2">
                Role
              </label>
              <select
                id="role"
                name="role"
                value={formData.role}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                disabled={loading}
              >
                <option value="">เลือก Role</option>
                {roles.map((role) => (
                  <option key={role.code} value={role.code}>
                    {role.thaiName} ({role.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="branchId" className="block text-sm font-medium text-gray-700 mb-2">
                สาขา
              </label>
              <select
                id="branchId"
                name="branchId"
                value={formData.branchId}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                disabled={loading}
              >
                <option value="">เลือกสาขา</option>
                {branches.map((branch) => (
                  <option key={branch.code} value={branch.code}>
                    {branch.displayName}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 py-4 font-bold text-white text-lg shadow-lg transition-all duration-300 hover:from-blue-600 hover:to-blue-700 hover:shadow-xl hover:scale-[1.02] focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:opacity-70 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              {loading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  กำลังเข้าสู่ระบบ...
                </span>
              ) : (
                "เข้าสู่ระบบ"
              )}
            </button>

            <p className="mt-4 text-center text-sm text-gray-500">
              กรอกข้อมูลเพื่อเข้าสู่ระบบ
            </p>
          </form>
        )}
      </div>
    </div>
  );
}

export default Login;