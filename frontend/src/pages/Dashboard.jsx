// src/pages/Dashboard.jsx (REFACTORED for Navbar component)
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.js";
import { useQuote } from "../hooks/useQuote.js";
import api from "../services/api";

// --- คอมโพเนนต์หลัก ---
function Dashboard() {
  const { employee } = useAuth();
  const { dispatch } = useQuote();
  const navigate = useNavigate();
  const [currentDate, setCurrentDate] = useState("");
  
  const isAdmin = employee?.role && typeof employee.role === "string" && 
    (employee.role.toLowerCase() === "admin" || employee.role.toLowerCase() === "superadmin");

  // โหลดวันที่ปัจจุบัน (ภาษาไทย)
  useEffect(() => {
    const date = new Date();
    const options = {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
      timeZone: "Asia/Bangkok",
    };
    const thaiDate = date.toLocaleDateString("th-TH", options);
    // เพิ่ม "พ.ศ."
    const year = date
      .toLocaleDateString("th-TH", { year: "numeric", timeZone: "Asia/Bangkok" })
      .split(" ")[0];
    setCurrentDate(thaiDate.replace(year, ` พ.ศ. ${year}`));
  }, []);

  const handleCreateQuote = () => {
    dispatch({ type: "RESET_QUOTE" });
    navigate("/create");
  };

  const handlePendingQuotes = () => {
    navigate("/quote-drafts");
  };

  const handleTodayQuotes = () => {
    navigate("/confirmed-quotes");
  };

  const handleAdminConfig = () => {
    navigate("/admin-config");
  };

  const [todayCount, setTodayCount] = useState(0);
  const [pendingCount, setPendingCount] = useState(0);
  const [contactCustomerCount, setContactCustomerCount] = useState(0);
  const [pendingApprovalCount, setPendingApprovalCount] = useState(0);
  const [specialPriceAvailable, setSpecialPriceAvailable] = useState(false);
  
  // ⭐ สิทธิ์การเข้าถึงหน้าต่างๆ จาก API
  const [pageAccess, setPageAccess] = useState({
    create_quote: true, // default allow for all
    project_price: false,
    special_price_approval: false,
    update_price: false,
  });

  useEffect(() => {
    async function loadDashboardData() {
      try {
        // ⭐ โหลดทุกอย่างพร้อมกันใน Promise.all เดียว
        const today = new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Bangkok" });

        const [resAccess, resStats, resPendingApprovals] = await Promise.all([
          // 1. สิทธิ์การเข้าถึง
          api.get("/api/config/page-access/user-pages").catch(() => ({ data: { accessible_pages: [] } })),
          // 2. สถิติ Dashboard (endpoint ใหม่ที่ดึงแค่ตัวเลข)
          api.get("/api/quotation/dashboard-stats").catch(() => ({ data: null })),
          // 3. รอการอนุมัติราคาพิเศษ
          api.get("/api/special-price-requests/pending/approvals").catch(() => ({ data: [] })),
        ]);

        // ตั้งค่าสิทธิ์
        const accessiblePages = resAccess.data?.accessible_pages || [];
        setPageAccess({
          create_quote: accessiblePages.includes("create_quote"),
          project_price: accessiblePages.includes("project_price"),
          special_price_approval: accessiblePages.includes("special_price_approval"),
          update_price: accessiblePages.includes("update_price"),
        });

        // ตั้งค่าสถิติ
        if (resStats.data) {
          setTodayCount(resStats.data.today_count || 0);
          setPendingCount(resStats.data.pending_count || 0);
          setContactCustomerCount(resStats.data.contact_customer_count || 0);
        }

        // ตั้งค่าการอนุมัติราคาพิเศษ
        const approvals = resStats.data?.pending_approval_count ?? (resPendingApprovals.data || []).length;
        setPendingApprovalCount(approvals);
        setSpecialPriceAvailable(true);

      } catch (err) {
        console.error("Dashboard load error:", err);
      }
    }

    loadDashboardData();
  }, []);

  // ⭐ Reload page access เมื่อกลับมาที่หน้า Dashboard
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // โหลดสิทธิ์ใหม่เมื่อกลับมาที่หน้า
        api.get("/api/config/page-access/user-pages")
          .then(res => {
            const accessiblePages = res.data?.accessible_pages || [];
            console.log("🔄 Reloaded page access:", accessiblePages);
            setPageAccess({
              create_quote: accessiblePages.includes("create_quote"),
              project_price: accessiblePages.includes("project_price"),
              special_price_approval: accessiblePages.includes("special_price_approval"),
              update_price: accessiblePages.includes("update_price"),
            });
          })
          .catch(err => console.error("Failed to reload page access:", err));
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  return (
    <div className="min-h-screen w-full bg-[#F5F5F5]">
      {/* ===== 2. Main Content (เนื้อหาหลัก) ===== */}
      <main className="mx-auto max-w-7xl p-6 lg:p-10">
        {/* --- 2.1 Welcome Banner (ป้ายต้อนรับสีน้ำเงิน) --- */}
        <div className="flex flex-col md:flex-row justify-between items-center rounded-[30px] bg-[#0084FF] p-8 text-white shadow-lg">
          <div className="space-y-2">
            <p className="font-bold">{currentDate}</p>
            <h1 className="text-4xl md:text-6xl font-bold">สวัสดี, {employee?.name || "..."}</h1>
            <p className="font-bold text-white/70">พนักงานรหัส: {employee?.id || "..."}</p>
            <p className="text-sm text-white/70">
              ยินดีต้อนรับเข้าสู่ระบบจัดการใบเสนอราคา ระบบพร้อมให้บริการแล้ว
            </p>
          </div>
          <div className="mt-6 md:mt-0 md:ml-8">
            <img src="/assets/waving-hand.png" alt="Checklist" className="w-20 h-20 mr-10" />
          </div>
        </div>

        {/* --- 2.2 Stats Cards (การ์ดสถิติ 3 ใบ) --- */}
        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {/* Card 1: ใบเสนอราคาวันนี้ */}
          <div
            className="rounded-[30px] bg-white p-8 shadow-lg cursor-pointer hover:bg-gray-100"
            onClick={handleTodayQuotes}
          >
            <div className="flex justify-between items-start">
              {/* Icon */}
              <div className="rounded-xl bg-[#0084FF] p-3 shadow-md">
                <img
                  src="/assets/document-text-svgrepo-com.svg"
                  alt="Document Icon"
                  className="w-8 h-8"
                />
              </div>
              {/* Text */}
              <div className="text-right">
                <p className="text-xl font-bold text-gray-400">ใบเสนอราคาวันนี้</p>
                <p className="text-6xl font-bold text-black">{todayCount}</p>
                <span className="text-sm font-bold text-gray-400">รายการทั้งหมด</span>
              </div>
            </div>
          </div>

          {/* Card 2: ลูกค้าที่ติดต่อ */}
          <div 
            className="rounded-[30px] p-8 shadow-lg bg-white cursor-pointer hover:bg-gray-100"
            onClick={() => navigate("/customers-today")}
          >
            <div className="flex justify-between items-start ">
              {/* Icon */}
              <div className="rounded-xl bg-[#05A628] p-3 shadow-md">
                <img src="/assets/people-icon.svg" alt="People Icon" className="w-8 h-8" />
              </div>
              {/* Text */}
              <div className="text-right">
                <p className="text-xl font-bold text-gray-400">ลูกค้าที่ติดต่อ</p>
                <p className="text-6xl font-bold text-black">{contactCustomerCount}</p>
                <span className="text-sm font-bold text-gray-400">รายการทั้งหมด</span>
              </div>
            </div>
          </div>

          {/* Card 3: รอดำเนินการ */}
          <div
            className="rounded-[30px] bg-white p-8 shadow-lg cursor-pointer hover:bg-gray-100 "
            onClick={handlePendingQuotes}
          >
            <div className="flex justify-between items-start">
              {/* Icon */}
              <div className="rounded-xl bg-[#EF833F] p-3 shadow-md">
                <img src="/assets/time-svgrepo-com.svg" alt="Time Icon" className="w-8 h-8 " />
              </div>
              {/* Text */}
              <div className="text-right ">
                <p className="text-xl font-bold text-gray-400 ">รอดำเนินการ</p>
                <p className="text-6xl font-bold text-black">{pendingCount}</p>
                <span className="text-sm font-bold text-gray-400 ">รายการทั้งหมด</span>
              </div>
            </div>
          </div>

        </div>
        <div className="mt-6 ">

          {/* Admin Config Card - แสดงเฉพาะ admin */}
          {isAdmin && (
            <div
              className="group relative cursor-pointer overflow-hidden rounded-[33px] bg-gray-700 hover:bg-gray-800 p-8 text-white shadow-lg mb-6"
              onClick={handleAdminConfig}
            >
              <img src="/assets/settings.png" className="w-16 h-16 mb-4" />
              <h2 className="text-4xl font-bold">การตั้งค่าระบบ</h2>
              <p className="mt-2 text-lg text-white/70">จัดการการตั้งค่าระบบ</p>
            </div>
          )}

          {/* Special Price Approval Card - แสดงตามสิทธิ์จาก API */}
          {pageAccess.special_price_approval && specialPriceAvailable && (
            <div
              className="group relative cursor-pointer overflow-hidden rounded-[33px] bg-[#9333EA] hover:bg-[#7e22ce] p-8 text-white shadow-lg"
              onClick={() => navigate("/special-price-approval")}
            >
              <img src="/assets/approve.png" className="w-16 h-16 mb-4" />
              <h2 className="text-4xl font-bold">อนุมัติราคาพิเศษ</h2>
              <p className="mt-2 text-lg text-white/70">
                มี {pendingApprovalCount} รายการรอการอนุมัติ
              </p>
            </div>
          )}

          {/* Update Price Card - แสดงตามสิทธิ์จาก API */}
          {pageAccess.update_price && (
            <div
              className="group relative cursor-pointer overflow-hidden  rounded-[33px] bg-[#0f766e] hover:bg-[#0f6d65] p-8 text-white shadow-lg mt-6"
              onClick={() => navigate("/update-price")}
            >
              <img src="/assets/refresh.png" className="w-16 h-16 mb-4" />
              <h2 className="text-4xl font-bold">เพิ่ม / อัปเดตราคา / จัดการโปรโมชั่น</h2>
              <p className="mt-2 text-lg text-white/70">สำหรับผู้จัดการ</p>
            </div>
          )}

          {/* Project Price Card - แสดงตามสิทธิ์จาก API */}
          {pageAccess.project_price && (
            <div
              className="group relative cursor-pointer overflow-hidden  rounded-[33px] bg-[#dd8901] hover:bg-[#cd7905] p-8 text-white shadow-lg mt-6"
              onClick={() => navigate("/project-price")}
            >
              <img src="/assets/project.png" className="w-16 h-16 mb-4" />
              <h2 className="text-4xl font-bold">สร้างรหัสโครงการ/บันทึกราคาโครงการ</h2>
              <p className="mt-2 text-lg text-white/70">จัดการโครงการ</p>
            </div>
          )}
        </div>

    
        {/* --- 2.3 Action Cards (การ์ดทำงาน 2 ใบ) --- */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Action 1: สร้างใบเสนอราคา (สีแดง) - แสดงตามสิทธิ์ */}
          {pageAccess.create_quote && (
            <div
              className="group relative cursor-pointer overflow-hidden rounded-[33px] bg-red-600/[.85] p-8 text-white shadow-lg transition-all hover:shadow-xl"
              onClick={handleCreateQuote}
            >
              <img src="/assets/plus.png" alt="Arrow" className="w-16 h-16 mb-4 ml-1" />
              <h2 className="text-4xl font-bold">สร้างใบเสนอราคา</h2>
              <p className="mt-2 text-lg text-white/70">เริ่มสร้างใบเสนอราคาใหม่</p>
              <div className="mt-6 flex items-center text-lg font-bold text-white/70 transition-all group-hover:translate-x-1">
                <span>เริ่มต้นเลย</span>
                <img src="/assets/right-arrow.png" alt="Arrow" className="w-5 h-5 ml-1" />
              </div>
            </div>
          )}

          {/* Action 2: ค้นหาข้อมูลลูกค้า (สีน้ำเงิน) */}
          <div 
            className="group relative cursor-pointer overflow-hidden rounded-[33px] bg-[#0084FF] p-8 text-white shadow-lg transition-all hover:shadow-xl"
            onClick={() => navigate("/customer-search")}
          >
            <img src="/assets/magnifier.png" alt="Arrow" className="w-16 h-16 mb-4 ml-1" />
            <h2 className="text-4xl font-bold">ค้นหาข้อมูลลูกค้า</h2>
            <p className="mt-2 text-lg text-white/70">ตรวจสอบข้อมูลลูกค้าและประวัติการซื้อ</p>
            <div className="mt-6 flex items-center text-lg font-bold text-white/70 transition-all group-hover:translate-x-1">
              <span>เริ่มต้นเลย</span>
              <img src="/assets/right-arrow.png" alt="Arrow" className="w-5 h-5 ml-1" />
            </div>
          </div>
        </div>

      </main>
    </div>
  );
}

export default Dashboard;
