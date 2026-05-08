# ภาพรวมโครงการ Smart Pricing & Quotation System

## 📋 ข้อมูลโครงการ

**ชื่อโครงการ:** Smart Pricing & Quotation System  
**ประเภท:** ระบบจัดการใบเสนอราคาและการคำนวณราคาอัจฉริยะ  
**เทคโนโลยี:** FastAPI (Backend) + React (Frontend) + MSSQL Database  
**การ Deploy:** Docker Compose

---

## 🎯 วัตถุประสงค์

ระบบนี้พัฒนาขึ้นเพื่อ:

1. **จัดการใบเสนอราคา** - สร้าง แก้ไข และติดตามสถานะใบเสนอราคา
2. **คำนวณราคาอัจฉริยะ** - คำนวณราคาตามระดับลูกค้า ประวัติการซื้อ และเงื่อนไขต่างๆ
3. **จัดการลูกค้า** - ติดตามข้อมูลลูกค้า ประวัติการซื้อ และวิเคราะห์พฤติกรรม
4. **จัดการสินค้า** - อัพเดทราคา จัดการรูปภาพสินค้า และราคาโครงการ
5. **ระบบอนุมัติ** - อนุมัติราคาพิเศษและส่วนลดพิเศษ
6. **รายงานและสถิติ** - วิเคราะห์ยอดขาย กำไร และประสิทธิภาพการขาย

---

