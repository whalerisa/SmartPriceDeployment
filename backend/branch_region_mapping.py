"""
Branch to Region Mapping Module

This module provides mapping from branch codes to their corresponding regions.
Data is extracted from employees.json to support region derivation when auth_token
does not include region information.

Regions:
- BKK: Bangkok (แยกจาก BE)
- E: East (แยกจาก BE)
- N: North
- S: South
- NE: Northeast
- C: Central
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Branch to Region mapping extracted from employees.json
# Note: 00TR is mapped to same region as 90HO (BKK)
BRANCH_REGION_MAP = {
    # Bangkok (BKK) - แยกจาก BE
    "00TR": "BKK",
    "01TJ": "BKK",
    "03TS": "BKK",
    "04TP": "BKK",
    "24TL": "BKK",
    "90HO": "BKK",
    
    # East (E) - แยกจาก BE
    "06RY": "E",
    "15CB": "E",
    
    # North (N)
    "11PL": "N",
    "12CM": "N",
    "17CR": "N",
    "23NS": "N",
    
    # South (S)
    "13SR": "S",
    "14HY": "S",
    "16PK": "S",
    
    # Northeast (NE)
    "08NR": "NE",
    "09UB": "NE",
    "10KK": "NE",
    "18UD": "NE",
    "20SK": "NE",
    
    # Central (C)
    "05AY": "C",
    "07RB": "C",
    "19PC": "C",
    "21BS": "C",
    "25SB": "C",
}


def get_region_from_branch(branch_code: str) -> str: #แปลงรหัสสาขาเป็นภูมิภาค
    """
    Get region code from branch code.
    
    Args:
        branch_code: Branch code from auth token (e.g., "03TS", "12CM")
        
    Returns:
        Region code (BKK, E, N, S, NE, C) or "Unknown" if branch not found
        
    Example:
        >>> get_region_from_branch("03TS")
        'BKK'
        >>> get_region_from_branch("12CM")
        'N'
        >>> get_region_from_branch("INVALID")
        'Unknown'
    """
    if not branch_code:
        logger.warning("Empty branch_code provided")
        return "Unknown"
    
    # ⭐ Normalize 90HO เป็น 00TR
    normalized_branch = "00TR" if branch_code == "90HO" else branch_code
    
    region = BRANCH_REGION_MAP.get(normalized_branch, "Unknown")
    
    if region == "Unknown":
        logger.warning(f"Branch code '{normalized_branch}' not found in mapping, returning 'Unknown'")
    else:
        logger.info(f"Mapped branch '{branch_code}' (normalized: '{normalized_branch}') to region '{region}'")
    
    return region


def load_branch_mapping_from_employees_json(file_path: str = "employees.json") -> dict:
    """
    Load branch-to-region mapping from employees.json file.
    This function can be used to refresh the mapping if needed.
    
    Args:
        file_path: Path to employees.json file
        
    Returns:
        Dictionary mapping branch codes to regions
    """
    try:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"employees.json not found at {file_path}")
            return {}
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        mapping = {}
        for employee in data.get("employees", []):
            branch = employee.get("branch")
            region = employee.get("region")
            if branch and region:
                mapping[branch] = region
        
        logger.info(f"Loaded {len(mapping)} branch-to-region mappings from {file_path}")
        return mapping
        
    except Exception as e:
        logger.error(f"Error loading branch mapping from {file_path}: {e}")
        return {}


def get_all_branches_by_region(region: str) -> list: #ดึงรายชื่อสาขาทั้งหมดในภูมิภาคเดียวกัน/ให้ Regional Manager (RM) เห็นใบเสนอราคาทุกสาขาในภูมิภาคของตน
    """
    Get all branch codes for a specific region.
    
    Args:
        region: Region code (BKK, E, N, S, NE, C)
        
    Returns:
        List of branch codes in the specified region
        
    Example:
        >>> get_all_branches_by_region("BKK")
        ['00TR', '01TJ', '03TS', '04TP', '24TL', '90HO']
    """
    return [branch for branch, reg in BRANCH_REGION_MAP.items() if reg == region]


def get_regions_for_rm(rm_branch: str) -> list:
    """
    Get all regions that an RM is responsible for based on their branch.
    
    Args:
        rm_branch: RM's branch code (e.g., "90HO")
        
    Returns:
        List of region codes the RM is responsible for
        
    Example:
        >>> get_regions_for_rm("90HO")
        ['BKK', 'E']  # RM ที่ 90HO ดูแล BKK และ E
    """
    # ⭐ หา region ของ branch นี้ก่อน
    branch_region = get_region_from_branch(rm_branch)
    
    # ⭐ ถ้า branch อยู่ใน BKK หรือ E ให้ดูแลทั้ง 2 ภาค
    if branch_region in ["BKK", "E"]:
        return ["BKK", "E"]
    
    # ⭐ ภาคอื่นๆ ดูแลแค่ภาคของตัวเอง
    if branch_region != "Unknown":
        return [branch_region]
    
    return []


def get_regions_for_rm_by_employee_id(employee_id: str) -> list:
    """
    Get all regions that an RM is responsible for based on their employee ID.
    Reads from employees.json file - RM สามารถมี multiple entries กับ region ต่างกัน
    
    Args:
        employee_id: RM's employee ID (e.g., "20054")
        
    Returns:
        List of region codes the RM is responsible for
        Empty list if employee_id not found (will use default region from branch)
        
    Example:
        >>> get_regions_for_rm_by_employee_id("20054")
        ['BKK', 'E']  # RM รหัส 20054 มี 2 entries ใน employees.json กับ region BKK และ E
        
        >>> get_regions_for_rm_by_employee_id("99999")
        []  # ไม่พบ RM นี้ ให้ใช้ default region
    """
    try:
        import json
        from pathlib import Path
        
        # ⭐ ดึงข้อมูลจาก employees.json
        employees_path = Path(__file__).parent / "employees.json"
        
        if not employees_path.exists():
            logger.warning(f"employees.json not found at {employees_path}, using default region")
            return []
        
        with open(employees_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        employees = data.get("employees", [])
        
        #ดึง regions ทั้งหมดของ RM นี้
        regions = []
        for emp in employees:
            if emp.get("employee_id") == employee_id and emp.get("role") == "RM":
                region = emp.get("region")
                if region and region not in regions:
                    regions.append(region)
        
        if regions:
            logger.info(f"RM {employee_id} is responsible for regions: {regions}")
            return regions
        else:
            logger.info(f"RM {employee_id} not found in employees.json, will use default region from branch")
            return []
            
    except Exception as e:
        logger.error(f"Error loading RM regions from employees.json: {e}")
        return []


def get_region_name(region_code: str) -> str:
    """
    Get full region name from region code.
    
    Args:
        region_code: Region code (BKK, E, N, S, NE, C)
        
    Returns:
        Full region name
    """
    region_names = {
        "BKK": "Bangkok",
        "E": "East",
        "N": "North",
        "S": "South",
        "NE": "Northeast",
        "C": "Central",
        "Unknown": "Unknown"
    }
    return region_names.get(region_code, "Unknown")
