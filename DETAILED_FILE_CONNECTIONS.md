# DETAILED FILE CONNECTIONS - Smart Pricing System

## 🔗 HOW FILES CONNECT TO EACH OTHER

### FRONTEND → BACKEND CONNECTION MAP

#### 1. AUTHENTICATION FLOW
```
Frontend:
  Login.jsx
    ↓ (api.post("/login/init"))
Backend:
  main.py (router registration)
    ↓
  login.py (POST /login/init)
    ↓
  auth_dependency.py (JWT token creation)
    ↓
  role_mapping.py (Role mapping)
    ↓
  branch_region_mapping.py (Branch mapping)
    ↓
  config/config_external_api.py (Employee API config)
    ↓
  External: Employee API
    ↓
  Return: JWT Token
    ↓
Frontend:
  AuthContext.jsx (Store token)
```

#### 2. QUOTE CREATION FLOW (Step 1-6)
```
Frontend:
  CreateQuote/Step1_CustomerSearch.jsx
    ↓ (api.get("/api/customer/search"))
Backend:
  main.py
    ↓
  customer.py (GET /api/customer/search)
    ↓
  config/db_mssql.py (Database connection)
    ↓
  MSSQL: Customer table
    ↓
  Return: Customer list
    ↓
Frontend:
  CustomerSearchSection.jsx (Display results)
```

#### 3. PRODUCT SELECTION FLOW
```
Frontend:
  CreateQuote/Step2_ProductSelection.jsx
    ↓ (api.get("/api/items/categories/list"))
Backend:
  main.py
    ↓
  items.py (GET /items/categories/list)
    ↓
  config/db_mssql.py
    ↓
  MSSQL: Item_Master table
    ↓
  Return: Category list
    ↓
Frontend:
  CategoryCard.jsx (Display categories)
    ↓ (api.get("/api/items/categories/{category}/list"))
Backend:
  items.py (GET /items/categories/{category}/list)
    ↓
  config/db_mssql.py
    ↓
  MSSQL: Item_Master table (filtered by category)
    ↓
  Return: Items in category
    ↓
Frontend:
  ProductList.jsx (Display items)
```

#### 4. PRICING CALCULATION FLOW
```
Frontend:
  CreateQuote/Step3_PriceReview.jsx
    ↓ (api.post("/api/pricing/calculate"))
Backend:
  main.py
    ↓
  pricing_router.py (POST /api/pricing/calculate)
    ↓
  LevelPrice.py (Tier-based pricing logic)
    ↓
  price.py (Price calculation)
    ↓
  config/db_mssql.py
    ↓
  MSSQL: Item_Master, Item_Price, Special_Price_Request, Project_Price tables
    ↓
  Return: Calculated prices
    ↓
Frontend:
  Step3_PriceReview.jsx (Display prices)
```

#### 5. SHIPPING CALCULATION FLOW
```
Frontend:
  CreateQuote/Step4_Shipping.jsx
    ↓ (api.post("/api/shipping/calculate"))
Backend:
  main.py
    ↓
  shipping.py (POST /api/shipping/calculate)
    ↓
  config/db_mssql.py
    ↓
  MSSQL: Shipping rules table
    ↓
  Return: Shipping cost
    ↓
Frontend:
  ShippingModal.jsx (Display shipping cost)
```

#### 6. QUOTE SAVE FLOW
```
Frontend:
  CreateQuote/Step6_Summary.jsx
    ↓ (api.post("/quotation"))
Backend:
  main.py
    ↓
  quotation.py (POST /quotation)
    ↓
  config/db_mssql.py
    ↓
  MSSQL: Quote_Header, Quote_Line tables
    ↓
  Return: Quote ID
    ↓
Frontend:
  Dashboard.jsx (Show success message)
```

#### 7. PRICE UPLOAD FLOW
```
Frontend:
  UpdatePrice.jsx
    ↓ (api.post("/api/price-update/upload"))
Backend:
  main.py
    ↓
  price_update.py (POST /api/price-update/upload)
    ↓
  services/price_upload_service.py (File validation & processing)
    ↓
  config/db_mssql.py
    ↓
  MSSQL: Item_Price table (Upsert)
    ↓
  Return: Upload result
    ↓
Frontend:
  UploadPriceExcel.jsx (Display result)
```

#### 8. SPECIAL PRICE REQUEST FLOW
```
Frontend:
  PriceEditModal.jsx
    ↓ (api.post("/api/special-price-request"))
Backend:
  main.py
    ↓
  special_price_request_router.py (POST /api/special-price-request)
    ↓
  config/db_mssql.py
    ↓
  MSSQL: Special_Price_Request table
    ↓
  Return: Request ID
    ↓
Frontend:
  SpecialPriceApproval.jsx (Show pending requests)
    ↓ (api.put("/api/special-price-request/{id}/approve"))
Backend:
  special_price_request_router.py (PUT /api/special-price-request/{id}/approve)
    ↓
  config/db_mssql.py
    ↓
  MSSQL: Special_Price_Request table (Update status)
    ↓
  Return: Approval result
```

