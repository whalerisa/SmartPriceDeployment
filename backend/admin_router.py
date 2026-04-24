"""
Admin Router

This router provides admin endpoints for price management.

Endpoints:
- POST /admin/prices/upload - Upload price file (CSV or Excel) and update Item_Price table
"""

import logging
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query as QueryParam
from pydantic import BaseModel

from config.db_mssql import get_mssql_conn
from services.price_upload_service import PriceUploadService, ValidationError


# Configure logging
logger = logging.getLogger(__name__)


# Initialize router
router = APIRouter(prefix="/admin", tags=["Admin"])


# Response models
class UploadResponse(BaseModel):
    """Response for price upload endpoint"""
    success: bool
    message: str
    total_rows: int
    successful_updates: int
    errors: int
    error_details: list[str]


@router.post("/prices/upload", response_model=UploadResponse) #Upload Excel ราคา
async def upload_prices(
    file: UploadFile = File(...),
    branch_code: str = QueryParam(..., description="Branch code(s) for price data (comma-separated)")
):
    """
    Upload price file (CSV or Excel) and update Item_Price table.
    
    Process:
    1. Validate file format (CSV, XLSX, XLS)
    2. Validate required columns (SKU, SDM, R2, R1, W2, W1)
    3. For each branch code:
       - For each row:
         - Validate SKU exists in Item_Master
         - Upsert to Item_Price table (update if exists, insert if not)
         - Set UpdatedAt timestamp
    4. Return summary with total_rows, successful_updates, errors
    
    Args:
        file: Uploaded file (CSV or Excel)
        branch_code: Branch code(s) for price data (comma-separated, e.g., "00TR,05AY")
    
    Returns:
        UploadResponse with statistics and error details
    
    Raises:
        HTTPException 400: When file format is invalid or required columns missing
        HTTPException 500: When database operation fails
    """
    logger.info(f"Received price upload request for branches: {branch_code}")
    
    # Parse branch codes
    branch_codes = [b.strip() for b in branch_code.split(",") if b.strip()]
    if not branch_codes:
        raise HTTPException(status_code=400, detail="No valid branch codes provided")
    
    logger.info(f"Processing upload for {len(branch_codes)} branch(es): {branch_codes}")
    
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_ext}. Supported: .csv, .xlsx, .xls"
        )
    
    # Save uploaded file to temporary location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        logger.info(f"Saved uploaded file to: {temp_path}")
    
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Process upload for each branch
    try:
        conn = get_mssql_conn()
        service = PriceUploadService(conn)
        
        total_rows = 0
        total_successful = 0
        total_errors = 0
        all_error_details = []
        
        for branch in branch_codes:
            logger.info(f"Processing upload for branch: {branch}")
            result = service.process_upload(temp_path, branch)
            
            total_rows += result.total_rows
            total_successful += result.successful_updates
            total_errors += result.errors
            all_error_details.extend(result.error_details)
            
            logger.info(
                f"Branch {branch}: successful={result.successful_updates}, errors={result.errors}"
            )
        
        conn.close()
        
        # Build response
        success = total_errors == 0
        message = (
            f"Successfully uploaded {total_successful} prices across {len(branch_codes)} branch(es)"
            if success
            else f"Uploaded {total_successful} prices with {total_errors} errors across {len(branch_codes)} branch(es)"
        )
        
        logger.info(
            f"Price upload completed: success={success}, "
            f"total={total_rows}, successful={total_successful}, "
            f"errors={total_errors}, branches={len(branch_codes)}"
        )
        
        return UploadResponse(
            success=success,
            message=message,
            total_rows=total_rows,
            successful_updates=total_successful,
            errors=total_errors,
            error_details=all_error_details
        )
    
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Failed to process upload: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")
    
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.debug(f"Removed temporary file: {temp_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary file: {str(e)}")



# =====================================================
# EMPLOYEE ACCESS CONTROL ENDPOINTS
# =====================================================

class EmployeeAccessResponse(BaseModel):
    """Response for employee access control"""
    allowed_price_update_employees: list[str]
    allowed_project_price_employees: list[str]


@router.get("/employee-access", response_model=EmployeeAccessResponse) #ดึงรายชื่อพนักงานที่มีสิทธิ์เข้าถึงฟีเจอร์บางอย่าง
def get_employee_access():
    """
    Get employee access control lists from environment variables.
    
    Returns:
        EmployeeAccessResponse with lists of allowed employee IDs
    """
    # Get from environment variables
    price_update_str = os.getenv("ALLOWED_PRICE_UPDATE_EMPLOYEES", "")
    project_price_str = os.getenv("ALLOWED_PROJECT_PRICE_EMPLOYEES", "")
    
    # Debug log
    logger.info(f"🔍 Raw ALLOWED_PRICE_UPDATE_EMPLOYEES: {price_update_str}")
    logger.info(f"🔍 Raw ALLOWED_PROJECT_PRICE_EMPLOYEES: {project_price_str}")
    
    # Parse comma-separated strings into lists
    price_update_employees = [e.strip() for e in price_update_str.split(",") if e.strip()]
    project_price_employees = [e.strip() for e in project_price_str.split(",") if e.strip()]
    
    logger.info(f"✅ Retrieved employee access: {len(price_update_employees)} price update, {len(project_price_employees)} project price")
    logger.info(f"✅ Price Update: {price_update_employees}")
    logger.info(f"✅ Project Price: {project_price_employees}")
    
    return EmployeeAccessResponse(
        allowed_price_update_employees=price_update_employees,
        allowed_project_price_employees=project_price_employees
    )
