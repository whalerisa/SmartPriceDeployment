# products_router.py — Unified Routers (Clean) + Keep ALL endpoints & response keys the same
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Dict, Any, List, Callable

import pandas as pd
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel

from config.db_mssql import get_mssql_conn
from services.sku_enricher import enrich_by_category
from auth_dependency import get_branch_code

# ==========================================================
# ROOT ROUTER (include only this in main.py)
# ==========================================================
api_router = APIRouter()


# ==========================================================
# SHARED: Database helpers
# ==========================================================
# ⭐ Updated to use Item_Master table
ITEMS_TABLE_NAME = "Item_Master"


def _read_table(table: str) -> pd.DataFrame:
    """ดึงข้อมูลจาก MSSQL"""
    conn = get_mssql_conn()
    df = pd.read_sql_query(f'SELECT * FROM {table}', conn)
    conn.close()
    df.columns = [c.strip() for c in df.columns]
    return df


@lru_cache(maxsize=256)
def load_code_name_mapping(table_name: str) -> dict:
    """
    Cached mapping loader: table must have Code, Name
    """
    df = _read_table(table_name)
    if "Code" not in df.columns or "Name" not in df.columns:
        return {}
    out = {}
    for _, r in df.iterrows():
        out[str(r["Code"]).strip()] = str(r["Name"]).strip()
    return out


def _zfill(v: Optional[str], n: int) -> Optional[str]:
    if v is None or v == "":
        return None
    return str(v).zfill(n)


def _parse_by_slices(sku: str, slices: Dict[str, slice], prefix: str, min_len: int) -> Dict[str, Optional[str]]:
    s = (sku or "").strip().upper()
    if not s.startswith(prefix) or len(s) < min_len:
        # return keys with None to keep downstream stable
        return {k: None for k in slices.keys()}
    out = {}
    for k, sl in slices.items():
        try:
            out[k] = s[sl]
        except Exception:
            out[k] = None
    return out


def _load_items_by_prefix(prefix: str) -> pd.DataFrame:
    df = _read_table(ITEMS_TABLE_NAME)
    if "No." not in df.columns:
        return pd.DataFrame()
    q = df[df["No."].astype(str).str.upper().str.startswith(prefix)].copy()
    if q.empty:
        return pd.DataFrame()
    q["SKU"] = q["No."].astype(str).str.upper().str.strip()
    q["Inventory"] = pd.to_numeric(q.get("Inventory", 0), errors="coerce").fillna(0)
    return q


def _apply_filters(df: pd.DataFrame, filters: Dict[str, Optional[str]], pad: Dict[str, int]) -> pd.DataFrame:
    q = df
    for k, v in filters.items():
        if not v:
            continue
        if k not in q.columns:
            continue
        want = str(v)
        if k in pad:
            want = _zfill(want, pad[k])
        q = q[q[k].astype(str) == want]
    return q


def _unique_sorted(df: pd.DataFrame, col: str) -> List[str]:
    if col not in df.columns or df.empty:
        return []
    s = df[col].dropna().astype(str)
    s = s[s != ""]
    return sorted(set(s.tolist()))


def _list_code_name(codes: List[str], mapping: dict) -> List[dict]:
    return [{"code": c, "name": mapping.get(c, c)} for c in codes]


# ==========================================================
# GENERIC SKU CATEGORY SPEC
# ==========================================================
@dataclass(frozen=True)
class SkuCategorySpec:
    prefix: str
    min_len: int
    slices: Dict[str, slice]          # parsed columns
    pad: Dict[str, int]               # zfill for filtering

    # mapping tables
    map_brand: Optional[str] = None
    map_group: Optional[str] = None
    map_subgroup: Optional[str] = None
    map_color: Optional[str] = None
    map_thickness: Optional[str] = None
    map_character: Optional[str] = None  # accessories

    # output keys (must match your original response)
    master_keys: Dict[str, str] = None   # parsed_col -> response_list_key (e.g. "subGroup" -> "subGroups")


def _build_master_response(
    spec: SkuCategorySpec,
    df: pd.DataFrame,
    filters: Dict[str, Optional[str]],
    include_source_filters: bool = False,
) -> Dict[str, Any]:
    """
    Build master/options response with key names matching original.
    """
    # mappings
    brand_map = load_code_name_mapping(spec.map_brand) if spec.map_brand else {}
    group_map = load_code_name_mapping(spec.map_group) if spec.map_group else {}
    sub_map = load_code_name_mapping(spec.map_subgroup) if spec.map_subgroup else {}
    color_map = load_code_name_mapping(spec.map_color) if spec.map_color else {}
    thick_map = load_code_name_mapping(spec.map_thickness) if spec.map_thickness else {}
    char_map = load_code_name_mapping(spec.map_character) if spec.map_character else {}

    out: Dict[str, Any] = {}
    if include_source_filters:
        out["source"] = "sqlite"
        out["filters"] = filters

    # for each list we must return with original key name
    for parsed_col, resp_key in spec.master_keys.items():
        codes = _unique_sorted(df, parsed_col)
        if resp_key == "brands":
            out[resp_key] = _list_code_name(codes, brand_map)
        elif resp_key == "groups":
            out[resp_key] = _list_code_name(codes, group_map)
        elif resp_key == "subGroups":
            out[resp_key] = _list_code_name(codes, sub_map)
        elif resp_key == "colors":
            out[resp_key] = _list_code_name(codes, color_map)
        elif resp_key == "thickness":
            out[resp_key] = _list_code_name(codes, thick_map)
        elif resp_key == "characters":
            out[resp_key] = _list_code_name(codes, char_map)
        else:
            # fallback
            out[resp_key] = _list_code_name(codes, {})
    return out


# ==========================================================
# 1) ITEMS ROUTER (from items.py) — keep outputs the same
# ==========================================================
items_router = APIRouter(prefix="/items", tags=["items"])


