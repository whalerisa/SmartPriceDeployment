# auth_dependency.py
from fastapi import Header, Request
import jwt
import os
import logging
from role_mapping import map_thai_role_to_code
from branch_region_mapping import get_region_from_branch

logger = logging.getLogger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-this")
JWT_ALG = "HS256"


def get_branch_code(request: Request, authorization: str = Header(None)) -> str:
    """
    Extract branch code from JWT token in cookies or Authorization header.
    
    Returns:
        Branch code from token, or "00TR" as default if no token provided
    """
    token = request.cookies.get("auth_token")
    if not token and authorization:
        token = authorization.replace("Bearer ", "").strip()

    if not token:
        logger.info("No auth_token cookie or Authorization header provided, using default branch 00TR")
        return "00TR"  # Default branch
    
    try:
        
        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        
        # Get branchId from payload
        branch_id = payload.get("branchId")
        
        if not branch_id:
            logger.warning("No branchId in token, using default branch 00TR")
            return "00TR"  # Default if no branchId in token
        
        logger.info(f"Extracted branch code from token: {branch_id}")
        return branch_id
    
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired, using default branch 00TR")
        return "00TR"  # Don't raise error, just use default
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}, using default branch 00TR")
        return "00TR"  # Don't raise error, just use default
    except Exception as e:
        logger.error(f"Error extracting branch code: {e}, using default branch 00TR")
        return "00TR"  # Default on any error


def get_employee_info(request: Request, authorization: str = Header(None)) -> dict:
    """
    Extract employee information from JWT token in cookies or Authorization header.
    Now uses role from token and maps Thai role names to internal codes.
    
    Returns:
        Dictionary with employee_id, name, branch_code, role (mapped), and region (derived from branch)
    """
    default_info = {
        "employee_id": "UNKNOWN",
        "name": "Unknown User",
        "branch_code": "00TR",
        "role": "Sales",
        "region": "BE"  # Default region for 00TR
    }
    
    token = request.cookies.get("auth_token")
    if not token and authorization:
        token = authorization.replace("Bearer ", "").strip()

    if not token:
        logger.info("No auth_token cookie or Authorization header provided, using default employee info")
        return default_info
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        
        logger.debug(f"[JWT] Payload keys: {list(payload.keys())}")
        
        # Extract employee_id from "sub" field (JWT standard)
        employee_id = payload.get("sub")
        if not employee_id:
            employee_id = payload.get("employeeId") or payload.get("employee_id") or payload.get("id") or "UNKNOWN"
        employee_id = str(employee_id) if employee_id != "UNKNOWN" else "UNKNOWN"
        
        # Extract name
        name = payload.get("name") or payload.get("username") or payload.get("fullName") or "Unknown User"
        
        # Extract branchId
        branch_code = payload.get("branchId") or payload.get("branch_code") or payload.get("branch") or "00TR"
        
        # Extract role from token (NEW: supports nested role object)
        role_internal = "Sales"  # Default
        thai_role_name = None
        
        # Check if role is in nested object format: {"role": {"app": "Smart Quotation", "role": "พนักงานขาย"}}
        role_obj = payload.get("role")
        if isinstance(role_obj, dict):
            # Nested role object
            if role_obj.get("app") == "Smart Quotation":
                thai_role_name = role_obj.get("role")
                if thai_role_name:
                    role_internal = map_thai_role_to_code(thai_role_name)
                    logger.info(f"[JWT] Mapped Thai role '{thai_role_name}' to '{role_internal}'")
        elif isinstance(role_obj, str):
            # Direct string role (could be Thai or English)
            thai_role_name = role_obj
            role_internal = map_thai_role_to_code(thai_role_name)
            logger.info(f"[JWT] Mapped role '{thai_role_name}' to '{role_internal}'")
        
        # Fallback: check old format (roles array or direct role field)
        if not thai_role_name:
            role_data = payload.get("roles") or payload.get("role")
            if isinstance(role_data, list) and len(role_data) > 0:
                if isinstance(role_data[0], dict):
                    role_internal = role_data[0].get("role", "Sales")
                else:
                    role_internal = role_data[0]
            elif isinstance(role_data, str):
                role_internal = role_data
            else:
                role_internal = payload.get("position") or "Sales"
        
        # Derive region from branch code (NEW: using branch_region_mapping)
        region = get_region_from_branch(branch_code)
        logger.info(f"[JWT] Derived region '{region}' from branch '{branch_code}'")
        
        employee_info = {
            "employee_id": employee_id,
            "name": name,
            "branch_code": branch_code,
            "role": role_internal,  # Internal role code (Sales, ZM, RM, SDM, PM, CEO)
            "region": region,  # Derived from branch
            "thai_role_name": thai_role_name  # Keep original Thai name for reference
        }
        
        logger.info(
            f"[JWT] Extracted: employee_id={employee_id}, name={name}, "
            f"branch={branch_code}, role={role_internal}, region={region}, "
            f"thai_role_name={thai_role_name}"
        )
        
        return employee_info
    
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired, using default employee info")
        return default_info
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}, using default employee info")
        return default_info
    except Exception as e:
        logger.error(f"Error extracting employee info: {e}, using default employee info")
        import traceback
        traceback.print_exc()
        return default_info
