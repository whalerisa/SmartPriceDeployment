// src/components/PageAccessRoute.jsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useState, useEffect } from "react";
import api from "../services/api";
import Loader from "./Loader";

/**
 * PageAccessRoute - ตรวจสอบสิทธิ์การเข้าถึงหน้าเฉพาะ
 * 
 * @param {string} pageId - รหัสหน้าที่ต้องการตรวจสอบ (เช่น "create_quote", "project_price")
 * @param {string} redirectTo - เส้นทางที่จะ redirect ไปถ้าไม่มีสิทธิ์ (default: "/dashboard")
 */
const PageAccessRoute = ({ pageId, redirectTo = "/dashboard" }) => {
  const { employee, loading: authLoading } = useAuth();
  const [hasAccess, setHasAccess] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAccess = async () => {
      if (!employee) {
        setHasAccess(false);
        setLoading(false);
        return;
      }

      try {
        const response = await api.get("/api/config/page-access/user-pages");
        const accessiblePages = response.data?.accessible_pages || [];
        setHasAccess(accessiblePages.includes(pageId));
      } catch (error) {
        console.error("Failed to check page access:", error);
        setHasAccess(false);
      } finally {
        setLoading(false);
      }
    };

    if (!authLoading) {
      checkAccess();
    }
  }, [employee, authLoading, pageId]);

  // แสดงหน้า loading ขณะที่กำลังตรวจสอบ
  if (authLoading || loading) {
    return <Loader />;
  }

  // ถ้าไม่มีสิทธิ์ ให้ redirect ไปหน้าที่กำหนด
  if (!hasAccess) {
    return <Navigate to={redirectTo} replace />;
  }

  return <Outlet />;
};

export default PageAccessRoute;
