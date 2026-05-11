# Items.py API - ละเอียดทั้งหมด

**File:** `backend/items.py`  
**Router Prefix:** `/items`  
**Total APIs:** 8 endpoints

---

## 📋 API OVERVIEW

| # | Endpoint | Method | Purpose |
|---|----------|--------|---------|
| 1 | `/categories/list` | GET | ดึงรายชื่อหมวดหมู่สินค้า |
| 2 | `/categories/{category}/list` | GET | ดึงสินค้าตามหมวดหมู่ (พร้อม filter) |
| 3 | `/list` | GET | ดึงสินค้าแบบ pagination |
| 4 | `/search` | GET | ค้นหาสินค้า (Full-Text Search) |
| 5 | `/{sku}` | GET | ดึงรายละเอียดสินค้า |
| 6 | `/related/{sku}` | GET | ดึงสินค้าที่เกี่ยวข้อง (Group เดียวกัน) |
| 7 | `/categories/{category}/filter-options` | GET | ดึง filter options (Cascading) |
| 8 | `/{sku}/stock` | GET | ดึงข้อมูล stock จาก BC API |

---

## 🔍 DETAILED API EXPLANATION

### 1️⃣ GET `/categories/list`

**Purpose:** ดึงรายชื่อหมวดหมู่สินค้าทั้งหมด

**Request:**
```
GET /api/items/categories/list
```

**Parameters:** ไม่มี

**Response:**
```json
[
  {
    "name": "G",
    "count": 150
  },
  {
    "name": "A",
    "count": 200
  },
  {
    "name": "C",
    "count": 80
  },
  {
    "name": "Y",
    "count": 120
  },
  {
    "name": "S",
    "count": 50
  },
  {
    "name": "E",
    "count": 300
  }
]
```

**Business Logic:**
```python
# ดึงอักษรตัวแรกของ SKU (category)
SELECT LEFT(SKU, 1) AS name, COUNT(*) AS count
FROM Item_Master
WHERE LEFT(SKU, 1) IN ('G', 'A', 'C', 'Y', 'S', 'E')
  AND Blocked = 0
GROUP BY LEFT(SKU, 1)
```

**Category Codes:**
- **G** = Glass (กระจก)
- **A** = Aluminium (อลูมิเนียม)
- **C** = C-Line (โครงคร่าว)
- **Y** = Gypsum (ยิปซัม)
- **S** = Sealant (ซิลิโคน)
- **E** = Accessories (อุปกรณ์)

**Use Case:** 
- Display category buttons in product browser
- Show item count per category

---

### 2️⃣ GET `/categories/{category}/list`

**Purpose:** ดึงสินค้าตามหมวดหมู่ พร้อม filter และ pagination

**Request:**
```
GET /api/items/categories/A/list?limit=10&offset=0&brand=01&group=02&search=profile
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| category | string | ✅ | Category code (G, A, C, Y, S, E) |
| limit | int | ❌ | Items per page (default: 10) |
| offset | int | ❌ | Pagination offset (default: 0) |
| brand | string | ❌ | Brand code (ตามประเภท) |
| group | string | ❌ | Group code |
| subGroup | string | ❌ | Sub-group code |
| color | string | ❌ | Color code |
| thickness | string | ❌ | Thickness code |
| character | string | ❌ | Character (for Accessories) |
| search | string | ❌ | Search text (SKU, name, alternate name) |

**Response:**
```json
{
  "items": [
    {
      "sku": "A01010101010101",
      "sku2": "ALU-001",
      "name": "Aluminium Profile 20x20",
      "unit": "เส้น",
      "product_group": "Profile",
      "product_sub_group": "Square",
      "alternate_names": "AL-PROFILE-20"
    }
  ],
  "limit": 10,
  "offset": 0,
  "count": 1,
  "total": 150
}
```

**Business Logic:**

**SKU Format by Category:**
```
A (Aluminium):  ABBGGSSSCCDD
  - A: Category
  - BB: Brand (2 digits)
  - GG: Group (2 digits)
  - SSS: Sub-group (3 digits)
  - CC: Color (2 digits)
  - DD: Thickness (2 digits)

