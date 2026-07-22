"""Arabic Parts and Hellenistic Lots calculation module."""

from __future__ import annotations
from typing import Dict, Any
from ._signs import degrees_to_zodiac

def normalize_deg(deg: float) -> float:
    """Normalize angle to 0.0 - 360.0 degrees."""
    return deg % 360.0

def calc_lot(asc: float, point1: float, point2: float) -> float:
    """Calculate a Lot given formula: Asc + Point1 - Point2."""
    return normalize_deg(asc + point1 - point2)

def calculate_lots(
    asc_deg: float,
    sun_deg: float,
    moon_deg: float,
    venus_deg: float,
    mars_deg: float,
    jupiter_deg: float,
    saturn_deg: float,
    mercury_deg: float,
    is_day_chart: bool,
    reverse_day_night: bool = True
) -> Dict[str, Dict[str, Any]]:
    """Calculate major Hellenistic Hermetic Lots and Arabic Parts."""
    lots = {}
    
    # 1. Lot of Fortune (福德点 / 幸运点)
    if is_day_chart or not reverse_day_night:
        fortune_deg = calc_lot(asc_deg, moon_deg, sun_deg)
    else:
        fortune_deg = calc_lot(asc_deg, sun_deg, moon_deg)
        
    # 2. Lot of Spirit (精神点 / 官禄精神)
    if is_day_chart or not reverse_day_night:
        spirit_deg = calc_lot(asc_deg, sun_deg, moon_deg)
    else:
        spirit_deg = calc_lot(asc_deg, moon_deg, sun_deg)
        
    # 3. Lot of Eros (桃花 / 爱欲点)
    if is_day_chart or not reverse_day_night:
        eros_deg = calc_lot(asc_deg, venus_deg, spirit_deg)
    else:
        eros_deg = calc_lot(asc_deg, spirit_deg, venus_deg)
        
    # 4. Lot of Necessity (必然点)
    if is_day_chart or not reverse_day_night:
        necessity_deg = calc_lot(asc_deg, fortune_deg, mercury_deg)
    else:
        necessity_deg = calc_lot(asc_deg, mercury_deg, fortune_deg)
        
    # 5. Lot of Courage (勇气点)
    if is_day_chart or not reverse_day_night:
        courage_deg = calc_lot(asc_deg, fortune_deg, mars_deg)
    else:
        courage_deg = calc_lot(asc_deg, mars_deg, fortune_deg)
        
    # 6. Lot of Victory (胜利点)
    if is_day_chart or not reverse_day_night:
        victory_deg = calc_lot(asc_deg, jupiter_deg, fortune_deg)
    else:
        victory_deg = calc_lot(asc_deg, fortune_deg, jupiter_deg)
        
    # 7. Lot of Nemesis (惩戒 / 报应点)
    if is_day_chart or not reverse_day_night:
        nemesis_deg = calc_lot(asc_deg, fortune_deg, saturn_deg)
    else:
        nemesis_deg = calc_lot(asc_deg, saturn_deg, fortune_deg)
        
    raw_lots = {
        "fortune": fortune_deg,
        "spirit": spirit_deg,
        "eros": eros_deg,
        "necessity": necessity_deg,
        "courage": courage_deg,
        "victory": victory_deg,
        "nemesis": nemesis_deg,
    }
    
    for name, deg in raw_lots.items():
        sign, deg_in_sign = degrees_to_zodiac(deg)
        lots[name] = {
            "longitude_deg": round(deg, 4),
            "sign": sign,
            "degree_in_sign": round(deg_in_sign, 4)
        }
        
    return lots
