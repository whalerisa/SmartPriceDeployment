"""
D365 Sales Quote API Router

POST /api/d365/sales-quote — สร้าง Sales Quote เข้า D365 Business Central โดยตรง
ขั้นตอน:
  1) POST .../salesQuotes        -> สร้าง header แล้วเก็บ "id" ที่ได้
  2) POST .../salesQuotes(id)/salesQuoteLines  -> เพิ่มรายการสินค้าทีละบรรทัด

POST /api/d365/sales-quote/export — (ของเดิม) ส่งออกข้อมูลเป็น JSON เฉยๆ ไม่ยิงเข้า D365
"""

import os
import base64
import logging
from typing import List, Optional
from datetime import datetime, date

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/d365", tags=["D365 Sales Quote API"])


# ==================== Config (จาก .env) ====================


D365_BC_BASE_URL = os.getenv(
    "D365_BC_BASE_URL",
    "http://192.192.0.36:23348/BCTNG/api/v2.0/companies",
).rstrip("/")
D365_BC_COMPANY_ID = os.getenv("D365_BC_COMPANY_ID", "").strip()
D365_BC_USERNAME = os.getenv("D365_BC_USERNAME", "").strip()
D365_BC_ACCESS_KEY = os.getenv("D365_BC_ACCESS_KEY", "").strip()

# Timeout (วินาที) สำหรับการเรียก D365
D365_BC_TIMEOUT = float(os.getenv("D365_BC_TIMEOUT", "30"))


def _build_auth_headers() -> dict:
    """สร้าง header สำหรับ Basic Auth: base64 ของ user:accesskey"""
    raw = f"{D365_BC_USERNAME}:{D365_BC_ACCESS_KEY}".encode("utf-8")
    token = base64.b64encode(raw).decode("ascii")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _quotes_url() -> str:
    """URL สำหรับสร้าง/อ่าน salesQuotes ของบริษัท"""
    return f"{D365_BC_BASE_URL}({D365_BC_COMPANY_ID})/salesQuotes"


def _quote_lines_url(quote_id: str) -> str:
    """URL สำหรับเพิ่ม line ให้กับ quote ที่ระบุ"""
    return f"{D365_BC_BASE_URL}({D365_BC_COMPANY_ID})/salesQuotes({quote_id})/salesQuoteLines"


def _ensure_config():
    """ตรวจสอบว่า config ครบก่อนเรียกใช้งานจริง"""
    missing = []
    if not D365_BC_COMPANY_ID:
        missing.append("D365_BC_COMPANY_ID")
    if not D365_BC_USERNAME:
        missing.append("D365_BC_USERNAME")
    if not D365_BC_ACCESS_KEY:
        missing.append("D365_BC_ACCESS_KEY")
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"D365 BC config ไม่ครบ กรุณาตั้งค่าใน .env: {', '.join(missing)}",
        )


# ==================== Models ====================

class D365QuoteLineItem(BaseModel):
    sku: str = Field(..., description="Item Code (No.) ใช้เป็น lineObjectNumber")
    description: str = Field("", description="รายละเอียดสินค้า")
    quantity: float = Field(..., description="จำนวน")
    unit_price: float = Field(0, description="ราคาต่อหน่วย (unitPrice)")
    price_per_sqft: Optional[float] = Field(None, description="ราคาต่อ sq.ft (กระจก)")
    price_per_sheet: Optional[float] = Field(None, description="ราคาต่อแผ่น (กระจก)")
    variant_code: Optional[str] = Field("", description="Variant Code")


class D365CreateQuoteRequest(BaseModel):
    quote_code: str = Field(..., description="รหัส Quote เช่น TRQT-6805/0001 (ใช้เป็น externalDocumentNumber)")
    customer_no: str = Field(..., description="D365 Customer No. เช่น 08015AY (customerNumber)")
    sales_admin: str = Field("", description="Sales Admin code เช่น 20614")
    project_code: Optional[str] = Field(None, description="Project Code")
    document_date: Optional[date] = Field(None, description="documentDate (ถ้าไม่ส่งจะใช้วันที่วันนี้)")
    shipment_date: Optional[date] = Field(None, description="วันที่จัดส่ง (Shipment Date)")
    items: List[D365QuoteLineItem] = Field(..., description="รายการสินค้า")


# ==================== D365 calls ====================