#### 9. PROJECT PRICING FLOW
```
Frontend:
  CreateQuote/Step6_Summary.jsx
    ↓ (api.get("/api/project-prices/by-customer"))
Backend:
  main.py
    ↓
  project_price_router.py (GET /api/project-prices/by-customer)
    ↓
  config/db_mssql.py
    ↓
  MSSQL: Project_Price table
    ↓
  Return: Project list
    ↓
Frontend:
  Project selector dropdown
    ↓ (api.post("/api/pricing/calculate") with project_id)
Backend:
  pricing_router.py (POST /api/pricing/calculate)
    ↓
  LevelPrice.py (Apply project pricing)
    ↓
  Return: Project-adjusted prices
```

#### 10. CROSS-SELL FLOW
```
Frontend:
  CreateQuote/Step6_Summary.jsx
    ↓ (api.get("/api/cross-sell/rules"))
Backend:
  main.py
    ↓
  cross_sell_router.py (GET /api/cross-sell/rules)
    ↓
  services/cross_sell_service.py (Cross-sell logic)
    ↓
  config/db_mssql.py
    ↓
  MSSQL: CrossSell_Rules table
    ↓
  Return: Recommended products
    ↓
Frontend:
  CrossSellPanel.jsx (Display recommendations)
```

---

## 📊 BACKEND INTERNAL CONNECTIONS

### MAIN.PY ROUTER REGISTRATION
```
main.py
├─ app.include_router(quotation_router, prefix="/api")
│  └─ quotation.py
│
├─ app.include_router(customer_router)
│  └─ customer.py
│
├─ app.include_router(items_router, prefix="/api")
│  └─ items.py
│
├─ app.include_router(pricing_router)
│  └─ pricing_router.py
│     ├─ LevelPrice.py
│     └─ price.py
│
├─ app.include_router(shipping_router)
│  └─ shipping.py
│
├─ app.include_router(login_router, prefix="/api")
│  └─ login.py
│     ├─ auth_dependency.py
│     ├─ role_mapping.py
│     └─ branch_region_mapping.py
│
├─ app.include_router(special_price_request_router)
│  └─ special_price_request_router.py
│
├─ app.include_router(project_price_router)
│  └─ project_price_router.py
│
├─ app.include_router(cross_sell_router, prefix="/api")
│  └─ cross_sell_router.py
│     └─ services/cross_sell_service.py
│
└─ ... (20 more routers)
```

### PRICING ENGINE CONNECTIONS
```
pricing_router.py
├─ calculate_pricing()
│  ├─ LevelPrice.py
│  │  ├─ get_tier_price()
│  │  └─ apply_discount()
│  │
│  ├─ price.py
│  │  ├─ calculate_unit_price()
│  │  └─ calculate_line_total()
│  │
│  ├─ config/db_mssql.py
│  │  ├─ Item_Master table
│  │  ├─ Item_Price table
│  │  ├─ Special_Price_Request table
│  │  └─ Project_Price table
│  │
│  └─ Return: Calculated prices with validations
```

### AUTHENTICATION FLOW
```
auth_dependency.py
├─ get_branch_code()
│  ├─ Extract JWT token from cookies/header
│  ├─ Decode JWT
│  └─ Extract branch code
│
└─ Used by: All routers that need branch_code

login.py
├─ POST /login/init
│  ├─ load_employee()
│  │  ├─ config/config_external_api.py (Employee API config)
│  │  ├─ External: Employee API call
│  │  └─ role_mapping.py (Map role)
│  │
│  ├─ Generate JWT token
│  └─ Return token
│
├─ POST /login/select-branch
│  ├─ branch_region_mapping.py (Get region)
│  └─ Return updated token
│
└─ POST /login/logout
   └─ Clear token
```

### DATABASE CONNECTIONS
```
config/db_mssql.py
├─ get_mssql_conn()
│  └─ Returns MSSQL connection
│
└─ Used by: All routers for database queries

config/db_sqlite.py
├─ get_sqlite_conn()
│  └─ Returns SQLite connection (fallback)
│
└─ Used by: Fallback when MSSQL unavailable

config/config_external_api.py
├─ CUSTOMER_API_URL, CUSTOMER_API_KEY
├─ ITEM_API_URL, ITEM_API_KEY
├─ EMPLOYEE_API_URL, EMPLOYEE_API_KEY
├─ INVOICE_API_URL, INVOICE_API_KEY
├─ BRANCH_API_URL, BRANCH_API_KEY
└─ Used by: External API clients
```

