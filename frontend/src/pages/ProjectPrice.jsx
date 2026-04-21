import React, { useState, useEffect } from "react";
import { Building2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import api from "../services/api.js";
import ProjectPriceManagement from "./ProjectPriceManagement";

export default function ProjectPrice() {
  const { employee } = useAuth();
  const navigate = useNavigate();
  const [hasAccess, setHasAccess] = useState(false);
  const [loading, setLoading] = useState(true);

  // ⭐ ตรวจสอบสิทธิ์จาก API
  useEffect(() => {
    const checkAccess = async () => {
      try {
        const res = await api.get("/api/config/page-access/check/project_price");
        setHasAccess(res.data.has_access);
        console.log("🔐 Project Price access check:", res.data);
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

  // แสดง loading
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">กำลังตรวจสอบสิทธิ์...</div>
      </div>
    );
  }

  // ถ้าไม่มีสิทธิ์ ให้แสดงข้อความ
  if (employee && !hasAccess) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <h2 className="text-xl font-bold text-red-800 mb-2">ไม่มีสิทธิ์เข้าถึง</h2>
          <p className="text-red-600">ขออภัย คุณไม่มีสิทธิ์เข้าถึงหน้านี้</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <Building2 className="w-8 h-8 text-teal-600" />
        <h1 className="text-2xl font-bold">ราคาโครงการ</h1>
      </div>

      <ProjectPriceManagement />
    </div>
  );
}
