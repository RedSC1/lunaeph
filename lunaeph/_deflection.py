"""Solar gravitational deflection of light.

Ported from taiyin-ephemeris C++:
  src/corrections.cpp  — apply_gravitational_deflection_from_body_with_model
  include/taiyin/physical_constants.h — TAIYIN_AU_KM, solar Schwarzschild radius

For all planets the effect is << 0.01 arcsec — well below the threshold
that matters for a star chart.  Included because the formula is ~20 lines.
"""

from __future__ import annotations

import math
from typing import Sequence

# --- helpers (inline, no numpy) ---

def _norm(v: Sequence[float]) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _scale(v: Sequence[float], s: float) -> tuple[float, float, float]:
    return (v[0] * s, v[1] * s, v[2] * s)


def _unit(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = _norm(v)
    if n == 0.0:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AU_KM = 149597870.7
# Solar Schwarzschild radius: 2 * G * M_sun / c^2
_SOLAR_SCHWARZSCHILD_KM = 2.953250
_SOLAR_SCHWARZSCHILD_AU = _SOLAR_SCHWARZSCHILD_KM / _AU_KM  # ~1.974e-8


# ---------------------------------------------------------------------------
# Deflection
# ---------------------------------------------------------------------------

def apply_solar_deflection(
    observer_pos_au: tuple[float, float, float],
    target_pos_au: tuple[float, float, float],
    sun_pos_au: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> tuple[float, float, float]:
    """Apply solar gravitational deflection to a target position.

    Parameters
    ----------
    observer_pos_au: observer position (AU).  For geocentric, this is the
        Earth's heliocentric position.
    target_pos_au: target position, same frame (AU).
    sun_pos_au: Sun position (AU).  Defaults to origin.

    Returns: deflection-corrected position (AU).

    Formula
    -------
        p  = unit(target - observer)        # apparent direction
        e  = unit(observer - sun)           # Sun → observer
        q  = unit(target - sun)             # Sun → source
        deflected = p + R_s/(r·(1 + q·e)) · (e·(p·q) - q·(p·e))
    """
    geo = _sub(target_pos_au, observer_pos_au)
    distance = _norm(geo)
    if distance == 0.0:
        return geo

    p = _unit(geo)
    obs_from_sun = _sub(observer_pos_au, sun_pos_au)
    tgt_from_sun = _sub(target_pos_au, sun_pos_au)

    e = _unit(obs_from_sun)
    q = _unit(tgt_from_sun)

    r_obs = _norm(obs_from_sun)
    if r_obs == 0.0:
        return _sub(target_pos_au, observer_pos_au)  # at the Sun, can't deflect

    p_dot_q = _dot(p, q)
    p_dot_e = _dot(p, e)
    q_dot_e = _dot(q, e)

    raw_denom = 1.0 + q_dot_e
    # Clamp denominator near zero (target behind the Sun) to avoid singularity.
    # 1e-5 ≈ 0.25° solar radius → deflection is capped at ~8e-3 rad ≈ 0.5°.
    denom = raw_denom if raw_denom > 1e-5 else 1e-5
    if not math.isfinite(denom) or denom == 0.0:
        return _sub(target_pos_au, observer_pos_au)

    scale = _SOLAR_SCHWARZSCHILD_AU / (r_obs * denom)

    deflected = (
        p[0] + scale * (e[0] * p_dot_q - q[0] * p_dot_e),
        p[1] + scale * (e[1] * p_dot_q - q[1] * p_dot_e),
        p[2] + scale * (e[2] * p_dot_q - q[2] * p_dot_e),
    )
    direction = _unit(deflected)
    return _scale(direction, distance)
