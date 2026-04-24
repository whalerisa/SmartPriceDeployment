# login.py — ใช้ Employee API
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import jwt, os, httpx

from config.config_external_api import EMP_API_URL, EMP_API_HEADERS
from role_mapping import get_all_role_codes, get_role_display_name, get_thai_role_name
from branch_region_mapping import BRANCH_REGION_MAP, get_region_from_branch

router = APIRouter(prefix="/login", tags=["auth"])

# === CONFIG ===
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-this")
JWT_ALG = "HS256"
JWT_EXPIRE_HOURS = 12


# === SCHEMA ===
class LoginRequest(BaseModel):
    employeeCode: str


class ManualLoginRequest(BaseModel):
    employeeCode: str
    role: str
    branchId: str
    password: str


# === HELPER ===
async def load_employee(code: str):
    """
    ดึงข้อมูลพนักงานจาก API และเพิ่มข้อมูล role จาก employees.json
    รองรับพนักงานที่มีหลายสาขา
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                EMP_API_URL,
                headers=EMP_API_HEADERS,
            )
            response.raise_for_status()
            data = response.json()
            
            # API ส่งมาเป็น dict with 'data' key
            if isinstance(data, dict) and 'data' in data:
                employees = data['data']
            elif isinstance(data, list):
                employees = data
            else:
                employees = []
            
            print(f"🔍 [LOAD_EMPLOYEE] Looking for employee code: {code}")
            print(f"   Total employees from API: {len(employees)}")
            
            # หาพนักงานที่ตรงกับ code (อาจมีหลายรายการสำหรับสาขาต่างๆ)
            matching_employees = []
            for emp in employees:
                emp_code = str(emp.get("EmpCode", "")).strip()
                if emp_code.lower() == code.lower():
                    matching_employees.append(emp)
            
            if not matching_employees:
                print(f"   ❌ Employee code {code} not found in API response")
                return None
            
            # ใช้ record แรก เพื่อดึงข้อมูลพื้นฐาน
            first_emp = matching_employees[0]
            emp_name = str(first_emp.get("EmpName", "")).strip()
            
            print(f"   ✅ Found {len(matching_employees)} record(s) for employee:")
            print(f"      Code: {code}")
            print(f"      Name: {emp_name}")
            
            # เก็บสาขาทั้งหมด
            branches = []
            for emp in matching_employees:
                emp_brch = str(emp.get("EmpBrchCode", "")).strip()
                if emp_brch:
                    branches.append(emp_brch)
                    print(f"      Branch: {emp_brch}")
            
            # ถ้าไม่มีสาขา ให้ใช้ default
            if not branches:
                branches = [None]
            
            # ⭐ ลำดับความสำคัญของสาขา: 00TR > 90HO > อื่นๆ
            # ให้ 00TR อยู่ด้านหน้า (primary) ถ้ามี
            priority_order = ["00TR", "90HO"]
            sorted_branches = []
            
            # เพิ่มสาขาตามลำดับความสำคัญ
            for priority_branch in priority_order:
                if priority_branch in branches:
                    sorted_branches.append(priority_branch)
                    branches.remove(priority_branch)
            
            # เพิ่มสาขาที่เหลือ
            sorted_branches.extend(branches)
            branches = sorted_branches
            
            print(f"      Sorted branches (priority: 00TR > 90HO): {branches}")
            
            emp_data = {
                "id": code,
                "name": emp_name,
                "branchId": branches[0],  # ใช้สาขาแรกเป็น primary
                "branches": branches,     # เก็บสาขาทั้งหมด
            }
            
            # เพิ่มข้อมูล role และ region จาก employees.json
            role_info = get_employee_role(code)
            if role_info:
                emp_data["role"] = role_info.get("role")
                emp_data["region"] = role_info.get("region")
            
            return emp_data
            
    except Exception as e:
        print(f"❌ Error fetching employee from API: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_employee_role(employee_id: str):
    """
    ดึงข้อมูล role และ region จาก employees.json
    """
    import json
    import os
    try:
        # Try multiple possible locations for the employees file
        possible_paths = [
            "employees.json",
            os.path.join("backend", "employees.json"),
            os.path.join(os.path.dirname(__file__), "employees.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "employees.json"),
            os.path.join(os.getcwd(), "employees.json"),
            os.path.join(os.getcwd(), "backend", "employees.json"),
        ]
        
        employees_file = None
        for path in possible_paths:
            if os.path.exists(path):
                employees_file = path
                break
        
        if not employees_file:
            print(f"❌ employees.json not found in any of these locations: {possible_paths}")
            return None
        
        with open(employees_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            employees = data.get("employees", [])
            
            for emp in employees:
                if str(emp.get("employee_id")) == str(employee_id):
                    print(f"✅ Found employee {employee_id} in {employees_file}")
                    return {
                        "role": emp.get("role"),
                        "region": emp.get("region")
                    }
            return None
    except Exception as e:
        print(f"❌ Error reading employees.json: {e}")
        return None


# === INIT ROUTE (อ่าน UXP token และสร้าง auth_token) ===
@router.post("/init")
async def init_from_uxp(request: Request, response: Response):
    """
    อ่าน UXP token จาก cookie และสร้าง auth_token cookie ของ Smart Pricing
    """
    # ลองหา UXP token จาก cookie
    uxp_token = None
    possible_names = ['token', 'uxp_token', 'access_token', 'jwt']
    
    for name in possible_names:
        token = request.cookies.get(name)
        if token:
            uxp_token = token
            print(f"✅ Found UXP token in cookie: {name}")
            break
    
    if not uxp_token:
        raise HTTPException(status_code=401, detail="ไม่พบ UXP token - กรุณา login ผ่าน UXP Portal")
    
    try:
        # Decode UXP token
        payload = jwt.decode(uxp_token, options={"verify_signature": False})
        print(f"UXP Token Payload: {payload}")
        
        # ดึงรหัสพนักงาน
        emp_code = (
            payload.get("sub") or 
            payload.get("employeeCode") or 
            payload.get("employee_id") or 
            payload.get("id") or 
            payload.get("empCode")
        )
        
        if not emp_code:
            raise HTTPException(status_code=400, detail="ไม่พบรหัสพนักงานใน UXP token")
        
        # ⭐ ดึง branches จาก UXP token
        uxp_branches = payload.get("branches", [])
        print(f"✅ Branches from UXP token: {uxp_branches}")
        
        # ดึงข้อมูลพนักงานจาก API
        emp = await load_employee(str(emp_code))
        if not emp:
            raise HTTPException(status_code=401, detail=f"ไม่พบข้อมูลพนักงาน: {emp_code}")
        
        # ⭐ ถ้า UXP token มี branches ให้ใช้แทน (และเรียงลำดับความสำคัญ)
        if uxp_branches:
            # ลำดับความสำคัญของสาขา: 00TR > 90HO > อื่นๆ
            priority_order = ["00TR", "90HO"]
            sorted_branches = []
            
            # เพิ่มสาขาตามลำดับความสำคัญ
            remaining_branches = list(uxp_branches)
            for priority_branch in priority_order:
                if priority_branch in remaining_branches:
                    sorted_branches.append(priority_branch)
                    remaining_branches.remove(priority_branch)
            
            # เพิ่มสาขาที่เหลือ
            sorted_branches.extend(remaining_branches)
            
            emp["branches"] = sorted_branches
            emp["branchId"] = sorted_branches[0]  # ใช้สาขาแรก (หลังเรียงลำดับ) เป็น primary
            print(f"✅ Updated branches from UXP token: {sorted_branches}")
        
        # ⭐ ถ้ามีสาขา 90HO และ 00TR ให้ใช้ 00TR โดยอัตโนมัติ
        branches = emp.get("branches", [])
        if "90HO" in branches and "00TR" in branches:
            print(f"✅ Employee {emp_code} has 90HO and 00TR, auto-selecting 00TR")
            emp["branchId"] = "00TR"
            # ไม่ต้อง return เพื่อให้ผ่านไปสร้าง token ด้านล่าง
        elif len(branches) > 1:
            # ถ้ามีหลายสาขาแต่ไม่ใช่กรณี 90HO+00TR ให้ส่งกลับเพื่อให้ผู้ใช้เลือก
            print(f"✅ Employee {emp_code} has {len(branches)} branches, returning for selection")
            return {
                "token": None,
                "employee": {
                    "id": emp["id"],
                    "name": emp["name"],
                    "branchId": emp["branchId"],
                    "branches": emp["branches"],
                }
            }
        
        # ถ้ามีเพียงสาขาเดียว ให้สร้าง token เลย
        token_payload = {
            "sub": emp["id"],
            "name": emp["name"],
            "branchId": emp["branchId"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
        }
        
        # ⭐ เพิ่ม branches ลงใน token
        if emp.get("branches"):
            token_payload["branches"] = emp["branches"]
        
        # เพิ่ม role และ region จาก UXP token ก่อน (ถ้ามี)
        uxp_roles = payload.get("roles") or payload.get("role")
        if uxp_roles:
            # ถ้า roles เป็น array ให้เอาตัวแรก, ถ้าเป็น string ใช้เลย
            if isinstance(uxp_roles, list) and len(uxp_roles) > 0:
                role_data = uxp_roles[0]
            elif isinstance(uxp_roles, str):
                role_data = uxp_roles
            else:
                role_data = None
            
            if role_data:
                # ถ้า role_data เป็น dict (nested format) ให้ดึง role field
                if isinstance(role_data, dict):
                    thai_role = role_data.get("role")
                else:
                    thai_role = role_data
                
                # แปลง Thai role เป็น English role code
                if thai_role:
                    from role_mapping import map_thai_role_to_code
                    role_code = map_thai_role_to_code(thai_role)
                    token_payload["role"] = role_code
                    print(f"✅ Extracted role from UXP token: {thai_role} → {role_code}")
        
        # ถ้าไม่มี role จาก UXP token ให้ดึงจาก employees.json
        if not token_payload.get("role") and emp.get("role"):
            token_payload["role"] = emp["role"]
            print(f"✅ Using role from employees.json: {token_payload['role']}")
        
        # เพิ่ม region ถ้ามี
        if emp.get("region"):
            token_payload["region"] = emp["region"]
        
        token = jwt.encode(
            token_payload,
            JWT_SECRET,
            algorithm=JWT_ALG,
        )
        
        # สร้าง HttpOnly cookie
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
            samesite="lax",
            max_age=JWT_EXPIRE_HOURS * 3600,
            path="/",
        )
        
        return {"token": token, "employee": emp}
        
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"UXP token ไม่ถูกต้อง: {str(e)}")
    except Exception as e:
        print(f"❌ Error in init_from_uxp: {e}")
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")


# === SELECT BRANCH ROUTE (เลือกสาขาเมื่อพนักงานมีหลายสาขา) ===
@router.post("/select-branch")
async def select_branch(request: Request, response: Response):
    """
    สร้าง auth_token ด้วยสาขาที่ผู้ใช้เลือก
    """
    try:
        body = await request.json()
        emp_code = body.get("employeeCode")
        selected_branch = body.get("branchId")
        
        if not emp_code or not selected_branch:
            raise HTTPException(status_code=400, detail="ต้องระบุ employeeCode และ branchId")
        
        # ดึงข้อมูลพนักงาน
        emp = await load_employee(emp_code)
        if not emp:
            raise HTTPException(status_code=401, detail=f"ไม่พบข้อมูลพนักงาน: {emp_code}")
        
        # ตรวจสอบว่าสาขาที่เลือกอยู่ในรายการสาขาของพนักงาน
        if selected_branch not in emp.get("branches", []):
            raise HTTPException(status_code=400, detail=f"สาขา {selected_branch} ไม่ใช่สาขาของพนักงาน")
        
        # สร้าง token payload
        token_payload = {
            "sub": emp["id"],
            "name": emp["name"],
            "branchId": selected_branch,
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
        }
        
        # ⭐ เพิ่ม branches ลงใน token
        if emp.get("branches"):
            token_payload["branches"] = emp["branches"]
        
        # เพิ่ม role และ region ถ้ามี
        if emp.get("role"):
            token_payload["role"] = emp["role"]
        if emp.get("region"):
            token_payload["region"] = emp["region"]
        
        # สร้าง JWT token
        token = jwt.encode(
            token_payload,
            JWT_SECRET,
            algorithm=JWT_ALG,
        )
        
        # สร้าง HttpOnly cookie
        response.set_cookie(
            key="auth_token",
            value=token,
            httponly=True,
            secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
            samesite="lax",
            max_age=JWT_EXPIRE_HOURS * 3600,
            path="/",
        )
        
        return {
            "token": token,
            "employee": {
                "id": emp["id"],
                "name": emp["name"],
                "branchId": selected_branch,
                "role": emp.get("role"),
                "region": emp.get("region"),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in select_branch: {e}")
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")


# === LOGIN ROUTE ===
@router.post("")
async def login(req: LoginRequest):
    emp = await load_employee(req.employeeCode)
    if not emp:
        raise HTTPException(status_code=401, detail="รหัสพนักงานไม่ถูกต้อง")

    token_payload = {
        "sub": emp["id"],
        "name": emp["name"],
        "branchId": emp["branchId"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    
    # ⭐ เพิ่ม branches ลงใน token
    if emp.get("branches"):
        token_payload["branches"] = emp["branches"]
    
    # เพิ่ม role และ region ถ้ามี
    if emp.get("role"):
        token_payload["role"] = emp["role"]
    if emp.get("region"):
        token_payload["region"] = emp["region"]
    
    token = jwt.encode(
        token_payload,
        JWT_SECRET,
        algorithm=JWT_ALG,
    )

    return {"token": token, "employee": emp}


# === MANUAL LOGIN ROUTE ===
@router.post("/manual")
async def manual_login(req: ManualLoginRequest, response: Response):
    """
    Manual login - ให้ผู้ใช้กรอกรหัสพนักงาน, role, สาขา และรหัสผ่าน
    """
    # ⭐ เช็ค password
    MANUAL_LOGIN_PASSWORD = os.getenv("MANUAL_LOGIN_PASSWORD", "Tng#kmitl2")
    if req.password != MANUAL_LOGIN_PASSWORD:
        raise HTTPException(status_code=401, detail="รหัสผ่านไม่ถูกต้อง")
    
    # ดึงข้อมูลพนักงานจาก API (เพื่อตรวจสอบว่ามีรหัสพนักงานนี้จริง)
    emp = await load_employee(req.employeeCode)
    
    # ถ้าไม่เจอในระบบ ให้สร้างข้อมูลพื้นฐาน
    if not emp:
        emp = {
            "id": req.employeeCode,
            "name": f"Employee {req.employeeCode}",
            "branchId": req.branchId,
        }
    else:
        # ถ้าเจอในระบบ ให้ใช้ branchId ที่ผู้ใช้กรอก (override)
        emp["branchId"] = req.branchId
    
    # ดึง region จาก branch
    region = get_region_from_branch(req.branchId)
    
    # แปลง Thai role name เป็น internal role code
    from role_mapping import map_thai_role_to_code, load_custom_roles
    
    # Debug: แสดง custom roles ที่โหลดได้
    custom_roles = load_custom_roles()
    print(f"🔍 [MANUAL_LOGIN] Custom roles loaded: {list(custom_roles.keys())}")
    
    role_code = map_thai_role_to_code(req.role)
    
    print(f"🔍 [MANUAL_LOGIN] Mapping role:")
    print(f"   Selected role (input): {req.role}")
    print(f"   Mapped role (output): {role_code}")
    
    # สร้าง token payload
    token_payload = {
        "sub": emp["id"],
        "name": emp["name"],
        "branchId": req.branchId,
        "role": role_code,  # ใช้ role code ที่แปลงแล้ว
        "region": region,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    
    # ⭐ เพิ่ม branches ลงใน token (ถ้ามี)
    if emp.get("branches"):
        token_payload["branches"] = emp["branches"]
    
    # สร้าง JWT token
    token = jwt.encode(
        token_payload,
        JWT_SECRET,
        algorithm=JWT_ALG,
    )
    
    # สร้าง HttpOnly cookie
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        max_age=JWT_EXPIRE_HOURS * 3600,
        path="/",
    )
    
    return {
        "token": token,
        "employee": {
            "id": emp["id"],
            "name": emp["name"],
            "branchId": req.branchId,
            "role": role_code,  # ส่ง role code กลับไปด้วย
            "region": region,
        }
    }


# === ME ROUTE ===
@router.get("/me")
async def get_current_user(request: Request):
    """
    ดึงข้อมูลผู้ใช้ปัจจุบันจาก cookie auth_token
    """
    token = request.cookies.get("auth_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="ไม่พบ token")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        employee_data = {
            "id": payload.get("sub"),
            "name": payload.get("name"),
            "branchId": payload.get("branchId"),
        }
        
        # ⭐ DEBUG: Log employee data
        print(f"🔍 [GET_CURRENT_USER] Employee data from JWT:")
        print(f"   ID: {employee_data.get('id')}")
        print(f"   Name: {employee_data.get('name')}")
        print(f"   BranchId: {employee_data.get('branchId')}")
        
        # เพิ่ม role และ region ถ้ามี
        if payload.get("role"):
            employee_data["role"] = payload.get("role")
        if payload.get("region"):
            employee_data["region"] = payload.get("region")
        
        return {
            "employee": employee_data
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token หมดอายุ")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token ไม่ถูกต้อง")


# === LOGOUT ROUTE ===
@router.post("/logout")
async def logout(response: Response):
    """
    Logout - ลบ cookie auth_token
    """
    response.delete_cookie(key="auth_token", path="/")
    return {"message": "ออกจากระบบสำเร็จ"}


# === GET ROLES ROUTE ===
@router.get("/roles")
async def get_roles():
    """
    ดึงรายการ roles ทั้งหมดจาก role_mapping
    """
    role_codes = get_all_role_codes()
    roles = []
    
    for code in role_codes:
        thai_name = get_thai_role_name(code)
        display_name = get_role_display_name(code)
        roles.append({
            "code": code,
            "displayName": display_name,
            "thaiName": thai_name
        })
    
    return {"roles": roles}


# === GET BRANCHES ROUTE ===
@router.get("/branches")
async def get_branches():
    """
    ดึงรายการสาขาทั้งหมดจาก branch_region_mapping
    """
    branches = []
    
    for branch_code, region_code in BRANCH_REGION_MAP.items():
        branches.append({
            "code": branch_code,
            "region": region_code,
            "displayName": f"{branch_code} ({region_code})"
        })
    
    # เรียงตาม branch code
    branches.sort(key=lambda x: x["code"])
    
    return {"branches": branches}
