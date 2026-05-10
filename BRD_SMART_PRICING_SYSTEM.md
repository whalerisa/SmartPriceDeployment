# Business Requirements Document (BRD)
## Smart Pricing System

**Document Version:** 1.0  
**Last Updated:** May 2026  
**Status:** Active  

---

## 📋 EXECUTIVE SUMMARY

Smart Pricing System is a comprehensive quotation and pricing management platform designed to streamline the sales process for building materials (glass, aluminium, gypsum, etc.). The system automates price calculation based on customer tier, delivery method, payment terms, and special pricing rules, while integrating with Business Central (D365) for inventory and sales data.

**Key Objective:** Enable sales teams to create accurate, competitive quotes quickly while maintaining profit margins and compliance with pricing policies.

---

## 🎯 BUSINESS OBJECTIVES

1. **Accelerate Quote Generation** - Reduce quote creation time from hours to minutes
2. **Ensure Pricing Accuracy** - Eliminate manual calculation errors
3. **Maintain Profit Margins** - Apply consistent pricing rules across all sales
4. **Support Multi-Tier Pricing** - Offer different prices based on customer value
5. **Enable Special Pricing** - Allow flexible pricing with approval workflows
6. **Integrate with D365** - Sync inventory, customer, and sales data
7. **Automate D365 Quote Creation** - Reduce manual data entry via RPA
8. **Provide Analytics** - Track pricing trends and customer profitability

---

## 👥 STAKEHOLDERS

| Role | Responsibility | Needs |
|------|-----------------|-------|
| **Sales Team** | Create quotes, manage customers | Fast quote generation, accurate pricing |
| **Sales Manager (ZM)** | Approve special prices, manage team | Approval workflows, pricing visibility |
| **Regional Manager (RM)** | Monitor regional sales, pricing | Analytics, pricing compliance |
| **Sales Director (SDM)** | Strategic pricing decisions | Pricing trends, profit analysis |
| **Project Manager (PM)** | Manage project-specific pricing | Project pricing management |
| **Admin** | System configuration, user management | Configuration tools, access control |
| **Finance** | Invoice tracking, profit analysis | Accurate pricing, profit reports |

---

## 📊 SYSTEM SCOPE

### IN SCOPE
- ✅ Multi-step quote creation wizard
- ✅ Dynamic pricing calculation (tier-based)
- ✅ Special price request workflow
- ✅ Project-specific pricing
- ✅ Price upload (Excel/CSV)
- ✅ Customer search and management
- ✅ Product catalog browsing
- ✅ Quote draft management
- ✅ Quote printing/PDF generation
- ✅ RPA automation for D365 quote creation
- ✅ Promotion management
- ✅ Cross-sell recommendations
- ✅ Customer analytics
- ✅ Role-based access control

### OUT OF SCOPE
- ❌ Invoice creation (handled by D365)
- ❌ Payment processing
- ❌ Inventory management (read-only from D365)
- ❌ Customer credit management (read-only)
- ❌ Financial reporting (separate system)

---

## 🔄 CORE FEATURES

### 1. QUOTE CREATION WIZARD (6 Steps)

#### Step 1: Customer Search
- **Requirement:** Search and select customer
- **Inputs:** Customer code, phone, name
- **Outputs:** Customer data (code, name, payment terms, credit limit, sales history)
- **Business Rules:**
  - Support "ขายสด" (cash sales) as default customer
  - Display customer sales history by category
  - Show customer tier information

#### Step 2: Product Selection
- **Requirement:** Browse and select products
- **Inputs:** Category selection, product search
- **Outputs:** Selected items with quantity and specifications
- **Business Rules:**
  - Support 6 product categories: Glass (G), Aluminium (A), C-Line (C), Gypsum (Y), Sealant (S), Accessories (E)
  - For Glass: Support size selection (standard, semi-standard, custom)
  - For Aluminium: Support weight-based pricing
  - Display product images and specifications
  - Show stock availability

#### Step 3: Price Review
- **Requirement:** Review and adjust prices
- **Inputs:** Cart items, customer data
- **Outputs:** Calculated prices with tier information
- **Business Rules:**
  - Display system price (calculated by LevelPrice + Price engine)
  - Allow manual price override (triggers special price request)
  - Show price breakdown (unit price, line total)
  - Display price source (system, manual, project, history, special)
  - Highlight prices below R1 (requires approval)

