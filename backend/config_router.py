"""
Config Router

This router provides endpoints for system configuration management.
Only accessible to admin users.

Endpoints:
- GET /config - Get all system configuration
- PUT /config - Update system configuration
- GET /config/api-status - Check API connectivity status
"""

import logging
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from pydantic import BaseModel

from auth_dependency import get_employee_info
from config.config_external_api import (
    SDM_THRESHOLD_PRICE, BASE_URL
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Config"])


# ==================== Models ====================

class PriceConfig(BaseModel):
    """Price Configuration"""
    sdm_threshold_price: float
    price_levels: Dict[str, float] = {}


class PageAccessConfig(BaseModel):
    """Page Access Configuration for a specific page"""
    page_name: str
    page_label: str
    allowed_roles: list[str] = []


class AccessControlConfig(BaseModel):
    """Access Control Configuration"""
    price_update_employees: list[str] = []
    project_price_employees: list[str] = []
    special_price_approvers: list[str] = []
    page_access: Dict[str, PageAccessConfig] = {}  # New: Role-based page access


class SystemConfig(BaseModel):
    """System Configuration"""
    base_url: str
    timezone: str = "Asia/Bangkok"
    language: str = "th"
    version: str = "1.0.0"
    vat_rate: float = 0.07  # ⭐ VAT rate (default 7%)
    project_code_mode: str = "auto"  # ⭐ Project code mode: "auto" (running number) or "manual" (user input)
    project_files_folder: str = "./uploads/project_files"  # ⭐ Folder for project files
    product_images_folder: str = "./uploads/product_images"  # ⭐ Folder for product images


class ConfigResponse(BaseModel):
    """Complete Configuration Response"""
    api_configs: Dict[str, Any]  # Empty dict for security
    price_config: PriceConfig
    access_control: AccessControlConfig
    system_config: SystemConfig


# ==================== Helper Functions ====================

def get_current_employee(request: Request, authorization: str = Header(None)) -> dict:
    """Get current employee from JWT token"""
    return get_employee_info(request, authorization)


def check_admin_role(employee_info: dict) -> bool:
    """Check if user has admin role"""
    role = employee_info.get("role", "").lower()
    return role == "admin"


def test_api_connection(url: str, headers: dict, timeout: int = 5) -> tuple[bool, str]:
    """Test API connection - DEPRECATED: Not used anymore for security reasons"""
    return False, "API testing disabled for security"


def _update_env_file(updates: Dict[str, str]) -> None:
    """
    Update .env file with new values.
    
    Args:
        updates: Dictionary of key-value pairs to update in .env file
    """
    # Find .env file
    possible_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "backend", ".env"),
        ".env",
    ]
    
    env_file = None
    for path in possible_paths:
        if os.path.exists(path):
            env_file = path
            break
    
    if not env_file:
        logger.warning(f"⚠️ .env file not found in any of the expected locations: {possible_paths}")
        return
    
    try:
        # Read current .env file
        lines = []
        env_content = {}
        
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and "=" in stripped and not stripped.startswith("#"):
                    key, value = stripped.split("=", 1)
                    env_content[key.strip()] = value.strip()
                lines.append(line)
        
        # Update with new values
        env_content.update(updates)
        
        # Write back to file - preserve structure and comments
        with open(env_file, "w", encoding="utf-8") as f:
            for line in lines:
                stripped = line.strip()
                
                # Skip empty lines and comments
                if not stripped or stripped.startswith("#"):
                    f.write(line)
                    continue
                
                # Update key-value pairs
                if "=" in stripped:
                    key, _ = stripped.split("=", 1)
                    key = key.strip()
                    
                    if key in updates:
                        # Write updated value
                        f.write(f"{key}={updates[key]}\n")
                    else:
                        # Keep original value
                        f.write(line)
                else:
                    f.write(line)
            
            # Add any new keys that weren't in the original file
            for key, value in updates.items():
                if key not in env_content or env_content[key] != value:
                    # Check if key was already written
                    found = False
                    for line in lines:
                        if line.strip().startswith(f"{key}="):
                            found = True
                            break
                    
                    if not found:
                        f.write(f"{key}={value}\n")
        
        logger.info(f"✅ .env file updated successfully: {env_file}")
        logger.info(f"📝 Updated keys: {list(updates.keys())}")
    
    except Exception as e:
        logger.error(f"❌ Failed to update .env file: {e}")
        raise


