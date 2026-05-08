"""
Invoice Quantity Calculator

Utility functions for calculating line item quantities according to product type-specific rules:
- Glass products: Quantities in square feet (ตารางฟุต)
- Aluminum products: Quantities in linear meters (เส้น) and kilograms (กิโล)
- Standard products: Quantities in pieces (ชิ้น)

Requirements:
- Requirement 3: Calculate Glass Product Quantities in Square Feet
- Requirement 4: Calculate Glass Product Quantities from Description
- Requirement 5: Calculate Aluminum Product Quantities
- Requirement 6: Display Standard Product Quantities
"""
#คำนวณตารางฟุต,กิโล,จำนวน จากinvoice

import re
from typing import Optional, Dict, Any


# ============================================================================
# GLASS PRODUCT CALCULATIONS
# ============================================================================

def extract_glass_dimensions_from_sku(sku: str) -> Optional[Dict[str, float]]:
    """
    Extract glass dimensions from SKU (last 6 characters).
    
    Format: Last 6 characters are [width_inches][height_inches]
    Example: "G01010010106012048" → "012048" → 12 inches × 48 inches
    
    Args:
        sku: Product SKU string
    
    Returns:
        Dict with 'width_inches' and 'height_inches', or None if extraction fails
        
    Requirement: 3.1, 3.2
    """
    if not sku or len(sku) < 6:
        return None
    
    try:
        # Extract last 6 characters
        dimension_str = sku[-6:]
        
        # Parse as 3 digits for width, 3 digits for height
        if len(dimension_str) != 6:
            return None
        
        width_str = dimension_str[:3]
        height_str = dimension_str[3:]
        
        width_inches = float(width_str)
        height_inches = float(height_str)
        
        # Validate dimensions are reasonable (> 0)
        if width_inches <= 0 or height_inches <= 0:
            return None
        
        return {
            "width_inches": width_inches,
            "height_inches": height_inches,
        }
    except (ValueError, IndexError):
        return None


def calculate_glass_square_feet_from_sku(sku: str, quantity: int) -> Optional[Dict[str, Any]]:
    """
    Calculate glass product quantity in square feet from SKU dimensions.
    
    Formula: (width_inches × height_inches) / 144 = square_feet_per_unit
    Total: square_feet_per_unit × quantity = total_square_feet
    
    Args:
        sku: Product SKU string
        quantity: Line item quantity (number of units)
    
    Returns:
        Dict with 'total_square_feet', 'unit', and 'dimensions', or None if calculation fails
        
    Requirement: 3.1, 3.2, 3.3, 3.4, 3.5
    """
    if quantity <= 0:
        return None
    
    dimensions = extract_glass_dimensions_from_sku(sku)
    if not dimensions:
        return None
    
    width_inches = dimensions["width_inches"]
    height_inches = dimensions["height_inches"]
    
    # Calculate square feet per unit
    square_feet_per_unit = (width_inches * height_inches) / 144
    
    # Calculate total square feet
    total_square_feet = square_feet_per_unit * quantity
    
    return {
        "total_square_feet": total_square_feet,
        "unit": "ตารางฟุต",  # square feet in Thai
        "dimensions": {
            "width_inches": width_inches,
            "height_inches": height_inches,
            "square_feet_per_unit": square_feet_per_unit,
        },
    }


def extract_glass_dimensions_from_description(description: str) -> Optional[Dict[str, float]]:
    """
    Extract glass dimensions from description field.
    
    Patterns: "1000x1000MM", "1000X1000mm", "1000 x 1000 MM", "978x382 มม.", etc.
    Converts millimeters to inches: mm / 25.4 = inches
    
    Args:
        description: Product description string
    
    Returns:
        Dict with 'width_inches' and 'height_inches', or None if extraction fails
        
    Requirement: 4.1, 4.2, 4.3
    """
    if not description or not isinstance(description, str):
        return None
    
    try:
        # Pattern to match dimensions like "1000x1000MM", "1000 x 1000 mm", or "978x382 มม."
        # Matches: positive number x positive number MM/mm/มม. (with optional spaces and dots)
        # Uses positive lookahead to ensure no minus sign before numbers
        pattern = r'(?<![0-9-])(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:MM|mm|Mm|mM|มม\.?)'
        
        match = re.search(pattern, description)
        if not match:
            return None
        
        width_mm = float(match.group(1))
        height_mm = float(match.group(2))
        
        # Validate dimensions are reasonable (> 0)
        if width_mm <= 0 or height_mm <= 0:
            return None
        
        # Convert millimeters to inches
        width_inches = width_mm / 25.4
        height_inches = height_mm / 25.4
        
        return {
            "width_inches": width_inches,
            "height_inches": height_inches,
        }
    except (ValueError, AttributeError):
        return None


def calculate_glass_square_feet_from_description(
    description: str, quantity: int
) -> Optional[Dict[str, Any]]:
    """
    Calculate glass product quantity in square feet from description dimensions.
    
    Formula: (width_inches × height_inches) / 144 = square_feet_per_unit
    Total: square_feet_per_unit × quantity = total_square_feet
    
    Args:
        description: Product description string
        quantity: Line item quantity (number of units)
    
    Returns:
        Dict with 'total_square_feet', 'unit', and 'dimensions', or None if calculation fails
        
    Requirement: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """
    if quantity <= 0:
        return None
    
    dimensions = extract_glass_dimensions_from_description(description)
    if not dimensions:
        return None
    
    width_inches = dimensions["width_inches"]
    height_inches = dimensions["height_inches"]
    
    # Calculate square feet per unit
    square_feet_per_unit = (width_inches * height_inches) / 144
    
    # Calculate total square feet
    total_square_feet = square_feet_per_unit * quantity
    
    return {
        "total_square_feet": total_square_feet,
        "unit": "ตารางฟุต",  # square feet in Thai
        "dimensions": {
            "width_inches": width_inches,
            "height_inches": height_inches,
            "square_feet_per_unit": square_feet_per_unit,
        },
    }


