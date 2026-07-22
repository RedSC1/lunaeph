"""Almuten Figuris (胜者星 / 生命主宰星) calculation module."""

from __future__ import annotations
import math
from typing import Dict, Any, List
from ._classical import TRADITIONAL_PLANETS, get_essential_dignities
from ._signs import degrees_to_zodiac

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

def get_day_and_hour_rulers(jd_utc: float) -> tuple[str, str]:
    """Calculate Chaldean Day Ruler and Hour Ruler for a given UTC Julian Day."""
    # Day of week: 0 = Monday, 6 = Sunday (using standard Julian day modulo)
    # JD 2451545.0 (2000-01-01 12:00 UTC) is Saturday
    day_idx = int(math.floor(jd_utc + 1.5)) % 7
    # Map Python weekday (0=Mon...6=Sun) to Chaldean
    # Saturday = 6, Sunday = 0, Mon = 1, Tue = 2, Wed = 3, Thu = 4, Fri = 5
    day_ruler = DAY_RULERS[(day_idx + 1) % 7]
    
    # Hour ruler approximation based on 24-hour division
    hour_of_day = int(((jd_utc + 0.5) % 1.0) * 24.0)
    hour_ruler_start_idx = CHALDEAN_HOUR_ORDER.index(day_ruler)
    hour_ruler = CHALDEAN_HOUR_ORDER[(hour_ruler_start_idx + hour_of_day) % 7]
    
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
    asc_lon = math.radians((houses["ascendant"]["degree"] + houses["ascendant"]["minute"] / 60.0) + ({"Aries":0, "Taurus":30, "Gemini":60, "Cancer":90, "Leo":120, "Virgo":150, "Libra":180, "Scorpio":210, "Sagittarius":240, "Capricorn":270, "Aquarius":300, "Pisces":330}[houses["ascendant"]["sign"]]))
    is_day_chart = ((sun_lon - asc_lon) % (2.0 * math.pi)) > math.pi
    
    # 1. Five Vital Points (5 Hylegial Places)
    # (1) Sun, (2) Moon, (3) Ascendant, (4) Lot of Fortune, (5) Prenatal Syzygy (approx. by Moon position for simplicity)
    vital_points = {
        "sun": (planets["sun"]["sign"], planets["sun"]["degree"] + planets["sun"]["minute"] / 60.0),
        "moon": (planets["moon"]["sign"], planets["moon"]["degree"] + planets["moon"]["minute"] / 60.0),
        "ascendant": (houses["ascendant"]["sign"], houses["ascendant"]["degree"] + houses["ascendant"]["minute"] / 60.0),
        "fortune": (lots["fortune"]["sign"], lots["fortune"]["degree_in_sign"]),
        "syzygy": (planets["moon"]["sign"], planets["moon"]["degree"] + planets["moon"]["minute"] / 60.0), # SAN approximation
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
    day_ruler, hour_ruler = get_day_and_hour_rulers(jd_utc)
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
        p_lon = ({"Aries":0, "Taurus":30, "Gemini":60, "Cancer":90, "Leo":120, "Virgo":150, "Libra":180, "Scorpio":210, "Sagittarius":240, "Capricorn":270, "Aquarius":300, "Pisces":330}[p_sign]) + p_deg
        
        # Simple Whole Sign house calculation
        asc_sign = houses["ascendant"]["sign"]
        p_house = (({"Aries":0, "Taurus":30, "Gemini":60, "Cancer":90, "Leo":120, "Virgo":150, "Libra":180, "Scorpio":210, "Sagittarius":240, "Capricorn":270, "Aquarius":300, "Pisces":330}[p_sign] // 30 - {"Aries":0, "Taurus":30, "Gemini":60, "Cancer":90, "Leo":120, "Virgo":150, "Libra":180, "Scorpio":210, "Sagittarius":240, "Capricorn":270, "Aquarius":300, "Pisces":330}[asc_sign] // 30) % 12) + 1
        
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