def load_items_sqlite() -> pd.DataFrame:
    df = _read_table(ITEMS_TABLE_NAME)

    # rename important columns (match your response usage)
    rename_map = {"No.": "sku", "Description": "name", "Package Size": "pkg_size"}
    df = df.rename(columns={old: new for old, new in rename_map.items() if old in df.columns})

    # category - ดูจากอักษรตัวแรกของ SKU แทน Inventory Posting Group
    df["category"] = df["sku"].astype(str).str[0].str.upper()

    # prices (keep keys priceR1..W2 same, just normalize numeric once)
    for col, out_col in [("R1", "priceR1"), ("R2", "priceR2"), ("W1", "priceW1"), ("W2", "priceW2")]:
        if col in df.columns:
            df[out_col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[out_col] = 0

    # cost
    if "RE" in df.columns:
        df["cost"] = pd.to_numeric(df["RE"], errors="coerce").fillna(0)
    else:
        df["cost"] = 0

    # product_weight
    if "Product Weight" in df.columns:
        df["product_weight"] = pd.to_numeric(df["Product Weight"], errors="coerce").fillna(0)
    else:
        df["product_weight"] = 0

    # pkg_size fallback
    if "pkg_size" not in df.columns:
        df["pkg_size"] = 1

    # Variant flag
    if "Variant Mandatory if Exists" in df.columns:
        df["isVariant"] = df["Variant Mandatory if Exists"].astype(str).str.strip().str.upper().eq("YES")
    else:
        df["isVariant"] = False

    # Product Group/Sub Group
    df["product_group"] = df["Product Group"].astype(str).str.strip() if "Product Group" in df.columns else None
    df["product_sub_group"] = df["Product Sub Group"].astype(str).str.strip() if "Product Sub Group" in df.columns else None

    # Alternate Names
    df["alternate_names"] = df["AlternateName"].astype(str).str.strip() if "AlternateName" in df.columns else None

    # No. 2
    df["sku2"] = df["No. 2"].astype(str).str.strip() if "No. 2" in df.columns else None

    return df


@items_router.get("/categories/list")
def get_item_categories():
    df = load_items_sqlite()
    grouped = df.groupby("category").size().reset_index(name="count").rename(columns={"category": "name"})
    return grouped.to_dict("records")


@items_router.get("/categories/{category_name}")
def get_items_by_category(category_name: str):
    df = load_items_sqlite()
    filtered = df[df["category"] == category_name.upper()]

    items = []
    for _, row in filtered.iterrows():
        extra = enrich_by_category(row["category"], row["sku"]) or {}
        items.append({
            "sku": row["sku"],
            "name": row["name"],
            "inventory": row.get("Inventory", 0),
            "unit": row.get("Base Unit Measure", ""),
            "category": row["category"],
            "isVariant": bool(row.get("isVariant", False)),
            "prices": {
                "R1": row.get("priceR1", 0),
                "R2": row.get("priceR2", 0),
                "W1": row.get("priceW1", 0),
                "W2": row.get("priceW2", 0),
            },
            "pkg_size": row.get("pkg_size", 1),
            "product_weight": row.get("product_weight", 0),
            "sqft_sheet": row.get("Sqft_Sheet"),
            "product_group": row.get("product_group"),
            "product_sub_group": row.get("product_sub_group"),
            "alternate_names": row.get("alternate_names"),
            "sku2": row.get("sku2"),
            **extra,
        })
    return items


@items_router.get("/search")
def full_text_search_items(q: str = Query(..., min_length=3)):
    df = load_items_sqlite()
    q = q.strip().lower()

    def contains(series: pd.Series) -> pd.Series:
        return series.astype(str).str.lower().str.contains(q, na=False)

    mask = contains(df["sku"]) | contains(df["name"])
    if "sku2" in df.columns: mask |= contains(df["sku2"])
    if "Base Unit Measure" in df.columns: mask |= contains(df["Base Unit Measure"])
    if "alternate_names" in df.columns: mask |= contains(df["alternate_names"])

    return df[mask].head(50).to_dict("records")


# ==========================================================
# 2) SKU BASED ROUTERS (ALU / CL / SEA / GYP / ACC)
# ==========================================================

# ---------- ALUMINIUM ----------
aluminium_router = APIRouter(prefix="/aluminium", tags=["aluminium"])
ALU = SkuCategorySpec(
    prefix="A",
    min_len=12,
    slices={"brand": slice(1, 3), "group": slice(3, 5), "subGroup": slice(5, 8), "color": slice(8, 10), "thickness": slice(10, 12)},
    pad={"brand": 2, "group": 2, "subGroup": 3, "color": 2, "thickness": 2},
    map_brand="Aluminium_Brand",
    map_group="Aluminium_Group",
    map_subgroup="Aluminium_SubGroup",
    map_color="Aluminium_Color",
    map_thickness="Aluminium_Thickness",
    master_keys={"brand": "brands", "group": "groups", "subGroup": "subGroups", "color": "colors", "thickness": "thickness"},
)


def _load_parsed_items(spec: SkuCategorySpec) -> pd.DataFrame:
    df = _load_items_by_prefix(spec.prefix)
    if df.empty:
        return df
    parsed = pd.json_normalize(df["SKU"].apply(lambda x: _parse_by_slices(x, spec.slices, spec.prefix, spec.min_len)))
    out = pd.concat([df.reset_index(drop=True), parsed.reset_index(drop=True)], axis=1)
    out["onhand_qty"] = pd.to_numeric(out.get("Inventory", 0), errors="coerce").fillna(0).astype(int)
    return out


@aluminium_router.get("/options")
@aluminium_router.get("/master")
def aluminium_master(
    brand: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
    subGroup: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    thickness: Optional[str] = Query(None),
):
    df = _load_parsed_items(ALU)
    if df.empty:
        return {"source": "sqlite", "filters": {}, "brands": [], "groups": [], "subGroups": [], "colors": [], "thickness": []}

    filters = {"brand": brand, "group": group, "subGroup": subGroup, "color": color, "thickness": thickness}
    q = _apply_filters(df, filters, ALU.pad)

    return _build_master_response(ALU, q, filters, include_source_filters=True)


@aluminium_router.get("/items")
def aluminium_items(
    branch_code: str = Depends(get_branch_code),
    brand: Optional[str] = None,
    group: Optional[str] = None,
    subGroup: Optional[str] = None,
    color: Optional[str] = None,
    thickness: Optional[str] = None,
):
    """Get aluminium items filtered by branch_code"""
    conn = get_mssql_conn()
    
    # Build WHERE clause
    where_clauses = ["im.SKU LIKE 'A%'"]
    params = []
    
    # Add branch filter
    where_clauses.append("EXISTS (SELECT 1 FROM Item_Price ip WHERE ip.SKU = im.SKU AND ip.BranchCode = ?)")
    params.append(branch_code)
    
    # Add SKU pattern filters
    if brand:
        where_clauses.append("SUBSTRING(im.SKU, 2, 2) = ?")
        params.append(brand.zfill(2))
    if group:
        where_clauses.append("SUBSTRING(im.SKU, 4, 2) = ?")
        params.append(group.zfill(2))
    if subGroup:
        where_clauses.append("SUBSTRING(im.SKU, 6, 3) = ?")
        params.append(subGroup.zfill(3))
    if color:
        where_clauses.append("SUBSTRING(im.SKU, 9, 2) = ?")
        params.append(color.zfill(2))
    if thickness:
        where_clauses.append("SUBSTRING(im.SKU, 11, 2) = ?")
        params.append(thickness.zfill(2))
    
    where_sql = " AND ".join(where_clauses)
    
    sql = f"""
        SELECT 
            im.SKU,
            im.Description,
            im.Base_Unit_of_Measure,
            im.Product_Group,
            im.Product_Sub_Group,
            SUBSTRING(im.SKU, 2, 2) AS brand,
            SUBSTRING(im.SKU, 4, 2) AS [group],
            SUBSTRING(im.SKU, 6, 3) AS subGroup,
            SUBSTRING(im.SKU, 9, 2) AS color,
            SUBSTRING(im.SKU, 11, 2) AS thickness
        FROM Item_Master im
        WHERE {where_sql}
        ORDER BY im.SKU
    """
    
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    
    if df.empty:
        return []
    
    # Load mappings
    brand_map = load_code_name_mapping("Aluminium_Brand")
    group_map = load_code_name_mapping("Aluminium_Group")
    sub_map = load_code_name_mapping("Aluminium_SubGroup")
    color_map = load_code_name_mapping("Aluminium_Color")

    items = []
    for _, row in df.iterrows():
        items.append({
            "sku": row["SKU"],
            "name": row.get("Description", ""),
            "brand": row.get("brand"),
            "brandName": brand_map.get(row.get("brand"), ""),
            "group": row.get("group"),
            "groupName": group_map.get(row.get("group"), ""),
            "subGroup": row.get("subGroup"),
            "subGroupName": sub_map.get(row.get("subGroup"), ""),
            "color": row.get("color"),
            "colorName": color_map.get(row.get("color"), ""),
            "thickness": row.get("thickness"),
            "inventory": 0,
            "unit": row.get("Base_Unit_of_Measure", ""),
            "product_group": row.get("Product_Group"),
            "product_sub_group": row.get("Product_Sub_Group"),
        })
    return items


# ---------- C-LINE ----------
cline_router = APIRouter(prefix="/cline", tags=["cline"])
CL = SkuCategorySpec(
    prefix="C",
    min_len=12,
    slices={"brand": slice(1, 3), "group": slice(3, 5), "subGroup": slice(5, 8), "color": slice(8, 10), "thickness": slice(10, 12)},
    pad={"brand": 2, "group": 2, "subGroup": 3, "color": 2, "thickness": 2},
    map_brand="CLine_Brand",
    map_group="CLine_Group",
    map_subgroup="CLine_SubGroup",
    map_color="CLine_Color",
    map_thickness="CLine_Thickness",
    master_keys={"brand": "brands", "group": "groups", "subGroup": "subGroups", "color": "colors", "thickness": "thickness"},
)


@cline_router.get("/items")
def get_cline_items(
    branch_code: str = Depends(get_branch_code),
    brand: str = None,
    group: str = None,
    subGroup: str = None,
    color: str = None,
    thickness: str = None
):
    """Get C-Line items filtered by branch_code"""
    conn = get_mssql_conn()
    
    # Build WHERE clause
    where_clauses = ["im.SKU LIKE 'C%'"]
    params = []
    
    # ⭐ ลบการกรองตามราคา - แสดงสินค้าทั้งหมดแม้ไม่มีราคา
    # where_clauses.append("EXISTS (SELECT 1 FROM Item_Price ip WHERE ip.SKU = im.SKU AND ip.BranchCode = ?)")
    # params.append(branch_code)
    
    # Add SKU pattern filters
    if brand:
        where_clauses.append("SUBSTRING(im.SKU, 2, 2) = ?")
        params.append(brand.zfill(2))
    if group:
        where_clauses.append("SUBSTRING(im.SKU, 4, 2) = ?")
        params.append(group.zfill(2))
    if subGroup:
        where_clauses.append("SUBSTRING(im.SKU, 6, 3) = ?")
        params.append(subGroup.zfill(3))
    if color:
        where_clauses.append("SUBSTRING(im.SKU, 9, 2) = ?")
        params.append(color.zfill(2))
    if thickness:
        where_clauses.append("SUBSTRING(im.SKU, 11, 2) = ?")
        params.append(thickness.zfill(2))
    
    where_sql = " AND ".join(where_clauses)
    
    sql = f"""
        SELECT 
            im.SKU AS [No.],
            im.Description,
            im.Base_Unit_of_Measure AS [Base Unit of Measure],
            im.Product_Group AS [Product Group],
            im.Product_Sub_Group AS [Product Sub Group],
            SUBSTRING(im.SKU, 2, 2) AS brand,
            SUBSTRING(im.SKU, 4, 2) AS [group],
            SUBSTRING(im.SKU, 6, 3) AS subGroup,
            SUBSTRING(im.SKU, 9, 2) AS color,
            SUBSTRING(im.SKU, 11, 2) AS thickness,
            0 AS Inventory,
            1 AS [Package Size],
            0 AS [Product Weight]
        FROM Item_Master im
        WHERE {where_sql}
        ORDER BY im.SKU
    """
    
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    
    if df.empty:
        return []

    brand_map = load_code_name_mapping("CLine_Brand")
    group_map = load_code_name_mapping("CLine_Group")
    sub_map = load_code_name_mapping("CLine_SubGroup")
    color_map = load_code_name_mapping("CLine_Color")
    thick_map = load_code_name_mapping("CLine_Thickness")

    results = []
    for _, row in df.iterrows():
        results.append({
            "sku": str(row["No."]).strip(),
            "name": str(row.get("Description", "")).strip(),
            "brand": row.get("brand"),
            "group": row.get("group"),
            "subGroup": row.get("subGroup"),
            "color": row.get("color"),
            "thickness": row.get("thickness"),
            "brandName": brand_map.get(row.get("brand"), row.get("brand")),
            "groupName": group_map.get(row.get("group"), row.get("group")),
            "subGroupName": sub_map.get(row.get("subGroup"), row.get("subGroup")),
            "colorName": color_map.get(row.get("color"), row.get("color")),
            "thicknessName": thick_map.get(row.get("thickness"), row.get("thickness")),
            "inventory": int(row.get("Inventory", 0) or 0),
            "unit": row.get("Base Unit of Measure", "") or "",
            "pkg_size": int(row.get("Package Size", 1) or 1),
            "product_weight": float(row.get("Product Weight", 0) or 0),
            "product_group": row.get("Product Group"),
            "product_sub_group": row.get("Product Sub Group"),
        })
    return results


@cline_router.get("/master")
def cline_master(
    brand: str = None,
    group: str = None,
    subGroup: str = None,
    color: str = None,
    thickness: str = None
):
    df = _load_parsed_items(CL)
    if df.empty:
        return {"brands": [], "groups": [], "subGroups": [], "colors": [], "thickness": []}

    filters = {"brand": brand, "group": group, "subGroup": subGroup, "color": color, "thickness": thickness}
    q = _apply_filters(df, filters, CL.pad)

    return _build_master_response(CL, q, filters, include_source_filters=False)


@cline_router.get("/options")
def cline_options():
    # keep same response shape as before
    def mapping_to_list(mapping: dict):
        return [{"code": k, "name": v} for k, v in mapping.items()]

    return {
        "brands": mapping_to_list(load_code_name_mapping("CLine_Brand")),
        "groups": mapping_to_list(load_code_name_mapping("CLine_Group")),
        "subGroups": mapping_to_list(load_code_name_mapping("CLine_SubGroup")),
        "colors": mapping_to_list(load_code_name_mapping("CLine_Color")),
        "thickness": mapping_to_list(load_code_name_mapping("CLine_Thickness")),
    }


# ---------- ACCESSORIES ----------
accessories_router = APIRouter(prefix="/accessories", tags=["accessories"])
ACC = SkuCategorySpec(
    prefix="E",
    min_len=11,  # to safely read char position
    slices={
        "brand": slice(1, 4),
        "group": slice(4, 6),
        "subGroup": slice(6, 8),
        "color": slice(8, 10),
        "character": slice(10, 11),
    },
    pad={},  # accessories ไม่ได้ zfill ในโค้ดเดิม
    map_brand="Accessories_Brand",
    map_group="Accessories_Group",
    map_subgroup="Accessories_SubGroup",
    map_color="Accessories_Color",
    map_character="Character",
    master_keys={"brand": "brands", "group": "groups", "subGroup": "subGroups", "color": "colors", "character": "characters"},
)


@accessories_router.get("/items")
def get_accessories_items(
    branch_code: str = Depends(get_branch_code),
    brand: str = None,
    group: str = None,
    subGroup: str = None,
    color: str = None,
    character: str = None
):
    """Get accessories items filtered by branch_code"""
    conn = get_mssql_conn()
    
    # Build WHERE clause
    where_clauses = ["im.SKU LIKE 'E%'", "LEN(im.SKU) >= 11"]
    params = []
    
    # ⭐ ลบการกรองตามราคา - แสดงสินค้าทั้งหมดแม้ไม่มีราคา
    # where_clauses.append("EXISTS (SELECT 1 FROM Item_Price ip WHERE ip.SKU = im.SKU AND ip.BranchCode = ?)")
    # params.append(branch_code)
    
    # Add SKU pattern filters (accessories don't use zfill)
    if brand:
        where_clauses.append("SUBSTRING(im.SKU, 2, 3) = ?")
        params.append(brand)
    if group:
        where_clauses.append("SUBSTRING(im.SKU, 5, 2) = ?")
        params.append(group)
    if subGroup:
        where_clauses.append("SUBSTRING(im.SKU, 7, 2) = ?")
        params.append(subGroup)
    if color:
        where_clauses.append("SUBSTRING(im.SKU, 9, 2) = ?")
        params.append(color)
    if character:
        where_clauses.append("SUBSTRING(im.SKU, 11, 1) = ?")
        params.append(character)
    
    where_sql = " AND ".join(where_clauses)
    
    sql = f"""
        SELECT 
            im.SKU AS [No.],
            im.Description,
            im.Base_Unit_of_Measure AS [Base Unit of Measure],
            im.Product_Group AS [Product Group],
            im.Product_Sub_Group AS [Product Sub Group],
            ip.AlternateName,
            SUBSTRING(im.SKU, 2, 3) AS brand,
            SUBSTRING(im.SKU, 5, 2) AS [group],
            SUBSTRING(im.SKU, 7, 2) AS subGroup,
            SUBSTRING(im.SKU, 9, 2) AS color,
            SUBSTRING(im.SKU, 11, 1) AS [character],
            0 AS inventory
        FROM Item_Master im
        LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
        WHERE {where_sql}
        ORDER BY im.SKU
    """
    
    # Add branch_code for the LEFT JOIN
    all_params = [branch_code] + params
    df = pd.read_sql(sql, conn, params=all_params)
    conn.close()
    
    if df.empty:
        return []

    brand_map = load_code_name_mapping("Accessories_Brand")
    group_map = load_code_name_mapping("Accessories_Group")
    sub_map = load_code_name_mapping("Accessories_SubGroup")
    color_map = load_code_name_mapping("Accessories_Color")
    char_map = load_code_name_mapping("Character")

    results = []
    for _, row in df.iterrows():
        results.append({
            "sku": row["No."],
            "name": row["Description"],
            "alternateName": row.get("AlternateName"),
            "brand": row.get("brand"),
            "brandName": brand_map.get(row.get("brand"), ""),
            "group": row.get("group"),
            "groupName": group_map.get(row.get("group"), ""),
            "subGroup": row.get("subGroup"),
            "subGroupName": sub_map.get(row.get("subGroup"), ""),
            "color": row.get("color"),
            "colorName": color_map.get(row.get("color"), ""),
            "character": row.get("character"),
            "characterName": char_map.get(row.get("character"), ""),
            "inventory": row.get("inventory", 0),
            "unit": row.get("Base Unit of Measure", ""),
            "product_group": row.get("Product Group"),
            "product_sub_group": row.get("Product Sub Group"),
        })
    return results


@accessories_router.get("/master")
def accessories_master(
    brand: str = None,
    group: str = None,
    subGroup: str = None,
    color: str = None,
    character: str = None
):
    df = _load_parsed_items(ACC)
    if df.empty:
        return {"brands": [], "groups": [], "subGroups": [], "colors": [], "characters": []}

    filters = {"brand": brand, "group": group, "subGroup": subGroup, "color": color, "character": character}
    q = _apply_filters(df, filters, ACC.pad)

    return _build_master_response(ACC, q, filters, include_source_filters=False)


@accessories_router.get("/options")
def accessories_options(
    brand: str = None,
    group: str = None,
    subGroup: str = None,
    color: str = None,
    character: str = None
):
    return accessories_master(brand=brand, group=group, subGroup=subGroup, color=color, character=character)


# ---------- SEALANT ----------
sealant_router = APIRouter(prefix="/sealant", tags=["sealant"])
SEA = SkuCategorySpec(
    prefix="S",
    min_len=10,
    slices={"brand": slice(1, 3), "group": slice(3, 5), "subGroup": slice(5, 8), "color": slice(8, 10)},
    pad={"brand": 2, "group": 2, "subGroup": 3, "color": 2},
    map_brand="Sealant_Brand",
    map_group="Sealant_Group",
    map_subgroup="Sealant_SubGroup",
    map_color="Sealant_Color",
    master_keys={"brand": "brands", "group": "groups", "subGroup": "subGroups", "color": "colors"},
)


@sealant_router.get("/master")
def sealant_master(
    brand: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
    subGroup: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
):
    df = _load_parsed_items(SEA)
    if df.empty:
        return {"brands": [], "groups": [], "subGroups": [], "colors": []}

    filters = {"brand": brand, "group": group, "subGroup": subGroup, "color": color}
    q = _apply_filters(df, filters, SEA.pad)

    return _build_master_response(SEA, q, filters, include_source_filters=False)


@sealant_router.get("/options")
def sealant_options(
    brand: Optional[str] = None,
    group: Optional[str] = None,
    subGroup: Optional[str] = None,
    color: Optional[str] = None,
):
    return sealant_master(brand=brand, group=group, subGroup=subGroup, color=color)


@sealant_router.get("/items")
def sealant_items(
    branch_code: str = Depends(get_branch_code),
    brand: Optional[str] = None,
    group: Optional[str] = None,
    subGroup: Optional[str] = None,
    color: Optional[str] = None,
):
    """Get sealant items filtered by branch_code"""
    conn = get_mssql_conn()
    
    # Build WHERE clause
    where_clauses = ["im.SKU LIKE 'S%'"]
    params = []
    
    # ⭐ ลบการกรองตามราคา - แสดงสินค้าทั้งหมดแม้ไม่มีราคา
    # where_clauses.append("EXISTS (SELECT 1 FROM Item_Price ip WHERE ip.SKU = im.SKU AND ip.BranchCode = ?)")
    # params.append(branch_code)
    
    # Add SKU pattern filters
    if brand:
        where_clauses.append("SUBSTRING(im.SKU, 2, 2) = ?")
        params.append(brand.zfill(2))
    if group:
        where_clauses.append("SUBSTRING(im.SKU, 4, 2) = ?")
        params.append(group.zfill(2))
    if subGroup:
        where_clauses.append("SUBSTRING(im.SKU, 6, 3) = ?")
        params.append(subGroup.zfill(3))
    if color:
        where_clauses.append("SUBSTRING(im.SKU, 9, 2) = ?")
        params.append(color.zfill(2))
    
    where_sql = " AND ".join(where_clauses)
    
    sql = f"""
        SELECT 
            im.SKU,
            im.Description,
            im.Base_Unit_of_Measure AS [Base Unit of Measure],
            im.Product_Group AS [Product Group],
            im.Product_Sub_Group AS [Product Sub Group],
            SUBSTRING(im.SKU, 2, 2) AS brand,
            SUBSTRING(im.SKU, 4, 2) AS [group],
            SUBSTRING(im.SKU, 6, 3) AS subGroup,
            SUBSTRING(im.SKU, 9, 2) AS color,
            0 AS onhand_qty
        FROM Item_Master im
        WHERE {where_sql}
        ORDER BY im.SKU
    """
    
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    
    if df.empty:
        return []

    brand_map = load_code_name_mapping("Sealant_Brand")
    group_map = load_code_name_mapping("Sealant_Group")
    sub_map = load_code_name_mapping("Sealant_SubGroup")
    color_map = load_code_name_mapping("Sealant_Color")

    items = []
    for _, row in df.iterrows():
        items.append({
            "sku": row["SKU"],
            "name": row.get("Description", ""),
            "brand": row.get("brand"),
            "brandName": brand_map.get(row.get("brand"), ""),
            "group": row.get("group"),
            "groupName": group_map.get(row.get("group"), ""),
            "subGroup": row.get("subGroup"),
            "subGroupName": sub_map.get(row.get("subGroup"), ""),
            "color": row.get("color"),
            "colorName": color_map.get(row.get("color"), ""),
            "inventory": row.get("onhand_qty", 0),
            "unit": row.get("Base Unit of Measure", ""),
            "product_group": row.get("Product Group"),
            "product_sub_group": row.get("Product Sub Group"),
        })
    return items


# ---------- GYPSUM ----------
gypsum_router = APIRouter(prefix="/gypsum", tags=["gypsum"])
GYP = SkuCategorySpec(
    prefix="Y",
    min_len=18,
    slices={
        "brand": slice(1, 3),
        "group": slice(3, 5),
        "subGroup": slice(5, 7),
        "color": slice(7, 10),
        "thickness": slice(10, 12),
        "sizeCode": slice(12, 18),
    },
    pad={"brand": 2, "group": 2, "subGroup": 2, "color": 3, "thickness": 2},
    map_brand="Gypsum_Brand",
    map_group="Gypsum_Group",
    map_subgroup="Gypsum_SubGroup",
    map_color="Gypsum_Color",
    map_thickness="Gypsum_Thickness",
    master_keys={"brand": "brands", "group": "groups", "subGroup": "subGroups", "color": "colors", "thickness": "thickness"},
)


@gypsum_router.get("/master")
def gypsum_master(
    brand: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
    subGroup: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    thickness: Optional[str] = Query(None),
):
    df = _load_parsed_items(GYP)
    if df.empty:
        return {"brands": [], "groups": [], "subGroups": [], "colors": [], "thickness": []}

    filters = {"brand": brand, "group": group, "subGroup": subGroup, "color": color, "thickness": thickness}
    q = _apply_filters(df, filters, GYP.pad)

    return _build_master_response(GYP, q, filters, include_source_filters=False)


@gypsum_router.get("/options")
def gypsum_options(
    brand: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
    subGroup: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    thickness: Optional[str] = Query(None),
):
    return gypsum_master(brand=brand, group=group, subGroup=subGroup, color=color, thickness=thickness)


@gypsum_router.get("/items")
def gypsum_items(
    branch_code: str = Depends(get_branch_code),
    brand: Optional[str] = None,
    group: Optional[str] = None,
    subGroup: Optional[str] = None,
    color: Optional[str] = None,
    thickness: Optional[str] = None,
):
    """Get gypsum items filtered by branch_code"""
    conn = get_mssql_conn()
    
    # Build WHERE clause
    where_clauses = ["im.SKU LIKE 'Y%'", "LEN(im.SKU) >= 18"]
    params = []
    
    # ⭐ ลบการกรองตามราคา - แสดงสินค้าทั้งหมดแม้ไม่มีราคา
    # where_clauses.append("EXISTS (SELECT 1 FROM Item_Price ip WHERE ip.SKU = im.SKU AND ip.BranchCode = ?)")
    # params.append(branch_code)
    
    # Add SKU pattern filters
    if brand:
        where_clauses.append("SUBSTRING(im.SKU, 2, 2) = ?")
        params.append(brand.zfill(2))
    if group:
        where_clauses.append("SUBSTRING(im.SKU, 4, 2) = ?")
        params.append(group.zfill(2))
    if subGroup:
        where_clauses.append("SUBSTRING(im.SKU, 6, 2) = ?")
        params.append(subGroup.zfill(2))
    if color:
        where_clauses.append("SUBSTRING(im.SKU, 8, 3) = ?")
        params.append(color.zfill(3))
    if thickness:
        where_clauses.append("SUBSTRING(im.SKU, 11, 2) = ?")
        params.append(thickness.zfill(2))
    
    where_sql = " AND ".join(where_clauses)
    
    sql = f"""
        SELECT 
            im.SKU,
            im.Description,
            im.Base_Unit_of_Measure AS [Base Unit of Measure],
            im.Product_Group AS [Product Group],
            im.Product_Sub_Group AS [Product Sub Group],
            SUBSTRING(im.SKU, 2, 2) AS brand,
            SUBSTRING(im.SKU, 4, 2) AS [group],
            SUBSTRING(im.SKU, 6, 2) AS subGroup,
            SUBSTRING(im.SKU, 8, 3) AS color,
            SUBSTRING(im.SKU, 11, 2) AS thickness,
            0 AS onhand_qty,
            1 AS [Package Size],
            0 AS [Product Weight]
        FROM Item_Master im
        WHERE {where_sql}
        ORDER BY im.SKU
    """
    
    df = pd.read_sql(sql, conn, params=params)
    conn.close()
    
    if df.empty:
        return []

    brand_map = load_code_name_mapping("Gypsum_Brand")
    group_map = load_code_name_mapping("Gypsum_Group")
    sub_map = load_code_name_mapping("Gypsum_SubGroup")
    color_map = load_code_name_mapping("Gypsum_Color")
    thick_map = load_code_name_mapping("Gypsum_Thickness")

    items = []
    for _, row in df.iterrows():
        items.append({
            "sku": row["SKU"],
            "name": row.get("Description", ""),
            "brand": row.get("brand"),
            "brandName": brand_map.get(row.get("brand"), ""),
            "group": row.get("group"),
            "groupName": group_map.get(row.get("group"), ""),
            "subGroup": row.get("subGroup"),
            "subGroupName": sub_map.get(row.get("subGroup"), ""),
            "color": row.get("color"),
            "colorName": color_map.get(row.get("color"), ""),
            "thickness": row.get("thickness"),
            "inventory": row.get("onhand_qty", 0),
            "unit": row.get("Base Unit of Measure", "") or "",
            "pkg_size": int(row.get("Package Size", 1) or 1),
            "product_weight": float(row.get("Product Weight", 0) or 0),
            "product_group": row.get("Product Group"),
            "product_sub_group": row.get("Product Sub Group"),
        })
    return items


# ==========================================================
# 7) GLASS ROUTER (keep logic as-is, only minor tidy)
# ==========================================================
glass_router = APIRouter(prefix="/glass", tags=["glass"])

# ⚡ Cache สำหรับ glass list (10 นาที)
_glass_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 600,  # 10 minutes
}


