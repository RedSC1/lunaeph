"""Time conversions: JD ⇄ calendar, deltaT, UT1 ⇄ TT, GMST/GAST.

Ported from taiyin-ephemeris C++ sources:
  src/time.cpp          — deltaT model, calendar ↔ JD
  src/interpolation.cpp — Catmull-Rom and cubic polynomial
  src/internal/delta_t_data.h / .cpp — S15 spline + annual table

Model choices (hardcoded, not configurable):
  deltaT:    Stephenson & Morrison (2004/2015) S15 spline (–720 to 1953)
             + annual observed table (1953–2050) with Catmull-Rom
             + parabolic extrapolation beyond
  GMST/GAST: IAU 2006 GMST + IAU2000B equation of equinoxes
             (the nutation side is in _precession.py; GAST is wired
              externally once precession is available)
"""

from __future__ import annotations

import math
from typing import Sequence

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JD_J2000 = 2451545.0
DAYS_PER_JULIAN_CENTURY = 36525.0
DAYS_PER_JULIAN_MILLENNIUM = 365250.0
ARCSEC_PER_RADIAN = 206264.80624709636
ARCSEC_TO_RAD = 1.0 / ARCSEC_PER_RADIAN
TWO_PI = 2.0 * math.pi

# ---------------------------------------------------------------------------
# S15 spline: Stephenson & Morrison (2004, 2015)
# ---------------------------------------------------------------------------

_S15_SPLINE = [
    # (x0, x1, a3,      a2,        a1,          a0)
    (-720.0, -100.0, 409.160000,   776.247000,  -9999.586000,  20371.848000),
    (-100.0,  400.0, -503.433000,  1303.151000, -5822.270000,  11557.668000),
    ( 400.0, 1000.0,  1085.087000, -298.291000, -5671.519000,  6535.116000),
    (1000.0, 1150.0,  -25.346000,  184.811000,  -753.210000,   1650.393000),
    (1150.0, 1300.0,  -24.641000,  108.771000,  -459.628000,   1056.647000),
    (1300.0, 1500.0,  -29.414000,  61.953000,   -421.345000,   681.149000),
    (1500.0, 1600.0,   16.197000,  -6.572000,   -192.841000,   292.343000),
    (1600.0, 1650.0,   3.018000,   10.505000,   -78.697000,    109.127000),
    (1650.0, 1720.0,   -2.127000,  38.333000,   -68.089000,    43.952000),
    (1720.0, 1800.0,  -37.939000,  41.731000,   2.507000,      12.068000),
    (1800.0, 1810.0,   1.918000,   -1.126000,   -3.481000,     18.367000),
    (1810.0, 1820.0,  -3.812000,   4.629000,    0.021000,      15.678000),
    (1820.0, 1830.0,   3.250000,   -6.806000,   -2.157000,     16.516000),
    (1830.0, 1840.0,  -0.096000,   2.944000,    -6.018000,     10.804000),
    (1840.0, 1850.0,  -0.539000,   2.658000,    -0.416000,     7.634000),
    (1850.0, 1855.0,  -0.883000,   0.261000,    1.642000,      9.338000),
    (1855.0, 1860.0,   1.558000,   -2.389000,   -0.486000,     10.357000),
    (1860.0, 1865.0,  -2.477000,   2.284000,    -0.591000,     9.040000),
    (1865.0, 1870.0,   2.720000,   -5.148000,   -3.456000,     8.255000),
    (1870.0, 1875.0,  -0.914000,   3.011000,    -5.593000,     2.371000),
    (1875.0, 1880.0,  -0.039000,   0.269000,    -2.314000,     -1.126000),
    (1880.0, 1885.0,   0.563000,   0.152000,    -1.893000,     -3.210000),
    (1885.0, 1890.0,  -1.438000,   1.842000,    0.101000,      -4.388000),
    (1890.0, 1895.0,   1.871000,   -2.474000,   -0.531000,     -3.884000),
    (1895.0, 1900.0,  -0.232000,   3.138000,    0.134000,      -5.017000),
    (1900.0, 1905.0,  -1.257000,   2.443000,    5.715000,      -1.977000),
    (1905.0, 1910.0,   0.720000,   -1.329000,   6.828000,      4.923000),
    (1910.0, 1915.0,  -0.825000,   0.831000,    6.330000,      11.142000),
    (1915.0, 1920.0,   0.262000,   -1.643000,   5.518000,      17.479000),
    (1920.0, 1925.0,   0.008000,   -0.856000,   3.020000,      21.617000),
    (1925.0, 1930.0,   0.127000,   -0.831000,   1.333000,      23.789000),
    (1930.0, 1935.0,   0.142000,   -0.449000,   0.052000,      24.418000),
    (1935.0, 1940.0,   0.702000,   -0.022000,   -0.419000,     24.164000),
    (1940.0, 1945.0,  -1.106000,   2.086000,    1.645000,      24.426000),
    (1945.0, 1950.0,   0.614000,   -1.232000,   2.499000,      27.050000),
    (1950.0, 1953.0,  -0.277000,   0.220000,    1.127000,      28.932000),
]

