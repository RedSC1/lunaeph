"""Classical Horary & Electional Astrology: Light Rays, Besiegement, Translation, Collection & Prohibition module.

Implements:
1. Moiety of Orbs (古典星体光芒半径与容许度相加)
2. Besiegement by Light/Aspects (围攻 - 某星受双星相位夹击)
3. Translation of Light (传光 / 光线传递 - 快速星传递能量)
4. Collection of Light (聚光 / 光线汇聚 - 主星吸收多星光芒)
5. Prohibition of Light (阻隔 / 绝光 - 拦截中碍)
"""

from __future__ import annotations
import math
from typing import Dict, Any, List
from ._classical import TRADITIONAL_PLANETS
from ._signs import degrees_to_zodiac

# Classical Orbs of Light (Full Orb in degrees according to Lilly / Bonatti)
PLANETARY_ORBS_OF_LIGHT = {
    "sun": 15.0,       # Half = 7.5°
    "moon": 12.0,      # Half = 6.0°
    "saturn": 9.0,     # Half = 4.5°
    "jupiter": 9.0,    # Half = 4.5°
    "mars": 8.0,       # Half = 4.0°
    "venus": 7.0,      # Half = 3.5°
    "mercury": 7.0,    # Half = 3.5°
    "uranus": 5.0,     # Half = 2.5°
    "neptune": 5.0,    # Half = 2.5°
    "pluto": 5.0,      # Half = 2.5°
    "chiron": 3.0,     # Half = 1.5°
}

PLANET_SYMBOLS = {
    "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀",
    "mars": "♂", "jupiter": "♃", "saturn": "♄",
    "uranus": "♅", "neptune": "♆", "pluto": "♇", "chiron": "⚷"
}

def get_moiety_of_orbs(planet1: str, planet2: str) -> float:
    """
    Calculate Moiety of Orbs (古典双星光芒半径之和 / 2).
    Combined Orb Limit = (Orb1 + Orb2) / 2.0
    """
    p1 = planet1.lower()
    p2 = planet2.lower()
    orb1 = PLANETARY_ORBS_OF_LIGHT.get(p1, 6.0)
    orb2 = PLANETARY_ORBS_OF_LIGHT.get(p2, 6.0)
    return (orb1 + orb2) / 2.0

def get_active_aspects_for_planet(chart_data: Dict[str, Any], target_planet: str, include_modern: bool = False) -> List[Dict[str, Any]]:
    """Find all active classical/modern aspects received by target_planet."""
    planets = chart_data["planets"]
    target_key = target_planet.lower()
    if target_key not in planets:
        return []
        
    t_lon = math.degrees(planets[target_key]["longitude_rad"])
    aspects = []
    
    candidate_keys = list(TRADITIONAL_PLANETS)
    if include_modern:
        candidate_keys.extend(["uranus", "neptune", "pluto", "chiron"])
    
    for other_key in candidate_keys:
        if other_key == target_key or other_key not in planets:
            continue
        o_lon = math.degrees(planets[other_key]["longitude_rad"])
        
        moiety = get_moiety_of_orbs(target_key, other_key)
        diff = abs(t_lon - o_lon) % 360.0
        if diff > 180.0:
            diff = 360.0 - diff
            
        for angle in [0, 60, 90, 120, 180]:
            orb_val = abs(diff - angle)
            if orb_val <= moiety:
                aspects.append({
                    "planet": other_key,
                    "planet_name": planets[other_key]["name"],
                    "symbol": PLANET_SYMBOLS.get(other_key, other_key),
                    "aspect_angle": angle,
                    "orb": round(orb_val, 2)
                })
                break
                
    return aspects

def calc_besiegement(chart_data: Dict[str, Any], include_modern: bool = False) -> List[Dict[str, Any]]:
    """
    Calculate Besiegement by Light/Aspects (光线/相位围攻).
    Occurs when a target planet receives active aspects from two planets simultaneously.
    """
    planets = chart_data["planets"]
    besiegements = []
    
    candidate_targets = list(TRADITIONAL_PLANETS)
    if include_modern:
        candidate_targets.extend(["uranus", "neptune", "pluto", "chiron"])
        
    for p_key in candidate_targets:
        if p_key not in planets:
            continue
        p = planets[p_key]
        p_lon = math.degrees(p["longitude_rad"])
        sign, deg = degrees_to_zodiac(p_lon)
        deg_m = int(round((deg % 1) * 60))
        deg_d = int(deg)
        pos_str = f"{sign} {deg_d}°{deg_m:02d}'"
        
        aspects = get_active_aspects_for_planet(chart_data, p_key, include_modern=include_modern)
        
        # Pairs of aspects form a besiegement
        n = len(aspects)
        for i in range(n):
            for j in range(i + 1, n):
                a1 = aspects[i]
                a2 = aspects[j]
                
                besiegements.append({
                    "target_planet": p["name"],
                    "target_symbol": PLANET_SYMBOLS.get(p_key, p_key),
                    "target_pos": pos_str,
                    "planet_a": a1["planet_name"],
                    "symbol_a": a1["symbol"],
                    "aspect_a_deg": a1["aspect_angle"],
                    "planet_b": a2["planet_name"],
                    "symbol_b": a2["symbol"],
                    "aspect_b_deg": a2["aspect_angle"],
                    "description": f"{PLANET_SYMBOLS.get(p_key, p_key)}({pos_str}) 被 {a1['symbol']}({a1['aspect_angle']}°)和 {a2['symbol']}({a2['aspect_angle']}°)围攻"
                })
                
    return besiegements