def _create_quote_header(req: D365CreateQuoteRequest) -> dict:
    """สร้าง Sales Quote header แล้วคืน response (มี id)"""
    doc_date = (req.document_date or date.today()).isoformat()
    payload = {
        "customerNumber": req.customer_no,
        "documentDate": doc_date,
        "externalDocumentNumber": req.quote_code,
    }

    url = _quotes_url()
    logger.info(f"➡️ POST D365 sales quote header: {url} | payload={payload}")
    resp = requests.post(
        url,
        json=payload,
        headers=_build_auth_headers(),
        timeout=D365_BC_TIMEOUT,
    )

    if resp.status_code not in (200, 201):
        logger.error(f"❌ สร้าง header ไม่สำเร็จ ({resp.status_code}): {resp.text}")
        raise HTTPException(
            status_code=502,
            detail=f"สร้าง Sales Quote header ไม่สำเร็จ ({resp.status_code}): {resp.text}",
        )

    data = resp.json()
    quote_id = data.get("id")
    if not quote_id:
        raise HTTPException(
            status_code=502,
            detail=f"ไม่พบ 'id' ใน response ของ header: {data}",
        )
    logger.info(f"✅ สร้าง header สำเร็จ id={quote_id} number={data.get('number')}")
    return data


def _add_quote_line(quote_id: str, item: D365QuoteLineItem) -> dict:
    """เพิ่ม 1 line ให้ quote"""
    payload = {
        "lineType": "Item",
        "lineObjectNumber": item.sku,
        "quantity": item.quantity,
        "unitPrice": item.unit_price,
    }

    url = _quote_lines_url(quote_id)
    logger.info(f"➡️ POST D365 quote line: {url} | payload={payload}")
    resp = requests.post(
        url,
        json=payload,
        headers=_build_auth_headers(),
        timeout=D365_BC_TIMEOUT,
    )

    if resp.status_code not in (200, 201):
        logger.error(f"❌ เพิ่ม line ไม่สำเร็จ ({resp.status_code}): {resp.text}")
        raise HTTPException(
            status_code=502,
            detail=f"เพิ่ม line (sku={item.sku}) ไม่สำเร็จ ({resp.status_code}): {resp.text}",
        )

    return resp.json()


# ==================== Endpoints ====================

@router.post("/sales-quote", summary="สร้าง Sales Quote เข้า D365 Business Central")
def create_d365_sales_quote(request: D365CreateQuoteRequest):
    """
    สร้าง Sales Quote เข้า D365 โดยตรง:
      1) สร้าง header -> เก็บ id
      2) เพิ่ม line ทีละรายการ
    """
    _ensure_config()

    if not request.items:
        raise HTTPException(status_code=400, detail="ต้องมีรายการสินค้าอย่างน้อย 1 รายการ")

    # 1) header
    header = _create_quote_header(request)
    quote_id = header["id"]

    # 2) lines
    created_lines = []
    for item in request.items:
        line = _add_quote_line(quote_id, item)
        created_lines.append(line)

    logger.info(
        f"✅ สร้าง D365 Sales Quote สำเร็จ: quote_code={request.quote_code} "
        f"id={quote_id} จำนวน lines={len(created_lines)}"
    )

    return JSONResponse(content={
        "success": True,
        "message": "สร้าง Sales Quote เข้า D365 สำเร็จ",
        "quote_id": quote_id,
        "quote_number": header.get("number"),
        "customer_number": header.get("customerNumber"),
        "customer_name": header.get("customerName"),
        "document_date": header.get("documentDate"),
        "external_document_number": header.get("externalDocumentNumber"),
        "lines_created": len(created_lines),
    })


@router.post("/sales-quote/export", summary="ส่งออกข้อมูล D365 Sales Quote เป็น JSON (ไม่ยิงเข้า D365)")
def export_d365_sales_quote(request: D365CreateQuoteRequest):
    """รับข้อมูล Quote แล้วส่งออกเป็น JSON เฉยๆ (ของเดิม สำหรับตรวจสอบ payload)"""
    output = {
        "quote_code": request.quote_code,
        "customer_no": request.customer_no,
        "sales_admin": request.sales_admin,
        "your_reference": request.quote_code,
        "project_code": request.project_code,
        "document_date": (request.document_date or date.today()).isoformat(),
        "shipment_date": request.shipment_date.isoformat() if request.shipment_date else None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "items": [
            {
                "sku": item.sku,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "price_per_sqft": item.price_per_sqft,
                "price_per_sheet": item.price_per_sheet,
                "variant_code": item.variant_code,
            }
            for item in request.items
        ],
    }

    logger.info(f"✅ D365 JSON exported for quote: {request.quote_code}")

    return JSONResponse(content={
        "success": True,
        "message": "ส่งออก JSON สำเร็จ",
        "payload": output,
    })
