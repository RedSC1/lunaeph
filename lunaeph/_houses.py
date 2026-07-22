"""House systems — Placidus, Koch, Whole Sign, Equal, Porphyry,
Regiomontanus, Campanus, Alcabitius.

Ported from taiyin-ephemeris C++:
  src/astrology/house_systems.cpp — all house evaluators
  src/astrology/houses.cpp       — GAST → ARMC wiring
"""

from __future__ import annotations

import enum
import math

from ._time import TWO_PI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HALF_PI = 0.5 * math.pi
_PLACIDUS_TOLERANCE_RAD = 0.001 / 206264.80624709636  # 1 mas
_MAX_PLACIDUS_ITERATIONS = 100


def _norm(x: float) -> float:
    return x % TWO_PI


def _norm_signed(x: float) -> float:
    x = x % TWO_PI
    return x - TWO_PI if x > math.pi else x


def _asin_checked(value: float) -> float | None:
    if not math.isfinite(value) or abs(value) > 1.0:
        return None
    return math.asin(value)


# ---------------------------------------------------------------------------
# House system enum
# ---------------------------------------------------------------------------

class HouseSystem(enum.Enum):
    PLACIDUS = "placidus"
    KOCH = "koch"
    WHOLE_SIGN = "whole_sign"
    EQUAL = "equal"
    PORPHYRY = "porphyry"
    REGIOMONTANUS = "regiomontanus"
    CAMPANUS = "campanus"
    ALCABITIUS = "alcabitius"


# ---------------------------------------------------------------------------
# Fundamental angles
# ---------------------------------------------------------------------------

def ascendant_rad(armc_rad: float, obliquity_rad: float,
                  latitude_rad: float) -> float:
    x = -(math.sin(obliquity_rad) * math.tan(latitude_rad)
          + math.cos(obliquity_rad) * math.sin(armc_rad))
    return _norm(math.atan2(math.cos(armc_rad), x))


def midheaven_rad(armc_rad: float, obliquity_rad: float) -> float:
    return _norm(math.atan2(
        math.sin(armc_rad),
        math.cos(armc_rad) * math.cos(obliquity_rad)))


def vertex_rad(armc_rad: float, obliquity_rad: float,
               latitude_rad: float) -> float:
    pole = _HALF_PI - latitude_rad if latitude_rad >= 0.0 else -_HALF_PI - latitude_rad
    vx = _gc_ecl_intersect(armc_rad - _HALF_PI, pole, obliquity_rad)
    mc = midheaven_rad(armc_rad, obliquity_rad)
    if abs(latitude_rad) <= obliquity_rad and _norm_signed(vx - mc) > 0.0:
        vx = _norm(vx + math.pi)
    return vx


def east_point_rad(armc_rad: float) -> float:
    return _norm(armc_rad + _HALF_PI)


# ---------------------------------------------------------------------------
# Great-circle ecliptic intersection
# ---------------------------------------------------------------------------

def _gc_ecl_intersect(eq_angle_rad: float, pole_lat_rad: float,
                      obliquity_rad: float) -> float:
    """Ecliptic intersection of a great circle defined by equatorial angle."""
    return _norm(math.atan2(
        math.sin(eq_angle_rad),
        math.cos(obliquity_rad) * math.cos(eq_angle_rad)
        - math.sin(obliquity_rad) * math.tan(pole_lat_rad)))


# ---------------------------------------------------------------------------
# Quadrant fill
# ---------------------------------------------------------------------------

def _fill_quadrant(asc: float, mc: float,
                   c2: float, c3: float, c11: float, c12: float,
                   out: list[float]) -> None:
    out[0] = _norm(asc)                    # 1
    out[1] = c2                             # 2
    out[2] = c3                             # 3
    out[3] = _norm(mc + math.pi)            # 4  (IC)
    out[4] = _norm(c11 + math.pi)           # 5
    out[5] = _norm(c12 + math.pi)           # 6
    out[6] = _norm(asc + math.pi)           # 7  (Desc)
    out[7] = _norm(c2 + math.pi)            # 8
    out[8] = _norm(c3 + math.pi)            # 9
    out[9] = _norm(mc)                      # 10 (MC)
    out[10] = c11                           # 11
    out[11] = c12                           # 12


