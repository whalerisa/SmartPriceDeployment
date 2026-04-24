"""
Customer Tier Calculation Module

This module calculates customer price tiers based on multiple factors:
- Tenure (customer age)
- Accumulated purchases (6 months)
- Purchase frequency
- Business type (Gen Bus)

Uses Z-Score normalization to convert raw values to 0-100 scores,
then maps the weighted average to price tiers (R2->R1, R1->W2, W2->W1).
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.special import erf


# ============== CONSTANTS ==============

# Factor weights (must sum to 100)
class Weights:
    ACCUM_6M = 20.72
    FREQUENCY = 28.5
    TENURE = 16.84
    GEN_BUS = 33.94
    TOTAL = 100.0


# Price tier thresholds
class TierThresholds:
    R2_TO_R1 = (0, 40)      # Low-value customers
    R1_TO_W2 = (40, 70)     # Medium-value customers
    W2_TO_W1 = (70, 100)    # High-value customers


# Business type score mapping
GEN_BUS_SCORES = {
    "W": 0.15,  # Wholesale
    "R": 0.27,  # Retail
    "P": 0.21,  # Project
    "I": 0.15,  # Industrial (same as Wholesale)
}


# Column name candidates (case-insensitive matching)
class ColumnNames:
    TENURE = ["customer_date"]
    ACCUM_6M = ["accum_6m"]
    FREQUENCY = ["frequency"]
    GEN_BUS = ["gen_bus"]


# Statistics cache (to avoid recalculating every time)
class StatisticsCache:
    """Singleton cache for statistics"""
    _instance = None
    _cache = None
    _cache_timestamp = None
    _cache_duration_minutes = 60
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get(cls) -> Dict:
        """Get cached statistics if valid, otherwise calculate new"""
        instance = cls()
        
        # Check if cache is still valid
        cache_is_valid = (
            instance._cache is not None and 
            instance._cache_timestamp is not None and 
            (datetime.now() - instance._cache_timestamp).total_seconds() < instance._cache_duration_minutes * 60
        )
        
        if cache_is_valid:
            print("✅ Using cached statistics")
            return instance._cache
        
        # Cache is expired or doesn't exist
        if instance._cache_timestamp is not None:
            age_minutes = (datetime.now() - instance._cache_timestamp).total_seconds() / 60
            print(f"⏰ Cache expired (age: {age_minutes:.1f} minutes > {instance._cache_duration_minutes} minutes)")
            print("🗑️  Clearing expired cache...")
            instance.clear()
        
        # Calculate new statistics
        print("🔄 Calculating fresh statistics from customer database...")
        stats = calculate_statistics_from_database()
        
        # Update cache
        instance._cache = stats
        instance._cache_timestamp = datetime.now()
        
        return stats
    
    @classmethod
    def clear(cls):
        """Clear the cache"""
        instance = cls()
        instance._cache = None
        instance._cache_timestamp = None
        print("🗑️  Statistics cache cleared")
    
    @classmethod
    def info(cls) -> Dict:
        """Get cache information"""
        instance = cls()
        
        if instance._cache_timestamp is None:
            return {"cached": False, "cache_age_minutes": 0}
        
        age_seconds = (datetime.now() - instance._cache_timestamp).total_seconds()
        age_minutes = age_seconds / 60
        
        return {
            "cached": instance._cache is not None,
            "cache_age_minutes": round(age_minutes, 2),
            "cache_valid": age_minutes < instance._cache_duration_minutes,
            "cache_duration_minutes": instance._cache_duration_minutes
        }


# ============== HELPER FUNCTIONS ==============

def get_resource_path(relative_path: str) -> str:
    """
    Locate resource file across different environments.
    
    Supports:
    - PyInstaller (frozen executable)
    - Development (relative to file)
    - Docker (relative to file)
    
    Args:
        relative_path: Path relative to this file
        
    Returns:
        Absolute path to resource file
    """
    candidates = []
    
    # PyInstaller internal path
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, relative_path))
    
    # PyInstaller external path (sibling to executable)
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, relative_path))
    
    # Development/Docker path
    candidates.append(str(Path(__file__).parent / relative_path))
    
    # Return first existing path
    for path in candidates:
        if os.path.exists(path):
            return path
    
    # Default to development path
    return str(Path(__file__).parent / relative_path)


def calculate_statistics_from_database() -> Dict:
    """
    Calculate mean and standard deviation statistics from Customer table.
    
    Returns:
        Dictionary containing calculated statistics from real customer data
    """
    try:
        from config.db_mssql import get_mssql_conn
        
        conn = get_mssql_conn()
        cursor = conn.cursor()
        
        # Query to get customer statistics from Customer table
        sql = """
        SELECT 
            CAST(accum_6m AS FLOAT) as accum_6m,
            CAST(frequency AS FLOAT) as frequency,
            CAST(DATEDIFF(YEAR, customer_date, GETDATE()) AS FLOAT) as tenure_years
        FROM dbo.Customer
        WHERE accum_6m > 0 
            AND frequency > 0
            AND customer_date IS NOT NULL
        """
        
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        if not rows:
            raise Exception("No customer data found for statistics calculation")
        
        # Debug: Check what we got from SQL
        print(f"📊 Fetched {len(rows)} customers from database")
        if rows:
            print(f"📊 First row: {rows[0]}")
            print(f"📊 First row type: {type(rows[0])}")
        
        # Convert rows directly - pyodbc returns tuples
        data = []
        for row in rows:
            try:
                # pyodbc returns Row objects that can be accessed like tuples
                if len(row) == 3:
                    data.append([float(row[0]), float(row[1]), float(row[2])])
                else:
                    print(f"⚠️  Skipping row with unexpected length: {len(row)}")
            except (TypeError, ValueError, IndexError) as e:
                print(f"⚠️  Error processing row: {e}")
                continue
        
        if not data:
            raise Exception(f"No valid data after processing. Total rows fetched: {len(rows)}")
        
        print(f"📊 Successfully processed {len(data)} rows")
        
        # Create DataFrame
        df = pd.DataFrame(data, columns=['accum_6m', 'frequency', 'tenure_years'])
        
        # Ensure all columns are numeric
        df['accum_6m'] = pd.to_numeric(df['accum_6m'], errors='coerce')
        df['frequency'] = pd.to_numeric(df['frequency'], errors='coerce')
        df['tenure_years'] = pd.to_numeric(df['tenure_years'], errors='coerce')
        
        # Remove rows with NaN values
        df = df.dropna()
        
        if len(df) == 0:
            raise Exception("No valid data after cleaning")
        
        # Calculate log-transformed accumulated amount (same as original logic)
        df['accum_6m_ln'] = np.log1p(df['accum_6m'])  # log(1 + x)
        
        # Calculate statistics
        stats = {
            "accum_6m_ln_mean": float(df['accum_6m_ln'].mean()),
            "accum_6m_ln_sd": float(df['accum_6m_ln'].std()),
            "frequency_mean": float(df['frequency'].mean()),
            "frequency_sd": float(df['frequency'].std()),
            "tenure_mean": float(df['tenure_years'].mean()),
            "tenure_sd": float(df['tenure_years'].std())
        }
        
        print(f"✅ Calculated statistics from {len(df)} customers:")
        print(f"   - Accum 6M (ln): mean={stats['accum_6m_ln_mean']:.2f}, sd={stats['accum_6m_ln_sd']:.2f}")
        print(f"   - Frequency: mean={stats['frequency_mean']:.2f}, sd={stats['frequency_sd']:.2f}")
        print(f"   - Tenure: mean={stats['tenure_mean']:.2f}, sd={stats['tenure_sd']:.2f}")
        
        cursor.close()
        conn.close()
        
        return stats
        
    except Exception as e:
        print(f"❌ Error calculating statistics from database: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Failed to calculate statistics: {str(e)}")


def load_statistics() -> Dict:
    """
    Load statistics - calculates from database only (no fallback to JSON file).
    
    Automatically clears cache if expired and recalculates.
    Uses singleton pattern to maintain cache across imports.
    
    Returns:
        Dictionary containing statistics
    """
    return StatisticsCache.get()


def clear_statistics_cache():
    """Clear the statistics cache to force recalculation on next request."""
    StatisticsCache.clear()


def get_cache_info() -> Dict:
    """Get information about the current statistics cache."""
    return StatisticsCache.info()


def find_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """
    Find column name from candidates list (case-insensitive).
    
    Args:
        df: DataFrame to search
        candidates: List of possible column names
        
    Returns:
        Matched column name or None
    """
    # Try exact match first
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    
    # Try case-insensitive match
    lower_cols = {col.strip().lower(): col for col in df.columns}
    for candidate in candidates:
        key = candidate.strip().lower()
        if key in lower_cols:
            return lower_cols[key]
    
    return None
    

def calculate_z_score(values: pd.Series, mean: Optional[float], sd: Optional[float]) -> pd.Series: #แปลงค่าดิบเป็นคะแนน 0-100 โดยใช้ Z-Score และ CDF
    """
    Convert raw values to 0-100 scores using Z-Score and CDF.
    
    Formula:
        1. Z = (X - μ) / σ
        2. Percentile = CDF(Z) = (erf(Z / √2) + 1) / 2
        3. Score = Percentile * 100
    
    Args:
        values: Raw values to convert
        mean: Population mean
        sd: Population standard deviation
        
    Returns:
        Series of scores (0-100), or 0 if statistics unavailable
    """
    if mean is None or sd is None or sd == 0:
        return pd.Series(0.0, index=values.index)
    
    # Calculate Z-score
    z_scores = (values - mean) / sd
    
    # Convert to percentile using CDF
    percentiles = (erf(z_scores / np.sqrt(2)) + 1) / 2
    
    # Convert to 0-100 scale
    scores = percentiles * 100
    
    return scores.fillna(0.0)


def map_score_to_tier(score: float) -> str:
    """
    Map total score to price tier.
    
    Args:
        score: Total weighted score (0-100)
        
    Returns:
        Price tier string (R2->R1, R1->W2, W2->W1, or Unknown)
    """
    if pd.isna(score):
        return "Unknown"
    
    if TierThresholds.R2_TO_R1[0] <= score < TierThresholds.R2_TO_R1[1]:
        return "R2->R1"
    elif TierThresholds.R1_TO_W2[0] <= score < TierThresholds.R1_TO_W2[1]:
        return "R1->W2"
    elif TierThresholds.W2_TO_W1[0] <= score <= TierThresholds.W2_TO_W1[1]:
        return "W2->W1"
    
    return "Unknown"


def map_gen_bus_score(gen_bus: str) -> float:
    """
    Map business type to score.
    
    Args:
        gen_bus: Business type code (W/R/P/I)
        
    Returns:
        Score value (0-1 scale)
    """
    gen_bus = str(gen_bus).strip().upper()
    return GEN_BUS_SCORES.get(gen_bus, GEN_BUS_SCORES["R"])


# ============== SCORE CALCULATORS ==============

def calculate_tenure_score(df: pd.DataFrame, col_name: Optional[str], stats: Dict) -> pd.Series: #คำนวณอายุลูกค้า
    """Calculate tenure (customer age) score."""
    if not col_name:
        return pd.Series(0.0, index=df.index)
    
    current_year = datetime.now().year
    customer_dates = pd.to_datetime(df[col_name], errors="coerce")
    tenure_years = current_year - customer_dates.dt.year
    
    return calculate_z_score(
        tenure_years,
        stats.get("tenure_mean"),
        stats.get("tenure_sd")
    )


def calculate_accum_score(df: pd.DataFrame, col_name: Optional[str], stats: Dict) -> pd.Series: #คำนวณยอดซื้อสะสม6เดือน
    """Calculate accumulated purchase score (log-transformed)."""
    if not col_name:
        return pd.Series(0.0, index=df.index)
    
    accum_values = pd.to_numeric(df[col_name], errors="coerce")
    accum_log = np.log1p(accum_values)  # log(1 + x) to handle zeros
    
    return calculate_z_score(
        accum_log,
        stats.get("accum_6m_ln_mean"),
        stats.get("accum_6m_ln_sd")
    )


def calculate_frequency_score(df: pd.DataFrame, col_name: Optional[str], stats: Dict) -> pd.Series: #คำนวณความถี่ในการซื้อ
    """Calculate purchase frequency score."""
    if not col_name:
        return pd.Series(0.0, index=df.index)
    
    frequency = pd.to_numeric(df[col_name], errors="coerce")
    
    return calculate_z_score(
        frequency,
        stats.get("frequency_mean"),
        stats.get("frequency_sd")
    )


def calculate_gen_bus_score(df: pd.DataFrame, col_name: Optional[str]) -> pd.Series: #คำนวณประเภทลูกค้า
    """Calculate business type score."""
    if not col_name:
        return pd.Series(0.0, index=df.index)
    
    gen_bus_values = df[col_name].astype(str).str.strip().str.upper()
    scores = gen_bus_values.apply(map_gen_bus_score).fillna(GEN_BUS_SCORES["R"])
    
    return scores * 100  # Convert to 0-100 scale


# ============== MAIN FUNCTION ==============

def LevelPrice(df: pd.DataFrame, debug: bool = True) -> pd.DataFrame:
    """
    Calculate customer price tiers based on multiple factors.
    
    Args:
        df: DataFrame with customer data (customer_date, accum_6m, frequency, gen_bus)
        debug: Whether to print debug information
        
    Returns:
        DataFrame with added score columns and tier classification
        
    Added columns:
        - _TenureScore_Z: Tenure score (0-100)
        - _Accum6mScore_Z: Accumulated purchase score (0-100)
        - _FrequencyScore_Z: Purchase frequency score (0-100)
        - _GenBusScore_Z: Business type score (0-100)
        - _Score_Z: Total weighted score (0-100)
        - _Tier_Z: Price tier (R2->R1, R1->W2, W2->W1)
        - tier: Price tier (alias for _Tier_Z)
    """
    # Load statistics
    stats = load_statistics()
    
    # Find column names
    col_tenure = find_column(df, ColumnNames.TENURE)
    col_accum = find_column(df, ColumnNames.ACCUM_6M)
    col_freq = find_column(df, ColumnNames.FREQUENCY)
    col_gen_bus = find_column(df, ColumnNames.GEN_BUS)
    
    # Calculate individual factor scores
    df["_TenureScore_Z"] = calculate_tenure_score(df, col_tenure, stats)
    df["_Accum6mScore_Z"] = calculate_accum_score(df, col_accum, stats)
    df["_FrequencyScore_Z"] = calculate_frequency_score(df, col_freq, stats)
    df["_GenBusScore_Z"] = calculate_gen_bus_score(df, col_gen_bus)
    
    # Calculate weighted total score
    df["_Score_Z"] = (
        df["_Accum6mScore_Z"].fillna(0) * Weights.ACCUM_6M +
        df["_FrequencyScore_Z"].fillna(0) * Weights.FREQUENCY +
        df["_TenureScore_Z"].fillna(0) * Weights.TENURE +
        df["_GenBusScore_Z"].fillna(0) * Weights.GEN_BUS
    ) / Weights.TOTAL
    
    # Map score to tier
    df["_Tier_Z"] = df["_Score_Z"].apply(map_score_to_tier)
    df["tier"] = df["_Tier_Z"]  # Alias without underscore
    
    # Debug output
    if debug:
        _print_debug_info(df)
    
    return df


def _print_debug_info(df: pd.DataFrame) -> None:
    """Print debug information about calculated scores."""
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_colwidth", None)
    pd.set_option("display.expand_frame_repr", False)
    
    debug_cols = [
        col for col in [
            "sku",
            "_Accum6mScore_Z",
            "_FrequencyScore_Z",
            "_TenureScore_Z",
            "_GenBusScore_Z",
            "_Score_Z",
            "_Tier_Z",
        ]
        if col in df.columns
    ]
    
    print("\n=== LEVEL PRICE SCORE DEBUG ===")
    print(df[debug_cols].head(10))
    print("=== END LEVEL PRICE DEBUG ===\n")