# Annual observed deltaT table, 1953–2050
_ANNUAL_DELTA_T = [
    (1953, 30.00), (1954, 30.20), (1955, 30.41), (1956, 30.76),
    (1957, 31.34), (1958, 32.03), (1959, 32.65), (1960, 33.07),
    (1961, 33.36), (1962, 33.62), (1963, 33.96), (1964, 34.44),
    (1965, 35.09), (1966, 35.95), (1967, 36.93), (1968, 37.95),
    (1969, 38.95), (1970, 39.93), (1971, 40.95), (1972, 42.14),
    (1973, 43.38), (1974, 44.48), (1975, 45.48), (1976, 46.46),
    (1977, 47.52), (1978, 48.53), (1979, 49.59), (1980, 50.54),
    (1981, 51.38), (1982, 52.17), (1983, 52.96), (1984, 53.79),
    (1985, 54.34), (1986, 54.87), (1987, 55.32), (1988, 55.82),
    (1989, 56.30), (1990, 56.86), (1991, 57.57), (1992, 58.31),
    (1993, 59.12), (1994, 59.98), (1995, 60.79), (1996, 61.63),
    (1997, 62.30), (1998, 62.97), (1999, 63.47), (2000, 63.83),
    (2001, 64.09), (2002, 64.30), (2003, 64.47), (2004, 64.57),
    (2005, 64.69), (2006, 64.85), (2007, 65.15), (2008, 65.46),
    (2009, 65.78), (2010, 66.07), (2011, 66.32), (2012, 66.60),
    (2013, 66.91), (2014, 67.28), (2015, 67.64), (2016, 68.10),
    (2017, 68.59), (2018, 68.97), (2019, 69.22), (2020, 69.36),
    (2021, 69.36), (2022, 69.29), (2023, 69.20), (2024, 69.18),
    (2025, 69.14), (2026, 69.11), (2027, 69.10), (2028, 69.08),
    (2029, 69.07), (2030, 69.08), (2031, 69.09), (2032, 69.12),
    (2033, 69.16), (2034, 69.20), (2035, 69.26), (2036, 69.33),
    (2037, 69.41), (2038, 69.51), (2039, 69.61), (2040, 69.72),
    (2041, 69.85), (2042, 69.98), (2043, 70.13), (2044, 70.28),
    (2045, 70.45), (2046, 70.63), (2047, 70.81), (2048, 71.01),
    (2049, 71.22), (2050, 71.44),
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cubic_poly(a0: float, a1: float, a2: float, a3: float, x: float) -> float:
    """a0 + a1*x + a2*x² + a3*x³"""
    return ((a3 * x + a2) * x + a1) * x + a0


def _catmull_rom(
    t0: float, t1: float, t2: float, t3: float,
    p0: float, p1: float, p2: float, p3: float,
    t: float,
) -> float:
    """Catmull-Rom spline at *t* between knots (t1,p1) and (t2,p2)."""
    dt1 = t2 - t1
    x = (t - t1) / dt1
    m1 = ((p2 - p0) / (t2 - t0)) * dt1
    m2 = ((p3 - p1) / (t3 - t1)) * dt1
    x2 = x * x
    x3 = x2 * x
    return (
        (2.0 * x3 - 3.0 * x2 + 1.0) * p1
        + (x3 - 2.0 * x2 + x) * m1
        + (-2.0 * x3 + 3.0 * x2) * p2
        + (x3 - x2) * m2
    )


def _normalize_radians(angle: float) -> float:
    """Normalize to [0, 2π)."""
    return angle % TWO_PI


def _decimal_year_from_jd(jd: float) -> float:
    """Convert Julian date to decimal year."""
    year, month, day = _jd_to_calendar_date(jd)
    days_in_year = 366.0 if _is_leap(year) else 365.0
    # approximate: fraction from start of year
    jd_start = _calendar_date_to_jd(year, 1, 1.0)
    return year + (jd - jd_start) / days_in_year


def _is_leap(year: int) -> bool:
    """Gregorian calendar leap year."""
    if year % 4 != 0:
        return False
    if year % 100 != 0:
        return True
    return year % 400 == 0


def _jd_to_calendar_date(jd: float) -> tuple[int, int, float]:
    """Julian date to Gregorian (year, month, day.fraction).

    Julian → Gregorian transition at JD 2299161 (1582-10-15).
    """
    return _jd_to_gregorian(jd)


def _calendar_date_to_jd(year: int, month: int, day: float) -> float:
    """Gregorian (year, month, day) to Julian date."""
    return _gregorian_to_jd(year, month, day)


def _jd_to_gregorian(jd: float) -> tuple[int, int, float]:
    """JD to Gregorian calendar (Meeus / Fliegel & Van Flandern)."""
    z = int(jd + 0.5)
    f = jd + 0.5 - z

    if z < 2299161:
        a = z
    else:
        alpha = (z - 1867216) // 36524
        a = z + 1 + alpha - alpha // 4

    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)

    day_frac = b - d - int(30.6001 * e) + f
    if e < 14:
        month = e - 1
    else:
        month = e - 13
    if month > 2:
        year = c - 4716
    else:
        year = c - 4715

    return year, month, day_frac


