"""
Item Master Cache Refresh Job - Standalone Version for Airflow
ดึงข้อมูล Item Master จาก D365 มาลง database

This is a standalone version that doesn't require external imports.
All dependencies are included in this file.

Configuration:
--------------
The script uses hardcoded default values from production environment:
- ITEM_API_URL: http://192.192.0.37:8280/sp683-item/1.0.0
- ITEM_API_KEY: (production key included)
- MSSQL_SERVER: 192.192.0.220,50681
- MSSQL_DATABASE: SP681
- MSSQL_USERNAME: sp681_user
- MSSQL_PASSWORD: (production password included)

You can override these defaults using environment variables:
- ITEM_API_URL
- ITEM_API_KEY
- MSSQL_SERVER
- MSSQL_DATABASE
- MSSQL_USERNAME
- MSSQL_PASSWORD
- MSSQL_DRIVER (optional, defaults to "{ODBC Driver 17 for SQL Server}")

Usage:
------
1. Direct execution:
   python item_master_cache_refresh_standalone.py

2. In Airflow DAG:
   from item_master_cache_refresh_standalone import run_item_master_cache_refresh
   
   def task_function():
       result = run_item_master_cache_refresh()
       if result.errors:
           raise Exception(f"Job failed with {len(result.errors)} errors")
       return result

3. With custom configuration:
   import os
   os.environ['ITEM_API_URL'] = 'https://custom-api.example.com'
   os.environ['ITEM_API_KEY'] = 'custom-key'
   result = run_item_master_cache_refresh()

Requirements:
-------------
- pyodbc
- requests

Install with:
    pip install pyodbc requests
"""

import os
import time
import logging
import pyodbc
import requests
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from logging.handlers import TimedRotatingFileHandler
from requests.exceptions import RequestException, Timeout


# =========================
# LOGGING SETUP
# =========================

LOG_FILE = "logs/item_master_cache_refresh.log"
LOG_LEVEL = "INFO"
LOG_BACKUP_COUNT = 30


def setup_logger():
    """Setup logger with file and console handlers"""
    logger = logging.getLogger('item_master_cache')
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

# Default values from production environment
# Override these using environment variables if needed
MSSQL_CONFIG = {
    "server": os.getenv("MSSQL_SERVER", "192.192.0.220,50681"),
    "database": os.getenv("MSSQL_DATABASE", "SP681"),
    "username": os.getenv("MSSQL_USERNAME", "sp681_user"),
    "password": os.getenv("MSSQL_PASSWORD", "Tng#kmitl2"),
    "driver": os.getenv("MSSQL_DRIVER", "{ODBC Driver 17 for SQL Server}"),
}

