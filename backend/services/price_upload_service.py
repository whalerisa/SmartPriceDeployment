"""
Price Upload Service

This service handles price file uploads (CSV or Excel) and updates the Item_Price table.
It validates file format, required columns, and SKU existence before processing.

Features:
- Support for CSV and Excel (.xlsx, .xls) formats
- Column validation (SKU, SDM, R2, R1, W2, W1)
- SKU existence validation against Item_Master
- Upsert logic (update existing, insert new)
- Error handling with detailed summary
"""

import logging
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of a price upload operation"""
    total_rows: int
    successful_updates: int
    errors: int
    error_details: List[str]


class ValidationError(Exception):
    """Raised when file validation fails"""
    pass


class PriceUploadService:
    """
    Service for processing price file uploads and updating Item_Price table.
    
    Responsibilities:
    - Validate file format (CSV or Excel)
    - Validate required columns
    - Validate SKU existence in Item_Master
    - Upsert prices to Item_Price table
    - Track upload statistics
    """
    
    # Required columns in price file
    REQUIRED_COLUMNS = ["SDM", "R2", "R1", "W2", "W1"]
    
    # Accepted SKU column names (in order of preference)
    SKU_COLUMN_NAMES = ["SKU", "No_", "Item_No", "No", "ItemNo"]
    
    # Branch code for this upload (set via process_upload)
    _branch_code = None
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = [".csv", ".xlsx", ".xls"]
    
    def __init__(self, db_connection):
        """
        Initialize Price Upload Service.
        
        Args:
            db_connection: Database connection (pyodbc connection)
        """
        self.db_connection = db_connection
        logger.info("PriceUploadService initialized")
    
    def process_upload(self, file_path: str, branch_code: str, employee_info: dict) -> UploadResult:
        """
        Process price file (CSV or Excel) and update Item_Price table.
        
        Process:
        1. Validate file format and required columns
        2. Parse file into list of price records
        3. For each row:
           - Validate SKU exists in Item_Master
           - Skip rows with invalid SKU and log warning
           - Upsert to Item_Price table (update if exists, insert if not)
           - Set UpdatedAt timestamp
        4. Return summary with total_rows, successful_updates, errors
        
        Args:
            file_path: Path to uploaded file
        
        Returns:
            UploadResult with statistics (total_rows, successful, errors)
        
        Raises:
            ValidationError: When file format is invalid or required columns missing
        """
        self._branch_code = branch_code
        self._employee_info = employee_info  # ⭐ เก็บข้อมูล employee
        logger.info(f"Processing price upload: {file_path} for branch: {branch_code}")
        logger.info(f"Uploaded by: {employee_info.get('employee_id')} ({employee_info.get('name')})")
        
        # Validate file format
        self._validate_file_format(file_path)
        
        # Parse file
        try:
            price_data = self._parse_file(file_path)
        except Exception as e:
            logger.error(f"Failed to parse file: {str(e)}")
            raise ValidationError(f"Failed to parse file: {str(e)}")
        
        # Validate required columns
        self._validate_columns(price_data)
        
        # Process each row
        total_rows = len(price_data)
        successful_updates = 0
        errors = 0
        error_details = []
        
        # ⭐ สร้าง version log
        version_id = self._create_version_log(price_data)
        logger.info(f"Created version log: {version_id}")
        
        logger.info(f"Processing {total_rows} price records")
        
        for idx, row in enumerate(price_data, start=1):
            try:
                # Use the detected SKU column name
                sku = row.get(self._sku_column, "").strip()
                
                # Skip empty SKU
                if not sku:
                    error_msg = f"Row {idx}: Empty SKU"
                    logger.warning(error_msg)
                    error_details.append(error_msg)
                    errors += 1
                    continue
                
                # Validate SKU exists in Item_Master
                if not self._sku_exists(sku):
                    error_msg = f"Row {idx}: SKU '{sku}' not found in Item_Master"
                    logger.warning(error_msg)
                    error_details.append(error_msg)
                    errors += 1
                    continue
                
                # Extract price values
                # Try to get PackageSize from Excel, default to 1 if not present or invalid
                package_size = self._parse_decimal(row.get("PackageSize"))
                if package_size is None or package_size <= 0:
                    package_size = 1
                
                # Get AlternateName if present (optional field)
                alternate_name = row.get("AlternateName", "")
                if alternate_name and isinstance(alternate_name, str):
                    alternate_name = alternate_name.strip()
                else:
                    alternate_name = None
                
                price_record = {
                    "SKU": sku,
                    "BranchCode": self._branch_code,
                    "SDM": self._parse_decimal(row.get("SDM")),
                    "R2": self._parse_decimal(row.get("R2")),
                    "R1": self._parse_decimal(row.get("R1")),
                    "W2": self._parse_decimal(row.get("W2")),
                    "W1": self._parse_decimal(row.get("W1")),
                    "PackageSize": package_size,
                    "AlternateName": alternate_name
                }
                
                # Upsert price
                self._upsert_price(price_record, version_id, idx)  # ⭐ ส่ง version_id และ row index
                successful_updates += 1
                logger.debug(f"Successfully processed SKU: {sku}")
            
            except Exception as e:
                error_msg = f"Row {idx}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                error_details.append(error_msg)
                errors += 1
                # Continue processing remaining rows
        
        # Log summary
        logger.info(
            f"Price upload completed: "
            f"total_rows={total_rows}, "
            f"successful_updates={successful_updates}, "
            f"errors={errors}"
        )
        
        return UploadResult(
            total_rows=total_rows,
            successful_updates=successful_updates,
            errors=errors,
            error_details=error_details
        )
    
    def _validate_file_format(self, file_path: str):
        """
        Validate file format is CSV or Excel.
        
        Args:
            file_path: Path to file
        
        Raises:
            ValidationError: If file format is not supported
        """
        if not os.path.exists(file_path):
            raise ValidationError(f"File not found: {file_path}")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in self.SUPPORTED_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file format: {file_ext}. "
                f"Supported formats: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )
        
        logger.debug(f"File format validated: {file_ext}")
    
    def _parse_file(self, file_path: str) -> List[Dict]:
        """
        Parse CSV or Excel file into list of dictionaries.
        
        Args:
            file_path: Path to file
        
        Returns:
            List of dictionaries, one per row
        
        Raises:
            Exception: If file cannot be parsed
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == ".csv":
                df = pd.read_csv(file_path)
            elif file_ext in [".xlsx", ".xls"]:
                df = pd.read_excel(file_path, engine="openpyxl" if file_ext == ".xlsx" else None)
            else:
                raise ValidationError(f"Unsupported file extension: {file_ext}")
            
            # Convert DataFrame to list of dictionaries
            records = df.to_dict("records")
            logger.debug(f"Parsed {len(records)} records from file")
            
            return records
        
        except Exception as e:
            logger.error(f"Error parsing file: {str(e)}")
            raise
    
    def _validate_columns(self, price_data: List[Dict]):
        """
        Validate required columns exist in parsed data.
        
        Args:
            price_data: List of price records
        
        Raises:
            ValidationError: If required columns are missing
        """
        if not price_data:
            raise ValidationError("File is empty")
        
        # Get columns from first row
        actual_columns = set(price_data[0].keys())
        required_columns = set(self.REQUIRED_COLUMNS)
        
        # Check for SKU column (accept multiple variations)
        sku_column = None
        for col_name in self.SKU_COLUMN_NAMES:
            if col_name in actual_columns:
                sku_column = col_name
                break
        
        if not sku_column:
            raise ValidationError(
                f"Missing SKU column. Expected one of: {', '.join(self.SKU_COLUMN_NAMES)}"
            )
        
        # Store the SKU column name for later use
        self._sku_column = sku_column
        logger.debug(f"Using SKU column: {sku_column}")
        
        # Check other required columns
        missing_columns = required_columns - actual_columns
        
        if missing_columns:
            raise ValidationError(
                f"Missing required columns: {', '.join(sorted(missing_columns))}"
            )
        
        logger.debug("All required columns present")
    
    def _sku_exists(self, sku: str) -> bool:
        """
        Check if SKU exists in Item_Master table.
        
        Args:
            sku: SKU to check
        
        Returns:
            True if SKU exists, False otherwise
        """
        cursor = self.db_connection.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM Item_Master WHERE SKU = ?",
                (sku,)
            )
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            cursor.close()
    
    def _parse_decimal(self, value) -> Optional[float]:
        """
        Parse decimal value from various input types.
        
        Args:
            value: Value to parse (can be string, number, or None)
        
        Returns:
            Float value or None if invalid
        """
        if pd.isna(value) or value is None or value == "":
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid decimal value: {value}")
            return None
    
    def _create_version_log(self, price_data: List[Dict]) -> int:
        """
        สร้าง version log ใน Item_Update_Version
        
        Returns:
            version_id ที่สร้างขึ้น
        """
        cursor = self.db_connection.cursor()
        try:
            # สร้าง version_name: UPLOAD_YYYYMMDD_HHMMSS
            now = datetime.now()
            version_name = f"UPLOAD_{now.strftime('%Y%m%d_%H%M%S')}"
            
            # หา update_type จาก SKU (ตัวอักษรแรก)
            categories = set()
            for row in price_data:
                sku = row.get(self._sku_column, "").strip()
                if sku and len(sku) > 0:
                    category = sku[0].upper()
                    if category in ['G', 'A', 'Y', 'S', 'C', 'E']:
                        categories.add(category)
            
            # ถ้ามีหลาย category ให้ใช้ MIXED, ถ้ามี 1 category ให้ใช้ category นั้น
            if len(categories) > 1:
                update_type = "MIXED"
            elif len(categories) == 1:
                update_type = list(categories)[0]
            else:
                update_type = "MIXED"  # default
            
            # ดึงข้อมูล employee
            uploaded_by = self._employee_info.get('employee_id', 'system')
            job_title = self._employee_info.get('role', 'MANAGER')
            
            # ⭐ หา version_id ถัดไป (MAX + 1)
            cursor.execute("SELECT ISNULL(MAX(version_id), 0) + 1 FROM Item_Update_Version")
            version_id = int(cursor.fetchone()[0])
            
            # ⭐ ใช้เวลาจาก Python แทน GETDATE()
            uploaded_at = datetime.now()
            
            # Insert version log พร้อม version_id
            cursor.execute("""
                INSERT INTO Item_Update_Version (
                    version_id, version_name, update_type, uploaded_by, job_title, 
                    uploaded_at, status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (version_id, version_name, update_type, uploaded_by, job_title, uploaded_at))
            
            self.db_connection.commit()
            
            logger.info(f"Created version log: {version_id} ({version_name}), type: {update_type}")
            return version_id
            
        except Exception as e:
            logger.error(f"Failed to create version log: {e}")
            self.db_connection.rollback()
            raise
        finally:
            cursor.close()
    
    def _upsert_price(self, price_data: Dict, version_id: int, row_index: int):
        """
        Insert or update price in Item_Price table และบันทึก detail log
        
        Logic:
        - ดึงราคาเก่าจาก Item_Price (ถ้ามี)
        - Check if SKU exists in Item_Price
        - If exists: UPDATE all price fields and UpdatedAt
        - If not exists: INSERT with UpdatedAt = current timestamp
        - บันทึก detail log ลง Item_Update_Version_Detail
        
        Args:
            price_data: Dictionary with SKU and price fields
            version_id: ID ของ version log
            row_index: ลำดับแถวในไฟล์
        
        Raises:
            Exception: If database operation fails
        """
        sku = price_data["SKU"]
        
        cursor = self.db_connection.cursor()
        try:
            branch_code = price_data["BranchCode"]
            
            # ⭐ ดึงราคาเก่าก่อน update
            cursor.execute("""
                SELECT R1, R2, W1, W2, AlternateName
                FROM Item_Price
                WHERE SKU = ? AND BranchCode = ?
            """, (sku, branch_code))
            
            old_row = cursor.fetchone()
            if old_row:
                old_R1, old_R2, old_W1, old_W2, old_alternate_name = old_row
                exists = True
            else:
                old_R1 = old_R2 = old_W1 = old_W2 = old_alternate_name = None
                exists = False
            
            # ราคาใหม่
            new_R1 = price_data["R1"]
            new_R2 = price_data["R2"]
            new_W1 = price_data["W1"]
            new_W2 = price_data["W2"]
            new_alternate_name = price_data["AlternateName"]
            
            # ⭐ คำนวณ change flags
            change_price_flag = 0
            if exists:
                if (old_R1 != new_R1 or old_R2 != new_R2 or 
                    old_W1 != new_W1 or old_W2 != new_W2):
                    change_price_flag = 1
            else:
                # SKU ใหม่ถือว่ามีการเปลี่ยนแปลงราคา
                change_price_flag = 1
            
            change_altname_flag = 0
            if exists:
                if old_alternate_name != new_alternate_name:
                    change_altname_flag = 1
            else:
                # SKU ใหม่ถ้ามี alternate name ถือว่ามีการเปลี่ยนแปลง
                if new_alternate_name:
                    change_altname_flag = 1
            
            # Update หรือ Insert ราคา
            if exists:
                # Update existing price
                cursor.execute(
                    """
                    UPDATE Item_Price
                    SET SDM = ?,
                        R2 = ?,
                        R1 = ?,
                        W2 = ?,
                        W1 = ?,
                        PackageSize = ?,
                        AlternateName = ?,
                        UpdatedAt = GETDATE()
                    WHERE SKU = ? AND BranchCode = ?
                    """,
                    (
                        price_data["SDM"],
                        price_data["R2"],
                        price_data["R1"],
                        price_data["W2"],
                        price_data["W1"],
                        price_data["PackageSize"],
                        price_data["AlternateName"],
                        sku,
                        branch_code
                    )
                )
                logger.debug(f"Updated price for SKU: {sku}, Branch: {branch_code}")
            
            else:
                # Insert new price with UpdatedAt timestamp
                cursor.execute(
                    """
                    INSERT INTO Item_Price (
                        SKU, BranchCode, SDM, R2, R1, W2, W1, PackageSize, AlternateName, UpdatedAt
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                    """,
                    (
                        sku,
                        branch_code,
                        price_data["SDM"],
                        price_data["R2"],
                        price_data["R1"],
                        price_data["W2"],
                        price_data["W1"],
                        price_data["PackageSize"],
                        price_data["AlternateName"]
                    )
                )
                logger.debug(f"Inserted new price for SKU: {sku}, Branch: {branch_code}")
            
            # ⭐ บันทึก detail log
            # หา id ถัดไป (MAX + 1)
            cursor.execute("SELECT ISNULL(MAX(id), 0) + 1 FROM Item_Update_Version_Detail")
            detail_id = int(cursor.fetchone()[0])
            
            cursor.execute("""
                INSERT INTO Item_Update_Version_Detail (
                    id, version_id, sku, new_no2, 
                    new_R1, new_R2, new_W1, new_W2,
                    old_R1, old_R2, old_W1, old_W2,
                    new_alternate_name, old_alternate_name,
                    change_price_flag, change_altname_flag
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                detail_id,
                version_id,
                sku,
                new_alternate_name,  # new_no2 (ชื่อสินค้า)
                new_R1, new_R2, new_W1, new_W2,
                old_R1, old_R2, old_W1, old_W2,
                new_alternate_name,
                old_alternate_name,
                change_price_flag,
                change_altname_flag
            ))
            
            self.db_connection.commit()
        
        finally:
            cursor.close()
