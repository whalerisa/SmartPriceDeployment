"""
Business Central Item API Client

This client handles communication with BC Item APIs using API Key authentication.
Separate from bc_client.py which uses Basic Auth for different BC APIs.

Supports:
- SP683 Item API (for Item Master data)
- SP683 Item Ledger Entries API (for Inventory data)
"""

import os
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

import requests
from requests.exceptions import RequestException, Timeout


# Configure logging
logger = logging.getLogger(__name__)


# Custom exceptions
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


@dataclass
class BCAPIConfig:
    """Configuration for BC Item APIs"""
    item_api_url: str
    item_api_key: str
    itemledger_api_url: str
    itemledger_api_key: str


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
        itemledger_api_url: Optional[str] = None,
        itemledger_api_key: Optional[str] = None,
        max_retries: int = 3,
        item_timeout: int = 30,
        ledger_timeout: int = 5
    ):
        """
        Initialize BC API Client with configuration.
        
        Args:
            item_api_url: Base URL for Item API (defaults to env ITEM_API_URL)
            item_api_key: API key for Item API (defaults to env ITEM_API_KEY)
            itemledger_api_url: Base URL for Item Ledger API (defaults to env ITEMLEDGER_API_URL)
            itemledger_api_key: API key for Item Ledger API (defaults to env ITEMLEDGER_API_KEY)
            max_retries: Maximum number of retries for failed requests (default: 3)
            item_timeout: Timeout in seconds for Item API requests (default: 30)
            ledger_timeout: Timeout in seconds for Ledger API requests (default: 5)
        """
        # Load from environment if not provided
        self.item_api_url = item_api_url or os.getenv("ITEM_API_URL", "").strip().strip('"')
        self.item_api_key = item_api_key or os.getenv("ITEM_API_KEY", "").strip()
        self.itemledger_api_url = itemledger_api_url or os.getenv("ITEMLEDGER_API_URL", "").strip().strip('"')
        self.itemledger_api_key = itemledger_api_key or os.getenv("ITEMLEDGER_API_KEY", "").strip()
        
        # Validate configuration
        if not self.item_api_url:
            raise ValueError("ITEM_API_URL not configured")
        if not self.item_api_key:
            raise ValueError("ITEM_API_KEY not configured")
        if not self.itemledger_api_url:
            raise ValueError("ITEMLEDGER_API_URL not configured")
        if not self.itemledger_api_key:
            raise ValueError("ITEMLEDGER_API_KEY not configured")
        
        self.max_retries = max_retries
        self.item_timeout = item_timeout
        self.ledger_timeout = ledger_timeout
        
        logger.info(f"BC API Client initialized with Item API: {self.item_api_url}")
        logger.info(f"BC API Client initialized with Ledger API: {self.itemledger_api_url}")
    
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
    
    def fetch_inventory(self, item_no: str, branch_code: str = None) -> List[Dict]:
        """
        Fetch inventory ledger entries for specific item using POST.
        
        Args:
            item_no: Item number (SKU) to query
            branch_code: Optional branch code to filter by
        
        Returns:
            List of ledger entries with Item_No_, Quantity, Location_Code
        
        Raises:
            AuthenticationError: When API key is invalid
            ClientError: When API returns 4xx error
            ServerError: When API returns 5xx error after retries
            NetworkError: When network request fails after retries
        """
      
        payload = {
            
            "Item_No": {"$eq": item_no}
        }
        
        # เพิ่ม filter สาขาถ้ามี (ใช้ Location_Code แทน Branch_Code)
        if branch_code:
            payload["Location_Code"] = {"$eq": branch_code}
        
        url = self.itemledger_api_url
        response_data = self._make_request_post(
            url=url,
            api_key=self.itemledger_api_key,
            payload=payload,
            timeout=self.ledger_timeout
        )
        
        # Extract entries from response (check both "data" and "value" keys)
        if isinstance(response_data, dict):
            if "data" in response_data:
                return response_data["data"] if response_data["data"] else []
            elif "value" in response_data:
                return response_data["value"]
        elif isinstance(response_data, list):
            return response_data
        
        logger.warning(f"Unexpected response format: {type(response_data)}")
        return []
    
    def _make_request(
        self,
        url: str,
        api_key: str,
        params: Optional[Dict] = None,
        timeout: int = 30,
        retry_count: int = 0
    ) -> Dict:
        """
        Make HTTP GET request with retry logic and error handling.
        
        Args:
            url: API endpoint URL
            api_key: API key for authentication
            params: Query parameters
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
            logger.debug(f"Making GET request to {url} with params {params}")
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=timeout
            )
            
            return self._handle_response(response, url, api_key, params, timeout, retry_count)
        
        except (Timeout, RequestException) as e:
            return self._handle_request_exception(e, url, api_key, params, timeout, retry_count)
        
        except ValueError as e:
            # JSON parsing error
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise ClientError(f"Invalid JSON response: {str(e)}") from e
    
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
            
            return self._handle_response(response, url, api_key, payload, timeout, retry_count, method="POST")
        
        except (Timeout, RequestException) as e:
            return self._handle_request_exception(e, url, api_key, payload, timeout, retry_count, method="POST")
        
        except ValueError as e:
            # JSON parsing error
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise ClientError(f"Invalid JSON response: {str(e)}") from e
    
    def _handle_response(
        self,
        response,
        url: str,
        api_key: str,
        params_or_payload: Optional[Dict],
        timeout: int,
        retry_count: int,
        method: str = "GET"
    ) -> Dict:
        """Handle HTTP response with appropriate error handling and retries."""
        # Handle different status codes
        if response.status_code == 200:
            try:
                # ⭐ Log response headers เพื่อ debug
                logger.debug(f"Response headers: {response.headers}")
                logger.debug(f"Response encoding: {response.encoding}")
                
                return response.json()
            except Exception as e:
                # ⭐ ถ้า json() fail อาจเป็นเพราะ gzip error
                logger.warning(f"JSON parsing failed: {str(e)}, trying raw content")
                try:
                    # ลองใช้ raw content
                    import json
                    logger.debug(f"Raw response text (first 500 chars): {response.text[:500]}")
                    return json.loads(response.text)
                except Exception as e2:
                    logger.error(f"Failed to parse response: {str(e2)}")
                    raise ClientError(f"Invalid JSON response: {str(e2)}") from e2
        
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
                if method == "POST":
                    return self._make_request_post(url, api_key, params_or_payload, timeout, retry_count + 1)
                else:
                    return self._make_request(url, api_key, params_or_payload, timeout, retry_count + 1)
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
        params_or_payload: Optional[Dict],
        timeout: int,
        retry_count: int,
        method: str = "GET"
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
            if method == "POST":
                return self._make_request_post(url, api_key, params_or_payload, timeout, retry_count + 1)
            else:
                return self._make_request(url, api_key, params_or_payload, timeout, retry_count + 1)
        else:
            logger.error(f"{error_type} after {self.max_retries} retries")
            raise NetworkError(
                f"{error_type} after {self.max_retries} retries"
            ) from exception
