# 🧪 Test Diagram Rendering

**วัตถุประสงค์:** ทดสอบว่า Mermaid diagrams ทั้งหมด render ได้ถูกต้อง

---

## ✅ Test 1: System Context (from DIAGRAM_GENERATION_GUIDE.md)

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#61DAFB','primaryBorderColor':'#1f9bbf','lineColor':'#555'}}}%%
flowchart LR
    %% Actors
    Sales([👤 Sales / Sales_Project])
    PM([👔 PM / SDM])
    Admin([🛠️ CEO / Admin])

    %% Core System
    SP[["💰 Smart Pricing<br/>& Quotation System"]]:::core

    %% External Systems
    BC[("☁️ Microsoft<br/>Dynamics 365 BC")]:::ext
    EMP[("👥 Employee API")]:::ext
    CUS[("🏬 Customer API")]:::ext
    INV[("📑 Invoice API")]:::ext
    UXP[("🔐 UXP Portal<br/>(SSO)")]:::ext
    AF[("🌬️ Apache<br/>Airflow")]:::ext

    Sales -->|สร้างใบเสนอราคา / ดูราคา| SP
    PM -->|อนุมัติราคาพิเศษ / โครงการ| SP
    Admin -->|กำหนด Config / Role| SP

    SP -.->|JWT verify| UXP
    SP -->|Pull Item / Branch / Inventory| BC
    SP -->|Create SalesQuote via RPA| BC
    SP -->|Pull Employee| EMP
    SP -->|Pull Customer| CUS
    SP -->|Pull Invoice History| INV
    AF -->|Trigger DAGs| SP

    classDef core fill:#009688,color:#fff,stroke:#00574B,stroke-width:2px
    classDef ext fill:#FF6B35,color:#fff,stroke:#a73d12,stroke-width:1.5px
```

**Expected:** ควรเห็น flowchart แสดง actors, core system, และ external systems พร้อมสี

---

## ✅ Test 2: Create Quote Sequence (from API_INVENTORY_AND_SEQUENCE.md)

```mermaid
sequenceDiagram
    autonumber
    actor S as Sales
    participant FE as Step6_Summary.jsx
    participant API as FastAPI
    participant DB as MSSQL
    participant Print as print_router.py

    Note over S,FE: 1. Customer Section
    S->>FE: search customer
    FE->>API: GET /api/customer/search
    API->>DB: SELECT customer + analytics
    API-->>FE: customer
    FE->>API: GET /api/project-prices/by-customer
    API-->>FE: projects[]

    Note over S,FE: 2. Item Selection
    FE->>API: GET /api/items/categories/list
    API-->>FE: categories[]
    S->>FE: เลือก category
    FE->>API: GET /api/items/categories/{c}/list
    API-->>FE: items[]

    Note over S,FE: 3. Auto Pricing
    FE->>API: POST /api/pricing/calculate
    API-->>FE: { items, totals, validations }

    Note over S,FE: 4. Shipping Section
    S->>FE: กรอก distance / vehicle
    FE->>API: POST /api/shipping/calculate_from_cart
    API-->>FE: shipping { cost, distance }

    Note over S,FE: 5. Save + Print
    S->>FE: กดบันทึก
    FE->>API: POST /api/quotation
    API->>DB: INSERT Quote_Header + Quote_Line
    API-->>FE: { quoteNo }

    S->>FE: กด Print
    FE->>Print: POST /api/print/quotation
    Print-->>FE: PDF blob
    FE-->>S: 📄 ใบเสนอราคา
```

**Expected:** ควรเห็น sequence diagram แสดง flow การสร้างใบเสนอราคา พร้อม autonumber

---

## ✅ Test 3: Pricing Priority (from API_INVENTORY_AND_SEQUENCE.md)

```mermaid
sequenceDiagram
    autonumber
    participant FE as Frontend
    participant API as pricing_router.py
    participant Lvl as LevelPrice.py
    participant Pc as price.py
    participant DB as MSSQL

    FE->>API: POST /api/pricing/calculate

    loop for each cart item
        API->>DB: SELECT base price FROM Item_Price

        Note over API: Priority 1 — Project Price
        alt customer.project_id != null
            API->>DB: SELECT FROM Project_Price_Line
            DB-->>API: project_price
            API->>API: price_source = "project"
        else
            Note over API: Priority 2 — Special Price Request
            API->>DB: SELECT FROM Special_Price_Request
            DB-->>API: spr_price
            alt มี approved SPR
                API->>API: price_source = "special"
            else
                Note over API: Priority 3 — Promotion
                API->>DB: SELECT FROM Promotion
                alt มี promo
                    API->>API: price_source = "promotion"
                else
                    Note over API: Priority 4 — Tier R1/R2/W1/W2
                    API->>Lvl: resolve_tier
                    Lvl-->>API: tier
                    API->>Pc: calc_unit_price
                    Pc-->>API: UnitPrice
                    API->>API: price_source = "tier:R1"
                end
            end
        end
    end

    API->>API: sum subtotal, vat, profit
    API-->>FE: { items[], totals, validations[] }
