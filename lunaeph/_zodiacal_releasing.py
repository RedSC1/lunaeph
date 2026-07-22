"""Zodiacal Releasing (希腊化黄道释放) calculation module."""

from __future__ import annotations
from typing import Dict, Any, List
from ._signs import SIGN_NAMES, degrees_to_zodiac, sign_name_index, sign_index_name

# Sign durations in Years for Zodiacal Releasing (Valens / Chris Brennan)
ZR_SIGN_YEARS = {
    "Aries": 15.0,
    "Taurus": 8.0,
    "Gemini": 20.0,
    "Cancer": 25.0,
    "Leo": 19.0,
    "Virgo": 20.0,
    "Libra": 8.0,
    "Scorpio": 15.0,
    "Sagittarius": 12.0,
    "Capricorn": 27.0,
    "Aquarius": 30.0,
    "Pisces": 12.0,
}


def calc_zr_l1_periods(start_sign: str, max_years: float = 100.0) -> List[Dict[str, Any]]:
    """Calculate Level 1 (L1) Zodiacal Releasing periods."""
    periods = []
    current_idx = sign_name_index(start_sign)
    current_age = 0.0
    
    while current_age < max_years:
        sign = sign_index_name(current_idx)
        duration = ZR_SIGN_YEARS[sign]
        end_age = current_age + duration
        
        periods.append({
            "level": 1,
            "sign": sign,
            "start_age": round(current_age, 4),
            "end_age": round(end_age, 4),
            "duration_years": duration,
        })
        
        current_age = end_age
        current_idx = (current_idx + 1) % 12
        
    return periods

def calc_zr_l2_subperiods(l1_sign: str, l1_start_age: float, l1_duration: float) -> List[Dict[str, Any]]:
    """
    Calculate Level 2 (L2) sub-periods for a specific L1 period.
    Handles 'Loosing of the Bond' (LB / 跳宫/解脱) when L2 exceeds 1 full cycle of 12 signs.
    """
    subperiods = []
    l1_start_idx = sign_name_index(l1_sign)
    current_idx = l1_start_idx
    
    current_age = l1_start_age
    l1_end_age = l1_start_age + l1_duration
    
    cycle_count = 0
    sign_in_cycle = 0
    
    while current_age < l1_end_age:
        sign = sign_index_name(current_idx)
        # 1 Month = 1/12 year = 0.0833333 years in 360-day year standard
        months_duration = ZR_SIGN_YEARS[sign]
        duration_years = months_duration / 12.0
        
        # Clamp to L1 end age
        if current_age + duration_years > l1_end_age:
            duration_years = l1_end_age - current_age
            
        end_age = current_age + duration_years
        
        is_lb = (cycle_count > 0 and sign_in_cycle == 0)
        
        subperiods.append({
            "level": 2,
            "sign": sign,
            "start_age": round(current_age, 4),
            "end_age": round(end_age, 4),
            "duration_months": months_duration,
            "is_loosing_of_the_bond": is_lb
        })
        
        current_age = end_age
        sign_in_cycle += 1
        
        if sign_in_cycle == 12:
            # Full 12-sign cycle completed -> Trigger Loosing of the Bond (LB)
            # Jump to the sign opposite to the L1 starting sign!
            cycle_count += 1
            sign_in_cycle = 0
            current_idx = (l1_start_idx + 6) % 12
        else:
            current_idx = (current_idx + 1) % 12
            
    return subperiods

def get_current_zr(start_sign: str, age_years: float) -> Dict[str, Any]:
    """Get active L1 and L2 Zodiacal Releasing period at a given age."""
    l1_periods = calc_zr_l1_periods(start_sign, max_years=max(120.0, age_years + 30.0))
    
    active_l1 = None
    for p in l1_periods:
        if p["start_age"] <= age_years < p["end_age"]:
            active_l1 = p
            break
            
    if not active_l1:
        active_l1 = l1_periods[0]
        
    l2_periods = calc_zr_l2_subperiods(active_l1["sign"], active_l1["start_age"], active_l1["duration_years"])
    
    active_l2 = None
    for p2 in l2_periods:
        if p2["start_age"] <= age_years < p2["end_age"]:
            active_l2 = p2
            break
            
    if not active_l2:
        active_l2 = l2_periods[0]
        
    return {
        "l1": active_l1,
        "l2": active_l2
    }
