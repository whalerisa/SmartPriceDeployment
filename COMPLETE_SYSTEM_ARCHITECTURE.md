# COMPLETE SYSTEM ARCHITECTURE - Smart Pricing System

## 📊 SYSTEM OVERVIEW

Smart Pricing System is a comprehensive quotation and pricing management platform with:
- **Frontend**: React + Vite (TypeScript/JSX)
- **Backend**: FastAPI (Python)
- **Database**: MSSQL (with SQLite fallback)
- **External APIs**: Business Central, Employee API, Customer API, Invoice API
- **RPA**: Selenium-based automation for D365 BC Sales Quote creation
- **Deployment**: Docker Compose (Frontend + Backend)

---

## 🏗️ ARCHITECTURE LAYERS

### Layer 1: PRESENTATION LAYER (Frontend - React)
- User Interface (React Components)
- State Management (Context API)
- API Communication (Axios)
- Routing (React Router)

### Layer 2: API LAYER (Backend - FastAPI)
- REST API Endpoints
- Authentication & Authorization
- Business Logic
- Data Validation

### Layer 3: SERVICE LAYER (Backend)
- Pricing Engine
- Cache Management
- File Upload Service
- External API Integration

### Layer 4: DATA LAYER (Backend)
- MSSQL Database
- SQLite Fallback
- Cache Storage

### Layer 5: EXTERNAL INTEGRATIONS
- Business Central APIs
- Employee API
- Customer API
- Invoice API
- RPA Automation

---

## 🔌 INSTALLATION & SETUP

### Prerequisites
- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- MSSQL Server (or SQLite)
- Chrome Browser (for RPA)

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Docker Setup
```bash
docker-compose up -d
```

### Environment Configuration
- **backend/.env** - API keys, database config, external API URLs
- **frontend/.env** - API URL, SSO URLs

---

## 📁 BACKEND FILE STRUCTURE

### Core Application
- **main.py** - FastAPI app initialization, router registration, CORS, static files

### Authentication & Authorization
- **auth_dependency.py** - JWT token extraction, branch code extraction
- **login.py** - Login endpoints (UXP, manual, branch selection)
- **role_mapping.py** - Thai role to code mapping
- **branch_region_mapping.py** - Branch to region mapping
- **employee_position_mapper.py** - Employee position mapping

### API Routers (26 routers)
1. **quotation.py** - Quote CRUD, reorder, pre-order
2. **pricing_router.py** - Pricing calculation engine
3. **customer.py** - Customer data & search
4. **items.py** - Item master data
5. **employees.py** - Employee data
6. **shipping.py** - Shipping cost calculation
7. **products_router.py** - Product listing & filtering
8. **invoice_router.py** - Invoice management
9. **branch.py** - Branch information
10. **admin_router.py** - Admin configuration
11. **config_router.py** - System configuration
12. **cache_refresh_router.py** - Cache refresh triggers
13. **promotion_router.py** - Promotion management
14. **project_price_router.py** - Project pricing
15. **special_price_request_router.py** - Special price workflow
16. **print_router.py** - Quote printing/PDF
17. **product_image_router.py** - Product images
18. **project_files_router.py** - Project files
19. **statistics_router.py** - Analytics
20. **external_price_api_router.py** - External price API
21. **cross_sell_router.py** - Cross-sell recommendations
22. **credit_router.py** - Customer credit
23. **customer_analytics.py** - Customer analytics
24. **price_update.py** - Price updates
25. **chrome_debug_router.py** - Chrome debugging
26. **quotation_reorder.py** - Quote reorder logic

### Database Configuration
- **config/db_mssql.py** - MSSQL connection
- **config/db_sqlite.py** - SQLite connection
- **config/config_external_api.py** - External API config
- **config/cache_config.py** - Cache config

### Pricing Logic
- **LevelPrice.py** - Tier-based pricing (R1, R2, W1, W2, SDM)
- **price.py** - Price calculation with delivery type

### Services
- **services/price_upload_service.py** - Excel/CSV price upload
- **services/cross_sell_service.py** - Cross-sell logic
- **services/sku_enricher.py** - SKU enrichment