#### Step 4: Shipping Configuration
- **Requirement:** Configure delivery method and cost
- **Inputs:** Delivery type (pickup/delivery), vehicle type, distance, unload hours, staff count
- **Outputs:** Shipping cost
- **Business Rules:**
  - Calculate shipping cost based on delivery parameters
  - Support pickup (no shipping cost) and delivery (calculated cost)
  - Display shipping cost breakdown

#### Step 5: Tax & Delivery Summary
- **Requirement:** Review tax and delivery settings
- **Inputs:** Tax invoice requirement, delivery date
- **Outputs:** Tax invoice surcharge (if applicable)
- **Business Rules:**
  - Support tax invoice requirement (10 baht surcharge)
  - Distribute surcharge across items
  - Display required delivery date

#### Step 6: Final Summary
- **Requirement:** Review complete quote and save
- **Inputs:** All previous steps data
- **Outputs:** Quote saved to database, option to send to D365
- **Business Rules:**
  - Display complete quote summary
  - Show totals (subtotal, VAT, total)
  - Show profit margin
  - Support quote save as draft or confirmed
  - Support sending to D365 via RPA
  - Support quote reorder from history

---

### 2. PRICING ENGINE

#### 2.1 Tier-Based Pricing (LevelPrice)

**Objective:** Calculate customer tier based on customer value metrics

**Input Metrics:**
- Tenure: Days as customer
- Accumulation: Total sales last 6 months
- Frequency: Number of purchases last 6 months
- Gen_Bus: Customer type (RETAIL, WHOLESALE, etc.)

**Calculation:**
```
1. Convert each metric to score (0-100)
2. Calculate weighted average:
   - Tenure: 25%
   - Accumulation: 25%
   - Frequency: 25%
   - Gen_Bus: 25%
3. Map score to tier:
   - 0-20: R2 (highest price)
   - 20-40: R1
   - 40-60: W2
   - 60-80: W1
   - 80-100: P (lowest price)
```

**Output:** Customer tier (R2→R1, R1→W2, W2→W1, W1→P)

#### 2.2 Price Interpolation (Price)

**Objective:** Calculate final unit price based on tier and scoring factors

**Input Factors:**
- Quantity score: qty / pkg_size (0.0-1.0)
- Relevant sales score: log(sales_by_category) / 13 (0.0-1.0)
- Shipment score: 1.0 if PICKUP, 0.0 if DELIVERY
- Weights: Qty 33.82%, Sales 39.71%, Shipment 26.47%

**Calculation:**
```
1. Calculate combined score (0.0-1.0)
2. Interpolate price between tier boundaries:
   new_price = low_price + (high_price - low_price) * (1 - score)
3. Apply payment term markup:
   - NET 0: 0%
   - NET 15: +0.30%
   - NET 30: +0.60%
   - NET 45: +0.90%
   - NET 60: +1.20%
   - NET 90: +1.50%
4. Round to 2 decimal places
```

**Output:** Final unit price

#### 2.3 Price Priority

**Priority Order (highest to lowest):**
1. Manual Price (if approved or promotion)
2. Promotion Price (no approval needed)
3. Project Price (if project_id provided)
4. History Price (if higher than system price)
5. Special Price Request (if approved & active)
6. System Price (LevelPrice + Price calculation)

#### 2.4 Category-Specific Pricing

**Glass (G):**
- Quantity = Pieces × Sqft_Sheet (unless sold by pack)
- Price = Price_per_sqft × Sqft_Sheet
- Rounding: Round up to nearest 0.50

**Aluminium (A):**
- Quantity = Pieces
- Price = Price_per_kg × Weight
- Rounding: No rounding (exact price)

**Others (C, Y, S, E):**
- Quantity = Pieces
- Price = Unit price
- Rounding: Round up to nearest 0.50

---

### 3. SPECIAL PRICE REQUEST WORKFLOW

**Objective:** Allow flexible pricing with approval chain

**Process:**
```
1. Sales creates special price request (price < R1)
2. System determines approval level:
   - Price < SDM: PM approval required
   - Price < W1: SDM approval required
   - Price < W2: ZM + RM approval required
   - Price < R1: ZM approval required
3. Approver reviews and approves/rejects
4. If approved: Price becomes active for customer
5. If rejected: Sales must use system price
```

**Business Rules:**
- Special price valid for specific date range
- Can be used multiple times for same customer
- Audit trail of all approvals
- Automatic expiration after end date

---

### 4. PROJECT PRICING

**Objective:** Support project-specific pricing

**Features:**
- Create project with custom prices for specific items
- Prices override system pricing for project
- Valid for specific date range
- Support multiple projects per customer
- Auto-select project when creating quote

