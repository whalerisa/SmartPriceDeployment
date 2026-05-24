"""
D365 Sales Quote API Router

POST /api/d365/sales-quote — รับข้อมูล Quote แล้วส่งออกเป็น JSON
ข้อมูลเหมือน RPA + เพิ่ม shipment_date
ทีม D365 สามารถนำ JSON นี้ไปใช้ต่อได้เลย
"""

import json
import logging
import os
from typing import List, Optional
from datetime import datetime, date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/d365", tags=["D365 Sales Quote API"])

# โฟลเดอร์เก็บ JSON output
OUTPUT_DIR = Path(__file__).parent / "data" / "d365_quotes"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==================== Models ====================

class D365QuoteLineItem(BaseModel):
    sku: str = Field(..., description="Item Code (No.)")
    description: str = Field("", description="รายละเอียดสินค้า")
    quantity: float = Field(..., description="จำนวน")
    unit_price: float = Field(0, description="ราคาต่อหน่วย")
    price_per_sqft: Optional[float] = Field(None, description="ราคาต่อ sq.ft (กระจก)")
    price_per_sheet: Optional[float] = Field(None, description="ราคาต่อแผ่น (กระจก)")
    variant_code: Optional[str] = Field("", description="Variant Code")


class D365CreateQuoteRequest(BaseModel):
    """ข้อมูลเหมือน RPA + shipment_date"""
    quote_code: str = Field(..., description="รหัส Quote เช่น TRQT-6805/0001")
    customer_no: str = Field(..., description="D365 Customer No. เช่น 08015AY")
    sales_admin: str = Field("", description="Sales Admin code เช่น 20614")
    your_reference: str = Field("", description="เลข Quote อ้างอิง")
    project_code: Optional[str] = Field(None, description="Project Code")
    shipment_date: Optional[date] = Field(None, description="วันที่จัดส่ง (Shipment Date)")
    items: List[D365QuoteLineItem] = Field(..., description="รายการสินค้า")


# ==================== Endpoint ====================

@router.post("/sales-quote", summary="สร้าง JSON สำหรับ D365 Sales Quote")
def create_d365_sales_quote(request: D365CreateQuoteRequest):
    """
    รับข้อมูล Quote แล้วสร้าง JSON file ส่งออก
    ทีม D365 นำไฟล์ JSON นี้ไปใช้ต่อได้เลย
    """

    # สร้าง JSON payload
    output = {
        "quote_code": request.quote_code,
        "customer_no": request.customer_no,
        "sales_admin": request.sales_admin,
        "your_reference": request.your_reference,
        "project_code": request.project_code,
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

    # บันทึกเป็นไฟล์ JSON
    safe_name = request.quote_code.replace("/", "_").replace("\\", "_")
    filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = OUTPUT_DIR / filename

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ D365 JSON saved: {filepath}")
    except Exception as e:
        logger.error(f"❌ Failed to save JSON: {e}")
        raise HTTPException(status_code=500, detail=f"ไม่สามารถบันทึกไฟล์ได้: {e}")

    return JSONResponse(content={
        "success": True,
        "message": f"JSON สร้างสำเร็จ: {filename}",
        "filename": filename,
        "payload": output,
    })
