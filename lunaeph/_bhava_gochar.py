"""Vedic Bhava Chalit (宫位盘) and Gochar/Transit (行运/Sade Sati) calculation module."""

from __future__ import annotations
import math
from typing import Dict, Any, List
from ._signs import SIGN_NAMES, sign_name_index, sign_index_name, sign_name_to_longitude

def calc_bhava_chalit(chart_data: Dict[str, Any], ayanamsha_mode: str = "lahiri") -> Dict[str, Any]:
    """
    Calculate Bhava Chalit (印占宫位调整盘).
    Determines if a planet shifts to an adjacent house (Bhava) compared to its Rashi (sign) house.
    """
    from ._ayanamsha import calc_ayanamsha_deg
    
    jd_tt = chart_data["jd_tt"]
    ayan = calc_ayanamsha_deg(jd_tt, ayanamsha_mode)
    
    planets = chart_data["planets"]
    houses = chart_data["houses"]
    asc_deg = sign_name_to_longitude(houses["ascendant"]["sign"], houses["ascendant"]["degree"] + houses["ascendant"]["minute"] / 60.0)
    sid_asc_deg = (asc_deg - ayan) % 360.0
    
    bhava_results = {}
    
    for k, p in planets.items():
        trop_lon = math.degrees(p["longitude_rad"])
        sid_lon = (trop_lon - ayan) % 360.0
        
        # Rashi house (Whole Sign from Sidereal Ascendant)
        asc_sign_idx = int(sid_asc_deg // 30.0)
        planet_sign_idx = int(sid_lon // 30.0)
        rashi_house = ((planet_sign_idx - asc_sign_idx) % 12) + 1
        
        # Bhava Chalit house (Cusp mid-point division)
        # Each Bhava spans 15° before and 15° after the exact Ascendant degree
        bhava_offset = (sid_lon - (sid_asc_deg - 15.0)) % 360.0
        bhava_house = int(bhava_offset // 30.0) + 1
        
        shifted = (rashi_house != bhava_house)
        
        bhava_results[k] = {
            "name": p["name"],
            "rashi_house": rashi_house,
            "bhava_house": bhava_house,
            "shifted": shifted
        }
        
    return bhava_results

def calc_sade_sati(natal_moon_sidereal_sign: str, transit_saturn_sidereal_sign: str) -> Dict[str, Any]:
    """
    Check Indian Sade Sati (土星萨德萨蒂 - 7.5年大难/考验运).
    Active when transit Saturn is in the 12th, 1st, or 2nd house from natal Moon.
    """
    moon_idx = sign_name_index(natal_moon_sidereal_sign)
    saturn_idx = sign_name_index(transit_saturn_sidereal_sign)
    
    diff = (saturn_idx - moon_idx) % 12
    
    if diff == 11:  # 12th house from Moon
        return {"is_active": True, "phase": "Phase 1 (Rising / 12th House)", "description": "Saturn transiting 12th house from Moon (Expense & Mental stress)"}
    elif diff == 0:  # 1st house (Conjunction with Moon)
        return {"is_active": True, "phase": "Phase 2 (Peak / 1st House)", "description": "Saturn transiting over natal Moon (Core Peak Transformation)"}
    elif diff == 1:  # 2nd house from Moon
        return {"is_active": True, "phase": "Phase 3 (Setting / 2nd House)", "description": "Saturn transiting 2nd house from Moon (Family & Financial realignment)"}
    else:
        return {"is_active": False, "phase": "None", "description": "No Sade Sati active"}
