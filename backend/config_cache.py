"""
Config Cache Module

This module provides in-memory caching for configuration data
to avoid needing to restart the server when config changes.
"""

import logging
import os
import json
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Global in-memory cache
_config_cache: Dict[str, Any] = {}


def get_cached_config(key: str, default: Any = None) -> Any:
    """
    Get configuration from cache.
    Falls back to environment variable if not in cache.
    
    Args:
        key: Configuration key
        default: Default value if not found
        
    Returns:
        Configuration value
    """
    # Check cache first
    if key in _config_cache:
        logger.debug(f"Config cache HIT for key: {key}")
        return _config_cache[key]
    
    # Fall back to environment variable
    env_value = os.getenv(key)
    if env_value:
        logger.debug(f"Config cache MISS for key: {key}, loading from env")
        return env_value
    
    logger.debug(f"Config not found for key: {key}, using default")
    return default


def set_cached_config(key: str, value: Any) -> None:
    """
    Set configuration in cache.
    
    Args:
        key: Configuration key
        value: Configuration value
    """
    _config_cache[key] = value
    logger.info(f"Config cached for key: {key}")


def clear_cache() -> None:
    """Clear all cached configuration."""
    global _config_cache
    _config_cache = {}
    logger.info("Config cache cleared")


def get_page_access_config() -> Dict[str, Any]:
    """
    Get page access configuration from cache.
    
    Returns:
        Dictionary of page access configuration
    """
    cached = get_cached_config("PAGE_ACCESS_CONFIG")
    
    if cached:
        try:
            if isinstance(cached, str):
                return json.loads(cached)
            return cached
        except:
            logger.error("Failed to parse cached PAGE_ACCESS_CONFIG")
    
    # Default configuration
    return {
        "create_quote": {
            "page_name": "create_quote",
            "page_label": "สร้างใบเสนอราคา",
            "allowed_roles": ["Sales", "Sales_Project", "ZM", "RM", "SDM", "PM", "CEO", "Admin"]
        },
        "project_price": {
            "page_name": "project_price",
            "page_label": "สร้างรหัสโครงการ",
            "allowed_roles": ["PM", "SDM", "CEO", "Admin"]
        },
        "special_price_approval": {
            "page_name": "special_price_approval",
            "page_label": "หน้าอนุมัติราคา",
            "allowed_roles": ["ZM", "RM", "SDM", "PM", "CEO", "Admin"]
        },
        "update_price": {
            "page_name": "update_price",
            "page_label": "เพิ่มราคา",
            "allowed_roles": ["PM", "SDM", "CEO", "Admin"]
        },
    }


def set_page_access_config(config: Dict[str, Any]) -> None:
    """
    Set page access configuration in cache.
    
    Args:
        config: Page access configuration dictionary
    """
    set_cached_config("PAGE_ACCESS_CONFIG", config)
    logger.info(f"Page access config updated for {len(config)} pages")


def get_role_approval_scope() -> Dict[str, Any]:
    """
    Get role approval scope configuration from cache.
    
    Returns:
        Dictionary of role approval scope configuration
    """
    cached = get_cached_config("ROLE_APPROVAL_SCOPE")
    
    if cached:
        try:
            if isinstance(cached, str):
                return json.loads(cached)
            return cached
        except:
            logger.error("Failed to parse cached ROLE_APPROVAL_SCOPE")
    
    # Default configuration
    return {
        "Sales": {"min_level": "R2", "max_level": "R2"},
        "ZM": {"min_level": "R1", "max_level": "W2"},
        "RM": {"min_level": "W2", "max_level": "W1"},
        "SDM": {"min_level": "W1", "max_level": "SDM"},
        "PM": {"min_level": "R2", "max_level": "SDM"},
        "CEO": {"min_level": "R2", "max_level": "SDM"},
    }


def set_role_approval_scope(config: Dict[str, Any]) -> None:
    """
    Set role approval scope configuration in cache.
    
    Args:
        config: Role approval scope configuration dictionary
    """
    set_cached_config("ROLE_APPROVAL_SCOPE", config)
    logger.info(f"Role approval scope updated for {len(config)} roles")