# Default API configuration from production environment
# Override these using environment variables if needed
DEFAULT_ITEM_API_URL = "http://192.192.0.37:8280/silver_item_dx/1.0.0"
DEFAULT_ITEM_API_KEY = "eyJ4NXQjUzI1NiI6Ik16QXpNVEZqT0RRMU1ETmpPVFUxWkRBNE5HUTVNRGt6WXpFM01XSTRNbVJsWkdVM1l6WmpZams0WkdSa00yUmhNbUl3TWpBeFl6SmxNR0pqTmpkbU53PT0iLCJraWQiOiJnYXRld2F5X2NlcnRpZmljYXRlX2FsaWFzIiwidHlwIjoiSldUIiwiYWxnIjoiUlMyNTYifQ==.eyJzdWIiOiJhZG1pbkBjYXJib24uc3VwZXIiLCJhcHBsaWNhdGlvbiI6eyJpZCI6MzQsInV1aWQiOiIzNTU5OGQ4NS1jM2VlLTQ3ODktOGViMC03MGM5YzEwNGJiMmYifSwiaXNzIjoiaHR0cHM6XC9cL2xvY2FsaG9zdDo5NDQzXC9vYXV0aDJcL3Rva2VuIiwia2V5dHlwZSI6IlBST0RVQ1RJT04iLCJ0b2tlbl90eXBlIjoiYXBpS2V5IiwiaWF0IjoxNzczNDg5MjIwLCJqdGkiOiJiZGI0NWM0MC1mNmE4LTRlNDctYmU5MS00ZTk1MmVlMWMxMjcifQ==.X95g4oBEvoKGfym2H2VCSe-iFtJGsjiDCuBW6ObzUGJr_G3aZWMFQXM70gzR9y6vQwAQuy7kjij1Ahe1239MGgfKRk73Hr_4T55kIH3IiZZcACk61M1YJi15Z5thzaxWn8Lhh2gQ_h8pjXfA0zVoivUwva5fiQz82yCLFhZgXSzo_aSufuTKtSbcGCIX8upUGHSz_3cSegf_xP6EhdASxfY-Lbq_fVViQwHMnjE320R_ZnYSi_RXIG1Zc8eDCpS81egjBZ7JiAcQyI7QOsZq8cocmis4TKumYBQ9HW6qUqgRiIoBH_Rfj1TaBSIqU0cQUQkgK6U2FUTixHBbbWBC3A=="


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
# BC API CLIENT
# =========================

class AuthenticationError(Exception):
    """Raised when API returns 401 or 403"""
    pass


class ClientError(Exception):
    """Raised when API returns 4xx (except 401/403)"""
    pass


class ServerError(Exception):
    """Raised when API returns 5xx after retries"""
    pass


class NetworkError(Exception):
    """Raised when network request fails after retries"""
    pass