# ---------------------------------------------------------------------------
# Individual house system evaluators
# ---------------------------------------------------------------------------

def _eval_whole_sign(armc: float, obl: float, lat: float,
                     asc: float, mc: float, out: list[float]) -> bool:
    sign_start = math.floor(math.degrees(asc) / 30.0) * 30.0
    for i in range(12):
        out[i] = _norm(math.radians(sign_start) + i * math.pi / 6.0)
    return True


def _eval_equal(armc: float, obl: float, lat: float,
                asc: float, mc: float, out: list[float]) -> bool:
    for i in range(12):
        out[i] = _norm(asc + i * math.pi / 6.0)
    return True


def _eval_porphyry(armc: float, obl: float, lat: float,
                   asc: float, mc: float, out: list[float]) -> bool:
    ic = _norm(mc + math.pi)
    mc_to_asc = _norm(asc - mc)
    asc_to_ic = _norm(ic - asc)
    _fill_quadrant(
        asc, mc,
        _norm(asc + asc_to_ic / 3.0),
        _norm(asc + 2.0 * asc_to_ic / 3.0),
        _norm(mc + mc_to_asc / 3.0),
        _norm(mc + 2.0 * mc_to_asc / 3.0),
        out)
    return True


def _placidus_cusp_iter(eq_angle: float, pole_initial: float,
                        lat: float, obl: float, divisor: float) -> float | None:
    """Iterative solver for one Placidus cusp."""
    sine = math.sin(obl)
    tan_lat = math.tan(lat)
    cusp = _gc_ecl_intersect(eq_angle, pole_initial, obl)
    if not math.isfinite(cusp):
        return None
    for i in range(_MAX_PLACIDUS_ITERATIONS):
        decl = _asin_checked(sine * math.sin(cusp))
        if decl is None:
            return None
        tan_dec = math.tan(decl)
        if not math.isfinite(tan_dec) or abs(tan_dec) < 1e-15:
            return _norm(eq_angle)
        pole_num = _asin_checked(tan_lat * tan_dec)
        if pole_num is None:
            return None
        pole_lat = math.atan(math.sin(pole_num / divisor) / tan_dec)
        if not math.isfinite(pole_lat):
            return None
        nxt = _gc_ecl_intersect(eq_angle, pole_lat, obl)
        if not math.isfinite(nxt):
            return None
        if i > 0 and abs(_norm_signed(nxt - cusp)) < _PLACIDUS_TOLERANCE_RAD:
            return nxt
        cusp = nxt
    return None


def _eval_placidus(armc: float, obl: float, lat: float,
                   asc: float, mc: float, out: list[float]) -> bool:
    if abs(lat) >= _HALF_PI - obl:
        return False
    tan_obl = math.tan(obl)
    if not math.isfinite(tan_obl):
        return False
    a = _asin_checked(math.tan(lat) * tan_obl)
    if a is None:
        return False
    p11 = math.atan(math.sin(a / 3.0) / tan_obl)
    p12 = math.atan(math.sin(2.0 * a / 3.0) / tan_obl)
    c11 = _placidus_cusp_iter(armc + math.pi / 6.0,       p11, lat, obl, 3.0)
    c12 = _placidus_cusp_iter(armc + math.pi / 3.0,       p12, lat, obl, 1.5)
    c2  = _placidus_cusp_iter(armc + 2.0 * math.pi / 3.0, p12, lat, obl, 1.5)
    c3  = _placidus_cusp_iter(armc + 5.0 * math.pi / 6.0, p11, lat, obl, 3.0)
    if any(c is None for c in (c2, c3, c11, c12)):
        return False
    _fill_quadrant(asc, mc, c2, c3, c11, c12, out)
    return True


