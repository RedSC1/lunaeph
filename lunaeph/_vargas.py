"""Indian Divisional Charts (十六大分盘 Shodasha Vargas & D9 Navamsha) calculation module."""

from __future__ import annotations
import math
from typing import Dict, Any, List
from ._signs import SIGN_NAMES, degrees_to_zodiac, sign_name_index, sign_index_name

def calc_d9_navamsha(sidereal_lon_deg: float) -> tuple[str, float]:
    """
    Calculate D9 (Navamsha / 九分盘) position for a given sidereal longitude.
    Each sign (30°) is divided into 9 segments of 3°20' (3.333333°).
    
    Starting sign rules:
    - Fire signs (Aries, Leo, Sagittarius): starts from Aries (1)
    - Earth signs (Taurus, Virgo, Capricorn): starts from Capricorn (10)
    - Air signs (Gemini, Libra, Aquarius): starts from Libra (7)
    - Water signs (Cancer, Scorpio, Pisces): starts from Cancer (4)
    """
    deg = sidereal_lon_deg % 360.0
    sign_idx = int(deg // 30.0)
    deg_in_sign = deg % 30.0
    
    sub_idx = int(deg_in_sign // 3.3333333333333335) # 0 to 8
    sub_rem_deg = (deg_in_sign % 3.3333333333333335) * 9.0
    
    element = sign_idx % 4 # 0=Fire, 1=Earth, 2=Air, 3=Water
    start_sign_map = {0: 0, 1: 9, 2: 6, 3: 3} # Aries, Capricorn, Libra, Cancer
    start_sign_idx = start_sign_map[element]
    
    d9_sign_idx = (start_sign_idx + sub_idx) % 12
    return sign_index_name(d9_sign_idx), sub_rem_deg

def calc_d10_dasamsa(sidereal_lon_deg: float) -> tuple[str, float]:
    """
    Calculate D10 (Dasamsa / 十分盘 - 事业盘) position.
    Each sign (30°) is divided into 10 segments of 3° (3.0°).
    
    Starting sign rules:
    - Odd signs (Aries, Gemini, Leo...): starts from same sign
    - Even signs (Taurus, Cancer, Virgo...): starts from 9th sign from same sign
    """
    deg = sidereal_lon_deg % 360.0
    sign_idx = int(deg // 30.0)
    deg_in_sign = deg % 30.0
    
    sub_idx = int(deg_in_sign // 3.0) # 0 to 9
    sub_rem_deg = (deg_in_sign % 3.0) * 10.0
    
    if sign_idx % 2 == 0: # Odd sign (0-indexed: 0=Aries, 2=Gemini)
        start_sign_idx = sign_idx
    else: # Even sign
        start_sign_idx = (sign_idx + 8) % 12
        
    d10_sign_idx = (start_sign_idx + sub_idx) % 12
    return sign_index_name(d10_sign_idx), sub_rem_deg

def calc_d3_drekkana(sidereal_lon_deg: float) -> tuple[str, float]:
    """
    Calculate D3 (Drekkana / 三分盘 - 兄弟/勇气) position (1-5-9 Parasara Rule).
    Each sign (30°) is divided into 3 segments of 10° (10.0°).
    """
    deg = sidereal_lon_deg % 360.0
    sign_idx = int(deg // 30.0)
    deg_in_sign = deg % 30.0
    
    sub_idx = int(deg_in_sign // 10.0) # 0, 1, 2
    sub_rem_deg = (deg_in_sign % 10.0) * 3.0
    
    if sub_idx == 0:
        d3_sign_idx = sign_idx
    elif sub_idx == 1:
        d3_sign_idx = (sign_idx + 4) % 12 # 5th sign
    else:
        d3_sign_idx = (sign_idx + 8) % 12 # 9th sign
        
    return sign_index_name(d3_sign_idx), sub_rem_deg

def calc_d12_dwadasamsa(sidereal_lon_deg: float) -> tuple[str, float]:
    """
    Calculate D12 (Dwadasamsa / 十二分盘 - 父母/祖先) position.
    Each sign (30°) is divided into 12 segments of 2.5°.
    """
    deg = sidereal_lon_deg % 360.0
    sign_idx = int(deg // 30.0)
    deg_in_sign = deg % 30.0
    
    sub_idx = int(deg_in_sign // 2.5) # 0 to 11
    sub_rem_deg = (deg_in_sign % 2.5) * 12.0
    
    d12_sign_idx = (sign_idx + sub_idx) % 12
    return sign_index_name(d12_sign_idx), sub_rem_deg

def calc_d60_shashtiamsa(sidereal_lon_deg: float) -> tuple[str, float]:
    """
    Calculate D60 (Shashtiamsa / 六十分盘 - 前世业力/灵魂基因) position.
    Each sign (30°) is divided into 60 segments of 0.5°.
    """
    deg = sidereal_lon_deg % 360.0
    sign_idx = int(deg // 30.0)
    deg_in_sign = deg % 30.0
    
    sub_idx = int(deg_in_sign // 0.5) # 0 to 59
    sub_rem_deg = (deg_in_sign % 0.5) * 60.0
    
    d60_sign_idx = (sign_idx + sub_idx) % 12
    return sign_index_name(d60_sign_idx), sub_rem_deg

def calculate_divisional_charts(chart_data: Dict[str, Any], ayanamsha_mode: str = "lahiri") -> Dict[str, Any]:
    """
    Calculate Indian Divisional Charts (Vargas) including D1, D3, D9, D10, D12, D60, and Vargottama status.
    """
    from ._ayanamsha import calc_ayanamsha_deg
    
    jd_tt = chart_data["jd_tt"]
    ayan = calc_ayanamsha_deg(jd_tt, ayanamsha_mode)
    
    planets = chart_data["planets"]
    houses = chart_data["houses"]
    
    vargas = {
        "ayanamsha_mode": ayanamsha_mode,
        "ayanamsha_deg": round(ayan, 4),
        "vargottama_planets": [],
        "d1_rashi": {},
        "d3_drekkana": {},
        "d9_navamsha": {},
        "d10_dasamsa": {},
        "d12_dwadasamsa": {},
        "d60_shashtiamsa": {}
    }
    
    for k, p in planets.items():
        trop_lon = math.degrees(p["longitude_rad"])
        sid_lon = (trop_lon - ayan) % 360.0
        
        # D1 Rashi
        d1_sign, d1_deg = degrees_to_zodiac(sid_lon)
        # D3 Drekkana
        d3_sign, d3_deg = calc_d3_drekkana(sid_lon)
        # D9 Navamsha
        d9_sign, d9_deg = calc_d9_navamsha(sid_lon)
        # D10 Dasamsa
        d10_sign, d10_deg = calc_d10_dasamsa(sid_lon)
        # D12 Dwadasamsa
        d12_sign, d12_deg = calc_d12_dwadasamsa(sid_lon)
        # D60 Shashtiamsa
        d60_sign, d60_deg = calc_d60_shashtiamsa(sid_lon)
        
        vargas["d1_rashi"][k] = {"name": p["name"], "sign": d1_sign, "degree": round(d1_deg, 4)}
        vargas["d3_drekkana"][k] = {"name": p["name"], "sign": d3_sign, "degree": round(d3_deg, 4)}
        vargas["d9_navamsha"][k] = {"name": p["name"], "sign": d9_sign, "degree": round(d9_deg, 4)}
        vargas["d10_dasamsa"][k] = {"name": p["name"], "sign": d10_sign, "degree": round(d10_deg, 4)}
        vargas["d12_dwadasamsa"][k] = {"name": p["name"], "sign": d12_sign, "degree": round(d12_deg, 4)}
        vargas["d60_shashtiamsa"][k] = {"name": p["name"], "sign": d60_sign, "degree": round(d60_deg, 4)}
        
        # Vargottama Check (Same sign in D1 & D9)
        if d1_sign == d9_sign:
            vargas["vargottama_planets"].append(k)
            
    return vargas