class BCAPIClient:
    """
    Client for Business Central Item APIs with API Key authentication.
    
    Features:
    - API Key authentication (Authorization header)
    - Retry logic with exponential backoff
    - Configurable timeouts
    - OData pagination support
    """
    
    def __init__(
        self,
        item_api_url: Optional[str] = None,
        item_api_key: Optional[str] = None,
        max_retries: int = 3,
        item_timeout: int = 30
    ):
        """
        Initialize BC API Client with configuration.
        
        Args:
            item_api_url: Base URL for Item API (defaults to env ITEM_API_URL or hardcoded default)
            item_api_key: API key for Item API (defaults to env ITEM_API_KEY or hardcoded default)
            max_retries: Maximum number of retries for failed requests (default: 3)
            item_timeout: Timeout in seconds for Item API requests (default: 30)
        """
        # Load from environment if not provided, fallback to hardcoded defaults
        self.item_api_url = (
            item_api_url or 
            os.getenv("ITEM_API_URL", "").strip().strip('"') or 
            DEFAULT_ITEM_API_URL
        )
        self.item_api_key = (
            item_api_key or 
            os.getenv("ITEM_API_KEY", "").strip() or 
            DEFAULT_ITEM_API_KEY
        )
        
        # Validate configuration
        if not self.item_api_url:
            raise ValueError("ITEM_API_URL not configured")
        if not self.item_api_key:
            raise ValueError("ITEM_API_KEY not configured")
        
        self.max_retries = max_retries
        self.item_timeout = item_timeout
        
        logger.info(f"BC API Client initialized with Item API: {self.item_api_url}")
    
    def fetch_items(self, page: int = 1, size: int = 100) -> List[Dict]:
        """
        Fetch items from SP683 Item API with pagination.
        
        Args:
            page: Page number (starts from 1)
            size: Number of records per page (max 100)
        
        Returns:
            List of item dictionaries with BC API fields
        
        Raises:
            AuthenticationError: When API key is invalid
            ClientError: When API returns 4xx error
            ServerError: When API returns 5xx error after retries
            NetworkError: When network request fails after retries
        """
        # Try empty payload first - API might not support pagination
        payload = {}
        
        url = self.item_api_url
        response_data = self._make_request_post(
            url=url,
            api_key=self.item_api_key,
            payload=payload,
            timeout=self.item_timeout
        )
        
        # Extract items from response
        if isinstance(response_data, dict):
            # Try to get 'data' field first, fallback to 'value', then the dict itself
            items = response_data.get("data") or response_data.get("value") or response_data
            if isinstance(items, list):
                return items
            return []
        elif isinstance(response_data, list):
            return response_data
        else:
            logger.warning(f"Unexpected response format: {type(response_data)}")
            return []
    
    def _make_request_post(
        self,
        url: str,
        api_key: str,
        payload: Optional[Dict] = None,
        timeout: int = 30,
        retry_count: int = 0
    ) -> Dict:
        """
        Make HTTP POST request with retry logic and error handling.
        
        Args:
            url: API endpoint URL
            api_key: API key for authentication
            payload: JSON payload
            timeout: Request timeout in seconds
            retry_count: Current retry attempt (internal use)
        
        Returns:
            Parsed JSON response
        
        Raises:
            AuthenticationError: When API returns 401 or 403
            ClientError: When API returns other 4xx errors
            ServerError: When API returns 5xx after retries
            NetworkError: When network request fails after retries
        """
        headers = {
            "apikey": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        try:
            logger.debug(f"Making POST request to {url} with payload {payload}")
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout
            )
            
            return self._handle_response(response, url, api_key, payload, timeout, retry_count)
        
        except (Timeout, RequestException) as e:
            return self._handle_request_exception(e, url, api_key, payload, timeout, retry_count)
        
        except ValueError as e:
            # JSON parsing error
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise ClientError(f"Invalid JSON response: {str(e)}") from e
    
    def _handle_response(
        self,
        response,
        url: str,
        api_key: str,
        payload: Optional[Dict],
        timeout: int,
        retry_count: int
    ) -> Dict:
        """Handle HTTP response with appropriate error handling and retries."""
        # Handle different status codes
        if response.status_code == 200:
            return response.json()
        
        # Authentication errors - no retry
        elif response.status_code in (401, 403):
            logger.error(f"Authentication failed: {response.status_code} - {response.text}")
            raise AuthenticationError(
                f"Authentication failed with status {response.status_code}: {response.text}"
            )
        
        # Other client errors - no retry
        elif 400 <= response.status_code < 500:
            logger.error(f"Client error: {response.status_code} - {response.text}")
            raise ClientError(
                f"Client error {response.status_code}: {response.text}"
            )
        
        # Server errors - retry
        elif response.status_code >= 500:
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Server error {response.status_code}, retrying in {wait_time}s "
                    f"(attempt {retry_count + 1}/{self.max_retries})"
                )
                time.sleep(wait_time)
                return self._make_request_post(url, api_key, payload, timeout, retry_count + 1)
            else:
                logger.error(
                    f"Server error after {self.max_retries} retries: "
                    f"{response.status_code} - {response.text}"
                )
                raise ServerError(
                    f"Server error {response.status_code} after {self.max_retries} retries: "
                    f"{response.text}"
                )
        
        else:
            logger.error(f"Unexpected status code: {response.status_code}")
            raise ClientError(f"Unexpected status code: {response.status_code}")
    
    def _handle_request_exception(
        self,
        exception,
        url: str,
        api_key: str,
        payload: Optional[Dict],
        timeout: int,
        retry_count: int
    ):
        """Handle request exceptions (timeout, network errors) with retries."""
        if isinstance(exception, Timeout):
            error_type = "Request timeout"
        else:
            error_type = f"Network error: {str(exception)}"
        
        if retry_count < self.max_retries:
            wait_time = 2 ** retry_count
            logger.warning(
                f"{error_type}, retrying in {wait_time}s "
                f"(attempt {retry_count + 1}/{self.max_retries})"
            )
            time.sleep(wait_time)
            return self._make_request_post(url, api_key, payload, timeout, retry_count + 1)
        else:
            logger.error(f"{error_type} after {self.max_retries} retries")
            raise NetworkError(
                f"{error_type} after {self.max_retries} retries"
            ) from exception