C (C-Line):     CBBGGSSSCCDD
  - Same as Aluminium

E (Accessories): EBBGGSSCCX
  - E: Category
  - BBB: Brand (3 digits)
  - GG: Group (2 digits)
  - SS: Sub-group (2 digits)
  - CC: Color (2 digits)
  - X: Character (1 digit)

S (Sealant):    SBBGGSSSCC
  - S: Category
  - BB: Brand (2 digits)
  - GG: Group (2 digits)
  - SSS: Sub-group (3 digits)
  - CC: Color (2 digits)

Y (Gypsum):     YBBGGSSCCCDD
  - Y: Category
  - BB: Brand (2 digits)
  - GG: Group (2 digits)
  - SS: Sub-group (2 digits)
  - CCC: Color (3 digits)
  - DD: Thickness (2 digits)
```

**Filter Logic:**
```python
# Extract SKU components using SUBSTRING
if category == "A":
    if brand:
        WHERE SUBSTRING(SKU, 2, 2) = brand
    if group:
        WHERE SUBSTRING(SKU, 4, 2) = group
    # ... etc

# Search filter
if search:
    WHERE (SKU LIKE '%search%' 
        OR No_2 LIKE '%search%' 
        OR Description LIKE '%search%'
        OR AlternateName LIKE '%search%')
```

**Use Case:**
- Browse products by category
- Filter by specifications (brand, group, color, etc.)
- Search within category

---

### 3️⃣ GET `/list`

**Purpose:** ดึงสินค้าแบบ pagination ทั่วไป (ไม่จำกัดหมวดหมู่)

**Request:**
```
GET /api/items/list?limit=50&offset=0&productType=A&search=profile
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| limit | int | ❌ | Items per page (default: 50) |
| offset | int | ❌ | Pagination offset (default: 0) |
| productType | string | ❌ | Category code (G, A, C, Y, S, E) |
| search | string | ❌ | Search text |
| brand | string | ❌ | Brand filter (LIKE search) |
| category | string | ❌ | Category filter (Product_Group) |
| subCategory | string | ❌ | Sub-category filter (Product_Sub_Group) |
| color | string | ❌ | Color filter (LIKE search) |
| thickness | string | ❌ | Thickness filter (LIKE search) |
| size | string | ❌ | Size filter (LIKE search) |

**Response:**
```json
{
  "items": [
    {
      "sku": "A01010101010101",
      "sku2": "ALU-001",
      "name": "Aluminium Profile 20x20",
      "unit": "เส้น",
      "category": "A",
      "product_group": "Profile",
      "product_sub_group": "Square",
      "alternate_names": "AL-PROFILE-20"
    }
  ],
  "limit": 50,
  "offset": 0,
  "count": 1,
  "total": 500
}
```

**Business Logic:**
- ใช้ LIKE search สำหรับ generic filters
- ไม่ใช้ SKU pattern extraction (ยืดหยุ่นกว่า)
- Support cross-category search

**Use Case:**
- General product listing
- Search across all categories
- Admin product management

---

### 4️⃣ GET `/search`

**Purpose:** ค้นหาสินค้า (Full-Text Search)

**Request:**
```
GET /api/items/search?q=profile
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| q | string | ✅ | Search query (min 1 char) |

**Response:**
```json
[
  {
    "sku": "A01010101010101",
    "sku2": "ALU-001",
    "name": "Aluminium Profile 20x20",
    "inventory": 0,
    "unit": "เส้น",
    "category": "A",
    "isVariant": false,
    "prices": {
      "R1": 150,
      "R2": 160,
      "W1": 140,
      "W2": 145
    },
    "pkg_size": 1,
    "product_weight": 2.5,
    "sqft_sheet": 0,
    "product_group": "Profile",
    "product_sub_group": "Square",
    "alternate_names": "AL-PROFILE-20"
  }
]
```

**Business Logic:**

**Search Strategy:**
```
1. Check if Full-Text Index exists on Item_Master
   
