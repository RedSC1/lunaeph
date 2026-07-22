"""Chart calculation — wires time, precession, houses, signs, aspects.

The following algorithms are adapted from 寿星天文历 (sxwnl) by 许剑伟:
  - Equation of Time          (pty_zty2)
  - Sunrise / Sunset / Twilight (sunShengJ, SZJ.St)
  - Syzygy sequence            (suoN, so_low)
  - Prenatal syzygy search     (so_low-based search)

寿星天文历 copyright notice:
  本程序是开源的，你可以使用其中的任意部分代码，但不得随意修改
  "天文算法(eph.js)"及"农历算法(lunar.js)中古历部分的数据及算法"。
  一旦修改可能影响万年历的准确性，如果你对天文学不太了解而仅凭
  对历法的热情，请不要对此做任何修改，以免弄巧成拙。

  如果在你自己开发的软件中使用了本程序的核心算法及数据，你可以
  在你的软件中申明"数据或算法来源于寿星天文历"，也可以不申明，
  但不可以申明为它其它来源。如有异义，可与我共内探讨。

  — 许剑伟 (xunmeng04#163.com), https://github.com/sxwnl/sxwnl

Atmospheric refraction (hybrid Bennett+Smart) and WGS84 geodetic model
are adapted from taiyin‑ephemeris (Apache 2.0).
"""

from __future__ import annotations

import math
from typing import Callable

from ._time import (
    calendar_to_jd,
    jd_to_calendar,
    jd_ut1_to_tt,
    jd_tt_to_ut1,
    delta_t_seconds_from_jd_ut1,
    gast_rad,
)
from ._precession import (
    iau2000b_nutation_angles,
    equation_of_equinoxes_rad,
    j2000_ecliptic_to_date,
    mean_obliquity_rad,
)
from ._aberration import apply_light_corrections
from ._deflection import apply_solar_deflection
from ._houses import calc_houses, HouseSystem
from ._signs import sign_degree_minute, sign_name_to_longitude
from ._aspects import find_all_aspects, _ANGLE_NAMES


# ---------------------------------------------------------------------------
# Planet list
# ---------------------------------------------------------------------------

# taiyin body IDs + our name
_PLANETS: list[tuple[int, str, str]] = [
    # (body_id, key, display_name)
    (10, "sun",     "Sun"),
    (301, "moon",   "Moon"),
    (1,  "mercury", "Mercury"),
    (2,  "venus",   "Venus"),
    (4,  "mars",    "Mars"),
    (5,  "jupiter", "Jupiter"),
    (6,  "saturn",  "Saturn"),
    (7,  "uranus",  "Uranus"),
    (8,  "neptune", "Neptune"),
    (9,  "pluto",   "Pluto"),
]

ASTRODIENST_TROPICAL_MONTH_DAYS = 27.32158218
TROPICAL_YEAR_DAYS = 365.2421897


def _km_to_au(km: float) -> float:
    return km / 149597870.7


def _to_xyz(v: tuple[float, ...]) -> tuple[float, float, float]:
    """Narrow a variable-length tuple to a 3-tuple for the type checker."""
    return (v[0], v[1], v[2])


# ---------------------------------------------------------------------------
# Mathematical / Geometrical Helpers
# ---------------------------------------------------------------------------

def _spherical_midpoint(lat1_deg: float, lon1_deg: float,
                        lat2_deg: float, lon2_deg: float) -> tuple[float, float]:
    """Spherical geographic midpoint between two coordinates."""
    phi1, lam1 = math.radians(lat1_deg), math.radians(lon1_deg)
    phi2, lam2 = math.radians(lat2_deg), math.radians(lon2_deg)

    x1 = math.cos(phi1) * math.cos(lam1)
    y1 = math.cos(phi1) * math.sin(lam1)
    z1 = math.sin(phi1)

    x2 = math.cos(phi2) * math.cos(lam2)
    y2 = math.cos(phi2) * math.sin(lam2)
    z2 = math.sin(phi2)

    xm, ym, zm = x1 + x2, y1 + y2, z1 + z2
    rm = math.sqrt(xm * xm + ym * ym + zm * zm)

    if rm < 1e-9:
        return (lat1_deg, lon1_deg)

    phi_m = math.asin(zm / rm)
    lam_m = math.atan2(ym, xm) % (2.0 * math.pi)

    lat_m_deg = math.degrees(phi_m)
    lon_m_deg = math.degrees(lam_m)
    if lon_m_deg > 180.0:
        lon_m_deg -= 360.0

    return (lat_m_deg, lon_m_deg)


def _circular_midpoint(a_rad: float, b_rad: float,
                       ref_asc_rad: float | None = None) -> float:
    """Circular midpoint of two ecliptic longitudes in radians.

    Explicitly resolves the 180-degree midpoint ambiguity by measuring
    towards *ref_asc_rad* (or defaulting to +90 degrees from A).
    """
    a = a_rad % (2.0 * math.pi)
    b = b_rad % (2.0 * math.pi)
    diff = (b - a) % (2.0 * math.pi)
    if diff > math.pi:
        diff -= 2.0 * math.pi

    if abs(abs(diff) - math.pi) < 1e-7:
        cand1 = (a + math.pi / 2.0) % (2.0 * math.pi)
        cand2 = (a - math.pi / 2.0) % (2.0 * math.pi)
        if ref_asc_rad is not None:
            d1 = abs((cand1 - ref_asc_rad + math.pi) % (2.0 * math.pi) - math.pi)
            d2 = abs((cand2 - ref_asc_rad + math.pi) % (2.0 * math.pi) - math.pi)
            return cand1 if d1 <= d2 else cand2
        return cand1
    return (a + diff / 2.0) % (2.0 * math.pi)


def _house_placement(lon_rad: float, cusps: list[dict]) -> int:
    """Determine which house (1-indexed, 1..12) *lon_rad* falls into."""
    c_lons = [c["longitude_rad"] for c in cusps]
    for i in range(12):
        c_curr = c_lons[i]
        c_next = c_lons[(i + 1) % 12]
        span = (c_next - c_curr) % (2.0 * math.pi)
        offset = (lon_rad - c_curr) % (2.0 * math.pi)
        if offset < span:
            return i + 1
    return 1


def _brentq(f: Callable[[float], float], a: float, b: float,
            xtol: float = 1e-9, maxiter: int = 100) -> float:
    """Pure-Python Brent's method for root finding."""
    fa = f(a)
    fb = f(b)
    if fa * fb > 0:
        raise ValueError(f"Root not bracketed: f(a)={fa}, f(b)={fb}")
    if abs(fa) < abs(fb):
        a, b = b, a
        fa, fb = fb, fa
    c = a
    fc = fa
    mflag = True
    d = 0.0
    for _ in range(maxiter):
        if abs(b - a) < xtol or abs(fb) < xtol:
            return b
        if fa != fc and fb != fc:
            s = (a * fb * fc / ((fa - fb) * (fa - fc)) +
                 b * fa * fc / ((fb - fa) * (fb - fc)) +
                 c * fa * fb / ((fc - fa) * (fc - fb)))
        else:
            s = b - fb * (b - a) / (fb - fa)

        cond1 = not ((3 * a + b) / 4 <= s <= b or b <= s <= (3 * a + b) / 4)
        cond2 = mflag and abs(s - b) >= abs(b - c) / 2.0
        cond3 = not mflag and abs(s - b) >= abs(c - d) / 2.0
        cond4 = mflag and abs(b - c) < xtol
        cond5 = not mflag and abs(c - d) < xtol

        if cond1 or cond2 or cond3 or cond4 or cond5:
            s = (a + b) / 2.0
            mflag = True
        else:
            mflag = False

        fs = f(s)
        d = c
        c = b
        fc = fb
        if fa * fs < 0:
            b = s
            fb = fs
        else:
            a = s
            fa = fs
        if abs(fa) < abs(fb):
            a, b = b, a
            fa, fb = fb, fa
    return b


def _newton_bisection(f: Callable[[float], float], a: float, b: float,
                      xtol: float = 1e-9, maxiter: int = 50) -> float:
    """Hybrid Newton-Bisection root finding (finite differences)."""
    fa = f(a)
    fb = f(b)
    if fa * fb > 0:
        raise ValueError(f"Root not bracketed: f(a)={fa}, f(b)={fb}")
    
    if fa > 0:
        a, b = b, a
        fa, fb = fb, fa

    x = 0.5 * (a + b)
    fx = f(x)
    
    for _ in range(maxiter):
        if abs(b - a) < xtol or abs(fx) < xtol:
            return x
            
        eps = 1e-5
        dfx = (f(x + eps) - fx) / eps
        
        if dfx > 0.0:
            next_x = x - fx / dfx
        else:
            next_x = a - 1.0
            
        if (a < next_x < b):
            x = next_x
        else:
            x = 0.5 * (a + b)
            
        fx = f(x)
        
        if fx < 0:
            a = x
        else:
            b = x

    return x


def _get_body_lon_at_jd(jd_utc: float, body_id: int) -> float:
    """Compute ecliptic longitude of body_id at jd_utc."""
    from taiyin_semi_analytic import position as _pos, velocity_icrf as _vel
    jd_tt = jd_ut1_to_tt(jd_utc)
    earth_pos_km = _to_xyz(_pos(jd_tt, 399))
    earth_vel_km_per_day = _to_xyz(_vel(jd_tt, 399))
    earth_pos_au = _to_xyz(tuple(_km_to_au(v) for v in earth_pos_km))
    earth_vel_au_per_day = _to_xyz(tuple(_km_to_au(v) for v in earth_vel_km_per_day))

    geo_au = apply_light_corrections(
        jd_tt,
        lambda jd: _to_xyz(tuple(_km_to_au(v) for v in _pos(jd, body_id))),
        earth_pos_au,
        earth_vel_au_per_day,
        light_time=True,
        aberration=True,
    )
    geo_au = apply_solar_deflection(
        earth_pos_au,
        _to_xyz((earth_pos_au[0] + geo_au[0],
                 earth_pos_au[1] + geo_au[1],
                 earth_pos_au[2] + geo_au[2])),
    )
    from ._precession import rotate_equator_to_ecliptic, _J2000_OBLIQUITY_RAD
    geo_ecl = rotate_equator_to_ecliptic(geo_au, _J2000_OBLIQUITY_RAD)
    ecl_date = j2000_ecliptic_to_date(geo_ecl, jd_tt)
    x, y, z = ecl_date
    return math.atan2(y, x) % (2.0 * math.pi)


