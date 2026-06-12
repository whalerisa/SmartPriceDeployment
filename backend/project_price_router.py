from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from config.db_mssql import get_mssql_conn
from branch_region_mapping import BRANCH_REGION_MAP
import jwt
import os

router = APIRouter(prefix="/api/project-prices", tags=["project-prices"])

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-this")
JWT_ALG = "HS256"

def get_branch_code_from_numeric(numeric_code: str) -> str:
    """
    Map numeric branch code (e.g., 056903002) to 2-letter code (e.g., AY)
    
    Pattern analysis:
    - 05 = region code
    - 6903 = branch identifier  
    - 002 = sub-branch
    
    Uses BRANCH_REGION_MAP to dynamically build the mapping
    """
    if not numeric_code or len(numeric_code) < 2:
        return 'XX'
    
    # ⭐ Build mapping dynamically from BRANCH_REGION_MAP
    # Extract numeric prefix (first 2 digits) from branch codes
    numeric_to_letter = {}
    for branch_code in BRANCH_REGION_MAP.keys():
        # Extract numeric prefix from branch code (e.g., "00TR" -> "00", "12CM" -> "12")
        if len(branch_code) >= 4:
            numeric_prefix = branch_code[:2]
            letter_suffix = branch_code[2:]
            numeric_to_letter[numeric_prefix] = letter_suffix
    
    # Extract first 2 digits from numeric code
    prefix = numeric_code[:2]
    
    if prefix in numeric_to_letter:
        return numeric_to_letter[prefix]
    
    # Fallback: return last 2 characters uppercase
    return numeric_code[-2:].upper()

def get_branch_code_from_db(numeric_code: str) -> str:
    """
    Get 2-letter branch code using the mapping function
    """
    return get_branch_code_from_numeric(numeric_code)

def auto_expire_projects(cursor) -> int:
    """
    เปลี่ยนสถานะโครงการที่เลยวันสิ้นสุดให้เป็น 'expired' อัตโนมัติ

    เงื่อนไข: status = 'active' และ price_end_date < วันนี้ (วันสิ้นสุดถือว่ายังใช้ได้)
    คืนค่าจำนวนแถวที่ถูกอัปเดต
    """
    cursor.execute("""
        UPDATE Project_Price_Header
        SET status = 'expired', updated_at = GETDATE()
        WHERE status = 'active'
        AND price_end_date < CAST(GETDATE() AS DATE)
    """)
    updated = cursor.rowcount
    if updated and updated > 0:
        print(f"⏰ [AUTO EXPIRE] อัปเดตโครงการหมดอายุ {updated} รายการ")
    return updated

def get_current_user_from_token(authorization: str = Header(None)) -> dict:
    """Extract user info from JWT token"""
    if not authorization:
        return {"username": "anonymous", "id": None, "employee_id": None}
    
    try:
        token = authorization.replace("Bearer ", "").strip()
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        # JWT token ใช้ "sub" สำหรับ employee ID
        employee_id = payload.get("sub") or payload.get("id") or payload.get("employee_id")
        return {
            "username": payload.get("name", "unknown"),
            "id": employee_id,
            "employee_id": employee_id,
            "branchId": payload.get("branchId"),
            "branch_code": payload.get("branchId") or payload.get("branch_code")
        }
    except Exception as e:
        print(f"❌ Error decoding JWT token: {e}")
        return {"username": "anonymous", "id": None, "employee_id": None}

class ProjectPriceLine(BaseModel):
    sku: str
    product_name: Optional[str] = None
    unit: Optional[str] = None
    price: float
    quantity: Optional[float] = None

class ProjectPriceCreate(BaseModel):
    project_code: str
    project_name: Optional[str] = None
    customer_code: Optional[str] = None
    customer_name: Optional[str] = None
    branch_code: Optional[str] = None  # สาขาที่พนักงานเลือก (บันทึกลง database)
    price_start_date: str
    price_end_date: str
    request_by: Optional[str] = None
    request_date: Optional[str] = None
    remark: Optional[str] = None
    created_by_employee_code: Optional[str] = None
    price_mode: Optional[str] = None  # price_mode flag (project/branch/customer)
    items: List[ProjectPriceLine] = []

