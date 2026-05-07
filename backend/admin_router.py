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

from fastapi import APIRouter, UploadFile, File, HTTPException, Query as QueryParam, Depends
from pydantic import BaseModel

from config.db_mssql import get_mssql_conn
from services.price_upload_service import PriceUploadService, ValidationError
from auth_dependency import get_employee_info


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
    branch_code: str = QueryParam(..., description="Branch code(s) for price data (comma-separated)"),
    employee_info: dict = Depends(get_employee_info)
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
    logger.info(f"Uploaded by: {employee_info.get('employee_id')} ({employee_info.get('name')}), Role: {employee_info.get('role')}")
    
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
            result = service.process_upload(
                file_path=temp_path,
                branch_code=branch,
                employee_info=employee_info  # ⭐ ส่งข้อมูล employee
            )
            
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


@router.post("/prices/schedule", response_model=UploadResponse) #Schedule Price Upload
async def schedule_price_upload(
    file: UploadFile = File(...),
    branch_code: str = QueryParam(..., description="Branch code(s) for price data (comma-separated)"),
    scheduled_date: str = QueryParam(..., description="Scheduled date in YYYY-MM-DD format"),
    employee_info: dict = Depends(get_employee_info)
):
    """
    Schedule price file upload for a future date.
    
    Process:
    1. Validate file format and scheduled date
    2. Detect category from file content (G, A, Y, S, C, E)
    3. Save file with naming convention: {Category}{DDMMYYYY}.xlsx
    4. Store file in configured SCHEDULED_UPLOAD_FOLDER
    5. Standalone job will process files on scheduled date
    
    Args:
        file: Uploaded file (CSV or Excel)
        branch_code: Branch code(s) for price data (comma-separated)
        scheduled_date: Date to upload (YYYY-MM-DD format)
    
    Returns:
        UploadResponse with success message
    
    Raises:
        HTTPException 400: When validation fails
        HTTPException 500: When file save fails
    """
    import pandas as pd
    from datetime import datetime
    
    logger.info(f"Received scheduled price upload request")
    logger.info(f"Scheduled date: {scheduled_date}, Branches: {branch_code}")
    logger.info(f"Uploaded by: {employee_info.get('employee_id')} ({employee_info.get('name')})")
    
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: {file_ext}. Supported: .csv, .xlsx, .xls"
        )
    
    # Validate scheduled date
    try:
        scheduled_dt = datetime.strptime(scheduled_date, "%Y-%m-%d")
        if scheduled_dt.date() < datetime.now().date():
            raise HTTPException(status_code=400, detail="Scheduled date cannot be in the past")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Parse branch codes
    branch_codes = [b.strip() for b in branch_code.split(",") if b.strip()]
    if not branch_codes:
        raise HTTPException(status_code=400, detail="No valid branch codes provided")
    
    # Save to temporary file first to read content
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        logger.info(f"Saved uploaded file to temporary location: {temp_path}")
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Detect category from file content
    try:
        # Read Excel file
        if file_ext == ".csv":
            df = pd.read_csv(temp_path)
        else:
            df = pd.read_excel(temp_path)
        
        # Find SKU column
        sku_column = None
        for col_name in ["SKU", "No_", "Item_No", "No", "ItemNo"]:
            if col_name in df.columns:
                sku_column = col_name
                break
        
        if not sku_column:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail="SKU column not found in file")
        
        # Detect category from first SKU
        categories = set()
        for idx, row in df.iterrows():
            sku = str(row.get(sku_column, "")).strip()
            if sku and len(sku) > 0:
                category = sku[0].upper()
                if category in ['G', 'A', 'Y', 'S', 'C', 'E']:
                    categories.add(category)
        
        if not categories:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail="No valid SKU categories found (G, A, Y, S, C, E)")
        
        # Use first category or MIXED if multiple
        if len(categories) == 1:
            category = list(categories)[0]
        else:
            category = "MIXED"
        
        logger.info(f"Detected category: {category}")
        
    except HTTPException:
        raise
    except Exception as e:
        os.remove(temp_path)
        logger.error(f"Failed to detect category: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
    
    # Generate filename: {Category}{DDMMYYYY}.xlsx
    # Format date as DDMMYYYY (Buddhist year)
    day = scheduled_dt.strftime("%d")
    month = scheduled_dt.strftime("%m")
    year_buddhist = str(scheduled_dt.year + 543)  # Convert to Buddhist year
    filename = f"{category}{day}{month}{year_buddhist}.xlsx"
    
    # Get folder path from environment variable (set by config_router.py)
    scheduled_folder = os.getenv("PRICE_FILES_FOLDER", "./uploads/price_files")
    logger.info(f"Using price files folder from config: {scheduled_folder}")
    
    # Create folder if not exists
    try:
        os.makedirs(scheduled_folder, exist_ok=True)
    except Exception as e:
        os.remove(temp_path)
        logger.error(f"Failed to create scheduled upload folder: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create folder: {str(e)}")
    
    # Move file to scheduled folder
    final_path = os.path.join(scheduled_folder, filename)
    try:
        # If file already exists, add timestamp to make it unique
        if os.path.exists(final_path):
            timestamp = datetime.now().strftime("%H%M%S")
            filename_base, filename_ext = os.path.splitext(filename)
            filename = f"{filename_base}_{timestamp}{filename_ext}"
            final_path = os.path.join(scheduled_folder, filename)
        
        # Move file
        os.rename(temp_path, final_path)
        logger.info(f"Saved scheduled upload file: {final_path}")
        
        # Save metadata to a companion JSON file
        import json
        metadata = {
            "filename": filename,
            "scheduled_date": scheduled_date,
            "branch_codes": branch_codes,
            "category": category,
            "uploaded_by": employee_info.get('employee_id'),
            "uploaded_by_name": employee_info.get('name'),
            "uploaded_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        metadata_path = final_path + ".meta.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved metadata: {metadata_path}")
        
    except Exception as e:
        # Clean up temp file if move fails
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Failed to save scheduled upload file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    return UploadResponse(
        success=True,
        message=f"Scheduled upload saved successfully. File will be processed on {scheduled_date}",
        total_rows=0,
        successful_updates=0,
        errors=0,
        error_details=[]
    )



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