### EXTERNAL API CLIENTS
```
api/bc_item_client.py
├─ BCAPIClient class
│  ├─ fetch_items()
│  ├─ fetch_inventory()
│  └─ Used by: jobs/item_master_cache_refresh.py
│
└─ config/config_external_api.py (API config)

api/bc_branch_client.py
├─ BCBranchClient class
│  ├─ fetch_branches()
│  └─ Used by: branch.py router
│
└─ config/config_external_api.py (API config)
```

### SCHEDULED JOBS
```
jobs/item_master_cache_refresh.py
├─ Scheduled by: APScheduler
├─ Calls: api/bc_item_client.py
├─ Updates: MSSQL cache tables
└─ Logs: jobs/logs/item_master_cache_refresh.log

jobs/customer_cache_refresh_standalone.py
├─ Scheduled by: APScheduler
├─ Calls: config/config_external_api.py (Customer API)
├─ Updates: MSSQL cache tables
└─ Logs: jobs/logs/customer_cache_refresh.log

jobs/invoice_cache_refresh.py
├─ Scheduled by: APScheduler
├─ Calls: config/config_external_api.py (Invoice API)
├─ Updates: MSSQL cache tables
└─ Logs: jobs/logs/invoice_cache_refresh.log

jobs/scheduled_price_upload_standalone.py
├─ Scheduled by: APScheduler
├─ Calls: services/price_upload_service.py
├─ Updates: Item_Price table
└─ Logs: jobs/logs/scheduled_price_upload.log
```

### AIRFLOW DAGs
```
dags/item_master_cache_refresh_dag.py
├─ Task 1: Fetch items from BC API
├─ Task 2: Validate data
├─ Task 3: Update MSSQL
└─ Task 4: Log results

dags/d365_cache_refresh_pipeline_dag.py
├─ Task 1: Refresh item master
├─ Task 2: Refresh customer data
├─ Task 3: Refresh invoice data
└─ Task 4: Refresh branch data

dags/scheduled_price_upload_dag.py
├─ Task 1: Check for new price files
├─ Task 2: Validate file format
├─ Task 3: Upload prices
└─ Task 4: Log results
```

---

## 🎨 FRONTEND INTERNAL CONNECTIONS

### ROUTING STRUCTURE
```
App.jsx
├─ React Router setup
├─ ProtectedRoute wrapper
└─ Routes:
   ├─ /login → Login.jsx
   ├─ /dashboard → Dashboard.jsx
   ├─ /create-quote → CreateQuote/
   │  ├─ Step1_CustomerSearch.jsx
   │  ├─ Step2_ProductSelection.jsx
   │  ├─ Step3_PriceReview.jsx
   │  ├─ Step4_Shipping.jsx
   │  ├─ Step5_Summary.jsx
   │  └─ Step6_Summary.jsx
   ├─ /update-price → UpdatePrice.jsx
   ├─ /project-price → ProjectPrice.jsx
   ├─ /special-price-approval → SpecialPriceApproval.jsx
   └─ /admin → AdminConfig.jsx
```

### CONTEXT & STATE MANAGEMENT
```
AuthContext.jsx
├─ Provides: user, token, login, logout
├─ Used by: All pages via useAuth hook
└─ Stores: JWT token, employee info, branch info

CreateQuote State (useReducer)
├─ state.customer
├─ state.cart
├─ state.shippingCustomerPay
├─ state.deliveryType
├─ state.project_code
└─ Used by: All CreateQuote steps
```

### COMPONENT HIERARCHY
```
CreateQuote/Step6_Summary.jsx (Main component)
├─ CustomerSearchSection.jsx
│  └─ api.get("/api/customer/search")
│
├─ ItemPickerModal.jsx
│  └─ api.get("/api/items/search")
│
├─ GlassPickerModal.jsx
│  └─ api.get("/api/items/search")
│
├─ ProductList.jsx
│  ├─ api.get("/api/items/categories/list")
│  └─ api.get("/api/items/categories/{category}/list")
│
├─ ProductDetail.jsx
│  └─ api.get("/api/items/{sku}")
│
├─ CartItemRow.jsx
│  └─ Display cart items
│
├─ CrossSellPanel.jsx
│  └─ api.get("/api/cross-sell/rules")
│
├─ ShippingModal.jsx
│  └─ api.post("/api/shipping/calculate")
│
├─ TaxDeliverySection.jsx
│  └─ Display tax & delivery info
│
└─ useStep6Pricing hook
   └─ api.post("/api/pricing/calculate")
```

