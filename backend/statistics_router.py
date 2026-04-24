# backend/statistics_router.py
from fastapi import APIRouter, HTTPException
from typing import Dict
from LevelPrice import load_statistics, clear_statistics_cache, get_cache_info, calculate_statistics_from_database

router = APIRouter(
    prefix="/api/statistics",
    tags=["statistics"]
)

#ใช้จัดกาาร cache ของ mean,sd

@router.get("/current")
def get_current_statistics() -> Dict:
    """
    Get current statistics (mean and standard deviation) used for customer tier calculation.
    
    Returns:
        Dictionary containing current statistics with cache information
    """
    try:
        stats = load_statistics()
        cache_info = get_cache_info()
        
        return {
            "statistics": stats,
            "cache_info": cache_info,
            "source": "calculated_from_database"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading statistics: {str(e)}")


@router.post("/refresh")
def refresh_statistics() -> Dict:
    """
    Force refresh statistics by clearing cache and recalculating from database.
    
    Returns:
        Dictionary containing refreshed statistics
    """
    try:
        # Clear cache to force recalculation
        clear_statistics_cache()
        
        # Calculate fresh statistics
        stats = calculate_statistics_from_database()
        
        return {
            "message": "Statistics refreshed successfully",
            "statistics": stats,
            "source": "freshly_calculated_from_database"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing statistics: {str(e)}")


@router.get("/cache-info")
def get_statistics_cache_info() -> Dict:
    """
    Get information about the statistics cache.
    
    Returns:
        Dictionary containing cache status and age
    """
    return get_cache_info()


@router.delete("/cache")
def clear_statistics_cache_endpoint() -> Dict:
    """
    Clear the statistics cache.
    
    Returns:
        Confirmation message
    """
    clear_statistics_cache()
    return {"message": "Statistics cache cleared successfully"}