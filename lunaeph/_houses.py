"""House systems — Placidus, with ascendant, midheaven, vertex, east point.

Ported from taiyin-ephemeris C++:
  src/astrology/house_systems.cpp — Placidus cusp iteration,
      great_circle_ecliptic_intersection, ascendant/midheaven/vertex formulas
  src/astrology/houses.cpp       — calc_house_positions_impl (GAST → ARMC wiring)

For v0.1 only Placidus is implemented.  The caller is expected to have
already computed true obliquity and GAST via _precession and _time.
"""

from __future__ import annotations

import math
from typing import Sequence

from ._time import DAYS_PER_JULIAN_CENTURY, JD_J2000, TWO_PI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PLACIDUS_TOLERANCE_RAD = 0.001 / 206264.80624709636  # 1 mas
_MAX_PLACIDUS_ITERATIONS = 100
_HALF_PI = 0.5 * math.pi


def _normalize_rad(x: float) -> float:
    return x % TWO_PI


def _normalize_signed_rad(x: float) -> float:
    x = x % TWO_PI
    if x > math.pi:
        x -= TWO_PI
    return x


def _asin_checked(value: float) -> float | None:
    """Safe asin that returns None on invalid input."""
    if not math.isfinite(value) or abs(value) > 1.0:
        return None
    return math.asin(value)


# ---------------------------------------------------------------------------
# Fundamental angles
# ---------------------------------------------------------------------------

def ascendant_rad(armc_rad: float, obliquity_rad: float,
                  latitude_rad: float) -> float:
    """Ascendant from ARMC, true obliquity, and geodetic latitude."""
    x = -(math.sin(obliquity_rad) * math.tan(latitude_rad)
          + math.cos(obliquity_rad) * math.sin(armc_rad))
    return _normalize_rad(math.atan2(math.cos(armc_rad), x))


def midheaven_rad(armc_rad: float, obliquity_rad: float) -> float:
    """Midheaven (MC) from ARMC and true obliquity."""
    return _normalize_rad(math.atan2(
        math.sin(armc_rad),
        math.cos(armc_rad) * math.cos(obliquity_rad)))


def vertex_rad(armc_rad: float, obliquity_rad: float,
               latitude_rad: float) -> float:
    """Vertex (anti-vertex at +π)."""
    pole_lat = _HALF_PI - latitude_rad if latitude_rad >= 0.0 else -_HALF_PI - latitude_rad
    vx = _great_circle_ecliptic_intersection_rad(
        armc_rad - _HALF_PI, pole_lat, obliquity_rad)
    mc = midheaven_rad(armc_rad, obliquity_rad)
    if abs(latitude_rad) <= obliquity_rad and _normalize_signed_rad(vx - mc) > 0.0:
        vx = _normalize_rad(vx + math.pi)
    return vx


def east_point_rad(armc_rad: float) -> float:
    """East point = ARMC + π/2."""
    return _normalize_rad(armc_rad + _HALF_PI)


# ---------------------------------------------------------------------------
# Great-circle ecliptic intersection
# ---------------------------------------------------------------------------

def _great_circle_ecliptic_intersection_rad(
    equatorial_angle_rad: float,
    pole_latitude_rad: float,
    obliquity_rad: float,
) -> float:
    """Ecliptic longitude at which a great circle (defined by equatorial
    angle and pole latitude) intersects the ecliptic."""
    return _normalize_rad(math.atan2(
        math.sin(equatorial_angle_rad),
        math.cos(obliquity_rad) * math.cos(equatorial_angle_rad)
        - math.sin(obliquity_rad) * math.tan(pole_latitude_rad)))


# ---------------------------------------------------------------------------
# Placidus cusp (single)
# ---------------------------------------------------------------------------

def _placidus_cusp_rad(
    rectasc_rad: float,
    initial_pole_lat_rad: float,
    latitude_rad: float,
    obliquity_rad: float,
    divisor: float,
) -> float | None:
    """Iteratively solve one Placidus house cusp.

    *divisor* is 3.0 for houses 3/11 and 1.5 for houses 2/12.
    """
    sine = math.sin(obliquity_rad)
    tan_lat = math.tan(latitude_rad)

    cusp = _great_circle_ecliptic_intersection_rad(
        rectasc_rad, initial_pole_lat_rad, obliquity_rad)
    if not math.isfinite(cusp):
        return None

    for i in range(_MAX_PLACIDUS_ITERATIONS):
        decl = _asin_checked(sine * math.sin(cusp))
        if decl is None:
            return None
        tan_dec = math.tan(decl)
        if not math.isfinite(tan_dec) or abs(tan_dec) < 1e-15:
            return _normalize_rad(rectasc_rad)

        pole_num = _asin_checked(tan_lat * tan_dec)
        if pole_num is None:
            return None
        pole_lat = math.atan(math.sin(pole_num / divisor) / tan_dec)
        if not math.isfinite(pole_lat):
            return None

        nxt = _great_circle_ecliptic_intersection_rad(
            rectasc_rad, pole_lat, obliquity_rad)
        if not math.isfinite(nxt):
            return None

        if i > 0 and abs(_normalize_signed_rad(nxt - cusp)) < _PLACIDUS_TOLERANCE_RAD:
            return nxt
        cusp = nxt

    # did not converge within max iterations
    return None


# ---------------------------------------------------------------------------
# Fill quadrant cusps
# ---------------------------------------------------------------------------

