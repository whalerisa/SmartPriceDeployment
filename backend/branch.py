"""
Branch Router

This module provides API endpoints for branch data from MSSQL.
"""

from fastapi import APIRouter, HTTPException
from config.db_mssql import get_mssql_conn
from branch_region_mapping import (
    get_all_branches_by_region,
    get_region_name,
    BRANCH_REGION_MAP
)
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/branches", tags=["branches"])


@router.get("") #ดึงชื่อสาขาทั้งหมด
def get_branches():
    """
    Get all branches from MSSQL Branch table.
    
    Returns:
        List of branches with Code and Name
    """
    conn = None
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # Query all branches ordered by Code
        cursor.execute("SELECT Code, Name FROM Branch ORDER BY Code")
        rows = cursor.fetchall()
        
        # Convert to list of dictionaries
        branches = [
            {"Code": row[0], "Name": row[1]}
            for row in rows
        ]
        
        cursor.close()
        
        logger.info(f"Fetched {len(branches)} branches from database")
        
        return {"branches": branches}
    
    except Exception as e:
        logger.error(f"Failed to fetch branches: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch branches: {str(e)}"
        )
    
    finally:
        if conn:
            conn.close()


@router.get("/regions")
def get_regions():
    """
    Get all available regions with their branch information.
    
    Returns:
        List of regions with code, name, and branches
    """
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # Query all branches
        cursor.execute("SELECT Code, Name FROM Branch ORDER BY Code")
        rows = cursor.fetchall()
        
        # Create a mapping of branch code to branch name
        branch_names = {row[0]: row[1] for row in rows}
        
        cursor.close()
        conn.close()
        
        # Build regions with their branches
        regions = []
        region_codes = set(BRANCH_REGION_MAP.values())
        
        for region_code in sorted(region_codes):
            if region_code == "Unknown":
                continue
                
            branch_codes = get_all_branches_by_region(region_code)
            branches = [
                {
                    "Code": code,
                    "Name": branch_names.get(code, "Unknown")
                }
                for code in branch_codes
                if code in branch_names
            ]
            
            regions.append({
                "code": region_code,
                "name": get_region_name(region_code),
                "branches": branches
            })
        
        logger.info(f"Fetched {len(regions)} regions from database")
        
        return {"regions": regions}
    
    except Exception as e:
        logger.error(f"Failed to fetch regions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch regions: {str(e)}"
        )


@router.get("/regions/{region_code}")
def get_branches_by_region(region_code: str):
    """
    Get all branches for a specific region.
    
    Args:
        region_code: Region code (BE, N, S, NE, C)
        
    Returns:
        List of branches in the specified region
    """
    try:
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # Query all branches
        cursor.execute("SELECT Code, Name FROM Branch ORDER BY Code")
        rows = cursor.fetchall()
        
        # Create a mapping of branch code to branch name
        branch_names = {row[0]: row[1] for row in rows}
        
        cursor.close()
        conn.close()
        
        # Get branches for the region
        branch_codes = get_all_branches_by_region(region_code)
        branches = [
            {
                "Code": code,
                "Name": branch_names.get(code, "Unknown")
            }
            for code in branch_codes
            if code in branch_names
        ]
        
        logger.info(f"Fetched {len(branches)} branches for region {region_code}")
        
        return {
            "region_code": region_code,
            "region_name": get_region_name(region_code),
            "branches": branches
        }
    
    except Exception as e:
        logger.error(f"Failed to fetch branches for region {region_code}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch branches for region {region_code}: {str(e)}"
        )
