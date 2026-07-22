"""Vondrák 2011 precession + IAU2000B nutation.

Ported from taiyin-ephemeris C++ sources:
  src/coordinates.cpp            — vondrak2011_precession_matrix, iau2000b_nutation,
                                  mean_obliquity_iau2006, frame bias
  src/internal/coordinate_model_data.h / .cpp — periodic terms + polynomials
  src/earth_rotation.cpp         — equation of equinoxes

Model choices (hardcoded):
  Precession: Vondrák 2011 (Newhall/Zijiang Yan 2011 parameterisation)
  Nutation:   IAU 2000B (77 lunisolar + planetary terms)
  Obliquity:  IAU 2006 polynomial (Capitaine et al. 2003 / Hilton et al. 2006)
  Frame bias: IAU 2006 ICRF→J2000 (dα₀, dε₀, dγ₀)
"""

from __future__ import annotations

import math
from typing import Sequence

from ._time import ARCSEC_TO_RAD, DAYS_PER_JULIAN_CENTURY, JD_J2000, TWO_PI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_J2000_OBLIQUITY_ARCSEC = 84381.406
_J2000_OBLIQUITY_RAD = _J2000_OBLIQUITY_ARCSEC * ARCSEC_TO_RAD

# Frame bias: ICRF → J2000 mean equator/equinox (IAU 2006)
_FRAME_BIAS_DR_RAD = -0.0146 * ARCSEC_TO_RAD
_FRAME_BIAS_DX_RAD = -0.016617 * ARCSEC_TO_RAD
_FRAME_BIAS_DE_RAD = -0.0068192 * ARCSEC_TO_RAD

# ---------------------------------------------------------------------------
# Vondrák 2011 — ecliptic & equator data
# ---------------------------------------------------------------------------

# polynomial coefficients (ascending degree: constant, t, t², t³)
_VONDRAK_ECLIPTIC_PA = (5851.607687, -0.1189, -0.00028913, 1.01e-07)
_VONDRAK_ECLIPTIC_QA = (-1600.8863, 1.1689818, -2e-07, -4.37e-07)
_VONDRAK_EQUATOR_XA = (5453.282155, 0.4252841, -0.00037173, -1.52e-07)
_VONDRAK_EQUATOR_YA = (-73750.93035, -0.7675452, -0.00018725, 2.31e-07)

# Vondrák periodic terms: (period_centuries, cos_0, cos_1, sin_0, sin_1)
_VONDRAK_ECLIPTIC_PERIODIC = (
    (708.15, -5486.751211, -684.66156,     667.66673,    -5523.863691),
    (2309,   -17.127623,   2446.28388,    -2354.886252,  -549.74745),
    (1620,   -617.517403,  399.671049,    -428.152441,   -310.998056),
    (492.2,   413.44294,   -356.652376,    376.202861,    421.535876),
    (1183,    78.614193,   -186.387003,    184.778874,    -36.776172),
    (622,    -180.732815,  -316.80007,     335.321713,   -145.278396),
    (882,    -87.676083,    198.296701,   -185.138669,    -34.74445),
    (547,     46.140315,    101.135679,   -120.97283,     22.885731),
)

_VONDRAK_EQUATOR_PERIODIC = (
    (256.75,  -819.940624,  75004.344875,  81491.287984,  1558.515853),
    (708.15, -8444.676815,    624.033993,    787.163481,  7774.939698),
    (274.2,   2600.009459,   1251.136893,   1251.296102, -2219.534038),
    (241.45,  2755.17563,   -1102.212834,  -1257.950837, -2523.969396),
    (2309,    -167.659835,  -2660.66498,   -2966.79973,    247.850422),
    (492.2,    871.855056,    699.291817,    639.744522,  -846.485643),
    (396.1,    44.769698,    153.16722,     131.600209,  -1393.124055),
    (288.9,  -512.313065,   -950.865637,   -445.040117,    368.526116),
    (231.1,  -819.415595,    499.754645,    584.522874,    749.045012),
    (1610,   -538.071099,   -145.18821,     -89.756563,    444.704518),
    (620,    -189.793622,    558.116553,    524.42963,     235.934465),
    (157.87, -402.922932,    -23.923029,    -13.549067,    374.049623),
    (220.3,   179.516345,   -165.405086,   -210.157124,   -171.33018),
    (1200,     -9.814756,      9.344131,    -44.919798,    -22.899655),
)

