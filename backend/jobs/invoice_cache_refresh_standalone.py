"""
Invoice Cache Refresh Job - Standalone Version for Airflow
ดึงข้อมูล Invoice จาก D365 มาลง database

This is a standalone version that doesn't require external imports.
All dependencies are included in this file.

Configuration:
--------------
The script uses hardcoded default values from production environment:
- INVOICE_API_URL: http://192.192.0.37:8280/invoice-sp681/1.0.0
- INVOICE_API_KEY: (production key included)
- MSSQL_SERVER: 192.192.0.220,50681
- MSSQL_DATABASE: SP681
- MSSQL_USERNAME: sp681_user
- MSSQL_PASSWORD: (production password included)

You can override these defaults using environment variables.

Usage:
------
1. Direct execution:
   python invoice_cache_refresh_standalone.py
   
   # With custom months
   python invoice_cache_refresh_standalone.py --months 12

2. In Airflow DAG:
   from invoice_cache_refresh_standalone import run_invoice_cache_refresh
   
   def task_function():
       result = run_invoice_cache_refresh(months=6)
       if result.errors:
           raise Exception(f"Job failed with {len(result.errors)} errors")
       return result

Requirements:
-------------
- pyodbc
- requests
- pandas

Install with:
    pip install pyodbc requests pandas
"""

import os
import sys
import time
import logging
import pyodbc
import requests
import pandas as pd
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta  # ✅ เพิ่ม relativedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from logging.handlers import TimedRotatingFileHandler


# =========================
# LOGGING SETUP
# =========================

LOG_FILE = "logs/invoice_cache_refresh.log"
LOG_LEVEL = "INFO"
LOG_BACKUP_COUNT = 30


def setup_logger():
    """Setup logger with file and console handlers"""
    logger = logging.getLogger('invoice_cache')
    logger.setLevel(getattr(logging, LOG_LEVEL))
    logger.handlers.clear()
    
    # Create logs directory if not exists
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # File handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when='midnight',
        interval=1,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logger()


# =========================
# CONFIGURATION
# =========================

# Database Configuration
MSSQL_CONFIG = {
    "server": os.getenv("MSSQL_SERVER", "192.192.0.220,50681"),
    "database": os.getenv("MSSQL_DATABASE", "SP681"),
    "username": os.getenv("MSSQL_USERNAME", "sp681_user"),
    "password": os.getenv("MSSQL_PASSWORD", "Tng#kmitl2"),
    "driver": os.getenv("MSSQL_DRIVER", "{ODBC Driver 17 for SQL Server}"),
}

# API Configuration - Invoice API
DEFAULT_INVOICE_API_URL = "http://192.192.0.37:8280/invoice-sp681/1.0.0"
DEFAULT_INVOICE_API_KEY = "eyJ4NXQjUzI1NiI6Ik16QXpNVEZqT0RRMU1ETmpPVFUxWkRBNE5HUTVNRGt6WXpFM01XSTRNbVJsWkdVM1l6WmpZams0WkdSa00yUmhNbUl3TWpBeFl6SmxNR0pqTmpkbU53PT0iLCJraWQiOiJnYXRld2F5X2NlcnRpZmljYXRlX2FsaWFzIiwidHlwIjoiSldUIiwiYWxnIjoiUlMyNTYifQ==.eyJzdWIiOiJkZXZVc2VyQGNhcmJvbi5zdXBlciIsImFwcGxpY2F0aW9uIjp7ImlkIjo2OSwidXVpZCI6ImNlODcxN2I0LTUwOTQtNDBlMy1hNzdjLWY2M2UyNWQwNWNjNSJ9LCJpc3MiOiJodHRwczpcL1wvbG9jYWxob3N0Ojk0NDNcL29hdXRoMlwvdG9rZW4iLCJrZXl0eXBlIjoiUFJPRFVDVElPTiIsInRva2VuX3R5cGUiOiJhcGlLZXkiLCJpYXQiOjE3NjkxNzcyMDIsImp0aSI6IjYyZjhlNWEzLWUxYjktNDYwMS1iMDk0LWIwYjNhM2I2YTU1YyJ9.gNjVXzh-q9ITNMybUmrdL8Vuvptxvm3zLUKX5DXqK98qzhfSmP2dwWGteviBQLGOOlmYws0zoqf0DLzlswcT08gYhQIzXNPHTMek47w127DWHdp97lcBFNEGDBlRVxuzRq_Y9_gkwugNI7vDhu41SE7nj0tEy15-iDmGH8RNrUZEp_tML8nCjTpBs0jPcar7dIbJxyP94O63pjdSN2GXW6TTMOCRlKUsMO5EiAjJKCzHFgvFabmFZNrk12jvmLXyh7QnqXCQF1o3UNmKS7--GS3qie2mpHWyaQxP1Qa6kNWdPbHlzIp27eA208Az6XAlq2s6iaXLdcvAfZKPWcbRGQ=="

