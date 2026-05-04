"""Special Price Request Router"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from auth_dependency import get_employee_info
from employee_position_mapper import (
    find_zm_at_branch, find_rm_in_region, find_sdm,
    find_pm_by_category, find_all_pms_by_categories
)
from branch_region_mapping import get_region_from_branch, get_regions_for_rm, get_regions_for_rm_by_employee_id
from config.db_mssql import get_mssql_conn
import logging
import os
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/special-price-requests", tags=["special-price-requests"])


# === SCHEMAS ===
class SpecialPriceItem(BaseModel):
    sku: str
    item_name: str
    quantity: float
    unit: str
    normal_price: float
    requested_price: float
    approval_level: str


class SpecialPriceRequestCreate(BaseModel):
    quote_no: str
    customer_code: str
    customer_name: str
    customer_type: Optional[str] = None
    items: List[SpecialPriceItem]
    request_reason: str
    valid_from: str
    valid_to: str


class RejectionRequest(BaseModel):
    reason: str


# === HELPER FUNCTIONS ===

def get_default_config() -> Dict[str, Any]:
    """
    Get default config with hardcoded role approval scope.
    
    Logic การอนุมัติ (ตายตัว):
    - ราคา >= R1: ไม่ต้องขออนุมัติ
    - R1 > ราคา >= W2: ZM_ONLY (อนุมัติจาก ZM เท่านั้น)
    - W2 > ราคา >= W1: ZM_THEN_RM (ต้องผ่าน ZM → RM)
    - W1 > ราคา >= SDM: SDM_APPROVAL (ต้องผ่าน ZM → RM → SDM)
    - ราคา < SDM: PM_APPROVAL (ต้องผ่าน ZM → RM → SDM → PM)
    """
    return {
        "price_config": {
            "role_approval_scope": {
                "Sales": {"min_level": "R2", "max_level": "R2"},
                "ZM": {"min_level": "R1", "max_level": "W2"},
                "RM": {"min_level": "W2", "max_level": "W1"},
                "SDM": {"min_level": "W1", "max_level": "SDM"},
                "PM": {"min_level": "R2", "max_level": "SDM"},
                "CEO": {"min_level": "R2", "max_level": "SDM"}
            }
        }
    }


def price_level_order() -> Dict[str, int]:
    """Get price level order (higher number = higher price)"""
    return {
        "R2": 5,
        "R1": 4,
        "W2": 3,
        "W1": 2,
        "SDM": 1
    }


def determine_approval_level(
    requested_price: float,
    r1_price: float,
    w2_price: float,
    w1_price: float,
    sdm_price: float
) -> Optional[str]:
    """
    Determine approval level based on requested price and price thresholds
    
    Returns:
        - None: ไม่ต้องขออนุมัติ (ราคา >= R1)
        - 'ZM_ONLY': ต้องอนุมัติจาก ZM เท่านั้น (R1 > ราคา >= W2)
        - 'ZM_THEN_RM': ต้องผ่าน ZM และ RM (W2 > ราคา >= W1)
        - 'SDM_APPROVAL': ต้องผ่าน ZM, RM และ SDM (W1 > ราคา >= SDM)
        - 'PM_APPROVAL': ต้องผ่าน ZM, RM, SDM และ PM (ราคา < SDM)
    """
    if requested_price >= r1_price:
        return None  # ไม่ต้องขออนุมัติ
    elif requested_price >= w2_price:
        return 'ZM_ONLY'
    elif requested_price >= w1_price:
        return 'ZM_THEN_RM'
    elif requested_price >= sdm_price:
        return 'SDM_APPROVAL'
    else:
        return 'PM_APPROVAL'


def extract_product_categories(items: List[SpecialPriceItem]) -> set:
    """Extract unique product categories from items based on SKU first letter"""
    categories = set()
    for item in items:
        if item.sku and len(item.sku) > 0:
            category = item.sku[0].upper()
            if category in ['G', 'A', 'C', 'Y', 'S', 'E']:
                categories.add(category)
    return categories


def calculate_request_total(items: List[SpecialPriceItem]) -> float:
    """Calculate total requested amount"""
    return sum(float(item.requested_price) * float(item.quantity) for item in items)


def is_price_below_sdm(requested_total: float, sdm_threshold: Optional[float] = None) -> bool:
    """Check if requested total is below SDM threshold"""
    if sdm_threshold is None:
        sdm_threshold = float(os.getenv("SDM_THRESHOLD_PRICE", "50000"))
    return requested_total < sdm_threshold


# === ENDPOINTS ===

@router.get("/approver-info")
async def get_approver_info(employee_info: dict = Depends(get_employee_info)):
    """Get approver information for current user"""
    try:
        employee_id = employee_info.get('employee_id')
        name = employee_info.get('name', 'Unknown')
        role = employee_info.get('role', 'Sales')
        branch_code = employee_info.get('branch_code')
        region = employee_info.get('region')
        
        logger.info(f"Getting approver info for: {employee_id} ({name}), Role: {role}")
        
        return {
            "employee_id": employee_id,
            "name": name,
            "role": role,
            "branch_code": branch_code,
            "region": region,
            "can_approve": role in ['ZM', 'RM', 'SDM', 'PM']
        }
        
    except Exception as e:
        logger.error(f"Error getting approver info: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get approver info: {str(e)}"
        )


@router.get("/pm-by-categories")
async def get_pm_by_categories(categories: str):
    """
    Get PM information for given product categories
    
    Query params:
        categories: Comma-separated list of categories (e.g., "A,G,C")
    
    Returns:
        Dictionary mapping category to PM info
    """
    try:
        category_list = [c.strip().upper() for c in categories.split(',') if c.strip()]
        
        if not category_list:
            raise HTTPException(status_code=400, detail="No categories provided")
        
        logger.info(f"Getting PMs for categories: {category_list}")
        
        pms = await find_all_pms_by_categories(category_list)
        
        # Format response
        result = {}
        for category in category_list:
            pm = pms.get(category)
            if pm:
                result[category] = {
                    "employee_id": pm['employee_id'],
                    "name": pm['name'],
                    "role": pm['role'],
                    "category": pm['category'],
                    "found": True
                }
            else:
                result[category] = {
                    "employee_id": None,
                    "name": None,
                    "role": None,
                    "category": category,
                    "found": False
                }
        
        logger.info(f"PM lookup result: {result}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting PMs by categories: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get PMs: {str(e)}"
        )


@router.get("/quote/{quote_no:path}")
async def get_special_price_request_by_quote(quote_no: str):
    """Get special price request by quote number"""
    try:
        logger.info(f"Getting special price request for quote: {quote_no}")
        
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # Query special price request by quote_no
        cursor.execute("""
            SELECT * FROM special_price_requests
            WHERE quote_no = ?
            ORDER BY created_at DESC
        """, (quote_no,))
        
        row = cursor.fetchone()
        
        if not row:
            cursor.close()
            conn.close()
            # Return null instead of 404 - this is an expected case when no SPR exists yet
            return None
        
        columns = [column[0] for column in cursor.description]
        request_dict = dict(zip(columns, row))
        
        # Query items for this request
        cursor.execute("""
            SELECT * FROM special_price_request_items
            WHERE request_id = ?
            ORDER BY id
        """, (request_dict.get("id"),))
        
        item_rows = cursor.fetchall()
        item_columns = [column[0] for column in cursor.description]
        
        items = []
        for item_row in item_rows:
            item_dict = dict(zip(item_columns, item_row))
            items.append({
                "sku": item_dict.get("sku"),
                "item_name": item_dict.get("item_name"),
                "quantity": item_dict.get("quantity"),
                "unit": item_dict.get("unit"),
                "normal_price": item_dict.get("normal_price"),
                "requested_price": item_dict.get("requested_price"),
                "approval_level": item_dict.get("approval_level"),
            })
        
        result = {
            "id": request_dict.get("id"),
            "quote_no": request_dict.get("quote_no"),
            "status": request_dict.get("status"),
            "request_reason": request_dict.get("request_reason"),
            "original_total": request_dict.get("original_total"),
            "requested_total": request_dict.get("requested_total"),
            "discount_percentage": request_dict.get("discount_percentage"),
            "valid_from": str(request_dict.get("valid_from")) if request_dict.get("valid_from") else None,
            "valid_to": str(request_dict.get("valid_to")) if request_dict.get("valid_to") else None,
            "requester_name": request_dict.get("requester_name"),
            "customer_name": request_dict.get("customer_name"),
            "created_at": str(request_dict.get("created_at")) if request_dict.get("created_at") else None,
            "approved_at": str(request_dict.get("approved_at")) if request_dict.get("approved_at") else None,
            "items": items,
        }
        
        cursor.close()
        conn.close()
        
        logger.info(f"  Found SPR #{request_dict.get('id')} with status: {request_dict.get('status')}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting special price request by quote: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get special price request: {str(e)}"
        )


@router.get("/pending/approvals")
async def get_pending_approvals(employee_info: dict = Depends(get_employee_info)):
    """Get pending approvals for current user"""
    try:
        current_employee_id = employee_info.get('employee_id')
        current_role = employee_info.get('role', 'Sales')
        current_branch = employee_info.get('branch_code')
        
        print(f"🔍 [PENDING_APPROVALS] Getting pending approvals for:")
        print(f"  Employee ID: {current_employee_id}")
        print(f"  Role: {current_role}")
        print(f"  Branch: {current_branch}")
        print(f"  Full employee_info: {employee_info}")
        
        logger.info(f"Getting pending approvals for:")
        logger.info(f"  Employee ID: {current_employee_id}")
        logger.info(f"  Role: {current_role}")
        logger.info(f"  Branch: {current_branch}")
        logger.info(f"  Full employee_info: {employee_info}")  # ⭐ เพิ่ม log
        
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        pending_requests = []
        
        # Query based on role
        if current_role == 'ZM':
            # ZM ดูคำขอที่ status = PENDING_ZM และ approver_employee_id = ZM_{branch}
            # เช่น ZM ที่สาขา 03TS จะเห็นคำขอที่ approver_employee_id = "ZM_03TS"
            position_id = f"ZM_{current_branch}"
            logger.info(f"  Looking for requests with approver_employee_id = {position_id} and status = PENDING_ZM")
            
            cursor.execute("""
                SELECT * FROM special_price_requests
                WHERE status = 'PENDING_ZM'
                AND approver_employee_id = ?
                ORDER BY created_at DESC
            """, (position_id,))
            
        elif current_role == 'RM':
            # ⭐ RM ดูคำขอที่ status = PENDING_RM จากทุกภูมิภาคที่ดูแล
            rm_branch = employee_info.get('branch_code')
            rm_regions = get_regions_for_rm(rm_branch)
            
            logger.info(f"  RM branch: {rm_branch}")
            logger.info(f"  RM responsible regions: {rm_regions}")
            logger.info(f"  Looking for requests with status = PENDING_RM from regions: {rm_regions}")
            
            # ⭐ สร้าง position_ids สำหรับทุกภูมิภาคที่ RM ดูแล
            position_ids = [f"RM_{region}" for region in rm_regions]
            placeholders = ','.join(['?' for _ in position_ids])
            
            cursor.execute(f"""
                SELECT * FROM special_price_requests
                WHERE status = 'PENDING_RM'
                AND approver_employee_id IN ({placeholders})
                ORDER BY created_at DESC
            """, position_ids)
            
        elif current_role == 'SDM':
            # SDM ดูคำขอที่ status = PENDING_SDM
            logger.info(f"  Looking for requests with status = PENDING_SDM")
            
            cursor.execute("""
                SELECT * FROM special_price_requests
                WHERE status = 'PENDING_SDM'
                ORDER BY created_at DESC
            """)
            
        elif current_role == 'PM' or current_role.startswith('PM_'):
            # PM ดูคำขอที่ status = PENDING_PM
            # PM ไม่ต้อง check branch - ดูได้ทุกคำขอที่ status = PENDING_PM
            # PM ทุกคนอยู่ที่ 90HO และอนุมัติได้ทุก category
            logger.info(f"  Looking for requests with status = PENDING_PM (all PMs at 90HO can see all categories)")
            
            cursor.execute("""
                SELECT * FROM special_price_requests
                WHERE status = 'PENDING_PM'
                ORDER BY created_at DESC
            """)
            
        else:
            # Sales หรือ role อื่น ๆ ไม่มีสิทธิ์อนุมัติ
            logger.info(f"  Role {current_role} cannot approve requests")
            return []
        
        rows = cursor.fetchall()
        logger.info(f"  Found {len(rows)} pending requests")
        
        # Get column names from cursor description
        columns = [column[0] for column in cursor.description]
        
        for row in rows:
            # Convert row to dict using column names
            row_dict = dict(zip(columns, row))
            
            # Query items for this request
            cursor.execute("""
                SELECT * FROM special_price_request_items
                WHERE request_id = ?
                ORDER BY id
            """, (row_dict.get("id"),))
            
            item_rows = cursor.fetchall()
            item_columns = [column[0] for column in cursor.description]
            
            items = []
            for item_row in item_rows:
                item_dict = dict(zip(item_columns, item_row))
                items.append({
                    "sku": item_dict.get("sku"),
                    "item_name": item_dict.get("item_name"),
                    "quantity": item_dict.get("quantity"),
                    "unit": item_dict.get("unit"),
                    "normal_price": item_dict.get("normal_price"),
                    "requested_price": item_dict.get("requested_price"),
                    "approval_level": item_dict.get("approval_level"),
                    "category": item_dict.get("category"),
                    "is_sold_by_pack": item_dict.get("is_sold_by_pack"),
                    "sqft_sheet": item_dict.get("sqft_sheet"),
                    "product_weight": item_dict.get("product_weight"),
                })
            
            request_data = {
                "id": row_dict.get("id"),
                "quote_no": row_dict.get("quote_no"),
                "request_reason": row_dict.get("request_reason"),
                "original_total": row_dict.get("original_total"),
                "requested_total": row_dict.get("requested_total"),
                "discount_percentage": row_dict.get("discount_percentage"),
                "status": row_dict.get("status"),
                "approver_employee_id": row_dict.get("approver_employee_id"),
                "approved_by": row_dict.get("approved_by"),
                "created_at": str(row_dict.get("created_at")) if row_dict.get("created_at") else None,
                "updated_at": str(row_dict.get("updated_at")) if row_dict.get("updated_at") else None,
                
                # เพิ่มข้อมูลผู้ขอและลูกค้า
                "requester_name": row_dict.get("requester_name"),
                "requester_employee_id": row_dict.get("requester_employee_id"),
                "customer_name": row_dict.get("customer_name"),
                "customer_code": row_dict.get("customer_code"),
                "request_number": row_dict.get("quote_no"),  # ใช้ quote_no เป็น request_number
                
                # เพิ่มวันที่ใช้ราคา
                "valid_from": str(row_dict.get("valid_from")) if row_dict.get("valid_from") else None,
                "valid_to": str(row_dict.get("valid_to")) if row_dict.get("valid_to") else None,
                
                # เพิ่ม items
                "items": items,
            }
            
            logger.info(f"  Request #{row_dict.get('id')}: {row_dict.get('quote_no')} - {row_dict.get('status')} ({len(items)} items)")
            pending_requests.append(request_data)
        
        cursor.close()
        conn.close()
        return pending_requests
        
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pending approvals: {str(e)}"
        )


@router.post("")
async def create_special_price_request(
    request_data: SpecialPriceRequestCreate,
    employee_info: dict = Depends(get_employee_info)
):
    """Create a new special price request"""
    try:
        # 1. ดึงข้อมูลผู้ขอจาก token
        requester_id = employee_info.get('employee_id')
        requester_name = employee_info.get('name', 'Unknown')
        branch_code = employee_info.get('branch_code')
        role = employee_info.get('role', 'Sales')
        
        if not branch_code:
            raise HTTPException(status_code=400, detail="Branch code not found in token")
        
        # 2. คำนวณ region จาก branch
        region = get_region_from_branch(branch_code)
        
        logger.info(f"Creating special price request:")
        logger.info(f"  Requester: {requester_id} ({requester_name})")
        logger.info(f"  Branch: {branch_code}, Region: {region}")
        logger.info(f"  Quote No: {request_data.quote_no}")
        logger.info(f"  Customer: {request_data.customer_code} - {request_data.customer_name}")
        logger.info(f"  Items: {len(request_data.items)}")
        
        # 3. คำนวณยอดรวมและตรวจสอบว่า < SDM threshold
        requested_total = calculate_request_total(request_data.items)
        below_sdm = is_price_below_sdm(requested_total)
        
        logger.info(f"  Requested Total: {requested_total}")
        logger.info(f"  Below SDM Threshold: {below_sdm}")
        
        # 4. หาผู้อนุมัติโดยใช้ employee_position_mapper
        logger.info("Finding approvers...")
        
        zm = await find_zm_at_branch(branch_code)
        logger.info(f"  ZM: {zm}")
        
        rm = await find_rm_in_region(region)
        logger.info(f"  RM: {rm}")
        
        # หา PM ถ้าราคา < SDM
        pm_approver = None
        product_categories = None
        if below_sdm:
            product_categories = extract_product_categories(request_data.items)
            logger.info(f"  Product Categories: {product_categories}")
            
            if product_categories:
                pms = await find_all_pms_by_categories(list(product_categories))
                if pms:
                    # ใช้ PM ตัวแรก (ถ้ามีหลายหมวดหมู่)
                    pm_approver = list(pms.values())[0]
                    logger.info(f"  PM Approver: {pm_approver}")
                else:
                    logger.warning(f"  ⚠️ PM not found for categories: {product_categories}")
                    logger.warning(f"  ⚠️ Request will be created but PM routing may fail during approval")
            else:
                logger.warning(f"  ⚠️ No product categories found in items")
        else:
            sdm = await find_sdm()
            logger.info(f"  SDM: {sdm}")
        
        # 5. สร้าง request object (ยังไม่บันทึกลงฐานข้อมูล - ต้องสร้างตารางก่อน)
        special_price_request = {
            "quote_no": request_data.quote_no,
            "requester_id": requester_id,
            "requester_name": requester_name,
            "requester_role": role,
            "branch": branch_code,
            "region": region,
            
            # ข้อมูลลูกค้า
            "customer_code": request_data.customer_code,
            "customer_name": request_data.customer_name,
            "customer_type": request_data.customer_type,
            
            # ข้อมูลสินค้า
            "items": [item.dict() for item in request_data.items],
            "total_items": len(request_data.items),
            
            # เหตุผลและวันที่
            "request_reason": request_data.request_reason,
            "valid_from": request_data.valid_from,
            "valid_to": request_data.valid_to,
            
            # ผู้อนุมัติ (เก็บ employee_id จริง)
            "zm_approver_id": zm['employee_id'] if zm else None,
            "zm_approver_name": zm['name'] if zm else None,
            "zm_approver_branch": zm['branch'] if zm else None,
            
            "rm_approver_id": rm['employee_id'] if rm else None,
            "rm_approver_name": rm['name'] if rm else None,
            "rm_approver_region": rm.get('region') if rm else None,
            
            # PM approver (ถ้าราคา < SDM)
            "pm_approver_id": pm_approver['employee_id'] if pm_approver else None,
            "pm_approver_name": pm_approver['name'] if pm_approver else None,
            "pm_category": pm_approver['category'] if pm_approver else None,
            
            # SDM approver (ถ้าราคา >= SDM)
            "sdm_approver_id": None,  # จะกำหนดในภายหลัง
            "sdm_approver_name": None,
            
            # สถานะ
            "status": "pending_zm",  # เริ่มที่ ZM เสมอ
            "created_at": datetime.now().isoformat(),
        }
        
        logger.info("Saving special price request to database...")
        
        # บันทึกลงฐานข้อมูล
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # คำนวณยอดรวม
        original_total = sum(float(item.normal_price) * float(item.quantity) for item in request_data.items)
        discount_percentage = ((original_total - requested_total) / original_total * 100) if original_total > 0 else 0
        
        # กำหนด status และ approver_employee_id เริ่มต้น
        # เริ่มที่ ZM เสมอ (ไม่ว่าจะต้องผ่านใครบ้าง)
        initial_status = 'PENDING_ZM'
        approver_id = f"ZM_{branch_code}"
        
        # ⭐ Log PM info for debugging (ไม่บันทึกลง database ตอนสร้าง)
        # PM routing จะใช้ approver_employee_id = 'PM_{category}' เหมือนระดับอื่น
        if pm_approver:
            logger.info(f"  📝 PM Routing Info (will be used when SDM approves):")
            logger.info(f"     PM Category: {pm_approver['category']}")
            logger.info(f"     PM Name: {pm_approver['name']}")
            logger.info(f"     PM Employee ID: {pm_approver['employee_id']}")
            logger.info(f"     PM Branch: 90HO (all PMs)")
            logger.info(f"     Will route to: PM_{pm_approver['category']}")
        
        # Insert special_price_requests (ใช้คอลัมน์เดิมเหมือนระดับอื่น)
        cursor.execute("""
            INSERT INTO special_price_requests (
                request_number, quote_no, customer_code, customer_name, customer_type,
                requester_name, request_reason, original_total, requested_total, discount_percentage,
                status, approver_employee_id, branch, valid_from, valid_to,
                employee_id, created_at, updated_at
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
        """, (
            request_data.quote_no,  # request_number
            request_data.quote_no,  # quote_no
            request_data.customer_code,
            request_data.customer_name,
            request_data.customer_type,
            requester_name,
            request_data.request_reason,
            original_total,
            requested_total,
            discount_percentage,
            initial_status,
            approver_id,
            branch_code,
            request_data.valid_from,
            request_data.valid_to,
            requester_id
        ))
        
        request_id = cursor.fetchone()[0]
        logger.info(f"  Created request ID: {request_id}")
        
        # Insert items (ใช้เฉพาะคอลัมน์ที่มีในตาราง)
        for item in request_data.items:
            # คำนวณ original_amount และ requested_amount
            original_amount = float(item.normal_price) * float(item.quantity)
            requested_amount = float(item.requested_price) * float(item.quantity)
            is_below_normal = 1 if item.requested_price < item.normal_price else 0
            
            cursor.execute("""
                INSERT INTO special_price_request_items (
                    request_id, item_code, item_name, quantity, unit,
                    normal_price, requested_price, original_amount, requested_amount,
                    is_below_normal, approval_level, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
            """, (
                request_id,
                item.sku,  # item_code
                item.item_name,
                item.quantity,
                item.unit,
                item.normal_price,
                item.requested_price,
                original_amount,
                requested_amount,
                is_below_normal,
                item.approval_level
            ))
        
        # ⭐ อัพเดท Quote_Header ให้เชื่อมโยงกับ special price request
        cursor.execute("""
            UPDATE Quote_Header
            SET special_price_request_id = ?,
                special_price_status = ?
            WHERE QuoteNo = ?
        """, (request_id, initial_status, request_data.quote_no))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✅ Special price request saved to database successfully")
        logger.info(f"   Request ID: {request_id}")
        logger.info(f"   Status: {initial_status}")
        logger.info(f"   Approver: {approver_id}")
        logger.info(f"   ✅ Quote_Header updated with request_id: {request_id}")
        
        return {
            "success": True,
            "message": "Special price request created successfully",
            "request_id": request_id,
            "quote_no": request_data.quote_no,
            "status": initial_status,
            "approver_employee_id": approver_id
        }
        
    except Exception as e:
        logger.error(f"Error creating special price request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create special price request: {str(e)}"
        )


@router.post("/{request_id}/approve")
async def approve_request(request_id: int, employee_info: dict = Depends(get_employee_info)):
    """Approve a special price request"""
    try:
        current_employee_id = employee_info.get('employee_id')
        current_role = employee_info.get('role', 'Sales')
        current_name = employee_info.get('name', 'Unknown')
        current_branch = employee_info.get('branch_code')
        
        logger.info(f"Approving request #{request_id}")
        logger.info(f"  Approver: {current_employee_id} ({current_name})")
        logger.info(f"  Role: {current_role}")
        logger.info(f"  Branch: {current_branch}")
        
        # ⭐ Load config (hardcoded values)
        config = get_default_config()
        logger.info(f"  Config loaded: {config}")
        
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # 1. ดึงข้อมูลคำขอ
        cursor.execute("""
            SELECT * FROM special_price_requests
            WHERE id = ?
        """, (request_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")
        
        columns = [column[0] for column in cursor.description]
        request = dict(zip(columns, row))
        
        current_status = request.get('status')
        approver_employee_id = request.get('approver_employee_id')
        
        logger.info(f"  Current status: {current_status}")
        logger.info(f"  Approver employee ID: {approver_employee_id}")
        
        # 2. ตรวจสอบสิทธิ์
        if current_role == 'ZM':
            # ZM ต้องเช็คว่าเป็น ZM ของสาขานี้
            expected_position = f"ZM_{current_branch}"
            if current_status != 'PENDING_ZM' and current_status != 'SDM_APPROVAL':
                raise HTTPException(status_code=403, detail="This request is not pending ZM approval")
            if approver_employee_id != expected_position:
                raise HTTPException(status_code=403, detail=f"You are not the assigned approver (expected {approver_employee_id})")
        
        elif current_role == 'RM':
            if current_status != 'PENDING_RM':
                raise HTTPException(status_code=403, detail="This request is not pending RM approval")
            
            # ⭐ RM ต้องเช็คว่าคำขอมาจากสาขาในภูมิภาคที่ RM ดูแล
            # ดึง region ของคำขอจาก approver_employee_id (เช่น "RM_BKK" หรือ "RM_E")
            if not approver_employee_id or not approver_employee_id.startswith('RM_'):
                raise HTTPException(status_code=400, detail="Invalid approver employee ID for RM")
            
            request_region = approver_employee_id.split('_')[1]  # "RM_BKK" → "BKK"
            rm_branch = employee_info.get('branch_code')  # Branch ของ RM ที่ login
            
            # ⭐ ดึงภูมิภาคทั้งหมดที่ RM คนนี้ดูแล (รองรับ RM ดูแลหลายภาค)
            rm_regions = get_regions_for_rm(rm_branch)
            
            logger.info(f"  Request region: {request_region}")
            logger.info(f"  RM branch: {rm_branch}")
            logger.info(f"  RM responsible regions: {rm_regions}")
            
            # ⭐ เช็คว่า request_region อยู่ในภูมิภาคที่ RM ดูแลหรือไม่
            if request_region not in rm_regions:
                raise HTTPException(
                    status_code=403, 
                    detail=f"You are RM responsible for regions {rm_regions}, but this request is from region {request_region}"
                )
        
        elif current_role == 'SDM':
            if current_status != 'PENDING_SDM':
                raise HTTPException(status_code=403, detail="This request is not pending SDM approval")
        
        elif current_role == 'PM' or current_role.startswith('PM_'):
            # ⭐ PM approval (ไม่ต้อง check branch - PM ดูแลทั้งบริษัท)
            if current_status != 'PENDING_PM':
                raise HTTPException(status_code=403, detail="This request is not pending PM approval")
            
            # เช็คว่า PM นี้เป็น PM ของ category ที่ถูกต้องหรือไม่
            if not approver_employee_id or not approver_employee_id.startswith('PM_'):
                raise HTTPException(status_code=400, detail="Invalid approver employee ID for PM")
            
            request_category = approver_employee_id.split('_')[1]  # PM_A → A
            logger.info(f"  Request category: {request_category}")
            
            # ⭐ PM ทุกคนอนุมัติได้ทุก category (เพราะ PM ดูแลทั้งบริษัท และอยู่ที่ 90HO)
            logger.info(f"  ✅ PM approval for category: {request_category} (no branch/category restriction - all PMs at 90HO can approve)")
        
        else:
            raise HTTPException(status_code=403, detail="You do not have permission to approve requests")
        
        # 3. Query items เพื่อดู approval_level
        cursor.execute("""
            SELECT approval_level FROM special_price_request_items
            WHERE request_id = ?
        """, (request_id,))
        
        item_rows = cursor.fetchall()
        approval_levels = [row[0] for row in item_rows]
        
        # ⭐ DEBUG: แสดง approval_level ทั้งหมด
        logger.info(f"  📋 Approval levels in request: {approval_levels}")
        
        # ตรวจสอบว่าต้องส่งต่อหรือไม่
        needs_rm = any(level in ['ZM_THEN_RM', 'RM', 'SDM_APPROVAL', 'ZM_THEN_RM_THEN_SDM', 'PM_APPROVAL'] for level in approval_levels)
        needs_sdm = any(level in ['SDM', 'SDM_APPROVAL', 'ZM_THEN_RM_THEN_SDM'] for level in approval_levels)
        needs_pm = any(level == 'PM_APPROVAL' for level in approval_levels)
        
        logger.info(f"  Needs RM: {needs_rm}")
        logger.info(f"  Needs SDM: {needs_sdm}")
        logger.info(f"  Needs PM: {needs_pm} ⭐")
        
        # 4. กำหนด status ใหม่และ approver ใหม่
        new_status = None
        new_approver_id = None
        
        if current_status in ['PENDING_ZM', 'SDM_APPROVAL']:
            # ZM อนุมัติแล้ว
            if needs_rm or needs_sdm or needs_pm:
                # ส่งต่อ RM (ทุกกรณีที่ไม่ใช่ ZM_ONLY)
                new_status = 'PENDING_RM'
                # คำนวณ region จาก branch ของคำขอ
                request_branch = request.get('branch')
                from branch_region_mapping import get_region_from_branch
                region = get_region_from_branch(request_branch) if request_branch else employee_info.get('region')
                new_approver_id = f"RM_{region}"
                logger.info(f"  → Forwarding to RM: {new_approver_id} (Branch: {request_branch}, Region: {region})")
            else:
                # อนุมัติเลย (ZM_ONLY)
                new_status = 'APPROVED'
                new_approver_id = None
                logger.info(f"  → Approved by ZM (final)")
        
        elif current_status == 'PENDING_RM':
            # RM อนุมัติแล้ว
            # เช็คว่าต้องส่ง SDM หรือ PM (PM ต้องผ่าน SDM ก่อน)
            if needs_pm or needs_sdm:
                # ส่งต่อ SDM (SDM จะเป็นคนส่งต่อให้ PM ถ้าจำเป็น)
                new_status = 'PENDING_SDM'
                new_approver_id = 'SDM_GLOBAL'
                logger.info(f"  → Forwarding to SDM (needs_pm={needs_pm}, needs_sdm={needs_sdm})")
            else:
                # อนุมัติเลย (ZM_THEN_RM)
                new_status = 'APPROVED'
                new_approver_id = None
                logger.info(f"  → Approved by RM (final)")
        
        elif current_status == 'PENDING_SDM':
            # SDM อนุมัติแล้ว
            # เช็คว่าต้องส่ง PM หรือไม่ (ใช้ needs_pm ที่คำนวณไว้แล้ว)
            if needs_pm:
                # ส่งต่อ PM (ดึง category จาก items)
                cursor.execute("""
                    SELECT DISTINCT LEFT(item_code, 1) as category
                    FROM special_price_request_items
                    WHERE request_id = ? AND approval_level = 'PM_APPROVAL'
                """, (request_id,))
                
                category_rows = cursor.fetchall()
                if category_rows:
                    pm_category = category_rows[0][0]  # ใช้ category แรก
                    new_status = 'PENDING_PM'
                    new_approver_id = f'PM_{pm_category}'
                    logger.info(f"  → SDM forwarding to PM: {new_approver_id} (Category: {pm_category}, Branch: 90HO)")
                else:
                    # ไม่มี category ให้อนุมัติเลย
                    new_status = 'APPROVED'
                    new_approver_id = None
                    logger.info(f"  → No PM category found, approved by SDM (final)")
            else:
                # อนุมัติเลย (ไม่ต้องส่ง PM)
                new_status = 'APPROVED'
                new_approver_id = None
                logger.info(f"  → Approved by SDM (final)")
        
        elif current_status == 'PENDING_PM':
            # ⭐ PM อนุมัติแล้ว (ขั้นสุดท้าย)
            new_status = 'APPROVED'
            new_approver_id = None
            logger.info(f"  → Approved by PM (final)")
        
        # 5. อัปเดตฐานข้อมูล
        update_query = """
            UPDATE special_price_requests
            SET status = ?,
                approver_employee_id = ?,
                approved_by = ?,
                approved_at = GETDATE(),
                updated_at = GETDATE()
            WHERE id = ?
        """
        
        cursor.execute(update_query, (
            new_status,
            new_approver_id,
            current_employee_id,
            request_id
        ))
        
        # ⭐ อัพเดท Quote_Header ด้วย
        quote_no = request.get('quote_no')
        cursor.execute("""
            UPDATE Quote_Header
            SET special_price_status = ?
            WHERE QuoteNo = ?
        """, (new_status, quote_no))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Request #{request_id} approved successfully")
        logger.info(f"   New status: {new_status}")
        logger.info(f"   Approved by: {current_employee_id} ({current_name})")
        logger.info(f"   ✅ Quote_Header updated with status: {new_status}")
        
        return {
            "success": True,
            "message": "Request approved successfully",
            "new_status": new_status,
            "approved_by": current_employee_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to approve request: {str(e)}"
        )


@router.post("/{request_id}/reject")
async def reject_request(request_id: int, rejection_data: RejectionRequest, employee_info: dict = Depends(get_employee_info)):
    """Reject a special price request"""
    try:
        current_employee_id = employee_info.get('employee_id')
        current_role = employee_info.get('role', 'Sales')
        current_name = employee_info.get('name', 'Unknown')
        current_branch = employee_info.get('branch_code')
        rejection_reason = rejection_data.reason.strip()
        
        logger.info(f"Rejecting request #{request_id}")
        logger.info(f"  Rejector: {current_employee_id} ({current_name})")
        logger.info(f"  Role: {current_role}")
        logger.info(f"  Branch: {current_branch}")
        logger.info(f"  Reason: {rejection_reason}")
        
        if not rejection_reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # 1. ดึงข้อมูลคำขอ
        cursor.execute("""
            SELECT * FROM special_price_requests
            WHERE id = ?
        """, (request_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")
        
        columns = [column[0] for column in cursor.description]
        request = dict(zip(columns, row))
        
        current_status = request.get('status')
        approver_employee_id = request.get('approver_employee_id')
        
        logger.info(f"  Current status: {current_status}")
        logger.info(f"  Approver employee ID: {approver_employee_id}")
        
        # 2. ตรวจสอบสิทธิ์ (ต้องเป็นผู้อนุมัติที่ได้รับมอบหมาย)
        if current_role == 'ZM':
            # ZM ต้องเช็คว่าเป็น ZM ของสาขานี้
            expected_position = f"ZM_{current_branch}"
            if current_status not in ['PENDING_ZM', 'SDM_APPROVAL']:
                raise HTTPException(status_code=403, detail="This request is not pending ZM approval")
            if approver_employee_id != expected_position:
                raise HTTPException(status_code=403, detail=f"You are not the assigned approver (expected {approver_employee_id})")
        
        elif current_role == 'RM':
            if current_status != 'PENDING_RM':
                raise HTTPException(status_code=403, detail="This request is not pending RM approval")
            
            # ⭐ RM ต้องเช็คว่าคำขอมาจากสาขาในภูมิภาคที่ RM ดูแล
            if not approver_employee_id or not approver_employee_id.startswith('RM_'):
                raise HTTPException(status_code=400, detail="Invalid approver employee ID for RM")
            
            request_region = approver_employee_id.split('_')[1]  # "RM_BKK" → "BKK"
            rm_branch = employee_info.get('branch_code')  # Branch ของ RM ที่ login
            
            # ⭐ ดึงภูมิภาคทั้งหมดที่ RM คนนี้ดูแล (รองรับ RM ดูแลหลายภาค)
            rm_regions = get_regions_for_rm(rm_branch)
            
            logger.info(f"  Request region: {request_region}")
            logger.info(f"  RM branch: {rm_branch}")
            logger.info(f"  RM responsible regions: {rm_regions}")
            
            # ⭐ เช็คว่า request_region อยู่ในภูมิภาคที่ RM ดูแลหรือไม่
            if request_region not in rm_regions:
                raise HTTPException(
                    status_code=403, 
                    detail=f"You are RM responsible for regions {rm_regions}, but this request is from region {request_region}"
                )
        
        elif current_role == 'SDM':
            if current_status != 'PENDING_SDM':
                raise HTTPException(status_code=403, detail="This request is not pending SDM approval")
        
        elif current_role == 'PM' or current_role.startswith('PM_'):
            # PM approval (ไม่ต้อง check branch - PM ดูแลทั้งบริษัท)
            if current_status != 'PENDING_PM':
                raise HTTPException(status_code=403, detail="This request is not pending PM approval")
        
        else:
            raise HTTPException(status_code=403, detail="You do not have permission to reject requests")
        
        # 3. อัปเดตฐานข้อมูล - เปลี่ยน status เป็น REJECTED
        update_query = """
            UPDATE special_price_requests
            SET status = 'REJECTED',
                approver_employee_id = NULL,
                rejection_reason = ?,
                approved_by = ?,
                approved_at = GETDATE(),
                updated_at = GETDATE()
            WHERE id = ?
        """
        
        cursor.execute(update_query, (
            rejection_reason,
            current_employee_id,
            request_id
        ))
        
        # ⭐ อัพเดท Quote_Header ด้วย
        quote_no = request.get('quote_no')
        cursor.execute("""
            UPDATE Quote_Header
            SET special_price_status = 'REJECTED'
            WHERE QuoteNo = ?
        """, (quote_no,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Request #{request_id} rejected successfully")
        logger.info(f"   Rejected by: {current_employee_id} ({current_name})")
        logger.info(f"   Reason: {rejection_reason}")
        logger.info(f"   ✅ Quote_Header updated with status: REJECTED")
        
        return {
            "success": True,
            "message": "Request rejected successfully",
            "status": "REJECTED",
            "approved_by": current_employee_id,
            "rejection_reason": rejection_reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reject request: {str(e)}"
        )