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


def get_cached_config(key: str, default: Any = None) -> Any: #ดึงค่า Config แคช หรือ env 
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


def set_cached_config(key: str, value: Any) -> None: #เก็บค่า config ลงแคช เมื่อ Admin บันทึกการตั้งค่า
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


def get_page_access_config() -> Dict[str, Any]: #ดึงสิทิ์กรเข้าถึงหน้าต่างๆ จากแคชหรือไฟล์ JSON เมื่อ User เข้าหน้า (ตรวจสอบสิทธิ์
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
        # Try multiple possible locations for the config file
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "page_access_config.json"),  # Development
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_access_config.json"),  # Absolute path
            os.path.join(os.getcwd(), "page_access_config.json"),  # Current working directory
            os.path.join(os.getcwd(), "backend", "page_access_config.json"),  # CWD/backend
            "page_access_config.json",  # Relative to CWD
        ]
        
        config_file = None
        for path in possible_paths:
            if os.path.exists(path):
                config_file = path
                break
        
        if config_file and os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Cache it for future use
                set_cached_config("PAGE_ACCESS_CONFIG", config)
                logger.info(f"✅ Loaded page access config from {config_file}")
                return config
        else:
            logger.warning(f"⚠️ page_access_config.json not found in any of these locations: {possible_paths}")
    except Exception as e:
        logger.error(f"❌ Failed to load page access config from file: {e}")
    
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
            "allowed_roles": ["Sales_Project", "PM", "SDM", "CEO", "Admin"]  # ⭐ เพิ่ม Sales_Project
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


def set_page_access_config(config: Dict[str, Any]) -> None: #บันทึกสิทธิ์หน้าต่างๆ ลงแคชและไฟล์ JSON เมื่อ Admin บันทึกการตั้งค่าสิทธิ์
    """
    Set page access configuration in cache and persist to file.
    
    Args:
        config: Page access configuration dictionary
    """
    # Update cache
    set_cached_config("PAGE_ACCESS_CONFIG", config)
    
    # Persist to JSON file
    try:
        # Try multiple possible locations for the config file
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "page_access_config.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_access_config.json"),
            os.path.join(os.getcwd(), "page_access_config.json"),
            os.path.join(os.getcwd(), "backend", "page_access_config.json"),
        ]
        
        config_file = None
        for path in possible_paths:
            if os.path.exists(path) or os.path.exists(os.path.dirname(path)):
                config_file = path
                break
        
        if not config_file:
            config_file = possible_paths[0]  # Default to first path
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Page access config updated and saved to {config_file} for {len(config)} pages")
    except Exception as e:
        logger.error(f"❌ Failed to save page access config to file: {e}")
        # Still update cache even if file save fails
        logger.info(f"Page access config updated in cache for {len(config)} pages")