2. If Full-Text Index exists:
   - For alphanumeric query (SKU-like):
     Use CONTAINS with prefix search: "query*"
     Priority: SKU > No_2 > Description > AlternateName
   
   - For text query:
     Use FREETEXT for fuzzy matching
     Also use CONTAINS for SKU pattern

3. If Full-Text Index NOT exists:
   - Fallback to LIKE search
   - Pattern: LIKE '%query%'
   - Priority: SKU LIKE 'query%' > No_2 > Description > AlternateName
```

**Search Priority:**
```
1. SKU exact prefix match (LIKE 'query%')
2. No_2 (alternate SKU)
3. Description (product name)
4. AlternateName (custom name)
```

**Limit:** Top 50 results

**Use Case:**
- Quick product search
- Auto-complete in search box
- Find product by SKU or name

---

### 5️⃣ GET `/{sku}`

**Purpose:** ดึงรายละเอียดสินค้า (Item Detail)

**Request:**
```
GET /api/items/A01010101010101
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sku | string | ✅ | SKU or No_2 |

**Response:**
```json
{
  "sku": "A01010101010101",
  "sku2": "ALU-001",
  "name": "Aluminium Profile 20x20",
  "inventory": 0,
  "unit": "เส้น",
  "category": "A",
  "isVariant": false,
  "prices": {
    "R1": 150,
    "R2": 160,
    "W1": 140,
    "W2": 145
  },
  "pkg_size": 1,
  "product_weight": 2.5,
  "sqft_sheet": 0,
  "product_group": "Profile",
  "product_sub_group": "Square",
  "alternate_names": "AL-PROFILE-20",
  "stock": {
    "branches": [
      {
        "Location_Code": "BKK",
        "quantity": 100
      }
    ],
    "total_quantity": 100
  }
}
```

**Business Logic:**

**Lookup Strategy:**
```
1. Try to find by SKU first
   SELECT * FROM Item_Master WHERE SKU = ?

2. If not found, try by No_2 (alternate SKU)
   SELECT * FROM Item_Master WHERE No_2 = ?

3. If still not found, return 404 error
```

**Data Enrichment:**
```
1. Load from Item_Master + Item_Price
2. Extract category from first letter of SKU
3. For Glass (G): Parse SKU to calculate sqft_sheet
   - Last 6 digits: WWWLLL (width, length in inches)
   - sqft_sheet = (width * length) / 144
4. Enrich with category-specific data (via sku_enricher)
5. Fetch stock from BC Item Ledger API
```

**Stock Calculation:**
```
- Call BC API: fetch_inventory(sku, branch_code)
- Sum Quantity from all ledger entries
- Return only for current employee's branch
```

**Use Case:**
- Product detail page
- Add to cart (get full product info)
- Price review (get all pricing tiers)

---

### 6️⃣ GET `/related/{sku}`

**Purpose:** ดึงสินค้าที่เกี่ยวข้อง (Related Products)

**Request:**
```
GET /api/items/related/A01010101010101?category=A&brand=01&limit=50
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sku | string | ✅ | Reference SKU |
| category | string | ❌ | Category code (for filter) |
| limit | int | ❌ | Max results (default: 50) |
| brand | string | ❌ | Brand filter |
| group | string | ❌ | Group filter |
| subGroup | string | ❌ | Sub-group filter |
| color | string | ❌ | Color filter |
| thickness | string | ❌ | Thickness filter |
| character | string | ❌ | Character filter |

**Response:**
```json
{
  "items": [
    {
      "sku": "A01010101010102",
      "sku2": "ALU-002",
      "name": "Aluminium Profile 20x25",
      "unit": "เส้น",
      "product_group": "Profile",
      "product_sub_group": "Square"
    }
  ],
  "total": 15,
  "product_group": "Profile"
}
```

**Business Logic:**

**Related Items Strategy:**
```
1. Find Product_Group of reference SKU
2. Get all items in same Product_Group
3. Exclude reference SKU itself
4. Apply additional filters (brand, group, color, etc.)
5. Return top N items
```

**Filter Logic:**
- Same as `/categories/{category}/list`
- Uses SKU pattern extraction by category

**Use Case:**
- Cross-sell recommendations
- "Similar products" section
- Product comparison

---

### 7️⃣ GET `/categories/{category}/filter-options`

**Purpose:** ดึง filter options ที่ปรับตาม filter ที่เลือกแล้ว (Cascading Filter)

**Request:**
```
GET /api/items/categories/A/filter-options?brand=01&group=02
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| category | string | ✅ | Category code |
| brand | string | ❌ | Current brand filter (comma-separated) |
| group | string | ❌ | Current group filter (comma-separated) |
| subGroup | string | ❌ | Current sub-group filter |
| color | string | ❌ | Current color filter |
| thickness | string | ❌ | Current thickness filter |
| character | string | ❌ | Current character filter |

