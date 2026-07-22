"""Almuten Figuris (胜者星 / 生命主宰星) calculation module."""

from __future__ import annotations
import math
from typing import Dict, Any, List
from ._classical import TRADITIONAL_PLANETS, get_essential_dignities
from ._signs import degrees_to_zodiac, sign_name_to_longitude, sign_name_index, SIGN_START_DEG

# House Accidental Dignity Weights (Ibn Ezra / Robert Zoller Standard)
HOUSE_WEIGHTS = {
    1: 12, 10: 11, 7: 10, 4: 9, 11: 8, 5: 7,
    2: 6,  9: 5,  8: 4,  3: 3, 12: 2, 6: 1
}

# Chaldean planetary day rulers starting from Sunday
# Sunday = Sun, Monday = Moon, Tuesday = Mars, Wednesday = Mercury, Thursday = Jupiter, Friday = Venus, Saturday = Saturn
DAY_RULERS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"]

# Planetary hours order (Chaldean sequence: Saturn -> Jupiter -> Mars -> Sun -> Venus -> Mercury -> Moon)
CHALDEAN_HOUR_ORDER = ["saturn", "jupiter", "mars", "sun", "venus", "mercury", "moon"]

def get_day_and_hour_rulers(jd_utc: float, observer: dict | None = None, tz: float = 0.0) -> tuple[str, str]:
    """Calculate Chaldean Day Ruler and Hour Ruler for a given UTC Julian Day and location."""
    import datetime
    from ._time import jd_to_calendar
    
    # Get local calendar date and time
    jd_local = jd_utc + (tz / 24.0)
    y, mo, d, h, mi, s = jd_to_calendar(jd_local)
    
    if observer and "lat_deg" in observer and "lon_deg" in observer:
        from ._chart import sun_times
        lat = observer["lat_deg"]
        lon = observer["lon_deg"]
        
        st = sun_times(y, mo, d, lon, lat, tz=tz)
        rise = st["rise"]
        set_ = st["set"]
        
        if rise is not None and set_ is not None:
            # Check if before local sunrise (belongs to previous astrological day)
            if jd_utc < rise:
                dt = datetime.date(y, mo, d) - datetime.timedelta(days=1)
                st_prev = sun_times(dt.year, dt.month, dt.day, lon, lat, tz=tz)
                rise_prev = st_prev["rise"]
                set_prev = st_prev["set"]
                
                chald_day_idx = (dt.weekday() + 1) % 7
                day_ruler = DAY_RULERS[chald_day_idx]
                
                if set_prev is not None and rise is not None:
                    night_len = (rise - set_prev) / 12.0
                    h_idx = 12 + int((jd_utc - set_prev) / night_len) if night_len > 0 else 12
                    h_idx = max(12, min(23, h_idx))
                    start_idx = CHALDEAN_HOUR_ORDER.index(day_ruler)
                    hour_ruler = CHALDEAN_HOUR_ORDER[(start_idx + h_idx) % 7]
                    return day_ruler, hour_ruler
            else:
                dt = datetime.date(y, mo, d)
                chald_day_idx = (dt.weekday() + 1) % 7
                day_ruler = DAY_RULERS[chald_day_idx]
                
                if jd_utc < set_:
                    # Daytime hour (12 divisions between sunrise and sunset)
                    day_len = (set_ - rise) / 12.0
                    h_idx = int((jd_utc - rise) / day_len) if day_len > 0 else 0
                    h_idx = max(0, min(11, h_idx))
                else:
                    # Nighttime hour
                    dt_next = dt + datetime.timedelta(days=1)
                    st_next = sun_times(dt_next.year, dt_next.month, dt_next.day, lon, lat, tz=tz)
                    next_rise = st_next["rise"] if st_next["rise"] is not None else set_ + 0.5
                    night_len = (next_rise - set_) / 12.0
                    h_idx = 12 + int((jd_utc - set_) / night_len) if night_len > 0 else 12
                    h_idx = max(12, min(23, h_idx))
                    
                start_idx = CHALDEAN_HOUR_ORDER.index(day_ruler)
                hour_ruler = CHALDEAN_HOUR_ORDER[(start_idx + h_idx) % 7]
                return day_ruler, hour_ruler

    # Fallback to local weekday & 24h approximation
    dt = datetime.date(y, mo, d)
    chald_day_idx = (dt.weekday() + 1) % 7
    day_ruler = DAY_RULERS[chald_day_idx]
    
    hour_of_day = int(h)
    start_idx = CHALDEAN_HOUR_ORDER.index(day_ruler)
    hour_ruler = CHALDEAN_HOUR_ORDER[(start_idx + hour_of_day) % 7]
    return day_ruler, hour_ruler

