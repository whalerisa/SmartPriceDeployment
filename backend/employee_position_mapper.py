"""
Employee Position Mapper - API Based
Queries UXP Auth API: GET /auth/get-user-by-role
"""
import logging
import httpx
from typing import Optional, Dict
from config.config_external_api import EMP_QUERY_API_URL, EMP_QUERY_API_HEADERS

logger = logging.getLogger(__name__)

async def query_employee_by_role(role_name: str, branch_code: str = None, app_name: str = "Smart Quotation") -> Optional[Dict]:
    """Query employee from API by role and branch"""
    try:
        params = {"roleName": role_name, "appName": app_name}
        if branch_code:
            params["branchCode"] = branch_code
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(EMP_QUERY_API_URL, params=params, headers=EMP_QUERY_API_HEADERS)
            response.raise_for_status()
            data = response.json()
            if data.get("success") and data.get("data"):
                emp = data["data"][0]
                logger.info(f"✅ Found: {emp.get('username')} for {role_name} at {branch_code}")
                return emp
            return None
    except Exception as e:
        logger.error(f"❌ API error: {e}")
        return None

async def find_zm_at_branch(branch_code: str) -> Optional[Dict]:
    """Find Zone Manager at branch"""
    emp = await query_employee_by_role("ผู้จัดการสาขา (R1-W2)", branch_code)
    if emp:
        return {"employee_id": emp.get("username"), "branch": emp.get("branchCode"), 
                "name": emp.get("empName"), "role": "ZM"}
    return None

async def find_rm_in_region(region_code: str) -> Optional[Dict]:
    """Find Regional Manager in region"""
    region_map = {"BE": "90HO", "N": "12CM", "S": "13SR", "NE": "10KK", "C": "21BS"}
    branch = region_map.get(region_code)
    if not branch:
        return None
    emp = await query_employee_by_role("ผู้จัดการภูมิภาค (R1-W2)", branch)
    if emp:
        return {"employee_id": emp.get("username"), "branch": emp.get("branchCode"),
                "name": emp.get("empName"), "role": "RM", "region": region_code}
    return None

async def find_sdm() -> Optional[Dict]:
    """Find Sales Director Manager"""
    emp = await query_employee_by_role("ผู้จัดการฝ่ายขาย (W1-SDM)", "90HO")
    if emp:
        return {"employee_id": emp.get("username"), "branch": emp.get("branchCode"),
                "name": emp.get("empName"), "role": "SDM", "region": "ALL"}
    return None

async def resolve_approver_position(position_id: str) -> Optional[Dict]:
    """Resolve position ID to employee (ZM_03TS -> employee info)"""
    if not position_id or "_" not in position_id:
        return None
    role, identifier = position_id.split("_", 1)
    if role == "ZM":
        return await find_zm_at_branch(identifier)
    elif role == "RM":
        return await find_rm_in_region(identifier)
    elif role == "SDM":
        return await find_sdm()
    return None


async def find_pm() -> Optional[Dict]:
    """Find Product Manager"""
    emp = await query_employee_by_role("ผู้จัดการผลิตภัณฑ์ (Below SDM)", "90HO")
    if emp:
        return {"employee_id": emp.get("username"), "branch": emp.get("branchCode"),
                "name": emp.get("empName"), "role": "PM", "region": "ALL"}
    return None

async def find_ceo() -> Optional[Dict]:
    """Find CEO"""
    emp = await query_employee_by_role("กรรมการผู้จัดการ", "90HO")
    if emp:
        return {"employee_id": emp.get("username"), "branch": emp.get("branchCode"),
                "name": emp.get("empName"), "role": "CEO", "region": "ALL"}
    return None

async def find_sales_at_branch(branch_code: str) -> Optional[Dict]:
    """Find Sales at branch"""
    emp = await query_employee_by_role("พนักงานขาย", branch_code)
    if emp:
        return {"employee_id": emp.get("username"), "branch": emp.get("branchCode"),
                "name": emp.get("empName"), "role": "Sales"}
    return None


async def find_pm_by_category(category: str) -> Optional[Dict]:
    """
    Find Product Manager by product category
    
    Args:
        category: Product category (G, A, C, Y, S, E)
    
    Returns:
        PM employee info or None
    """
    category_map = {
        'G': 'ผู้จัดการผลิตภัณฑ์กระจก',
        'A': 'ผู้จัดการผลิตภัณฑ์อลูมิเนียม',
        'C': 'ผู้จัดการผลิตภัณฑ์โครงคร่าวฝ้าเพดานโครงผนัง',
        'Y': 'ผู้จัดการผลิตภัณฑ์ยิปซัม',
        'S': 'ผู้จัดการผลิตภัณฑ์ซีลแลนท์',
        'E': 'ผู้จัดการผลิตภัณฑ์อุปกรณ์และอื่นๆ'
    }
    
    role_name = category_map.get(category.upper())
    if not role_name:
        logger.warning(f"Unknown product category: {category}")
        return None
    
    # ⭐ PM ทุกคนอยู่ที่ branch 90HO
    emp = await query_employee_by_role(role_name, "90HO")
    if emp:
        return {
            "employee_id": emp.get("username"),
            "branch": "90HO",  # PM ทุกคนอยู่ที่ 90HO
            "name": emp.get("empName"),
            "role": "PM",
            "category": category.upper(),
            "region": "ALL"
        }
    
    logger.warning(f"PM not found for category: {category}")
    return None


async def find_all_pms_by_categories(categories: list) -> Dict[str, Dict]:
    """
    Find all PMs for given product categories
    
    Args:
        categories: List of product categories (G, A, C, Y, S, E)
    
    Returns:
        Dictionary mapping category to PM info
    """
    pms = {}
    for category in categories:
        pm = await find_pm_by_category(category)
        if pm:
            pms[category] = pm
            logger.info(f"✅ Found PM for category {category}: {pm['name']}")
        else:
            logger.warning(f"⚠️ PM not found for category {category}")
    
    return pms
