"""Jaimini Chara Karakas & Huber Age Point System module."""

from __future__ import annotations
import math
from typing import Dict, Any, List
from ._classical import TRADITIONAL_PLANETS

KARAKA_NAMES_7 = [
    ("Atmakaraka", "AK", "Soul & Core Destiny (灵魂星)"),
    ("Amatyakaraka", "AmK", "Career & Profession (事业星)"),
    ("Bhratrukaraka", "BK", "Siblings & Courage (兄弟星)"),
    ("Matrukaraka", "MK", "Mother & Emotional Comfort (母亲星)"),
    ("Pitrukaraka", "PiK", "Father & Authority (父亲星)"),
    ("Putrakaraka", "PK", "Children & Creative Genius (子女星)"),
    ("Jnatikaraka", "GK", "Obstacles, Relatives & Competition (阻碍星)"),
]

KARAKA_NAMES_8 = [
    ("Atmakaraka", "AK", "Soul & Core Destiny (灵魂星)"),
    ("Amatyakaraka", "AmK", "Career & Profession (事业星)"),
    ("Bhratrukaraka", "BK", "Siblings & Courage (兄弟星)"),
    ("Matrukaraka", "MK", "Mother & Emotional Comfort (母亲星)"),
    ("Pitrukaraka", "PiK", "Father & Lineage (父亲星)"),
    ("Putrakaraka", "PK", "Children & Creative Genius (子女星)"),
    ("Jnatikaraka", "GK", "Obstacles, Relatives & Competition (阻碍星)"),
    ("Darakaraka", "DK", "Spouse & Life Partner (伴侣星)"),
]

def calc_jaimini_chara_karakas(chart_data: Dict[str, Any], scheme: str = "7_karaka", ayanamsha_mode: str = "lahiri") -> Dict[str, Any]:
    """
    Calculate Jaimini Chara Karakas (贾伊米尼动态生命星系).
    
    :param chart_data: Chart dictionary
    :param scheme: '7_karaka' (classic 7 planets) or '8_karaka' (includes Rahu)
    :param ayanamsha_mode: Sidereal Ayanamsha mode ('lahiri', 'true_chitra', etc.)
    """
    from ._ayanamsha import calc_ayanamsha_deg
    
    jd_tt = chart_data["jd_tt"]
    ayan = calc_ayanamsha_deg(jd_tt, ayanamsha_mode)
    planets = chart_data["planets"]
    
    scheme_lower = scheme.lower()
    candidate_keys = list(TRADITIONAL_PLANETS)
    if scheme_lower in ("8_karaka", "8"):
        candidate_keys.append("north_node") # Rahu included in 8-karaka scheme
        
    planet_degs = []
    for k in candidate_keys:
        if k in planets:
            trop_lon = math.degrees(planets[k]["longitude_rad"])
            sid_lon = (trop_lon - ayan) % 360.0
            deg_in_sign = sid_lon % 30.0
            planet_degs.append((k, planets[k]["name"], deg_in_sign))
            
    # Sort planets by highest degree within sign
    planet_degs.sort(key=lambda item: item[2], reverse=True)
    
    karaka_list = KARAKA_NAMES_8 if scheme_lower in ("8_karaka", "8") else KARAKA_NAMES_7
    
    results = {}
    for i, (full_name, abbrev, desc) in enumerate(karaka_list):
        if i < len(planet_degs):
            key, name, deg = planet_degs[i]
            results[abbrev] = {
                "karaka": full_name,
                "abbrev": abbrev,
                "description": desc,
                "planet_key": key,
                "planet_name": name,
                "degree_in_sign": round(deg, 4)
            }
            
    return {
        "scheme": scheme_lower,
        "ayanamsha_mode": ayanamsha_mode,
        "karakas": results
    }

def calc_huber_age_point(chart_data: Dict[str, Any], age_years: float) -> Dict[str, Any]:
    """
    Calculate Huber School Age Point (胡伯心理学派 6年/宫 年龄点推运).
    
    Age 0 = Ascendant (Cusp 1)
    Age 6 = Cusp 2
    Age 12 = Cusp 3
    Age 18 = IC (Cusp 4)
    Age 36 = Descendant (Cusp 7)
    Age 54 = MC (Cusp 10)
    Age 72 = Ascendant (Full 72-year lifecycle)
    """
    houses = chart_data["houses"]
    asc_deg = (houses["ascendant"]["degree"] + houses["ascendant"]["minute"] / 60.0) + ({"Aries":0, "Taurus":30, "Gemini":60, "Cancer":90, "Leo":120, "Virgo":150, "Libra":180, "Scorpio":210, "Sagittarius":240, "Capricorn":270, "Aquarius":300, "Pisces":330}[houses["ascendant"]["sign"]])
    
    # 6 years per house (Total 72 years for 12 houses)
    cycle_age = age_years % 72.0
    house_index = int(cycle_age // 6.0) # 0 to 11
    house_progress = (cycle_age % 6.0) / 6.0 # 0.0 to 1.0
    
    active_house = house_index + 1
    
    # Calculate exact Age Point ecliptic longitude
    ap_lon_deg = (asc_deg + (cycle_age / 72.0) * 360.0) % 360.0
    from ._signs import degrees_to_zodiac
    sign, deg_in_sign = degrees_to_zodiac(ap_lon_deg)
    
    return {
        "age_years": age_years,
        "active_house": active_house,
        "house_progress_pct": round(house_progress * 100.0, 2),
        "age_point_longitude_deg": round(ap_lon_deg, 4),
        "sign": sign,
        "degree_in_sign": round(deg_in_sign, 4)
    }