# Job Configuration
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
API_PAGE_SIZE = int(os.getenv("API_PAGE_SIZE", "5000"))
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "120"))
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))       # จำนวนครั้ง retry สูงสุด
API_RETRY_DELAY = int(os.getenv("API_RETRY_DELAY", "10"))      # รอกี่วินาทีก่อน retry


def get_mssql_conn():
    """Create and return MSSQL database connection"""
    conn_str = (
        f"DRIVER={MSSQL_CONFIG['driver']};"
        f"SERVER={MSSQL_CONFIG['server']};"
        f"DATABASE={MSSQL_CONFIG['database']};"
        f"UID={MSSQL_CONFIG['username']};"
        f"PWD={MSSQL_CONFIG['password']};"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


# =========================
# DATA MODELS
# =========================

@dataclass
class InvoiceCacheRecord:
    """โครงสร้างข้อมูล invoice สำหรับ cache"""
    document_no: str
    customer_code: str
    posting_date: date
    sku: str
    order_no: Optional[str] = ""
    sell_to_customer_name: Optional[str] = ""
    description: Optional[str] = ""
    variant_code: Optional[str] = ""
    quantity: float = 0.0
    unit_of_measure: Optional[str] = ""
    unit_price: float = 0.0
    line_amount: float = 0.0
    line_amount_include_vat: float = 0.0
    project_no: Optional[str] = ""


@dataclass
class InvoiceJobResult:
    """ผลการรัน invoice cache job"""
    start_time: datetime
    end_time: datetime
    calculation_date: date
    invoices_processed: int = 0
    invoices_inserted: int = 0
    invoices_failed: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        return (self.end_time - self.start_time).total_seconds()


# =========================
# API FUNCTIONS
# =========================

def load_all_invoices_from_d365(start_date: date, end_date: date) -> List[Dict]:
    """
    ดึงข้อมูล invoice ทั้งหมดจาก D365 API ตามช่วงวันที่
    
    ⚠️ AGGRESSIVE RETRY MODE:
    - Retry ทุก error ไม่เว้น
    - ถ้า page ใดล้มเหลว จะ raise exception เพื่อให้ Airflow retry ทั้ง job
    - รับประกันว่าได้ข้อมูลครบถ้วน 100%
    """
    invoice_api_url = os.getenv("INVOICE_API_URL", "").strip() or DEFAULT_INVOICE_API_URL
    invoice_api_key = os.getenv("INVOICE_API_KEY", "").strip() or DEFAULT_INVOICE_API_KEY
    
    headers = {
        "apikey": invoice_api_key,
        "Content-Type": "application/json",
    }
    
    rows = []
    page = 1
    max_page = 1000
    
    logger.info(f"📥 Loading invoices from D365 API...")
    logger.info(f"   Date range: {start_date} to {end_date}")
    logger.info(f"   Retry config: MAX_RETRIES={API_MAX_RETRIES}, DELAY={API_RETRY_DELAY}s")
    
    date_from = start_date.isoformat()
    date_to = end_date.isoformat()
    
    while page <= max_page:
        payload = {
            "page": page,
            "size": API_PAGE_SIZE,
            "Posting Date": {"$gte": date_from, "$lte": date_to}
        }

        # ⭐ Retry loop สำหรับแต่ละ page (retry ทุกกรณี error)
        retry = 0
        success = False
        last_error = None
        
        while retry <= API_MAX_RETRIES:
            try:
                if retry > 0:
                    wait = API_RETRY_DELAY * retry  # backoff: 10s, 20s, 30s
                    logger.warning(f"  🔄 Retry {retry}/{API_MAX_RETRIES} for page={page} (waiting {wait}s...)")
                    time.sleep(wait)

                resp = requests.post(
                    invoice_api_url,
                    json=payload,
                    headers=headers,
                    timeout=API_TIMEOUT,
                )
                resp.raise_for_status()

                data = resp.json()
                items = data.get("data") or []

                if not items:
                    logger.info(f"  ✓ page={page}: No more data (reached end)")
                    logger.info(f"📊 Total invoices loaded: {len(rows)}")
                    return rows  # จบ job สำเร็จ

                rows.extend(items)
                logger.info(f"  ✓ page={page}: Loaded {len(items)} invoices (total: {len(rows)})")

                if len(items) < API_PAGE_SIZE:
                    logger.info(f"  ✓ Completed (last page with {len(items)} items)")
                    logger.info(f"📊 Total invoices loaded: {len(rows)}")
                    return rows  # จบ job สำเร็จ

                success = True
                break  # page นี้สำเร็จ ออกจาก retry loop

            except requests.exceptions.Timeout as e:
                last_error = f"TIMEOUT (timeout={API_TIMEOUT}s): {e}"
                logger.error(f"  ❌ {last_error}")
                logger.warning(f"  ⚠️ Partial data so far: {len(rows)} records")
                retry += 1

            except requests.exceptions.ConnectionError as e:
                last_error = f"CONNECTION ERROR: {e}"
                logger.error(f"  ❌ {last_error}")
                retry += 1

            except requests.exceptions.HTTPError as e:
                status_code = getattr(resp, 'status_code', 'unknown')
                last_error = f"HTTP ERROR {status_code}: {e}"
                logger.error(f"  ❌ {last_error}")
                retry += 1

            except Exception as e:
                last_error = f"UNEXPECTED ERROR ({type(e).__name__}): {e}"
                logger.error(f"  ❌ {last_error}")
                retry += 1

        # ✅ ถ้า page นี้ล้มเหลวหลัง retry หมด → RAISE EXCEPTION
        if not success:
            error_msg = (
                f"⛔ CRITICAL: Page {page} failed after {API_MAX_RETRIES} retries.\n"
                f"   Last error: {last_error}\n"
                f"   Partial data collected: {len(rows)} records\n"
                f"   ❌ Job FAILED - ไม่รับประกันความครบถ้วนของข้อมูล"
            )
            logger.error(error_msg)
            # � Raise exception เพื่อให้ Airflow retry ทั้ง job
            raise Exception(f"Failed to fetch page {page} after {API_MAX_RETRIES} retries: {last_error}")

        page += 1
    
    logger.info(f"📊 Total invoices loaded: {len(rows)}")
    return rows


def parse_invoice_record(invoice_data: Dict, calculation_date: date) -> Optional[InvoiceCacheRecord]:
    """แปลงข้อมูล invoice จาก API เป็น InvoiceCacheRecord"""
    try:
        # ข้อมูลที่จำเป็น (ใช้ field names ใหม่)
        document_no = invoice_data.get('Document No.') or invoice_data.get('document_no')
        customer_code = invoice_data.get('customer_code')  # ✅ NEW
        posting_date_str = invoice_data.get('Posting Date') or invoice_data.get('posting_date')
        sku = invoice_data.get('sku')  # ✅ NEW
        
        if not document_no or not customer_code or not posting_date_str:
            return None
        
        # แปลงวันที่
        try:
            if isinstance(posting_date_str, str):
                posting_date = datetime.fromisoformat(posting_date_str.replace("Z", "+00:00")).date()
            else:
                posting_date = posting_date_str
        except:
            return None
        
        # ข้อมูลเพิ่มเติม (ใช้ field names ใหม่)
        order_no = invoice_data.get('Order No.') or invoice_data.get('order_no') or ""
        sell_to_customer_name = invoice_data.get('Sell_to_Customer_Name') or ""  # ✅ NEW
        description = invoice_data.get('Description') or invoice_data.get('description') or ""
        variant_code = invoice_data.get('Variant_Code') or invoice_data.get('variant_code') or ""  
        unit_of_measure = invoice_data.get('Unit of Measure') or invoice_data.get('unit_of_measure') or ""
        project_no = invoice_data.get('Project_No') or invoice_data.get('project_no') or "" 
        
        # ตัวเลข (ใช้ field names ใหม่)
        try:
            quantity = float(invoice_data.get('Quantity') or invoice_data.get('quantity') or 0)
        except:
            quantity = 0.0
        
        try:
            unit_price = float(invoice_data.get('Unit_Price') or invoice_data.get('unit_price') or 0)  # ✅ NEW
        except:
            unit_price = 0.0
        
        try:
            line_amount = float(invoice_data.get('Line_Amount') or invoice_data.get('line_amount') or 0)  # ✅ NEW
        except:
            line_amount = 0.0
        
        try:
            line_amount_vat = float(invoice_data.get('Line_Amount_Include_VAT') or 
                                   invoice_data.get('amount_including_vat') or 0)  # ✅ NEW
        except:
            line_amount_vat = 0.0
        
        return InvoiceCacheRecord(
            document_no=document_no,
            order_no=order_no,
            customer_code=customer_code,
            sell_to_customer_name=sell_to_customer_name,
            posting_date=posting_date,
            sku=sku,
            description=description,
            variant_code=variant_code,
            quantity=quantity,
            unit_of_measure=unit_of_measure,
            unit_price=unit_price,
            line_amount=line_amount,
            line_amount_include_vat=line_amount_vat,
            project_no=project_no
        )
        
    except Exception as e:
        logger.warning(f"  ⚠️ Failed to parse invoice: {e}")
        return None


# =========================
# DATABASE FUNCTIONS
# =========================

def upsert_invoice_batch(invoices: List[InvoiceCacheRecord], conn: pyodbc.Connection) -> int:
    """บันทึก invoice batch ลง database แบบ executemany (เร็วกว่า row-by-row)"""
    if not invoices:
        return 0
    
    cursor = conn.cursor()
    current_time = datetime.now()
    
    # ใช้ MERGE statement เดียวกัน แต่ใช้ executemany แทน
    merge_sql = """
    MERGE INTO Invoice AS target
    USING (VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)) 
        AS source (Document_No, Order_No, customer_code, Sell_to_Customer_Name,
                   Posting_Date, sku, Description, Variant_Code, Quantity,
                   Unit_of_Measure, Unit_Price, Line_Amount, Line_Amount_Include_VAT,
                   Project_No, updated_at)
    ON target.Document_No = source.Document_No AND target.sku = source.sku
    WHEN MATCHED THEN
        UPDATE SET
            Order_No = source.Order_No,
            customer_code = source.customer_code,
            Sell_to_Customer_Name = source.Sell_to_Customer_Name,
            Posting_Date = source.Posting_Date,
            Description = source.Description,
            Variant_Code = source.Variant_Code,
            Quantity = source.Quantity,
            Unit_of_Measure = source.Unit_of_Measure,
            Unit_Price = source.Unit_Price,
            Line_Amount = source.Line_Amount,
            Line_Amount_Include_VAT = source.Line_Amount_Include_VAT,
            Project_No = source.Project_No,
            updated_at = source.updated_at
    WHEN NOT MATCHED THEN
        INSERT (Document_No, Order_No, customer_code, Sell_to_Customer_Name,
                Posting_Date, sku, Description, Variant_Code, Quantity,
                Unit_of_Measure, Unit_Price, Line_Amount, Line_Amount_Include_VAT,
                Project_No, created_at, updated_at)
        VALUES (source.Document_No, source.Order_No, source.customer_code,
                source.Sell_to_Customer_Name, source.Posting_Date, source.sku,
                source.Description, source.Variant_Code, source.Quantity,
                source.Unit_of_Measure, source.Unit_Price, source.Line_Amount,
                source.Line_Amount_Include_VAT, source.Project_No, source.updated_at, source.updated_at);
    """
    
    # เตรียมข้อมูลเป็น list of tuples
    params = [
        (
            invoice.document_no,
            invoice.order_no or None,
            invoice.customer_code,
            invoice.sell_to_customer_name or None,
            invoice.posting_date,
            invoice.sku,
            invoice.description or None,
            invoice.variant_code or None,
            invoice.quantity,
            invoice.unit_of_measure or None,
            invoice.unit_price,
            invoice.line_amount,
            invoice.line_amount_include_vat,
            invoice.project_no or None,
            current_time
        )
        for invoice in invoices
    ]
    
    DB_MAX_RETRIES = int(os.getenv("DB_MAX_RETRIES", "3"))
    DB_RETRY_DELAY = int(os.getenv("DB_RETRY_DELAY", "5"))

    # ── Phase 1: executemany (fast) with retry ──────────────────────────────
    batch_success = False
    for attempt in range(1, DB_MAX_RETRIES + 1):
        try:
            cursor.fast_executemany = True
            cursor.executemany(merge_sql, params)
            conn.commit()
            success_count = len(invoices)
            logger.info(f"  ✅ Batch inserted/updated {success_count} invoices")
            batch_success = True
            break
        except Exception as e:
            conn.rollback()
            if attempt < DB_MAX_RETRIES:
                wait = DB_RETRY_DELAY * attempt  # backoff: 5s, 10s, 15s
                logger.warning(
                    f"  ⚠️ Batch attempt {attempt}/{DB_MAX_RETRIES} failed: {e} "
                    f"— retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                logger.error(
                    f"  ❌ Batch failed after {DB_MAX_RETRIES} attempts: {e}"
                )

    if batch_success:
        cursor.close()
        return success_count

    # ── Phase 2: fallback row-by-row with retry ─────────────────────────────
    logger.info("  🔄 Falling back to row-by-row insert with retry...")
    cursor.fast_executemany = False
    success_count = 0

    for param in params:
        doc_no = param[0]
        row_saved = False

        for attempt in range(1, DB_MAX_RETRIES + 1):
            try:
                cursor.execute(merge_sql, param)
                success_count += 1
                row_saved = True
                break
            except Exception as row_e:
                conn.rollback()
                if attempt < DB_MAX_RETRIES:
                    wait = DB_RETRY_DELAY * attempt
                    logger.warning(
                        f"  ⚠️ Row {doc_no} attempt {attempt}/{DB_MAX_RETRIES} failed: {row_e} "
                        f"— retrying in {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        f"  ❌ Row {doc_no} failed after {DB_MAX_RETRIES} attempts: {row_e}"
                    )

        if not row_saved:
            logger.error(f"  ⛔ Skipping invoice {doc_no} — could not save after all retries")

    conn.commit()
    logger.info(f"  ✅ Row-by-row completed: {success_count}/{len(params)} saved")

    cursor.close()
    return success_count


# =========================
# MAIN JOB FUNCTION
# =========================

def run_invoice_cache_refresh(months: int = 6) -> InvoiceJobResult:
    """
    รัน invoice cache refresh job
    
    Args:
        months: จำนวนเดือนย้อนหลังที่ต้องการดึง (default: 6)
    
    Returns:
        InvoiceJobResult
    """
    start_time = datetime.now()
    calculation_date = date.today()
    
    logger.info("=" * 80)
    logger.info("🚀 Starting Invoice Cache Refresh Job")
    logger.info(f"   Start Time: {start_time}")
    logger.info(f"   Calculation Date: {calculation_date}")
    logger.info(f"   Months: {months}")
    logger.info("=" * 80)
    
    result = InvoiceJobResult(
        start_time=start_time,
        end_time=start_time,
        calculation_date=calculation_date
    )
    
    try:
        # คำนวณช่วงวันที่ (ใช้ relativedelta นับเดือนที่แม่นยำ)
        end_date = calculation_date
        start_date = calculation_date - relativedelta(months=months)
        
        # ดึงข้อมูล invoice (จะ raise exception ถ้าล้มเหลว)
        invoices_data = load_all_invoices_from_d365(start_date, end_date)
        
        if not invoices_data:
            logger.warning("⚠️ No invoices loaded from API (date range may be empty)")
            result.end_time = datetime.now()
            return result
        
        # แปลงและบันทึกข้อมูล
        conn = get_mssql_conn()
        batch = []
        
        for idx, inv_data in enumerate(invoices_data, 1):
            try:
                invoice_record = parse_invoice_record(inv_data, calculation_date)
                
                if not invoice_record:
                    result.invoices_failed += 1
                    continue
                
                batch.append(invoice_record)
                result.invoices_processed += 1
                
                # บันทึก batch
                if len(batch) >= BATCH_SIZE:
                    success_count = upsert_invoice_batch(batch, conn)
                    result.invoices_inserted += success_count
                    logger.info(f"  ✓ Processed {result.invoices_processed}/{len(invoices_data)} invoices")
                    batch = []
                
            except Exception as e:
                logger.error(f"  ❌ Error processing invoice {idx}: {e}")
                result.invoices_failed += 1
                result.errors.append(f"Invoice {idx}: {str(e)}")
        
        # บันทึก batch สุดท้าย
        if batch:
            success_count = upsert_invoice_batch(batch, conn)
            result.invoices_inserted += success_count
        
        conn.close()
        
        # ✅ ตรวจสอบว่าบันทึกข้อมูลครบหรือไม่
        if result.invoices_processed > 0:
            success_rate = (result.invoices_inserted / result.invoices_processed) * 100
            logger.info(f"📊 Success rate: {success_rate:.2f}% ({result.invoices_inserted}/{result.invoices_processed})")
        
    except Exception as e:
        error_msg = f"❌ CRITICAL ERROR: {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        result.errors.append(error_msg)
        result.end_time = datetime.now()
        
        # 🚨 Re-raise exception เพื่อให้ Airflow รู้ว่า job ล้มเหลว
        raise
    
    result.end_time = datetime.now()
    
    logger.info("=" * 80)
    if result.errors:
        logger.error("❌ Invoice Cache Refresh Job FAILED")
    else:
        logger.info("✅ Invoice Cache Refresh Job Completed Successfully")
    logger.info(f"   Duration: {result.duration_seconds:.2f} seconds")
    logger.info(f"   Invoices Processed: {result.invoices_processed}")
    logger.info(f"   Invoices Inserted: {result.invoices_inserted}")
    logger.info(f"   Invoices Failed: {result.invoices_failed}")
    if result.errors:
        logger.error(f"   ⚠️ Errors: {len(result.errors)}")
        for err in result.errors[:3]:  # แสดง 3 errors แรก
            logger.error(f"      - {err}")
    logger.info("=" * 80)
    
    return result


# =========================
# CLI ENTRY POINT
# =========================

if __name__ == "__main__":
    """Run the job when executed as a script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Invoice Cache Refresh Job (Aggressive Retry Mode)')
    parser.add_argument('--months', type=int, default=6, help='Number of months to fetch (default: 6)')
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 Invoice Cache Refresh Job - AGGRESSIVE RETRY MODE")
    print("=" * 80)
    print(f"⚙️  Config:")
    print(f"   - Months: {args.months}")
    print(f"   - Max Retries: {API_MAX_RETRIES}")
    print(f"   - Retry Delay: {API_RETRY_DELAY}s (with exponential backoff)")
    print(f"   - Timeout: {API_TIMEOUT}s")
    print(f"   - Batch Size: {BATCH_SIZE}")
    print("=" * 80)
    print(f"⚠️  Note: Job will FAIL and raise exception if any page cannot be fetched")
    print(f"   after {API_MAX_RETRIES} retries to ensure data completeness.")
    print("=" * 80)
    print()
    
    try:
        result = run_invoice_cache_refresh(months=args.months)
        
        # Print summary
        print("\n" + "=" * 80)
        print("INVOICE CACHE RESULT:")
        print("=" * 80)
        print(f"Duration: {result.duration_seconds:.2f} seconds")
        print(f"Processed: {result.invoices_processed}")
        print(f"Inserted: {result.invoices_inserted}")
        print(f"Failed: {result.invoices_failed}")
        
        if result.errors:
            print(f"\n⚠️ Errors ({len(result.errors)}):")
            for error in result.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(result.errors) > 10:
                print(f"  ... and {len(result.errors) - 10} more errors")
            print("\n❌ Job completed with errors")
            exit(1)
        else:
            print("\n✅ Invoice cache refresh completed successfully")
            exit(0)
            
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ JOB FAILED")
        print("=" * 80)
        print(f"Error: {type(e).__name__}")
        print(f"Detail: {str(e)}")
        print("=" * 80)
        print("\n💡 Tip: Airflow will automatically retry this job based on DAG configuration")
        exit(1)
