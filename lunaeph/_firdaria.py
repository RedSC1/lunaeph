"""Firdaria (法达推运) calculation module."""

from __future__ import annotations
from typing import TypedDict

PLANET_YEARS = {
    "sun": 10,
    "venus": 8,
    "mercury": 13,
    "moon": 9,
    "saturn": 11,
    "jupiter": 12,
    "mars": 7,
    "north_node": 3,
    "south_node": 2,
}

CHALDEAN_ORDER = ["saturn", "jupiter", "mars", "sun", "venus", "mercury", "moon"]

DAY_PLANET_ORDER = ["sun", "venus", "mercury", "moon", "saturn", "jupiter", "mars"]
NIGHT_PLANET_ORDER = ["moon", "saturn", "jupiter", "mars", "sun", "venus", "mercury"]

class SubFirdarPeriod(TypedDict):
    ruler: str
    start_age: float
    end_age: float

class MajorFirdarPeriod(TypedDict):
    ruler: str
    start_age: float
    end_age: float
    sub_periods: list[SubFirdarPeriod]

def get_firdaria_order(is_day_chart: bool, nodes_after_mercury: bool = True) -> list[str]:
    """
    Get the major Firdaria sequence.
    
    If nodes_after_mercury=True (爱星盘默认/Al-Andarzaghar流派):
      Day chart: Sun -> Venus -> Mercury -> Moon -> Saturn -> Jupiter -> Mars -> North Node -> South Node
      Night chart: Moon -> Saturn -> Jupiter -> Mars -> Sun -> Venus -> Mercury -> North Node -> South Node
    (Note: In both day and night, if nodes_after_mercury is True, nodes are placed after the planetary sequence, 
     which for night chart ends at Mercury, and for day chart ends at Mars. Some variants force nodes after Mercury).
    """
    base_order = list(DAY_PLANET_ORDER if is_day_chart else NIGHT_PLANET_ORDER)
    
    if nodes_after_mercury:
        # Standard: Nodes placed at the end of the 7-planet sequence
        if "mercury" in base_order and base_order[-1] == "mercury":
            # Night chart ends at Mercury
            return base_order + ["north_node", "south_node"]
        elif "mercury" in base_order:
            # If explicitly requested right after mercury
            idx = base_order.index("mercury")
            return base_order[:idx+1] + ["north_node", "south_node"] + base_order[idx+1:]
        else:
            return base_order + ["north_node", "south_node"]
    else:
        # Nodes placed at the very end of sequence
        return base_order + ["north_node", "south_node"]

def calc_firdaria_timeline(is_day_chart: bool, nodes_after_mercury: bool = True, max_cycles: int = 2) -> list[MajorFirdarPeriod]:
    """Calculate complete Firdaria timeline up to max_cycles (default 2 cycles = 150 years)."""
    major_order = get_firdaria_order(is_day_chart, nodes_after_mercury)
    timeline: list[MajorFirdarPeriod] = []
    current_age = 0.0
    
    for cycle in range(max_cycles):
        for major_ruler in major_order:
            years = PLANET_YEARS[major_ruler]
            end_age = current_age + years
            
            sub_periods: list[SubFirdarPeriod] = []
            
            if major_ruler in ("north_node", "south_node"):
                # Nodes have no sub-periods
                sub_periods.append({
                    "ruler": major_ruler,
                    "start_age": current_age,
                    "end_age": end_age
                })
            else:
                # 7 sub-periods of equal length
                sub_len = years / 7.0
                # Start Chaldean order from major ruler
                start_idx = CHALDEAN_ORDER.index(major_ruler)
                sub_rulers = [CHALDEAN_ORDER[(start_idx + i) % 7] for i in range(7)]
                
                sub_start = current_age
                for sub_ruler in sub_rulers:
                    sub_end = sub_start + sub_len
                    sub_periods.append({
                        "ruler": sub_ruler,
                        "start_age": sub_start,
                        "end_age": sub_end
                    })
                    sub_start = sub_end
                    
            timeline.append({
                "ruler": major_ruler,
                "start_age": current_age,
                "end_age": end_age,
                "sub_periods": sub_periods
            })
            current_age = end_age
            
    return timeline

def get_current_firdaria(is_day_chart: bool, age: float, nodes_after_mercury: bool = True) -> dict:
    """Get active Major and Minor Firdaria for a specific age."""
    timeline = calc_firdaria_timeline(is_day_chart, nodes_after_mercury)
    
    for major in timeline:
        if major["start_age"] <= age < major["end_age"]:
            for sub in major["sub_periods"]:
                if sub["start_age"] <= age < sub["end_age"]:
                    return {
                        "major_ruler": major["ruler"],
                        "major_start_age": major["start_age"],
                        "major_end_age": major["end_age"],
                        "minor_ruler": sub["ruler"],
                        "minor_start_age": sub["start_age"],
                        "minor_end_age": sub["end_age"],
                    }
    return {}
