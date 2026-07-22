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
    custom: list[tuple[str, float, float]] | None = None,
) -> list[dict]:
    """Find all aspects among bodies.

    Parameters
    ----------
    bodies: {name: ecliptic_longitude_rad}
    orbs: optional {aspect_name: orb_deg} overrides for built-in aspects.
        A key not matching any built-in aspect gets auto-registered as
        a custom aspect: ``name`` must be "angle_num" (e.g. "70.0").
    custom: optional list of (name, angle_deg, orb_deg) for additional
        custom aspects beyond what *orbs* provides.

    Returns: list of dicts with body1, body2, aspect, angle_deg, orb_deg.
    """
    # Build the full aspect list: builtins + custom
    all_aspects: list[tuple[str, float, float, bool]] = [
        (a.name, a.angle_deg, a.orb_deg, a.major) for a in ASPECTS
    ]
    # Override orbs for builtins, add auto-registered customs
    if orbs:
        for key, orb_val in orbs.items():
            found = False
            for i, (name, ang, _, major) in enumerate(all_aspects):
                if name == key:
                    all_aspects[i] = (name, ang, orb_val, major)
                    found = True
                    break
            if not found:
                # Auto-register: key is the angle as string, e.g. "70.0"
                try:
                    angle = float(key)
                except ValueError:
                    continue
                all_aspects.append((key, angle, orb_val, False))
    # Append explicit custom aspects
    if custom:
        for name, angle, orb_val in custom:
            all_aspects.append((name, angle, orb_val, False))

    names = sorted(bodies.keys())
    results = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            sep = angular_separation_deg(bodies[names[i]], bodies[names[j]])
            for name, angle, orb, major in all_aspects:
                if orb <= 0.0:
                    continue
                if abs(sep - angle) <= orb:
                    results.append({
                        "body1": names[i],
                        "body2": names[j],
                        "aspect": name,
                        "angle_deg": round(sep, 4),
                        "orb_deg": round(abs(sep - angle), 4),
                        "major": major,
                    })
                    break  # closest matching aspect only
    return results