def search_solar_longitude(target_lon_rad: float, start_jd: float, end_jd: float) -> float:
    """Find the exact JD when the Sun reaches target_lon_rad within [start_jd, end_jd]."""
    def obj_fn(jd: float) -> float:
        sun_lon = _get_body_lon_at_jd(jd, 10)
        return (sun_lon - target_lon_rad + math.pi) % (2.0 * math.pi) - math.pi
        
    return _newton_bisection(obj_fn, start_jd, end_jd)


def search_lunar_longitude(target_lon_rad: float, start_jd: float, end_jd: float) -> float:
    """Find the exact JD when the Moon reaches target_lon_rad within [start_jd, end_jd]."""
    def obj_fn(jd: float) -> float:
        moon_lon = _get_body_lon_at_jd(jd, 301)
        return (moon_lon - target_lon_rad + math.pi) % (2.0 * math.pi) - math.pi

    return _newton_bisection(obj_fn, start_jd, end_jd)


def search_prenatal_syzygy(birth_jd_utc: float) -> tuple[str, float]:
    """Return (sign_name, degree_in_sign) of the prenatal syzygy point.

    The prenatal syzygy (出生前朔望点) is the last New Moon or Full Moon
    before birth — one of the 5 Hylegial places in medieval astrology.

    Algorithm: search backward from birth in ~14.8-day windows (half the
    synodic month) to bracket the Sun-Moon conjunction or opposition,
    then refine with Newton-Bisection.

    Fallback: if root-finding fails (should never happen), returns natal
    Moon position.
    """
    birth_sun = _get_body_lon_at_jd(birth_jd_utc, 10)
    birth_moon = _get_body_lon_at_jd(birth_jd_utc, 301)

    # If Moon is ahead of Sun by < 180°, we're waxing → last syzygy was New Moon
    # If Moon is ahead of Sun by > 180°, we're waning → last syzygy was Full Moon
    diff = (birth_moon - birth_sun) % (2.0 * math.pi)
    target = 0.0 if diff < math.pi else math.pi

    jd_hi = birth_jd_utc
    for _ in range(5):
        jd_lo = jd_hi - 14.8

        def obj_fn(jd: float) -> float:
            s = _get_body_lon_at_jd(jd, 10)
            m = _get_body_lon_at_jd(jd, 301)
            return (m - s - target + math.pi) % (2.0 * math.pi) - math.pi

        try:
            syzygy_jd = _newton_bisection(obj_fn, jd_lo, jd_hi)
        except ValueError:
            jd_hi = jd_lo
            continue

        syzygy_lon_deg = math.degrees(_get_body_lon_at_jd(syzygy_jd, 301)) % 360.0
        from ._signs import degrees_to_zodiac
        sign, deg = degrees_to_zodiac(syzygy_lon_deg)
        return sign, deg

    # Fallback (should not be reached)
    from ._signs import degrees_to_zodiac
    sign, deg = degrees_to_zodiac(math.degrees(birth_moon) % 360.0)
    return sign, deg


# ---------------------------------------------------------------------------
# Syzygy (朔望月) sequence — for lunar calendar, eclipse search, etc.
# Core algorithm adapted from 寿星万年历 (sxwnl) by 许剑伟.
# ---------------------------------------------------------------------------

SYNODIC_MONTH = 29.530588861  # mean synodic month in days
_J2000 = 2451545.0


def _suo_n(jd_utc: float) -> int:
    """Return the new moon serial number for a given JD_UTC.

    n = 0 corresponds to the new moon nearest to J2000.0.
    """
    return int(math.floor((jd_utc - _J2000) / SYNODIC_MONTH))


def _syzygy_root(n: int, target_rad: float) -> float:
    """Find the exact JD_UTC of the n-th syzygy.

    target_rad = 0 for new moon, target_rad = π for full moon.
    Uses the analytical estimate from 寿星万年历 so_low (error < 2 hours),
    then refines with Newton-Bisection.
    """
    W = n * 2.0 * math.pi + target_rad  # total Moon-Sun phase at syzygy

    # Analytical estimate adapted from 寿星万年历 so_low() — error < 2 hours
    v = 7771.37714500204
    t = (W + 1.08472) / v
    t -= (
        -0.0000331 * t * t
        + 0.10976 * math.cos(0.785 + 8328.6914 * t)
        + 0.02224 * math.cos(0.187 + 7214.0629 * t)
        - 0.03342 * math.cos(4.669 + 628.3076 * t)
    ) / v
    t += (32.0 * (t + 1.8) * (t + 1.8) - 20.0) / 86400.0 / 36525.0
    jd_approx = t * 36525.0 + _J2000  # TT, close enough for bracket

    # Bracket: ±3 days — the analytical estimate can drift ~2 days at extreme
    # epochs (±3000 years) due to secular changes in lunar orbit, but never more.
    jd_lo = jd_approx - 3.0
    jd_hi = jd_approx + 3.0

    def obj_fn(jd: float) -> float:
        s = _get_body_lon_at_jd(jd, 10)
        m = _get_body_lon_at_jd(jd, 301)
        return (m - s - target_rad + math.pi) % (2.0 * math.pi) - math.pi

    return _newton_bisection(obj_fn, jd_lo, jd_hi)


def new_moons_between(jd_start: float, jd_end: float) -> list[float]:
    """Return all new moon JD_UTC values in [jd_start, jd_end]."""
    n_start = _suo_n(jd_start) - 1  # Go one earlier to be safe
    n_end = _suo_n(jd_end) + 1
    results = []
    for n in range(n_start, n_end + 1):
        jd = _syzygy_root(n, 0.0)
        if jd_start <= jd <= jd_end:
            results.append(jd)
    return results


def full_moons_between(jd_start: float, jd_end: float) -> list[float]:
    """Return all full moon JD_UTC values in [jd_start, jd_end]."""
    n_start = _suo_n(jd_start) - 1
    n_end = _suo_n(jd_end) + 1
    results = []
    for n in range(n_start, n_end + 1):
        jd = _syzygy_root(n, math.pi)
        if jd_start <= jd <= jd_end:
            results.append(jd)
    return results



# ---------------------------------------------------------------------------
# Equation of Time & Sunrise/Sunset
# ---------------------------------------------------------------------------
# EoT:  pty_zty2 from 寿星万年历 (sxwnl) — mean vs apparent solar time
# Rise/Set: sunShengJ iterative fixed-point search from sxwnl
# Refraction: hybrid model (Bennett + Smart) from taiyin-ephemeris
# Earth shape: WGS84 ellipsoid → geocentric AU from taiyin-ephemeris
# ---------------------------------------------------------------------------

# WGS84 ellipsoid
_WGS84_A_M = 6378137.0
_WGS84_F = 1.0 / 298.257223563
_WGS84_E2 = _WGS84_F * (2.0 - _WGS84_F)
_AU_M = 149597870700.0

# Solar semi-diameter at 1 AU (mean)
_SUN_SEMI_DIAMETER_RAD = 0.004654  # ~16 arcmin

# Altitude thresholds for twilight (unrefracted geometric; refraction is tiny at these angles)
_TWILIGHT_CIVIL_RAD    = math.radians(-6.0)
_TWILIGHT_NAUTICAL_RAD = math.radians(-12.0)
_TWILIGHT_ASTRONOM_RAD = math.radians(-18.0)

_ARC_MIN_TO_RAD = math.radians(1.0 / 60.0)
_ARC_SEC_TO_RAD = math.radians(1.0 / 3600.0)


# ---------------------------------------------------------------------------
# Refraction
# ---------------------------------------------------------------------------

def _hybrid_refraction_rad(altitude_rad: float, pressure_mbar: float = 1013.25,
                           temperature_c: float = 10.0) -> float:
    """Atmospheric refraction in radians (apparent − geometric altitude).

    Hybrid model from taiyin-ephemeris:
      alt ≥ 16°: Smart formula (58.276 tan z − 0.0824 tan³ z)
      alt ≤ 14°: Bennett formula (1.02 / tan(alt + 10.3/(alt + 5.11)))
      14°–16°:  linear blend between the two

    Scaled by (P / 1010 mbar) × (283 K / T) for non‑standard conditions.
    Returns 0 below −2° geometric altitude.
    """
    temp_k = 273.0 + temperature_c
    if pressure_mbar <= 0.0 or temp_k <= 0.0:
        return 0.0

    alt_deg = math.degrees(altitude_rad)
    if alt_deg < -2.0:
        return 0.0

    # Smart (high altitude)
    z_deg = 90.0 - alt_deg
    tan_z = math.tan(math.radians(z_deg))
    smart_am = (58.276 * tan_z - 0.0824 * tan_z * tan_z * tan_z) / 60.0  # arcmin

    # Bennett (low altitude)
    arg_deg = alt_deg + 10.3 / (alt_deg + 5.11)
    bennett_am = 1.02 / math.tan(math.radians(arg_deg))

    # Blend
    if alt_deg >= 16.0:
        r_am = smart_am
    elif alt_deg <= 14.0:
        r_am = bennett_am
    else:
        w = (alt_deg - 14.0) / 2.0
        r_am = bennett_am * (1.0 - w) + smart_am * w

    if r_am <= 0.0:
        return 0.0

    scale = (pressure_mbar / 1010.0) * (283.0 / temp_k)
    return r_am * scale * _ARC_MIN_TO_RAD


def _sun_rise_set_target_alt(pressure_mbar: float = 1013.25,
                              temperature_c: float = 10.0) -> float:
    """Geometric altitude of Sun's centre at sunrise/set (radians, negative).

    Sunrise/set is defined as the Sun's upper limb touching the apparent
    horizon.  Because refraction lifts the image, the geometric centre must
    be *below* the astronomical horizon by an amount equal to
    refraction + semi‑diameter.

    We iterate 3× to solve  h + refraction(h) = +semi_diameter.
    """
    h = -0.015  # radians ≈ −0.86°  (first guess)
    for _ in range(3):
        ref = _hybrid_refraction_rad(h, pressure_mbar, temperature_c)
        target = _SUN_SEMI_DIAMETER_RAD - ref
        h = target
    return h


def _twilight_target_alt(twilight_rad: float, pressure_mbar: float = 1013.25,
                          temperature_c: float = 10.0) -> float:
    """Geometric altitude for a given twilight definition (radians, negative).

    Civil  = −6°, Nautical = −12°, Astronomical = −18° apparent.
    Refraction is small at these altitudes (≤ 9′), so we apply it directly
    without iteration:  geometric = apparent − refraction.
    """
    ref = _hybrid_refraction_rad(twilight_rad, pressure_mbar, temperature_c)
    return twilight_rad - ref


# ---------------------------------------------------------------------------
# Observer position on Earth
# ---------------------------------------------------------------------------