**Business Rules:**
- Project price takes precedence over system price
- Project price does not require approval
- Project prices are exact (no rounding)

---

### 5. PRICE UPLOAD

**Objective:** Bulk update prices from Excel/CSV

**Features:**
- Support Excel (.xlsx, .xls) and CSV formats
- Validate required columns (SKU, R1, R2, W1, W2, SDM)
- Validate SKU existence in Item_Master
- Upsert to Item_Price table
- Show upload summary (total, successful, errors)

**Business Rules:**
- Only admin can upload prices
- Prices effective immediately after upload
- Audit trail of all uploads
- Support branch-specific pricing

---

### 6. PROMOTION MANAGEMENT

**Objective:** Create and manage promotional pricing

**Features:**
- Create promotion with custom price
- Set promotion date range
- Apply to specific customers or all
- No approval required for promotions
- Automatic expiration after end date

**Business Rules:**
- Promotion price overrides system price
- Promotion does not require special price approval
- Can be combined with project pricing

---

### 7. CUSTOMER ANALYTICS

**Objective:** Provide insights into customer profitability

**Metrics:**
- Total sales by customer (6 months, 12 months)
- Purchase frequency
- Average order value
- Profit margin by customer
- Sales by category

**Business Rules:**
- Data updated daily from D365
- Support filtering by date range, region, category
- Export to Excel

---

### 8. RPA AUTOMATION

**Objective:** Automate D365 Sales Quote creation

**Features:**
- Send quote to D365 via RPA
- Automate quote creation in D365
- Populate customer, items, prices
- Generate D365 quote number
- Support offline mode with bundled chromedriver

**Business Rules:**
- Only confirmed quotes can be sent to D365
- RPA runs on separate machine with Chrome remote debugging
- Automatic retry on failure
- Audit trail of all RPA operations

---

## 📱 USER INTERFACE REQUIREMENTS

### Frontend Technology
- **Framework:** React 19 with Vite
- **Styling:** Tailwind CSS
- **State Management:** Context API + useReducer
- **Routing:** React Router v7
- **HTTP Client:** Axios

### Key Pages
1. **Login** - Employee authentication via UXP
2. **Dashboard** - Quick access to main features
3. **Create Quote** - 6-step wizard
4. **Update Price** - Price upload
5. **Project Price** - Project pricing management
6. **Special Price Approval** - Approval workflow
7. **Promotion Management** - Promotion CRUD
8. **Admin Config** - System configuration

### Responsive Design
- Support desktop (1920x1080 minimum)
- Support tablet (iPad)
- Mobile-friendly navigation

---

## 🔐 SECURITY & ACCESS CONTROL

### Authentication
- JWT token-based authentication
- Integration with UXP (User Experience Portal)
- Token expiration: 12 hours
- Support manual login with employee code

### Authorization
- Role-based access control (RBAC)
- Roles: Sales, ZM, RM, SDM, PM, CEO, Admin
- Page-level access control
- API endpoint protection

### Data Security
- All API calls require valid JWT token
- Sensitive data (API keys) stored in .env
- HTTPS for all communications
- SQL injection prevention via parameterized queries

---

## 🗄️ DATA REQUIREMENTS

### Database
- **Primary:** MSSQL Server
- **Fallback:** SQLite
- **Branch-specific pricing:** Support multiple branches

### Key Tables
- Item_Master: Product information
- Item_Price: Product pricing by branch
- Customer: Customer data
- Quote_Header: Quote header
- Quote_Line: Quote line items
- Special_Price_Request: Special price requests
- Project_Price: Project pricing
- Promotion: Promotions

### Data Sync
- Item Master: Sync from D365 daily
- Customer: Sync from D365 daily
- Invoice: Sync from D365 daily
- Branch: Sync from D365 daily

---

## 🔌 EXTERNAL INTEGRATIONS

### Business Central (D365)
- **Item API:** Fetch item master data
- **Item Ledger API:** Fetch inventory
- **Branch API:** Fetch branch information
- **Sales Quote API:** Create sales quotes
- **Customer API:** Fetch customer data
- **Invoice API:** Fetch invoice data
- **Employee API:** Fetch employee data

### Authentication
- API Key authentication
- Separate API keys for each endpoint
- Keys stored in .env file

---

## 📊 REPORTING & ANALYTICS