## 🏗️ สถาปัตยกรรมระบบ

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  - Vite + React 19 + TailwindCSS                            │
│  - Pages: Dashboard, CreateQuote, UpdatePrice, etc.         │
│  - Components: Wizard, Modals, Forms                         │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST API
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  - Python 3.x + FastAPI + Uvicorn                           │
│  - Routers: 25+ API endpoints                               │
│  - Services: Pricing, Cache, Upload                         │
│  - Jobs: Background tasks (cache refresh)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ SQL Queries
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Database (MSSQL)                           │
│  - Quote_Header, Quote_Line                                 │
│  - Item_Master, Item_Price                                  │
│  - Customer_Master, Special_Price_Requests                  │
│  - Project_Price_Header, Project_Price_Line                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  External Services                           │
│  - Employee API (Authentication)                            │
│  - Customer API (Customer Data)                             │
│  - Item API (Product Master Data)                           │
│  - RPA Agent (Chrome automation for BC integration)         │
└─────────────────────────────────────────────────────────────┘
```

---

## 👥 ผู้ใช้งานระบบ

### 1. **พนักงานขาย (Sales)**
   - สร้างใบเสนอราคา
   - ค้นหาลูกค้าและสินค้า
   - ดูประวัติการซื้อของลูกค้า
   - ขอราคาพิเศษ

### 2. **พนักงานขายโครงการ (Sales_Project)**
   - สร้างใบเสนอราคาโครงการ
   - ใช้ราคาโครงการพิเศษ
   - จัดการไฟล์โครงการ

### 3. **ผู้จัดการสาขา (ZM - Zone Manager)**
   - อนุมัติราคาพิเศษระดับสาขา
   - ดูรายงานยอดขายสาขา
   - จัดการพนักงานในสาขา

### 4. **ผู้จัดการภาค (RM - Regional Manager)**
   - อนุมัติราคาพิเศษระดับภาค
   - ดูรายงานยอดขายทุกสาขาในภาค
   - ติดตามประสิทธิภาพการขาย

### 5. **ผู้จัดการฝ่ายขาย (SDM - Sales Director Manager)**
   - อนุมัติราคาพิเศษระดับสูง
   - ดูรายงานยอดขายทั้งหมด
   - กำหนดนโยบายราคา

### 6. **ผู้จัดการผลิตภัณฑ์ (PM - Product Manager)**
   - อัพเดทราคาสินค้า
   - จัดการราคาโครงการ
   - อนุมัติราคาพิเศษตามหมวดสินค้า

### 7. **กรรมการผู้จัดการ (CEO)**
   - ดูรายงานระดับผู้บริหาร
   - อนุมัติราคาพิเศษทุกระดับ
   - ติดตามกำไรและประสิทธิภาพ

### 8. **ผู้ดูแลระบบ (Admin/SuperAdmin)**
   - จัดการสิทธิ์ผู้ใช้
   - ตั้งค่าระบบ
   - จัดการข้อมูลพื้นฐาน

---

## 📦 โครงสร้างโปรเจค

```
smart-pricing/
├── backend/                    # Backend (FastAPI)
│   ├── main.py                # Entry point
│   ├── *_router.py            # API routers (25+ files)
│   ├── api/                   # External API clients
│   │   ├── bc_client.py       # Business Central client
│   │   ├── bc_item_client.py  # Item API client
│   │   └── bc_branch_client.py # Branch API client
│   ├── config/                # Configuration
│   │   ├── db_mssql.py        # MSSQL connection
│   │   ├── db_sqlite.py       # SQLite (backup)
│   │   └── config_external_api.py # API configs
│   ├── services/              # Business logic
│   │   ├── price_upload_service.py
│   │   ├── cross_sell_service.py
│   │   └── sku_enricher.py
│   ├── jobs/                  # Background jobs
│   │   ├── item_master_cache_refresh.py
│   │   └── customer_cache_refresh_standalone.py
│   ├── schemas/               # Pydantic models
│   ├── utils/                 # Utilities
│   ├── static/                # Static files
│   ├── logs/                  # Log files
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile            # Docker image
│
├── frontend/                  # Frontend (React)
│   ├── src/
│   │   ├── App.jsx           # Main app component
│   │   ├── main.jsx          # Entry point
│   │   ├── pages/            # Page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── UpdatePrice.jsx
│   │   │   ├── ProjectPrice.jsx
│   │   │   ├── SpecialPriceApproval.jsx
│   │   │   └── CreateQuote/  # Wizard pages
│   │   │       ├── CreateQuoteWizard.jsx
│   │   │       ├── Step1_CustomerInfo.jsx
│   │   │       ├── Step2_ProductSelection.jsx
│   │   │       ├── Step3_GlassCutting.jsx
│   │   │       ├── Step4_CrossSell.jsx
│   │   │       ├── Step5_Delivery.jsx
│   │   │       └── Step6_Summary.jsx
│   │   ├── components/       # Reusable components
│   │   │   ├── Navbar.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   ├── PageAccessRoute.jsx
│   │   │   ├── wizard/       # Wizard components
│   │   │   ├── quotes/       # Quote components
│   │   │   ├── products/     # Product components
│   │   │   └── updatePrice/  # Price update components
│   │   ├── context/          # React contexts
│   │   │   └── AuthContext.jsx
│   │   ├── services/         # API services
│   │   │   └── api.js
│   │   ├── hooks/            # Custom hooks
│   │   └── utils/            # Utilities
│   ├── public/               # Public assets
│   ├── package.json          # NPM dependencies
│   └── Dockerfile           # Docker image
│
├── rpa_agent/                # RPA automation
│   ├── rpa_agent.py          # Chrome automation
│   └── start_agent_and_chrome.bat
│
├── docker-compose.yml        # Docker orchestration
├── create_release.bat        # Build script
└── README.md                # Documentation
```

---

## 🔑 คุณสมบัติหลัก

### 1. **ระบบใบเสนอราคา (Quotation)**
- สร้างใบเสนอราคาใหม่ผ่าน Wizard 6 ขั้นตอน
- แก้ไขและอัพเดทใบเสนอราคา
- ซื้อซ้ำจากใบเสนอราคาเดิม (Reorder)
- ตรวจสอบวันหมดอายุและคำนวณราคาใหม่อัตโนมัติ
- รองรับ IBT (Inter-Branch Transfer)
- รองรับ Pre-Order

### 2. **ระบบคำนวณราคา (Pricing)**
- คำนวณราคาตามระดับลูกค้า (R2, R1, W2, W1, SDM)
- ราคาพิเศษตามประวัติการซื้อ
- ราคาโครงการ (Project Price)
- ราคาโปรโมชั่น
- ราคาพิเศษที่ขออนุมัติ (Special Price Request)
- คำนวณค่าขนส่งอัตโนมัติ
- คำนวณ VAT และส่วนลด

### 3. **ระบบจัดการสินค้า (Product Management)**
- อัพเดทราคาสินค้าจาก Excel
- จัดการรูปภาพสินค้า (Product Image Manager)
- จัดการราคาโครงการ
- ระบบ Cross-sell (แนะนำสินค้าเสริม)
- ตัดกระจกตามขนาด (Glass Cutting)

### 4. **ระบบจัดการลูกค้า (Customer Management)**
- ค้นหาลูกค้า
- ดูประวัติการซื้อ
- วิเคราะห์พฤติกรรมการซื้อ
- ติดตามลูกค้าที่เข้ามาแต่ละวัน
- จัดการเครดิตและเงื่อนไขการชำระเงิน

### 5. **ระบบอนุมัติ (Approval System)**
- อนุมัติราคาพิเศษตามสิทธิ์
- ระบบ workflow อนุมัติหลายระดับ
- ติดตามสถานะการอนุมัติ
- ประวัติการอนุมัติ

### 6. **ระบบรายงาน (Reporting)**
- Dashboard สรุปยอดขาย
- รายงานกำไร
- รายงานประสิทธิภาพพนักงาน
- สถิติการขายตามสาขา/ภาค
- Export ข้อมูลเป็น Excel

---

## 🔐 ระบบ Authentication & Authorization

### Authentication
- **JWT Token** - ใช้ JWT token เก็บใน HttpOnly Cookie
- **UXP Integration** - รองรับ login ผ่าน UXP Portal
- **Manual Login** - รองรับ login แบบ manual สำหรับ testing
- **Multi-Branch Support** - รองรับพนักงานที่มีหลายสาขา

### Authorization
- **Role-Based Access Control (RBAC)** - ควบคุมสิทธิ์ตาม role
- **Page Access Control** - จำกัดการเข้าถึงหน้าต่างๆ
- **Branch-Based Filtering** - กรองข้อมูลตามสาขา
- **Region-Based Access** - RM เห็นข้อมูลทุกสาขาในภาค
- **Approval Scope** - กำหนดขอบเขตการอนุมัติตาม role

---

## 🗄️ ฐานข้อมูล

### หลักการออกแบบ
- **MSSQL** - ฐานข้อมูลหลัก (production)
- **SQLite** - ฐานข้อมูลสำรอง (development/backup)
- **Normalized Design** - ออกแบบตาม normalization principles
- **Indexed Columns** - สร้าง index สำหรับ performance

### ตารางหลัก
1. **Quote_Header** - ข้อมูลหัวใบเสนอราคา
2. **Quote_Line** - รายการสินค้าในใบเสนอราคา
3. **Item_Master** - ข้อมูลสินค้า
4. **Item_Price** - ราคาสินค้าแต่ละสาขา
5. **Customer_Master** - ข้อมูลลูกค้า
6. **Special_Price_Requests** - คำขอราคาพิเศษ
7. **Project_Price_Header** - ข้อมูลโครงการ
8. **Project_Price_Line** - ราคาสินค้าในโครงการ
9. **Promotions** - โปรโมชั่น
10. **Product_Images** - รูปภาพสินค้า

---

## 🚀 การติดตั้งและ Deploy

### Development
```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