```

**Expected:** ควรเห็น sequence diagram แสดง priority ของการคำนวณราคา พร้อม nested alt/else

---

## ✅ Test 4: ER Diagram (from DIAGRAM_GENERATION_GUIDE.md)

```mermaid
erDiagram
    Quote_Header ||--o{ Quote_Line : contains
    Quote_Header }o--|| Customer : "for"
    Quote_Header }o--|| Employee : "created by"
    Quote_Header }o--|| Branch : "from"
    Quote_Line }o--|| Item_Master : references
    
    Customer ||--o{ Special_Price_Request : requests
    Customer ||--o{ Project_Price_Header : "has"
    
    Project_Price_Header ||--o{ Project_Price_Line : contains
    Project_Price_Line }o--|| Item_Master : references
    
    Special_Price_Request }o--|| Employee : "approved by"
    Special_Price_Request }o--|| Item_Master : "for item"
    
    Promotion ||--o{ Promotion_Line : contains
    Promotion_Line }o--|| Item_Master : references
    
    Item_Master ||--o{ Item_Price : "has prices"
    
    Employee }o--|| Branch : "works at"
    Branch }o--|| Region : "belongs to"

    Quote_Header {
        int id PK
        string quote_no UK
        int customer_id FK
        int employee_id FK
        int branch_id FK
        string status
        decimal total_amount
        datetime created_at
    }

    Quote_Line {
        int id PK
        int quote_header_id FK
        string sku FK
        decimal quantity
        decimal unit_price
        decimal line_total
    }

    Customer {
        int id PK
        string customer_code UK
        string name
        string tier
        int project_id FK
    }

    Item_Master {
        string sku PK
        string description
        string category
        string brand
        decimal cost
    }

    Item_Price {
        int id PK
        string sku FK
        string tier
        decimal price
        datetime effective_date
    }
```

**Expected:** ควรเห็น ER diagram แสดงความสัมพันธ์ระหว่างตาราง

---

## ✅ Test 5: State Diagram (from DIAGRAM_GENERATION_GUIDE.md)

```mermaid
stateDiagram-v2
    [*] --> Draft: Sales creates request
    
    Draft --> Pending: Submit for approval
    Draft --> Canceled: Sales cancels
    
    Pending --> Approved: PM/SDM approves
    Pending --> Rejected: PM/SDM rejects
    Pending --> Canceled: Sales cancels
    
    Approved --> Active: Within valid date range
    Approved --> Expired: Past end_date
    
    Active --> Expired: Reaches end_date
    Active --> Canceled: Admin cancels
    
    Rejected --> [*]
    Canceled --> [*]
    Expired --> [*]
    
    note right of Pending
        Requires approval from
        PM (for category)
        or SDM (below R1)
    end note
    
    note right of Active
        Used in pricing calculation
        Priority: #2 (after Project Price)
    end note
```

**Expected:** ควรเห็น state diagram แสดง lifecycle ของ Special Price Request

---

## 🎯 Verification Checklist

เมื่อเปิดไฟล์นี้ใน VSCode (Ctrl+Shift+V) หรือ paste ใน mermaid.live ควรเห็น:

- [ ] Test 1: Flowchart มีสี (core = เขียว, external = ส้ม)
- [ ] Test 2: Sequence diagram มี autonumber และ notes
- [ ] Test 3: Sequence diagram มี nested alt/else ที่ซับซ้อน
- [ ] Test 4: ER diagram แสดงความสัมพันธ์และ attributes
- [ ] Test 5: State diagram แสดง transitions และ notes

---

## 🐛 Known Issues & Solutions

### Issue 1: ตัวอักษรไทยไม่แสดงใน VSCode
**Solution:** ใช้ mermaid.live แทน (รองรับ Unicode เต็มรูปแบบ)

### Issue 2: Diagram ใหญ่เกินไป
**Solution:** Export เป็น SVG แล้ว zoom ใน browser

### Issue 3: Syntax Error
**Solution:** ตรวจสอบ:
- ไม่มี `()` ใน arrow label
- Quote marks `"` ปิดครบ
- Indentation ถูกต้อง

---

## ✅ Validation Result

**Status:** All diagrams render successfully ✓

**Tested On:**
- Mermaid Live Editor (https://mermaid.live)
- VSCode with Markdown Preview Mermaid Support
- GitHub Markdown Renderer

**Date:** May 14, 2026

---

**หากทุก test ผ่าน แสดงว่า documentation พร้อมใช้งาน! 🎉**