def calc_translation_of_light(chart_data: Dict[str, Any], include_modern: bool = False) -> List[Dict[str, Any]]:
    """
    Calculate Translation of Light (传光 / 光线传递).
    Occurs when a fast-moving planet (e.g. Moon) separates from aspecting Planet A
    and applies immediately to aspect Planet B, transferring energy between them.
    """
    planets = chart_data["planets"]
    translations = []
    
    candidate_others = list(TRADITIONAL_PLANETS)
    if include_modern:
        candidate_others.extend(["uranus", "neptune", "pluto", "chiron"])
    
    for fast_key in ["moon", "mercury", "venus"]:
        if fast_key not in planets:
            continue
        fast_p = planets[fast_key]
        fast_lon = math.degrees(fast_p["longitude_rad"])
        
        separating_from = []
        applying_to = []
        
        for other_key in candidate_others:
            if other_key == fast_key or other_key not in planets:
                continue
            other_p = planets[other_key]
            other_lon = math.degrees(other_p["longitude_rad"])
            
            moiety = get_moiety_of_orbs(fast_key, other_key)
            diff = (fast_lon - other_lon) % 360.0
            
            for target_angle in [0, 60, 90, 120, 180]:
                angle_diff = abs(diff - target_angle)
                if angle_diff > 180.0:
                    angle_diff = 360.0 - angle_diff
                    
                if angle_diff <= moiety:
                    if diff > target_angle:
                        separating_from.append({"planet": other_key, "symbol": PLANET_SYMBOLS.get(other_key, other_key), "aspect": target_angle})
                    else:
                        applying_to.append({"planet": other_key, "symbol": PLANET_SYMBOLS.get(other_key, other_key), "aspect": target_angle})

        for sep in separating_from:
            for app in applying_to:
                if sep["planet"] != app["planet"]:
                    translations.append({
                        "translator": fast_p["name"],
                        "translator_symbol": PLANET_SYMBOLS.get(fast_key, fast_key),
                        "from_planet": sep["planet"].capitalize(),
                        "from_symbol": sep["symbol"],
                        "to_planet": app["planet"].capitalize(),
                        "to_symbol": app["symbol"],
                        "description": f"{PLANET_SYMBOLS.get(fast_key, fast_key)} 把光线从 {sep['symbol']} 向 {app['symbol']} 传递"
                    })
                    
    return translations

def calc_collection_of_light(chart_data: Dict[str, Any], include_modern: bool = False) -> List[Dict[str, Any]]:
    """
    Calculate Collection of Light (聚光 / 光线汇聚/收集).
    Occurs when a planet collects light/aspects from multiple other planets.
    """
    planets = chart_data["planets"]
    collections = []
    
    candidate_collectors = ["sun", "jupiter", "saturn", "mars"]
    if include_modern:
        candidate_collectors.extend(["uranus", "neptune", "pluto"])
        
    for collector_key in candidate_collectors:
        if collector_key not in planets:
            continue
        c_p = planets[collector_key]
        aspects = get_active_aspects_for_planet(chart_data, collector_key, include_modern=include_modern)
        
        if len(aspects) >= 2:
            sources = [a["symbol"] for a in aspects]
            sources_str = "、".join(sources)
            collections.append({
                "collector": c_p["name"],
                "collector_symbol": PLANET_SYMBOLS.get(collector_key, collector_key),
                "source_symbols": sources,
                "description": f"{PLANET_SYMBOLS.get(collector_key, collector_key)} 从 {sources_str} 收集光线"
            })

    return collections

def calc_prohibition(chart_data: Dict[str, Any], include_modern: bool = False) -> List[Dict[str, Any]]:
    """
    Calculate Prohibition / Interception (阻隔 / 绝光).
    Occurs when two planets apply to aspect each other, but a heavier/malefic planet intervenes.
    """
    planets = chart_data["planets"]
    prohibitions = []
    
    # Sun & Mercury conjunction checked for Saturn prohibition
    if "sun" in planets and "mercury" in planets and "saturn" in planets:
        sun_lon = math.degrees(planets["sun"]["longitude_rad"])
        merc_lon = math.degrees(planets["mercury"]["longitude_rad"])
        sat_lon = math.degrees(planets["saturn"]["longitude_rad"])
        
        moiety_sm = get_moiety_of_orbs("sun", "mercury")
        diff_sm = abs(sun_lon - merc_lon) % 360.0
        if diff_sm > 180.0:
            diff_sm = 360.0 - diff_sm
            
        if diff_sm <= moiety_sm: # Sun & Mercury in aspect
            # Saturn forms square to Sun
            moiety_ss = get_moiety_of_orbs("sun", "saturn")
            diff_ss = abs(sun_lon - sat_lon) % 360.0
            if diff_ss > 180.0:
                diff_ss = 360.0 - diff_ss
            if abs(diff_ss - 90.0) <= moiety_ss:
                prohibitions.append({
                    "planet_a": "Sun",
                    "symbol_a": "☉",
                    "planet_b": "Mercury",
                    "symbol_b": "☿",
                    "intervener": "Saturn",
                    "symbol_intervener": "♄",
                    "description": "☉ 与 ☿ 的相位，预计将被 ♄ 阻隔"
                })
                
    return prohibitions
