"""Chart calculation — wires time, precession, houses, signs, aspects."""

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
)
from ._aberration import apply_light_corrections
from ._deflection import apply_solar_deflection
from ._houses import calc_houses, HouseSystem
from ._signs import sign_degree_minute
from ._aspects import find_all_aspects


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


def _km_to_au(km: float) -> float:
    return km / 149597870.7


def _au_to_km(au: float) -> float:
    return au * 149597870.7


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

class Chart(dict):
    """A calculated astrology chart.

    Dict-like (chart["planets"], chart["houses"], etc.) plus ``set_orb()``
    to tweak aspect orbs after the fact.  The built-in default orb table
    (in ``_aspects.DEFAULT_ORBS``) is never modified.
    """

    def __init__(self, data: dict):
        super().__init__(data)
        self._body_lons = {k: p["longitude_rad"]
                           for k, p in data["planets"].items()}
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
                _compute_angle_aspects(self._body_lons, angle, orb_deg))
        return self

    def reset_orb(self, angle: float | str | int) -> "Chart":
        """Restore the default orb for *angle*."""
        from ._aspects import DEFAULT_ORBS
        return self.set_orb(angle, DEFAULT_ORBS.get(float(angle), 0.0))


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
) -> dict:
    """Calculate a western astrology chart.

    Parameters
    ----------
    year .. second: UTC calendar datetime.
    latitude_deg, longitude_deg: observer geodetic coordinates.
    house_system: HouseSystem enum (default Placidus).
    taiyin_position_fn: (body_id, jd_tdb) → (x, y, z) km ICRF.
        If None, imports taiyin_semi_analytic.position.
    taiyin_velocity_fn: (body_id, jd_tdb) → (vx, vy, vz) km/day ICRF.
        If None, imports taiyin_semi_analytic.velocity_icrf.

    Returns: dict with jd, date, observer, planets, houses, aspects.
    """
    # --- time ---
    # Convert local time → UTC
    utc_hour = hour - tz
    jd_utc = calendar_to_jd(year, month, day, utc_hour, minute, second)
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
    # taiyin API: position(jd, body_id), velocity_icrf(jd, body_id)
    earth_pos_km = taiyin_position_fn(jd_tt, 399)
    earth_vel_km_per_day = taiyin_velocity_fn(jd_tt, 399)
    earth_pos_au = tuple(_km_to_au(v) for v in earth_pos_km)
    earth_vel_au_per_day = tuple(_km_to_au(v) for v in earth_vel_km_per_day)

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
        helio_pos_km = taiyin_position_fn(jd_tt, body_id)
        helio_pos_au = tuple(_km_to_au(v) for v in helio_pos_km)

        # Geocentric
        geo_au = (
            helio_pos_au[0] - earth_pos_au[0],
            helio_pos_au[1] - earth_pos_au[1],
            helio_pos_au[2] - earth_pos_au[2],
        )

        # Light-time + aberration
        geo_au = apply_light_corrections(
            jd_tt,
            lambda jd: tuple(_km_to_au(v)
                             for v in taiyin_position_fn(jd, body_id)),
            earth_pos_au,
            earth_vel_au_per_day,
            light_time=True,
            aberration=True,
        )

        # Solar deflection
        geo_au = apply_solar_deflection(earth_pos_au, (
            earth_pos_au[0] + geo_au[0],
            earth_pos_au[1] + geo_au[1],
            earth_pos_au[2] + geo_au[2],
        ))

        # J2000 ecliptic → true ecliptic of date
        ecl_date = j2000_ecliptic_to_date(geo_au, jd_tt)

        # Spherical
        x, y, z = ecl_date
        r = math.sqrt(x * x + y * y + z * z)
        lon = math.atan2(y, x) % (2.0 * math.pi)
        lat = math.asin(z / r) if r > 0.0 else 0.0

        sign_info, deg, min_ = sign_degree_minute(lon)
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

    # --- aspects ---
    body_lons = {k: p["longitude_rad"] for k, p in planets.items()}
    aspects = find_all_aspects(body_lons)

    # --- assemble ---
    y, mo, d, h, mi, s = jd_to_calendar(jd_utc)
    data = {
        "jd_utc": jd_utc,
        "jd_tt": jd_tt,
        "delta_t_s": delta_t_seconds_from_jd_ut1(jd_utc),
        "date_utc": f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{int(s):02d}Z",
        "observer": {
            "lat_deg": latitude_deg,
            "lon_deg": longitude_deg,
        },
        "planets": planets,
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
    return Chart(data)


def _format_angle(rad: float) -> dict:
    sign, deg, min_ = sign_degree_minute(rad)
    return {
        "sign": sign.name,
        "sign_abbrev": sign.abbrev,
        "degree": deg,
        "minute": min_,
        "longitude_rad": rad,
    }
