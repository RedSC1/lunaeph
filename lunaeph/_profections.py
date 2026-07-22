"""Annual, Monthly, and Daily Profections (小限推运) module."""

from __future__ import annotations
from typing import Dict, Any
from ._signs import degrees_to_zodiac, SIGN_NAMES, sign_name_index, sign_index_name
from ._classical import DOMICILE_RULERS

# Re-exported for backward compatibility
get_sign_by_index = sign_index_name
get_sign_index = sign_name_index

def calc_profection(
    asc_deg: float,
    age_years: float,
    start_point_deg: float = None,
    whole_sign: bool = True
) -> Dict[str, Any]:
    """
    Calculate Annual, Monthly, and Daily Profections for a given age.
    
    :param asc_deg: Ascendant longitude in degrees.
    :param age_years: Age in completed/fractional years (e.g. 21.0).
    :param start_point_deg: Starting point longitude in degrees (defaults to Ascendant).
    :param whole_sign: If True, uses Whole Sign Profection (1 year = 1 sign).
    :return: Dictionary containing annual, monthly, and daily profected lords and signs.
    """
    if start_point_deg is None:
        start_point_deg = asc_deg
        
    start_sign, start_deg_in_sign = degrees_to_zodiac(start_point_deg)
    start_sign_idx = get_sign_index(start_sign)
    
    # 1. Annual Profection (年小限)
    years_passed = int(age_years)
    fractional_year = age_years - years_passed
    
    annual_sign_idx = (start_sign_idx + years_passed) % 12
    annual_sign = get_sign_by_index(annual_sign_idx)
    annual_ruler = DOMICILE_RULERS[annual_sign]
    
    annual_house = ((annual_sign_idx - get_sign_index(degrees_to_zodiac(asc_deg)[0])) % 12) + 1
    
    # 2. Monthly Profection (月小限 - 以年度小限宫位为起点)
    months_passed = int(fractional_year * 12.0)
    fractional_month = (fractional_year * 12.0) - months_passed
    
    monthly_sign_idx = (annual_sign_idx + months_passed) % 12
    monthly_sign = get_sign_by_index(monthly_sign_idx)
    monthly_ruler = DOMICILE_RULERS[monthly_sign]
    
    # 3. Daily Profection (日小限 - 月限 12 平分，每期约 2.5 天)
    daily_sign_idx = (monthly_sign_idx + int(fractional_month * 12.0)) % 12
    daily_sign = get_sign_by_index(daily_sign_idx)
    daily_ruler = DOMICILE_RULERS[daily_sign]
    
    return {
        "age_years": round(age_years, 4),
        "annual": {
            "sign": annual_sign,
            "house": annual_house,
            "ruler": annual_ruler,
            "years_passed": years_passed
        },
        "monthly": {
            "sign": monthly_sign,
            "ruler": monthly_ruler,
            "months_passed": months_passed
        },
        "daily": {
            "sign": daily_sign,
            "ruler": daily_ruler
        }
    }
