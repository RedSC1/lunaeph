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

