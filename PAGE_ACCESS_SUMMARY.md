# สรุปสิทธิ์การเข้าถึงแต่ละหน้า

## 1. สร้างใบเสนอราคา (Create Quote)
**หน้า:** `/create-quote`

**สิทธิ์ที่เข้าได้:**
- Sales
- Sales_Project
- ZM (Zone Manager)
- PM (Product Manager)
- Admin
- RM (Regional Manager)
- PM_ALUMINIUM
- PM_CLINE
- PM_EQUIPMENT
- PM_GLASS
- PM_GYPSUM
- PM_SEALANT
- CEO

**จำนวนสิทธิ์:** 13 สิทธิ์

---

## 2. สร้างรหัสโครงการ (Project Price)
**หน้า:** `/project-price`

**สิทธิ์ที่เข้าได้:**
- Admin
- ZM (Zone Manager)
- Sales_Project
- RM (Regional Manager)
- PM (Product Manager)
- PM_ALUMINIUM
- PM_CLINE
- PM_EQUIPMENT
- PM_GLASS
- PM_GYPSUM
- PM_SEALANT
- CEO
- SDM (Sales Development Manager)

**จำนวนสิทธิ์:** 13 สิทธิ์

---

## 3. หน้าอนุมัติราคา (Special Price Approval)
**หน้า:** `/special-price-approval`

**สิทธิ์ที่เข้าได้:**
- ZM (Zone Manager)
- RM (Regional Manager)
- SDM (Sales Development Manager)
- PM (Product Manager)
- Admin
- PM_ALUMINIUM
- PM_CLINE
- PM_EQUIPMENT
- PM_GLASS
- PM_GYPSUM
- PM_SEALANT
- CEO

**จำนวนสิทธิ์:** 12 สิทธิ์

---

## 4. เพิ่มราคา (Update Price)
**หน้า:** `/update-price`

**สิทธิ์ที่เข้าได้:**
- PM (Product Manager)
- Admin
- PM_ALUMINIUM
- PM_CLINE
- PM_EQUIPMENT
- PM_GLASS
- PM_GYPSUM
- PM_SEALANT

**จำนวนสิทธิ์:** 8 สิทธิ์

---

## สรุปสิทธิ์ทั้งหมด

| สิทธิ์ | Create Quote | Project Price | Special Price Approval | Update Price |
|-------|:---:|:---:|:---:|:---:|
| Sales | ✓ | ✗ | ✗ | ✗ |
| Sales_Project | ✓ | ✓ | ✗ | ✗ |
| ZM | ✓ | ✓ | ✓ | ✗ |
| PM | ✓ | ✓ | ✓ | ✓ |
| Admin | ✓ | ✓ | ✓ | ✓ |
| RM | ✓ | ✓ | ✓ | ✗ |
| PM_ALUMINIUM | ✓ | ✓ | ✓ | ✓ |
| PM_CLINE | ✓ | ✓ | ✓ | ✓ |
| PM_EQUIPMENT | ✓ | ✓ | ✓ | ✓ |
| PM_GLASS | ✓ | ✓ | ✓ | ✓ |
| PM_GYPSUM | ✓ | ✓ | ✓ | ✓ |
| PM_SEALANT | ✓ | ✓ | ✓ | ✓ |
| CEO | ✓ | ✓ | ✓ | ✗ |
| SDM | ✗ | ✓ | ✓ | ✗ |

---

## หมายเหตุ

- **Sales:** สามารถสร้างใบเสนอราคาได้เท่านั้น
- **PM (Product Manager):** สามารถเข้าได้ทุกหน้า
- **Admin:** สามารถเข้าได้ทุกหน้า
- **PM_* (Specialized PM):** สามารถเข้าได้ทุกหน้า (เหมือน PM)
- **CEO:** สามารถเข้าได้ 3 หน้า (ไม่มี Update Price)
- **SDM:** สามารถเข้าได้ 2 หน้า (Project Price และ Special Price Approval)

---

## หน้าที่ยังไม่มีการกำหนดสิทธิ์

- Dashboard
- Promotion Management
- Admin Config
- อื่นๆ (ถ้ามี)

หน้าเหล่านี้อาจไม่มีการตรวจสอบสิทธิ์ หรือใช้การตรวจสอบแบบอื่น
