"""
Role Mapping Module

This module provides mapping from Thai role names (from auth_token) to internal role codes.
The auth_token contains role names in Thai which need to be translated to English codes
for internal use throughout the application.

Role Mappings:
1. พนักงานขาย → Sales
2. พนักงานขายโครงการ → Sales_Project
3. ผู้จัดการสาขา (R1-W2) → ZM (Zone Manager)
4. ผู้จัดการภูมิภาค (R1-W2) → RM (Regional Manager)
5. ผู้จัดการฝ่ายขาย (W1-SDM) → SDM (Sales Director Manager)
6. ผู้จัดการผลิตภัณฑ์ (Below SDM) → PM (Product Manager - General)
7. ผู้จัดการผลิตภัณฑ์โครงคร่าวฝ้าเพดานโครงผนัง → PM_CLINE (Product Manager - Cline)
8. ผู้จัดการผลิตภัณฑ์กระจก → PM_GLASS (Product Manager - Glass)
9. ผู้จัดการผลิตภัณฑ์อุปกรณ์และอื่นๆ → PM_EQUIPMENT (Product Manager - Equipment & Others)
10. ผู้จัดการผลิตภัณฑ์อลูมิเนียม → PM_ALUMINIUM (Product Manager - Aluminium)
11. ผู้จัดการผลิตภัณฑ์ยิปซัม → PM_GYPSUM (Product Manager - Gypsum)
12. ผู้จัดการผลิตภัณฑ์ซีลแลนท์ → PM_SEALANT (Product Manager - Sealant)
13. กรรมการผู้จัดการ → CEO
14. ผู้ดูแลระบบ → Admin (System Administrator)
15. ผู้ดูแลระบบสูงสุด → SuperAdmin (Super Administrator)
"""

import logging
import os
import json

logger = logging.getLogger(__name__)

# Thai role name to internal role code mapping
THAI_ROLE_TO_CODE = {
    "พนักงานขาย": "Sales",
    "พนักงานขายโครงการ": "Sales_Project",  # ⭐ Project Sales
    "ผู้จัดการสาขา (R1-W2)": "ZM",  # Zone Manager
    "ผู้จัดการภาค (W2-W1)": "RM",  # Regional Manager
    "ผู้จัดการฝ่ายขาย (W1-SDM)": "SDM",  # Sales Director Manager
    "ผู้จัดการผลิตภัณฑ์ (Below SDM)": "PM",  # Product Manager - General
    "ผู้จัดการแผนก": "PM",  # Product Manager - Department Manager (from UXP API)
    "ผู้จัดการผลิตภัณฑ์โครงคร่าวฝ้าเพดานโครงผนัง": "PM",  # Product Manager - Cline
    "ผู้จัดการผลิตภัณฑ์กระจก": "PM",  # Product Manager - Glass
    "ผู้จัดการผลิตภัณฑ์อุปกรณ์และอื่นๆ": "PM",  # Product Manager - Equipment & Others
    "ผู้จัดการผลิตภัณฑ์อลูมิเนียม": "PM",  # Product Manager - Aluminium
    "ผู้จัดการผลิตภัณฑ์ยิปซัม": "PM",  # Product Manager - Gypsum
    "ผู้จัดการผลิตภัณฑ์ซีลแลนท์": "PM",  # Product Manager - Sealant
    "กรรมการผู้จัดการ": "CEO",
    "Admin": "Admin",  # System Administrator
    "SuperAdmin": "SuperAdmin",  # Super Administrator
}

# Valid role codes (for when role is already in English)
VALID_ROLE_CODES = {
    "Sales", "Sales_Project", "ZM", "RM", "SDM", "PM", "CEO", "Admin", "SuperAdmin",
    "PM_CLINE", "PM_GLASS", "PM_EQUIPMENT", "PM_ALUMINIUM", "PM_GYPSUM", "PM_SEALANT"
}

# Default role when mapping fails
DEFAULT_ROLE = "Sales"

# Product Manager roles (all PM variants)
PM_ROLES = {
    "PM", "PM_CLINE", "PM_GLASS", "PM_EQUIPMENT", "PM_ALUMINIUM", "PM_GYPSUM", "PM_SEALANT"
}

# Management roles (can manage prices and approve special prices)
MANAGEMENT_ROLES = {"ZM", "RM", "SDM"} | PM_ROLES


def is_pm_role(role_code: str) -> bool:
    """Check if role is any PM variant"""
    return role_code == "PM" or role_code.startswith("PM_")


