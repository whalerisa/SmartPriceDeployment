"""
Scheduled Price Upload Job - Fully Standalone Version

ไฟล์นี้เป็น standalone 100% ไม่ต้อง import ไฟล์อื่นในโปรเจค
สามารถนำไปวางที่ไหนก็ได้ รันได้เลย

Requirements:
- pyodbc
- pandas
- openpyxl

Install: pip install pyodbc pandas openpyxl

Usage:
    python scheduled_price_upload_fully_standalone.py
"""

import os
import re
import logging
import pyodbc
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from logging.handlers import TimedRotatingFileHandler
import pandas as pd


# =========================
# CONFIGURATION
# =========================

# ⭐ Database Configuration (แก้ไขตรงนี้)
MSSQL_CONFIG = {
    "server": "192.192.0.220,50681",
    "database": "SP681",
    "username": "sp681_user",
    "password": "Tng#kmitl2",
    "driver": "{ODBC Driver 17 for SQL Server}",
}

# ⭐ Scheduled Upload Folder (แก้ไขตรงนี้)
SCHEDULED_FOLDER = r"/mnt/c/Users/kongd/Desktop/SP681/UploadsPrice"

# ⭐ Log Configuration
LOG_FILE = "scheduled_price_upload.log"
LOG_LEVEL = "INFO"
LOG_BACKUP_COUNT = 30


# =========================
# LOGGING SETUP
# =========================

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
# DATABASE
# =========================

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
class UploadResult:
    """Result of a price upload operation"""
    total_rows: int
    successful_updates: int
    errors: int
    error_details: List[str]


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
# PRICE UPLOAD SERVICE (Embedded)
# =========================

