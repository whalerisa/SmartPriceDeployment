import React, { useState, useEffect } from "react";
import api from "../services/api";
import { useNavigate } from "react-router-dom";

export default function ConfirmedQuotesPage() {
  const navigate = useNavigate();
  const [quotes, setQuotes] = useState([]);
  const [search, setSearch] = useState("");
  const [filterDate, setFilterDate] = useState("");
  const [filterMonth, setFilterMonth] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const itemsPerPage = 20; // แสดง 20 รายการต่อหน้า

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api.get("/api/quotation?status=complete");
      setQuotes(res.data || []);
      setCurrentPage(1); // รีเซ็ตไปหน้าแรก
    } catch (err) {
      console.error("Error loading confirmed quotations:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const fmtDate = (d) =>
    new Date(d).toLocaleDateString("th-TH", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });

  const filtered = quotes.filter((q) => {
    const matchSearch =
      q.number?.toLowerCase().includes(search.toLowerCase()) ||
      q.customer?.name?.toLowerCase().includes(search.toLowerCase()) ||
      q.customer?.phone?.includes(search);

    const matchDate = filterDate ? q.createdAt?.slice(0, 10) === filterDate : true;

    const matchMonth = filterMonth ? q.createdAt?.slice(0, 7) === filterMonth : true;

    return matchSearch && matchDate && matchMonth;
  });

  // ⭐ คำนวณ pagination
  const totalPages = Math.ceil(filtered.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedQuotes = filtered.slice(startIndex, endIndex);

  // ⭐ ฟังก์ชันเปลี่ยนหน้า
  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">ใบเสนอราคาที่ยืนยันแล้ว</h1>

      {/* ฟิลเตอร์ */}
      <div className="bg-white p-5 rounded-xl shadow-md mb-6">
        <div className="grid grid-cols-3 gap-4">
          {/* ค้นหา */}
          <div>
            <label className="text-gray-700 font-medium">ค้นหา</label>
            <input
              className="mt-1 w-full rounded-lg border px-4 py-2"
              placeholder="เลขที่ใบเสนอราคา / ชื่อลูกค้า / เบอร์โทร"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setCurrentPage(1); // รีเซ็ตไปหน้าแรก
              }}
            />
          </div>

          {/* ฟิลเตอร์ตามวันที่ */}
          <div>
            <label className="text-gray-700 font-medium">ค้นหาตามวันที่ยืนยัน</label>
            <input
              type="date"
              className="mt-1 w-full rounded-lg border px-4 py-2"
              value={filterDate}
              onChange={(e) => {
                setFilterDate(e.target.value);
                setFilterMonth(""); // clear month filter
                setCurrentPage(1); // รีเซ็ตไปหน้าแรก
              }}
            />
          </div>

          {/* ฟิลเตอร์ตามเดือน */}
          <div>
            <label className="text-gray-700 font-medium">ค้นหาตามเดือน</label>
            <input
              type="month"
              className="mt-1 w-full rounded-lg border px-4 py-2"
              value={filterMonth}
              onChange={(e) => {
                setFilterMonth(e.target.value);
                setFilterDate(""); // clear date filter
                setCurrentPage(1); // รีเซ็ตไปหน้าแรก
              }}
            />
          </div>
        </div>
      </div>

      {/* ข้อมูลสรุป */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
        <p className="text-sm text-gray-700">
          แสดง <span className="font-bold">{startIndex + 1}</span> ถึง{" "}
          <span className="font-bold">{Math.min(endIndex, filtered.length)}</span> จาก{" "}
          <span className="font-bold">{filtered.length}</span> รายการ
        </p>
      </div>

      {/* ตาราง */}
      <div className="bg-white rounded-xl shadow-md p-4 mb-6">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-100">
            <tr>
              {[
                "เลขที่ใบเสนอราคา",
                "รหัสลูกค้า",
                "ชื่อลูกค้า",
                "พนักงานขาย",
                "วันยืนยัน",
                "มูลค่า (บาท)",
                "จัดการ",
              ].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-bold uppercase text-gray-600"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-100">
            {paginatedQuotes.length === 0 && (
              <tr>
                <td colSpan="7" className="text-center py-6 text-gray-500">
                  {loading ? "กำลังโหลด..." : "ไม่พบข้อมูลใบเสนอราคาที่ค้นหา"}
                </td>
              </tr>
            )}

            {paginatedQuotes.map((q) => (
              <tr key={q.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-blue-600 font-medium">{q.quoteNo}</td>
                <td className="px-4 py-3">{q.customer?.id}</td>
                <td className="px-4 py-3">{q.customer?.name}</td>
                <td className="px-4 py-3">{q.employee?.name}</td>
                <td className="px-4 py-3">{fmtDate(q.createdAt)}</td>
                <td className="px-4 py-3 text-green-600 font-semibold">
                  ฿ {Number(q.totals?.grandTotal || 0).toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <button
                    className="px-4 py-1.5 rounded-lg bg-blue-600 text-white text-sm shadow hover:bg-blue-700"
                    onClick={() => navigate(`/order/${encodeURIComponent(q.quoteNo)}`)}
                  >
                    ดูรายละเอียด
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ⭐ Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between bg-white rounded-xl shadow-md p-4">
          <button
            onClick={handlePreviousPage}
            disabled={currentPage === 1}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              currentPage === 1
                ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            ← ก่อนหน้า
          </button>

          {/* Page Numbers */}
          <div className="flex gap-2">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                onClick={() => handlePageChange(page)}
                className={`px-3 py-2 rounded-lg font-medium transition-colors ${
                  currentPage === page
                    ? "bg-blue-600 text-white"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
              >
                {page}
              </button>
            ))}
          </div>

          <button
            onClick={handleNextPage}
            disabled={currentPage === totalPages}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              currentPage === totalPages
                ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            ถัดไป →
          </button>
        </div>
      )}
    </div>
  );
}