# ---------------------------------------------------------------------------
# IAU 2000B nutation table (77 terms)
# ---------------------------------------------------------------------------

# (l, lp, f, D, Ω,  ps, pst, pc,  ec, ect, es)
_IAU2000B_TERMS = (
    ( 0,  0,  0,  0,  1, -172064161, -174666,  33386,  92052331,   9086,  15377),
    ( 0,  0,  2, -2,  2, -13170906,   -1675, -13696,   5730336,  -3015,  -4587),
    ( 0,  0,  2,  0,  2,  -2276413,    -234,   2796,    978459,   -485,   1374),
    ( 0,  0,  0,  0,  2,   2074554,     207,   -698,   -897492,    470,   -291),
    ( 0,  1,  0,  0,  0,   1475877,   -3633,  11817,     73871,   -184,  -1924),
    ( 0,  1,  2, -2,  2,   -516821,    1226,   -524,    224386,   -677,   -174),
    ( 1,  0,  0,  0,  0,    711159,      73,   -872,     -6750,      0,    358),
    ( 0,  0,  2,  0,  1,   -387298,    -367,    380,    200728,     18,    318),
    ( 1,  0,  2,  0,  2,   -301461,     -36,    816,    129025,    -63,    367),
    ( 0, -1,  2, -2,  2,    215829,    -494,    111,    -95929,    299,    132),
    ( 0,  0,  2, -2,  1,    128227,     137,    181,    -68982,     -9,     39),
    (-1,  0,  2,  0,  2,    123457,      11,     19,    -53311,     32,     -4),
    (-1,  0,  0,  2,  0,    156994,      10,   -168,     -1235,      0,     82),
    ( 1,  0,  0,  0,  1,     63110,      63,     27,    -33228,      0,     -9),
    (-1,  0,  0,  0,  1,    -57976,     -63,   -189,     31429,      0,    -75),
    (-1,  0,  2,  2,  2,    -59641,     -11,    149,     25543,    -11,     66),
    ( 1,  0,  2,  0,  1,    -51613,     -42,    129,     26366,      0,     78),
    (-2,  0,  2,  0,  1,     45893,      50,     31,    -24236,    -10,     20),
    ( 0,  0,  0,  2,  0,     63384,      11,   -150,     -1220,      0,     29),
    ( 0,  0,  2,  2,  2,    -38571,      -1,    158,     16452,    -11,     68),
    ( 0, -2,  2, -2,  2,     32481,       0,      0,    -13870,      0,      0),
    (-2,  0,  0,  2,  0,    -47722,       0,    -18,       477,      0,    -25),
    ( 2,  0,  2,  0,  2,    -31046,      -1,    131,     13238,    -11,     59),
    ( 1,  0,  2, -2,  2,     28593,       0,     -1,    -12338,     10,     -3),
    (-1,  0,  2,  0,  1,     20441,      21,     10,    -10758,      0,     -3),
    ( 2,  0,  0,  0,  0,     29243,       0,    -74,      -609,      0,     13),
    ( 0,  0,  2,  0,  0,     25887,       0,    -66,      -550,      0,     11),
    ( 0,  1,  0,  0,  1,    -14053,     -25,     79,      8551,     -2,    -45),
    (-1,  0,  0,  2,  1,     15164,      10,     11,     -8001,      0,     -1),
    ( 0,  2,  2, -2,  2,    -15794,      72,    -16,      6850,    -42,     -5),
    ( 0,  0, -2,  2,  0,     21783,       0,     13,      -167,      0,     13),
    ( 1,  0,  0, -2,  1,    -12873,     -10,    -37,      6953,      0,    -14),
    ( 0, -1,  0,  0,  1,    -12654,      11,     63,      6415,      0,     26),
    (-1,  0,  2,  2,  1,    -10204,       0,     25,      5222,      0,     15),
    ( 0,  2,  0,  0,  0,     16707,     -85,    -10,       168,     -1,     10),
    ( 1,  0,  2,  2,  2,     -7691,       0,     44,      3268,      0,     19),
    (-2,  0,  2,  0,  0,    -11024,       0,    -14,       104,      0,      2),
    ( 0,  1,  2,  0,  2,      7566,     -21,    -11,     -3250,      0,     -5),
    ( 0,  0,  2,  2,  1,     -6637,     -11,     25,      3353,      0,     14),
    ( 0, -1,  2,  0,  2,     -7141,      21,      8,      3070,      0,      4),
    ( 0,  0,  0,  2,  1,     -6302,     -11,      2,      3272,      0,      4),
    ( 1,  0,  2, -2,  1,      5800,      10,      2,     -3045,      0,     -1),
    ( 2,  0,  2, -2,  2,      6443,       0,     -7,     -2768,      0,     -4),
    (-2,  0,  0,  2,  1,     -5774,     -11,    -15,      3041,      0,     -5),
    ( 2,  0,  2,  0,  1,     -5350,       0,     21,      2695,      0,     12),
    ( 0, -1,  2, -2,  1,     -4752,     -11,     -3,      2719,      0,     -3),
    ( 0,  0,  0, -2,  1,     -4940,     -11,    -21,      2720,      0,     -9),
    (-1, -1,  0,  2,  0,      7350,       0,     -8,       -51,      0,      4),
    ( 2,  0,  0, -2,  1,      4065,       0,      6,     -2206,      0,      1),
    ( 1,  0,  0,  2,  0,      6579,       0,    -24,      -199,      0,      2),
    ( 0,  1,  2, -2,  1,      3579,       0,      5,     -1900,      0,      1),
    ( 1, -1,  0,  0,  0,      4725,       0,     -6,       -41,      0,      3),
    (-2,  0,  2,  0,  2,     -3075,       0,     -2,      1313,      0,     -1),
    ( 3,  0,  2,  0,  2,     -2904,       0,     15,      1233,      0,      7),
    ( 0, -1,  0,  2,  0,      4348,       0,    -10,       -81,      0,      2),
    ( 1, -1,  2,  0,  2,     -2878,       0,      8,      1232,      0,      4),
    ( 0,  0,  0,  1,  0,     -4230,       0,      5,       -20,      0,     -2),
    (-1, -1,  2,  2,  2,     -2819,       0,      7,      1207,      0,      3),
    (-1,  0,  2,  0,  0,     -4056,       0,      5,        40,      0,     -2),
    ( 0, -1,  2,  2,  2,     -2647,       0,     11,      1129,      0,      5),
    (-2,  0,  0,  0,  1,     -2294,       0,    -10,      1266,      0,     -4),
    ( 1,  1,  2,  0,  2,      2481,       0,     -7,     -1062,      0,     -3),
    ( 2,  0,  0,  0,  1,      2179,       0,     -2,     -1129,      0,     -2),
    (-1,  1,  0,  1,  0,      3276,       0,      1,        -9,      0,      0),
    ( 1,  1,  0,  0,  0,     -3389,       0,      5,        35,      0,     -2),
    ( 1,  0,  2,  0,  0,      3339,       0,    -13,      -107,      0,      1),
    (-1,  0,  2, -2,  1,     -1987,       0,     -6,      1073,      0,     -2),
    ( 1,  0,  0,  0,  2,     -1981,       0,      0,       854,      0,      0),
    (-1,  0,  0,  1,  0,      4026,       0,   -353,      -553,      0,   -139),
    ( 0,  0,  2,  1,  2,      1660,       0,     -5,      -710,      0,     -2),
    (-1,  0,  2,  4,  2,     -1521,       0,      9,       647,      0,      4),
    (-1,  1,  0,  1,  1,      1314,       0,      0,      -700,      0,      0),
    ( 0, -2,  2, -2,  1,     -1283,       0,      0,       672,      0,      0),
    ( 1,  0,  2,  2,  1,     -1331,       0,      8,       663,      0,      4),
    (-2,  0,  2,  2,  2,      1383,       0,     -2,      -594,      0,     -2),
    (-1,  0,  0,  0,  2,      1405,       0,      4,      -610,      0,      2),
    ( 1,  1,  2, -2,  2,      1290,       0,      0,      -556,      0,      0),
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _poly4(coeff: Sequence[float], t: float) -> float:
    """c₀ + c₁·t + c₂·t² + c₃·t³"""
    return ((coeff[3] * t + coeff[2]) * t + coeff[1]) * t + coeff[0]


def _fmod_arcsec_to_rad(arcsec: float) -> float:
    """Fmod arcseconds to [0, 1296000) and convert to radians."""
    return (arcsec % 1296000.0) * ARCSEC_TO_RAD


def _3x3_multiply(a, b):
    """Multiply two 3×3 matrices (each a tuple of 3 tuples)."""
    return (
        (
            a[0][0] * b[0][0] + a[0][1] * b[1][0] + a[0][2] * b[2][0],
            a[0][0] * b[0][1] + a[0][1] * b[1][1] + a[0][2] * b[2][1],
            a[0][0] * b[0][2] + a[0][1] * b[1][2] + a[0][2] * b[2][2],
        ),
        (
            a[1][0] * b[0][0] + a[1][1] * b[1][0] + a[1][2] * b[2][0],
            a[1][0] * b[0][1] + a[1][1] * b[1][1] + a[1][2] * b[2][1],
            a[1][0] * b[0][2] + a[1][1] * b[1][2] + a[1][2] * b[2][2],
        ),
        (
            a[2][0] * b[0][0] + a[2][1] * b[1][0] + a[2][2] * b[2][0],
            a[2][0] * b[0][1] + a[2][1] * b[1][1] + a[2][2] * b[2][1],
            a[2][0] * b[0][2] + a[2][1] * b[1][2] + a[2][2] * b[2][2],
        ),
    )


def _3x3_apply(matrix, vector):
    """Apply 3×3 matrix to 3-vector."""
    return (
        matrix[0][0] * vector[0] + matrix[0][1] * vector[1] + matrix[0][2] * vector[2],
        matrix[1][0] * vector[0] + matrix[1][1] * vector[1] + matrix[1][2] * vector[2],
        matrix[2][0] * vector[0] + matrix[2][1] * vector[1] + matrix[2][2] * vector[2],
    )


def _rotation_x(angle: float):
    """Rotation matrix about X axis."""
    c = math.cos(angle)
    s = math.sin(angle)
    return (
        (1.0, 0.0, 0.0),
        (0.0,   c,   s),
        (0.0,  -s,   c),
    )


def _rotation_y(angle: float):
    """Rotation matrix about Y axis."""
    c = math.cos(angle)
    s = math.sin(angle)
    return (
        (  c, 0.0,  -s),
        (0.0, 1.0, 0.0),
        (  s, 0.0,   c),
    )


def _rotation_z(angle: float):
    """Rotation matrix about Z axis."""
    c = math.cos(angle)
    s = math.sin(angle)
    return (
        (  c,   s, 0.0),
        ( -s,   c, 0.0),
        (0.0, 0.0, 1.0),
    )


def _vondrak_periodic_sum(terms, t: float) -> tuple[float, float]:
    """Sum periodic Vondrák terms → (p, q) for ecliptic or (x, y) for equator."""
    result_0 = 0.0
    result_1 = 0.0
    for period, c0, c1, s0, s1 in terms:
        arg = TWO_PI * t / period
        cos_a = math.cos(arg)
        sin_a = math.sin(arg)
        result_0 += cos_a * c0 + sin_a * s0
        result_1 += cos_a * c1 + sin_a * s1
    return result_0, result_1


# Precomputed at import time: three rotations combined (angles are constants).
# Small-angle skew-symmetric equivalent:
#   [[ 1,     dr,  -dx ],
#    [ -dr,   1,   -de ],
#    [ dx,    de,   1  ]]
_FRAME_BIAS_MATRIX = _3x3_multiply(
    _3x3_multiply(
        _rotation_x(-_FRAME_BIAS_DE_RAD),
        _rotation_y(_FRAME_BIAS_DX_RAD),
    ),
    _rotation_z(_FRAME_BIAS_DR_RAD),
)


def _cross(a, b):
    """Cross product."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(v):
    """Euclidean norm."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _normalize(v):
    """Normalize to unit vector."""
    n = _norm(v)
    return (v[0] / n, v[1] / n, v[2] / n)


# ---------------------------------------------------------------------------
# Public: obliquity
# ---------------------------------------------------------------------------

def mean_obliquity_rad(jd_tt: float) -> float:
    """IAU 2006 mean obliquity of the ecliptic (radians)."""
    t = (jd_tt - JD_J2000) / DAYS_PER_JULIAN_CENTURY
    # ((((-0.0000000434*t - 0.000000576)*t + 0.00200340)*t
    #   - 0.0001831)*t - 46.836769)*t + 84381.406
    arcsec = (((((-4.34e-08 * t - 5.76e-07) * t + 0.00200340) * t
                - 0.0001831) * t - 46.836769) * t + 84381.406)
    return arcsec * ARCSEC_TO_RAD


# ---------------------------------------------------------------------------
# Public: precession
# ---------------------------------------------------------------------------

def vondrak2011_precession_matrix(
    jd_tt: float,
) -> tuple:
    """Vondrák 2011 precession matrix (ICRF → mean equator of date).

    Returns (matrix_3x3, mean_obliquity_rad).
    """
    t = (jd_tt - JD_J2000) / DAYS_PER_JULIAN_CENTURY

    # --- ecliptic pole ---
    p_per, q_per = _vondrak_periodic_sum(_VONDRAK_ECLIPTIC_PERIODIC, t)
    p = (p_per + _poly4(_VONDRAK_ECLIPTIC_PA, t)) * ARCSEC_TO_RAD
    q = (q_per + _poly4(_VONDRAK_ECLIPTIC_QA, t)) * ARCSEC_TO_RAD

    sin_eps0 = math.sin(_J2000_OBLIQUITY_RAD)
    cos_eps0 = math.cos(_J2000_OBLIQUITY_RAD)
    z_ecliptic = math.sqrt(max(1.0 - p * p - q * q, 0.0))
    ecliptic_pole = (
        p,
        -q * cos_eps0 - z_ecliptic * sin_eps0,
        -q * sin_eps0 + z_ecliptic * cos_eps0,
    )

    # --- equator pole ---
    x_per, y_per = _vondrak_periodic_sum(_VONDRAK_EQUATOR_PERIODIC, t)
    x = (x_per + _poly4(_VONDRAK_EQUATOR_XA, t)) * ARCSEC_TO_RAD
    y = (y_per + _poly4(_VONDRAK_EQUATOR_YA, t)) * ARCSEC_TO_RAD

    z_equator = math.sqrt(max(1.0 - x * x - y * y, 0.0))
    equator_pole = (x, y, z_equator)

    # --- equinox basis ---
    equinox_x = _normalize(_cross(equator_pole, ecliptic_pole))
    equinox_y = _cross(equator_pole, equinox_x)

    # Precession matrix (ICRF → mean equator of date)
    rp = (
        (equinox_x[0],   equinox_x[1],   equinox_x[2]),
        (equinox_y[0],   equinox_y[1],   equinox_y[2]),
        (equator_pole[0], equator_pole[1], equator_pole[2]),
    )
    matrix = _3x3_multiply(rp, _FRAME_BIAS_MATRIX)
    obliquity = mean_obliquity_rad(jd_tt)
    return matrix, obliquity


# ---------------------------------------------------------------------------
# Public: nutation
# ---------------------------------------------------------------------------

def _iau2000b_fundamental_args(t: float) -> list[float]:
    """Five fundamental Delaunay arguments (radians) at *t* centuries since J2000."""
    return [
        _fmod_arcsec_to_rad(485868.249036 + t * 1717915923.2178),
        _fmod_arcsec_to_rad(1287104.79305 + t * 129596581.0481),
        _fmod_arcsec_to_rad(335779.526232 + t * 1739527262.8478),
        _fmod_arcsec_to_rad(1072260.70369 + t * 1602961601.2090),
        _fmod_arcsec_to_rad(450160.398036 - t * 6962890.5431),
    ]


def iau2000b_nutation_angles(
    jd_tt: float,
) -> dict[str, float]:
    """IAU 2000B nutation.

    Returns dict with keys:
      dpsi_rad, deps_rad, mean_obliquity_rad, true_obliquity_rad
    """
    t = (jd_tt - JD_J2000) / DAYS_PER_JULIAN_CENTURY
    fa = _iau2000b_fundamental_args(t)

    dp = 0.0
    de = 0.0
    for l, lp, f, d, om, ps, pst, pc, ec, ect, es in _IAU2000B_TERMS:
        arg = l * fa[0] + lp * fa[1] + f * fa[2] + d * fa[3] + om * fa[4]
        s = math.sin(arg)
        c = math.cos(arg)
        dp += (ps + pst * t) * s + pc * c
        de += (ec + ect * t) * c + es * s

    dpsi_arcsec = -0.000135 + dp * 1.0e-7
    deps_arcsec = 0.000388 + de * 1.0e-7
    mean_obliquity = mean_obliquity_rad(jd_tt)

    return {
        "dpsi_rad": dpsi_arcsec * ARCSEC_TO_RAD,
        "deps_rad": deps_arcsec * ARCSEC_TO_RAD,
        "mean_obliquity_rad": mean_obliquity,
        "true_obliquity_rad": mean_obliquity + deps_arcsec * ARCSEC_TO_RAD,
    }


# ---------------------------------------------------------------------------
# Public: equation of equinoxes
# ---------------------------------------------------------------------------

def equation_of_equinoxes_rad(jd_tt: float) -> float:
    """Equation of equinoxes = Δψ · cos(ε)  (radians)."""
    nut = iau2000b_nutation_angles(jd_tt)
    return nut["dpsi_rad"] * math.cos(nut["true_obliquity_rad"])


# ---------------------------------------------------------------------------
# Public: coordinate transforms
# ---------------------------------------------------------------------------

def rotate_ecliptic_to_equator(
    vector: tuple[float, float, float],
    obliquity_rad: float,
) -> tuple[float, float, float]:
    """Rotate ecliptic coordinates to equatorial (about X axis by obliquity)."""
    cos_e = math.cos(obliquity_rad)
    sin_e = math.sin(obliquity_rad)
    x, y, z = vector
    return (x,
            cos_e * y - sin_e * z,
            sin_e * y + cos_e * z)


def rotate_equator_to_ecliptic(
    vector: tuple[float, float, float],
    obliquity_rad: float,
) -> tuple[float, float, float]:
    """Rotate equatorial coordinates to ecliptic (inverse of above)."""
    cos_e = math.cos(obliquity_rad)
    sin_e = math.sin(obliquity_rad)
    x, y, z = vector
    return (x,
            cos_e * y + sin_e * z,
            -sin_e * y + cos_e * z)


# ---------------------------------------------------------------------------
# High-level: J2000 ecliptic → true ecliptic of date
# ---------------------------------------------------------------------------

def j2000_ecliptic_to_date(
    vector_j2000_ecliptic: tuple[float, float, float],
    jd_tt: float,
) -> tuple[float, float, float]:
    """Convert a J2000.0 ecliptic position to the true ecliptic of date.

    vector_j2000_ecliptic  — (x, y, z) in J2000 ecliptic frame (km or AU)
    jd_tt                  — TT Julian date
    returns                — (x, y, z) in true ecliptic of date

    Pipeline:
      J2000 ecliptic → J2000 equator → Vondrák 2011 → mean eq. of date
      → nutation → true eq. of date → true ecliptic of date
    """
    nut = iau2000b_nutation_angles(jd_tt)
    precession, _ = vondrak2011_precession_matrix(jd_tt)

    # Step 1: J2000 ecliptic → J2000 equator
    v = rotate_ecliptic_to_equator(vector_j2000_ecliptic, _J2000_OBLIQUITY_RAD)

    # Step 2: J2000 equator → mean equator of date (Vondrák 2011)
    v = _3x3_apply(precession, v)

    # Step 3: mean equator → true equator (nutation)
    # nutation matrix = R1(-ε̅) · R3(-Δψ) · R1(ε̅)
    mean_obl = nut["mean_obliquity_rad"]
    dpsi = nut["dpsi_rad"]
    m = _3x3_multiply(
        _3x3_multiply(
            _rotation_x(-mean_obl),
            _rotation_z(-dpsi),
        ),
        _rotation_x(mean_obl),
    )
    v = _3x3_apply(m, v)

    # Step 4: true equator → true ecliptic
    v = rotate_equator_to_ecliptic(v, nut["true_obliquity_rad"])

    return v


def j2000_ecliptic_longitude_to_date(
    longitude_rad: float,
    latitude_rad: float,
    radius: float,
    jd_tt: float,
) -> tuple[float, float, float]:
    """Convert a single J2000 ecliptic spherical point to true-ecliptic-of-date L,B,R.

    Convenience wrapper: converts spherical → Cartesian, applies
    j2000_ecliptic_to_date, converts back.
    """
    cos_lat = math.cos(latitude_rad)
    cart = (
        cos_lat * math.cos(longitude_rad),
        cos_lat * math.sin(longitude_rad),
        math.sin(latitude_rad),
    )
    cart_date = j2000_ecliptic_to_date(cart, jd_tt)
    x, y, z = cart_date
    r = _norm(cart_date)
    if r == 0.0:
        return 0.0, 0.0, 0.0
    return (
        math.atan2(y, x) % TWO_PI,
        math.asin(z / r),
        r * radius,  # scale back to original radius
    )
