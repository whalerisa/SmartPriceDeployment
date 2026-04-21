"""
Page Access Control Module

This module provides functions to check if a user has access to specific pages
based on their role.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def load_page_access_config() -> dict:
    """
    Load page access configuration from cache.
    Falls back to default configuration if not found.
    
    Returns:
        Dictionary mapping page IDs to their access configuration
    """
    from config_cache import get_page_access_config
    return get_page_access_config()


def check_page_access(page_id: str, user_role: str) -> bool:
    """
    Check if a user with the given role has access to the specified page.
    
    Args:
        page_id: Page identifier (e.g., "create_quote", "project_price")
        user_role: User's role code (e.g., "Sales", "ZM", "Admin")
        
    Returns:
        True if user has access, False otherwise
        
    Example:
        >>> check_page_access("create_quote", "Sales")
        True
        >>> check_page_access("project_price", "Sales")
        False
    """
    if not page_id or not user_role:
        logger.warning(f"Invalid parameters: page_id='{page_id}', user_role='{user_role}'")
        return False
    
    # Load configuration
    page_access_config = load_page_access_config()
    
    # Check if page exists in configuration
    if page_id not in page_access_config:
        logger.warning(f"Page '{page_id}' not found in access configuration")
        return False
    
    # Get allowed roles for this page
    page_config = page_access_config[page_id]
    allowed_roles = page_config.get("allowed_roles", [])
    
    # Check if user's role is in allowed roles
    has_access = user_role in allowed_roles
    
    logger.info(f"Access check: page='{page_id}', role='{user_role}', allowed={has_access}")
    
    return has_access


def get_user_accessible_pages(user_role: str) -> list[str]:
    """
    Get list of page IDs that the user can access based on their role.
    
    Args:
        user_role: User's role code (e.g., "Sales", "ZM", "Admin")
        
    Returns:
        List of page IDs that the user can access
        
    Example:
        >>> get_user_accessible_pages("Sales")
        ['create_quote']
        >>> get_user_accessible_pages("Admin")
        ['create_quote', 'project_price', 'special_price_approval', 'update_price']
    """
    if not user_role:
        return []
    
    # Load configuration
    page_access_config = load_page_access_config()
    
    # Filter pages where user's role is in allowed_roles
    accessible_pages = [
        page_id
        for page_id, config in page_access_config.items()
        if user_role in config.get("allowed_roles", [])
    ]
    
    logger.info(f"User with role '{user_role}' can access {len(accessible_pages)} pages: {accessible_pages}")
    
    return accessible_pages


def get_page_label(page_id: str) -> Optional[str]:
    """
    Get the display label for a page.
    
    Args:
        page_id: Page identifier
        
    Returns:
        Page label or None if not found
    """
    page_access_config = load_page_access_config()
    
    if page_id in page_access_config:
        return page_access_config[page_id].get("page_label")
    
    return None