# ==================== Endpoints ====================

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify router is working"""
    return {"message": "Config router is working!"}


@router.get("/settings", response_model=ConfigResponse)
async def get_config(employee: dict = Depends(get_current_employee)):
    """
    Get all system configuration.
    Only accessible to admin users.
    
    Note: API configurations (URLs and keys) are not included for security reasons.
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can access config")
    
    try:
        # API Configurations - Return empty for security (not editable via UI)
        api_configs = {}
        
        # Price Configuration
        price_config = PriceConfig(
            sdm_threshold_price=SDM_THRESHOLD_PRICE,
            price_levels={
                "SDM": 0,
                "R2": 0,
                "R1": 0,
                "W2": 0,
                "W1": 0
            }
        )
        
        # Access Control Configuration
        price_update_str = os.getenv("ALLOWED_PRICE_UPDATE_EMPLOYEES", "")
        project_price_str = os.getenv("ALLOWED_PROJECT_PRICE_EMPLOYEES", "")
        special_price_str = os.getenv("ALLOWED_SPECIAL_PRICE_APPROVERS", "")
        
        # Load page access configuration from cache
        from config_cache import get_page_access_config
        page_access_dict = get_page_access_config()
        page_access = {
            page_id: PageAccessConfig(**config)
            for page_id, config in page_access_dict.items()
        }
        
        access_control = AccessControlConfig(
            price_update_employees=[e.strip() for e in price_update_str.split(",") if e.strip()],
            project_price_employees=[e.strip() for e in project_price_str.split(",") if e.strip()],
            special_price_approvers=[e.strip() for e in special_price_str.split(",") if e.strip()],
            page_access=page_access
        )
        
        # System Configuration
        vat_rate_str = os.getenv("VAT_RATE", "0.07")
        try:
            vat_rate = float(vat_rate_str)
        except:
            vat_rate = 0.07
        
        project_code_mode = os.getenv("PROJECT_CODE_MODE", "auto")
        project_files_folder = os.getenv("PROJECT_FILES_FOLDER", "./uploads/project_files")
        product_images_folder = os.getenv("PRODUCT_IMAGES_FOLDER", "./uploads/product_images")
        
        system_config = SystemConfig(
            base_url=BASE_URL,
            timezone=os.getenv("TIMEZONE", "Asia/Bangkok"),
            language=os.getenv("LANGUAGE", "th"),
            version=os.getenv("APP_VERSION", "1.0.0"),
            vat_rate=vat_rate,
            project_code_mode=project_code_mode,
            project_files_folder=project_files_folder,
            product_images_folder=product_images_folder
        )
        
        return ConfigResponse(
            api_configs=api_configs,
            price_config=price_config,
            access_control=access_control,
            system_config=system_config
        )
    
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings", response_model=dict)
async def update_config(
    config_data: Dict[str, Any],
    employee: dict = Depends(get_current_employee)
):
    """
    Update system configuration.
    Only accessible to admin users.
    
    Supported updates:
    - price_config.sdm_threshold_price
    - access_control.price_update_employees
    - access_control.project_price_employees
    - access_control.special_price_approvers
    - access_control.page_access
    - system_config.timezone
    - system_config.language
    - system_config.vat_rate
    - system_config.project_code_mode
    - system_config.project_files_folder
    - system_config.product_images_folder
    
    Note: API configurations (URLs and keys) cannot be updated via this endpoint for security reasons.
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can update config")
    
    try:
        import json
        from config_cache import set_page_access_config
        
        # Track which env vars need to be persisted to .env file
        env_updates = {}
        
        # ⚠️ API configurations are NOT updatable via this endpoint for security reasons
        # API URLs and keys should be managed through environment variables or .env file
        
        if "price_config" in config_data:
            price_cfg = config_data["price_config"]
            if "sdm_threshold_price" in price_cfg:
                os.environ["SDM_THRESHOLD_PRICE"] = str(price_cfg["sdm_threshold_price"])
                env_updates["SDM_THRESHOLD_PRICE"] = str(price_cfg["sdm_threshold_price"])
        
        if "access_control" in config_data:
            ac = config_data["access_control"]
            if "price_update_employees" in ac:
                os.environ["ALLOWED_PRICE_UPDATE_EMPLOYEES"] = ",".join(ac["price_update_employees"])
                env_updates["ALLOWED_PRICE_UPDATE_EMPLOYEES"] = ",".join(ac["price_update_employees"])
            if "project_price_employees" in ac:
                os.environ["ALLOWED_PROJECT_PRICE_EMPLOYEES"] = ",".join(ac["project_price_employees"])
                env_updates["ALLOWED_PROJECT_PRICE_EMPLOYEES"] = ",".join(ac["project_price_employees"])
            if "special_price_approvers" in ac:
                os.environ["ALLOWED_SPECIAL_PRICE_APPROVERS"] = ",".join(ac["special_price_approvers"])
                env_updates["ALLOWED_SPECIAL_PRICE_APPROVERS"] = ",".join(ac["special_price_approvers"])
            
            # Store page_access configuration in cache (immediate effect)
            if "page_access" in ac:
                set_page_access_config(ac["page_access"])
                # Also store in environment for persistence
                os.environ["PAGE_ACCESS_CONFIG"] = json.dumps(ac["page_access"])
                env_updates["PAGE_ACCESS_CONFIG"] = json.dumps(ac["page_access"])
        
        if "system_config" in config_data:
            sys_cfg = config_data["system_config"]
            if "timezone" in sys_cfg:
                os.environ["TIMEZONE"] = sys_cfg["timezone"]
                env_updates["TIMEZONE"] = sys_cfg["timezone"]
            if "language" in sys_cfg:
                os.environ["LANGUAGE"] = sys_cfg["language"]
                env_updates["LANGUAGE"] = sys_cfg["language"]
            if "vat_rate" in sys_cfg:
                os.environ["VAT_RATE"] = str(sys_cfg["vat_rate"])
                env_updates["VAT_RATE"] = str(sys_cfg["vat_rate"])
            if "project_code_mode" in sys_cfg:
                os.environ["PROJECT_CODE_MODE"] = sys_cfg["project_code_mode"]
                env_updates["PROJECT_CODE_MODE"] = sys_cfg["project_code_mode"]
            if "project_files_folder" in sys_cfg:
                os.environ["PROJECT_FILES_FOLDER"] = sys_cfg["project_files_folder"]
                env_updates["PROJECT_FILES_FOLDER"] = sys_cfg["project_files_folder"]
            if "product_images_folder" in sys_cfg:
                os.environ["PRODUCT_IMAGES_FOLDER"] = sys_cfg["product_images_folder"]
                env_updates["PRODUCT_IMAGES_FOLDER"] = sys_cfg["product_images_folder"]
        
        # Persist changes to .env file
        if env_updates:
            _update_env_file(env_updates)
        
        logger.info(f"Config updated by {employee.get('employee_id')}: {list(env_updates.keys())}")
        
        return {
            "success": True,
            "message": "Configuration updated successfully. Changes take effect immediately.",
        }
    
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roles", response_model=list[str])
async def get_available_roles(employee: dict = Depends(get_current_employee)):
    """
    Get list of all available roles in the system.
    Only accessible to admin users.
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can access config")
    
    from role_mapping import get_all_role_codes
    return get_all_role_codes()