def parse_glass_sku(sku: str):
    """
    Parse glass SKU with validation.
    Expected format: GBBTTSSSCCTTWWWHHH (18 characters)
    G = Glass category
    BB = Brand (2 digits)
    TT = Type (2 digits)
    SSS = SubGroup (3 digits)
    CC = Color (2 digits)
    TT = Thickness (2 digits)
    WWW = Width (3 digits, can be 000 for template SKU)
    HHH = Height (3 digits, can be 000 for template SKU)
    """
    # Validate SKU length
    if not sku or len(sku) != 18:
        return None
    
    # Skip non-glass SKU
    if not sku.startswith('G'):
        return None
    
    try:
        width_str = sku[12:15]
        height_str = sku[15:18]
        
        # Convert to int (allow 0 for template SKUs)
        width = int(width_str) if width_str.strip() else 0
        height = int(height_str) if height_str.strip() else 0
        
        return {
            "brand": sku[1:3],
            "type": sku[3:5],
            "subGroup": sku[5:8],
            "color": sku[8:10],
            "thickness": sku[10:12],
            "width": width,
            "height": height,
        }
    except (ValueError, IndexError) as e:
        # Return None for invalid SKU format
        print(f"⚠️ Failed to parse SKU {sku}: {e}")
        return None


def load_glass_data():
    """⚡ โหลดข้อมูลกระจกพร้อม cache"""
    import time
    
    current_time = time.time()
    
    # ตรวจสอบ cache
    if _glass_cache["data"] is not None:
        age = current_time - _glass_cache["timestamp"]
        if age < _glass_cache["ttl"]:
            print(f"✅ Using cached glass data (age: {age:.1f}s)")
            return _glass_cache["data"]
    
    print("📥 Loading glass data from database...")
    
    # ⚡ ใช้ MSSQL สำหรับ Item_Master
    conn = get_mssql_conn()
    cur = conn.cursor()

    # ⚡ ใช้ SQL ที่มี WHERE clause เพื่อกรองที่ database level
    # ⚠️ MSSQL column names: SKU, No_2, Description, Variant_Mandatory, Product_Group, Product_Sub_Group
    cur.execute("""
        SELECT
            SKU AS No,
            No_2,
            Description,
            0 AS Inventory,
            Variant_Mandatory AS Variant_Mandatory_if_Exists,
            Product_Group,
            Product_Sub_Group
        FROM Item_Master
        WHERE SKU LIKE 'G%'
        ORDER BY SKU
    """)
    rows = cur.fetchall()

    # โหลด mapping tables (ใช้ MSSQL)
    cur.execute("SELECT Code, Name FROM Glass_Brand")
    brand_map = {str(c).zfill(2): n for c, n in cur.fetchall()}

    cur.execute("SELECT Code, Name FROM Glass_Color")
    color_map = {str(c).zfill(2): n for c, n in cur.fetchall()}

    cur.execute("SELECT Code, Name FROM Glass_Group")
    type_map = {str(c).zfill(2): n for c, n in cur.fetchall()}

    cur.execute("SELECT Type, Code, Name FROM Glass_SubGroup")
    subgroup_map = {(str(t).zfill(2), str(c).zfill(3)): n for t, c, n in cur.fetchall()}

    # ปิด connection
    conn.close()

    # ⚡ สร้าง result พร้อม enrich
    result = []
    variant_counts = {}  # Track variant_mandatory values
    for sku, sku2, desc, inv, vmand, product_group, product_sub_group in rows:
        parsed = parse_glass_sku(sku)
        
        # Skip invalid SKU
        if parsed is None:
            print(f"⚠️ Skipping invalid glass SKU: {sku}")
            continue
        
        # Track variant_mandatory values for debugging
        variant_counts[vmand] = variant_counts.get(vmand, 0) + 1
        
        # Convert to int for comparison (database returns string)
        is_variant = int(vmand) == 2 if vmand else False  # 2 = มี variant, 1 = ไม่มี variant

        brandName = brand_map.get(parsed["brand"], "")
        colorName = color_map.get(parsed["color"], "")
        typeName = type_map.get(parsed["type"], "")
        subGroupName = subgroup_map.get((parsed["type"], parsed["subGroup"]), "")

        result.append({
            "sku": sku,
            "sku2": sku2 or "",
            "description": desc,
            "isVariant": is_variant,
            "inventory": inv,
            "brand": parsed["brand"],
            "brandName": brandName,
            "type": parsed["type"],
            "typeName": typeName,
            "group": parsed["type"],
            "groupName": typeName,
            "subGroup": parsed["subGroup"],
            "subGroupName": subGroupName,
            "color": parsed["color"],
            "colorName": colorName,
            "thickness": parsed["thickness"],
            "width": parsed["width"],
            "height": parsed["height"],
            "product_group": product_group,
            "product_sub_group": product_sub_group,
        })

    # บันทึกลง cache
    _glass_cache["data"] = result
    _glass_cache["timestamp"] = current_time
    
    # Count variant items
    variant_count = sum(1 for item in result if item["isVariant"])
    non_variant_count = len(result) - variant_count
    
    print(f"💾 Glass data cached ({len(result)} items, TTL: {_glass_cache['ttl']}s)")
    print(f"📊 Variant_Mandatory distribution: {variant_counts}")
    print(f"   → Variant items (isVariant=true): {variant_count}")
    print(f"   → Non-variant items (isVariant=false): {non_variant_count}")
    
    return result


