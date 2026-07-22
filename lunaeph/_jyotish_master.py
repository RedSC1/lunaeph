"""Master Vedic Astrology (Jyotish) module: Upagrahas, KP Sub-Lords, Graha Maitri, Ashtakavarga."""

from __future__ import annotations
import math
from typing import Dict, Any, List
from ._signs import SIGN_NAMES, degrees_to_zodiac

# 9-planet Vimshottari order & years for KP Sub-lord calculation
KP_ORDER = ["ketu", "venus", "sun", "moon", "mars", "rahu", "jupiter", "saturn", "mercury"]
KP_YEARS = [7.0, 20.0, 6.0, 10.0, 7.0, 18.0, 16.0, 19.0, 17.0] # Total 120

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

# Naisargika (Natural) Planetary Friendships in Jyotish
NAISARGIKA_FRIENDS = {
    "sun": {"friends": ["moon", "mars", "jupiter"], "enemies": ["venus", "saturn"], "neutrals": ["mercury"]},
    "moon": {"friends": ["sun", "mercury"], "enemies": [], "neutrals": ["mars", "jupiter", "venus", "saturn"]},
    "mars": {"friends": ["sun", "moon", "jupiter"], "enemies": ["mercury"], "neutrals": ["venus", "saturn"]},
    "mercury": {"friends": ["sun", "venus"], "enemies": ["moon"], "neutrals": ["mars", "jupiter", "saturn"]},
    "jupiter": {"friends": ["sun", "moon", "mars"], "enemies": ["mercury", "venus"], "neutrals": ["saturn"]},
    "venus": {"friends": ["mercury", "saturn"], "enemies": ["sun", "moon"], "neutrals": ["mars", "jupiter"]},
    "saturn": {"friends": ["mercury", "venus"], "enemies": ["sun", "moon", "mars"], "neutrals": ["jupiter"]}
}

def calc_upagrahas(sun_sidereal_lon_deg: float) -> Dict[str, Any]:
    """Calculate the 5 Sun-based Upagrahas (五大副星/虚星)."""
    sun_deg = sun_sidereal_lon_deg % 360.0
    
    dhuma = (sun_deg + 133.33333333333334) % 360.0
    vyatipata = (360.0 - dhuma) % 360.0
    parivesha = (vyatipata + 180.0) % 360.0
    indrachapa = (360.0 - parivesha) % 360.0
    upaketu = (indrachapa + 16.666666666666668) % 360.0
    
    def _fmt(deg):
        sign, d = degrees_to_zodiac(deg)
        return {"longitude_deg": round(deg, 4), "sign": sign, "degree_in_sign": round(d, 4)}
        
    return {
        "dhuma": _fmt(dhuma),          # 烟星
        "vyatipata": _fmt(vyatipata),  # 倒悬星
        "parivesha": _fmt(parivesha),  # 晕星
        "indrachapa": _fmt(indrachapa),# 彩虹星
        "upaketu": _fmt(upaketu)       # 副计都
    }

def calc_kp_sublord(sidereal_lon_deg: float) -> Dict[str, Any]:
    """
    Calculate KP System Star-Lord and Sub-Lord (KP 派星主与副主星).
    Each 13°20' Nakshatra is divided into 9 unequal sub-lords proportional to Vimshottari Dasha years.
    """
    deg = sidereal_lon_deg % 360.0
    nak_idx = int(deg // 13.333333333333334)
    nak_name = NAKSHATRA_NAMES[nak_idx]
    star_lord = KP_ORDER[nak_idx % 9]
    
    # Position inside the Nakshatra (0 to 13.3333°)
    nak_deg = deg % 13.333333333333334
    
    # Sub-lord calculation
    star_lord_idx = KP_ORDER.index(star_lord)
    sub_start_deg = 0.0
    sub_lord = star_lord
    
    for i in range(9):
        curr_lord = KP_ORDER[(star_lord_idx + i) % 9]
        # Portion of 13.3333° = 13.3333 * (years / 120)
        span = 13.333333333333334 * (DASHA_YEARS_MAP(curr_lord) / 120.0)
        if sub_start_deg <= nak_deg < (sub_start_deg + span):
            sub_lord = curr_lord
            break
        sub_start_deg += span
        
    return {
        "nakshatra": nak_name,
        "star_lord": star_lord,
        "sub_lord": sub_lord
    }

def DASHA_YEARS_MAP(lord: str) -> float:
    idx = KP_ORDER.index(lord)
    return KP_YEARS[idx]

def calc_panchadha_maitri(chart_data: Dict[str, Any], ayanamsha_mode: str = "lahiri") -> Dict[str, Any]:
    """
    Calculate Panchadha Maitri (五分法印占复合敌友关系).
    Combines Naisargika (Natural) and Tatkalika (Temporary) friendships.
    """
    from ._ayanamsha import calc_ayanamsha_deg
    
    jd_tt = chart_data["jd_tt"]
    ayan = calc_ayanamsha_deg(jd_tt, ayanamsha_mode)
    planets = chart_data["planets"]
    houses = chart_data["houses"]
    asc_deg = (houses["ascendant"]["degree"] + houses["ascendant"]["minute"] / 60.0) + ({"Aries":0, "Taurus":30, "Gemini":60, "Cancer":90, "Leo":120, "Virgo":150, "Libra":180, "Scorpio":210, "Sagittarius":240, "Capricorn":270, "Aquarius":300, "Pisces":330}[houses["ascendant"]["sign"]])
    sid_asc_deg = (asc_deg - ayan) % 360.0
    asc_sign_idx = int(sid_asc_deg // 30.0)
    
    # Get Whole Sign house for each planet
    planet_houses = {}
    for p in NAISARGIKA_FRIENDS.keys():
        if p in planets:
            trop_lon = math.degrees(planets[p]["longitude_rad"])
            sid_lon = (trop_lon - ayan) % 360.0
            p_sign_idx = int(sid_lon // 30.0)
            h = ((p_sign_idx - asc_sign_idx) % 12) + 1
            planet_houses[p] = h

    maitri_matrix = {}
    
    for p1 in NAISARGIKA_FRIENDS.keys():
        if p1 not in planet_houses:
            continue
        maitri_matrix[p1] = {}
        h1 = planet_houses[p1]
        
        for p2 in NAISARGIKA_FRIENDS.keys():
            if p1 == p2 or p2 not in planet_houses:
                continue
            h2 = planet_houses[p2]
            
            # Temporary friendship: 2, 3, 4, 10, 11, 12 houses away = Friend (+1), else Enemy (-1)
            diff = ((h2 - h1) % 12)
            if diff in (1, 2, 3, 9, 10, 11): # 2nd, 3rd, 4th, 10th, 11th, 12th houses (1-indexed difference: 1,2,3, 9,10,11)
                tatkalika = 1 # Friend
            else:
                tatkalika = -1 # Enemy
                
            # Natural friendship
            nat_info = NAISARGIKA_FRIENDS[p1]
            if p2 in nat_info["friends"]:
                naisargika = 1
            elif p2 in nat_info["enemies"]:
                naisargika = -1
            else:
                naisargika = 0 # Neutral
                
            combined = naisargika + tatkalika
            if combined == 2:
                status = "Ati Mitra (Great Friend)"
            elif combined == 1:
                status = "Mitra (Friend)"
            elif combined == 0:
                status = "Sama (Neutral)"
            elif combined == -1:
                status = "Shatru (Enemy)"
            else:
                status = "Ati Shatru (Great Enemy)"
                
            maitri_matrix[p1][p2] = status
            
    return maitri_matrix
