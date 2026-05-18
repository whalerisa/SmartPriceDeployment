"""
Scheduled Price Upload Job - Standalone Version

This job runs daily to check for scheduled price upload files and process them.

File Naming Convention:
- {Category}{DDMMYYYY}.xlsx
- Example: G26092569.xlsx (Glass category, 26/09/2569 Buddhist year)

Process:
1. Check SCHEDULED_UPLOAD_FOLDER for files
2. Parse filename to extract date
3. If file date matches today, process upload
4. Move processed files to archive folder

Configuration:
--------------
Environment variables:
- SCHEDULED_UPLOAD_FOLDER: Folder containing scheduled upload files
- MSSQL_SERVER, MSSQL_DATABASE, MSSQL_USERNAME, MSSQL_PASSWORD

Usage:
------
1. Direct execution:
   python scheduled_price_upload_standalone.py

2. In Task Scheduler (Windows):
   Schedule to run daily at 00:00

Requirements:
-------------
- pyodbc
- pandas
- openpyxl

Install with:
    pip install pyodbc pandas openpyxl
"""

import os
import sys
import time
import logging
import pyodbc
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# Add parent directory to path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ⭐ Load .env file before importing anything else
from dotenv import load_dotenv

# Find and load .env file
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
else:
    print(f"⚠️ .env file not found at: {env_path}")

from services.price_upload_service import PriceUploadService, UploadResult, extract_version_key_from_filename


# =========================
# LOGGING SETUP
# =========================

LOG_FILE = "logs/scheduled_price_upload.log"
LOG_LEVEL = "INFO"
LOG_BACKUP_COUNT = 30


def setup_logger():
    """Setup logger with file and console handlers"""
    logger = logging.getLogger('scheduled_price_upload')
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
# DATABASE CONFIG
# =========================

