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
import requests

from auth_dependency import get_employee_info
from config.config_external_api import (
    CUSTOMER_API_URL, CUSTOMER_API_HEADERS,
    INVOICE_API_URL, INVOICE_API_HEADERS,
    CREDIT_API_URL, CREDIT_API_HEADERS,
    EMP_API_URL, EMP_API_HEADERS,
    LOCATION_API_URL, LOCATION_API_HEADERS,
    ITEMCOST_API_URL, ITEMCOST_API_HEADERS,
    REMAININGCREDIT_URL, REMAININGCREDIT_HEADERS,
    SDM_THRESHOLD_PRICE, BASE_URL
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Config"])


# ==================== Models ====================

class APIConfig(BaseModel):
    """API Configuration"""
    name: str
    url: str
    key: str
    status: Optional[str] = None


class RoleApprovalScope(BaseModel):
    """Role Approval Scope Configuration"""
    min_level: str  # R2, R1, W2, W1, SDM
    max_level: str  # R2, R1, W2, W1, SDM


class PriceConfig(BaseModel):
    """Price Configuration"""
    sdm_threshold_price: float
    price_levels: Dict[str, float] = {}
    role_approval_scope: Dict[str, RoleApprovalScope] = {}


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


class ConfigResponse(BaseModel):
    """Complete Configuration Response"""
    api_configs: Dict[str, APIConfig]
    price_config: PriceConfig
    access_control: AccessControlConfig
    system_config: SystemConfig


class APIStatusResponse(BaseModel):
    """API Status Response"""
    api_name: str
    url: str
    status: str  # "connected", "disconnected", "error"
    message: str


# ==================== Helper Functions ====================

def get_current_employee(request: Request, authorization: str = Header(None)) -> dict:
    """Get current employee from JWT token"""
    return get_employee_info(request, authorization)


def check_admin_role(employee_info: dict) -> bool:
    """Check if user has admin role"""
    role = employee_info.get("role", "").lower()
    return role == "admin"


def test_api_connection(url: str, headers: dict, timeout: int = 5) -> tuple[bool, str]:
    """Test API connection"""
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code in [200, 401, 403]:
            return True, "Connected"
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection Error"
    except Exception as e:
        return False, str(e)


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
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can access config")
    
    try:
        # API Configurations
        api_configs = {
            "customer_api": APIConfig(
                name="Customer API",
                url=CUSTOMER_API_URL,
                key=os.getenv("CUSTOMER_API_KEY", "")
            ),
            "invoice_api": APIConfig(
                name="Invoice API",
                url=INVOICE_API_URL,
                key=os.getenv("INVOICE_API_KEY", "")
            ),
            "credit_api": APIConfig(
                name="Credit API",
                url=CREDIT_API_URL,
                key=os.getenv("CREDIT_API_KEY", "")
            ),
            "employee_api": APIConfig(
                name="Employee API",
                url=EMP_API_URL,
                key=os.getenv("EMP_API_KEY", "")
            ),
            "location_api": APIConfig(
                name="Location API",
                url=LOCATION_API_URL,
                key=os.getenv("LOCATION_API_KEY", "")
            ),
            "itemcost_api": APIConfig(
                name="Item Cost API",
                url=ITEMCOST_API_URL,
                key=os.getenv("ITEM_COST_API_KEY", "")
            ),
            "remaining_credit_api": APIConfig(
                name="Remaining Credit API",
                url=REMAININGCREDIT_URL,
                key=os.getenv("REMAININGCREDIT_KEY", "")
            ),
        }
        
        # Price Configuration
        # Load role_approval_scope from cache first, then environment
        from config_cache import get_role_approval_scope
        role_approval_scope_dict = get_role_approval_scope()
        role_approval_scope = {
            role: RoleApprovalScope(**scope) 
            for role, scope in role_approval_scope_dict.items()
        }
        
        price_config = PriceConfig(
            sdm_threshold_price=SDM_THRESHOLD_PRICE,
            price_levels={
                "SDM": 0,
                "R2": 0,
                "R1": 0,
                "W2": 0,
                "W1": 0
            },
            role_approval_scope=role_approval_scope
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
        system_config = SystemConfig(
            base_url=BASE_URL,
            timezone=os.getenv("TIMEZONE", "Asia/Bangkok"),
            language=os.getenv("LANGUAGE", "th"),
            version=os.getenv("APP_VERSION", "1.0.0")
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


@router.get("/api-status", response_model=list[APIStatusResponse])
async def get_api_status(employee: dict = Depends(get_current_employee)):
    """
    Check API connectivity status.
    Only accessible to admin users.
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can access config")
    
    apis = [
        ("Customer API", CUSTOMER_API_URL, CUSTOMER_API_HEADERS),
        ("Invoice API", INVOICE_API_URL, INVOICE_API_HEADERS),
        ("Credit API", CREDIT_API_URL, CREDIT_API_HEADERS),
        ("Employee API", EMP_API_URL, EMP_API_HEADERS),
        ("Location API", LOCATION_API_URL, LOCATION_API_HEADERS),
        ("Item Cost API", ITEMCOST_API_URL, ITEMCOST_API_HEADERS),
        ("Remaining Credit API", REMAININGCREDIT_URL, REMAININGCREDIT_HEADERS),
    ]
    
    results = []
    for api_name, url, headers in apis:
        is_connected, message = test_api_connection(url, headers)
        status = "connected" if is_connected else "disconnected"
        results.append(APIStatusResponse(
            api_name=api_name,
            url=url,
            status=status,
            message=message
        ))
    
    return results


@router.put("/settings", response_model=dict)
async def update_config(
    config_data: Dict[str, Any],
    employee: dict = Depends(get_current_employee)
):
    """
    Update system configuration.
    Only accessible to admin users.
    
    Supported updates:
    - api_configs (all API URLs and keys)
    - price_config.sdm_threshold_price
    - price_config.role_approval_scope
    - access_control.price_update_employees
    - access_control.project_price_employees
    - access_control.special_price_approvers
    - access_control.page_access
    - system_config.base_url
    - system_config.timezone
    - system_config.language
    """
    if not check_admin_role(employee):
        raise HTTPException(status_code=403, detail="Only admin can update config")
    
    try:
        import json
        from config_cache import set_page_access_config, set_role_approval_scope
        
        # Update environment variables (in-memory only, not persisted)
        # For production, you should update .env file or use a database
        
        # Update API configurations
        if "api_configs" in config_data:
            api_cfgs = config_data["api_configs"]
            
            # Customer API
            if "customer_api" in api_cfgs:
                if "url" in api_cfgs["customer_api"]:
                    os.environ["CUSTOMER_API_URL"] = api_cfgs["customer_api"]["url"]
                if "key" in api_cfgs["customer_api"]:
                    os.environ["CUSTOMER_API_KEY"] = api_cfgs["customer_api"]["key"]
            
            # Invoice API
            if "invoice_api" in api_cfgs:
                if "url" in api_cfgs["invoice_api"]:
                    os.environ["INVOICE_API_URL"] = api_cfgs["invoice_api"]["url"]
                if "key" in api_cfgs["invoice_api"]:
                    os.environ["INVOICE_API_KEY"] = api_cfgs["invoice_api"]["key"]
            
            # Credit API
            if "credit_api" in api_cfgs:
                if "url" in api_cfgs["credit_api"]:
                    os.environ["CREDIT_API_URL"] = api_cfgs["credit_api"]["url"]
                if "key" in api_cfgs["credit_api"]:
                    os.environ["CREDIT_API_KEY"] = api_cfgs["credit_api"]["key"]
            
            # Employee API
            if "employee_api" in api_cfgs:
                if "url" in api_cfgs["employee_api"]:
                    os.environ["EMP_API_URL"] = api_cfgs["employee_api"]["url"]
                if "key" in api_cfgs["employee_api"]:
                    os.environ["EMP_API_KEY"] = api_cfgs["employee_api"]["key"]
            
            # Location API
            if "location_api" in api_cfgs:
                if "url" in api_cfgs["location_api"]:
                    os.environ["LOCATION_API_URL"] = api_cfgs["location_api"]["url"]
                if "key" in api_cfgs["location_api"]:
                    os.environ["LOCATION_API_KEY"] = api_cfgs["location_api"]["key"]
            
            # Item Cost API
            if "itemcost_api" in api_cfgs:
                if "url" in api_cfgs["itemcost_api"]:
                    os.environ["ITEMCOST_API_URL"] = api_cfgs["itemcost_api"]["url"]
                if "key" in api_cfgs["itemcost_api"]:
                    os.environ["ITEM_COST_API_KEY"] = api_cfgs["itemcost_api"]["key"]
            
            # Remaining Credit API
            if "remaining_credit_api" in api_cfgs:
                if "url" in api_cfgs["remaining_credit_api"]:
                    os.environ["REMAININGCREDIT_URL"] = api_cfgs["remaining_credit_api"]["url"]
                if "key" in api_cfgs["remaining_credit_api"]:
                    os.environ["REMAININGCREDIT_KEY"] = api_cfgs["remaining_credit_api"]["key"]
        
        if "price_config" in config_data:
            price_cfg = config_data["price_config"]
            if "sdm_threshold_price" in price_cfg:
                os.environ["SDM_THRESHOLD_PRICE"] = str(price_cfg["sdm_threshold_price"])
            
            # Store role_approval_scope in cache (immediate effect)
            if "role_approval_scope" in price_cfg:
                set_role_approval_scope(price_cfg["role_approval_scope"])
                # Also store in environment for persistence
                os.environ["ROLE_APPROVAL_SCOPE"] = json.dumps(price_cfg["role_approval_scope"])
        
        if "access_control" in config_data:
            ac = config_data["access_control"]
            if "price_update_employees" in ac:
                os.environ["ALLOWED_PRICE_UPDATE_EMPLOYEES"] = ",".join(ac["price_update_employees"])
            if "project_price_employees" in ac:
                os.environ["ALLOWED_PROJECT_PRICE_EMPLOYEES"] = ",".join(ac["project_price_employees"])
            if "special_price_approvers" in ac:
                os.environ["ALLOWED_SPECIAL_PRICE_APPROVERS"] = ",".join(ac["special_price_approvers"])
            
            # Store page_access configuration in cache (immediate effect)
            if "page_access" in ac:
                set_page_access_config(ac["page_access"])
                # Also store in environment for persistence
                os.environ["PAGE_ACCESS_CONFIG"] = json.dumps(ac["page_access"])
        
        if "system_config" in config_data:
            sys_cfg = config_data["system_config"]
            if "timezone" in sys_cfg:
                os.environ["TIMEZONE"] = sys_cfg["timezone"]
            if "language" in sys_cfg:
                os.environ["LANGUAGE"] = sys_cfg["language"]
        
        logger.info(f"Config updated by {employee.get('employee_id')}")
        
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
        
        # Store in environment (for production, use database)
        import json
        custom_roles_str = os.getenv("CUSTOM_ROLES", "{}")
        custom_roles = json.loads(custom_roles_str)
        
        custom_roles[role_code] = {
            "thai_name": role_name_thai,
            "display_name": role_display_name or role_code
        }
        
        os.environ["CUSTOM_ROLES"] = json.dumps(custom_roles)
        
        logger.info(f"Role {role_code} created by {employee.get('employee_id')}")
        
        return {
            "success": True,
            "message": f"Role {role_code} created successfully",
            "role_code": role_code
        }
    
    except Exception as e:
        logger.error(f"Error creating role: {str(e)}")
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
