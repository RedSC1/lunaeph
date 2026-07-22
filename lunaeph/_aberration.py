"""Light-time correction and annual stellar aberration.

Ported from taiyin-ephemeris C++:
  src/corrections.cpp  — solve_light_time_iteration,
                          apply_observer_velocity_aberration
  include/taiyin/corrections.h — TAIYIN_LIGHT_TIME_DAYS_PER_AU

Both corrections are applied in-place to geocentric positions.
The caller is expected to have already computed geocentric ICRF/Ecliptic
positions from taiyin before calling these functions.
"""

from __future__ import annotations

import math
from typing import Callable, Sequence

# Light-time: 1 AU / c ≈ 499.0 s / 86400 s/day
LIGHT_TIME_DAYS_PER_AU = 0.00577551833109

_DEFAULT_MAX_ITER = 5
_DEFAULT_TOLERANCE_DAYS = 1e-8  # ~0.9 ms → ~30 m at planetary distances


# ---------------------------------------------------------------------------
# Vector helpers (inlined to avoid numpy dependency)
# ---------------------------------------------------------------------------

def _norm(v: Sequence[float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(v: Sequence[float], s: float) -> tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _add(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = _norm(v)
    if n == 0.0:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


# ---------------------------------------------------------------------------
# Light-time
# ---------------------------------------------------------------------------

def apply_light_time(
    jd_tt: float,
    target_pos_au: tuple[float, float, float],
    observer_pos_au: tuple[float, float, float],
    target_pos_fn: Callable[[float], tuple[float, float, float]],
    max_iter: int = _DEFAULT_MAX_ITER,
    tol_days: float = _DEFAULT_TOLERANCE_DAYS,
) -> tuple[float, float, float]:
    """Retard a planetary position by the light-travel time.

    Parameters
    ----------
    jd_tt: TT Julian date of observation.
    target_pos_au: approximate geocentric position at jd_tt (AU).
    observer_pos_au: observer position (AU).  For geocentric this is zero;
        for topocentric this is the observer's geocentric position.
    target_pos_fn: callable returning the planet's heliocentric position
        (AU) at a given TT JD.
    max_iter: maximum Newton iterations (default 5).
    tol_days: convergence tolerance in days (default 1e-8).

    Returns: retarded geocentric position (AU).
    """
    position = _sub(target_pos_au, observer_pos_au)
    distance = _norm(position)
    if distance == 0.0:
        return position

    tau = distance * LIGHT_TIME_DAYS_PER_AU
    for _ in range(max_iter):
        emission_jd = jd_tt - tau
        retarded_target = target_pos_fn(emission_jd)
        position = _sub(retarded_target, observer_pos_au)
        distance = _norm(position)
        if distance == 0.0:
            return position
        next_tau = distance * LIGHT_TIME_DAYS_PER_AU
        if abs(next_tau - tau) <= tol_days:
            return position
        tau = next_tau

    # Exceeded max iterations — return last estimate
    return position


# ---------------------------------------------------------------------------
# Stellar aberration
# ---------------------------------------------------------------------------

def apply_aberration(
    source_geocentric_position_au: tuple[float, float, float],
    observer_velocity_au_per_day: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Apply annual stellar aberration (special-relativistic velocity form).

    source_geocentric_position_au: uncorrected geocentric position (AU).
    observer_velocity_au_per_day: observer velocity in the chosen frame
        (AU/day).  For annual aberration, this is Earth's barycentric or
        heliocentric velocity.

    Returns: aberration-corrected geocentric position (AU).
    """
    distance = _norm(source_geocentric_position_au)
    if distance == 0.0:
        return source_geocentric_position_au

    u = _scale(source_geocentric_position_au, 1.0 / distance)
    beta = _scale(observer_velocity_au_per_day, LIGHT_TIME_DAYS_PER_AU)
    beta2 = _dot(beta, beta)
    if beta2 >= 1.0:
        return source_geocentric_position_au

    inv_gamma = math.sqrt(1.0 - beta2)
    q = 1.0 + inv_gamma
    if q == 0.0:
        return source_geocentric_position_au

    u_dot_beta = _dot(u, beta)
    w1 = 1.0 + u_dot_beta / q

    aberrated = (
        u[0] * inv_gamma + beta[0] * w1,
        u[1] * inv_gamma + beta[1] * w1,
        u[2] * inv_gamma + beta[2] * w1,
    )
    direction = _normalize(aberrated)
    return _scale(direction, distance)


# ---------------------------------------------------------------------------
# Convenience: both corrections at once
# ---------------------------------------------------------------------------

def apply_light_corrections(
    jd_tt: float,
    heliocentric_target_fn: Callable[[float], tuple[float, float, float]],
    earth_heliocentric_pos_au: tuple[float, float, float],
    earth_heliocentric_vel_au_per_day: tuple[float, float, float],
    *,
    light_time: bool = True,
    aberration: bool = True,
) -> tuple[float, float, float]:
    """Apply light-time and aberration to a geocentric planet position.

    This is the recommended high-level entry point.  It:
      1. Converts to geocentric
      2. (optionally) retards for light-time
      3. (optionally) corrects for stellar aberration

    Returns the corrected geocentric position in AU.
    """
    target_pos = heliocentric_target_fn(jd_tt)
    geo = _sub(target_pos, earth_heliocentric_pos_au)

    if light_time:
        geo = apply_light_time(
            jd_tt, geo, (0.0, 0.0, 0.0),
            lambda jd: _sub(heliocentric_target_fn(jd),
                            earth_heliocentric_pos_au),
        )

    if aberration:
        geo = apply_aberration(geo, earth_heliocentric_vel_au_per_day)

    return geo
