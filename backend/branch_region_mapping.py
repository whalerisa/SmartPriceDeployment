"""
Branch to Region Mapping Module

This module provides mapping from branch codes to their corresponding regions.
Data is extracted from employees.json to support region derivation when auth_token
does not include region information.

Regions:
- BE: Bangkok East
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
# Note: 00TR is mapped to same region as 90HO (BE)
BRANCH_REGION_MAP = {
    # Bangkok East (BE)
    "00TR": "BE",  # Same as 90HO
    "01TJ": "BE",
    "03TS": "BE",
    "04TP": "BE",
    "06RY": "BE",
    "15CB": "BE",
    "24TL": "BE",
    "90HO": "BE",
    
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
        Region code (BE, N, S, NE, C) or "Unknown" if branch not found
        
    Example:
        >>> get_region_from_branch("03TS")
        'BE'
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
        region: Region code (BE, N, S, NE, C)
        
    Returns:
        List of branch codes in the specified region
        
    Example:
        >>> get_all_branches_by_region("BE")
        ['00TR', '01TJ', '03TS', '04TP', '06RY', '15CB', '24TL', '90HO']
    """
    return [branch for branch, reg in BRANCH_REGION_MAP.items() if reg == region]


def get_region_name(region_code: str) -> str:
    """
    Get full region name from region code.
    
    Args:
        region_code: Region code (BE, N, S, NE, C)
        
    Returns:
        Full region name
    """
    region_names = {
        "BE": "Bangkok East",
        "N": "North",
        "S": "South",
        "NE": "Northeast",
        "C": "Central",
        "Unknown": "Unknown"
    }
    return region_names.get(region_code, "Unknown")
