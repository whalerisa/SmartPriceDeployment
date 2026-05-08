# cache_refresh_router.py
# API endpoint for triggering customer cache refresh manually

from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime
from jobs.customer_cache_refresh_standalone import run_customer_cache_refresh
from config.cache_config import USE_DATABASE_CACHE

router = APIRouter(
    prefix="/api/cache",
    tags=["cache"]
)

# Global variable to track refresh status
_refresh_status = {
    "is_running": False,
    "last_run": None,
    "last_result": None,
}


def run_refresh_in_background():
    """Run cache refresh and update status"""
    global _refresh_status
    
    try:
        _refresh_status["is_running"] = True
        result = run_customer_cache_refresh()
        _refresh_status["last_run"] = datetime.now()
        _refresh_status["last_result"] = {
            "status": "success",
            "customers_processed": result.customers_processed,
            "customers_updated": result.customers_updated,
            "customers_failed": result.customers_failed,
            "duration_seconds": result.duration_seconds,
            "calculation_date": str(result.calculation_date),
        }
    except Exception as e:
        _refresh_status["last_result"] = {
            "status": "error",
            "error": str(e),
        }
    finally:
        _refresh_status["is_running"] = False


@router.get("/refresh-status")
def get_refresh_status():
    """
    DUTY: Get current status of customer cache refresh
    Returns: Refresh status (running/idle), last run time, result, cache enabled flag
    """
    return {
        "is_running": _refresh_status["is_running"],
        "last_run": _refresh_status["last_run"].isoformat() if _refresh_status["last_run"] else None,
        "last_result": _refresh_status["last_result"],
        "cache_enabled": USE_DATABASE_CACHE,
    }


@router.post("/refresh-customer-cache")
def trigger_customer_cache_refresh(background_tasks: BackgroundTasks):
    """
    DUTY: Trigger manual customer cache refresh in background
    Note: Takes 30-60 minutes. Check status with /api/cache/refresh-status
    Returns: Confirmation message with start time
    """
    if not USE_DATABASE_CACHE:
        raise HTTPException(
            status_code=400,
            detail="Database cache is not enabled. Set USE_DATABASE_CACHE=True in cache_config.py"
        )
    
    if _refresh_status["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Cache refresh is already running. Please wait for it to complete."
        )
    
    # Run refresh in background
    background_tasks.add_task(run_refresh_in_background)
    
    return {
        "message": "Customer cache refresh started in background",
        "note": "This may take 30-60 minutes. Use /api/cache/refresh-status to check progress.",
        "started_at": datetime.now().isoformat(),
    }


@router.get("/scheduler-status")
def get_scheduler_status():
    """
    DUTY: Get status of background scheduler and all scheduled jobs
    Returns: Scheduler status with next run times for all jobs
    """
    try:
        from jobs.scheduler import get_scheduler_status
        return get_scheduler_status()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scheduler status: {str(e)}"
        )