def _fill_quadrant_cusps(
    asc: float, mc: float,
    cusp_2: float, cusp_3: float,
    cusp_11: float, cusp_12: float,
    out: list[float],
) -> None:
    """Fill all 12 cusps from quadrant corners."""
    # House 1 = ascendant
    out[0] = _normalize_rad(asc)
    # House 2 and 3 from Placidus
    out[1] = cusp_2
    out[2] = cusp_3
    # House 4 = IC = ascendant + π
    out[3] = _normalize_rad(mc + math.pi)  # IC
    # House 5 and 6: opposing quadrant, filled symmetrically
    out[4] = _normalize_rad(cusp_11 + math.pi)
    out[5] = _normalize_rad(cusp_12 + math.pi)
    # House 7 = descendant = ascendant + π
    out[6] = _normalize_rad(asc + math.pi)
    # House 8 and 9
    out[7] = _normalize_rad(cusp_2 + math.pi)
    out[8] = _normalize_rad(cusp_3 + math.pi)
    # House 10 = MC
    out[9] = _normalize_rad(mc)
    # House 11 and 12
    out[10] = cusp_11
    out[11] = cusp_12


# ---------------------------------------------------------------------------
# Placidus — full cusp computation
# ---------------------------------------------------------------------------

def _fill_placidus_cusps(
    armc_rad: float,
    obliquity_rad: float,
    latitude_rad: float,
    asc_rad: float,
    mc_rad: float,
    out: list[float],
) -> bool:
    """Compute Placidus cusps 2, 3, 11, 12 and fill all 12."""
    if abs(latitude_rad) >= _HALF_PI - obliquity_rad:
        return False  # polar region — Placidus undefined

    tan_obl = math.tan(obliquity_rad)
    if not math.isfinite(tan_obl):
        return False

    a = _asin_checked(math.tan(latitude_rad) * tan_obl)
    if a is None:
        return False

    pole_11_3 = math.atan(math.sin(a / 3.0) / tan_obl)
    pole_12_2 = math.atan(math.sin(2.0 * a / 3.0) / tan_obl)

    cusp_11 = _placidus_cusp_rad(
        armc_rad + math.pi / 6.0, pole_11_3,
        latitude_rad, obliquity_rad, 3.0)
    cusp_12 = _placidus_cusp_rad(
        armc_rad + math.pi / 3.0, pole_12_2,
        latitude_rad, obliquity_rad, 1.5)
    cusp_2 = _placidus_cusp_rad(
        armc_rad + 2.0 * math.pi / 3.0, pole_12_2,
        latitude_rad, obliquity_rad, 1.5)
    cusp_3 = _placidus_cusp_rad(
        armc_rad + 5.0 * math.pi / 6.0, pole_11_3,
        latitude_rad, obliquity_rad, 3.0)

    if any(c is None for c in (cusp_2, cusp_3, cusp_11, cusp_12)):
        return False

    _fill_quadrant_cusps(asc_rad, mc_rad, cusp_2, cusp_3, cusp_11, cusp_12, out)
    return True


# ---------------------------------------------------------------------------
# Public: full house calculation
# ---------------------------------------------------------------------------

def calc_placidus_houses(
    gast_rad: float,
    observer_lon_rad: float,
    observer_lat_rad: float,
    true_obliquity_rad: float,
) -> dict:
    """Calculate Placidus house cusps.

    Parameters
    ----------
    gast_rad: GAST (Greenwich Apparent Sidereal Time) in radians.
        Compute via: _time.gast_rad(jd_ut1, jd_tt, eqeq_rad) where
        eqeq_rad comes from _precession.equation_of_equinoxes_rad(jd_tt).
    observer_lon_rad: east-positive geographic longitude (radians).
    observer_lat_rad: geodetic latitude (radians).
    true_obliquity_rad: true obliquity of the ecliptic (radians), from
        _precession.iau2000b_nutation_angles()["true_obliquity_rad"].

    Returns
    -------
    dict with keys:
        armc_rad: ARMC (local sidereal time, radians)
        ascendant_rad: ecliptic longitude of the ascendant
        midheaven_rad: ecliptic longitude of the midheaven
        vertex_rad: ecliptic longitude of the vertex
        east_point_rad: ecliptic longitude of the east point
        cusps_rad: list of 12 ecliptic longitudes (0-indexed; cusps[0]
                   is house 1, cusps[9] is house 10)
    """
    armc = _normalize_rad(gast_rad + observer_lon_rad)

    asc = ascendant_rad(armc, true_obliquity_rad, observer_lat_rad)
    mc = midheaven_rad(armc, true_obliquity_rad)

    # Ensure ascendant is before MC (correct hemisphere)
    if _normalize_signed_rad(asc - mc) < 0.0:
        asc = _normalize_rad(asc + math.pi)

    cusps = [0.0] * 12
    ok = _fill_placidus_cusps(armc, true_obliquity_rad, observer_lat_rad,
                              asc, mc, cusps)
    if not ok:
        # Fallback to equal houses if Placidus fails (e.g. polar regions)
        for i in range(12):
            cusps[i] = _normalize_rad(asc + i * math.pi / 6.0)

    return {
        "armc_rad": armc,
        "ascendant_rad": asc,
        "midheaven_rad": mc,
        "vertex_rad": vertex_rad(armc, true_obliquity_rad, observer_lat_rad),
        "east_point_rad": east_point_rad(armc),
        "cusps_rad": cusps,
    }