@router.post("/")
async def create_project_price(project: ProjectPriceCreate, authorization: str = Header(None)):
    """สร้างราคาโครงการใหม่ (Manager เท่านั้น)"""
    current_user = get_current_user_from_token(authorization)
    conn = None
    
    try:
        # Validate วันที่สิ้นสุดต้องมากกว่าวันที่เริ่มใช้ราคา
        if project.price_end_date and project.price_start_date:
            if project.price_end_date <= project.price_start_date:
                raise HTTPException(
                    status_code=400, 
                    detail="วันที่สิ้นสุดต้องมากกว่าวันที่เริ่มใช้ราคา"
                )
        
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # ⭐ ดึง branch code จาก employee
        employee_branch = current_user.get('branch_code', '00TR')
        
        # ⭐ ตรวจสอบ mode จาก price_mode flag
        mode = project.price_mode or 'project'  # default
        
        # ⭐ แปลง branch_code ถ้าเป็นรหัสตัวเลข (เช่น 056903002) เป็น 2 ตัวอักษร
        if project.branch_code and len(project.branch_code) > 4:
            project.branch_code = get_branch_code_from_db(project.branch_code)
        
        print(f"🏗️ [CREATE PROJECT PRICE] Mode: {mode}, Employee Branch: {employee_branch}, Selected Branch: {project.branch_code}")
        
        # ⭐ ตรวจสอบว่าเป็น manual mode หรือไม่
        # ⭐ project_code_mode มีผลเฉพาะโหมด 'project' เท่านั้น
        # โหมด 'branch' และ 'customer' ใช้ running number เสมอ
        project_code_mode = os.getenv("PROJECT_CODE_MODE", "auto")
        
        if project_code_mode == "manual" and mode == "project" and project.project_code:
            # Manual mode: ใช้ project_code ที่ผู้ใช้กรอกมา (เฉพาะโหมดโครงการ)
            generated_code = project.project_code.strip()
            
            # ตรวจสอบว่า project_code ซ้ำหรือไม่
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM Project_Price_Header
                WHERE project_code = ?
            """, (generated_code,))
            if cursor.fetchone()[0] > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Project Code '{generated_code}' มีอยู่ในระบบแล้ว กรุณาใช้รหัสอื่น"
                )
            
            print(f"🏗️ [CREATE PROJECT PRICE] Manual Mode - Using provided code: {generated_code}")
        else:
            # Auto mode: สร้างเลขที่เอกสารอัตโนมัติ
            now = datetime.now()
            buddhist_year = str(now.year + 543)[-2:]
            month = str(now.month).zfill(2)
            
            if mode == 'customer':
                # Customer mode: YYMMCUSTCODE (ไม่มี running number)
                prefix = f"{buddhist_year}{month}{project.customer_code}"
            elif mode == 'branch':
                # Branch mode: BRYYMMXXX (BR = branch code 2 ตัวอักษรของคนสร้าง)
                branch_code = employee_branch[-2:].upper() if employee_branch else 'XX'
                prefix = f"{branch_code}{buddhist_year}{month}"
            else:  # project
                # Project mode: PJYYMMXXX (PJ = Project, ไม่มี branch)
                prefix = f"PJ{buddhist_year}{month}"
            
            # ⭐ Customer mode ไม่ต้องมี running number
            if mode == 'customer':
                generated_code = prefix
            else:
                # นับจำนวนเอกสารที่มี prefix เดียวกัน
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM Project_Price_Header
                    WHERE project_code LIKE ?
                """, (f"{prefix}%",))
                count = cursor.fetchone()[0]
                running_number = str(count + 1).zfill(3)
                generated_code = f"{prefix}{running_number}"
            
            print(f"🏗️ [CREATE PROJECT PRICE] Auto Mode - Generated Code: {generated_code}")
        
        # สร้าง Project Price Header
        cursor.execute("""
            INSERT INTO Project_Price_Header 
            (project_code, project_name, customer_code, customer_name, branch_code,
             price_start_date, price_end_date, request_by, request_date, status, remark, created_at, updated_at, CreatedByEmployeeCode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, GETDATE(), GETDATE(), ?)
        """, (
            generated_code,  # ใช้เลขที่ที่สร้างใหม่
            project.project_name,
            project.customer_code,
            project.customer_name,
            project.branch_code,
            project.price_start_date,
            project.price_end_date,
            project.request_by,
            project.request_date or datetime.now().strftime('%Y-%m-%d'),
            project.remark,
            # ✅ ลำดับความสำคัญ: created_by_employee_code จาก payload → employee_id จาก token → id จาก token
            project.created_by_employee_code or current_user.get('employee_id') or current_user.get('id')
        ))
        
        # ดึง ID ที่เพิ่งสร้าง
        cursor.execute("SELECT @@IDENTITY AS id")
        project_id = cursor.fetchone()[0]
        
        print(f"✅ [CREATE PROJECT PRICE] Created project with ID: {project_id}, Code: {generated_code}, Created by: {current_user.get('employee_id') or current_user.get('id') or 'Unknown'}")
        
        # สร้าง Project Price Lines
        for item in project.items:
            cursor.execute("""
                INSERT INTO Project_Price_Line 
                (project_id, sku, product_name, unit, price, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                item.sku,
                item.product_name,
                item.unit,
                item.price,
                item.quantity
            ))
            print(f"  ➕ Added item: {item.sku} - {item.price}")
        
        conn.commit()
        return {"success": True, "project_id": int(project_id), "project_code": generated_code}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [CREATE PROJECT PRICE] Error: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.get("/next-code/{mode}")
async def get_next_project_code(mode: str, branch_code: Optional[str] = None, customer_code: Optional[str] = None):
    """ดึงรหัสโครงการถัดไปตามโหมด"""
    conn = None
    
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        from datetime import datetime
        now = datetime.now()
        buddhist_year = str(now.year + 543)[-2:]  # YY (พ.ศ.)
        month = str(now.month).zfill(2)  # MM
        
        if mode == 'project':
            # หา running number ถัดไปสำหรับ PJ
            prefix = f"PJ{buddhist_year}{month}"
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM Project_Price_Header
                WHERE project_code LIKE ?
            """, (f"{prefix}%",))
            result = cursor.fetchone()
            count = (result[0] if result else 0) + 1
            run_num = str(count).zfill(3)
            next_code = f"{prefix}{run_num}"
            return {"next_code": next_code}
        
        elif mode == 'branch':
            if not branch_code:
                raise HTTPException(status_code=400, detail="branch_code required for branch mode")
            
            # เอาตัวอักษรสองตัวหลังสุดของ Code เช่น "03TS" → "TS"
            branch_prefix = branch_code[-2:].upper()
            
            # หา running number ถัดไปสำหรับ BR
            prefix = f"{branch_prefix}{buddhist_year}{month}"
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM Project_Price_Header
                WHERE project_code LIKE ?
            """, (f"{prefix}%",))
            result = cursor.fetchone()
            count = (result[0] if result else 0) + 1
            run_num = str(count).zfill(3)
            next_code = f"{prefix}{run_num}"
            return {"next_code": next_code}
        
        elif mode == 'customer':
            if not customer_code:
                raise HTTPException(status_code=400, detail="customer_code required for customer mode")
            
            # หา running number ถัดไปสำหรับ CUSTOMER
            prefix = f"{buddhist_year}{month}{customer_code}"
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM Project_Price_Header
                WHERE project_code LIKE ?
            """, (f"{prefix}%",))
            result = cursor.fetchone()
            count = (result[0] if result else 0) + 1
            next_code = prefix
            return {"next_code": next_code}
        
        else:
            raise HTTPException(status_code=400, detail="Invalid mode")
    
    except Exception as e:
        print(f"❌ [NEXT CODE API] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if conn:
            conn.close()

@router.get("/")
async def get_project_prices(status: Optional[str] = None, branch: Optional[str] = None, employee_code: Optional[str] = None):
    """ดึงรายการราคาโครงการทั้งหมด
    
    Parameters:
    - status: Filter by status (optional)
    - branch: Filter by branch code (optional)
    - employee_code: Filter by employee who created the project (optional)
    """
    conn = None
    
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # ⭐ อัปเดตโครงการที่หมดอายุให้เป็น 'expired' อัตโนมัติก่อนดึงข้อมูล
        if auto_expire_projects(cursor) > 0:
            conn.commit()
        
        query = "SELECT * FROM Project_Price_Header WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if branch:
            query += " AND branch_code = ?"
            params.append(branch)
        
        if employee_code:
            query += " AND CreatedByEmployeeCode = ?"
            params.append(employee_code)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        columns = [column[0] for column in cursor.description]
        projects = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        result = []
        for proj in projects:
            # ดึง Project Price Lines
            cursor.execute("""
                SELECT * FROM Project_Price_Line 
                WHERE project_id = ?
            """, (proj['project_id'],))
            line_columns = [column[0] for column in cursor.description]
            lines = [dict(zip(line_columns, row)) for row in cursor.fetchall()]
            
            result.append({
                "project_id": proj['project_id'],
                "project_code": proj['project_code'],
                "project_name": proj['project_name'],
                "customer_code": proj['customer_code'],
                "customer_name": proj['customer_name'],
                "branch_code": proj['branch_code'],
                "price_start_date": str(proj['price_start_date']),
                "price_end_date": str(proj['price_end_date']),
                "request_by": proj['request_by'],
                "request_date": str(proj['request_date']) if proj['request_date'] else None,
                "status": proj['status'],
                "remark": proj['remark'],
                "created_at": str(proj['created_at']),
                "created_by_employee_code": proj.get('CreatedByEmployeeCode'),
                "items": lines
            })
        
        return result
    
    finally:
        if conn:
            conn.close()

@router.get("/active-by-customer-sku")
async def get_active_project_price(customerCode: str, sku: str):
    """ดึงราคาโครงการที่ active สำหรับลูกค้าและ SKU"""
    conn = None
    
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        print(f"🏗️ [PROJECT PRICE API] Customer: {customerCode}, SKU: {sku}")
        
        query = """
            SELECT 
                ph.project_id, ph.project_code, ph.project_name,
                pl.sku, pl.product_name, pl.unit, pl.price, pl.quantity
            FROM Project_Price_Header ph
            JOIN Project_Price_Line pl ON ph.project_id = pl.project_id
            WHERE ph.status = 'active'
            AND ph.price_start_date <= ?
            AND ph.price_end_date >= ?
            AND ph.customer_code = ?
            AND pl.sku = ?
        """
        
        cursor.execute(query, [today, today, customerCode, sku])
        
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        print(f"📦 [PROJECT PRICE API] Found {len(results)} project prices")
        
        return results
    
    except Exception as e:
        print(f"❌ [PROJECT PRICE API] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if conn:
            conn.close()

@router.get("/by-customer")
async def get_projects_by_customer(customerCode: str):
    """ดึงรายการโครงการทั้งหมดของลูกค้า (active เท่านั้น) พร้อมรายการสินค้า"""
    conn = None
    
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        today = datetime.now().date().isoformat()
        
        print(f"🏗️ [PROJECT LIST API] Customer: {customerCode}, Today: {today}")
        
        # ดึงโครงการทั้งหมดของลูกค้าก่อน (ไม่กรองวันที่)
        query_all = """
            SELECT 
                project_id, project_code, project_name, customer_code,
                price_start_date, price_end_date, status
            FROM Project_Price_Header
            WHERE customer_code = ?
        """
        cursor.execute(query_all, [customerCode])
        all_projects = cursor.fetchall()
        print(f"📋 [PROJECT LIST API] All projects for {customerCode}: {len(all_projects)}")
        for p in all_projects:
            print(f"  - {p[1]}: status={p[6]}, dates={p[4]} to {p[5]}")
        
        # ดึงโครงการที่ active และอยู่ในช่วงเวลา
        query = """
            SELECT 
                project_id, project_code, project_name,
                price_start_date, price_end_date, remark, status
            FROM Project_Price_Header
            WHERE status = 'active'
            AND price_start_date <= ?
            AND price_end_date >= ?
            AND customer_code = ?
            ORDER BY project_name
        """
        
        cursor.execute(query, [today, today, customerCode])
        
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # แปลง date เป็น string
        for r in results:
            if r.get('price_start_date'):
                r['price_start_date'] = str(r['price_start_date'])
            if r.get('price_end_date'):
                r['price_end_date'] = str(r['price_end_date'])
            
            # ⭐ ดึงรายการสินค้าของโครงการ
            items_query = """
                SELECT 
                    sku, product_name, unit, price, quantity
                FROM Project_Price_Line
                WHERE project_id = ?
                ORDER BY product_name
            """
            cursor.execute(items_query, [r['project_id']])
            item_columns = [column[0] for column in cursor.description]
            items = [dict(zip(item_columns, row)) for row in cursor.fetchall()]
            
            r['items'] = items
            print(f"📦 [PROJECT LIST API] Project {r['project_code']}: {len(items)} items")
        
        print(f"📦 [PROJECT LIST API] Found {len(results)} active projects in date range")
        
        return results
    
    except Exception as e:
        print(f"❌ [PROJECT LIST API] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if conn:
            conn.close()

@router.get("/project-prices/{project_id}")
async def get_project_prices_by_id(project_id: int):
    """ดึงราคาสินค้าทั้งหมดในโครงการ"""
    conn = None
    
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        print(f"🏗️ [PROJECT PRICES API] Project ID: {project_id}")
        
        query = """
            SELECT 
                sku, product_name, unit, price, quantity
            FROM Project_Price_Line
            WHERE project_id = ?
        """
        
        cursor.execute(query, [project_id])
        
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        print(f"📦 [PROJECT PRICES API] Found {len(results)} items")
        
        return results
    
    except Exception as e:
        print(f"❌ [PROJECT PRICES API] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if conn:
            conn.close()

@router.put("/{project_id}/status")
async def update_project_status(
    project_id: int, 
    status: str,
    authorization: str = Header(None)
):
    """อัพเดทสถานะราคาโครงการ (active/expired/canceled)"""
    current_user = get_current_user_from_token(authorization)
    if status not in ['active', 'expired', 'canceled']:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    conn = None
    
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # ⭐ ตรวจสอบสถานะปัจจุบัน: ถ้าหมดอายุแล้ว ห้ามเปลี่ยนกลับเป็น active/canceled
        cursor.execute("""
            SELECT status FROM Project_Price_Header WHERE project_id = ?
        """, (project_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")
        
        current_status = row[0]
        # ⭐ โครงการหมดอายุห้ามกลับเป็น active แต่ยังยกเลิก (canceled) เพื่อซ่อนออกจากหน้าจอได้
        if current_status == 'expired' and status == 'active':
            raise HTTPException(
                status_code=400,
                detail="โครงการหมดอายุแล้ว ไม่สามารถเปลี่ยนกลับเป็น active ได้"
            )
        
        cursor.execute("""
            UPDATE Project_Price_Header 
            SET status = ?, updated_at = GETDATE()
            WHERE project_id = ?
        """, (status, project_id))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"success": True}
    
    finally:
        if conn:
            conn.close()

@router.put("/{project_id}")
async def update_project_price(project_id: int, project: ProjectPriceCreate, authorization: str = Header(None)):
    """อัพเดทราคาโครงการ """
    current_user = get_current_user_from_token(authorization)
    conn = None
    
    try:
        # Validate วันที่สิ้นสุดต้องมากกว่าวันที่เริ่มใช้ราคา
        if project.price_end_date and project.price_start_date:
            if project.price_end_date <= project.price_start_date:
                raise HTTPException(
                    status_code=400, 
                    detail="วันที่สิ้นสุดต้องมากกว่าวันที่เริ่มใช้ราคา"
                )
        
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        print(f"🔧 [UPDATE PROJECT PRICE] Project ID: {project_id}, Code: {project.project_code}")
        
        # อัพเดท Project Price Header
        cursor.execute("""
            UPDATE Project_Price_Header 
            SET project_name = ?, customer_code = ?, customer_name = ?, branch_code = ?,
                price_start_date = ?, price_end_date = ?, request_by = ?, request_date = ?, 
                remark = ?, updated_at = GETDATE()
            WHERE project_id = ?
        """, (
            project.project_name,
            project.customer_code,
            project.customer_name,
            project.branch_code,
            project.price_start_date,
            project.price_end_date,
            project.request_by,
            project.request_date or datetime.now().strftime('%Y-%m-%d'),
            project.remark,
            project_id
        ))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        
        print(f"✅ [UPDATE PROJECT PRICE] Updated header for project ID: {project_id}")
        
        # ลบ Project Price Lines เดิม
        cursor.execute("DELETE FROM Project_Price_Line WHERE project_id = ?", (project_id,))
        print(f"🗑️ [UPDATE PROJECT PRICE] Deleted old items")
        
        # สร้าง Project Price Lines ใหม่
        for item in project.items:
            cursor.execute("""
                INSERT INTO Project_Price_Line 
                (project_id, sku, product_name, unit, price, quantity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                item.sku,
                item.product_name,
                item.unit,
                item.price,
                item.quantity
            ))
            print(f"  ➕ Added item: {item.sku} - {item.price}")
        
        conn.commit()
        return {"success": True, "project_id": project_id}
    
    except Exception as e:
        print(f"❌ [UPDATE PROJECT PRICE] Error: {str(e)}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.delete("/{project_id}")
async def delete_project_price(project_id: int, authorization: str = Header(None)):
    """ลบราคาโครงการ"""
    current_user = get_current_user_from_token(authorization)
    conn = None
    
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM Project_Price_Line WHERE project_id = ?", (project_id,))
        cursor.execute("DELETE FROM Project_Price_Header WHERE project_id = ?", (project_id,))
        
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {"success": True}
    
    finally:
        if conn:
            conn.close()

@router.get("/customer/{customer_code}/all")
async def get_all_projects_by_customer(customer_code: str):
    """
    ดึงรายการโครงการทั้งหมดของลูกค้า (ไม่กรองสถานะหรือวันที่)
    
    Parameters:
    - customer_code: รหัสลูกค้า (เช่น 08015AY)
    
    Response:
    [
        {
            "project_code": "PJ2501001",
            "project_name": "โครงการคอนโดXXX",
            "customer_code": "08015AY",
            "customer_name": "บริษัท ABC",
            "branch_code": "BKK",
            "request_by": "สมชาย",
            "remark": "หมายเหตุ"
        },
        ...
    ]
    """
    conn = None
    
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        print(f"🔍 [GET ALL PROJECTS] Customer: {customer_code}")
        
        # ดึงโครงการทั้งหมดของลูกค้า (ไม่กรองสถานะหรือวันที่)
        query = """
            SELECT 
                project_code, project_name, customer_code, customer_name,
                branch_code, request_by, remark
            FROM Project_Price_Header
            WHERE customer_code = ?
            ORDER BY project_code DESC
        """
        
        cursor.execute(query, [customer_code])
        
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        print(f"📦 [GET ALL PROJECTS] Found {len(results)} projects for customer {customer_code}")
        
        return results
    
    except Exception as e:
        print(f"❌ [GET ALL PROJECTS] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if conn:
            conn.close()

@router.get("/branch/{branch_code}/all")
async def get_all_projects_by_branch(branch_code: str):
    """
    ดึงรายการโครงการทั้งหมดของสาขา (ไม่กรองสถานะหรือวันที่)
    
    Parameters:
    - branch_code: รหัสสาขา (เช่น BKK, CNX)
    
    Response:
    [
        {
            "project_code": "PJ2501001",
            "project_name": "โครงการคอนโดXXX",
            "customer_code": "08015AY",
            "customer_name": "บริษัท ABC",
            "branch_code": "BKK",
            "request_by": "สมชาย",
            "remark": "หมายเหตุ"
        },
        ...
    ]
    """
    conn = None
    
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        print(f"🔍 [GET ALL PROJECTS BY BRANCH] Branch: {branch_code}")
        
        # ดึงโครงการทั้งหมดของสาขา (ไม่กรองสถานะหรือวันที่)
        query = """
            SELECT 
                project_code, project_name, customer_code, customer_name,
                branch_code, request_by, remark
            FROM Project_Price_Header
            WHERE branch_code = ?
            ORDER BY project_code DESC
        """
        
        cursor.execute(query, [branch_code])
        
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        print(f"📦 [GET ALL PROJECTS BY BRANCH] พบ {len(results)} โครงการสำหรับสาขา {branch_code}")
        
        return results
    
    except Exception as e:
        print(f"❌ [GET ALL PROJECTS BY BRANCH] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if conn:
            conn.close()