### Available Reports
1. **Quote Summary** - Total quotes, average value, conversion rate
2. **Pricing Analysis** - Price distribution, margin analysis
3. **Customer Analysis** - Top customers, sales by category
4. **Special Price Analysis** - Approved vs rejected requests
5. **Promotion Performance** - Promotion usage, impact on sales

### Export Formats
- Excel (.xlsx)
- PDF
- CSV

---

## 🚀 DEPLOYMENT

### Environment
- **Development:** Local machine
- **Staging:** Docker containers
- **Production:** Docker containers on cloud

### Deployment Method
- Docker Compose (Frontend + Backend)
- Frontend: Nginx reverse proxy
- Backend: FastAPI + Uvicorn
- Database: MSSQL Server

### Scaling
- Horizontal scaling via load balancer
- Database connection pooling
- Cache layer for frequently accessed data

---

## 📈 PERFORMANCE REQUIREMENTS

| Metric | Target | Current |
|--------|--------|---------|
| Quote creation time | < 5 minutes | 2-3 minutes |
| Price calculation | < 2 seconds | 1-2 seconds |
| Search response | < 1 second | 0.5-1 second |
| Page load time | < 3 seconds | 1-2 seconds |
| API response time | < 500ms | 200-400ms |
| Concurrent users | 100+ | 50+ |
| Uptime | 99.5% | 99.8% |

---

## 🎯 SUCCESS METRICS

### Business Metrics
- Quote creation time reduced by 80%
- Quote accuracy improved to 99%+
- Special price approval time < 1 hour
- Customer satisfaction score > 4.5/5
- Sales team adoption rate > 90%

### Technical Metrics
- System uptime > 99.5%
- API response time < 500ms
- Error rate < 0.1%
- Database query time < 100ms

---

## 📅 ROADMAP

### Phase 1 (Current)
- ✅ Core quote creation
- ✅ Tier-based pricing
- ✅ Special price requests
- ✅ Project pricing
- ✅ Price upload

### Phase 2 (Q3 2026)
- 🔄 Advanced analytics
- 🔄 Mobile app
- 🔄 AI-powered pricing recommendations
- 🔄 Multi-currency support

### Phase 3 (Q4 2026)
- 🔄 Predictive analytics
- 🔄 Integration with CRM
- 🔄 Automated pricing optimization
- 🔄 Real-time inventory sync

---

## 🐛 KNOWN ISSUES & LIMITATIONS

### Current Limitations
1. **Offline Mode:** Limited functionality without internet
2. **Real-time Sync:** Data synced daily, not real-time
3. **Mobile:** Limited mobile support (tablet-friendly only)
4. **Multi-currency:** Single currency (THB) only
5. **Bulk Operations:** Limited bulk quote creation

### Known Issues
1. **RPA:** Requires manual Chrome setup
2. **Performance:** Slow with large datasets (>10,000 items)
3. **Reporting:** Limited export formats

---

## 📞 SUPPORT & MAINTENANCE

### Support Channels
- Email: support@company.com
- Phone: +66-2-XXX-XXXX
- Internal Wiki: https://wiki.company.com/smart-pricing

### Maintenance Windows
- Weekly: Tuesday 2:00-3:00 AM (Bangkok time)
- Monthly: First Sunday 1:00-3:00 AM (Bangkok time)

### SLA
- Critical issues: 1 hour response time
- High priority: 4 hours response time
- Medium priority: 1 business day
- Low priority: 3 business days

---

## 📝 APPENDIX

### A. Glossary
- **BRD:** Business Requirements Document
- **D365:** Microsoft Dynamics 365
- **RPA:** Robotic Process Automation
- **JWT:** JSON Web Token
- **RBAC:** Role-Based Access Control
- **SKU:** Stock Keeping Unit
- **Tier:** Customer pricing tier (R2, R1, W2, W1, P)
- **Sqft:** Square feet
- **VAT:** Value Added Tax

### B. Related Documents
- COMPLETE_SYSTEM_ARCHITECTURE.md
- DETAILED_FILE_CONNECTIONS.md
- PRICING_CALCULATION_DETAILED_FLOW.md
- PROJECT_SYSTEM_DOCUMENTATION.md

### C. Contact Information
- **Product Owner:** [Name]
- **Technical Lead:** [Name]
- **Project Manager:** [Name]

---

**Document Approval:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | | | |
| Technical Lead | | | |
| Project Manager | | | |
| Stakeholder | | | |

---

**Change History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | May 2026 | AI Assistant | Initial BRD |
| | | | |

---

*This document is confidential and intended for authorized personnel only.*