class PriceUploadService:
    """Service for processing price file uploads"""
    
    def __init__(self, db_connection):
        self.db_connection = db_connection
        self._branch_code = None
        self._employee_info = None
        self._version_key = None  # ⭐ Key สำหรับบันทึกใน version_name
    
    def process_upload(self, file_path: str, branch_code: Optional[str], employee_info: dict, version_key: Optional[str] = None) -> UploadResult:
        """Process price file and update Item_Price table - reads Branch from file"""
        self._branch_code = branch_code  # Legacy - not used
        self._employee_info = employee_info
        self._version_key = version_key  # ⭐ เก็บ key
        
        logger.info(f"Processing price upload: {file_path}")
        if version_key:
            logger.info(f"Version key: {version_key}")
        
        # Parse Excel file
        try:
            df = pd.read_excel(file_path, engine="openpyxl")
            price_data = df.to_dict("records")
        except Exception as e:
            logger.error(f"Failed to parse file: {str(e)}")
            raise
        
        # Find SKU column
        sku_column = None
        for col_name in ["SKU", "No_", "Item_No", "No", "ItemNo"]:
            if col_name in df.columns:
                sku_column = col_name
                break
        
        if not sku_column:
            raise ValueError("SKU column not found")
        
        # ⭐ Find Branch column
        branch_column = None
        for col_name in ["Branch", "BranchCode", "Branch_Code", "สาขา"]:
            if col_name in df.columns:
                branch_column = col_name
                break
        
        if not branch_column:
            raise ValueError("Branch column not found - file must have Branch column")
        
        logger.info(f"Using SKU column: {sku_column}, Branch column: {branch_column}")
        
        # Create version log
        version_id = self._create_version_log(price_data, sku_column)
        
        # Process each row
        total_rows = len(price_data)
        successful_updates = 0
        errors = 0
        error_details = []
        
        BATCH_SIZE = 100
        batch_count = 0
        
        for idx, row in enumerate(price_data, start=1):
            try:
                # Get SKU
                sku_value = row.get(sku_column, "")
                if isinstance(sku_value, (int, float)):
                    sku = str(sku_value).strip()
                else:
                    sku = str(sku_value).strip() if sku_value else ""
                
                # Skip empty SKU
                if not sku or sku.lower() == 'nan':
                    errors += 1
                    continue
                
                # ⭐ Get Branch from file
                branch_value = row.get(branch_column, "")
                if isinstance(branch_value, (int, float)):
                    branch_code_from_file = str(branch_value).strip()
                else:
                    branch_code_from_file = str(branch_value).strip() if branch_value else ""
                
                # Skip empty Branch
                if not branch_code_from_file or branch_code_from_file.lower() == 'nan':
                    error_details.append(f"Row {idx}: SKU '{sku}' has empty Branch code")
                    errors += 1
                    continue
                
                # Validate SKU exists
                if not self._sku_exists(sku):
                    error_details.append(f"Row {idx}: SKU '{sku}' not found")
                    errors += 1
                    continue
                
                # Extract prices
                package_size = self._parse_decimal(row.get("PackageSize"))
                if package_size is None or package_size <= 0:
                    package_size = 1
                
                alternate_name = row.get("AlternateName", "")
                if alternate_name and isinstance(alternate_name, str):
                    alternate_name = alternate_name.strip()
                else:
                    alternate_name = None
                
                price_record = {
                    "SKU": sku,
                    "BranchCode": branch_code_from_file,  # ⭐ Use branch from file
                    "SDM": self._parse_decimal(row.get("SDM")),
                    "R2": self._parse_decimal(row.get("R2")),
                    "R1": self._parse_decimal(row.get("R1")),
                    "W2": self._parse_decimal(row.get("W2")),
                    "W1": self._parse_decimal(row.get("W1")),
                    "PackageSize": package_size,
                    "AlternateName": alternate_name
                }
                
                # Upsert price
                self._upsert_price(price_record, version_id, idx, auto_commit=False)
                successful_updates += 1
                batch_count += 1
                
                # Batch commit
                if batch_count >= BATCH_SIZE:
                    self.db_connection.commit()
                    batch_count = 0
            
            except Exception as e:
                error_details.append(f"Row {idx}: {str(e)}")
                errors += 1
        
        # Final commit
        if batch_count > 0:
            self.db_connection.commit()
        
        return UploadResult(
            total_rows=total_rows,
            successful_updates=successful_updates,
            errors=errors,
            error_details=error_details
        )
    
    def _sku_exists(self, sku: str) -> bool:
        """Check if SKU exists in Item_Master"""
        cursor = self.db_connection.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM Item_Master WHERE SKU = ?", (sku,))
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            cursor.close()
    
    def _parse_decimal(self, value) -> Optional[float]:
        """Parse decimal value"""
        if pd.isna(value) or value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _create_version_log(self, price_data: List[Dict], sku_column: str) -> int:
        """Create version log in Item_Update_Version"""
        cursor = self.db_connection.cursor()
        try:
            # ⭐ ใช้ key ถ้ามี, ไม่งั้น default
            if self._version_key:
                version_name = self._version_key
            else:
                now = datetime.now()
                version_name = f"UPLOAD_{now.strftime('%Y%m%d_%H%M%S')}"
            
            # Detect categories
            categories = set()
            for row in price_data:
                sku_value = row.get(sku_column, "")
                if isinstance(sku_value, (int, float)):
                    sku = str(sku_value).strip()
                else:
                    sku = str(sku_value).strip() if sku_value else ""
                
                if sku and len(sku) > 0:
                    category = sku[0].upper()
                    if category in ['G', 'A', 'Y', 'S', 'C', 'E']:
                        categories.add(category)
            
            update_type = "MIXED" if len(categories) > 1 else (list(categories)[0] if categories else "MIXED")
            
            uploaded_by = self._employee_info.get('employee_id', 'system')
            job_title = self._employee_info.get('role', 'MANAGER')
            
            # Get next version_id
            cursor.execute("SELECT ISNULL(MAX(version_id), 0) + 1 FROM Item_Update_Version")
            version_id = int(cursor.fetchone()[0])
            
            uploaded_at = datetime.now()
            
            cursor.execute("""
                INSERT INTO Item_Update_Version (
                    version_id, version_name, update_type, uploaded_by, job_title, 
                    uploaded_at, status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (version_id, version_name, update_type, uploaded_by, job_title, uploaded_at))
            
            self.db_connection.commit()
            return version_id
        finally:
            cursor.close()
    
    def _upsert_price(self, price_data: Dict, version_id: int, row_index: int, auto_commit: bool = True):
        """Insert or update price in Item_Price table"""
        sku = price_data["SKU"]
        cursor = self.db_connection.cursor()
        
        try:
            branch_code = price_data["BranchCode"]
            
            # Get old prices
            cursor.execute("""
                SELECT R1, R2, W1, W2, AlternateName
                FROM Item_Price WITH (NOLOCK)
                WHERE SKU = ? AND BranchCode = ?
            """, (sku, branch_code))
            
            old_row = cursor.fetchone()
            if old_row:
                old_R1, old_R2, old_W1, old_W2, old_alternate_name = old_row
                exists = True
            else:
                old_R1 = old_R2 = old_W1 = old_W2 = old_alternate_name = None
                exists = False
            
            new_R1 = price_data["R1"]
            new_R2 = price_data["R2"]
            new_W1 = price_data["W1"]
            new_W2 = price_data["W2"]
            new_alternate_name = price_data["AlternateName"]
            
            # Calculate change flags
            change_price_flag = 0
            if exists:
                if (old_R1 != new_R1 or old_R2 != new_R2 or old_W1 != new_W1 or old_W2 != new_W2):
                    change_price_flag = 1
            else:
                change_price_flag = 1
            
            change_altname_flag = 0
            if exists:
                if old_alternate_name != new_alternate_name:
                    change_altname_flag = 1
            else:
                if new_alternate_name:
                    change_altname_flag = 1
            
            # Update or Insert
            if exists:
                cursor.execute("""
                    UPDATE Item_Price
                    SET SDM = ?, R2 = ?, R1 = ?, W2 = ?, W1 = ?,
                        PackageSize = ?, AlternateName = ?, UpdatedAt = GETDATE()
                    WHERE SKU = ? AND BranchCode = ?
                """, (
                    price_data["SDM"], price_data["R2"], price_data["R1"],
                    price_data["W2"], price_data["W1"], price_data["PackageSize"],
                    price_data["AlternateName"], sku, branch_code
                ))
            else:
                cursor.execute("""
                    INSERT INTO Item_Price (
                        SKU, BranchCode, SDM, R2, R1, W2, W1, PackageSize, AlternateName, UpdatedAt
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                """, (
                    sku, branch_code, price_data["SDM"], price_data["R2"],
                    price_data["R1"], price_data["W2"], price_data["W1"],
                    price_data["PackageSize"], price_data["AlternateName"]
                ))
            
            # Save detail log
            cursor.execute("SELECT ISNULL(MAX(id), 0) + 1 FROM Item_Update_Version_Detail")
            detail_id = int(cursor.fetchone()[0])
            
            cursor.execute("""
                INSERT INTO Item_Update_Version_Detail (
                    id, version_id, sku, new_no2, 
                    new_R1, new_R2, new_W1, new_W2,
                    old_R1, old_R2, old_W1, old_W2,
                    new_alternate_name, old_alternate_name,
                    change_price_flag, change_altname_flag,
                    BranchCode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                detail_id, version_id, sku, new_alternate_name,
                new_R1, new_R2, new_W1, new_W2,
                old_R1, old_R2, old_W1, old_W2,
                new_alternate_name, old_alternate_name,
                change_price_flag, change_altname_flag,
                branch_code
            ))
            
            if auto_commit:
                self.db_connection.commit()
        finally:
            cursor.close()


# =========================
# BUSINESS LOGIC
# =========================

# ⭐ Filename key pattern: 1 letter (G/A/Y/S/C/E) + 4 digits, e.g. "G0001"
_KEY_PATTERN = re.compile(r'_([GAYSCE]\d{4})$', re.IGNORECASE)


def extract_version_key_from_filename(filename: str) -> Optional[str]:
    """ดึง key (G0000) จากชื่อไฟล์ เช่น G18052569_G0001.xlsx → G0001"""
    if not filename:
        return None
    name_without_ext = os.path.splitext(os.path.basename(filename))[0]
    match = _KEY_PATTERN.search(name_without_ext)
    if match:
        return match.group(1).upper()
    return None


def parse_filename_date(filename: str) -> Optional[datetime]:
    """Parse date from filename format: {Category}{DDMMYYYY}.xlsx or {Category}{DDMMYYYY}_{Key}.xlsx"""
    try:
        name_without_ext = os.path.splitext(filename)[0]
        
        # ⭐ ตัด suffix _G0000 ออกก่อนถ้ามี
        name_without_ext = _KEY_PATTERN.sub('', name_without_ext)
        
        if len(name_without_ext) < 9:
            return None
        
        date_str = name_without_ext[1:]  # Skip category letter
        
        day = int(date_str[0:2])
        month = int(date_str[2:4])
        year_buddhist = int(date_str[4:8])
        
        year_gregorian = year_buddhist - 543
        
        file_date = datetime(year_gregorian, month, day)
        return file_date
    except Exception as e:
        logger.warning(f"Failed to parse date from filename '{filename}': {e}")
        return None


def load_metadata(file_path: str) -> Optional[Dict]:
    """Load metadata from companion JSON file"""
    metadata_path = file_path + ".meta.json"
    
    if not os.path.exists(metadata_path):
        logger.warning(f"Metadata file not found: {metadata_path}")
        return None
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return metadata
    except Exception as e:
        logger.error(f"Failed to load metadata: {e}")
        return None


def process_scheduled_file(file_path: str, conn: pyodbc.Connection) -> UploadResult:
    """Process a scheduled price upload file"""
    logger.info(f"Processing file: {file_path}")
    
    metadata = load_metadata(file_path)
    
    # ⭐ ดึง version_key จาก metadata ก่อน, ถ้าไม่มีก็ลอง parse จากชื่อไฟล์
    version_key = None
    if metadata:
        version_key = metadata.get("version_key")
    if not version_key:
        version_key = extract_version_key_from_filename(file_path)
    if version_key:
        logger.info(f"Using version key: {version_key}")
    else:
        logger.warning(f"⚠️ No version key for {file_path}, will use default UPLOAD_... naming")
    
    if not metadata:
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
    
    # ⭐ Process once - branch codes are read from file
    service = PriceUploadService(conn)
    
    logger.info(f"  Processing file - branch codes will be read from Branch column")
    result = service.process_upload(
        file_path=file_path,
        branch_code=None,  # Not used - reads from file
        employee_info=employee_info,
        version_key=version_key  # ⭐ ส่ง key ไปบันทึกใน version_name
    )
    
    logger.info(f"  Processing completed: successful={result.successful_updates}, errors={result.errors}")
    
    return result


def archive_file(file_path: str, success: bool):
    """Move processed file to archive folder"""
    try:
        base_folder = os.path.dirname(file_path)
        archive_folder = os.path.join(base_folder, "archive")
        os.makedirs(archive_folder, exist_ok=True)
        
        filename = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        status = "success" if success else "failed"
        
        name_without_ext, ext = os.path.splitext(filename)
        archived_filename = f"{name_without_ext}_{status}_{timestamp}{ext}"
        archived_path = os.path.join(archive_folder, archived_filename)
        
        os.rename(file_path, archived_path)
        logger.info(f"Archived file to: {archived_path}")
        
        metadata_path = file_path + ".meta.json"
        if os.path.exists(metadata_path):
            archived_metadata_path = archived_path + ".meta.json"
            os.rename(metadata_path, archived_metadata_path)
    except Exception as e:
        logger.error(f"Failed to archive file: {e}")


# =========================
# MAIN JOB FUNCTION
# =========================

def run_scheduled_price_upload() -> ScheduledUploadJobResult:
    """Main job function"""
    start_time = datetime.now()
    result = ScheduledUploadJobResult(start_time=start_time, end_time=start_time)
    
    try:
        logger.info("=" * 80)
        logger.info("🕐 Scheduled Price Upload Job Started")
        logger.info(f"   Triggered at: {start_time}")
        logger.info("=" * 80)
        
        logger.info(f"📁 Using folder path: {SCHEDULED_FOLDER}")
        
        if not os.path.exists(SCHEDULED_FOLDER):
            logger.warning(f"Folder not found: {SCHEDULED_FOLDER}")
            logger.info("Creating folder...")
            os.makedirs(SCHEDULED_FOLDER, exist_ok=True)
        
        today = datetime.now().date()
        logger.info(f"📅 Today's date: {today}")
        
        # Find Excel files
        excel_files = []
        for filename in os.listdir(SCHEDULED_FOLDER):
            if filename.endswith(('.xlsx', '.xls')) and not filename.startswith('~'):
                excel_files.append(filename)
        
        logger.info(f"📄 Found {len(excel_files)} Excel file(s)")
        result.files_found = len(excel_files)
        
        if not excel_files:
            logger.info("✅ No files to process")
            result.end_time = datetime.now()
            return result
        
        conn = get_mssql_conn()
        
        for filename in excel_files:
            try:
                file_path = os.path.join(SCHEDULED_FOLDER, filename)
                file_date = parse_filename_date(filename)
                
                if not file_date:
                    logger.warning(f"⚠️ Skipping file with invalid date: {filename}")
                    continue
                
                logger.info(f"📄 File: {filename}, Date: {file_date.date()}")
                
                if file_date.date() == today:
                    logger.info(f"✅ File date matches today, processing...")
                    
                    upload_result = process_scheduled_file(file_path, conn)
                    
                    result.files_processed += 1
                    result.total_items_uploaded += upload_result.successful_updates
                    
                    if upload_result.successful_updates > 0:
                        logger.info(f"✅ File processed: {upload_result.successful_updates} items uploaded")
                        if upload_result.errors > 0:
                            logger.warning(f"⚠️ {upload_result.errors} rows skipped")
                        archive_file(file_path, success=True)
                    else:
                        result.files_failed += 1
                        result.errors.extend(upload_result.error_details)
                        logger.error(f"❌ File failed: No items uploaded")
                        archive_file(file_path, success=False)
                else:
                    logger.info(f"⏳ File scheduled for {file_date.date()}, skipping")
            
            except Exception as e:
                error_msg = f"Failed to process {filename}: {e}"
                logger.error(error_msg, exc_info=True)
                result.errors.append(error_msg)
                result.files_failed += 1
        
        conn.close()
        result.end_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info("✅ Job Completed")
        logger.info(f"   Duration: {result.duration_seconds:.2f} seconds")
        logger.info(f"   Files Found: {result.files_found}")
        logger.info(f"   Files Processed: {result.files_processed}")
        logger.info(f"   Files Failed: {result.files_failed}")
        logger.info(f"   Total Items Uploaded: {result.total_items_uploaded}")
        logger.info("=" * 80)
        
        return result
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
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