**Response:**
```json
{
  "brand": [
    {
      "code": "01",
      "name": "01 - Brand A"
    },
    {
      "code": "02",
      "name": "02 - Brand B"
    }
  ],
  "group": [
    {
      "code": "01",
      "name": "01 - Group 1"
    },
    {
      "code": "02",
      "name": "02 - Group 2"
    }
  ],
  "subGroup": [
    {
      "code": "001",
      "name": "001 - Sub-group A"
    }
  ],
  "color": [
    {
      "code": "01",
      "name": "01 - Black"
    },
    {
      "code": "02",
      "name": "02 - Silver"
    }
  ],
  "thickness": [
    {
      "code": "01",
      "name": "01 - 1mm"
    },
    {
      "code": "02",
      "name": "02 - 2mm"
    }
  ]
}
```

**Business Logic:**

**Cascading Filter Logic:**
```
1. Get current filters (brand, group, color, etc.)
2. For each field:
   - Query distinct values from Item_Master
   - Apply current filters to narrow down options
   - Load mapping table to get display names
   - Return {code, name} pairs

3. Mapping tables:
   - Aluminium_Brand, Aluminium_Group, etc.
   - CLine_Brand, CLine_Group, etc.
   - Accessories_Brand, Accessories_Group, etc.
   - Sealant_Brand, Sealant_Group, etc.
   - Gypsum_Brand, Gypsum_Group, etc.
```

**Example:**
```
User selects: Brand=01, Group=02
System returns:
- subGroup options: only those with Brand=01 AND Group=02
- color options: only those with Brand=01 AND Group=02
- thickness options: only those with Brand=01 AND Group=02
```

**Use Case:**
- Dynamic filter UI
- Prevent invalid filter combinations
- Show only available options

---

### 8️⃣ GET `/{sku}/stock`

**Purpose:** ดึงข้อมูล stock จาก Business Central API

**Request:**
```
GET /api/items/A01010101010101/stock
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sku | string | ✅ | SKU |

**Response:**
```json
{
  "sku": "A01010101010101",
  "Location_Code": "BKK",
  "quantity": 100.5
}
```

**Error Response:**
```json
{
  "sku": "A01010101010101",
  "Location_Code": "BKK",
  "quantity": 0,
  "error": "API connection failed"
}
```

**Business Logic:**

**Stock Fetch Process:**
```
1. Create BCAPIClient instance
2. Call client.fetch_inventory(sku, branch_code)
3. Get Item Ledger Entries from BC API
4. Sum Quantity from all entries
5. Return total quantity for branch

Error Handling:
- If API fails: return quantity=0 with error message
- Log error for debugging
```

**Data Source:**
- Business Central Item Ledger Entries API
- Filtered by: SKU + Branch Location Code
- Aggregated: Sum of all quantities

**Use Case:**
- Display stock availability
- Check stock before adding to cart
- Inventory management

---

## 🔗 HELPER FUNCTIONS

### `row_to_item(row, branch_code, inventory_service)`

**Purpose:** Convert database row to API response format

**Logic:**
```python
1. Extract category from first letter of SKU
2. For Glass (G):
   - Parse last 6 digits of SKU
   - Calculate sqft_sheet = (width * length) / 144
