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
    """DUTY: Query UXP Auth API to find employee by role and branch | WHEN: Called by other functions to resolve approvers"""
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
    """DUTY: Find Zone Manager at specific branch | WHEN: Quote creation, approval routing"""
    emp = await query_employee_by_role("ผู้จัดการสาขา (R1-W2)", branch_code)
    if emp:
        return {"employee_id": emp.get("username"), "branch": emp.get("branchCode"), 
                "name": emp.get("empName"), "role": "ZM"}
    return None

async def find_rm_in_region(region_code: str) -> Optional[Dict]:
    """DUTY: Find Regional Manager for region (maps BKK/E→90HO, N→12CM, S→13SR, NE→10KK, C→21BS) | WHEN: Quote approval routing"""
    region_map = {
        "BKK": "90HO",  # Bangkok
        "E": "90HO",    # East (RM คนเดียวกับ BKK)
        "N": "12CM",    # North
        "S": "13SR",    # South
        "NE": "10KK",   # Northeast
        "C": "21BS"     # Central
    }
    branch = region_map.get(region_code)
    if not branch:
        return None
    emp = await query_employee_by_role("ผู้จัดการภาค (W2-W1)", branch)
    if emp:
        return {"employee_id": emp.get("username"), "branch": emp.get("branchCode"),
                "name": emp.get("empName"), "role": "RM", "region": region_code}
    return None

async def find_sdm() -> Optional[Dict]:
    """DUTY: Find Sales Director Manager at 90HO | WHEN: High-value quote approval, special price requests""" 
    emp = await query_employee_by_role("ผู้จัดการฝ่ายขาย (W1-SDM)", "90HO")
    if emp:
        return {"employee_id": emp.get("username"), "branch": emp.get("branchCode"),
                "name": emp.get("empName"), "role": "SDM", "region": "ALL"}
    return None




async def find_pm_by_category(category: str) -> Optional[Dict]:
    """DUTY: Find Product Manager by category (G, A, C, Y, S, E) | WHEN: Category-specific approvals, special price requests"""
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
    """DUTY: Find all PMs for multiple categories | WHEN: Multi-category quote approvals"""
    pms = {}
    for category in categories:
        pm = await find_pm_by_category(category)
        if pm:
            pms[category] = pm
            logger.info(f"✅ Found PM for category {category}: {pm['name']}")
        else:
            logger.warning(f"⚠️ PM not found for category {category}")
    
    return pms