# =========================
# DATA MODELS
# =========================

@dataclass
class ItemMasterRecord:
    """Item Master record structure - only columns that exist in Item_Master table"""
    SKU: str
    No_2: Optional[str] = None
    Description: Optional[str] = None
    Base_Unit_of_Measure: Optional[str] = None
    Product_Group: Optional[str] = None
    Product_Sub_Group: Optional[str] = None
    Variant_Mandatory: Optional[int] = None
    Product_Weight: Optional[float] = None
    Blocked: Optional[int] = None
    Inventory_Posting_Group: Optional[str] = None
    Sales_Blocked: Optional[int] = None
    Purchasing_Blocked: Optional[int] = None


@dataclass
class ItemMasterJobResult:
    """Result of item master cache refresh job"""
    start_time: datetime
    end_time: datetime
    items_processed: int = 0
    items_inserted: int = 0
    items_updated: int = 0
    items_failed: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration_seconds(self) -> float:
        """Calculate job duration in seconds"""
        return (self.end_time - self.start_time).total_seconds()


# =========================
# BUSINESS LOGIC
# =========================

def parse_item_record(item_data: Dict) -> Optional[ItemMasterRecord]:
    """
    Parse item data from BC API response to ItemMasterRecord
    Only maps fields that exist in Item_Master table.
    Price fields (R1, R2, W1, W2) and AlternateName are stored in Item_Price table.
    
    Args:
        item_data: Item data from BC API
    
    Returns:
        ItemMasterRecord or None if parsing fails
    """
    try:
        # Extract required fields - NEW API field name: Item_No
        sku = item_data.get("Item_No")
        if not sku:
            logger.warning(f"Item missing Item_No: {item_data}")
            return None
        
        # Extract only fields that exist in Item_Master table
        record = ItemMasterRecord(
            SKU=sku,
            No_2=item_data.get("Item_No_2"),
            Description=item_data.get("Description"),
            Base_Unit_of_Measure=item_data.get("Base_Unit_Of_Measure"),
            Product_Group=item_data.get("Product_Group_No"),
            Product_Sub_Group=item_data.get("Product_Subgroup_No"),
            Variant_Mandatory=item_data.get("Variant_Mandatory"),
            Product_Weight=item_data.get("Product_Weight"),
            Blocked=item_data.get("Blocked"),
            Inventory_Posting_Group=item_data.get("Inventory_Posting_Group"),
            Sales_Blocked=item_data.get("Sales_Blocked"),
            Purchasing_Blocked=item_data.get("Purchasing_Blocked")
        )
        
        return record
        
    except Exception as e:
        logger.error(f"Failed to parse item record: {e}", exc_info=True)
        return None