def load_custom_roles() -> dict:
    """
    Load custom roles from JSON file.
    
    Returns:
        Dictionary of custom roles: {role_code: {thai_name, display_name}}
    """
    try:
        # Try multiple possible locations for the config file
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "custom_roles.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_roles.json"),
            os.path.join(os.getcwd(), "custom_roles.json"),
            os.path.join(os.getcwd(), "backend", "custom_roles.json"),
            "custom_roles.json",
        ]
        
        custom_roles_file = None
        for path in possible_paths:
            if os.path.exists(path):
                custom_roles_file = path
                break
        
        if custom_roles_file and os.path.exists(custom_roles_file):
            with open(custom_roles_file, "r", encoding="utf-8") as f:
                custom_roles = json.load(f)
            logger.info(f"✅ Loaded custom roles from {custom_roles_file}")
            return custom_roles
        else:
            logger.warning(f"⚠️ custom_roles.json not found in any of these locations: {possible_paths}")
    except Exception as e:
        logger.error(f"❌ Failed to load custom roles from file: {e}")
    return {}


def map_thai_role_to_code(thai_role_name: str) -> str:
    """
    Map Thai role name from auth_token to internal role code.
    Also accepts English role codes directly.
    
    Args:
        thai_role_name: Role name in Thai from auth_token (e.g., "พนักงานขาย")
                       or English role code (e.g., "Sales")
        
    Returns:
        Internal role code (Sales, ZM, RM, SDM, PM, CEO)
        Returns "Sales" as default if role name is not recognized
        
    Example:
        >>> map_thai_role_to_code("พนักงานขาย")
        'Sales'
        >>> map_thai_role_to_code("Sales")
        'Sales'
        >>> map_thai_role_to_code("ผู้จัดการสาขา (R1-W2)")
        'ZM'
        >>> map_thai_role_to_code("Unknown Role")
        'Sales'
    """
    if not thai_role_name:
        logger.warning("Empty thai_role_name provided, returning default role 'Sales'")
        return DEFAULT_ROLE
    
    # Check if it's already a valid English role code (including custom roles)
    all_valid_codes = set(VALID_ROLE_CODES)
    custom_roles = load_custom_roles()
    all_valid_codes.update(custom_roles.keys())
    
    if thai_role_name in all_valid_codes:
        logger.info(f"Role '{thai_role_name}' is already a valid role code")
        return thai_role_name
    
    # Try exact match for Thai role name in built-in mappings
    role_code = THAI_ROLE_TO_CODE.get(thai_role_name)
    
    if role_code:
        logger.info(f"Mapped Thai role '{thai_role_name}' to code '{role_code}'")
        return role_code
    
    # Try to find in custom roles Thai name mappings
    for code, info in custom_roles.items():
        if info.get("thai_name") == thai_role_name:
            logger.info(f"Mapped custom Thai role '{thai_role_name}' to code '{code}'")
            return code
    
    logger.warning(
        f"Unknown Thai role name '{thai_role_name}', returning default role '{DEFAULT_ROLE}'"
    )
    return DEFAULT_ROLE


def get_role_display_name(role_code: str) -> str:
    """
    Get display name for role code.
    
    Args:
        role_code: Internal role code (Sales, Sales_Project, ZM, RM, SDM, PM, PM_CLINE, PM_GLASS, etc.)
        
    Returns:
        Human-readable role name in English
    """
    role_display_names = {
        "Sales": "Sales",
        "Sales_Project": "Project Sales",  # ⭐ Project Sales
        "ZM": "Zone Manager",
        "RM": "Regional Manager",
        "SDM": "Sales Director Manager",
        "PM": "Product Manager",
        "PM_CLINE": "Product Manager - Cline",
        "PM_GLASS": "Product Manager - Glass",
        "PM_EQUIPMENT": "Product Manager - Equipment & Others",
        "PM_ALUMINIUM": "Product Manager - Aluminium",
        "PM_GYPSUM": "Product Manager - Gypsum",
        "PM_SEALANT": "Product Manager - Sealant",
        "CEO": "Chief Executive Officer",
        "Admin": "System Administrator",
        "SuperAdmin": "Super Administrator",
    }
    return role_display_names.get(role_code, role_code)


def get_thai_role_name(role_code: str) -> str:
    """
    Get Thai role name from internal role code (reverse mapping).
    
    Args:
        role_code: Internal role code (Sales, ZM, RM, SDM, PM, PM_FRAME, PM_GLASS, etc.)
        
    Returns:
        Thai role name or empty string if not found
    """
    # Create reverse mapping
    code_to_thai = {code: thai for thai, code in THAI_ROLE_TO_CODE.items()}
    return code_to_thai.get(role_code, "")


def is_valid_role_code(role_code: str) -> bool:
    """
    Check if a role code is valid.
    
    Args:
        role_code: Role code to validate
        
    Returns:
        True if role code is valid, False otherwise
    """
    return role_code in VALID_ROLE_CODES


def get_all_role_codes() -> list:
    """
    Get list of all valid role codes including custom roles.
    
    Returns:
        List of all internal role codes
    """
    # Start with built-in roles
    all_roles = list(VALID_ROLE_CODES)
    
    # Add custom roles from JSON file
    try:
        custom_roles = load_custom_roles()
        all_roles.extend(custom_roles.keys())
    except Exception as e:
        logger.warning(f"Failed to load custom roles: {e}")
    
    return sorted(list(set(all_roles)))  # Remove duplicates and sort