def _geodetic_to_ecef_au(lon_rad: float, lat_rad: float, height_m: float = 0.0) -> tuple[float, float, float]:
    """WGS84 geodetic → Earth-Centred Earth-Fixed in AU."""
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    n = _WGS84_A_M / math.sqrt(1.0 - _WGS84_E2 * sin_lat * sin_lat)
    x = (n + height_m) * cos_lat * math.cos(lon_rad) / _AU_M
    y = (n + height_m) * cos_lat * math.sin(lon_rad) / _AU_M
    z = (n * (1.0 - _WGS84_E2) + height_m) * sin_lat / _AU_M
    return (x, y, z)


def _observer_geocentric_au(lon_rad: float, lat_rad: float, height_m: float,
                             jd_ut1: float, jd_tt: float) -> tuple[float, float, float]:
    """Observer geocentric position in true equator-of-date equatorial frame (AU).

    ECEF → rotate by GMST → equatorial.  (Polar motion omitted — < 15 m, negligible
    for rise/set timing.)
    """
    from ._time import gmst_rad
    x_ecef, y_ecef, z_ecef = _geodetic_to_ecef_au(lon_rad, lat_rad, height_m)
    gmst = gmst_rad(jd_ut1, jd_tt)
    cos_g = math.cos(gmst)
    sin_g = math.sin(gmst)
    return (
        x_ecef * cos_g - y_ecef * sin_g,
        x_ecef * sin_g + y_ecef * cos_g,
        z_ecef,
    )


# ---------------------------------------------------------------------------
# Topocentric horizontal conversion
# ---------------------------------------------------------------------------

def _topocentric_to_horizontal(topocentric_au: tuple[float, float, float],
                                lst_rad: float, lat_rad: float) -> tuple[float, float]:
    """Equatorial topocentric (AU) → horizontal (azimuth_rad, altitude_rad)."""
    tx, ty, tz = topocentric_au
    # Hour angle
    ha = lst_rad - math.atan2(ty, tx)
    # Local Cartesian: east, north, up
    sin_lat = math.sin(lat_rad)
    cos_lat = math.cos(lat_rad)
    sin_ha = math.sin(ha)
    cos_ha = math.cos(ha)
    r = math.sqrt(tx * tx + ty * ty + tz * tz)
    dec = math.asin(tz / r) if r > 0.0 else 0.0
    # Horizontal
    sin_dec = math.sin(dec)
    cos_dec = math.cos(dec)
    alt = math.asin(sin_lat * sin_dec + cos_lat * cos_dec * cos_ha)
    az = math.atan2(-cos_dec * sin_ha,
                     sin_dec * cos_lat - cos_dec * sin_lat * cos_ha)
    return (az % (2.0 * math.pi), alt)


# ---------------------------------------------------------------------------
# Rise / Set core
# ---------------------------------------------------------------------------

def _sun_rise_set_core(jd_noon_ut: float, lon_rad: float, lat_rad: float,
                        height_m: float, target_alt_rad: float, sj: float,
                        pressure_mbar: float = 1013.25,
                        temperature_c: float = 10.0) -> float | None:
    """Core single-event rise/set calculator using WGS84 ellipsoid + hybrid refraction.

    sj = −1 for rise, +1 for set.  Returns JD_UT or None (polar day/night).
    """
    from ._precession import mean_obliquity_rad
    from ._time import gast_rad, delta_t_seconds_from_jd_ut1, gmst_rad

    # Start from local noon
    jd = math.floor(jd_noon_ut + 0.5) - lon_rad / (2.0 * math.pi)

    for _ in range(3):
        jd_tt = jd_ut1_to_tt(jd)
        jd_ut1 = jd  # UT1 ≈ UTC for this purpose

        # Sun geocentric equatorial position
        obl = mean_obliquity_rad(jd_tt)
        sun_lon = _get_body_lon_at_jd(jd, 10)
        sin_lon = math.sin(sun_lon)
        cos_lon = math.cos(sun_lon)
        cos_obl = math.cos(obl)
        sin_obl = math.sin(obl)
        ra = math.atan2(sin_lon * cos_obl, cos_lon) % (2.0 * math.pi)
        dec = math.asin(sin_obl * sin_lon)
        r_sun_au = 1.0  # ~1 AU, parallax is negligible for the Sun

        # Observer geocentric position
        obs_x, obs_y, obs_z = _observer_geocentric_au(lon_rad, lat_rad, height_m, jd_ut1, jd_tt)

        # Topocentric Sun position (Sun − observer)
        sun_x = r_sun_au * math.cos(dec) * math.cos(ra)
        sun_y = r_sun_au * math.cos(dec) * math.sin(ra)
        sun_z = r_sun_au * math.sin(dec)
        topo = (sun_x - obs_x, sun_y - obs_y, sun_z - obs_z)

        # Local sidereal time
        lst = gast_rad(jd_ut1, jd_tt) + lon_rad

        # Horizontal coordinates
        _, alt = _topocentric_to_horizontal(topo, lst, lat_rad)

        # Refracted altitude
        ref = _hybrid_refraction_rad(alt, pressure_mbar, temperature_c)
        apparent_alt = alt + ref

        # Hour angle at current time
        ha = (lst - ra) % (2.0 * math.pi)
        if ha > math.pi:
            ha -= 2.0 * math.pi

        # Required hour angle for target apparent altitude
        num = math.sin(target_alt_rad) - math.sin(lat_rad) * math.sin(dec)
        den = math.cos(lat_rad) * math.cos(dec)
        if abs(den) < 1e-15:
            return None
        cosH = num / den
        if abs(cosH) >= 1.0:
            return None

        H0 = math.acos(cosH)

        # Correction: difference between required and current hour angle
        djd = (sj * H0 - ha) / (2.0 * math.pi)
        jd += djd

        # Convergence check
        if abs(djd) < 1.0 / 86400.0:  # < 1 second
            break

    return jd


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def equation_of_time_minutes(jd_utc: float) -> float:
    """Equation of time in decimal minutes.

    EoT = apparent solar time − mean solar time.
    Positive → sundial is ahead of clock (true Sun crosses meridian early).

    Ported from 寿星万年历 pty_zty2, error < 1 second.
    """
    jd_tt = jd_ut1_to_tt(jd_utc)
    t = (jd_tt - 2451545.0) / 36525.0  # TT centuries from J2000

    # Mean solar ecliptic longitude (radians), uniform motion
    L_mean = (1753470142.0 + 628331965331.8 * t + 5296.74 * t * t) / 1e9 + math.pi

    # True geocentric solar ecliptic longitude (from body_id=10)
    true_lon = _get_body_lon_at_jd(jd_utc, 10)

    # Obliquity (arcsec → radians)
    obl = (84381.4088 - 46.836051 * t) * _ARC_SEC_TO_RAD

    # True solar Right Ascension (ecliptic → equatorial, solar lat = 0)
    RA_true = math.atan2(math.sin(true_lon) * math.cos(obl), math.cos(true_lon))

    # EoT = mean − true RA → normalize to [−π, π] → convert to minutes
    eot_rad = (L_mean - RA_true + math.pi) % (2.0 * math.pi) - math.pi
    return eot_rad * 1440.0 / (2.0 * math.pi)


def apparent_solar_time_minutes(jd_utc: float, lon_deg: float) -> float:
    """True (apparent) solar time of day in decimal minutes at a given JD and longitude.

    AST = mean solar time at meridian + EoT
        = (UT + lon/15) × 60  +  EoT
    """
    jd = jd_utc + 0.5
    ut_minutes = (jd - int(jd)) * 1440.0
    mean_solar_min = ut_minutes + lon_deg * 4.0
    eot_min = equation_of_time_minutes(jd_utc)
    return (mean_solar_min + eot_min) % 1440.0


def sun_times(year: int, month: int, day: int,
              lon_deg: float, lat_deg: float,
              tz: float = 0.0,
              height_m: float = 0.0,
              pressure_mbar: float = 1013.25,
              temperature_c: float = 10.0) -> dict[str, float | None]:
    """Compute sunrise, sunset, transit, and twilight times.

    WGS84 ellipsoid + hybrid atmospheric refraction model.

    Returns dict with JD_UT values (or None if the event doesn't occur):
        rise, set, transit           — upper limb at apparent horizon
        civil_dawn, civil_dusk       — Sun centre at −6° apparent
        nautical_dawn, nautical_dusk — Sun centre at −12° apparent
        astron_dawn, astron_dusk     — Sun centre at −18° apparent

    height_m:        elevation above sea level (metres)
    pressure_mbar:   station pressure (default 1013.25 = standard)
    temperature_c:   air temperature °C (default 10)
    """
    lon_rad = math.radians(lon_deg)
    lat_rad = math.radians(lat_deg)

    from ._precession import mean_obliquity_rad
    from ._time import gast_rad

    # Approx JD of local noon (UT)
    jd_noon_ut = calendar_to_jd(year, month, day, 12, 0, 0.0) - tz / 24.0

    # Refine to transit
    jd = jd_noon_ut
    for _ in range(2):
        jd_tt = jd_ut1_to_tt(jd)
        jd_ut1 = jd
        obl = mean_obliquity_rad(jd_tt)
        sun_lon = _get_body_lon_at_jd(jd, 10)
        sin_lon = math.sin(sun_lon)
        cos_lon = math.cos(sun_lon)
        cos_obl = math.cos(obl)
        ra = math.atan2(sin_lon * cos_obl, cos_lon) % (2.0 * math.pi)
        lst = gast_rad(jd_ut1, jd_tt) + lon_rad
        ha = (lst - ra + math.pi) % (2.0 * math.pi) - math.pi
        jd -= ha / (2.0 * math.pi)
    transit_jd = jd

    # Target altitudes
    rise_set_alt = _sun_rise_set_target_alt(pressure_mbar, temperature_c)
    civil_alt    = _twilight_target_alt(_TWILIGHT_CIVIL_RAD, pressure_mbar, temperature_c)
    nautical_alt = _twilight_target_alt(_TWILIGHT_NAUTICAL_RAD, pressure_mbar, temperature_c)
    astron_alt   = _twilight_target_alt(_TWILIGHT_ASTRONOM_RAD, pressure_mbar, temperature_c)

    rise  = _sun_rise_set_core(transit_jd, lon_rad, lat_rad, height_m, rise_set_alt, -1.0,
                               pressure_mbar, temperature_c)
    set   = _sun_rise_set_core(transit_jd, lon_rad, lat_rad, height_m, rise_set_alt, +1.0,
                               pressure_mbar, temperature_c)

    c_d  = _sun_rise_set_core(transit_jd, lon_rad, lat_rad, height_m, civil_alt, -1.0,
                              pressure_mbar, temperature_c)
    c_k  = _sun_rise_set_core(transit_jd, lon_rad, lat_rad, height_m, civil_alt, +1.0,
                              pressure_mbar, temperature_c)

    n_d  = _sun_rise_set_core(transit_jd, lon_rad, lat_rad, height_m, nautical_alt, -1.0,
                              pressure_mbar, temperature_c)
    n_k  = _sun_rise_set_core(transit_jd, lon_rad, lat_rad, height_m, nautical_alt, +1.0,
                              pressure_mbar, temperature_c)

    a_d  = _sun_rise_set_core(transit_jd, lon_rad, lat_rad, height_m, astron_alt, -1.0,
                              pressure_mbar, temperature_c)
    a_k  = _sun_rise_set_core(transit_jd, lon_rad, lat_rad, height_m, astron_alt, +1.0,
                              pressure_mbar, temperature_c)

    return {
        "rise": rise, "transit": transit_jd, "set": set,
        "civil_dawn": c_d, "civil_dusk": c_k,
        "nautical_dawn": n_d, "nautical_dusk": n_k,
        "astron_dawn": a_d, "astron_dusk": a_k,
    }