### External API Clients
- **api/bc_item_client.py** - Business Central Item API
- **api/bc_branch_client.py** - Business Central Branch API
- **api/router_sq.py** - Sales Quote routing

### Scheduled Jobs
- **jobs/item_master_cache_refresh.py** - Item cache refresh
- **jobs/customer_cache_refresh_standalone.py** - Customer cache
- **jobs/invoice_cache_refresh.py** - Invoice cache
- **jobs/scheduled_price_upload_standalone.py** - Price upload

### Airflow DAGs
- **dags/item_master_cache_refresh_dag.py**
- **dags/d365_cache_refresh_pipeline_dag.py**
- **dags/scheduled_price_upload_dag.py**

### Configuration Files
- **.env** - Environment variables
- **requirements.txt** - Python dependencies
- **custom_roles.json** - Role definitions
- **employees.json** - Employee data
- **Dockerfile** - Docker image

---

## 🎨 FRONTEND FILE STRUCTURE

### Entry Points
- **main.jsx** - React app initialization
- **App.jsx** - Main app component with routing
- **index.html** - HTML template

### Pages (Main Views)
- **Login.jsx** - Login page
- **Dashboard.jsx** - Dashboard
- **CreateQuote/** - Multi-step quote wizard
  - Step1_CustomerSearch.jsx
  - Step2_ProductSelection.jsx
  - Step3_PriceReview.jsx
  - Step4_Shipping.jsx
  - Step5_Summary.jsx
  - Step6_Summary.jsx
- **UpdatePrice.jsx** - Price update
- **ProjectPrice.jsx** - Project pricing
- **PromotionManagement.jsx** - Promotions
- **SpecialPriceApproval.jsx** - Special price approval
- **AdminConfig.jsx** - Admin config

### Components
- **wizard/** - Quote creation components
- **products/** - Product display components
- **updatePrice/** - Price update components
- **quotes/** - Quote display components
- **cross-sell/** - Cross-sell components
- **common/** - Reusable components

### Context & Services
- **context/AuthContext.jsx** - Authentication state
- **services/api.js** - API client (axios)

### Configuration Files
- **.env** - Environment variables
- **package.json** - Dependencies
- **vite.config.js** - Vite config
- **tailwind.config.js** - Tailwind config
- **Dockerfile** - Docker image
- **nginx.conf** - Nginx config

---

## 🤖 RPA AGENT

### Files
- **rpa_agent/rpa_agent.py** - Selenium automation for D365 BC
- **rpa_agent/start_agent_and_chrome.bat** - Chrome startup script

### Functionality
- Connects to Chrome via remote debugging (port 9222)
- Automates: Quote creation, series selection, customer entry
- Supports offline mode with bundled chromedriver.exe
- HTTP server for receiving automation requests

---

## 🔄 DATA FLOW & API CONNECTIONS

### 1. AUTHENTICATION FLOW
```
User Login (Frontend)
    ↓
Login.jsx → api.post("/login/init")
    ↓
login.py → load_employee() → Employee API
    ↓
Generate JWT Token
    ↓
Store in localStorage & cookies
    ↓
AuthContext updated
```

### 2. QUOTE CREATION FLOW
```
CreateQuote Pages (Frontend)
    ↓
Step1: Customer Search
    → api.get("/api/customer/search")
    → customer.py → MSSQL
    ↓
Step2: Product Selection
    → api.get("/api/items/categories/list")
    → api.get("/api/items/categories/{category}/list")
    → items.py → MSSQL
    ↓
Step3: Price Review
    → api.post("/api/pricing/calculate")
    → pricing_router.py → LevelPrice.py → price.py
    ↓
Step4: Shipping
    → api.post("/api/shipping/calculate")
    → shipping.py
    ↓
Step5-6: Summary & Save
    → api.post("/quotation")
    → quotation.py → MSSQL
```

### 3. PRICING CALCULATION FLOW
```
pricing_router.py → calculate_pricing()
    ↓
For each item:
    1. Get base price from Item_Master
    2. Apply customer tier (R1, R2, W1, W2)
    3. Check special price request
    4. Check project price
    5. Check history price
    6. Apply promotion
    7. Calculate tax
    ↓
Return: { items, totals, price_validations }
```

### 4. PRICE UPLOAD FLOW
```
UploadPriceExcel.jsx (Frontend)
    ↓
api.post("/api/price-update/upload")
    ↓
price_update.py
    ↓
price_upload_service.py
    ↓
Validate file format & columns
    ↓
For each row:
    - Validate SKU exists
    - Upsert to Item_Price table
    ↓
Return: { total_rows, successful, errors }
```

### 5. CACHE REFRESH FLOW
```
Scheduled Job (APScheduler)
    ↓
jobs/item_master_cache_refresh.py
    ↓
api/bc_item_client.py → Business Central API
    ↓
Fetch items & inventory
    ↓
Update MSSQL cache tables
    ↓
Log results
```

### 6. RPA AUTOMATION FLOW
```
Frontend: Create Quote
    ↓
api.post("/api/quotation/send-to-bc")
    ↓
quotation.py → RPA HTTP request
    ↓
rpa_agent.py → Selenium automation
    ↓
Connect to Chrome (port 9222)
    ↓
Automate D365 BC Sales Quote creation
    ↓
Return: Quote number
```

---

## 📊 API ENDPOINTS SUMMARY

### Authentication
- POST /login/init - Initialize login
- POST /login/select-branch - Select branch
- POST /login/manual - Manual login
- POST /login/logout - Logout

### Quotation
- GET /quotation - List quotes
- POST /quotation - Create quote
- GET /quotation/{id} - Get quote
- PUT /quotation/{id} - Update quote
- DELETE /quotation/{id} - Delete quote
- POST /quotation/{id}/send-to-bc - Send to BC

### Pricing
- POST /api/pricing/calculate - Calculate pricing
- GET /api/pricing/levels - Get pricing levels

### Customer
- GET /api/customer/search - Search customer
- GET /api/customer/{code} - Get customer
- GET /api/customer/analytics - Customer analytics

### Items
- GET /api/items/search - Search items
- GET /api/items/categories/list - List categories
- GET /api/items/categories/{category}/list - List items by category
- GET /api/items/{sku} - Get item detail
- GET /api/items/{sku}/stock - Get item stock

### Products
- GET /api/products - List products
- GET /api/products/{id} - Get product
- POST /api/products/filter - Filter products

### Shipping
- POST /api/shipping/calculate - Calculate shipping

### Price Update
- POST /api/price-update/upload - Upload prices
- GET /api/price-update/history - Price history

### Special Price Request
- POST /api/special-price-request - Create request
- GET /api/special-price-request - List requests
- PUT /api/special-price-request/{id}/approve - Approve
- PUT /api/special-price-request/{id}/reject - Reject

### Project Price
- GET /api/project-prices/by-customer - Get customer projects
- POST /api/project-prices - Create project price
- PUT /api/project-prices/{id} - Update project price

### Promotion
- GET /api/promotion - List promotions
- POST /api/promotion - Create promotion
- PUT /api/promotion/{id} - Update promotion

### Cross-Sell
- GET /api/cross-sell/rules - Get cross-sell rules

### Admin
- GET /api/admin/config - Get config
- PUT /api/admin/config - Update config

### Cache
- POST /api/cache/refresh - Refresh cache
- GET /api/cache/status - Cache status

### Print
- POST /api/print/quote - Print quote
- GET /api/print/quote/{id} - Get quote PDF

---

## 🗄️ DATABASE SCHEMA (MSSQL)

### Main Tables
- **Item_Master** - Product information
- **Item_Price** - Product pricing
- **Customer** - Customer data
- **Quote_Header** - Quote header
- **Quote_Line** - Quote line items
- **Special_Price_Request** - Special price requests
- **Project_Price** - Project pricing
- **Promotion** - Promotions
- **Employee** - Employee data
- **Branch** - Branch information
- **Region** - Region information

---

## 🔐 SECURITY & AUTHENTICATION

### JWT Token Structure
```json
{
  "sub": "employee_code",
  "employeeCode": "EMP001",
  "employeeName": "John Doe",
  "branchId": "00TR",
  "role": "Sales",
  "region": "Bangkok",
  "iat": 1234567890,
  "exp": 1234571490
}
```

### Authentication Flow
1. User logs in with employee code
2. Backend validates against Employee API
3. JWT token generated with employee info
4. Token stored in localStorage & cookies
5. Token sent in Authorization header for all requests
6. Backend validates token in auth_dependency.py

### Authorization
- Role-based access control (RBAC)
- Page access control via page_access_config.json
- API endpoint protection via Depends(get_branch_code)

---

## 🚀 DEPLOYMENT

### Docker Compose
```yaml
services:
  backend:
    build: ./backend
    ports: 8000:8000
    environment: MSSQL connection, API keys
  
  frontend:
    build: ./frontend
    ports: 3200:80
    depends_on: backend
```

### Environment Variables
- **backend/.env** - API keys, database URL, JWT secret
- **frontend/.env** - API URL, SSO URLs

### Build & Release
- create_release.bat - Release creation script
- Docker images pushed to registry

---

## 📈 KEY FEATURES

### 1. Multi-Tier Pricing
- R1, R2, W1, W2 pricing levels
- SDM special pricing
- Quantity-based discounts

### 2. Special Price Requests
- Create special price request
- Approval workflow
- Audit trail

### 3. Project Pricing
- Project-specific pricing
- Override system pricing
- Project-based quotes

### 4. Price Upload
- Excel/CSV file upload
- Bulk price updates
- Validation & error handling

### 5. RPA Automation
- D365 BC Sales Quote creation
- Automated data entry
- Offline support

### 6. Cache Management
- Item master cache
- Customer cache
- Invoice cache
- Scheduled refresh

### 7. Cross-Sell
- Product recommendations
- Rule-based suggestions
- Category-based grouping

### 8. Analytics
- Customer analytics
- Sales analytics
- Pricing analytics

---

## 🔗 EXTERNAL API INTEGRATIONS

### Business Central APIs
- **Item API** - Fetch item master data
- **Item Ledger API** - Fetch inventory
- **Branch API** - Fetch branch information
- **Sales Quote API** - Create sales quotes

### Employee API
- Fetch employee data
- Employee authentication
- Role & branch mapping

### Customer API
- Fetch customer data
- Customer search
- Customer analytics

### Invoice API
- Fetch invoice data
- Invoice details
- Invoice history

---

## 📝 CONFIGURATION FILES

### backend/.env
```
# Database
MSSQL_SERVER=localhost
MSSQL_DATABASE=SmartPricing
MSSQL_USER=sa
MSSQL_PASSWORD=password

# JWT
JWT_SECRET=your-secret-key
JWT_ALG=HS256

# External APIs
CUSTOMER_API_URL=http://api.example.com/customer
CUSTOMER_API_KEY=key
ITEM_API_URL=http://api.example.com/item
ITEM_API_KEY=key
```

### frontend/.env
```
VITE_API_URL=http://localhost:8000
VITE_SSO_LOGIN_URL=https://localhost:9443/auth/th2/login
VITE_SSO_LOGOUT_URL=https://localhost:9443/auth/th2/logout
VITE_UXP_LOGIN_URL=http://localhost:3000/hub
```

---

## 📋 INSTALLATION CHECKLIST

- [ ] Clone repository
- [ ] Install Python 3.9+
- [ ] Install Node.js 16+
- [ ] Install Docker & Docker Compose
- [ ] Configure backend/.env with API keys
- [ ] Configure frontend/.env with API URL
- [ ] Run: pip install -r requirements.txt (backend)
- [ ] Run: npm install (frontend)
- [ ] Run: docker-compose up -d
- [ ] Access: http://localhost:3200 (frontend)
- [ ] Access: http://localhost:8000/docs (API docs)

---

## 🐛 TROUBLESHOOTING

### Backend Issues
- Check .env file for API keys
- Verify MSSQL connection
- Check logs in backend/logs/

### Frontend Issues
- Clear browser cache
- Check frontend/.env for API URL
- Check browser console for errors

### Docker Issues
- Ensure Docker daemon is running
- Check docker-compose logs: docker-compose logs -f
- Verify port availability (8000, 3200)

---


