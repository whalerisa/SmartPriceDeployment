# router_sq.py
from fastapi import APIRouter, HTTPException
import sqlite3
import json
from datetime import datetime
from config.db_sqlite import get_conn



router = APIRouter(prefix="/sq", tags=["sales-queue"])

@router.post("/quote")
def create_sq(payload: dict):
    """
    payload structure (จาก FE เดิม):
    {
      customerNo: "...",
      quoteNo: "...",
      items: [
        { itemNo: "...", qty: 1, price: 65 }
      ]
    }
    """
    try:
        print("=== CREATE SQ PAYLOAD ===")
        print(payload)

        # ---------------------------
        # Validate payload
        # ---------------------------
        sell_to_customer_no = payload.get("customerNo")
        if not sell_to_customer_no:
            raise ValueError("customerNo is required")

        external_document_no = payload.get("quoteNo") or ""
        items = payload.get("items", [])

        if not items:
            raise ValueError("items is empty")

        conn = get_conn()
        cur = conn.cursor()

        # ---------------------------
        # 1) INSERT SQ HEADER (BC-style)
        # ---------------------------
        sq_no = f"SQ-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        document_type = "Quote"
        status = "Open"

        cur.execute(
            """
            INSERT INTO sales_queue
            (
              sq_no,
              Document_Type,
              Sell_to_Customer_No,
              External_Document_No,
              Status,
              payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                sq_no,
                document_type,
                sell_to_customer_no,
                external_document_no,
                status,
                json.dumps(payload, ensure_ascii=False),
            ),
        )

        queue_id = cur.lastrowid

        # ---------------------------
        # 2) INSERT SQ LINES (BC-style)
        # ---------------------------
        for idx, it in enumerate(items, start=1):
            item_no = it.get("itemNo")
            quantity = it.get("qty")
            unit_price = it.get("price") or 0
            line_amount = unit_price * quantity

            if not item_no:
                raise ValueError("itemNo is required in items")
            if quantity is None:
                raise ValueError("qty is required in items")

            cur.execute(
                """
                INSERT INTO sales_queue_line
                (
                  queue_id,
                  Line_No,
                  Document_No,
                  Type,
                  No,
                  Quantity,
                  Unit_Price,
                  Line_Amount
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    queue_id,
                    idx,
                    sq_no,
                    "Item",
                    item_no,
                    quantity,
                    unit_price,
                    line_amount,
                ),
            )

        conn.commit()

        return {
            "status": "SUCCESS",
            "sqNo": sq_no,
            "message": "บันทึก SQ เรียบร้อย (ยังไม่ส่งเข้า BC)",
        }

    except Exception as e:
        print("❌ CREATE SQ ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
