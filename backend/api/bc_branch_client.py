"""
Business Central Branch API Client

This client handles communication with BC Branch API to sync branch data.
"""

import os
import logging
from typing import List, Dict

from api.bc_item_client import BCAPIClient


# Configure logging
logger = logging.getLogger(__name__)


class BCBranchClient(BCAPIClient):
    """
    Client for Business Central Branch API.
    
    Extends BCAPIClient to fetch branch data.
    """
    
    def __init__(self):
        """Initialize Branch API Client with environment config."""
        branch_api_url = os.getenv("BRANCH_API_URL", "").strip().strip('"')
        branch_api_key = os.getenv("BRANCH_API_KEY", "").strip()
        
        if not branch_api_url or not branch_api_key:
            raise ValueError("BRANCH_API_URL and BRANCH_API_KEY must be set in environment")
        
        # Initialize parent with branch API credentials
        super().__init__(
            item_api_url=branch_api_url,
            item_api_key=branch_api_key,
            itemledger_api_url=branch_api_url,  # Not used for branch
            itemledger_api_key=branch_api_key   # Not used for branch
        )
        
        self.branch_api_url = branch_api_url
        self.branch_api_key = branch_api_key
        
        logger.info(f"BC Branch API Client initialized with URL: {branch_api_url}")
    
    def fetch_branches(self) -> List[Dict]:
        """
        Fetch all branches from BC Branch API.
        
        Returns:
            List of branch dictionaries with Code and Name fields
        
        Raises:
            AuthenticationError: When API key is invalid
            APIError: When API returns error response
        """
        url = self.branch_api_url
        
        # Try POST with empty payload (same pattern as Item API)
        response_data = self._make_request_post(
            url=url,
            api_key=self.branch_api_key,
            payload={},
            timeout=self.item_timeout
        )
        
        # Extract branches from response
        if isinstance(response_data, dict):
            # Try to get 'data' field first, fallback to 'value', then the dict itself
            branches = response_data.get("data") or response_data.get("value") or response_data
            if isinstance(branches, list):
                return branches
            return []
        elif isinstance(response_data, list):
            return response_data
        else:
            logger.warning(f"Unexpected response format: {type(response_data)}")
            return []