### HOOKS & UTILITIES
```
useAuth.js
├─ Returns: { user, token, login, logout }
└─ Uses: AuthContext

useStep6Data.js
├─ Returns: { vatRate, branches, isPreOrder, ... }
└─ Fetches: VAT rate, branches, special prices

useStep6Stock.js
├─ Returns: { selectedItemStock, stockLoading, ... }
└─ Fetches: api.get("/api/items/{sku}/stock")

useStep6Pricing.js
├─ Returns: { calculation, setCalculation, ... }
└─ Fetches: api.post("/api/pricing/calculate")

useStep6History.js
├─ Returns: { handleRepeatFromHistory }
└─ Fetches: api.get("/api/quotation?status=complete")
```

### API SERVICE
```
services/api.js
├─ axios instance with:
│  ├─ baseURL: http://localhost:8000
│  ├─ timeout: 3000000
│  ├─ withCredentials: true
│  └─ Authorization header with JWT token
│
└─ Helper functions:
   └─ getItemStock(sku)
```

---

## 🔄 DATA FLOW EXAMPLES

### Example 1: Create Quote with Pricing
```
1. User selects customer
   Frontend: CustomerSearchSection.jsx
   → api.get("/api/customer/search")
   → Backend: customer.py
   → MSSQL: Customer table
   → Return: Customer data

2. User adds items to cart
   Frontend: ItemPickerModal.jsx
   → api.get("/api/items/search")
   → Backend: items.py
   → MSSQL: Item_Master table
   → Return: Item list

3. User reviews prices
   Frontend: Step3_PriceReview.jsx
   → api.post("/api/pricing/calculate")
   → Backend: pricing_router.py
   → LevelPrice.py (Calculate tier price)
   → price.py (Calculate line total)
   → MSSQL: Item_Master, Item_Price, Special_Price_Request, Project_Price
   → Return: Calculated prices

4. User saves quote
   Frontend: Step6_Summary.jsx
   → api.post("/quotation")
   → Backend: quotation.py
   → MSSQL: Quote_Header, Quote_Line
   → Return: Quote ID
```

### Example 2: Upload Prices
```
1. User selects Excel file
   Frontend: UploadPriceExcel.jsx
   → File selected

2. User uploads file
   Frontend: UploadPriceExcel.jsx
   → api.post("/api/price-update/upload", formData)
   → Backend: price_update.py
   → services/price_upload_service.py
   → Validate file format
   → Validate columns (SKU, R1, R2, W1, W2)
   → For each row:
      - Validate SKU exists in Item_Master
      - Upsert to Item_Price table
   → MSSQL: Item_Master, Item_Price
   → Return: { total_rows, successful, errors }

3. User sees result
   Frontend: UploadPriceExcel.jsx
   → Display upload result
```

### Example 3: Approve Special Price Request
```
1. Admin views pending requests
   Frontend: SpecialPriceApproval.jsx
   → api.get("/api/special-price-request")
   → Backend: special_price_request_router.py
   → MSSQL: Special_Price_Request table
   → Return: Pending requests

2. Admin approves request
   Frontend: SpecialPriceApproval.jsx
   → api.put("/api/special-price-request/{id}/approve")
   → Backend: special_price_request_router.py
   → MSSQL: Special_Price_Request table (Update status)
   → Return: Approval result

3. Next pricing calculation uses approved price
   Frontend: CreateQuote/Step3_PriceReview.jsx
   → api.post("/api/pricing/calculate")
   → Backend: pricing_router.py
   → LevelPrice.py (Check Special_Price_Request table)
   → Return: Approved special price
```

---

## 📋 FILE DEPENDENCY MATRIX

| File | Depends On | Used By |
|------|-----------|---------|
| main.py | All routers | FastAPI app |
| auth_dependency.py | role_mapping.py, branch_region_mapping.py | All routers |
| login.py | auth_dependency.py, config_external_api.py | Frontend login |
| pricing_router.py | LevelPrice.py, price.py, db_mssql.py | Frontend pricing |
| quotation.py | db_mssql.py, auth_dependency.py | Frontend quote save |
| customer.py | db_mssql.py, auth_dependency.py | Frontend customer search |
| items.py | db_mssql.py, auth_dependency.py | Frontend product selection |
| price_upload_service.py | db_mssql.py | price_update.py |
| bc_item_client.py | config_external_api.py | jobs/item_master_cache_refresh.py |
| cross_sell_router.py | cross_sell_service.py, db_mssql.py | Frontend cross-sell |

---

## 🎯 SUMMARY

The Smart Pricing System is built with a clear separation of concerns:

1. **Frontend** (React) handles UI and user interactions
2. **Backend** (FastAPI) handles business logic and data processing
3. **Database** (MSSQL) stores all data
4. **External APIs** provide data from Business Central, Employee, Customer, Invoice systems
5. **RPA Agent** automates D365 BC operations
6. **Scheduled Jobs** refresh cache and upload prices

Each component communicates through well-defined APIs and follows a consistent pattern of request/response handling.