def _eval_koch(armc: float, obl: float, lat: float,
               asc: float, mc: float, out: list[float]) -> bool:
    if abs(lat) >= _HALF_PI - obl:
        return False
    cos_lat = math.cos(lat)
    if abs(cos_lat) < 1e-15:
        return False
    sin_a = max(-1.0, min(1.0,
               math.sin(mc) * math.sin(obl) / cos_lat))
    cos_a = math.sqrt(max(0.0, 1.0 - sin_a * sin_a))
    c = math.atan2(math.tan(lat), cos_a)
    ad3 = _asin_checked(math.sin(c) * sin_a)
    if ad3 is None:
        return False
    ad3 = ad3 / 3.0
    c11 = _gc_ecl_intersect(armc + math.pi / 6.0       - 2.0 * ad3, lat, obl)
    c12 = _gc_ecl_intersect(armc + math.pi / 3.0       - ad3,       lat, obl)
    c2  = _gc_ecl_intersect(armc + 2.0 * math.pi / 3.0 + ad3,       lat, obl)
    c3  = _gc_ecl_intersect(armc + 5.0 * math.pi / 6.0 + 2.0 * ad3, lat, obl)
    _fill_quadrant(asc, mc, c2, c3, c11, c12, out)
    return True


def _eval_regiomontanus(armc: float, obl: float, lat: float,
                        asc: float, mc: float, out: list[float]) -> bool:
    cos_lat = math.cos(lat)
    if abs(cos_lat) < 1e-15:
        return False
    p11 = math.atan(math.tan(lat) * 0.5)
    p12 = math.atan(math.tan(lat) * math.cos(math.pi / 6.0))
    c11 = _gc_ecl_intersect(armc + math.pi / 6.0,       p11, obl)
    c12 = _gc_ecl_intersect(armc + math.pi / 3.0,       p12, obl)
    c2  = _gc_ecl_intersect(armc + 2.0 * math.pi / 3.0, p12, obl)
    c3  = _gc_ecl_intersect(armc + 5.0 * math.pi / 6.0, p11, obl)
    _fill_quadrant(asc, mc, c2, c3, c11, c12, out)
    return True


def _eval_campanus(armc: float, obl: float, lat: float,
                   asc: float, mc: float, out: list[float]) -> bool:
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    if abs(cos_lat) < 1e-15:
        return False
    p11 = math.asin(max(-1.0, min(1.0, 0.5 * sin_lat)))
    p12 = math.asin(max(-1.0, min(1.0, math.cos(math.pi / 6.0) * sin_lat)))
    off11 = math.atan2(math.sqrt(3.0), cos_lat)
    off12 = math.atan2(1.0 / math.sqrt(3.0), cos_lat)
    base = armc + _HALF_PI
    c11 = _gc_ecl_intersect(base - off11, p11, obl)
    c12 = _gc_ecl_intersect(base - off12, p12, obl)
    c2  = _gc_ecl_intersect(base + off12, p12, obl)
    c3  = _gc_ecl_intersect(base + off11, p11, obl)
    _fill_quadrant(asc, mc, c2, c3, c11, c12, out)
    return True


def _eval_alcabitius(armc: float, obl: float, lat: float,
                     asc: float, mc: float, out: list[float]) -> bool:
    cos_lat = math.cos(lat)
    if abs(cos_lat) < 1e-15:
        return False
    asc_decl = _asin_checked(math.sin(asc) * math.sin(obl))
    if asc_decl is None:
        return False
    cos_lha = -math.tan(lat) * math.tan(asc_decl)
    if not math.isfinite(cos_lha) or abs(cos_lha) > 1.0:
        return False
    semi_diurnal = math.acos(cos_lha)
    semi_nocturnal = math.pi - semi_diurnal
    c11 = _gc_ecl_intersect(armc + semi_diurnal / 3.0,           0.0, obl)
    c12 = _gc_ecl_intersect(armc + 2.0 * semi_diurnal / 3.0,     0.0, obl)
    c2  = _gc_ecl_intersect(armc + math.pi - 2.0 * semi_nocturnal / 3.0, 0.0, obl)
    c3  = _gc_ecl_intersect(armc + math.pi - semi_nocturnal / 3.0,       0.0, obl)
    _fill_quadrant(asc, mc, c2, c3, c11, c12, out)
    return True