def upsert_item_batch(items: List[ItemMasterRecord], conn: pyodbc.Connection) -> tuple:
    """
    Upsert items into Item_Master table (insert or update) using batch operations with executemany

    Args:
        items: List of ItemMasterRecord to upsert
        conn: Database connection

    Returns:
        Tuple of (inserted_count, updated_count)
    """
    if not items:
        return 0, 0

    cursor = conn.cursor()
    inserted = 0
    updated = 0

    try:
        # Get all existing SKUs in one query
        logger.info("   Fetching existing SKUs from database...")
        cursor.execute("SELECT SKU FROM Item_Master")
        existing_skus = set(row[0] for row in cursor.fetchall())
        logger.info(f"   Found {len(existing_skus)} existing items in database")

        # Separate items into insert and update lists
        insert_items = []
        update_items = []

        for item in items:
            if item.SKU in existing_skus:
                update_items.append(item)
            else:
                insert_items.append(item)

        # Batch insert new items using executemany
        if insert_items:
            logger.info(f"   Inserting {len(insert_items)} new items...")
            
            insert_sql = """
                INSERT INTO Item_Master (
                    SKU, No_2, Description, Base_Unit_of_Measure,
                    Product_Group, Product_Sub_Group, Variant_Mandatory,
                    Product_Weight, blocked, Inventory_Posting_Group,
                    Sales_Blocked, Purchasing_Blocked
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            insert_params = [
                (
                    item.SKU,
                    item.No_2,
                    item.Description,
                    item.Base_Unit_of_Measure,
                    item.Product_Group,
                    item.Product_Sub_Group,
                    item.Variant_Mandatory,
                    item.Product_Weight,
                    item.Blocked,
                    item.Inventory_Posting_Group,
                    item.Sales_Blocked,
                    item.Purchasing_Blocked
                )
                for item in insert_items
            ]
            
            try:
                cursor.fast_executemany = True
                cursor.executemany(insert_sql, insert_params)
                conn.commit()
                inserted = len(insert_items)
                logger.info(f"   ✅ Inserted {inserted} items using executemany")
            except Exception as e:
                logger.error(f"   ❌ Batch insert failed: {e}")
                logger.info("   🔄 Falling back to row-by-row insert...")
                conn.rollback()
                cursor.fast_executemany = False
                
                for param in insert_params:
                    try:
                        cursor.execute(insert_sql, param)
                        inserted += 1
                    except Exception as row_e:
                        logger.error(f"   ❌ Failed to insert SKU {param[0]}: {row_e}")
                
                conn.commit()

        # Batch update existing items using executemany
        if update_items:
            logger.info(f"   Updating {len(update_items)} existing items...")
            
            update_sql = """
                UPDATE Item_Master
                SET
                    No_2 = ?,
                    Description = ?,
                    Base_Unit_of_Measure = ?,
                    Product_Group = ?,
                    Product_Sub_Group = ?,
                    Variant_Mandatory = ?,
                    Product_Weight = ?,
                    blocked = ?,
                    Inventory_Posting_Group = ?,
                    Sales_Blocked = ?,
                    Purchasing_Blocked = ?
                WHERE SKU = ?
            """
            
            # แบ่งเป็น batch เล็กๆ เพื่อแสดง progress
            batch_size = 2000
            total_updated = 0
            
            for batch_idx in range(0, len(update_items), batch_size):
                batch = update_items[batch_idx:batch_idx + batch_size]
                
                update_params = [
                    (
                        item.No_2,
                        item.Description,
                        item.Base_Unit_of_Measure,
                        item.Product_Group,
                        item.Product_Sub_Group,
                        item.Variant_Mandatory,
                        item.Product_Weight,
                        item.Blocked,
                        item.Inventory_Posting_Group,
                        item.Sales_Blocked,
                        item.Purchasing_Blocked,
                        item.SKU
                    )
                    for item in batch
                ]
                
                try:
                    cursor.fast_executemany = True
                    cursor.executemany(update_sql, update_params)
                    conn.commit()
                    total_updated += len(batch)
                    logger.info(f"   ✅ Progress: {total_updated}/{len(update_items)} items updated")
                except Exception as e:
                    logger.error(f"   ❌ Batch update failed: {e}")
                    logger.info("   🔄 Falling back to row-by-row update for this batch...")
                    conn.rollback()
                    cursor.fast_executemany = False
                    
                    for param in update_params:
                        try:
                            cursor.execute(update_sql, param)
                            total_updated += 1
                        except Exception as row_e:
                            logger.error(f"   ❌ Failed to update SKU {param[11]}: {row_e}")
                    
                    conn.commit()
                    logger.info(f"   Progress: {total_updated}/{len(update_items)} items updated")
            
            updated = total_updated

        logger.info(f"✓ Upserted items: {inserted} inserted, {updated} updated")

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to upsert items: {e}", exc_info=True)
        raise
    finally:
        cursor.close()

    return inserted, updated

    return inserted, updated



# =========================
# MAIN JOB FUNCTION
# =========================

def run_item_master_cache_refresh() -> ItemMasterJobResult:
    """
    Main job function: ดึงข้อมูล Item Master จาก D365 มาลง database
    
    Returns:
        ItemMasterJobResult with job execution details
    """
    start_time = datetime.now()
    result = ItemMasterJobResult(start_time=start_time, end_time=start_time)
    
    try:
        logger.info("=" * 80)
        logger.info("🕐 Item Master Cache Refresh Started")
        logger.info(f"   Triggered at: {start_time}")
        logger.info("=" * 80)
        
        # Initialize BC API client
        try:
            bc_client = BCAPIClient()
        except ValueError as e:
            error_msg = f"Failed to initialize BC API client: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
            result.end_time = datetime.now()
            return result
        
        # Fetch items from BC API
        logger.info("📥 Fetching items from D365...")
        try:
            items_data = bc_client.fetch_items(page=1, size=100)
            logger.info(f"   Fetched {len(items_data)} items from D365")
        except Exception as e:
            error_msg = f"Failed to fetch items from BC API: {e}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            result.end_time = datetime.now()
            return result
        
        # Parse items
        logger.info("🔄 Parsing items...")
        parsed_items = []
        for idx, item_data in enumerate(items_data, 1):
            parsed_item = parse_item_record(item_data)
            if parsed_item:
                parsed_items.append(parsed_item)
                result.items_processed += 1
            else:
                result.items_failed += 1
            
            # Log progress every 1000 items
            if idx % 1000 == 0:
                logger.info(f"   Progress: {idx}/{len(items_data)} items parsed")
        
        logger.info(f"   ✓ Parsed {result.items_processed} items, {result.items_failed} failed")
        
        # Upsert items to database
        if parsed_items:
            logger.info("💾 Upserting items to database...")
            try:
                conn = get_mssql_conn()
                inserted, updated = upsert_item_batch(parsed_items, conn)
                conn.close()
                
                result.items_inserted = inserted
                result.items_updated = updated
                logger.info(f"   Inserted: {inserted}, Updated: {updated}")
                
            except Exception as e:
                error_msg = f"Failed to upsert items to database: {e}"
                logger.error(error_msg, exc_info=True)
                result.errors.append(error_msg)
        
        result.end_time = datetime.now()
        
        logger.info("=" * 80)
        logger.info("✅ Item Master Cache Refresh Completed")
        logger.info(f"   Duration: {result.duration_seconds:.2f} seconds")
        logger.info(f"   Processed: {result.items_processed}")
        logger.info(f"   Inserted: {result.items_inserted}")
        logger.info(f"   Updated: {result.items_updated}")
        logger.info(f"   Failed: {result.items_failed}")
        if result.errors:
            logger.info(f"   Errors: {len(result.errors)}")
            for error in result.errors:
                logger.error(f"     - {error}")
        logger.info("=" * 80)
        
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in item master cache refresh: {e}", exc_info=True)
        result.errors.append(str(e))
        result.end_time = datetime.now()
        return result


# =========================
# CLI ENTRY POINT
# =========================

if __name__ == "__main__":
    """Run the job when executed as a script"""
    print("Starting Item Master Cache Refresh Job...")
    result = run_item_master_cache_refresh()
    
    # Print summary
    print("\n" + "=" * 80)
    print("JOB SUMMARY")
    print("=" * 80)
    print(f"Duration: {result.duration_seconds:.2f} seconds")
    print(f"Items Processed: {result.items_processed}")
    print(f"Items Inserted: {result.items_inserted}")
    print(f"Items Updated: {result.items_updated}")
    print(f"Items Failed: {result.items_failed}")
    
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")
        exit(1)
    else:
        print("\n✅ Job completed successfully!")
        exit(0)
