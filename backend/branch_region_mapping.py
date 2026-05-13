"""
Branch to Region Mapping Module

This module provides mapping from branch codes to their corresponding regions.

Regions:
- BKK: Bangkok
- E: East
- N: North
- S: South
- NE: Northeast
- C: Central
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Branch to Region mapping
BRANCH_REGION_MAP = {
    # Bangkok (BKK)
    "00TR": "BKK",
    "01TJ": "BKK",
    "03TS": "BKK",
    "04TP": "BKK",
    "24TL": "BKK",
    "90HO": "BKK",

    # East (E)
    "06RY": "E",
    "15CB": "E",

    # North (N)
    "11PL": "N",
    "12CM": "N",
    "17CR": "N",
    "23NS": "N",

    # South (S)
    "13SR": "S",
    "14HY": "S",
    "16PK": "S",

    # Northeast (NE)
    "08NR": "NE",
    "09UB": "NE",
    "10KK": "NE",
    "18UD": "NE",
    "20SK": "NE",

    # Central (C)
    "05AY": "C",
    "07RB": "C",
    "19PC": "C",
    "21BS": "C",
    "25SB": "C",
}


def get_region_from_branch(branch_code: str) -> str:
    """
    แปลงรหัสสาขาเป็นรหัสภูมิภาค

    Args:
        branch_code: รหัสสาขา เช่น "03TS", "12CM"

    Returns:
        รหัสภูมิภาค (BKK, E, N, S, NE, C) หรือ "Unknown" ถ้าไม่พบ

    Example:
        >>> get_region_from_branch("03TS")
        'BKK'
        >>> get_region_from_branch("12CM")
        'N'
    """
    if not branch_code:
        logger.warning("Empty branch_code provided")
        return "Unknown"

    # Normalize 90HO → 00TR (ทั้งคู่อยู่ใน BKK)
    normalized_branch = "00TR" if branch_code == "90HO" else branch_code

    region = BRANCH_REGION_MAP.get(normalized_branch, "Unknown")

    if region == "Unknown":
        logger.warning(f"Branch code '{normalized_branch}' not found in mapping")
    else:
        logger.info(f"Mapped branch '{branch_code}' → region '{region}'")

    return region


def get_all_branches_by_region(region: str) -> list:
    """
    ดึงรายชื่อสาขาทั้งหมดในภูมิภาคที่กำหนด

    Args:
        region: รหัสภูมิภาค (BKK, E, N, S, NE, C)

    Returns:
        รายชื่อรหัสสาขาในภูมิภาคนั้น

    Example:
        >>> get_all_branches_by_region("BKK")
        ['00TR', '01TJ', '03TS', '04TP', '24TL', '90HO']
    """
    return [branch for branch, reg in BRANCH_REGION_MAP.items() if reg == region]


def get_region_name(region_code: str) -> str:
    """
    แปลงรหัสภูมิภาคเป็นชื่อเต็ม

    Args:
        region_code: รหัสภูมิภาค (BKK, E, N, S, NE, C)

    Returns:
        ชื่อภูมิภาคภาษาอังกฤษ
    """
    region_names = {
        "BKK": "Bangkok",
        "E": "East",
        "N": "North",
        "S": "South",
        "NE": "Northeast",
        "C": "Central",
        "Unknown": "Unknown",
    }
    return region_names.get(region_code, "Unknown")
