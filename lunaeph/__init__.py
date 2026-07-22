"""LunaEph — a thin western astrology library on top of taiyin.

Usage
-----
>>> from lunaeph import calculate_chart, HouseSystem
>>> chart = calculate_chart(2026, 7, 22, 14, 30,
...                          latitude_deg=39.9, longitude_deg=116.4)
>>> chart["planets"]["sun"]["sign"]
'Leo'
>>> chart["houses"]["ascendant"]["sign"]
'Aries'
"""

from ._chart import calculate_chart, Chart
from ._houses import HouseSystem, calc_houses, calc_placidus_houses
from ._aspects import find_all_aspects, angular_separation_deg, DEFAULT_ORBS
from ._signs import sign_from_longitude, sign_degree_minute, SIGN_NAMES
from ._time import calendar_to_jd, jd_to_calendar, delta_t_seconds_from_jd_ut1
from ._precession import (
    iau2000b_nutation_angles,
    equation_of_equinoxes_rad,
    mean_obliquity_rad,
)

__all__ = [
    # chart
    "calculate_chart",
    "Chart",
    # houses
    "HouseSystem",
    "calc_houses",
    "calc_placidus_houses",
    # aspects
    "find_all_aspects",
    "angular_separation_deg",
    "DEFAULT_ORBS",
    # signs
    "sign_from_longitude",
    "sign_degree_minute",
    "SIGN_NAMES",
    # time
    "calendar_to_jd",
    "jd_to_calendar",
    "delta_t_seconds_from_jd_ut1",
    # precession
    "iau2000b_nutation_angles",
    "equation_of_equinoxes_rad",
    "mean_obliquity_rad",
]
__version__ = "0.1.0"
