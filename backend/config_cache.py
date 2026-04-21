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
    Get page access configuration from cache or file.
    
    Returns:
        Dictionary of page access configuration
    """
    # Check cache first
    cached = get_cached_config("PAGE_ACCESS_CONFIG")
    
    if cached:
        try:
            if isinstance(cached, str):
                return json.loads(cached)
            return cached
        except:
            logger.error("Failed to parse cached PAGE_ACCESS_CONFIG")
    
    # Try to load from JSON file
    try:
        config_file = os.path.join(os.path.dirname(__file__), "page_access_config.json")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Cache it for future use
                set_cached_config("PAGE_ACCESS_CONFIG", config)
                logger.info(f"Loaded page access config from {config_file}")
                return config
    except Exception as e:
        logger.error(f"Failed to load page access config from file: {e}")
    
    # Default configuration
    default_config = {
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
    return default_config


def set_page_access_config(config: Dict[str, Any]) -> None:
    """
    Set page access configuration in cache and persist to file.
    
    Args:
        config: Page access configuration dictionary
    """
    # Update cache
    set_cached_config("PAGE_ACCESS_CONFIG", config)
    
    # Persist to JSON file
    try:
        config_file = os.path.join(os.path.dirname(__file__), "page_access_config.json")
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"Page access config updated and saved to {config_file} for {len(config)} pages")
    except Exception as e:
        logger.error(f"Failed to save page access config to file: {e}")
        # Still update cache even if file save fails
        logger.info(f"Page access config updated in cache for {len(config)} pages")


def get_role_approval_scope() -> Dict[str, Any]:
    """
    Get role approval scope configuration from cache or file.
    
    Returns:
        Dictionary of role approval scope configuration
    """
    # Check cache first
    cached = get_cached_config("ROLE_APPROVAL_SCOPE")
    
    if cached:
        try:
            if isinstance(cached, str):
                return json.loads(cached)
            return cached
        except:
            logger.error("Failed to parse cached ROLE_APPROVAL_SCOPE")
    
    # Try to load from JSON file
    try:
        config_file = os.path.join(os.path.dirname(__file__), "role_approval_scope.json")
        if os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Cache it for future use
                set_cached_config("ROLE_APPROVAL_SCOPE", config)
                logger.info(f"Loaded role approval scope from {config_file}")
                return config
    except Exception as e:
        logger.error(f"Failed to load role approval scope from file: {e}")
    
    # Default configuration
    default_config = {
        "Sales": {"min_level": "R2", "max_level": "R2"},
        "ZM": {"min_level": "R1", "max_level": "W2"},
        "RM": {"min_level": "W2", "max_level": "W1"},
        "SDM": {"min_level": "W1", "max_level": "SDM"},
        "PM": {"min_level": "R2", "max_level": "SDM"},
        "CEO": {"min_level": "R2", "max_level": "SDM"},
    }
    return default_config


def set_role_approval_scope(config: Dict[str, Any]) -> None:
    """
    Set role approval scope configuration in cache and persist to file.
    
    Args:
        config: Role approval scope configuration dictionary
    """
    # Update cache
    set_cached_config("ROLE_APPROVAL_SCOPE", config)
    
    # Persist to JSON file
    try:
        config_file = os.path.join(os.path.dirname(__file__), "role_approval_scope.json")
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"Role approval scope updated and saved to {config_file} for {len(config)} roles")
    except Exception as e:
        logger.error(f"Failed to save role approval scope to file: {e}")
        # Still update cache even if file save fails
        logger.info(f"Role approval scope updated in cache for {len(config)} roles")
