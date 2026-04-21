// src/App.jsx (แก้ไข)
import { Routes, Route, Outlet } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import CreateQuoteWizard from "./pages/CreateQuote/CreateQuoteWizard.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Navbar from "./components/Navbar.jsx";
import QuoteDraftListPage from "./pages/QuoteDraftListPage.jsx";
import ConfirmedQuotesPage from "./pages/ConfirmedQuotesPage";
import OrderDetailPage from "./pages/OrderDetailPage.jsx";
import UpdatePrice from "./pages/UpdatePrice";
import ProjectPrice from "./pages/ProjectPrice";
import CustomerPerDay from "./pages/CustomerPerDay.jsx";
import CustomerDetail from "./pages/CustomerDetail.jsx";
import CustomerSearch from "./pages/CustomerSearch.jsx";
import PromotionManagement from "./pages/PromotionManagement.jsx";
import SpecialPriceApproval from "./pages/SpecialPriceApproval.jsx";
import AdminConfig from "./pages/AdminConfig.jsx";
import Login from "./pages/Login.jsx";

// --- Layout 1 (สำหรับ Dashboard) ---
const DashboardLayout = () => (
  <div className="min-h-screen w-full bg-[#F5F5F5] text-gray-800">
    <Navbar />
    <Outlet />
  </div>
);

// --- Layout 2 (สำหรับ Wizard) ---
const WizardLayout = () => (
  <div className="min-h-screen w-full flex flex-col bg-gray-100 text-gray-800">
    <Navbar />
    <main className="flex-1 w-full p-4 flex flex-col">
      <div className="bg-white container mx-auto max-w-[1280px] flex-1 flex flex-col rounded-lg shadow-lg">
        <Outlet />
      </div>
    </main>
  </div>
);

// --- คอมโพเนนต์ App หลัก ---
function App() {
  return (
    <Routes>
      {/* Login route - ไม่ต้องผ่าน ProtectedRoute */}
      <Route path="/login" element={<Login />} />

      <Route element={<ProtectedRoute />}>
        {/* 2.1: Dashboard (ใช้ DashboardLayout) */}
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/admin-config" element={<AdminConfig />} />
          <Route path="/update-price" element={<UpdatePrice />} />
          <Route path="/project-price" element={<ProjectPrice />} />
          <Route path="/quote-drafts" element={<QuoteDraftListPage />} />
          <Route path="/confirmed-quotes" element={<ConfirmedQuotesPage />} />
          <Route path="/order/:id" element={<OrderDetailPage />} />
          <Route path="/customers-today" element={<CustomerPerDay />} />
          <Route path="/customer-search" element={<CustomerSearch />} />
          <Route path="/customer/:customerId" element={<CustomerDetail />} />
          <Route path="/promotions" element={<PromotionManagement />} />
          <Route path="/special-price-approval" element={<SpecialPriceApproval />} />
        </Route>

        {/* 2.2: CreateQuote (ใช้ WizardLayout) */}
        <Route element={<WizardLayout />}>
          <Route path="/create" element={<CreateQuoteWizard />} />
        </Route>
      </Route>
    </Routes>
   );
}

export default App;