def _gregorian_to_jd(year: int, month: int, day: float) -> float:
    """Gregorian to JD (Meeus formula)."""
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    return (int(365.25 * (year + 4716))
            + int(30.6001 * (month + 1))
            + day
            + b
            - 1524.5)


# ---------------------------------------------------------------------------
# Calendar public API
# ---------------------------------------------------------------------------

def jd_to_calendar(
    jd: float,
) -> tuple[int, int, int, int, int, float]:
    """Return (year, month, day, hour, minute, second) in Gregorian/Julian."""
    y, m, d = _jd_to_calendar_date(jd)
    day_int = int(d)
    frac = d - day_int
    # Round fractional day to nearest second (avoid 59.999…→60.0 artefacts)
    total_seconds = round(frac * 86400.0)
    # Handle edge: 86400 → next day 00:00:00
    if total_seconds >= 86400:
        total_seconds = 0
        day_int += 1
    hour = total_seconds // 3600
    minute = (total_seconds - hour * 3600) // 60
    second = total_seconds - hour * 3600 - minute * 60
    return y, m, day_int, hour, minute, float(second)


def calendar_to_jd(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: float = 0.0,
) -> float:
    """Convert UTC calendar datetime to Julian date."""
    day_frac = day + (hour + (minute + second / 60.0) / 60.0) / 24.0
    return _calendar_date_to_jd(year, month, day_frac)


def decimal_year_from_jd(jd: float) -> float:
    """Decimal year for a given Julian date."""
    return _decimal_year_from_jd(jd)


# ---------------------------------------------------------------------------
# deltaT
# ---------------------------------------------------------------------------

def _eval_s15_delta_t(year_decimal: float) -> float:
    """S15 historical spline, –720 to 1953."""
    for x0, x1, a3, a2, a1, a0 in _S15_SPLINE:
        if x0 <= year_decimal < x1:
            t = (year_decimal - x0) / (x1 - x0)
            return _cubic_poly(a0, a1, a2, a3, t)
    # past last segment: clamp at end
    last = _S15_SPLINE[-1]
    return _cubic_poly(last[5], last[4], last[3], last[2], 1.0)


def _extrapolate_delta_t(year_decimal: float) -> float:
    """Parabolic extrapolation for ancient (−720) or far‑future (> table + 100)."""
    u = (year_decimal - 1820.0) / 100.0
    return -20.0 + 32.0 * u * u


def delta_t_seconds_from_decimal_year(year_decimal: float) -> float:
    """Return ΔT (TT – UT) in seconds for a decimal year.

    Three regimes (ported from taiyin time.cpp):
      −720 … 1953   S15 cubic spline segments
      1953 … 2050   annual observed table (Catmull‑Rom interpolation)
      otherwise      parabolic extrapolation with a linear blend
                     in the first century past the table.
    """
    if not math.isfinite(year_decimal):
        return year_decimal

    # S15 range
    if year_decimal >= -720.0 and year_decimal < 1953.0:
        return _eval_s15_delta_t(year_decimal)

    data = _ANNUAL_DELTA_T
    n = len(data)
    first_year = data[0][0]
    last_year = data[-1][0]

    # Annual table range
    if first_year <= year_decimal < last_year:
        # find segment index i such that year < data[i+1].year
        i = 0
        for idx in range(n - 1):
            if year_decimal < data[idx + 1][0]:
                i = idx
                break

        i0 = max(i - 1, 0)
        i1 = i
        i2 = min(i + 1, n - 1)
        i3 = min(i + 2, n - 1)
        return _catmull_rom(
            data[i0][0], data[i1][0], data[i2][0], data[i3][0],
            data[i0][1], data[i1][1], data[i2][1], data[i3][1],
            year_decimal,
        )

    # Extrapolation regions
    if year_decimal < -720.0:
        return _extrapolate_delta_t(year_decimal)

    # Blend between last table year and pure extrapolation
    t0 = last_year
    v0 = data[-1][1]
    if year_decimal > t0 + 100.0:
        return _extrapolate_delta_t(year_decimal)
    v = _extrapolate_delta_t(year_decimal)
    # linear blend of the delta between table tail and pure extrapolation
    dv = _linear_interp(t0, t0 + 100.0,
                        _extrapolate_delta_t(t0) - v0,
                        0.0,
                        year_decimal)
    return v - dv


