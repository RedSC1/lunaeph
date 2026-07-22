"""Vimshottari Dasha (印度 120 年九曜大运) calculation module."""

from __future__ import annotations
from typing import Dict, Any, List
from ._ayanamsha import calc_ayanamsha_deg

# 27 Nakshatras (lunar mansions) names
NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

# Fixed 9-planet Dasha order and years (Total 120 years)
DASHA_ORDER = ["ketu", "venus", "sun", "moon", "mars", "rahu", "jupiter", "saturn", "mercury"]

DASHA_YEARS = {
    "ketu": 7.0,
    "venus": 20.0,
    "sun": 6.0,
    "moon": 10.0,
    "mars": 7.0,
    "rahu": 18.0,
    "jupiter": 16.0,
    "saturn": 19.0,
    "mercury": 17.0,
}

NAKSHATRA_SPAN_DEG = 13.333333333333334  # 360 / 27 = 13°20'

def get_nakshatra_info(sidereal_moon_lon_deg: float) -> Dict[str, Any]:
    """Get Nakshatra name, index, and progress fraction for Moon longitude."""
    deg = sidereal_moon_lon_deg % 360.0
    idx = int(deg // NAKSHATRA_SPAN_DEG)
    progress_frac = (deg % NAKSHATRA_SPAN_DEG) / NAKSHATRA_SPAN_DEG
    lord = DASHA_ORDER[idx % 9]
    return {
        "nakshatra_index": idx,
        "nakshatra_name": NAKSHATRA_NAMES[idx],
        "progress_fraction": progress_frac,
        "dasha_lord": lord
    }

def calc_vimshottari_timeline(sidereal_moon_lon_deg: float, max_years: float = 120.0) -> List[Dict[str, Any]]:
    """Calculate Vimshottari Mahadasha timeline from birth to max_years."""
    nak = get_nakshatra_info(sidereal_moon_lon_deg)
    first_lord = nak["dasha_lord"]
    first_idx = DASHA_ORDER.index(first_lord)
    
    # Balance of first Dasha at birth
    first_total_years = DASHA_YEARS[first_lord]
    first_rem_years = first_total_years * (1.0 - nak["progress_fraction"])
    
    timeline = []
    current_age = 0.0
    current_idx = first_idx
    
    # First Mahadasha (partial)
    timeline.append({
        "mahadasha_lord": first_lord,
        "start_age": 0.0,
        "end_age": round(first_rem_years, 4),
        "duration_years": round(first_rem_years, 4),
        "is_first_partial": True
    })
    
    current_age = first_rem_years
    current_idx = (current_idx + 1) % 9
    
    while current_age < max_years:
        lord = DASHA_ORDER[current_idx]
        duration = DASHA_YEARS[lord]
        end_age = current_age + duration
        
        timeline.append({
            "mahadasha_lord": lord,
            "start_age": round(current_age, 4),
            "end_age": round(end_age, 4),
            "duration_years": duration,
            "is_first_partial": False
        })
        
        current_age = end_age
        current_idx = (current_idx + 1) % 9
        
    return timeline

def get_sub_dashas_for_period(parent_lord: str, parent_start_age: float, parent_duration_years: float) -> List[Dict[str, Any]]:
    """Calculate the 9 sub-periods for a parent Dasha period."""
    start_idx = DASHA_ORDER.index(parent_lord)
    subperiods = []
    current_age = parent_start_age
    
    for i in range(9):
        lord = DASHA_ORDER[(start_idx + i) % 9]
        # Duration formula: (parent_duration * lord_years) / 120.0
        dur_years = (parent_duration_years * DASHA_YEARS[lord]) / 120.0
        end_age = current_age + dur_years
        
        subperiods.append({
            "lord": lord,
            "start_age": round(current_age, 6),
            "end_age": round(end_age, 6),
            "duration_years": round(dur_years, 6),
            "duration_days": round(dur_years * 365.25, 2)
        })
        current_age = end_age
        
    return subperiods

LEVEL_NAMES = {
    1: "mahadasha",
    2: "antardasha",
    3: "pratyantardasha",
    4: "sookshma_dasha",
    5: "prana_dasha",
    6: "deha_dasha"
}

def get_current_dasha(sidereal_moon_lon_deg: float, age_years: float, max_level: int = 5) -> Dict[str, Any]:
    """
    Get active Vimshottari Dasha hierarchy down to ANY arbitrary recursion depth `max_level`.
    
    Level 1: Mahadasha (大运 / 年)
    Level 2: Antardasha (中运 / 月)
    Level 3: Pratyantardasha (小运 / 日)
    Level 4: Sookshma Dasha (微运 / 小时)
    Level 5: Prana Dasha (刹那运 / 分钟)
    Level 6: Deha Dasha (体运 / 秒)
    Level N: Arbitrary infinite recursion...
    """
    target_depth = max(1, max_level)
    timeline = calc_vimshottari_timeline(sidereal_moon_lon_deg, max_years=max(120.0, age_years + 30.0))
    
    active_maha = None
    for m in timeline:
        if m["start_age"] <= age_years < m["end_age"]:
            active_maha = m
            break
            
    if not active_maha:
        active_maha = timeline[0]
        
    dasha_chain = []
    
    # Level 1 entry
    l1_entry = {
        "level": 1,
        "name": LEVEL_NAMES.get(1, "level_1"),
        "lord": active_maha["mahadasha_lord"],
        "start_age": active_maha["start_age"],
        "end_age": active_maha["end_age"],
        "duration_years": active_maha["duration_years"],
        "duration_days": round(active_maha["duration_years"] * 365.25, 2)
    }
    dasha_chain.append(l1_entry)
    
    result = {
        "nakshatra": get_nakshatra_info(sidereal_moon_lon_deg),
        "mahadasha": active_maha,
        "dasha_chain": dasha_chain
    }
    
    current_lord = active_maha["mahadasha_lord"]
    current_start = active_maha["start_age"]
    current_dur = active_maha["duration_years"]
    
    for level in range(2, target_depth + 1):
        subs = get_sub_dashas_for_period(current_lord, current_start, current_dur)
        active_sub = None
        for s in subs:
            if s["start_age"] <= age_years < s["end_age"]:
                active_sub = s
                break
        if not active_sub:
            active_sub = subs[0]
            
        lvl_name = LEVEL_NAMES.get(level, f"level_{level}")
        sub_entry = {
            "level": level,
            "name": lvl_name,
            "lord": active_sub["lord"],
            "start_age": active_sub["start_age"],
            "end_age": active_sub["end_age"],
            "duration_years": active_sub["duration_years"],
            "duration_days": active_sub["duration_days"]
        }
        result[lvl_name] = active_sub
        dasha_chain.append(sub_entry)
        
        current_lord = active_sub["lord"]
        current_start = active_sub["start_age"]
        current_dur = active_sub["duration_years"]
        
    return result