3. Get prices from Item_Price table (R1, R2, W1, W2)
4. Get product weight
5. Check if variant (Variant_Mandatory == 2)
6. Return standardized item dict
```

**Output Format:**
```json
{
  "sku": "string",
  "sku2": "string",
  "name": "string",
  "inventory": 0,
  "unit": "string",
  "category": "string",
  "isVariant": boolean,
  "prices": {
    "R1": number,
    "R2": number,
    "W1": number,
    "W2": number
  },
  "pkg_size": number,
  "product_weight": number,
  "sqft_sheet": number,
  "product_group": "string",
  "product_sub_group": "string",
  "alternate_names": "string"
}
```

---

## 📊 DATABASE TABLES USED

| Table | Purpose | Key Columns |
|-------|---------|------------|
| Item_Master | Product master data | SKU, No_2, Description, Product_Group, Product_Weight, Variant_Mandatory |
| Item_Price | Product pricing by branch | SKU, BranchCode, R1, R2, W1, W2, SDM, PackageSize, AlternateName |

---

## 🔐 SECURITY & AUTHENTICATION

**All endpoints require:**
- ✅ Valid JWT token in Authorization header
- ✅ Branch code extracted from token (via `get_branch_code` dependency)
- ✅ Branch-specific pricing (Item_Price filtered by BranchCode)

**Example:**
```
GET /api/items/categories/list
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📈 PERFORMANCE CONSIDERATIONS

### Optimization Techniques:

1. **Full-Text Index**
   - Faster search (if index exists)
   - Fallback to LIKE if index missing

2. **Pagination**
   - OFFSET/FETCH for large datasets
   - Limit default: 10-50 items

3. **Lazy Loading**
   - Stock fetched separately (not in list)
   - Enrichment only on detail page

4. **Caching**
   - Filter options can be cached
   - Category list rarely changes

5. **Query Optimization**
   - LEFT JOIN with NOLOCK (read-only)
   - Index on SKU, No_2, BranchCode

---

## 🎯 USE CASES BY ENDPOINT

| Endpoint | Frontend Component | Use Case |
|----------|-------------------|----------|
| `/categories/list` | ProductCategorySelector | Show category buttons |
| `/categories/{category}/list` | ProductList | Browse products by category |
| `/list` | ProductList (generic) | General product listing |
| `/search` | ItemPickerModal, GlassPickerModal | Quick product search |
| `/{sku}` | ProductDetail, CartItemRow | Show product details |
| `/related/{sku}` | CrossSellPanel | Show related products |
| `/categories/{category}/filter-options` | DynamicsProductFilter | Dynamic filter UI |
| `/{sku}/stock` | useStep6Stock hook | Check stock availability |

---

## 🚀 EXAMPLE WORKFLOWS

### Workflow 1: Browse Glass Products
```
1. GET /api/items/categories/list
   → Show [G, A, C, Y, S, E] buttons

2. User clicks "G" (Glass)
   → GET /api/items/categories/G/list?limit=10
   → Show 10 glass products

3. User filters by size
   → GET /api/items/categories/G/filter-options?size=14x40
   → Show available sizes

4. User clicks product
   → GET /api/items/G01010010102014040
   → Show product detail + stock
```

### Workflow 2: Search Product
```
1. User types "profile" in search box
   → GET /api/items/search?q=profile
   → Show top 50 matching products

2. User clicks result
   → GET /api/items/A01010101010101
   → Show product detail + stock
```

### Workflow 3: Add to Cart
```
1. User adds item to cart
   → GET /api/items/{sku}/stock
   → Check availability

2. System shows stock info
   → Display quantity available
```

---

## 📝 NOTES

- **Category Extraction:** Uses first letter of SKU (not Inventory_Posting_Group)
- **Glass Sizing:** Parsed from last 6 digits of SKU
- **Stock:** Always returns 0 in list (fetched separately for performance)
- **Pricing:** Branch-specific (filtered by BranchCode)
- **Variant:** Determined by Variant_Mandatory field (2 = has variant)
- **Search:** Supports both SKU and text search with different strategies