### Production (Docker)
```bash
# Build และ run ด้วย Docker Compose
docker-compose up -d

# ระบบจะรันที่:
# - Backend: http://localhost:8000
# - Frontend: http://localhost:3200
```

---

## 📊 Performance & Optimization

### Caching
- **Item Master Cache** - cache ข้อมูลสินค้าเพื่อลด API calls
- **Customer Cache** - cache ข้อมูลลูกค้า
- **Price Cache** - cache การคำนวณราคา

### Background Jobs
- **Item Master Sync** - sync ข้อมูลสินค้าจาก external API
- **Customer Sync** - sync ข้อมูลลูกค้า
- **Price Upload** - อัพเดทราคาจาก Excel แบบ batch

### Database Optimization
- **Connection Pooling** - ใช้ connection pool
- **Query Optimization** - optimize SQL queries
- **Indexing** - สร้าง index ตามความจำเป็น

---

## 🔧 Configuration

### Environment Variables
```bash
# Database
MSSQL_SERVER=your-server
MSSQL_DATABASE=your-database
MSSQL_USERNAME=your-username
MSSQL_PASSWORD=your-password

# External APIs
CUSTOMER_API_KEY=your-api-key
ITEM_API_URL=your-api-url
ITEM_API_KEY=your-api-key
EMP_API_URL=your-employee-api-url

# JWT
JWT_SECRET=your-secret-key

# VAT
VAT_RATE=0.07

# Manual Login
MANUAL_LOGIN_PASSWORD=your-password
```

---

## 📝 License & Credits

**Developed by:** Tung Ngern Kij Co., Ltd.  
**Version:** 1.0.0  
**Last Updated:** 2026
