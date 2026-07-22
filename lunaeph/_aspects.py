"""Aspect calculation.

Built-in orbs are read-only defaults.  One source table — no duplication.
"""

from __future__ import annotations

import math

TWO_PI = 2.0 * math.pi

# (name, default_orb_deg, major)
_AspectSpec = tuple[str, float, bool]

# Single source of truth — angle → (name, orb, major)
_DEFAULT_SPECS: dict[float, _AspectSpec] = {
    0.0:   ("conjunction",      8.0, True),
    30.0:  ("semisextile",      2.0, False),
    36.0:  ("decile",           2.0, False),
    45.0:  ("semisquare",       2.0, False),
    60.0:  ("sextile",          5.0, True),
    72.0:  ("quintile",         1.5, False),
    90.0:  ("square",           7.0, True),
    120.0: ("trine",            7.0, True),
    135.0: ("sesquiquadrate",   2.0, False),
    144.0: ("biquintile",       1.5, False),
    150.0: ("quincunx",         3.0, False),
    180.0: ("opposition",       8.0, True),
}

# Derived read-only views (never modified)
DEFAULT_ORBS: dict[float, float] = {a: s[1] for a, s in _DEFAULT_SPECS.items()}
_ANGLE_NAMES: dict[float, str] = {a: s[0] for a, s in _DEFAULT_SPECS.items()}
_ANGLE_MAJOR: set[float] = {a for a, s in _DEFAULT_SPECS.items() if s[2]}


def angular_separation_deg(lon1_rad: float, lon2_rad: float) -> float:
    """Shortest angular distance between two ecliptic longitudes (degrees)."""
    diff = abs(lon1_rad - lon2_rad) % TWO_PI
    if diff > math.pi:
        diff = TWO_PI - diff
    return math.degrees(diff)


def _compute_angle_aspects(
    bodies: dict[str, float],
    angle_deg: float,
    orb_deg: float,
) -> list[dict]:
    """Scan all body pairs for a single aspect angle."""
    spec = _DEFAULT_SPECS.get(angle_deg)
    name = spec[0] if spec else str(angle_deg)
    major = angle_deg in _ANGLE_MAJOR
    names = sorted(bodies.keys())
    results = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            sep = angular_separation_deg(bodies[names[i]], bodies[names[j]])
            diff = abs(sep - angle_deg)
            if diff <= orb_deg:
                results.append({
                    "body1": names[i],
                    "body2": names[j],
                    "aspect": name,
                    "aspect_angle_deg": angle_deg,
                    "separation_deg": round(sep, 4),
                    "orb_deg": round(diff, 4),
                    "major": major,
                })
    return results


def find_all_aspects(
    bodies: dict[str, float],
    orbs: dict[float, float] | None = None,
) -> list[dict]:
    """Compute aspects for all angles in *orbs* (defaults to DEFAULT_ORBS)."""
    table = orbs if orbs is not None else DEFAULT_ORBS
    results = []
    for angle, orb in table.items():
        if orb > 0.0:
            results.extend(_compute_angle_aspects(bodies, angle, orb))
    return results
