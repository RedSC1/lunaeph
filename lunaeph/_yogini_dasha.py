"""Yogini Dasha (瑜伽女神大运系统 - 36年周期) calculation module."""

from __future__ import annotations
import math
from typing import Dict, Any, List

# 8 Yoginis: (name, associated_planet, duration_years)
YOGINI_TABLE = [
    ("Mangala",  "moon",    1),
    ("Pingala",  "sun",     2),
    ("Dhanya",   "jupiter", 3),
    ("Bhramari", "mars",    4),
    ("Bhadrika", "mercury", 5),
    ("Ulka",     "saturn",  6),
    ("Siddha",   "venus",   7),
    ("Sankata",  "rahu",    8),
]
YOGINI_CYCLE = 36.0  # Total cycle years


def calc_yogini_dasha(chart_data: Dict[str, Any], age_years: float = 0.0,
                      ayanamsha_mode: str = "lahiri", max_level: int = 2) -> Dict[str, Any]:
    """
    Calculate Yogini Dasha (瑜伽女神大运 / 36年短周期大运系统).

    :param chart_data: Chart dictionary
    :param age_years: Target age to find active dasha chain
    :param ayanamsha_mode: Sidereal ayanamsha mode
    :param max_level: Recursion depth (1=Maha only, 2=Maha+Antar, etc.)
    :return: Dict with timeline and active dasha chain
    """
    from ._ayanamsha import calc_ayanamsha_deg

    jd_tt = chart_data["jd_tt"]
    ayan = calc_ayanamsha_deg(jd_tt, ayanamsha_mode)
    moon_trop = math.degrees(chart_data["planets"]["moon"]["longitude_rad"])
    moon_sid = (moon_trop - ayan) % 360.0

    # Nakshatra index (0-26), each 13°20' = 13.3333°
    nak_span = 360.0 / 27.0
    nak_idx = int(moon_sid / nak_span)
    nak_progress = (moon_sid % nak_span) / nak_span  # 0.0 to 1.0

    # Starting Yogini index
    start_yogini_idx = (nak_idx + 3) % 8

    # Balance of starting Yogini period
    start_yogini = YOGINI_TABLE[start_yogini_idx]
    balance_years = start_yogini[2] * (1.0 - nak_progress)

    # Generate timeline covering at least 108 years (3 full cycles)
    timeline = []
    current_age = 0.0
    yogini_idx = start_yogini_idx
    first = True

    while current_age < 108.0:
        name, planet, years = YOGINI_TABLE[yogini_idx]
        duration = balance_years if first else float(years)
        first = False

        timeline.append({
            "yogini": name,
            "planet": planet,
            "start_age": round(current_age, 6),
            "end_age": round(current_age + duration, 6),
            "duration_years": round(duration, 6),
        })

        current_age += duration
        yogini_idx = (yogini_idx + 1) % 8

    # Find active dasha chain at given age
    def _find_active(tl: list, target_age: float, parent_start: float,
                     parent_dur: float, level: int, chain: list) -> list:
        for entry in tl:
            if entry["start_age"] <= target_age < entry["end_age"]:
                chain.append({
                    "level": level,
                    "yogini": entry["yogini"],
                    "planet": entry["planet"],
                    "start_age": entry["start_age"],
                    "end_age": entry["end_age"],
                    "duration_years": entry["duration_years"],
                })
                if level < max_level:
                    # Generate sub-periods
                    sub_tl = _sub_periods(entry, level + 1)
                    _find_active(sub_tl, target_age, entry["start_age"],
                                 entry["duration_years"], level + 1, chain)
                break
        return chain

    def _sub_periods(parent: dict, level: int) -> list:
        """Generate sub-periods within a parent Yogini period."""
        parent_yogini_idx = next(i for i, y in enumerate(YOGINI_TABLE)
                                  if y[0] == parent["yogini"])
        sub_tl = []
        sub_age = parent["start_age"]

        for j in range(8):
            sub_idx = (parent_yogini_idx + j) % 8
            sub_name, sub_planet, sub_years = YOGINI_TABLE[sub_idx]
            sub_dur = parent["duration_years"] * (sub_years / YOGINI_CYCLE)

            sub_tl.append({
                "yogini": sub_name,
                "planet": sub_planet,
                "start_age": round(sub_age, 6),
                "end_age": round(sub_age + sub_dur, 6),
                "duration_years": round(sub_dur, 6),
            })
            sub_age += sub_dur

        return sub_tl

    active_chain = _find_active(timeline, age_years, 0.0, 0.0, 1, [])

    return {
        "cycle_years": YOGINI_CYCLE,
        "start_yogini": start_yogini[0],
        "start_yogini_balance_years": round(balance_years, 6),
        "timeline": timeline,
        "active_at_age": {
            "age_years": age_years,
            "dasha_chain": active_chain,
        },
    }
