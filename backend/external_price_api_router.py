"""
External Price API Router

This router provides API endpoints for external systems to update prices.
Designed for integration with external price management systems.

Authentication: API Key based authentication
Rate Limiting: Recommended to implement rate limiting in production

Endpoints:
- POST /external/prices/update - Update prices for one or more SKUs
- POST /external/prices/bulk-update - Bulk update prices from JSON array
- GET /external/prices/status/{version_id} - Check upload status
"""

import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field, validator

from config.db_mssql import get_mssql_conn


# Configure logging
logger = logging.getLogger(__name__)


# Initialize router
router = APIRouter(prefix="/external/prices", tags=["External Price API"])


# ==================== Authentication ====================
# Authentication disabled - API is open for all requests
# To enable authentication, uncomment the verify_api_key function and add Depends(verify_api_key) to endpoints

# def verify_api_key(x_api_key: str = Header(..., description="API Key for authentication")):
#     """
#     Verify API key from request header.
#     
#     Args:
#         x_api_key: API key from X-API-Key header
#         
#     Returns:
#         API key if valid
#         
#     Raises:
#         HTTPException 401: If API key is invalid
#     """
#     # Get valid API keys from environment variable
#     valid_api_keys = os.getenv("EXTERNAL_API_KEYS", "").split(",")
#     valid_api_keys = [key.strip() for key in valid_api_keys if key.strip()]
#     
#     if not valid_api_keys:
#         logger.error("No API keys configured in EXTERNAL_API_KEYS environment variable")
#         raise HTTPException(
#             status_code=500,
#             detail="API keys not configured. Contact system administrator."
#         )
#     
#     if x_api_key not in valid_api_keys:
#         logger.warning(f"Invalid API key attempt: {x_api_key[:10]}...")
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid API key"
#         )
#     
#     logger.info(f"API key verified: {x_api_key[:10]}...")
#     return x_api_key


# ==================== Request/Response Models ====================

class PriceData(BaseModel):
    """Price data for a single SKU"""
    sku: str = Field(..., description="SKU code", min_length=1, max_length=50)
    branch_code: str = Field(..., description="Branch code (e.g., '00TR', '05AY')", min_length=2, max_length=10)
    sdm: Optional[float] = Field(None, description="SDM price level", ge=0)
    r2: Optional[float] = Field(None, description="R2 price level", ge=0)
    r1: Optional[float] = Field(None, description="R1 price level", ge=0)
    w2: Optional[float] = Field(None, description="W2 price level", ge=0)
    w1: Optional[float] = Field(None, description="W1 price level", ge=0)
    package_size: Optional[float] = Field(1, description="Package size (default: 1)", ge=0)
    alternate_name: Optional[str] = Field(None, description="Alternate product name", max_length=200)
    
    @validator('sku')
    def sku_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('SKU cannot be empty')
        return v.strip().upper()
    
    @validator('branch_code')
    def branch_code_must_be_valid(cls, v):
        if not v or not v.strip():
            raise ValueError('Branch code cannot be empty')
        return v.strip().upper()


class BulkPriceUpdateRequest(BaseModel):
    """Request for bulk price update"""
    prices: List[PriceData] = Field(..., description="List of price records to update", min_items=1, max_items=10000)
    uploaded_by: str = Field("external_api", description="Identifier of the uploader", max_length=50)
    job_title: str = Field("EXTERNAL", description="Job title of uploader", max_length=50)
    update_type: Optional[str] = Field(None, description="Update type (G, A, Y, S, C, E, or MIXED)")
    
    @validator('prices')
    def validate_prices_limit(cls, v):
        if len(v) > 10000:
            raise ValueError('Maximum 10000 price records per request')
        return v


class PriceUpdateResponse(BaseModel):
    """Response for price update"""
    success: bool
    message: str
    version_id: Optional[int] = None
    total_records: int
    successful_updates: int
    failed_updates: int
    errors: List[str] = []


class VersionStatusResponse(BaseModel):
    """Response for version status check"""
    version_id: int
    version_name: str
    update_type: str
    uploaded_by: str
    uploaded_at: str
    status: str
    total_records: int
    records_with_price_change: int
    records_with_name_change: int


