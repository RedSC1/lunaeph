"""Sidereal Ayanamsha (印度占星恒星岁差) calculation module."""

from __future__ import annotations
import math
from typing import Dict, Any

# Anchor constants from taiyin-ephemeris & Swiss Ephemeris
JD_J2000 = 2451545.0
JD_J1900 = 2415020.0

# Precession rate approximate: ~50.29 arcseconds per year (0.013968878 deg/yr)
# Using IAU 1976 / Vondrak 2011 precession model offset from reference epochs
AYANAMSHA_ANCHORS = {
    "lahiri": {
        "ref_jd": 2435553.5,  # 1956-03-21 00:00 TT
        "ref_val_deg": 23.245524742777778,  # 23°14'43.89"
        "name": "Lahiri (Official Indian)"
    },
    "fagan_bradley": {
        "ref_jd": 2433282.42346,  # 1950-01-01 00:00 TT (B1950.0)
        "ref_val_deg": 24.042044444444445,  # 24°02'31.36"
        "name": "Fagan-Bradley"
    },
    "raman": {
        "ref_jd": JD_J1900,
        "ref_val_deg": 21.014444444444443,  # 21°00'52"
        "name": "B.V. Raman"
    },
    "krishnamurti": {
        "ref_jd": JD_J1900,
        "ref_val_deg": 22.36388888888889,  # 22°21'50"
        "name": "Krishnamurti (KP System)"
    },
    "yukteswar": {
        "ref_jd": 2415020.0,
        "ref_val_deg": 21.411666666666666,  # 21°24'42"
        "name": "Sri Yukteswar"
    }
}

def calc_ayanamsha_deg(jd_tt: float, mode: str = "lahiri") -> float:
    """
    Calculate Ayanamsha (in degrees) for a given Julian Day (TT).
    
    :param jd_tt: Julian Day in Terrestrial Time.
    :param mode: 'lahiri', 'true_chitra'/'true_lahiri', 'fagan_bradley', 'raman', 'krishnamurti', 'yukteswar'.
    :return: Ayanamsha value in degrees.
    """
    mode_lower = mode.lower()
    
    if mode_lower in ("true_chitra", "true_lahiri"):
        # True Chitra (Spica anchored to 180.0 degrees / 0 Libra)
        t = (jd_tt - JD_J2000) / 36525.0
        spica_j2000_lon = 201.298247375
        prec_deg = (5029.0966 * t + 1.1120 * t**2) / 3600.0
        return (spica_j2000_lon - 180.0) + prec_deg

    if mode_lower in ("aldebaran_15tau", "babylonian"):
        # Western Sidereal / Babylonian: Aldebaran anchored at 15° Taurus (45.0°)
        t = (jd_tt - JD_J2000) / 36525.0
        aldebaran_j2000_lon = 69.79166667  # 9°47'30" Gemini
        prec_deg = (5029.0966 * t + 1.1120 * t**2) / 3600.0
        return (aldebaran_j2000_lon - 45.0) + prec_deg

    if mode_lower in ("true_aldebaran", "true_babylonian"):
        # True Aldebaran: Includes real-time proper motion (+62.78, -189.37 mas/yr)
        t = (jd_tt - JD_J2000) / 36525.0
        years = (jd_tt - JD_J2000) / 365.25
        # Proper motion in longitude ~ -0.000052 deg/yr (-0.187 arcsec/yr)
        pm_lon_deg = (-0.187 * years) / 3600.0
        aldebaran_apparent_lon = 69.79166667 + pm_lon_deg
        prec_deg = (5029.0966 * t + 1.1120 * t**2) / 3600.0
        return (aldebaran_apparent_lon - 45.0) + prec_deg

    if mode_lower in ("galactic_center", "galactic_0sag"):
        # Galactic Center anchored at 0° Sagittarius (240.0°)
        t = (jd_tt - JD_J2000) / 36525.0
        sgr_a_j2000_lon = 266.83777778  # Sgr A* ecliptic lon at J2000
        prec_deg = (5029.0966 * t + 1.1120 * t**2) / 3600.0
        return (sgr_a_j2000_lon - 240.0) + prec_deg
        
    if mode_lower not in AYANAMSHA_ANCHORS:
        mode_lower = "lahiri"
        
    anchor = AYANAMSHA_ANCHORS[mode_lower]
    ref_jd = anchor["ref_jd"]
    ref_val = anchor["ref_val_deg"]
    
    t_centuries = (jd_tt - ref_jd) / 36525.0
    # IAU 1976 / Vondrák 2011 precession rate
    ayanamsha_deg = ref_val + (5029.0966 * t_centuries + 1.1120 * t_centuries**2) / 3600.0
    return ayanamsha_deg % 360.0

def convert_to_sidereal(tropical_lon_deg: float, jd_tt: float, mode: str = "lahiri") -> Dict[str, Any]:
    """Convert tropical ecliptic longitude to sidereal longitude."""
    ayan = calc_ayanamsha_deg(jd_tt, mode)
    sidereal_lon = (tropical_lon_deg - ayan) % 360.0
    return {
        "sidereal_longitude_deg": round(sidereal_lon, 4),
        "ayanamsha_deg": round(ayan, 4),
        "mode": mode
    }
