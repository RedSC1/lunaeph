"""Aspect calculation.

All angles in degrees.  Orbs are defaults; override per-aspect when calling.
"""

from __future__ import annotations

import math
from typing import NamedTuple

TWO_PI = 2.0 * math.pi


class AspectDef(NamedTuple):
    name: str
    angle_deg: float
    orb_deg: float       # default orb
    major: bool


# Ordered from tightest to widest orb
ASPECTS: tuple[AspectDef, ...] = (
    AspectDef("conjunction",       0.0,   8.0, True),
    AspectDef("opposition",      180.0,   8.0, True),
    AspectDef("trine",           120.0,   7.0, True),
    AspectDef("square",           90.0,   7.0, True),
    AspectDef("sextile",          60.0,   5.0, True),
    AspectDef("quincunx",        150.0,   3.0, False),
    AspectDef("semisextile",      30.0,   2.0, False),
    AspectDef("semisquare",       45.0,   2.0, False),
    AspectDef("sesquiquadrate",  135.0,   2.0, False),
    AspectDef("quintile",         72.0,   1.5, False),
    AspectDef("biquintile",      144.0,   1.5, False),
)


def angular_separation_deg(lon1_rad: float, lon2_rad: float) -> float:
    """Shortest angular distance between two ecliptic longitudes (degrees)."""
    diff = abs(lon1_rad - lon2_rad) % TWO_PI
    if diff > math.pi:
        diff = TWO_PI - diff
    return math.degrees(diff)


def find_aspects(
    bodies: dict[str, float],
    orbs: dict[str, float] | None = None,
) -> list[dict]:
    """Find all aspects among bodies.

    Parameters
    ----------
    bodies: {name: ecliptic_longitude_rad}
    orbs: optional {aspect_name: orb_deg} overrides

    Returns: list of dicts with body1, body2, aspect, angle_deg, orb_deg.
    """
    names = sorted(bodies.keys())
    results = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            sep = angular_separation_deg(bodies[names[i]], bodies[names[j]])
            for asp in ASPECTS:
                orb = (orbs or {}).get(asp.name, asp.orb_deg)
                if abs(sep - asp.angle_deg) <= orb:
                    results.append({
                        "body1": names[i],
                        "body2": names[j],
                        "aspect": asp.name,
                        "angle_deg": round(sep, 4),
                        "orb_deg": round(abs(sep - asp.angle_deg), 4),
                        "major": asp.major,
                    })
                    break  # closest matching aspect only
    return results
