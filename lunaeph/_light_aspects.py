"""Classical Horary & Electional Astrology: Light Rays, Translation & Collection of Light module.

Implements:
1. Moiety of Orbs (古典星体光芒半径与容许度相加)
2. Translation of Light (传光 / 光线传递 - 快速星传递能量)
3. Collection of Light (聚光 / 光线汇聚 - 慢速星吸收能量)
4. Astronomical Light-Time & Light Deflection summary
"""

from __future__ import annotations
import math
from typing import Dict, Any, List
from ._classical import TRADITIONAL_PLANETS

# Classical Orbs of Light (Full Orb in degrees according to Lilly / Bonatti)
PLANETARY_ORBS_OF_LIGHT = {
    "sun": 15.0,       # Half = 7.5°
    "moon": 12.0,      # Half = 6.0°
    "saturn": 9.0,     # Half = 4.5°
    "jupiter": 9.0,    # Half = 4.5°
    "mars": 8.0,       # Half = 4.0°
    "venus": 7.0,      # Half = 3.5°
    "mercury": 7.0,    # Half = 3.5°
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

def calc_translation_of_light(chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Calculate Translation of Light (传光 / 光线传递).
    Occurs when a fast-moving planet (e.g. Moon) separates from aspecting Planet A
    and applies immediately to aspect Planet B, transferring the light/energy between them.
    """
    planets = chart_data["planets"]
    rates = chart_data.get("_body_rates", {})
    
    translations = []
    
    # Check Moon and Mercury as typical light translators
    for fast_key in ["moon", "mercury", "venus"]:
        if fast_key not in planets:
            continue
        fast_p = planets[fast_key]
        fast_lon = math.degrees(fast_p["longitude_rad"])
        
        separating_from = []
        applying_to = []
        
        for other_key in TRADITIONAL_PLANETS:
            if other_key == fast_key or other_key not in planets:
                continue
            other_p = planets[other_key]
            other_lon = math.degrees(other_p["longitude_rad"])
            
            moiety = get_moiety_of_orbs(fast_key, other_key)
            diff = (fast_lon - other_lon) % 360.0
            
            # Check major aspects (0, 60, 90, 120, 180)
            for target_angle in [0, 60, 90, 120, 180]:
                angle_diff = abs(diff - target_angle)
                if angle_diff > 180.0:
                    angle_diff = 360.0 - angle_diff
                    
                if angle_diff <= moiety:
                    # Determine if separating or applying
                    if diff > target_angle:
                        separating_from.append({"planet": other_key, "aspect": target_angle, "orb": round(angle_diff, 2)})
                    else:
                        applying_to.append({"planet": other_key, "aspect": target_angle, "orb": round(angle_diff, 2)})

        for sep in separating_from:
            for app in applying_to:
                if sep["planet"] != app["planet"]:
                    translations.append({
                        "translator": fast_p["name"],
                        "from_planet": sep["planet"].capitalize(),
                        "from_aspect_deg": sep["aspect"],
                        "to_planet": app["planet"].capitalize(),
                        "to_aspect_deg": app["aspect"],
                        "description": f"{fast_p['name']} translates light from {sep['planet'].capitalize()} to {app['planet'].capitalize()}"
                    })
                    
    return translations

def calc_collection_of_light(chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Calculate Collection of Light (聚光 / 光线汇聚).
    Occurs when two faster planets both apply to aspect a slower, heavier planet (Collector).
    """
    planets = chart_data["planets"]
    collections = []
    
    # Heavy slow collectors: Saturn, Jupiter, Mars
    for collector_key in ["saturn", "jupiter", "mars"]:
        if collector_key not in planets:
            continue
        c_p = planets[collector_key]
        c_lon = math.degrees(c_p["longitude_rad"])
        
        applying_planets = []
        for fast_key in ["sun", "moon", "mercury", "venus", "mars"]:
            if fast_key == collector_key or fast_key not in planets:
                continue
            f_p = planets[fast_key]
            f_lon = math.degrees(f_p["longitude_rad"])
            
            moiety = get_moiety_of_orbs(fast_key, collector_key)
            diff = (c_lon - f_lon) % 360.0
            if diff > 180.0:
                diff = 360.0 - diff
                
            for target_angle in [0, 60, 90, 120, 180]:
                orb_val = abs(diff - target_angle)
                if orb_val <= moiety:
                    applying_planets.append({"planet": f_p["name"], "aspect": target_angle, "orb": round(orb_val, 2)})

        if len(applying_planets) >= 2:
            p1, p2 = applying_planets[0], applying_planets[1]
            collections.append({
                "collector": c_p["name"],
                "planet_a": p1["planet"],
                "planet_b": p2["planet"],
                "description": f"{c_p['name']} collects light from both {p1['planet']} and {p2['planet']}"
            })

    return collections
