"""Zodiac signs, elements, modalities."""

from __future__ import annotations

import math
from typing import NamedTuple

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_ABBREV = [
    "Ari", "Tau", "Gem", "Can",
    "Leo", "Vir", "Lib", "Sco",
    "Sag", "Cap", "Aqu", "Pis",
]

ELEMENT = [
    "fire", "earth", "air", "water",
    "fire", "earth", "air", "water",
    "fire", "earth", "air", "water",
]

MODALITY = [
    "cardinal", "fixed", "mutable",
    "cardinal", "fixed", "mutable",
    "cardinal", "fixed", "mutable",
    "cardinal", "fixed", "mutable",
]

RULER = [
    "Mars", "Venus", "Mercury", "Moon",
    "Sun", "Mercury", "Venus", "Pluto",
    "Jupiter", "Saturn", "Uranus", "Neptune",
]

DETRIMENT = [
    "Venus", "Pluto", "Jupiter", "Saturn",
    "Uranus", "Neptune", "Mars", "Moon",
    "Mercury", "Moon", "Sun", "Mercury",
]

EXALTATION = [
    "Sun", "Moon", "North Node", "Jupiter",
    "Neptune", "Mercury", "Saturn", "Uranus",
    "South Node", "Mars", None, "Venus",
]

FALL = [
    "Saturn", "Uranus", "South Node", "Mars",
    None, "Venus", "Sun", "Moon",
    "North Node", "Jupiter", "Neptune", "Mercury",
]


class SignInfo(NamedTuple):
    number: int       # 0–11
    name: str
    abbrev: str
    element: str
    modality: str
    ruler: str | None
    detriment: str | None
    exaltation: str | None
    fall: str | None


_SIGNS = tuple(
    SignInfo(i, SIGN_NAMES[i], SIGN_ABBREV[i],
             ELEMENT[i], MODALITY[i],
             RULER[i], DETRIMENT[i],
             EXALTATION[i], FALL[i])
    for i in range(12)
)


def sign_from_longitude(longitude_rad: float) -> SignInfo:
    """Return the zodiac sign for an ecliptic longitude (radians)."""
    idx = int(math.degrees(longitude_rad % (2.0 * math.pi)) // 30)
    return _SIGNS[idx % 12]


def sign_degree_minute(longitude_rad: float) -> tuple[SignInfo, int, int]:
    """Return (sign, degree, minute) for an ecliptic longitude."""
    deg = math.degrees(longitude_rad % (2.0 * math.pi))
    idx = int(deg // 30)
    pos = deg % 30
    d = int(pos)
    m = int((pos - d) * 60.0 + 0.5)
    if m >= 60:
        m = 0
        d += 1
    return _SIGNS[idx % 12], d, m


def degrees_to_zodiac(deg_total: float) -> tuple[str, float]:
    """Convert total ecliptic longitude in degrees to (sign_name, degree_in_sign)."""
    deg = deg_total % 360.0
    idx = int(deg // 30)
    pos = deg % 30.0
    return SIGN_NAMES[idx % 12], pos


# ---------------------------------------------------------------------------
# Shared lookup tables — canonical source, imported by other modules
# ---------------------------------------------------------------------------

SIGN_START_DEG: dict[str, float] = {
    "Aries": 0.0, "Taurus": 30.0, "Gemini": 60.0, "Cancer": 90.0,
    "Leo": 120.0, "Virgo": 150.0, "Libra": 180.0, "Scorpio": 210.0,
    "Sagittarius": 240.0, "Capricorn": 270.0, "Aquarius": 300.0, "Pisces": 330.0,
}

# inverse lookup — sign index → start degree (avoid reconstructing from SIGN_START_DEG)
_SIGN_INDEX_START_DEG = [0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0]


def sign_name_to_longitude(sign_name: str, degree_in_sign: float) -> float:
    """Convert sign name + degree-within-sign → total ecliptic longitude in degrees.

    >>> sign_name_to_longitude("Leo", 5.5)
    125.5
    """
    return SIGN_START_DEG[sign_name] + degree_in_sign


def sign_name_index(sign_name: str) -> int:
    """Return 0-based index for a sign name.

    >>> sign_name_index("Aries")
    0
    >>> sign_name_index("Pisces")
    11
    """
    return SIGN_NAMES.index(sign_name)


def sign_index_name(idx: int) -> str:
    """Return sign name for a 0-based index (wraps safely).

    >>> sign_index_name(0)
    'Aries'
    >>> sign_index_name(12)
    'Aries'
    """
    return SIGN_NAMES[idx % 12]


def sign_index_start_deg(idx: int) -> float:
    """Return the 0° longitude of a sign by its 0-based index.

    >>> sign_index_start_deg(0)
    0.0
    >>> sign_index_start_deg(5)
    150.0
    """
    return _SIGN_INDEX_START_DEG[idx % 12]

