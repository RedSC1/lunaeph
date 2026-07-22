"""Sarvashtakavarga (八分点/行运力量评估) calculation module.

Classical Parashari Ashtakavarga bindu rules for 7 planets + Lagna.
"""

from __future__ import annotations
import math
from typing import Dict, Any, List
from ._signs import sign_name_to_longitude

# Benefic point (bindu) positions FROM each contributor for each planet's Ashtakavarga.
# Key: planet whose BAV we are computing. Value: dict of contributor -> list of houses (1-12) that give bindu.

_BAV_RULES = {
    "sun": {
        "sun": [1,2,4,7,8,9,10,11],
        "moon": [3,6,10,11],
        "mars": [1,2,4,7,8,9,10,11],
        "mercury": [3,5,6,9,10,11,12],
        "jupiter": [5,6,9,11],
        "venus": [6,7,12],
        "saturn": [1,2,4,7,8,9,10,11],
        "lagna": [3,4,6,10,11,12],
    },
    "moon": {
        "sun": [3,6,7,8,10,11],
        "moon": [1,3,6,7,10,11],
        "mars": [2,3,5,6,9,10,11],
        "mercury": [1,3,4,5,7,8,10,11],
        "jupiter": [1,4,7,8,10,11,12],
        "venus": [3,4,5,7,9,10,11],
        "saturn": [3,5,6,11],
        "lagna": [3,6,10,11],
    },
    "mars": {
        "sun": [3,5,6,10,11],
        "moon": [3,6,11],
        "mars": [1,2,4,7,8,10,11],
        "mercury": [3,5,6,11],
        "jupiter": [6,10,11,12],
        "venus": [6,8,11,12],
        "saturn": [1,4,7,8,9,10,11],
        "lagna": [1,3,6,10,11],
    },
    "mercury": {
        "sun": [5,6,9,11,12],
        "moon": [2,4,6,8,10,11],
        "mars": [1,2,4,7,8,9,10,11],
        "mercury": [1,3,5,6,9,10,11,12],
        "jupiter": [6,8,11,12],
        "venus": [1,2,3,4,5,8,9,11],
        "saturn": [1,2,4,7,8,9,10,11],
        "lagna": [1,2,4,6,8,10,11],
    },
    "jupiter": {
        "sun": [1,2,3,4,7,8,9,10,11],
        "moon": [2,5,7,9,11],
        "mars": [1,2,4,7,8,10,11],
        "mercury": [1,2,4,5,6,9,10,11],
        "jupiter": [1,2,3,4,7,8,10,11],
        "venus": [2,5,6,9,10,11],
        "saturn": [3,5,6,12],
        "lagna": [1,2,4,5,6,7,9,10,11],
    },
    "venus": {
        "sun": [8,11,12],
        "moon": [1,2,3,4,5,8,9,11,12],
        "mars": [3,5,6,9,11,12],
        "mercury": [3,5,6,9,11],
        "jupiter": [5,8,9,10,11],
        "venus": [1,2,3,4,5,8,9,10,11],
        "saturn": [3,4,5,8,9,10,11],
        "lagna": [1,2,3,4,5,8,9,11],
    },
    "saturn": {
        "sun": [1,2,4,7,8,10,11],
        "moon": [3,6,11],
        "mars": [3,5,6,10,11,12],
        "mercury": [6,8,9,10,11,12],
        "jupiter": [5,6,11,12],
        "venus": [6,11,12],
        "saturn": [3,5,6,11],
        "lagna": [1,3,4,6,10,11],
    },
}

def calc_ashtakavarga(chart_data: Dict[str, Any], ayanamsha_mode: str = "lahiri") -> Dict[str, Any]:
    """
    Calculate Sarvashtakavarga (八分点力量表).

    Returns Bhinnashtakavarga (individual planet bindu tables) and
    Sarvashtakavarga (cumulative 12-sign bindu totals, max 337).
    """
    from ._ayanamsha import calc_ayanamsha_deg

    jd_tt = chart_data["jd_tt"]
    ayan = calc_ayanamsha_deg(jd_tt, ayanamsha_mode)
    planets = chart_data["planets"]
    houses = chart_data["houses"]

    # Sidereal sign index for each contributor (0-11)
    def _sid_sign_idx(trop_lon_rad: float) -> int:
        sid_deg = (math.degrees(trop_lon_rad) - ayan) % 360.0
        return int(sid_deg // 30.0)

    contrib_signs = {}
    for pk in ["sun","moon","mars","mercury","jupiter","venus","saturn"]:
        if pk in planets:
            contrib_signs[pk] = _sid_sign_idx(planets[pk]["longitude_rad"])

    # Lagna sidereal sign index
    asc_deg = sign_name_to_longitude(houses["ascendant"]["sign"], houses["ascendant"]["degree"] + houses["ascendant"]["minute"]/60.0)
    asc_sid = (asc_deg - ayan) % 360.0
    contrib_signs["lagna"] = int(asc_sid // 30.0)

    bav = {}  # Bhinnashtakavarga
    sarva = [0] * 12  # Sarvashtakavarga totals

    planet_keys = ["sun","moon","mars","mercury","jupiter","venus","saturn"]

    for pk in planet_keys:
        rules = _BAV_RULES[pk]
        sign_bindus = [0] * 12

        for contributor, benefic_houses in rules.items():
            if contributor not in contrib_signs:
                continue
            c_sign = contrib_signs[contributor]
            benefic_set = set(benefic_houses)
            for sign_idx in range(12):
                # House distance from contributor to this sign (1-indexed)
                house_dist = ((sign_idx - c_sign) % 12) + 1
                if house_dist in benefic_set:
                    sign_bindus[sign_idx] += 1

        bav[pk] = sign_bindus
        for i in range(12):
            sarva[i] += sign_bindus[i]

    total = sum(sarva)

    return {
        "bhinnashtakavarga": bav,
        "sarvashtakavarga": sarva,
        "total_bindus": total,
    }
