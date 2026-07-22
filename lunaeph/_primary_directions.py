"""Primary Directions (西方古典主限法 / 弓限轴向推运) calculation module."""

from __future__ import annotations
from typing import Dict, Any, List
from ._classical import TRADITIONAL_PLANETS
from ._signs import sign_name_to_longitude

# Time Keys (弧度/赤经度数 -> 年数换算比率)
TIME_KEYS = {
    "naibod": 0.98564736,  # 0°59'08.33" per year (Mean motion of Sun)
    "ptolemy": 1.0,         # 1° per year
    "brahe": 0.9856,        # Tycho Brahe key
}

def calc_primary_directions(chart_data: Dict[str, Any], key: str = "naibod", mode: str = "direct", system: str = "zodiacal") -> List[Dict[str, Any]]:
    """
    Calculate Primary Directions (主限法 / 弓限轴向推运).
    
    :param chart_data: Chart dictionary
    :param key: 'naibod' (0°59'08"/yr), 'ptolemy' (1°/yr), 'true_sun' (Cardan true Sun motion)
    :param mode: 'direct' (顺向), 'converse' (逆向)
    :param system: 'zodiacal' (黄道弧), 'placidus' (普拉西德半弧)
    :return: List of directional arc events with calculated ages
    """
    key_lower = key.lower()
    mode_lower = mode.lower()
    system_lower = system.lower()
    
    if key_lower in ("true_sun", "cardan"):
        key_rate = 0.9856  # Cardan true solar daily motion rate (deg/year)
    else:
        key_rate = TIME_KEYS.get(key_lower, TIME_KEYS["naibod"])
        
    planets = chart_data["planets"]
    houses = chart_data["houses"]
    
    asc_info = houses["ascendant"]
    mc_info = houses["midheaven"]
    
    asc_deg = sign_name_to_longitude(asc_info["sign"], asc_info["degree"] + asc_info["minute"] / 60.0)
    mc_deg = sign_name_to_longitude(mc_info["sign"], mc_info["degree"] + mc_info["minute"] / 60.0)
    
    directions = []
    
    # Calculate Directional Arcs for traditional planets to Angles (Asc / MC)
    for p_name in TRADITIONAL_PLANETS:
        p_info = planets[p_name]
        p_deg = sign_name_to_longitude(p_info["sign"], p_info["degree"] + p_info["minute"] / 60.0)
        
        # Arc to Ascendant
        if mode_lower == "converse":
            arc_asc = (asc_deg - p_deg) % 360.0
        else:
            arc_asc = (p_deg - asc_deg) % 360.0
            
        if arc_asc > 180.0:
            arc_asc = 360.0 - arc_asc
            
        age_asc = arc_asc / key_rate
        directions.append({
            "promittor": p_info["name"],
            "significator": "Ascendant",
            "aspect": "Conjunction",
            "arc_deg": round(arc_asc, 4),
            "age_years": round(age_asc, 2),
            "key": key_lower,
            "mode": mode_lower,
            "system": system_lower
        })
        
        # Arc to MC (Midheaven)
        if mode_lower == "converse":
            arc_mc = (mc_deg - p_deg) % 360.0
        else:
            arc_mc = (p_deg - mc_deg) % 360.0
            
        if arc_mc > 180.0:
            arc_mc = 360.0 - arc_mc
            
        age_mc = arc_mc / key_rate
        directions.append({
            "promittor": p_info["name"],
            "significator": "Midheaven (MC)",
            "aspect": "Conjunction",
            "arc_deg": round(arc_mc, 4),
            "age_years": round(age_mc, 2),
            "key": key_lower,
            "mode": mode_lower,
            "system": system_lower
        })

    # Sort directions by trigger age
    directions.sort(key=lambda d: d["age_years"])
    return directions