MSSQL_CONFIG = {
    "server": os.getenv("MSSQL_SERVER", "192.192.0.220,50681"),
    "database": os.getenv("MSSQL_DATABASE", "SP681"),
    "username": os.getenv("MSSQL_USERNAME", "sp681_user"),
    "password": os.getenv("MSSQL_PASSWORD", "Tng#kmitl2"),
    "driver": os.getenv("MSSQL_DRIVER", "{ODBC Driver 17 for SQL Server}"),
}


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
class ScheduledUploadJobResult:
    """Result of scheduled price upload job"""
    start_time: datetime
    end_time: datetime
    files_found: int = 0
    files_processed: int = 0
    files_failed: int = 0
    total_items_uploaded: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate job duration in seconds"""
        return (self.end_time - self.start_time).total_seconds()


# =========================
# BUSINESS LOGIC
# =========================

def parse_filename_date(filename: str) -> Optional[datetime]:
    """
    Parse date from filename format: {Category}{DDMMYYYY}.xlsx or {Category}{DDMMYYYY}_{Key}.xlsx
    
    Args:
        filename: Filename to parse (e.g., "G26092569.xlsx" or "G26092569_G0001.xlsx")
    
    Returns:
        datetime object or None if parsing fails
    """
    try:
        # Remove extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # ⭐ ตัด suffix _G0000 ออกก่อนถ้ามี
        import re as _re
        name_without_ext = _re.sub(r'_[GAYSCE]\d{4}$', '', name_without_ext, flags=_re.IGNORECASE)
        
        # Extract date part (skip first character which is category)
        if len(name_without_ext) < 9:  # Category + 8 digits
            return None
        
        date_str = name_without_ext[1:]  # Skip category letter
        
        # Parse DDMMYYYY
        day = int(date_str[0:2])
        month = int(date_str[2:4])
        year_buddhist = int(date_str[4:8])
        
        # Convert Buddhist year to Gregorian year
        year_gregorian = year_buddhist - 543
        
        # Create datetime object
        file_date = datetime(year_gregorian, month, day)
        
        return file_date
        
    except Exception as e:
        logger.warning(f"Failed to parse date from filename '{filename}': {e}")
        return None


def load_metadata(file_path: str) -> Optional[Dict]:
    """
    Load metadata from companion JSON file
    
    Args:
        file_path: Path to Excel file
    
    Returns:
        Metadata dictionary or None if not found
    """
    metadata_path = file_path + ".meta.json"
    
    if not os.path.exists(metadata_path):
        logger.warning(f"Metadata file not found: {metadata_path}")
        return None
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return metadata
    except Exception as e:
        logger.error(f"Failed to load metadata from {metadata_path}: {e}")
        return None


def process_scheduled_file(file_path: str, conn: pyodbc.Connection) -> UploadResult:
    """
    Process a scheduled price upload file
    
    Args:
        file_path: Path to Excel file
        conn: Database connection
    
    Returns:
        UploadResult with statistics
    """
    logger.info(f"Processing file: {file_path}")
    
    # Load metadata
    metadata = load_metadata(file_path)
    
    # ⭐ ดึง version_key จาก metadata ก่อน, ถ้าไม่มีลอง parse จากชื่อไฟล์
    version_key = None
    if metadata:
        version_key = metadata.get("version_key")
    if not version_key:
        version_key = extract_version_key_from_filename(file_path)
    if version_key:
        logger.info(f"Using version key: {version_key}")
    else:
        logger.warning(f"⚠️ No version key found for {file_path}, will use default UPLOAD_... naming")
    
    if not metadata:
        logger.warning(f"No metadata found for {file_path}, using defaults")
        employee_info = {
            "employee_id": "system",
            "name": "Scheduled Upload System",
            "role": "SYSTEM"
        }
    else:
        employee_info = {
            "employee_id": metadata.get("uploaded_by", "system"),
            "name": metadata.get("uploaded_by_name", "Scheduled Upload System"),
            "role": "SYSTEM"
        }
    
    # ⭐ Process upload once - branch codes are read from file
    service = PriceUploadService(conn)
    
    logger.info(f"  Processing file - branch codes will be read from Branch column")
    result = service.process_upload(
        file_path=file_path,
        branch_code=None,  # Not used - reads from file
        employee_info=employee_info,
        version_key=version_key  # ⭐ ส่ง key ไปบันทึกใน version_name
    )
    
    logger.info(
        f"  Processing completed: successful={result.successful_updates}, errors={result.errors}"
    )
    
    return result


def archive_file(file_path: str, success: bool):
    """
    Move processed file to archive folder
    
    Args:
        file_path: Path to file
        success: Whether processing was successful
    """
    try:
        # Create archive folder
        base_folder = os.path.dirname(file_path)
        archive_folder = os.path.join(base_folder, "archive")
        os.makedirs(archive_folder, exist_ok=True)
        
        # Add timestamp to filename
        filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        status = "success" if success else "failed"
        
        name_without_ext, ext = os.path.splitext(filename)
        archived_filename = f"{name_without_ext}_{status}_{timestamp}{ext}"
        
        archived_path = os.path.join(archive_folder, archived_filename)
        
        # Move file
        os.rename(file_path, archived_path)
        logger.info(f"Archived file to: {archived_path}")
        
        # Also move metadata file if exists
        metadata_path = file_path + ".meta.json"
        if os.path.exists(metadata_path):
            archived_metadata_path = archived_path + ".meta.json"
            os.rename(metadata_path, archived_metadata_path)
            logger.info(f"Archived metadata to: {archived_metadata_path}")
        
    except Exception as e:
        logger.error(f"Failed to archive file {file_path}: {e}")


# =========================
# MAIN JOB FUNCTION
# =========================

def run_scheduled_price_upload() -> ScheduledUploadJobResult:
    """
    Main job function: Check for scheduled price upload files and process them
    
    Returns:
        ScheduledUploadJobResult with job execution details
    """
    start_time = datetime.now()
    result = ScheduledUploadJobResult(start_time=start_time, end_time=start_time)
    
    try:
        logger.info("=" * 80)
        logger.info("🕐 Scheduled Price Upload Job Started")
        logger.info(f"   Triggered at: {start_time}")
        logger.info("=" * 80)
        
        # Get folder path from environment variable (set by config_router.py)
        scheduled_folder = os.getenv("PRICE_FILES_FOLDER", "./uploads/price_files")
        
        logger.info(f"📁 Using price files folder from config: {scheduled_folder}")
        
        if not os.path.exists(scheduled_folder):
            logger.warning(f"Scheduled upload folder not found: {scheduled_folder}")
            logger.info("Creating folder...")
            os.makedirs(scheduled_folder, exist_ok=True)
        
        logger.info(f"📁 Checking folder: {scheduled_folder}")
        logger.info(f"📁 Folder exists: {os.path.exists(scheduled_folder)}")
        
        # Get today's date
        today = datetime.now().date()
        logger.info(f"📅 Today's date: {today}")
        
        # Find all Excel files in folder
        excel_files = []
        for filename in os.listdir(scheduled_folder):
            if filename.endswith(('.xlsx', '.xls')) and not filename.startswith('~'):
                excel_files.append(filename)
        
        logger.info(f"📄 Found {len(excel_files)} Excel file(s) in folder")
        result.files_found = len(excel_files)
        
        if not excel_files:
            logger.info("✅ No files to process")
            result.end_time = datetime.now()
            return result
        
        # Process each file
        conn = get_mssql_conn()
        
        for filename in excel_files:
            try:
                file_path = os.path.join(scheduled_folder, filename)
                
                # Parse date from filename
                file_date = parse_filename_date(filename)
                
                if not file_date:
                    logger.warning(f"⚠️  Skipping file with invalid date format: {filename}")
                    continue
                
                logger.info(f"📄 File: {filename}, Date: {file_date.date()}")
                
                # Check if file date matches today
                if file_date.date() == today:
                    logger.info(f"✅ File date matches today, processing...")
                    
                    # Process file
                    upload_result = process_scheduled_file(file_path, conn)
                    
                    result.files_processed += 1
                    result.total_items_uploaded += upload_result.successful_updates
                    
                    # ⭐ ถือว่าสำเร็จถ้ามีการอัปเดตอย่างน้อย 1 รายการ
                    if upload_result.successful_updates > 0:
                        logger.info(f"✅ File processed successfully: {upload_result.successful_updates} items uploaded")
                        if upload_result.errors > 0:
                            logger.warning(f"⚠️  Note: {upload_result.errors} rows were skipped (empty SKU or not found in Item_Master)")
                        archive_file(file_path, success=True)
                    else:
                        # ไม่มีการอัปเดตเลย = Failed
                        result.files_failed += 1
                        result.errors.extend(upload_result.error_details)
                        logger.error(f"❌ File processing failed: No items were uploaded")
                        archive_file(file_path, success=False)
                else:
                    logger.info(f"⏳ File scheduled for {file_date.date()}, skipping for now")
            
            except Exception as e:
                error_msg = f"Failed to process file {filename}: {e}"
                logger.error(error_msg, exc_info=True)
                result.errors.append(error_msg)
                result.files_failed += 1
        
        conn.close()
        
        result.end_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info("✅ Scheduled Price Upload Job Completed")
        logger.info(f"   Duration: {result.duration_seconds:.2f} seconds")
        logger.info(f"   Files Found: {result.files_found}")
        logger.info(f"   Files Processed: {result.files_processed}")
        logger.info(f"   Files Failed: {result.files_failed}")
        logger.info(f"   Total Items Uploaded: {result.total_items_uploaded}")
        if result.errors:
            logger.info(f"   Errors: {len(result.errors)}")
            for error in result.errors:
                logger.error(f"     - {error}")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in scheduled price upload job: {e}", exc_info=True)
        result.errors.append(str(e))
        result.end_time = datetime.now()
        return result


# =========================
# CLI ENTRY POINT
# =========================

if __name__ == "__main__":
    """Run the job when executed as a script"""
    print("Starting Scheduled Price Upload Job...")
    result = run_scheduled_price_upload()
    
    # Print summary
    print("\n" + "=" * 80)
    print("JOB SUMMARY")
    print("=" * 80)
    print(f"Duration: {result.duration_seconds:.2f} seconds")
    print(f"Files Found: {result.files_found}")
    print(f"Files Processed: {result.files_processed}")
    print(f"Files Failed: {result.files_failed}")
    print(f"Total Items Uploaded: {result.total_items_uploaded}")
    
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")
        exit(1)
    else:
        print("\n✅ Job completed successfully!")
        exit(0)