def _linear_interp(x0: float, x1: float, y0: float, y1: float, x: float) -> float:
    if x1 == x0:
        return y0
    u = (x - x0) / (x1 - x0)
    return y0 + (y1 - y0) * u


# ---------------------------------------------------------------------------
# deltaT: JD entry points
# ---------------------------------------------------------------------------

def delta_t_seconds_from_jd_ut1(jd_ut1: float) -> float:
    """ΔT (seconds) from UT1 Julian date."""
    return delta_t_seconds_from_decimal_year(
        _decimal_year_from_jd(jd_ut1))


def jd_ut1_to_tt(jd_ut1: float) -> float:
    """Convert UT1 JD to TT JD."""
    return jd_ut1 + delta_t_seconds_from_jd_ut1(jd_ut1) / 86400.0


def jd_tt_to_ut1(jd_tt: float) -> float:
    """Convert TT JD to UT1 JD (iterative, one pass)."""
    # Start with UT1 ≈ TT (ΔT ≈ 0), then one correction step
    jd_ut1_guess = jd_tt - 60.0 / 86400.0  # typical ΔT ~60s
    dt = delta_t_seconds_from_jd_ut1(jd_ut1_guess)
    return jd_tt - dt / 86400.0


# ---------------------------------------------------------------------------
# GMST / GAST
# ---------------------------------------------------------------------------

def _earth_rotation_angle_rad(jd_ut1: float) -> float:
    """ERA in radians (IAU 2006)."""
    return _normalize_radians(
        TWO_PI * (0.7790572732640 + 1.00273781191135448 * (jd_ut1 - JD_J2000))
    )


def _gmst_minus_era_rad(jd_tt: float) -> float:
    """GMST – ERA polynomial, returns radians."""
    t = (jd_tt - JD_J2000) / DAYS_PER_JULIAN_CENTURY
    t2 = t * t
    t3 = t2 * t
    t4 = t3 * t
    t5 = t4 * t
    arcsec = (0.014506
              + 4612.156534 * t
              + 1.3915817 * t2
              - 0.00000044 * t3
              - 0.000029956 * t4
              - 0.0000000368 * t5)
    return arcsec * ARCSEC_TO_RAD


def gmst_rad(jd_ut1: float, jd_tt: float) -> float:
    """GMST in radians (ERA + GMST–ERA offset)."""
    return _normalize_radians(
        _earth_rotation_angle_rad(jd_ut1) + _gmst_minus_era_rad(jd_tt))


def gast_rad(jd_ut1: float, jd_tt: float,
             equation_of_equinoxes_rad: float = 0.0) -> float:
    """GAST in radians = GMST + equation of equinoxes.

    Caller passes the nutation‑derived equation of equinoxes.
    (computed in _precession.py).  Defaults to 0 so GMST = GAST until wired.
    """
    return _normalize_radians(
        gmst_rad(jd_ut1, jd_tt) + equation_of_equinoxes_rad)


def _gmst_minus_era_rate_rad_per_day(jd_tt: float) -> float:
    """d/dt (GMST – ERA), radians/day."""
    t = (jd_tt - JD_J2000) / DAYS_PER_JULIAN_CENTURY
    t2 = t * t
    t3 = t2 * t
    t4 = t3 * t
    arcsec_per_century = (4612.156534
                          + 2.0 * 1.3915817 * t
                          - 3.0 * 0.00000044 * t2
                          - 4.0 * 0.000029956 * t3
                          - 5.0 * 0.0000000368 * t4)
    return arcsec_per_century * ARCSEC_TO_RAD / DAYS_PER_JULIAN_CENTURY


# ---------------------------------------------------------------------------
# Gregorian leap‑year helper (re‑exported for convenience)
# ---------------------------------------------------------------------------

is_leap_year = _is_leap