# ============================================================================
# ALUMINUM PRODUCT CALCULATIONS
# ============================================================================

def extract_aluminum_weight_per_unit(description: str) -> Optional[float]:
    """
    Extract weight per unit from aluminum product description.
    
    Patterns: 
    - "SMS/5.0" → extract "5.0" (weight per piece in kilograms)
    - "1.0/12.0 -10เส้น" → extract "12.0" (weight per piece in kilograms)
    - "weight: 12.0", etc.
    
    Args:
        description: Product description string
    
    Returns:
        Weight per unit in kilograms, or None if extraction fails
        
    Requirement: 5.2, 5.3
    """
    if not description or not isinstance(description, str):
        return None
    
    try:
        # Pattern 1: Match "SMS/5.0" or similar (word/number)
        pattern1 = r'[A-Z]+\s*/\s*(\d+(?:\.\d+)?)'
        match1 = re.search(pattern1, description)
        if match1:
            weight_per_unit = float(match1.group(1))
            if weight_per_unit > 0:
                return weight_per_unit
        
        # Pattern 2: Match "1.0/12.0 -10เส้น" (number/number)
        pattern2 = r'(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)'
        match2 = re.search(pattern2, description)
        if match2:
            weight_per_unit = float(match2.group(2))
            if weight_per_unit > 0:
                return weight_per_unit
        
        # Pattern 3: Match "weight: 12.0" or "w: 12.0"
        pattern3 = r'(?:weight|w)\s*:\s*(\d+(?:\.\d+)?)'
        match3 = re.search(pattern3, description, re.IGNORECASE)
        if match3:
            weight_per_unit = float(match3.group(1))
            if weight_per_unit > 0:
                return weight_per_unit
        
        return None
    except (ValueError, AttributeError):
        return None


def calculate_aluminum_quantities(
    description: str, quantity: int
) -> Optional[Dict[str, Any]]:
    """
    Calculate aluminum product quantities in linear meters and kilograms.
    
    Linear meters: quantity (number of pieces)
    Kilograms: weight_per_unit × quantity
    
    Args:
        description: Product description string (contains weight per unit)
        quantity: Line item quantity (number of pieces/linear meters)
    
    Returns:
        Dict with 'linear_meters', 'total_kilograms', 'units', or None if calculation fails
        
    Requirement: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    if quantity <= 0:
        return None
    
    weight_per_unit = extract_aluminum_weight_per_unit(description)
    if weight_per_unit is None:
        # If weight extraction fails, return linear meters only
        return {
            "linear_meters": quantity,
            "total_kilograms": None,
            "units": {
                "linear_meters": "เส้น",  # pieces in Thai
                "kilograms": "กิโล",  # kilograms in Thai
            },
        }
    
    # Calculate total weight
    total_kilograms = weight_per_unit * quantity
    
    return {
        "linear_meters": quantity,
        "total_kilograms": total_kilograms,
        "units": {
            "linear_meters": "เส้น",  # pieces in Thai
            "kilograms": "กิโล",  # kilograms in Thai
        },
        "weight_per_unit": weight_per_unit,
    }


# ============================================================================
# STANDARD PRODUCT CALCULATIONS
# ============================================================================

def calculate_standard_product_quantity(quantity: int) -> Dict[str, Any]:
    """
    Calculate standard product quantity (non-glass, non-aluminum).
    
    Display quantity as-is with unit label "ชิ้น" (pieces).
    
    Args:
        quantity: Line item quantity
    
    Returns:
        Dict with 'quantity' and 'unit'
        
    Requirement: 6.1, 6.2
    """
    return {
        "quantity": quantity,
        "unit": "ชิ้น",  # pieces in Thai
    }


# ============================================================================
# MAIN CALCULATION DISPATCHER
# ============================================================================

def calculate_line_item_quantity(
    product_type: str,
    variant_mandatory: int,
    sku: str,
    description: str,
    quantity: int,
) -> Dict[str, Any]:
    """
    Calculate line item quantity based on product type and variant flag.
    
    Dispatcher function that routes to appropriate calculation function based on:
    - product_type: "Glass", "Aluminum", or "Other"
    - variant_mandatory: 1 (size from SKU) or 2 (size from Description)
    
    Args:
        product_type: Product type ("Glass", "Aluminum", "Other")
        variant_mandatory: Variant flag (1 or 2)
        sku: Product SKU
        description: Product description
        quantity: Line item quantity
    
    Returns:
        Dict with calculated quantity and unit information
    """
    if quantity <= 0:
        return calculate_standard_product_quantity(0)
    
    if product_type == "Glass":
        # Check if SKU ends with "000000" (6 zeros) - indicates variant_mandatory=2
        sku_ends_with_zeros = sku and sku.endswith("000000")
        
        if variant_mandatory == 2 or sku_ends_with_zeros:
            # Extract dimensions from description
            result = calculate_glass_square_feet_from_description(description, quantity)
        else:
            # Extract dimensions from SKU (default)
            result = calculate_glass_square_feet_from_sku(sku, quantity)
        
        if result:
            return result
        # Fallback to standard if calculation fails
        return calculate_standard_product_quantity(quantity)
    
    elif product_type == "Aluminum":
        result = calculate_aluminum_quantities(description, quantity)
        if result:
            return result
        # Fallback to standard if calculation fails
        return calculate_standard_product_quantity(quantity)
    
    else:
        # Standard product (Other)
        return calculate_standard_product_quantity(quantity)