# ---------------------------------------------------------------------------
# Main entry point



# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

class Chart(dict):
    """A calculated astrology chart.

    Dict-like (chart["planets"], chart["houses"], etc.) plus ``set_orb()``
    to tweak aspect orbs after the fact.  The built-in default orb table
    (in ``_aspects.DEFAULT_ORBS``) is never modified.
    """

    def __init__(self, data: dict, body_rates: dict[str, float]):
        super().__init__(data)
        self._body_lons = {k: p["longitude_rad"]
                           for k, p in data["planets"].items()}
        self._body_rates = body_rates
        from ._aspects import DEFAULT_ORBS
        self._orbs: dict[float, float] = dict(DEFAULT_ORBS)

    def set_orb(self, angle: float | str | int, orb_deg: float) -> "Chart":
        """Set aspect *orb_deg* (in degrees) for *angle* and recompute.

        Only recomputes that one angle — other aspects are untouched.
        Pass *orb_deg* = 0.0 to disable the aspect entirely.
        """
        angle = float(angle)
        self._orbs[angle] = float(orb_deg)

        # Delete old entries by aspect_angle_deg (works for custom angles too)
        self["aspects"] = [
            a for a in self["aspects"] if a["aspect_angle_deg"] != angle
        ]

        # Recompute if orb > 0
        if orb_deg > 0.0:
            from ._aspects import _compute_angle_aspects
            self["aspects"].extend(
                _compute_angle_aspects(self._body_lons, angle, orb_deg,
                                       self._body_rates))
        return self

    def reset_orb(self, angle: float | str | int) -> "Chart":
        """Restore the default orb for *angle*."""
        from ._aspects import DEFAULT_ORBS
        if float(angle) in DEFAULT_ORBS:
            self.set_orb(angle, DEFAULT_ORBS[float(angle)])
        return self

    def firdaria(self, age: float | None = None, *, nodes_after_mercury: bool = True):
        """Calculate Firdaria (法达星限法).

        If *age* (years) is given, returns current active Major & Minor Firdar.
        If *age* is None, returns full Firdaria timeline.
        *nodes_after_mercury*: If True (default/爱星盘流派), places Lunar Nodes after Mercury/sequence.
        """
        from ._firdaria import calc_firdaria_timeline, get_current_firdaria
        sun_lon = self["planets"]["sun"]["longitude_rad"]
        asc_lon = self["houses"]["ascendant"]["longitude_rad"]
        is_day_chart = ((sun_lon - asc_lon) % (2.0 * math.pi)) > math.pi

        if age is not None:
            return get_current_firdaria(is_day_chart, age, nodes_after_mercury)
        return calc_firdaria_timeline(is_day_chart, nodes_after_mercury)

    def profection(self, age: float, *, start_point: str = "ascendant") -> dict:
        """Calculate Annual, Monthly, and Daily Profections (小限推运).

        *age*: Age in years (e.g. 21.0).
        *start_point*: 'ascendant', 'sun', 'moon', or a custom point name.
        """
        from ._profections import calc_profection
        asc_info = self["houses"]["ascendant"]
        asc_deg = sign_name_to_longitude(asc_info["sign"], asc_info["degree"] + asc_info["minute"] / 60.0)

        start_deg = asc_deg
        if start_point.lower() == "sun":
            sun_p = self["planets"]["sun"]
            start_deg = sign_name_to_longitude(sun_p["sign"], sun_p["degree"] + sun_p["minute"] / 60.0)
        elif start_point.lower() == "moon":
            moon_p = self["planets"]["moon"]
            start_deg = sign_name_to_longitude(moon_p["sign"], moon_p["degree"] + moon_p["minute"] / 60.0)
        elif start_point in self["planets"]:
            p = self["planets"][start_point]
            start_deg = sign_name_to_longitude(p["sign"], p["degree"] + p["minute"] / 60.0)
            
        return calc_profection(asc_deg, age, start_point_deg=start_deg)

    def ayanamsha(self, mode: str = "lahiri") -> float:
        """Calculate Sidereal Ayanamsha (度数) for this chart.

        *mode*: 'lahiri', 'true_chitra'/'true_lahiri', 'fagan_bradley', 'raman', 'krishnamurti', 'yukteswar'.
        """
        from ._ayanamsha import calc_ayanamsha_deg
        return calc_ayanamsha_deg(self["jd_tt"], mode)

    def sidereal_planets(self, mode: str = "lahiri") -> dict:
        """Get all planet positions converted to Sidereal Zodiac (恒星黄道)."""
        from ._ayanamsha import calc_ayanamsha_deg
        from ._signs import degrees_to_zodiac
        ayan = calc_ayanamsha_deg(self["jd_tt"], mode)
        
        result = {"ayanamsha_deg": round(ayan, 4), "mode": mode, "planets": {}}
        for k, p in self["planets"].items():
            trop_lon = math.degrees(p["longitude_rad"])
            sid_lon = (trop_lon - ayan) % 360.0
            sign, deg_in_sign = degrees_to_zodiac(sid_lon)
            result["planets"][k] = {
                "name": p["name"],
                "sidereal_longitude_deg": round(sid_lon, 4),
                "sign": sign,
                "degree_in_sign": round(deg_in_sign, 4)
            }
        return result

    def zodiacal_releasing(self, lot: str = "spirit", age: float | None = None) -> dict:
        """Calculate Zodiacal Releasing (希腊化黄道释放).

        *lot*: 'spirit' (精神点/事业), 'fortune' (福德点/健康), 'eros' (桃花/欲望).
        *age*: If given, returns active L1 and L2 periods for that age. If None, returns L1 timeline.
        """
        from ._zodiacal_releasing import calc_zr_l1_periods, get_current_zr
        lot_key = lot.lower()
        if lot_key not in self["lots"]:
            lot_key = "spirit"
            
        start_sign = self["lots"][lot_key]["sign"]
        
        if age is not None:
            return get_current_zr(start_sign, age)
        return {"lot": lot_key, "start_sign": start_sign, "l1_timeline": calc_zr_l1_periods(start_sign)}

    def almuten_figuris(self, school: str = "ibn_ezra") -> dict:
        """Calculate Almuten Figuris (生命主宰星 / 胜者星算法).

        *school*: 'ibn_ezra' (standard), 'bonatti' (strict sect triplicity), 'lilly' (cadent filter).
        """
        from ._almuten import calculate_almuten_figuris
        return calculate_almuten_figuris(self, school=school)

    def vimshottari_dasha(self, age: float | None = None, *, ayanamsha_mode: str = "lahiri", max_level: int = 5) -> dict:
        """Calculate Vimshottari Dasha (印度 120 年九曜大运 - 五级递归展开).

        *age*: If given, returns active Dasha hierarchy down to *max_level* (1 to 5).
        *max_level*: 1=Mahadasha, 2=Antardasha, 3=Pratyantardasha, 4=Sookshma, 5=Prana.
        *ayanamsha_mode*: 'lahiri', 'true_chitra'/'true_lahiri', 'fagan_bradley', 'raman', 'krishnamurti', 'yukteswar'.
        """
        from ._dasha import calc_vimshottari_timeline, get_current_dasha
        from ._ayanamsha import calc_ayanamsha_deg
        
        moon_trop_lon = math.degrees(self["planets"]["moon"]["longitude_rad"])
        ayan = calc_ayanamsha_deg(self["jd_tt"], ayanamsha_mode)
        sid_moon_lon = (moon_trop_lon - ayan) % 360.0
        
        if age is not None:
            return get_current_dasha(sid_moon_lon, age, max_level=max_level)
        return {
            "ayanamsha_mode": ayanamsha_mode,
            "sidereal_moon_lon_deg": round(sid_moon_lon, 4),
            "timeline": calc_vimshottari_timeline(sid_moon_lon)
        }

    def divisional_charts(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Indian Divisional Charts (十六大分盘 Shodasha Vargas & D9 Navamsha).

        Calculates D1 (Rashi), D3 (Drekkana), D9 (Navamsha), D10 (Dasamsa), D12 (Dwadasamsa), D60 (Shashtiamsa),
        and identifies Vargottama planets (同度共鸣).
        """
        from ._vargas import calculate_divisional_charts
        return calculate_divisional_charts(self, ayanamsha_mode=ayanamsha_mode)

    def primary_directions(self, key: str = "naibod", mode: str = "direct", system: str = "zodiacal") -> list:
        """Calculate Primary Directions (西方古典主限法 / 弓限轴向推运).

        *key*: 'naibod' (0°59'08"/yr), 'ptolemy' (1°/yr), 'true_sun' (Cardan true Sun motion).
        *mode*: 'direct' (顺向), 'converse' (逆向).
        *system*: 'zodiacal' (黄道弧), 'placidus' (普拉西德半弧).
        """
        from ._primary_directions import calc_primary_directions
        return calc_primary_directions(self, key=key, mode=mode, system=system)

    def bhava_chalit(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Bhava Chalit (印占宫位调整盘).

        Determines if planets shift houses based on exact Ascendant degree cusps.
        """
        from ._bhava_gochar import calc_bhava_chalit
        return calc_bhava_chalit(self, ayanamsha_mode=ayanamsha_mode)

    def sade_sati(self, transit_saturn_sidereal_sign: str, ayanamsha_mode: str = "lahiri") -> dict:
        """Check Indian Sade Sati (土星萨德萨蒂 - 7.5年大难/考验运).

        *transit_saturn_sidereal_sign*: Current transit Saturn sign in Sidereal Zodiac.
        """
        from ._bhava_gochar import calc_sade_sati
        from ._ayanamsha import calc_ayanamsha_deg
        from ._signs import degrees_to_zodiac
        
        moon_trop_lon = math.degrees(self["planets"]["moon"]["longitude_rad"])
        ayan = calc_ayanamsha_deg(self["jd_tt"], ayanamsha_mode)
        sid_moon_lon = (moon_trop_lon - ayan) % 360.0
        moon_sign, _ = degrees_to_zodiac(sid_moon_lon)
        
        return calc_sade_sati(moon_sign, transit_saturn_sidereal_sign)

    def upagrahas(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Indian Upagrahas (五大太阳虚星: Dhuma, Vyatipata, Parivesha, Indrachapa, Upaketu)."""
        from ._jyotish_master import calc_upagrahas
        from ._ayanamsha import calc_ayanamsha_deg
        sun_trop_lon = math.degrees(self["planets"]["sun"]["longitude_rad"])
        ayan = calc_ayanamsha_deg(self["jd_tt"], ayanamsha_mode)
        sid_sun_lon = (sun_trop_lon - ayan) % 360.0
        return calc_upagrahas(sid_sun_lon)

    def kp_sublord(self, planet: str = "moon", ayanamsha_mode: str = "kp") -> dict:
        """Calculate KP System Star-Lord and Sub-Lord (KP 派星主与副主星)."""
        from ._jyotish_master import calc_kp_sublord
        from ._ayanamsha import calc_ayanamsha_deg
        p_name = planet.lower()
        p_trop_lon = math.degrees(self["planets"][p_name]["longitude_rad"])
        ayan = calc_ayanamsha_deg(self["jd_tt"], ayanamsha_mode)
        sid_lon = (p_trop_lon - ayan) % 360.0
        return calc_kp_sublord(sid_lon)

    def panchadha_maitri(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Panchadha Maitri (五分法印占复合敌友关系)."""
        from ._jyotish_master import calc_panchadha_maitri
        return calc_panchadha_maitri(self, ayanamsha_mode=ayanamsha_mode)

    def jaimini_chara_karakas(self, scheme: str = "7_karaka", ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Jaimini Chara Karakas (贾伊米尼动态生命星系).

        *scheme*: '7_karaka' (7星制) or '8_karaka' (8星制含罗睺).
        """
        from ._jaimini_huber import calc_jaimini_chara_karakas
        return calc_jaimini_chara_karakas(self, scheme=scheme, ayanamsha_mode=ayanamsha_mode)

    def huber_age_point(self, age_years: float) -> dict:
        """Calculate Huber School Age Point (胡伯心理学派 6年/宫 年龄点推运)."""
        from ._jaimini_huber import calc_huber_age_point
        return calc_huber_age_point(self, age_years)

    def ashtakavarga(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Sarvashtakavarga (八分点/行运力量评估 337点系统)."""
        from ._ashtakavarga import calc_ashtakavarga
        return calc_ashtakavarga(self, ayanamsha_mode=ayanamsha_mode)

    def arudha_padas(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Jaimini Arudha Padas (贾伊米尼虚象宫/映射宫位 A1-A12)."""
        from ._arudha_pada import calc_arudha_padas
        return calc_arudha_padas(self, ayanamsha_mode=ayanamsha_mode)

    def yogini_dasha(self, age_years: float = 0.0, ayanamsha_mode: str = "lahiri",
                     max_level: int = 2) -> dict:
        """Calculate Yogini Dasha (瑜伽女神大运 36年周期)."""
        from ._yogini_dasha import calc_yogini_dasha
        return calc_yogini_dasha(self, age_years=age_years, ayanamsha_mode=ayanamsha_mode, max_level=max_level)

    def nakshatra_chart(self, ayanamsha_mode: str = "lahiri", system: str = "27") -> dict:
        """Calculate Nakshatra positions for all planets (27/28 星宿系统).

        *system*: '27' (标准) or '28' (含 Abhijit 毕宿).
        """
        from ._nakshatra import calc_nakshatra_chart
        return calc_nakshatra_chart(self, ayanamsha_mode=ayanamsha_mode, system=system)

    def nakshatra_compatibility(self, other: "Chart", ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Nakshatra-based Ashta Kuta compatibility (合婚八元素评分)."""
        from ._nakshatra import calc_nakshatra_compatibility, get_nakshatra_info
        from ._ayanamsha import calc_ayanamsha_deg
        ayan_a = calc_ayanamsha_deg(self["jd_tt"], ayanamsha_mode)
        ayan_b = calc_ayanamsha_deg(other["jd_tt"], ayanamsha_mode)
        moon_a = (math.degrees(self["planets"]["moon"]["longitude_rad"]) - ayan_a) % 360.0
        moon_b = (math.degrees(other["planets"]["moon"]["longitude_rad"]) - ayan_b) % 360.0
        nak_a = get_nakshatra_info(moon_a)
        nak_b = get_nakshatra_info(moon_b)
        compat = calc_nakshatra_compatibility(nak_a["index"], nak_b["index"])
        compat["person_a_nakshatra"] = nak_a["name"]
        compat["person_b_nakshatra"] = nak_b["name"]
        return compat

    def karakas(self, ayanamsha_mode: str = "lahiri", chara_scheme: str = "7_karaka") -> dict:
        """Calculate all three Karaka (指标星) systems: Naisargika + Sthira + Chara."""
        from ._karaka import calc_all_karakas
        return calc_all_karakas(self, ayanamsha_mode=ayanamsha_mode, chara_scheme=chara_scheme)

    def translation_of_light(self, include_modern: bool = False, orb_mode: str = "moiety") -> list:
        """Calculate Classical/Modern Translation of Light (传光 / 光线传递).
        
        *orb_mode*: 'moiety' (古典星体光芒半径和), 'aspect_orbs' (按相位容许度表), 'fixed_5deg' (固定5度).
        """
        from ._light_aspects import calc_translation_of_light
        return calc_translation_of_light(self, include_modern=include_modern, orb_mode=orb_mode)

    def collection_of_light(self, include_modern: bool = False, orb_mode: str = "moiety") -> list:
        """Calculate Classical/Modern Collection of Light (聚光 / 光线汇聚)."""
        from ._light_aspects import calc_collection_of_light
        return calc_collection_of_light(self, include_modern=include_modern, orb_mode=orb_mode)

    def besiegement(self, include_modern: bool = False, orb_mode: str = "moiety") -> list:
        """Calculate Besiegement by Light/Aspects (光线/相位围攻)."""
        from ._light_aspects import calc_besiegement
        return calc_besiegement(self, include_modern=include_modern, orb_mode=orb_mode)

    def prohibition(self, include_modern: bool = False, orb_mode: str = "moiety") -> list:
        """Calculate Prohibition of Light (阻隔 / 绝光)."""
        from ._light_aspects import calc_prohibition
        return calc_prohibition(self, include_modern=include_modern, orb_mode=orb_mode)

    def moiety_of_orbs(self, planet1: str, planet2: str) -> float:
        """Calculate Moiety of Orbs (古典双星光芒容许度交叠上限度数)."""
        from ._light_aspects import get_moiety_of_orbs
        return get_moiety_of_orbs(planet1, planet2)

    # -- convenience accessors --

    def planet(self, name: str) -> dict:
        """Return a planet dict e.g. chart.planet('sun')."""
        return self["planets"][name]

    @property
    def planets(self) -> list[str]:
        """List of planet keys."""
        return list(self["planets"].keys())

    def house_cusp(self, n: int) -> dict:
        """Return house *n* cusp (1-indexed) e.g. chart.house_cusp(1)."""
        return self["houses"]["cusps"][n - 1]

    @property
    def ascendant(self) -> dict:
        return self["houses"]["ascendant"]

    @property
    def midheaven(self) -> dict:
        return self["houses"]["midheaven"]

    @property
    def vertex(self) -> dict:
        return self["houses"]["vertex"]

    def aspects_to(self, body: str) -> list[dict]:
        """All aspects involving *body*."""
        return [a for a in self["aspects"]
                if a["body1"] == body or a["body2"] == body]

    def aspects_between(self, a: str, b: str) -> list[dict]:
        """Aspects between two specific bodies."""
        return [x for x in self["aspects"]
                if {x["body1"], x["body2"]} == {a, b}]

    # -- synastry / composite / davison --

    def synastry_with(self, other: "Chart") -> dict:
        """Synastry relationship analysis between two charts.

        Returns a dictionary containing:
        - ``cross_aspects``: list of aspects strictly between Chart A and Chart B
        - ``chart_a_in_chart_b_houses``: house placement of Chart A bodies in B
        - ``chart_b_in_chart_a_houses``: house placement of Chart B bodies in A
        """
        cross_aspects = []
        for b1_key, lon1 in self._body_lons.items():
            rate1 = self._body_rates.get(b1_key, 0.0)
            for b2_key, lon2 in other._body_lons.items():
                rate2 = other._body_rates.get(b2_key, 0.0)
                diff_deg = math.degrees((lon2 - lon1) % (2.0 * math.pi))
                if diff_deg > 180.0:
                    diff_deg = 360.0 - diff_deg
                for aspect_angle, orb in self._orbs.items():
                    if orb <= 0.0:
                        continue
                    orb_val = abs(diff_deg - aspect_angle)
                    if orb_val <= orb:
                        rel_rate = rate2 - rate1
                        ang_dist = (lon2 - lon1) % (2.0 * math.pi)
                        target_rad = math.radians(aspect_angle)
                        applying = (rel_rate * (ang_dist - target_rad)) < 0 if rel_rate != 0 else False
                        name = _ANGLE_NAMES.get(aspect_angle, f"{aspect_angle}°")
                        cross_aspects.append({
                            "chart_a_body": b1_key,
                            "chart_b_body": b2_key,
                            "aspect": name,
                            "aspect_angle_deg": aspect_angle,
                            "orb_deg": round(orb_val, 4),
                            "applying": applying,
                        })

        a_in_b = {k: _house_placement(lon, other["houses"]["cusps"])
                  for k, lon in self._body_lons.items()}
        b_in_a = {k: _house_placement(lon, self["houses"]["cusps"])
                  for k, lon in self._body_lons.items()}

        return {
            "chart_a_in_chart_b_houses": a_in_b,
            "chart_b_in_chart_a_houses": b_in_a,
            "cross_aspects": cross_aspects,
        }

    def composite_with(self, other: "Chart") -> "Chart":
        """Midpoint composite chart between two natal charts."""
        ref_asc = self["houses"]["ascendant"]["longitude_rad"]
        comp_body_lons = {}
        planets = {}
        for key in self._body_lons:
            if key in other._body_lons:
                lon_a = self._body_lons[key]
                lon_b = other._body_lons[key]
                m_lon = _circular_midpoint(lon_a, lon_b, ref_asc_rad=ref_asc)
                lat_a = self["planets"][key]["latitude_rad"]
                lat_b = other["planets"][key]["latitude_rad"]
                m_lat = (lat_a + lat_b) / 2.0
                dist_a = self["planets"][key]["distance_au"]
                dist_b = other["planets"][key]["distance_au"]
                m_dist = (dist_a + dist_b) / 2.0

                comp_body_lons[key] = m_lon
                sign_info, deg, min_ = sign_degree_minute(m_lon)
                planets[key] = {
                    "name": self["planets"][key]["name"],
                    "longitude_rad": m_lon,
                    "latitude_rad": m_lat,
                    "distance_au": m_dist,
                    "sign": sign_info.name,
                    "sign_abbrev": sign_info.abbrev,
                    "degree": deg,
                    "minute": min_,
                    "retrograde": False,
                }

        # Composite houses via ARMC midpoint
        armc_a = self["houses"]["armc_rad"]
        armc_b = other["houses"]["armc_rad"]
        comp_armc = _circular_midpoint(armc_a, armc_b, ref_asc_rad=ref_asc)

        lat_m_deg, lon_m_deg = _spherical_midpoint(
            self["observer"]["lat_deg"], self["observer"]["lon_deg"],
            other["observer"]["lat_deg"], other["observer"]["lon_deg"],
        )

        jd_mid = (self["jd_utc"] + other["jd_utc"]) / 2.0
        jd_tt_mid = jd_ut1_to_tt(jd_mid)
        obl = mean_obliquity_rad(jd_tt_mid)

        hs = HouseSystem(self["houses"]["system"])
        houses_data = calc_houses(comp_armc - math.radians(lon_m_deg),
                                  math.radians(lon_m_deg),
                                  math.radians(lat_m_deg),
                                  obl, hs)

        aspects = find_all_aspects(comp_body_lons)
        y, mo, d, h, mi, s = jd_to_calendar(jd_mid)

        data = {
            "jd_utc": jd_mid,
            "jd_tt": jd_tt_mid,
            "delta_t_s": delta_t_seconds_from_jd_ut1(jd_mid),
            "date_utc": f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{int(s):02d}Z",
            "observer": {
                "lat_deg": lat_m_deg,
                "lon_deg": lon_m_deg,
            },
            "planets": planets,
            "houses": {
                "system": houses_data["system"].value,
                "armc_rad": houses_data["armc_rad"],
                "ascendant": _format_angle(houses_data["ascendant_rad"]),
                "midheaven": _format_angle(houses_data["midheaven_rad"]),
                "vertex": _format_angle(houses_data["vertex_rad"]),
                "east_point": _format_angle(houses_data["east_point_rad"]),
                "cusps": [_format_angle(c) for c in houses_data["cusps_rad"]],
            },
            "aspects": aspects,
        }
        rates = {k: 0.0 for k in comp_body_lons}
        return Chart(data, rates)

    def davison_with(self, other: "Chart", *, mode: str = "spherical") -> "Chart":
        """Davison relationship chart (time and geographic midpoint).

        *mode* can be:
        - ``"spherical"``: 3D vector spherical geographic midpoint (default)
        - ``"arithmetic"``: simple arithmetic average of latitude and longitude
        """
        jd_mid = (self["jd_utc"] + other["jd_utc"]) / 2.0
        if mode == "arithmetic":
            lat_m_deg = (self["observer"]["lat_deg"] + other["observer"]["lat_deg"]) / 2.0
            lon_m_deg = (self["observer"]["lon_deg"] + other["observer"]["lon_deg"]) / 2.0
        else:
            lat_m_deg, lon_m_deg = _spherical_midpoint(
                self["observer"]["lat_deg"], self["observer"]["lon_deg"],
                other["observer"]["lat_deg"], other["observer"]["lon_deg"],
            )

        return calculate_chart(
            *self._jd_to_cal(jd_mid),
            tz=0.0,
            latitude_deg=lat_m_deg,
            longitude_deg=lon_m_deg,
        )

    # -- progressions / directions --

    def secondary_progression(self, age_years: float | None = None, *,
                              years: float | None = None,
                              target_jd: float | None = None,
                              latitude_deg: float | None = None,
                              longitude_deg: float | None = None) -> "Chart":
        """Secondary progression (1 ephemeris day per tropical year of life).

        Pass either *age_years* (or *years*), or *target_jd*.
        Note: Age 30 corresponds to 30 ephemeris days after birth.
        """
        val_years = age_years if age_years is not None else years
        if target_jd is not None:
            elapsed_years = (target_jd - self["jd_utc"]) / TROPICAL_YEAR_DAYS
            jd_prog = self["jd_utc"] + elapsed_years
        elif val_years is not None:
            jd_prog = self["jd_utc"] + val_years
        else:
            raise ValueError("Must specify either age_years/years or target_jd")

        lat = latitude_deg if latitude_deg is not None else self["observer"]["lat_deg"]
        lon = longitude_deg if longitude_deg is not None else self["observer"]["lon_deg"]
        return calculate_chart(
            *self._jd_to_cal(jd_prog),
            tz=0.0,
            latitude_deg=lat,
            longitude_deg=lon,
        )

    def progressed(self, years: float, rate: float = 1.0) -> "Chart":
        """Backwards-compatible alias for secondary progression."""
        return self.secondary_progression(age_years=years * rate)

    def tertiary_i(self, age_years: float | None = None, *,
                   years: float | None = None,
                   target_jd: float | None = None,
                   latitude_deg: float | None = None,
                   longitude_deg: float | None = None) -> "Chart":
        """Tertiary Progression I (1 ephemeris day per 27.32158218 days of life)."""
        val_years = age_years if age_years is not None else years
        if target_jd is not None:
            elapsed_life_days = target_jd - self["jd_utc"]
        elif val_years is not None:
            elapsed_life_days = val_years * TROPICAL_YEAR_DAYS
        else:
            raise ValueError("Must specify either age_years/years or target_jd")

        ephemeris_days_offset = elapsed_life_days / ASTRODIENST_TROPICAL_MONTH_DAYS
        jd_prog = self["jd_utc"] + ephemeris_days_offset
        lat = latitude_deg if latitude_deg is not None else self["observer"]["lat_deg"]
        lon = longitude_deg if longitude_deg is not None else self["observer"]["lon_deg"]
        return calculate_chart(
            *self._jd_to_cal(jd_prog),
            tz=0.0,
            latitude_deg=lat,
            longitude_deg=lon,
        )

    def tertiary_ii(self, age_years: float | None = None, *,
                    years: float | None = None,
                    target_jd: float | None = None,
                    latitude_deg: float | None = None,
                    longitude_deg: float | None = None) -> "Chart":
        """Tertiary Progression II (27.32158218 ephemeris days per tropical year of life).

        Astrodienst compatible constant: 27.32158218 ephemeris days = 1 year of life.
        """
        val_years = age_years if age_years is not None else years
        if target_jd is not None:
            elapsed_life_years = (target_jd - self["jd_utc"]) / TROPICAL_YEAR_DAYS
        elif val_years is not None:
            elapsed_life_years = val_years
        else:
            raise ValueError("Must specify either age_years/years or target_jd")

        ephemeris_days_offset = elapsed_life_years * ASTRODIENST_TROPICAL_MONTH_DAYS
        jd_prog = self["jd_utc"] + ephemeris_days_offset
        lat = latitude_deg if latitude_deg is not None else self["observer"]["lat_deg"]
        lon = longitude_deg if longitude_deg is not None else self["observer"]["lon_deg"]
        return calculate_chart(
            *self._jd_to_cal(jd_prog),
            tz=0.0,
            latitude_deg=lat,
            longitude_deg=lon,
        )

    def tertiary_progression(self, age_years: float | None = None, *,
                             years: float | None = None,
                             target_jd: float | None = None,
                             latitude_deg: float | None = None,
                             longitude_deg: float | None = None) -> "Chart":
        """Alias for tertiary_i."""
        return self.tertiary_i(age_years=age_years, years=years, target_jd=target_jd,
                               latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    def minor_progression(self, age_years: float | None = None, *,
                          years: float | None = None,
                          target_jd: float | None = None,
                          latitude_deg: float | None = None,
                          longitude_deg: float | None = None) -> "Chart":
        """Alias for tertiary_ii."""
        return self.tertiary_ii(age_years=age_years, years=years, target_jd=target_jd,
                                latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    def solar_arc(self, age_years: float | None = None, *,
                  years: float | None = None,
                  target_jd: float | None = None) -> "Chart":
        """True Solar Arc directed chart — advance all positions by Sun's secondary arc."""
        val_years = age_years if age_years is not None else years
        prog = self.secondary_progression(age_years=val_years, target_jd=target_jd)
        natal_sun_lon = self["planets"]["sun"]["longitude_rad"]
        prog_sun_lon = prog["planets"]["sun"]["longitude_rad"]
        arc = (prog_sun_lon - natal_sun_lon) % (2.0 * math.pi)

        # Shift all planets
        shifted_planets = {}
        shifted_body_lons = {}
        for k, p in self["planets"].items():
            new_lon = (p["longitude_rad"] + arc) % (2.0 * math.pi)
            shifted_body_lons[k] = new_lon
            sign_info, deg, min_ = sign_degree_minute(new_lon)
            shifted_planets[k] = {
                "name": p["name"],
                "longitude_rad": new_lon,
                "latitude_rad": p["latitude_rad"],
                "distance_au": p["distance_au"],
                "sign": sign_info.name,
                "sign_abbrev": sign_info.abbrev,
                "degree": deg,
                "minute": min_,
                "retrograde": p.get("retrograde", False),
            }

        # Shift houses & angles
        old_h = self["houses"]
        shifted_houses = {
            "system": old_h["system"],
            "armc_rad": (old_h["armc_rad"] + arc) % (2.0 * math.pi),
            "ascendant": _format_angle((old_h["ascendant"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "midheaven": _format_angle((old_h["midheaven"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "vertex": _format_angle((old_h["vertex"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "east_point": _format_angle((old_h["east_point"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "cusps": [_format_angle((c["longitude_rad"] + arc) % (2.0 * math.pi))
                      for c in old_h["cusps"]],
        }

        aspects = find_all_aspects(shifted_body_lons, body_rates=self._body_rates)

        data = dict(self)
        data["planets"] = shifted_planets
        data["houses"] = shifted_houses
        data["aspects"] = aspects
        return Chart(data, self._body_rates)

    def naibod_direction(self, age_years: float | None = None, *,
                         years: float | None = None,
                         target_jd: float | None = None) -> "Chart":
        """Naibod arc direction chart — advance all positions by mean solar motion (~0.98564733 deg/year)."""
        val_years = age_years if age_years is not None else years
        if target_jd is not None:
            val_years = (target_jd - self["jd_utc"]) / TROPICAL_YEAR_DAYS
        elif val_years is None:
            raise ValueError("Must specify either age_years/years or target_jd")

        arc = math.radians(val_years * 0.98564733)

        shifted_planets = {}
        shifted_body_lons = {}
        for k, p in self["planets"].items():
            new_lon = (p["longitude_rad"] + arc) % (2.0 * math.pi)
            shifted_body_lons[k] = new_lon
            sign_info, deg, min_ = sign_degree_minute(new_lon)
            shifted_planets[k] = {
                "name": p["name"],
                "longitude_rad": new_lon,
                "latitude_rad": p["latitude_rad"],
                "distance_au": p["distance_au"],
                "sign": sign_info.name,
                "sign_abbrev": sign_info.abbrev,
                "degree": deg,
                "minute": min_,
                "retrograde": p.get("retrograde", False),
            }

        old_h = self["houses"]
        shifted_houses = {
            "system": old_h["system"],
            "armc_rad": (old_h["armc_rad"] + arc) % (2.0 * math.pi),
            "ascendant": _format_angle((old_h["ascendant"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "midheaven": _format_angle((old_h["midheaven"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "vertex": _format_angle((old_h["vertex"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "east_point": _format_angle((old_h["east_point"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "cusps": [_format_angle((c["longitude_rad"] + arc) % (2.0 * math.pi))
                      for c in old_h["cusps"]],
        }

        aspects = find_all_aspects(shifted_body_lons, body_rates=self._body_rates)

        data = dict(self)
        data["planets"] = shifted_planets
        data["houses"] = shifted_houses
        data["aspects"] = aspects
        return Chart(data, self._body_rates)

    # -- returns --

    def solar_return(self, target_year: int, *,
                     latitude_deg: float | None = None,
                     longitude_deg: float | None = None) -> "Chart":
        """Solar Return chart for target_year solving exact Sun longitude recurrence."""
        natal_sun_lon = self["planets"]["sun"]["longitude_rad"]
        lat = latitude_deg if latitude_deg is not None else self["observer"]["lat_deg"]
        lon = longitude_deg if longitude_deg is not None else self["observer"]["lon_deg"]

        y, mo, d, h, mi, s = self._jd_to_cal(self["jd_utc"])
        elapsed_years = target_year - y
        jd_approx = self["jd_utc"] + elapsed_years * TROPICAL_YEAR_DAYS

        def obj_fn(jd: float) -> float:
            sun_lon = _get_body_lon_at_jd(jd, 10)
            return (sun_lon - natal_sun_lon + math.pi) % (2.0 * math.pi) - math.pi

        a, b = jd_approx - 5.0, jd_approx + 5.0
        if obj_fn(a) * obj_fn(b) > 0:
            a, b = jd_approx - 15.0, jd_approx + 15.0
            if obj_fn(a) * obj_fn(b) > 0:
                raise ValueError(f"Solar return not bracketed. Guess was jd={jd_approx}")

        jd_exact = search_solar_longitude(natal_sun_lon, a, b)
        return calculate_chart(*self._jd_to_cal(jd_exact), tz=0.0,
                               latitude_deg=lat, longitude_deg=lon)

    def lunar_return(self, target_year: int, target_month: int, *,
                     latitude_deg: float | None = None,
                     longitude_deg: float | None = None) -> "Chart":
        """Lunar Return chart for target_year & target_month solving exact Moon longitude recurrence."""
        natal_moon_lon = self["planets"]["moon"]["longitude_rad"]
        lat = latitude_deg if latitude_deg is not None else self["observer"]["lat_deg"]
        lon = longitude_deg if longitude_deg is not None else self["observer"]["lon_deg"]

        target_jd_approx = calendar_to_jd(target_year, target_month, 15, 12, 0, 0.0)
        elapsed_days = target_jd_approx - self["jd_utc"]
        lunar_cycles = round(elapsed_days / ASTRODIENST_TROPICAL_MONTH_DAYS)
        jd_approx = self["jd_utc"] + lunar_cycles * ASTRODIENST_TROPICAL_MONTH_DAYS

        def obj_fn(jd: float) -> float:
            moon_lon = _get_body_lon_at_jd(jd, 301)
            return (moon_lon - natal_moon_lon + math.pi) % (2.0 * math.pi) - math.pi

        a, b = jd_approx - 2.5, jd_approx + 2.5
        if obj_fn(a) * obj_fn(b) > 0:
            raise ValueError(f"Lunar return not bracketed in +/- 2.5 days. Guess was jd={jd_approx}")

        jd_exact = search_lunar_longitude(natal_moon_lon, a, b)
        return calculate_chart(*self._jd_to_cal(jd_exact), tz=0.0,
                               latitude_deg=lat, longitude_deg=lon)

    # -- derived methods (compositions) --

    def composite_secondary(self, other: "Chart", years: float,
                            latitude_deg: float | None = None,
                            longitude_deg: float | None = None) -> "Chart":
        """Derived method: Composite chart secondary progression."""
        return self.composite_with(other).secondary_progression(
            age_years=years, latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    def davison_tertiary(self, other: "Chart", years: float,
                         latitude_deg: float | None = None,
                         longitude_deg: float | None = None) -> "Chart":
        """Derived method: Davison chart tertiary progression (Tertiary I)."""
        return self.davison_with(other).tertiary_i(
            age_years=years, latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    def marks_with(self, other: "Chart", *, mode: str = "davison") -> "Chart":
        """Marks Relationship Chart (马盘).

        The chart of one person's internal experience of the relationship.
        Calculated as the midpoint between the natal chart (self) and the relationship chart.

        *mode* can be:
        - ``"davison"`` (default): self midpoint with Davison(self, other)
        - ``"composite"``: self midpoint with Composite(self, other)
        """
        if mode == "davison":
            rel = self.davison_with(other)
            return self.davison_with(rel)
        elif mode == "composite":
            rel = self.composite_with(other)
            return self.composite_with(rel)
        else:
            raise ValueError("mode must be 'davison' or 'composite'")

    def marks_secondary(self, other: "Chart", years: float,
                        latitude_deg: float | None = None,
                        longitude_deg: float | None = None) -> "Chart":
        """Derived method: Marks secondary progression."""
        return self.marks_with(other).secondary_progression(
            age_years=years, latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    def marks_tertiary(self, other: "Chart", years: float,
                       latitude_deg: float | None = None,
                       longitude_deg: float | None = None) -> "Chart":
        """Derived method: Marks tertiary progression."""
        return self.marks_with(other).tertiary_i(
            age_years=years, latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    @staticmethod
    def _jd_to_cal(jd: float) -> tuple[int, int, int, int, int, float]:
        from ._time import jd_to_calendar
        return jd_to_calendar(jd)


def calculate_chart(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: float = 0.0,
    *,
    tz: float = 0.0,
    latitude_deg: float = 0.0,
    longitude_deg: float = 0.0,
    house_system: HouseSystem = HouseSystem.PLACIDUS,
    taiyin_position_fn: Callable[[float, int], tuple[float, float, float]]
        | None = None,
    taiyin_velocity_fn: Callable[[float, int], tuple[float, float, float]]
        | None = None,
) -> Chart:
    """Calculate a western astrology chart.

    Returns a Chart (dict subclass) with planets, houses, aspects.
    """
    # --- time ---
    # Convert local time → UTC: compute JD in local, then shift by tz
    jd_local = calendar_to_jd(year, month, day, hour, minute, second)
    jd_utc = jd_local - tz / 24.0
    jd_tt = jd_ut1_to_tt(jd_utc)  # approximation: UTC≈UT1

    lat_rad = math.radians(latitude_deg)
    lon_rad = math.radians(longitude_deg)

    # --- ephemeris ---
    if taiyin_position_fn is None:
        from taiyin_semi_analytic import position as _pos
        taiyin_position_fn = _pos                          # type: ignore[assignment]
    if taiyin_velocity_fn is None:
        from taiyin_semi_analytic import velocity_icrf as _vel
        taiyin_velocity_fn = _vel                          # type: ignore[assignment]

    # Earth position + velocity for geocentric conversion
    earth_pos_km = _to_xyz(taiyin_position_fn(jd_tt, 399))
    earth_vel_km_per_day = _to_xyz(taiyin_velocity_fn(jd_tt, 399))
    earth_pos_au = _to_xyz(tuple(_km_to_au(v) for v in earth_pos_km))
    earth_vel_au_per_day = _to_xyz(tuple(_km_to_au(v) for v in earth_vel_km_per_day))

    # --- precession / nutation ---
    nut = iau2000b_nutation_angles(jd_tt)
    eqeq = equation_of_equinoxes_rad(jd_tt)
    jd_ut1 = jd_tt_to_ut1(jd_tt)
    gast = gast_rad(jd_ut1, jd_tt, eqeq)

    # --- houses ---
    houses = calc_houses(gast, lon_rad, lat_rad,
                         nut["true_obliquity_rad"], house_system)

    # --- planets ---
    planets = {}
    for body_id, key, name in _PLANETS:
        # Heliocentric ICRF position (km)
        helio_pos_km = _to_xyz(taiyin_position_fn(jd_tt, body_id))
        helio_pos_au = _to_xyz(tuple(_km_to_au(v) for v in helio_pos_km))

        # Geocentric
        geo_au = (
            helio_pos_au[0] - earth_pos_au[0],
            helio_pos_au[1] - earth_pos_au[1],
            helio_pos_au[2] - earth_pos_au[2],
        )

        # Light-time + aberration
        geo_au = apply_light_corrections(
            jd_tt,
            lambda jd: _to_xyz(tuple(_km_to_au(v)
                                     for v in taiyin_position_fn(jd, body_id))),
            earth_pos_au,
            earth_vel_au_per_day,
            light_time=True,
            aberration=True,
        )

        # Solar deflection
        geo_au = apply_solar_deflection(
            earth_pos_au,
            _to_xyz((earth_pos_au[0] + geo_au[0],
                     earth_pos_au[1] + geo_au[1],
                     earth_pos_au[2] + geo_au[2])),
        )

        # ICRF equatorial → J2000 ecliptic → true ecliptic of date
        from ._precession import rotate_equator_to_ecliptic, _J2000_OBLIQUITY_RAD
        geo_ecl = rotate_equator_to_ecliptic(geo_au, _J2000_OBLIQUITY_RAD)
        ecl_date = j2000_ecliptic_to_date(geo_ecl, jd_tt)

        # Spherical
        x, y, z = ecl_date
        r = math.sqrt(x * x + y * y + z * z)
        lon = math.atan2(y, x) % (2.0 * math.pi)
        lat = math.asin(z / r) if r > 0.0 else 0.0

        sign_info, deg, min_ = sign_degree_minute(lon)

        if key == "moon":
            from ._moon_points import calc_true_node_and_lilith, calc_mean_node_ecliptic_of_date, calc_mean_apogee_ecliptic_of_date
            
            # Compute geometric (unaberrated) Moon velocity in True Ecliptic of Date with dt = 1e-4
            dt = 1e-4
            def _moon_geo_ecl_raw(t_eval: float) -> tuple[float, float, float]:
                h_pos_km = _to_xyz(taiyin_position_fn(t_eval, body_id))
                e_pos_km = _to_xyz(taiyin_position_fn(t_eval, 399))
                g_au = (_km_to_au(h_pos_km[0] - e_pos_km[0]),
                        _km_to_au(h_pos_km[1] - e_pos_km[1]),
                        _km_to_au(h_pos_km[2] - e_pos_km[2]))
                g_ecl = rotate_equator_to_ecliptic(g_au, _J2000_OBLIQUITY_RAD)
                return j2000_ecliptic_to_date(g_ecl, t_eval)

            pos_geo = _moon_geo_ecl_raw(jd_tt)
            pos_plus = _moon_geo_ecl_raw(jd_tt + dt)
            pos_minus = _moon_geo_ecl_raw(jd_tt - dt)
            
            moon_vel = ((pos_plus[0] - pos_minus[0]) / (2.0 * dt),
                        (pos_plus[1] - pos_minus[1]) / (2.0 * dt),
                        (pos_plus[2] - pos_minus[2]) / (2.0 * dt))
                        
            true_node_rad, true_lilith_rad = calc_true_node_and_lilith(pos_geo, moon_vel)
            mean_node_rad = calc_mean_node_ecliptic_of_date(jd_tt)
            mean_lilith_rad = calc_mean_apogee_ecliptic_of_date(jd_tt)
            
            def _insert_point(p_key: str, p_name: str, p_rad: float):
                p_sinfo, p_deg, p_min = sign_degree_minute(p_rad)
                planets[p_key] = {
                    "name": p_name,
                    "longitude_rad": p_rad,
                    "latitude_rad": 0.0,
                    "distance_au": 1.0,
                    "sign": p_sinfo.name,
                    "sign_abbrev": p_sinfo.abbrev,
                    "degree": p_deg,
                    "minute": p_min,
                    "retrograde": False,
                }
            
            _insert_point("true_node", "True Node", true_node_rad)
            _insert_point("mean_node", "Mean Node", mean_node_rad)
            _insert_point("true_lilith", "True Lilith", true_lilith_rad)
            _insert_point("mean_lilith", "Mean Lilith", mean_lilith_rad)

        planets[key] = {
            "name": name,
            "longitude_rad": lon,
            "latitude_rad": lat,
            "distance_au": r,
            "sign": sign_info.name,
            "sign_abbrev": sign_info.abbrev,
            "degree": deg,
            "minute": min_,
        }

    # --- longitude rates (for applying/separating) ---
    from ._precession import rotate_equator_to_ecliptic, _J2000_OBLIQUITY_RAD
    dt = 0.001  # ~1.4 minutes
    body_lons = {k: p["longitude_rad"] for k, p in planets.items()}
    body_rates: dict[str, float] = {}
    for body_id, key, name in _PLANETS:
        helio_km2 = _to_xyz(taiyin_position_fn(jd_tt + dt, body_id))
        geo_au2 = _to_xyz(tuple(_km_to_au(v) for v in helio_km2))
        geo_au2 = (
            geo_au2[0] - earth_pos_au[0],
            geo_au2[1] - earth_pos_au[1],
            geo_au2[2] - earth_pos_au[2],
        )
        geo_ecl2 = rotate_equator_to_ecliptic(geo_au2, _J2000_OBLIQUITY_RAD)
        ecl_date2 = j2000_ecliptic_to_date(geo_ecl2, jd_tt + dt)
        x2, y2, z2 = ecl_date2
        lon2 = math.atan2(y2, x2) % (2.0 * math.pi)
        body_rates[key] = (lon2 - body_lons[key]) / dt

    # tag retrograde
    for key, p in planets.items():
        p["retrograde"] = body_rates.get(key, 0.0) < 0.0

    # classical dignities, receptions, and antiscia
    from ._classical import get_essential_dignities, get_accidental_dignities, get_rulers, TRADITIONAL_PLANETS
    
    sun_lon = body_lons.get("sun", 0.0)
    asc_lon = houses["ascendant_rad"]
    is_day_chart = ((sun_lon - asc_lon) % (2.0 * math.pi)) > math.pi
    
    for key, p in planets.items():
        lon = p["longitude_rad"]
        p["antiscia_rad"] = (math.pi - lon) % (2.0 * math.pi)
        p["contra_antiscia_rad"] = (2.0 * math.pi - lon) % (2.0 * math.pi)
        
        if key in TRADITIONAL_PLANETS:
            deg_in_sign = p["degree"] + p["minute"] / 60.0
            essential = get_essential_dignities(key, p["sign"], deg_in_sign, is_day_chart)
            speed_deg = math.degrees(body_rates.get(key, 0.0))
            accidental = get_accidental_dignities(key, lon, sun_lon, speed_deg, is_day_chart)
            
            # Receptions (who receives this planet?)
            rulers = get_rulers(p["sign"], deg_in_sign, is_day_chart)
            received_by = {}
            for dignity, ruler in rulers.items():
                if ruler and ruler != key: # Exclude self-reception
                    base_dignity = dignity.split("_")[0]
                    if ruler not in received_by:
                        received_by[ruler] = []
                    if base_dignity not in received_by[ruler]:
                        received_by[ruler].append(base_dignity)
            
            p["classical"] = {
                "essential_dignities": essential["details"],
                "accidental_conditions": accidental,
                "received_by": received_by,
                "essential_score": essential["score"],
                "systems": essential["systems"]
            }

    # Extract Mutual Receptions
    mutual_receptions = []
    trad_keys = [k for k in planets if k in TRADITIONAL_PLANETS]
    for i in range(len(trad_keys)):
        for j in range(i + 1, len(trad_keys)):
            k1 = trad_keys[i]
            k2 = trad_keys[j]
            k1_rec_k2 = planets[k2]["classical"]["received_by"].get(k1)
            k2_rec_k1 = planets[k1]["classical"]["received_by"].get(k2)
            if k1_rec_k2 and k2_rec_k1:
                mutual_receptions.append({
                    "planets": [k1, k2],
                    k1: k2_rec_k1,  # k1 is received by k2 by these dignities
                    k2: k1_rec_k2   # k2 is received by k1 by these dignities
                })

    # --- aspects ---
    aspects = find_all_aspects(body_lons, body_rates=body_rates)

    # --- assemble ---
    y, mo, d, h, mi, s = jd_to_calendar(jd_utc)
    # Extract same degree relationships (同度)
    degree_groups = {}
    
    # 1. Planets and nodes
    for k, p in planets.items():
        deg = p["degree"]
        if deg not in degree_groups:
            degree_groups[deg] = []
        degree_groups[deg].append(k)
        
    # 2. Angles (Ascendant, MC, Descendant, IC)
    _, asc_deg, _ = sign_degree_minute(houses["ascendant_rad"])
    if asc_deg not in degree_groups:
        degree_groups[asc_deg] = []
    degree_groups[asc_deg].append("ascendant")
    
    _, mc_deg, _ = sign_degree_minute(houses["midheaven_rad"])
    if mc_deg not in degree_groups:
        degree_groups[mc_deg] = []
    degree_groups[mc_deg].append("midheaven")
    
    # Keep only groups with 2 or more points
    same_degrees = []
    for deg, pts in degree_groups.items():
        if len(pts) >= 2:
            same_degrees.append({
                "degree": deg,
                "points": pts
            })

    # --- lots / arabic parts ---
    from ._lots import calculate_lots
    lots = calculate_lots(
        asc_deg=math.degrees(houses["ascendant_rad"]),
        sun_deg=math.degrees(body_lons.get("sun", 0.0)),
        moon_deg=math.degrees(body_lons.get("moon", 0.0)),
        venus_deg=math.degrees(body_lons.get("venus", 0.0)),
        mars_deg=math.degrees(body_lons.get("mars", 0.0)),
        jupiter_deg=math.degrees(body_lons.get("jupiter", 0.0)),
        saturn_deg=math.degrees(body_lons.get("saturn", 0.0)),
        mercury_deg=math.degrees(body_lons.get("mercury", 0.0)),
        is_day_chart=is_day_chart
    )

    # Return final chart object
    data = {
        "jd_utc": jd_utc,
        "jd_tt": jd_tt,
        "delta_t_s": delta_t_seconds_from_jd_ut1(jd_utc),
        "date_utc": f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{int(s):02d}Z",
        "observer": {
            "lat_deg": latitude_deg,
            "lon_deg": longitude_deg,
        },
        "date": {
            "jd_ut": jd_utc,
            "jd_tt": jd_tt,
        },
        "location": {
            "lat_deg": latitude_deg,
            "lon_deg": longitude_deg,
        },
        "planets": planets,
        "lots": lots,
        "mutual_receptions": mutual_receptions,
        "same_degrees": same_degrees,
        "houses": {
            "system": houses["system"].value,
            "armc_rad": houses["armc_rad"],
            "ascendant": _format_angle(houses["ascendant_rad"]),
            "midheaven": _format_angle(houses["midheaven_rad"]),
            "vertex": _format_angle(houses["vertex_rad"]),
            "east_point": _format_angle(houses["east_point_rad"]),
            "cusps": [_format_angle(c) for c in houses["cusps_rad"]],
        },
        "aspects": aspects,
    }
    return Chart(data, body_rates)


def _format_angle(rad: float) -> dict:
    sign, deg, min_ = sign_degree_minute(rad)
    return {
        "sign": sign.name,
        "sign_abbrev": sign.abbrev,
        "degree": deg,
        "minute": min_,
        "longitude_rad": rad,
    }