# ---------------------------------------------------------------------------
# Registry — extensible
# ---------------------------------------------------------------------------

_EVALUATORS: dict[HouseSystem, callable] = {
    HouseSystem.PLACIDUS:      _eval_placidus,
    HouseSystem.KOCH:          _eval_koch,
    HouseSystem.WHOLE_SIGN:    _eval_whole_sign,
    HouseSystem.EQUAL:         _eval_equal,
    HouseSystem.PORPHYRY:      _eval_porphyry,
    HouseSystem.REGIOMONTANUS: _eval_regiomontanus,
    HouseSystem.CAMPANUS:      _eval_campanus,
    HouseSystem.ALCABITIUS:    _eval_alcabitius,
}


def register_house_system(system: HouseSystem, evaluator: callable) -> None:
    """Register a custom house system evaluator.

    evaluator receives (armc_rad, obliquity_rad, latitude_rad,
                        ascendant_rad, midheaven_rad, out_list[12])
    and must return True on success.
    """
    _EVALUATORS[system] = evaluator


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_FALLBACK_ORDER = [
    HouseSystem.PORPHYRY,
    HouseSystem.EQUAL,
]


def calc_houses(
    gast_rad: float,
    observer_lon_rad: float,
    observer_lat_rad: float,
    true_obliquity_rad: float,
    system: HouseSystem = HouseSystem.PLACIDUS,
) -> dict:
    """Calculate house cusps for a given system.

    Parameters
    ----------
    gast_rad: GAST (Greenwich Apparent Sidereal Time), radians.
    observer_lon_rad: east-positive geodetic longitude, radians.
    observer_lat_rad: geodetic latitude, radians.
    true_obliquity_rad: true obliquity of ecliptic, radians.
    system: which house system to use (default Placidus).

    Returns: dict with
      system:            resolved HouseSystem
      armc_rad:          local ARMC
      ascendant_rad:     ecliptic longitude
      midheaven_rad:     ecliptic longitude
      vertex_rad:        ecliptic longitude
      east_point_rad:    ecliptic longitude
      cusps_rad:         list of 12 ecliptic longitudes
    """
    armc = _norm(gast_rad + observer_lon_rad)
    asc = ascendant_rad(armc, true_obliquity_rad, observer_lat_rad)
    mc = midheaven_rad(armc, true_obliquity_rad)

    if _norm_signed(asc - mc) < 0.0:
        asc = _norm(asc + math.pi)

    cusps = [0.0] * 12
    resolved = system
    evaluator = _EVALUATORS.get(system)
    ok = evaluator is not None and evaluator(
        armc, true_obliquity_rad, observer_lat_rad, asc, mc, cusps)

    if not ok:
        # Try fallbacks
        for fallback in _FALLBACK_ORDER:
            fb_eval = _EVALUATORS.get(fallback)
            if fb_eval is not None and fb_eval(
                    armc, true_obliquity_rad, observer_lat_rad,
                    asc, mc, cusps):
                resolved = fallback
                ok = True
                break
        if not ok:
            # Ultimate fallback: equal houses
            _eval_equal(armc, true_obliquity_rad, observer_lat_rad,
                        asc, mc, cusps)
            resolved = HouseSystem.EQUAL

    return {
        "system": resolved,
        "armc_rad": armc,
        "ascendant_rad": asc,
        "midheaven_rad": mc,
        "vertex_rad": vertex_rad(armc, true_obliquity_rad, observer_lat_rad),
        "east_point_rad": east_point_rad(armc),
        "cusps_rad": cusps,
    }


# Backwards-compatible alias
calc_placidus_houses = calc_houses  # defaults to Placidus
