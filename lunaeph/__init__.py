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

from ._chart import (
    calculate_chart, Chart,
    search_solar_longitude, search_lunar_longitude,
    search_prenatal_syzygy,
    new_moons_between, full_moons_between,
    equation_of_time_minutes, apparent_solar_time_minutes, sun_times,
)
from ._houses import HouseSystem, calc_houses, calc_placidus_houses
from ._aspects import find_all_aspects, angular_separation_deg, DEFAULT_ORBS
from ._signs import sign_from_longitude, sign_degree_minute, SIGN_NAMES
from ._time import calendar_to_jd, jd_to_calendar, delta_t_seconds_from_jd_ut1
from ._firdaria import calc_firdaria_timeline, get_current_firdaria
from ._lots import calculate_lots
from ._profections import calc_profection
from ._ayanamsha import calc_ayanamsha_deg
from ._zodiacal_releasing import calc_zr_l1_periods, get_current_zr
from ._almuten import calculate_almuten_figuris
from ._dasha import calc_vimshottari_timeline, get_current_dasha
from ._vargas import calculate_divisional_charts
from ._primary_directions import calc_primary_directions
from ._bhava_gochar import calc_bhava_chalit, calc_sade_sati
from ._jyotish_master import calc_upagrahas, calc_kp_sublord, calc_panchadha_maitri
from ._jaimini_huber import calc_jaimini_chara_karakas, calc_huber_age_point
from ._ashtakavarga import calc_ashtakavarga
from ._arudha_pada import calc_arudha_padas
from ._yogini_dasha import calc_yogini_dasha
from ._nakshatra import get_nakshatra_info, calc_nakshatra_chart, calc_nakshatra_compatibility
from ._karaka import calc_all_karakas
from ._light_aspects import (
    calc_translation_of_light,
    calc_collection_of_light,
    calc_besiegement,
    calc_prohibition,
    get_moiety_of_orbs
)
from ._precession import (
    iau2000b_nutation_angles,
    equation_of_equinoxes_rad,
    mean_obliquity_rad,
)

__all__ = [
    # chart
    "calculate_chart",
    "Chart",
    "search_solar_longitude",
    "search_lunar_longitude",
    "search_prenatal_syzygy",
    "new_moons_between",
    "full_moons_between",
    "equation_of_time_minutes",
    "apparent_solar_time_minutes",
    "sun_times",
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
    # firdaria
    "calc_firdaria_timeline",
    "get_current_firdaria",
    # lots & profections & ayanamsha & ZR
    "calculate_lots",
    "calc_profection",
    "calc_ayanamsha_deg",
    "calc_zr_l1_periods",
    "get_current_zr",
    "calculate_almuten_figuris",
    "calc_vimshottari_timeline",
    "get_current_dasha",
    "calculate_divisional_charts",
    "calc_primary_directions",
    "calc_bhava_chalit",
    "calc_sade_sati",
    "calc_upagrahas",
    "calc_kp_sublord",
    "calc_panchadha_maitri",
    "calc_jaimini_chara_karakas",
    "calc_huber_age_point",
    "calc_ashtakavarga",
    "calc_arudha_padas",
    "calc_yogini_dasha",
    "get_nakshatra_info",
    "calc_nakshatra_chart",
    "calc_nakshatra_compatibility",
    "calc_all_karakas",
    "calc_translation_of_light",
    "calc_collection_of_light",
    "calc_besiegement",
    "calc_prohibition",
    "get_moiety_of_orbs",
    # precession
    "iau2000b_nutation_angles",
    "equation_of_equinoxes_rad",
    "mean_obliquity_rad",
]
__version__ = "0.1.0"