@router.post("/roles", response_model=dict)
async def create_role(
    role_data: Dict[str, Any],
    employee: dict = Depends(get_current_employee)
):
    """
    Create a new role in the system.
    Only accessible to admin users.
    
    Request body:
    {
        "role_code": "NEW_ROLE",
        "role_name_thai": "ชื่อ Role ภาษาไทย",
        "role_display_name": "Display Name"
    }
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can create roles")
    
    try:
        role_code = role_data.get("role_code")
        role_name_thai = role_data.get("role_name_thai")
        role_display_name = role_data.get("role_display_name")
        
        if not role_code or not role_name_thai:
            raise HTTPException(status_code=400, detail="role_code and role_name_thai are required")
        
        # Load existing custom roles from JSON file
        import json
        
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
        
        if not custom_roles_file:
            custom_roles_file = possible_paths[0]  # Default to first path
        
        try:
            with open(custom_roles_file, "r", encoding="utf-8") as f:
                custom_roles = json.load(f)
        except:
            custom_roles = {}
        
        # Check if role already exists
        from role_mapping import get_all_role_codes
        existing_roles = get_all_role_codes()
        if role_code in existing_roles:
            raise HTTPException(status_code=400, detail=f"Role {role_code} already exists")
        
        # Add new role
        custom_roles[role_code] = {
            "thai_name": role_name_thai,
            "display_name": role_display_name or role_code
        }
        
        # Save to JSON file
        try:
            with open(custom_roles_file, "w", encoding="utf-8") as f:
                json.dump(custom_roles, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved custom roles to {custom_roles_file}")
        except Exception as e:
            logger.error(f"Failed to save custom roles to file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save role: {e}")
        
        logger.info(f"Role {role_code} created by {employee.get('employee_id')}")
        
        return {
            "success": True,
            "message": f"Role {role_code} created successfully",
            "role_code": role_code
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating role: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/roles/{role_code}", response_model=dict)
async def delete_role(
    role_code: str,
    employee: dict = Depends(get_current_employee)
):
    """
    Delete a custom role from the system.
    Only accessible to admin users.
    Cannot delete built-in roles.
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can delete roles")
    
    try:
        # Load existing custom roles from JSON file
        import json
        
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
        
        if not custom_roles_file:
            custom_roles_file = possible_paths[0]  # Default to first path
        
        try:
            with open(custom_roles_file, "r", encoding="utf-8") as f:
                custom_roles = json.load(f)
        except:
            raise HTTPException(status_code=404, detail="No custom roles found")
        
        # Check if role exists in custom roles
        if role_code not in custom_roles:
            raise HTTPException(status_code=404, detail=f"Custom role {role_code} not found")
        
        # Remove role
        del custom_roles[role_code]
        
        # Save to JSON file
        try:
            with open(custom_roles_file, "w", encoding="utf-8") as f:
                json.dump(custom_roles, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved custom roles to {custom_roles_file} after deleting {role_code}")
        except Exception as e:
            logger.error(f"Failed to save custom roles to file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete role: {e}")
        
        # Also remove from page access config
        from config_cache import get_page_access_config, set_page_access_config
        page_access_config = get_page_access_config()
        
        for page_id, page_config in page_access_config.items():
            if role_code in page_config.get("allowed_roles", []):
                page_config["allowed_roles"].remove(role_code)
        
        set_page_access_config(page_access_config)
        
        logger.info(f"Role {role_code} deleted by {employee.get('employee_id')}")
        
        return {
            "success": True,
            "message": f"Role {role_code} deleted successfully",
            "role_code": role_code
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting role: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/page-access/check/{page_id}")
async def check_page_access_endpoint(
    page_id: str,
    employee: dict = Depends(get_current_employee)
):
    """
    Check if current user has access to a specific page.
    
    Args:
        page_id: Page identifier (e.g., "create_quote", "project_price")
        
    Returns:
        {
            "has_access": bool,
            "page_id": str,
            "user_role": str
        }
    """
    from page_access import check_page_access
    
    user_role = employee.get("role", "")
    has_access = check_page_access(page_id, user_role)
    
    return {
        "has_access": has_access,
        "page_id": page_id,
        "user_role": user_role
    }


@router.get("/page-access/user-pages")
async def get_user_pages(employee: dict = Depends(get_current_employee)):
    """
    Get list of pages that the current user can access.
    
    Returns:
        {
            "accessible_pages": list[str],
            "user_role": str
        }
    """
    from page_access import get_user_accessible_pages
    
    user_role = employee.get("role", "")
    accessible_pages = get_user_accessible_pages(user_role)
    
    return {
        "accessible_pages": accessible_pages,
        "user_role": user_role
    }


# ==================== Region Manager Mapping Endpoints ====================

class RegionInfo(BaseModel):
    """Region Information"""
    region_code: str
    region_name: str
    region_name_thai: str
    rm_employee_id: Optional[str] = None
    branches: list[str]


class RegionMappingResponse(BaseModel):
    """Region Mapping Response"""
    regions: Dict[str, RegionInfo]


@router.get("/regions", response_model=RegionMappingResponse)
async def get_region_mapping(employee: dict = Depends(get_current_employee)):
    """
    Get region to RM mapping configuration from employees.json.
    Only accessible to admin users.
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can access region config")
    
    try:
        import json
        from branch_region_mapping import BRANCH_REGION_MAP
        
        # Try multiple possible locations for the employees file
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "employees.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "employees.json"),
            os.path.join(os.getcwd(), "employees.json"),
            os.path.join(os.getcwd(), "backend", "employees.json"),
            "employees.json",
        ]
        
        employees_file = None
        for path in possible_paths:
            if os.path.exists(path):
                employees_file = path
                break
        
        if not employees_file:
            raise HTTPException(status_code=404, detail="Employees file not found")
        
        # Load employees.json
        with open(employees_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Build region mapping from employees
        region_names = {
            "BKK": {"name": "Bangkok", "thai": "กรุงเทพฯ"},
            "E": {"name": "East", "thai": "ภาคตะวันออก"},
            "N": {"name": "North", "thai": "ภาคเหนือ"},
            "S": {"name": "South", "thai": "ภาคใต้"},
            "NE": {"name": "Northeast", "thai": "ภาคตะวันออกเฉียงเหนือ"},
            "C": {"name": "Central", "thai": "ภาคกลาง"},
        }
        
        regions = {}
        
        # Find RM for each region
        for region_code, region_info in region_names.items():
            # Find RM employee for this region
            rm_employee = next(
                (emp for emp in data.get("employees", []) 
                 if emp.get("region") == region_code and emp.get("role") == "RM"),
                None
            )
            
            # Get branches for this region
            branches = [branch for branch, reg in BRANCH_REGION_MAP.items() if reg == region_code]
            
            regions[region_code] = RegionInfo(
                region_code=region_code,
                region_name=region_info["name"],
                region_name_thai=region_info["thai"],
                rm_employee_id=rm_employee.get("employee_id") if rm_employee else None,
                branches=sorted(branches)
            )
        
        logger.info(f"✅ Successfully loaded region mapping with {len(regions)} regions")
        return RegionMappingResponse(regions=regions)
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Employees file not found")
    except Exception as e:
        logger.error(f"Error loading region mapping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/regions/{region_code}", response_model=dict)
async def update_region_manager(
    region_code: str,
    update_data: Dict[str, Any],
    employee: dict = Depends(get_current_employee)
):
    """
    Update Regional Manager employee_id for a specific region in employees.json.
    Only accessible to admin users.
    
    This endpoint changes the employee_id of the current RM, not the role.
    If the future RM replaces the current one, we update the employee_id field.
    
    Request body:
    {
        "rm_employee_id": "10027"
    }
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can update region config")
    
    try:
        import json
        
        # Try multiple possible locations for the employees file
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "employees.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "employees.json"),
            os.path.join(os.getcwd(), "employees.json"),
            os.path.join(os.getcwd(), "backend", "employees.json"),
            "employees.json",
        ]
        
        employees_file = None
        for path in possible_paths:
            if os.path.exists(path):
                employees_file = path
                break
        
        if not employees_file:
            raise HTTPException(status_code=404, detail="Employees file not found")
        
        logger.info(f"🔍 Updating region {region_code} with data: {update_data}")
        logger.info(f"📂 Employees file path: {employees_file}")
        logger.info(f"📂 Absolute path: {os.path.abspath(employees_file)}")
        
        # Load current employees
        with open(employees_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"📊 Loaded {len(data.get('employees', []))} employees from file")
        
        # Validate region code
        valid_regions = ["BKK", "E", "N", "S", "NE", "C"]
        if region_code not in valid_regions:
            raise HTTPException(status_code=404, detail=f"Region {region_code} not found")
        
        # Get new RM employee ID
        new_rm_id = update_data.get("rm_employee_id")
        if not new_rm_id:
            raise HTTPException(status_code=400, detail="rm_employee_id is required")
        
        logger.info(f"🎯 Target: Change RM employee_id to {new_rm_id} for region {region_code}")
        
        # Find current RM for this region
        current_rm_index = None
        old_rm_id = None
        for idx, emp in enumerate(data.get("employees", [])):
            if emp.get("region") == region_code and emp.get("role") == "RM":
                current_rm_index = idx
                old_rm_id = emp.get("employee_id")
                break
        
        logger.info(f"🔍 Current RM for region {region_code}: {old_rm_id} at index {current_rm_index}")
        
        if old_rm_id == new_rm_id:
            logger.info(f"ℹ️ No change needed - employee_id is already {new_rm_id}")
            return {
                "success": True,
                "message": f"ไม่มีการเปลี่ยนแปลง - รหัสพนักงานเป็น {new_rm_id} อยู่แล้ว",
                "region_code": region_code,
                "old_rm_id": old_rm_id,
                "new_rm_id": new_rm_id
            }
        
        # Remove any duplicate employees with the new employee_id to avoid conflicts
        employees_to_keep = []
        removed_duplicates = []
        for emp in data["employees"]:
            if emp.get("employee_id") == new_rm_id:
                removed_duplicates.append(emp)
                logger.info(f"🗑️ Removing duplicate employee: {emp}")
            else:
                employees_to_keep.append(emp)
        
        data["employees"] = employees_to_keep
        
        # Now update the current RM's employee_id
        if current_rm_index is not None:
            # Find the RM again after removing duplicates
            for emp in data["employees"]:
                if emp.get("region") == region_code and emp.get("role") == "RM":
                    emp["employee_id"] = new_rm_id
                    logger.info(f"✏️ Updated RM employee_id from {old_rm_id} to {new_rm_id}")
                    break
        else:
            # No current RM found, create a new one
            from branch_region_mapping import BRANCH_REGION_MAP
            first_branch = next(
                (branch for branch, reg in BRANCH_REGION_MAP.items() if reg == region_code),
                "90HO"
            )
            
            new_employee = {
                "employee_id": new_rm_id,
                "branch": first_branch,
                "region": region_code,
                "role": "RM"
            }
            data["employees"].append(new_employee)
            logger.info(f"➕ Created new RM {new_rm_id} for region {region_code} with branch {first_branch}")
        
        # Save to file
        logger.info(f"💾 Saving changes to {employees_file}")
        with open(employees_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Region {region_code} RM employee_id updated from {old_rm_id} to {new_rm_id} by {employee.get('employee_id')}")
        
        return {
            "success": True,
            "message": f"อัพเดทรหัสพนักงาน RM สำหรับภาค {region_code} สำเร็จ",
            "region_code": region_code,
            "old_rm_id": old_rm_id,
            "new_rm_id": new_rm_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating region manager: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Folder Path Validation Endpoints ====================

class FolderValidationRequest(BaseModel):
    """Request to validate folder path"""
    folder_path: str


class FolderValidationResponse(BaseModel):
    """Response from folder validation"""
    is_valid: bool
    message: str
    absolute_path: Optional[str] = None


@router.post("/validate-folder", response_model=FolderValidationResponse)
async def validate_folder_path(
    request: FolderValidationRequest,
    employee: dict = Depends(get_current_employee)
):
    """
    Validate if a folder path is valid and writable.
    Only accessible to admin users.
    
    Request body:
    {
        "folder_path": "./uploads/project_files"
    }
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can validate folders")
    
    try:
        from file_storage_config import FileStorageConfig
        
        folder_path = request.folder_path.strip()
        if not folder_path:
            return FolderValidationResponse(
                is_valid=False,
                message="Folder path cannot be empty"
            )
        
        is_valid, message = FileStorageConfig.validate_folder_path(folder_path)
        
        # Get absolute path
        from pathlib import Path
        path = Path(folder_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        
        return FolderValidationResponse(
            is_valid=is_valid,
            message=message,
            absolute_path=str(path)
        )
    
    except Exception as e:
        logger.error(f"Error validating folder: {str(e)}")
        return FolderValidationResponse(
            is_valid=False,
            message=f"Error validating folder: {str(e)}"
        )