@glass_router.get("/list")
def get_glass_list(
    branch_code: str = Depends(get_branch_code),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    brand: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    subGroup: Optional[str] = Query(None),
    color: Optional[str] = Query(None),
    thickness: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    isVariant: Optional[bool] = Query(None),
):
    """⚡ ดึงรายการกระจก (รองรับ Full-Text Search + กรองตาม branch_code)"""
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Glass search request: branch={branch_code}, search='{search}', brand={brand}, type={type}, subGroup={subGroup}, color={color}, thickness={thickness}, isVariant={isVariant}")
    
    # ⚡ Query จาก database พร้อมกรองตาม branch_code
    conn = get_mssql_conn()
    cur = conn.cursor()
    
    # สร้าง WHERE clause สำหรับ filter
    where_clauses = ["im.SKU LIKE 'G%'"]
    params = []
    
    # ⭐ ลบการกรองตามราคา - แสดงสินค้าทั้งหมดแม้ไม่มีราคา
    # where_clauses.append("EXISTS (SELECT 1 FROM Item_Price ip WHERE ip.SKU = im.SKU AND ip.BranchCode = ?)")
    # params.append(branch_code)
    
    if brand:
        where_clauses.append("SUBSTRING(im.SKU, 2, 2) = ?")
        params.append(brand)
    if type:
        where_clauses.append("SUBSTRING(im.SKU, 4, 2) = ?")
        params.append(type)
    if subGroup:
        where_clauses.append("SUBSTRING(im.SKU, 6, 3) = ?")
        params.append(subGroup)
    if color:
        where_clauses.append("SUBSTRING(im.SKU, 9, 2) = ?")
        params.append(color)
    if thickness:
        where_clauses.append("SUBSTRING(im.SKU, 11, 2) = ?")
        params.append(thickness)
    if isVariant is not None:
        where_clauses.append("im.Variant_Mandatory = ?")
        params.append(2 if isVariant else 1)
    
    # เพิ่ม search condition
    if search and search.strip():
        search_term = search.strip()
        
        # ตรวจสอบว่ามี Full-Text Index หรือไม่
        cur.execute("""
            SELECT COUNT(*) as has_fulltext
            FROM sys.fulltext_indexes 
            WHERE object_id = OBJECT_ID('Item_Master')
        """)
        has_fulltext = cur.fetchone()[0] > 0
        
        if has_fulltext:
            # ใช้ Full-Text Search
            search_pattern = f'"{search_term}*"'
            where_clauses.append("(CONTAINS((im.SKU, im.No_2, im.Description), ?) OR im.SKU LIKE ? OR im.No_2 LIKE ?)")
            params.extend([search_pattern, f"%{search_term}%", f"%{search_term}%"])
        else:
            # ใช้ LIKE
            where_clauses.append("(im.SKU LIKE ? OR im.No_2 LIKE ? OR im.Description LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
    
    where_sql = " AND ".join(where_clauses)
    
    logger.info(f"📊 SQL WHERE: {where_sql}")
    logger.info(f"📊 SQL PARAMS: {params}")
    
    # นับจำนวนทั้งหมด
    count_sql = f"""
        SELECT COUNT(*) as total
        FROM Item_Master im
        WHERE {where_sql}
    """
    cur.execute(count_sql, *params)
    total = cur.fetchone()[0]
    
    logger.info(f"✅ Found {total} items matching search")
    
    # ดึงข้อมูล พร้อมราคา
    sql = f"""
        SELECT
            im.SKU,
            im.No_2,
            im.Description,
            im.Variant_Mandatory,
            im.Product_Group,
            im.Product_Sub_Group,
            im.Base_Unit_of_Measure,
            ip.R1,
            ip.R2,
            ip.W1,
            ip.W2
        FROM Item_Master im
        LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
        WHERE {where_sql}
        ORDER BY im.SKU
        OFFSET ? ROWS
        FETCH NEXT ? ROWS ONLY
    """
    # เพิ่ม branch_code เป็น parameter แรก
    cur.execute(sql, branch_code, *params, offset, limit)
    rows = cur.fetchall()
    
    logger.info(f"📦 Retrieved {len(rows)} items")
    
    # โหลด mapping tables
    cur.execute("SELECT Code, Name FROM Glass_Brand")
    brand_map = {str(c).zfill(2): n for c, n in cur.fetchall()}
    
    cur.execute("SELECT Code, Name FROM Glass_Color")
    color_map = {str(c).zfill(2): n for c, n in cur.fetchall()}
    
    cur.execute("SELECT Code, Name FROM Glass_Group")
    type_map = {str(r[0]).zfill(2): r[1] for r in cur.fetchall()}
    
    cur.execute("SELECT Type, Code, Name FROM Glass_SubGroup")
    subgroup_map = {(str(t).zfill(2), str(c).zfill(3)): n for t, c, n in cur.fetchall()}
    
    conn.close()
    
    # แปลงผลลัพธ์
    items = []
    for row in rows:
        sku = row[0]
        parsed = parse_glass_sku(sku)
        if not parsed:
            continue
        
        is_variant = int(row[3]) == 2 if row[3] else False
        
        items.append({
            "sku": sku,
            "sku2": row[1] or "",
            "description": row[2] or "",
            "isVariant": is_variant,
            "inventory": 0,
            "brand": parsed["brand"],
            "brandName": brand_map.get(parsed["brand"], ""),
            "type": parsed["type"],
            "typeName": type_map.get(parsed["type"], ""),
            "group": parsed["type"],
            "groupName": type_map.get(parsed["type"], ""),
            "subGroup": parsed["subGroup"],
            "subGroupName": subgroup_map.get((parsed["type"], parsed["subGroup"]), ""),
            "color": parsed["color"],
            "colorName": color_map.get(parsed["color"], ""),
            "thickness": parsed["thickness"],
            "width": parsed["width"],
            "height": parsed["height"],
            "product_group": row[4],
            "product_sub_group": row[5],
            "unit": row[6] or "แผ่น",  # ⭐ เพิ่ม Base_Unit_of_Measure
            "prices": {
                "R1": float(row[7]) if row[7] is not None else 0,
                "R2": float(row[8]) if row[8] is not None else 0,
                "W1": float(row[9]) if row[9] is not None else 0,
                "W2": float(row[10]) if row[10] is not None else 0,
            }
        })
    
    return {
        "items": items,
        "limit": limit,
        "offset": offset,
        "count": len(items),
        "total": total,
    }


class GlassCalcRequest(BaseModel):
    sku: str
    widthRaw: float
    heightRaw: float
    widthRounded: float
    heightRounded: float
    sqftRaw: float
    sqftRounded: float
    qty: int


@glass_router.post("/calc")
def calc_glass(req: GlassCalcRequest, branch_code: str = Depends(get_branch_code)):
    parsed = parse_glass_sku(req.sku)

    # ⚡ ใช้ MSSQL สำหรับ mapping tables
    conn = get_mssql_conn()
    cur = conn.cursor()

    cur.execute("SELECT Name FROM Glass_Brand WHERE Code=?", (parsed["brand"],))
    row = cur.fetchone()
    brandName = row.Name if row else ""

    cur.execute("SELECT Name FROM Glass_Color WHERE Code=?", (parsed["color"],))
    row = cur.fetchone()
    colorName = row.Name if row else ""

    cur.execute("SELECT Code, Name FROM Glass_Group")
    type_map = {str(r.Code).zfill(2): r.Name for r in cur.fetchall()}

    cur.execute("""
        SELECT Name
        FROM Glass_SubGroup
        WHERE Type=? AND Code=?
    """, (parsed["type"], parsed["subGroup"]))
    row = cur.fetchone()
    subGroupName = row.Name if row else ""

    typeName = type_map.get(parsed["type"], "")

    # ⚡ ดึงราคา R2 จาก Item_Price ตาม branch_code
    cur.execute("""
        SELECT R2 
        FROM Item_Price WITH (NOLOCK)
        WHERE SKU = ? AND BranchCode = ?
    """, (req.sku, branch_code))
    row = cur.fetchone()
    price_r2 = float(row.R2) if row and row.R2 else 0.0
    
    conn.close()

    total_price_r2 = price_r2 * req.sqftRounded

    return {
        "sku": req.sku,
        "brand": parsed["brand"],
        "brandName": brandName,
        "type": parsed["type"],
        "typeName": typeName,
        "subGroup": parsed["subGroup"],
        "subGroupName": subGroupName,
        "color": parsed["color"],
        "colorName": colorName,
        "thickness": parsed["thickness"],
        "width": req.widthRounded,
        "height": req.heightRounded,
        "sqft": req.sqftRounded,
        "qty": req.qty,
        "totalSqft": req.sqftRounded * req.qty,
        "priceR2": price_r2,
        "totalPriceR2": total_price_r2,
        "widthRaw": req.widthRaw,
        "heightRaw": req.heightRaw,
        "widthRounded": req.widthRounded,
        "heightRounded": req.heightRounded,
    }


@glass_router.get("/filter-options")
def get_glass_filter_options(
    brand: Optional[str] = None,
    type: Optional[str] = None,
    subGroup: Optional[str] = None,
    color: Optional[str] = None,
    thickness: Optional[str] = None,
    branch_code: Optional[str] = None  # ทำให้เป็น optional สำหรับ Promotion
):
    """⚡ ดึง filter options ที่ถูกกรองแล้วตามเงื่อนไขปัจจุบัน
    
    ส่งกลับ options สำหรับแต่ละฟิลเตอร์ที่ยังไม่ได้เลือก
    เช่น ถ้าเลือก brand แล้ว ให้ส่ง type/subGroup/color/thickness ที่มีอยู่ใน brand นั้น
    
    รองรับ multiple values (comma-separated) เช่น brand=01,02
    """
    
    # แปลง comma-separated values เป็น list
    brand_list = brand.split(',') if brand else []
    type_list = type.split(',') if type else []
    subGroup_list = subGroup.split(',') if subGroup else []
    color_list = color.split(',') if color else []
    thickness_list = thickness.split(',') if thickness else []
    
    # Query จาก database
    conn = get_mssql_conn()
    cur = conn.cursor()
    
    # ดึงกระจกทั้งหมด (ถ้าไม่ระบุ branch_code)
    if branch_code:
        # ดึงเฉพาะกระจกที่มีราคาในสาขานี้
        cur.execute("""
            SELECT DISTINCT
                im.SKU
            FROM Item_Master im
            LEFT JOIN Item_Price ip WITH (NOLOCK) ON im.SKU = ip.SKU AND ip.BranchCode = ?
            WHERE im.SKU LIKE 'G%'
        """, (branch_code,))
    else:
        # ดึงกระจกทั้งหมด (สำหรับ Promotion)
        cur.execute("""
            SELECT DISTINCT SKU
            FROM Item_Master
            WHERE SKU LIKE 'G%'
        """)
    
    skus = [row[0] for row in cur.fetchall()]
    
    # โหลด mapping tables
    cur.execute("SELECT Code, Name FROM Glass_Brand")
    brand_map = {str(c).zfill(2): n for c, n in cur.fetchall()}
    
    cur.execute("SELECT Code, Name FROM Glass_Color")
    color_map = {str(c).zfill(2): n for c, n in cur.fetchall()}
    
    cur.execute("SELECT Code, Name FROM Glass_Group")
    type_map = {str(r[0]).zfill(2): r[1] for r in cur.fetchall()}
    
    cur.execute("SELECT Type, Code, Name FROM Glass_SubGroup")
    subgroup_rows = cur.fetchall()
    subgroup_map = {(str(t).zfill(2), str(c).zfill(3)): n for t, c, n in subgroup_rows}
    
    conn.close()
    
    # ⭐ กรอง SKU ตามเงื่อนไขปัจจุบัน (รองรับ multiple values)
    filtered_skus = []
    for sku in skus:
        parsed = parse_glass_sku(sku)
        if not parsed:
            continue
        
        # ตรวจสอบว่า SKU ตรงกับ filter ทั้งหมด
        if brand_list and parsed["brand"] not in brand_list:
            continue
        if type_list and parsed["type"] not in type_list:
            continue
        if subGroup_list and parsed["subGroup"] not in subGroup_list:
            continue
        if color_list and parsed["color"] not in color_list:
            continue
        if thickness_list and parsed["thickness"] not in thickness_list:
            continue
        
        filtered_skus.append(sku)
    
    # ⭐ สร้าง options สำหรับแต่ละฟิลเตอร์ โดยกรองตามเงื่อนไขปัจจุบัน
    brands = {}
    types = {}
    subGroups = {}
    colors = {}
    thicknesses = {}
    
    for sku in filtered_skus:
        parsed = parse_glass_sku(sku)
        if not parsed:
            continue
            
        brands[parsed["brand"]] = brand_map.get(parsed["brand"], parsed["brand"])
        types[parsed["type"]] = type_map.get(parsed["type"], parsed["type"])
        subGroups[parsed["subGroup"]] = subgroup_map.get((parsed["type"], parsed["subGroup"]), parsed["subGroup"])
        colors[parsed["color"]] = color_map.get(parsed["color"], parsed["color"])
        thicknesses[parsed["thickness"]] = parsed["thickness"]
    
    return {
        "brands": [{"value": k, "label": f"{k} - {v}"} for k, v in sorted(brands.items())],
        "types": [{"value": k, "label": f"{k} - {v}"} for k, v in sorted(types.items())],
        "subGroups": [{"value": k, "label": f"{k} - {v}"} for k, v in sorted(subGroups.items())],
        "colors": [{"value": k, "label": f"{k} - {v}"} for k, v in sorted(colors.items())],
        "thicknesses": [{"value": k, "label": f"{k} - {v} มม."} for k, v in sorted(thicknesses.items())],
    }


@glass_router.post("/clear-cache")
def clear_glass_cache():
    """🔄 Clear glass data cache (for testing/debugging)"""
    _glass_cache["data"] = None
    _glass_cache["timestamp"] = 0
    return {"message": "Glass cache cleared successfully"}


@glass_router.get("/{sku}/stock")
def get_glass_stock(sku: str, branch_code: str = Depends(get_branch_code)):
    """
    ดึงข้อมูล stock สำหรับกระจกเฉพาะสาขาของพนักงาน
    
    Response:
    {
        "sku": "G00080010000000000",
        "branch_code": "BKK",
        "quantity": 100
    }
    """
    try:
        from api.bc_item_client import BCAPIClient
        
        # สร้าง client
        client = BCAPIClient()
        
        # ดึงข้อมูล inventory ledger entries สำหรับ item และ branch นี้
        ledger_entries = client.fetch_inventory(sku, branch_code)
        
        # บวก Quantity จากทุก records
        total_quantity = 0
        for entry in ledger_entries:
            qty = entry.get("Quantity", 0)
            total_quantity += qty
        
        return {
            "sku": sku,
            "branch_code": branch_code,
            "quantity": float(total_quantity)
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching stock for SKU {sku} at branch {branch_code}: {str(e)}")
        
        # Return default response ถ้า API error
        return {
            "sku": sku,
            "branch_code": branch_code,
            "quantity": 0,
            "error": str(e)
        }


# ==========================================================
# INCLUDE ALL SUB-ROUTERS INTO api_router
# ==========================================================
api_router.include_router(items_router)
api_router.include_router(aluminium_router)
api_router.include_router(cline_router)
api_router.include_router(accessories_router)
api_router.include_router(sealant_router)
api_router.include_router(gypsum_router)
api_router.include_router(glass_router)