# ==================== Helper Functions ====================

def get_db_connection():
    """Get database connection"""
    return get_mssql_conn()


def sku_exists(conn, sku: str) -> bool:
    """Check if SKU exists in Item_Master"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM Item_Master WHERE SKU = ?", (sku,))
        count = cursor.fetchone()[0]
        return count > 0
    finally:
        cursor.close()


def create_version_log(conn, update_type: str, uploaded_by: str, job_title: str) -> int:
    """
    Create version log in Item_Update_Version
    
    Returns:
        version_id
    """
    cursor = conn.cursor()
    try:
        # Generate version name
        now = datetime.now()
        version_name = f"API_{now.strftime('%Y%m%d_%H%M%S')}"
        
        # Get next version_id
        cursor.execute("SELECT ISNULL(MAX(version_id), 0) + 1 FROM Item_Update_Version")
        version_id = int(cursor.fetchone()[0])
        
        uploaded_at = datetime.now()
        
        # Insert version log
        cursor.execute("""
            INSERT INTO Item_Update_Version (
                version_id, version_name, update_type, uploaded_by, job_title, 
                uploaded_at, status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
        """, (version_id, version_name, update_type, uploaded_by, job_title, uploaded_at))
        
        conn.commit()
        
        logger.info(f"Created version log: {version_id} ({version_name}), type: {update_type}")
        return version_id
        
    except Exception as e:
        logger.error(f"Failed to create version log: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()


def upsert_price_record(conn, price_data: PriceData, version_id: int) -> tuple[bool, str]:
    """
    Upsert price record and create detail log
    
    Returns:
        (success: bool, error_message: str)
    """
    cursor = conn.cursor()
    try:
        sku = price_data.sku
        branch_code = price_data.branch_code
        
        # Get old prices
        cursor.execute("""
            SELECT R1, R2, W1, W2, AlternateName
            FROM Item_Price WITH (NOLOCK)
            WHERE SKU = ? AND BranchCode = ?
        """, (sku, branch_code))
        
        old_row = cursor.fetchone()
        if old_row:
            old_R1, old_R2, old_W1, old_W2, old_alternate_name = old_row
            exists = True
        else:
            old_R1 = old_R2 = old_W1 = old_W2 = old_alternate_name = None
            exists = False
        
        # New prices
        new_R1 = price_data.r1
        new_R2 = price_data.r2
        new_W1 = price_data.w1
        new_W2 = price_data.w2
        new_alternate_name = price_data.alternate_name
        
        # Calculate change flags
        change_price_flag = 0
        if exists:
            if (old_R1 != new_R1 or old_R2 != new_R2 or 
                old_W1 != new_W1 or old_W2 != new_W2):
                change_price_flag = 1
        else:
            change_price_flag = 1
        
        change_altname_flag = 0
        if exists:
            if old_alternate_name != new_alternate_name:
                change_altname_flag = 1
        else:
            if new_alternate_name:
                change_altname_flag = 1
        
        # Update or Insert price
        if exists:
            cursor.execute("""
                UPDATE Item_Price
                SET SDM = ?,
                    R2 = ?,
                    R1 = ?,
                    W2 = ?,
                    W1 = ?,
                    PackageSize = ?,
                    AlternateName = ?,
                    UpdatedAt = GETDATE()
                WHERE SKU = ? AND BranchCode = ?
            """, (
                price_data.sdm,
                price_data.r2,
                price_data.r1,
                price_data.w2,
                price_data.w1,
                price_data.package_size,
                price_data.alternate_name,
                sku,
                branch_code
            ))
        else:
            cursor.execute("""
                INSERT INTO Item_Price (
                    SKU, BranchCode, SDM, R2, R1, W2, W1, PackageSize, AlternateName, UpdatedAt
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
            """, (
                sku,
                branch_code,
                price_data.sdm,
                price_data.r2,
                price_data.r1,
                price_data.w2,
                price_data.w1,
                price_data.package_size,
                price_data.alternate_name
            ))
        
        # Create detail log
        cursor.execute("SELECT ISNULL(MAX(id), 0) + 1 FROM Item_Update_Version_Detail")
        detail_id = int(cursor.fetchone()[0])
        
        cursor.execute("""
            INSERT INTO Item_Update_Version_Detail (
                id, version_id, sku, new_no2, 
                new_R1, new_R2, new_W1, new_W2,
                old_R1, old_R2, old_W1, old_W2,
                new_alternate_name, old_alternate_name,
                change_price_flag, change_altname_flag,
                BranchCode
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            detail_id,
            version_id,
            sku,
            new_alternate_name,
            new_R1, new_R2, new_W1, new_W2,
            old_R1, old_R2, old_W1, old_W2,
            new_alternate_name,
            old_alternate_name,
            change_price_flag,
            change_altname_flag,
            branch_code
        ))
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Failed to upsert price for SKU {price_data.sku}: {e}")
        return False, str(e)
    finally:
        cursor.close()


# ==================== API Endpoints ====================

@router.post("/update", response_model=PriceUpdateResponse)
async def update_single_price(
    price_data: PriceData,
    uploaded_by: str = "external_api"
):
    """
    Update price for a single SKU.
    
    This endpoint allows external systems to update price for one SKU at a time.
    **No authentication required** - Open API
    
    **Request Body:**
    ```json
    {
        "sku": "G001234",
        "branch_code": "00TR",
        "sdm": 100.00,
        "r2": 110.00,
        "r1": 120.00,
        "w2": 130.00,
        "w1": 140.00,
        "package_size": 1,
        "alternate_name": "Product Name"
    }
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "message": "Price updated successfully",
        "version_id": 123,
        "total_records": 1,
        "successful_updates": 1,
        "failed_updates": 0,
        "errors": []
    }
    ```
    """
    logger.info(f"Single price update request for SKU: {price_data.sku}, Branch: {price_data.branch_code}")
    
    conn = get_db_connection()
    
    try:
        # Validate SKU exists
        if not sku_exists(conn, price_data.sku):
            raise HTTPException(
                status_code=404,
                detail=f"SKU '{price_data.sku}' not found in Item_Master"
            )
        
        # Detect update type from SKU
        update_type = price_data.sku[0].upper() if price_data.sku else "MIXED"
        if update_type not in ['G', 'A', 'Y', 'S', 'C', 'E']:
            update_type = "MIXED"
        
        # Create version log
        version_id = create_version_log(conn, update_type, uploaded_by, "EXTERNAL")
        
        # Update price
        success, error_msg = upsert_price_record(conn, price_data, version_id)
        
        if success:
            conn.commit()
            logger.info(f"Successfully updated price for SKU: {price_data.sku}")
            
            return PriceUpdateResponse(
                success=True,
                message="Price updated successfully",
                version_id=version_id,
                total_records=1,
                successful_updates=1,
                failed_updates=0,
                errors=[]
            )
        else:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update price: {error_msg}")
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating price: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        conn.close()


@router.post("/bulk-update", response_model=PriceUpdateResponse)
async def bulk_update_prices(
    request: BulkPriceUpdateRequest
):
    """
    Bulk update prices for multiple SKUs.
    
    This endpoint allows external systems to update prices for multiple SKUs in a single request.
    Maximum 10000 records per request.
    **No authentication required** - Open API
    
    **Request Body:**
    ```json
    {
        "prices": [
            {
                "sku": "G001234",
                "branch_code": "00TR",
                "sdm": 100.00,
                "r2": 110.00,
                "r1": 120.00,
                "w2": 130.00,
                "w1": 140.00,
                "package_size": 1,
                "alternate_name": "Product Name"
            },
            {
                "sku": "G001235",
                "branch_code": "00TR",
                "sdm": 200.00,
                "r2": 220.00,
                "r1": 240.00,
                "w2": 260.00,
                "w1": 280.00
            }
        ],
        "uploaded_by": "external_system",
        "job_title": "EXTERNAL",
        "update_type": "G"
    }
    ```
    
    **Response:**
    ```json
    {
        "success": true,
        "message": "Bulk update completed: 2 successful, 0 failed",
        "version_id": 123,
        "total_records": 2,
        "successful_updates": 2,
        "failed_updates": 0,
        "errors": []
    }
    ```
    """
    logger.info(f"Bulk price update request: {len(request.prices)} records")
    
    conn = get_db_connection()
    
    try:
        # Auto-detect update type if not provided
        if not request.update_type:
            categories = set()
            for price in request.prices:
                if price.sku and len(price.sku) > 0:
                    category = price.sku[0].upper()
                    if category in ['G', 'A', 'Y', 'S', 'C', 'E']:
                        categories.add(category)
            
            if len(categories) == 1:
                update_type = list(categories)[0]
            else:
                update_type = "MIXED"
        else:
            update_type = request.update_type
        
        # Create version log
        version_id = create_version_log(
            conn, 
            update_type, 
            request.uploaded_by, 
            request.job_title
        )
        
        # Process each price record
        successful_updates = 0
        failed_updates = 0
        errors = []
        
        for idx, price_data in enumerate(request.prices, start=1):
            try:
                # Validate SKU exists
                if not sku_exists(conn, price_data.sku):
                    error_msg = f"Record {idx}: SKU '{price_data.sku}' not found in Item_Master"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    failed_updates += 1
                    continue
                
                # Update price
                success, error_msg = upsert_price_record(conn, price_data, version_id)
                
                if success:
                    successful_updates += 1
                else:
                    error_msg = f"Record {idx}: {error_msg}"
                    errors.append(error_msg)
                    failed_updates += 1
                
                # Commit every 100 records
                if idx % 100 == 0:
                    conn.commit()
                    logger.info(f"Committed batch: {successful_updates}/{len(request.prices)} records")
            
            except Exception as e:
                error_msg = f"Record {idx}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                failed_updates += 1
        
        # Final commit
        conn.commit()
        
        success = failed_updates == 0
        message = (
            f"Bulk update completed: {successful_updates} successful, {failed_updates} failed"
            if not success
            else f"All {successful_updates} records updated successfully"
        )
        
        logger.info(f"Bulk update completed: version_id={version_id}, success={successful_updates}, failed={failed_updates}")
        
        return PriceUpdateResponse(
            success=success,
            message=message,
            version_id=version_id,
            total_records=len(request.prices),
            successful_updates=successful_updates,
            failed_updates=failed_updates,
            errors=errors
        )
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in bulk update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        conn.close()


@router.get("/status/{version_id}", response_model=VersionStatusResponse)
async def get_version_status(
    version_id: int
):
    """
    Get status of a price update version.
    
    This endpoint allows checking the status and statistics of a previous price update.
    **No authentication required** - Open API
    
    **Response:**
    ```json
    {
        "version_id": 123,
        "version_name": "API_20260505_143022",
        "update_type": "G",
        "uploaded_by": "external_system",
        "uploaded_at": "2026-05-05T14:30:22",
        "status": "ACTIVE",
        "total_records": 100,
        "records_with_price_change": 85,
        "records_with_name_change": 10
    }
    ```
    """
    logger.info(f"Version status request: {version_id}")
    
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        
        # Get version info
        cursor.execute("""
            SELECT version_name, update_type, uploaded_by, uploaded_at, status
            FROM Item_Update_Version
            WHERE version_id = ?
        """, (version_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
        
        version_name, update_type, uploaded_by, uploaded_at, status = row
        
        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_records,
                SUM(CASE WHEN change_price_flag = 1 THEN 1 ELSE 0 END) as price_changes,
                SUM(CASE WHEN change_altname_flag = 1 THEN 1 ELSE 0 END) as name_changes
            FROM Item_Update_Version_Detail
            WHERE version_id = ?
        """, (version_id,))
        
        stats_row = cursor.fetchone()
        total_records, price_changes, name_changes = stats_row if stats_row else (0, 0, 0)
        
        cursor.close()
        
        return VersionStatusResponse(
            version_id=version_id,
            version_name=version_name,
            update_type=update_type,
            uploaded_by=uploaded_by,
            uploaded_at=uploaded_at.isoformat() if uploaded_at else "",
            status=status,
            total_records=total_records or 0,
            records_with_price_change=price_changes or 0,
            records_with_name_change=name_changes or 0
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting version status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        conn.close()
