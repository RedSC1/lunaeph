"""Jaimini Arudha Padas (虚象宫/映射宫位) calculation module."""

from __future__ import annotations
import math
from typing import Dict, Any
from ._signs import SIGN_NAMES, sign_name_to_longitude, sign_name_index

# Traditional 7-planet sign lordship
_SIGN_LORDS = {
    "Aries": "mars", "Taurus": "venus", "Gemini": "mercury", "Cancer": "moon",
    "Leo": "sun", "Virgo": "mercury", "Libra": "venus", "Scorpio": "mars",
    "Sagittarius": "jupiter", "Capricorn": "saturn", "Aquarius": "saturn", "Pisces": "jupiter",
}

def calc_arudha_padas(chart_data: Dict[str, Any], ayanamsha_mode: str = "lahiri") -> Dict[str, Any]:
    """
    Calculate Jaimini Arudha Padas (贾伊米尼虚象宫/映射宫位) for all 12 houses.

    Algorithm:
    1. Identify the sign of each house (Whole Sign from sidereal Ascendant)
    2. Find the lord of that sign
    3. Count signs from house to the lord's sign (distance D)
    4. Count D signs forward from the lord's sign -> Arudha Pada sign
    5. Exception: If Arudha = house sign itself -> use 10th from house
                  If Arudha = 7th from house -> use 4th from house
    """
    from ._ayanamsha import calc_ayanamsha_deg

    jd_tt = chart_data["jd_tt"]
    ayan = calc_ayanamsha_deg(jd_tt, ayanamsha_mode)
    planets = chart_data["planets"]
    houses = chart_data["houses"]

    # Sidereal Ascendant sign index
    asc_deg = sign_name_to_longitude(houses["ascendant"]["sign"], houses["ascendant"]["degree"] + houses["ascendant"]["minute"]/60.0)
    asc_sid = (asc_deg - ayan) % 360.0
    asc_sign_idx = int(asc_sid // 30.0)

    # Sidereal sign index for each planet
    planet_sign_idx = {}
    for pk, pv in planets.items():
        sid_deg = (math.degrees(pv["longitude_rad"]) - ayan) % 360.0
        planet_sign_idx[pk] = int(sid_deg // 30.0)

    results = {}

    for house_num in range(1, 13):
        house_sign_idx = (asc_sign_idx + house_num - 1) % 12
        house_sign = SIGN_NAMES[house_sign_idx]
        lord_key = _SIGN_LORDS[house_sign]

        lord_sign_idx = planet_sign_idx.get(lord_key, 0)
        lord_sign = SIGN_NAMES[lord_sign_idx]

        # Distance from house sign to lord's sign (1-indexed)
        dist = ((lord_sign_idx - house_sign_idx) % 12) + 1

        # Project same distance from lord's sign
        arudha_idx = (lord_sign_idx + dist - 1) % 12
        arudha_sign = SIGN_NAMES[arudha_idx]

        # Exception rules
        if arudha_idx == house_sign_idx:
            # Same as house -> shift to 10th from house
            arudha_idx = (house_sign_idx + 9) % 12
            arudha_sign = SIGN_NAMES[arudha_idx]
        elif (arudha_idx - house_sign_idx) % 12 == 6:
            # 7th from house -> shift to 4th from house
            arudha_idx = (house_sign_idx + 3) % 12
            arudha_sign = SIGN_NAMES[arudha_idx]

        key = f"A{house_num}"
        results[key] = {
            "house": house_num,
            "house_sign": house_sign,
            "lord": lord_key,
            "lord_sign": lord_sign,
            "arudha_sign": arudha_sign,
            "arudha_sign_index": arudha_idx,
        }

    # Convenience aliases
    results["arudha_lagna"] = results["A1"]
    results["upapada"] = results["A12"]

    return results