def calculate_almuten_figuris(chart_data: Dict[str, Any], school: str = "ibn_ezra") -> Dict[str, Any]:
    """
    Calculate Almuten Figuris (Victor of the Chart / 生命主宰星).
    
    :param chart_data: Chart dictionary
    :param school: 'ibn_ezra' (standard), 'bonatti' (strict sect triplicity), 'lilly' (cadent filter)
    """
    school_lower = school.lower()
    planets = chart_data["planets"]
    houses = chart_data["houses"]
    lots = chart_data["lots"]
    jd_utc = chart_data["jd_utc"]
    
    sun_lon = planets["sun"]["longitude_rad"]
    asc_lon = math.radians(sign_name_to_longitude(houses["ascendant"]["sign"], houses["ascendant"]["degree"] + houses["ascendant"]["minute"] / 60.0))
    is_day_chart = ((sun_lon - asc_lon) % (2.0 * math.pi)) > math.pi
    
    # 1. Five Vital Points (5 Hylegial Places)
    # (1) Sun, (2) Moon, (3) Ascendant, (4) Lot of Fortune, (5) Prenatal Syzygy
    from ._chart import search_prenatal_syzygy
    syzygy_sign, syzygy_deg = search_prenatal_syzygy(jd_utc)

    vital_points = {
        "sun": (planets["sun"]["sign"], planets["sun"]["degree"] + planets["sun"]["minute"] / 60.0),
        "moon": (planets["moon"]["sign"], planets["moon"]["degree"] + planets["moon"]["minute"] / 60.0),
        "ascendant": (houses["ascendant"]["sign"], houses["ascendant"]["degree"] + houses["ascendant"]["minute"] / 60.0),
        "fortune": (lots["fortune"]["sign"], lots["fortune"]["degree_in_sign"]),
        "syzygy": (syzygy_sign, syzygy_deg),
    }
    
    scores = {p: 0 for p in TRADITIONAL_PLANETS}
    essential_breakdown = {p: 0 for p in TRADITIONAL_PLANETS}
    accidental_breakdown = {p: 0 for p in TRADITIONAL_PLANETS}
    
    # Calculate Essential Points across 5 Vital Places
    for pt_name, (sign, deg) in vital_points.items():
        for p in TRADITIONAL_PLANETS:
            dignity_info = get_essential_dignities(p, sign, deg, is_day_chart)
            pt_score = dignity_info.get("score", 0)
            scores[p] += pt_score
            essential_breakdown[p] += pt_score

    # Calculate Accidental Points
    day_ruler, hour_ruler = get_day_and_hour_rulers(jd_utc, observer=chart_data.get("observer"), tz=chart_data.get("tz", 0.0))
    if day_ruler in scores:
        scores[day_ruler] += 7
        accidental_breakdown[day_ruler] += 7
    if hour_ruler in scores:
        scores[hour_ruler] += 6
        accidental_breakdown[hour_ruler] += 6
        
    # House Placement Accidental Scores
    # Find house placement for each traditional planet
    cusps = houses["cusps"] # List of 12 cusp dicts
    for p in TRADITIONAL_PLANETS:
        p_sign = planets[p]["sign"]
        p_deg = planets[p]["degree"] + planets[p]["minute"] / 60.0
        p_lon = sign_name_to_longitude(p_sign, p_deg)
        
        # Simple Whole Sign house calculation
        asc_sign = houses["ascendant"]["sign"]
        p_house = ((sign_name_index(p_sign) - sign_name_index(asc_sign)) % 12) + 1
        
        h_score = HOUSE_WEIGHTS.get(p_house, 0)
        if school_lower == "lilly" and p_house in (6, 8, 12) and essential_breakdown[p] <= 0:
            h_score = 0  # Lilly: peregrine planets in bad houses receive no accidental house bonus
            
        scores[p] += h_score
        accidental_breakdown[p] += h_score

    # Sort scores to find the winner (Victor)
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    winner, top_score = sorted_scores[0]
    
    return {
        "school": school_lower,
        "almuten_figuris": winner,
        "top_score": top_score,
        "day_ruler": day_ruler,
        "hour_ruler": hour_ruler,
        "scores": dict(sorted_scores),
        "essential_scores": essential_breakdown,
        "accidental_scores": accidental_breakdown
    }
