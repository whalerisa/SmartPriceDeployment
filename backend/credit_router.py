# credit_router.py
from fastapi import APIRouter, HTTPException
import httpx
from config.config_external_api import CREDIT_API_URL, CREDIT_API_HEADERS, REMAININGCREDIT_URL, REMAININGCREDIT_HEADERS
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/credit-status/{customer_id}")
async def get_credit_status(customer_id: str):
    """
    ดึงข้อมูลเครดิตของลูกค้าจาก External API
    
    Args:
        customer_id: รหัสลูกค้า
    
    Returns:
        {
            "customer_id": "0100ZTR",
            "customer_name": "Mock Customer (N Scomartr)",
            "status": "ปกติ",
            "credit_limit": 500000,
            "credit_available": 250000,
            "credit_terms": {
                "gs": 60,      // Glass/Glue (กระจก/กาว)
                "ae": 45,      // Aluminum/Equipment (อลูมิเนียม/อุปกรณ์)
                "yc": 30       // Gypsum/Frame (ยิปซัม/โครงคร่าว)
            },
            "updated_at": "2024-02-29T12:48:51.3992"
        }
    """
    try:
        # สร้าง URL สำหรับเรียก External API
        url = f"{CREDIT_API_URL}/api/external/credit-status/{customer_id}"
        
        logger.info(f"🔍 [CREDIT API] Calling: {url}")
        logger.info(f"🔍 [CREDIT API] Headers: {CREDIT_API_HEADERS}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers=CREDIT_API_HEADERS
            )
            
            logger.info(f"🔍 [CREDIT API] Response status: {response.status_code}")
            logger.info(f"🔍 [CREDIT API] Response body: {response.text}")
            
            response.raise_for_status()
            data = response.json()
            
            # ⭐ Map credit_terms keys from external API to frontend format
            # External API might return: ga, yc, ae
            # Frontend expects: gs (glass/glue), ae (aluminum/equipment), yc (gypsum/frame)
            if data.get("credit_terms"):
                credit_terms = data["credit_terms"]
                # Map 'ga' to 'gs' if it exists
                if "ga" in credit_terms and "gs" not in credit_terms:
                    credit_terms["gs"] = credit_terms.pop("ga")
                # Ensure all expected keys exist
                data["credit_terms"] = {
                    "gs": credit_terms.get("gs", 0),
                    "ae": credit_terms.get("ae", 0),
                    "yc": credit_terms.get("yc", 0),
                }
            else:
                # ถ้าไม่มี credit_terms ให้ set เป็น empty dict
                data["credit_terms"] = {
                    "gs": 0,
                    "ae": 0,
                    "yc": 0,
                }
            
            logger.info(f"✅ [CREDIT API] Success! Mapped data: {data}")
            logger.info(f"✅ [CREDIT API] Status: {data.get('status')}")
            logger.info(f"✅ [CREDIT API] Credit terms: {data.get('credit_terms')}")
            return data
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from credit API: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Credit API error: {e.response.text}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error to credit API: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to credit API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_credit_status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/api/remaining-credit/{customer_id}")
async def get_remaining_credit(customer_id: str):
    """
    ดึงข้อมูลยอดเครดิตคงเหลือของลูกค้าจาก External API
    
    Args:
        customer_id: รหัสลูกค้า
    
    Returns:
        ข้อมูลยอดเครดิตคงเหลือ
    """
    import requests
    import json
    
    try:
        logger.info(f"🔍 [REMAINING CREDIT API] Calling: {REMAININGCREDIT_URL}")
        logger.info(f"🔍 [REMAINING CREDIT API] Headers: {REMAININGCREDIT_HEADERS}")
        logger.info(f"🔍 [REMAINING CREDIT API] Customer ID: {customer_id}")
        
        # ⭐ ใช้ GET method (API ส่งข้อมูลทั้งหมดมา)
        response = requests.get(
            REMAININGCREDIT_URL,
            headers=REMAININGCREDIT_HEADERS,
            timeout=10.0
        )
        
        logger.info(f"🔍 [REMAINING CREDIT API] Response status: {response.status_code}")
        logger.info(f"🔍 [REMAINING CREDIT API] Content-Encoding: {response.headers.get('Content-Encoding', 'none')}")
        
        response.raise_for_status()
        
        # ⭐ ใช้ .json() ของ requests ซึ่งจะจัดการ encoding ให้อัตโนมัติ
        data = response.json()
        
        logger.info(f"✅ [REMAINING CREDIT API] Success! Data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
        
        # ⭐ Filter ข้อมูลตาม customer_id
        if isinstance(data, dict) and "data" in data:
            all_customers = data["data"]
            # หาลูกค้าที่ตรงกับ customer_id
            filtered_data = [
                customer for customer in all_customers 
                if customer.get("Customer No.") == customer_id or 
                   customer.get("Customer_No") == customer_id or
                   customer.get("customer_id") == customer_id
            ]
            
            if filtered_data:
                logger.info(f"✅ Found customer data for {customer_id}")
                return {"data": filtered_data}
            else:
                logger.warning(f"⚠️ No data found for customer {customer_id}")
                return {"data": []}
        
        return data
            
    except requests.HTTPError as e:
        logger.error(f"HTTP error from remaining credit API: {e.response.status_code if e.response else 'N/A'}")
        raise HTTPException(
            status_code=e.response.status_code if e.response else 500,
            detail=f"Remaining Credit API error: {e.response.text if e.response else str(e)}"
        )
    except requests.RequestException as e:
        logger.error(f"Request error to remaining credit API: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to remaining credit API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_remaining_credit: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
