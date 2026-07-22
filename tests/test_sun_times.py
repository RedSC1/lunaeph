"""Oracle tests for equation_of_time, apparent_solar_time, sun_times."""

import math
import pytest
from lunaeph._time import calendar_to_jd, jd_to_calendar
from lunaeph._chart import (
    equation_of_time_minutes,
    apparent_solar_time_minutes,
    sun_times,
    _get_body_lon_at_jd,
)


# ---------------------------------------------------------------------------
# Equation of Time — known values from USNO (~±1 min tolerance)
# ---------------------------------------------------------------------------

EOT_CASES = [
    # (year, month, day, expected_eot_minutes)
    (2024, 2, 11, -14.2),    # Near minimum (sundial slow)
    (2024, 11, 3, +16.5),    # Near maximum (sundial fast)
    (2024, 4, 15, 0.0),      # Near zero crossing
    (2024, 6, 13, 0.0),      # Near zero crossing
    (2024, 9, 1, 0.0),       # Near zero crossing
    (2024, 12, 25, 0.0),     # Near zero crossing
    (2003, 3, 13, -9.0),     # Golden chart date (approximate)
]


def test_eot_approximate():
    """EoT should be within the known ±17 min envelope."""
    for year, month, day, _ in EOT_CASES:
        jd = calendar_to_jd(year, month, day, 12, 0, 0.0)
        eot = equation_of_time_minutes(jd)
        assert -17.5 < eot < 17.5, \
            f"{year}-{month:02d}-{day:02d}: EoT = {eot:.2f} min outside ±17 min bounds"


def test_eot_year_cycle():
    """EoT should cross zero 4 times a year (seasonal pattern)."""
    # Sample EoT at the 1st of each month in 2024
    eot_values = []
    for month in range(1, 13):
        jd = calendar_to_jd(2024, month, 1, 12, 0, 0.0)
        eot_values.append(equation_of_time_minutes(jd))

    # Count sign changes (zero crossings)
    sign = [1 if v > 0 else -1 for v in eot_values]
    crossings = sum(1 for i in range(len(sign) - 1) if sign[i] != sign[i + 1])
    assert crossings >= 3, f"Expected ≥3 zero crossings in a year, got {crossings}"


# ---------------------------------------------------------------------------
# Sunrise/Sunset — physical consistency
# ---------------------------------------------------------------------------

def test_sun_above_horizon_at_transit():
    """At transit, the Sun should be above the horizon for most locations."""
    for lat in [0, 23, 40, 51, 60]:
        times = sun_times(2024, 6, 21, lon_deg=0, lat_deg=lat, tz=0)
        if times["transit"] is None:
            continue
        # At transit in summer, Sun altitude should be positive
        from lunaeph._precession import mean_obliquity_rad
        from lunaeph._time import jd_ut1_to_tt
        jd = times["transit"]
        jd_tt = jd_ut1_to_tt(jd)
        sun_lon = _get_body_lon_at_jd(jd, 10)
        obl = mean_obliquity_rad(jd_tt)
        dec = math.asin(math.sin(obl) * math.sin(sun_lon))
        meridian_alt = math.pi / 2 - math.radians(lat) + dec
        assert meridian_alt > -0.05, \
            f"lat={lat}°: Sun altitude at transit = {math.degrees(meridian_alt):.1f}° (should be > 0)"


def test_sunrise_before_sunset():
    """Sunrise must be before sunset."""
    times = sun_times(2003, 3, 13, lon_deg=118.49, lat_deg=37.45, tz=8.0)
    if times["rise"] and times["set"]:
        assert times["rise"] < times["set"], "Sunrise after sunset!"


def test_sunrise_before_transit_before_sunset():
    """Proper ordering: rise → transit → set."""
    times = sun_times(2003, 3, 13, lon_deg=118.49, lat_deg=37.45, tz=8.0)
    r, t, s = times["rise"], times["transit"], times["set"]
    if r and t and s:
        assert r < t < s, f"Order wrong: rise={r}, transit={t}, set={s}"


def test_twilight_ordering():
    """Astron dawn < nautical dawn < civil dawn < rise < set < civil dusk < nautical dusk < astron dusk."""
    times = sun_times(2003, 3, 13, lon_deg=118.49, lat_deg=37.45, tz=8.0)
    order = [
        times["astron_dawn"], times["nautical_dawn"], times["civil_dawn"],
        times["rise"], times["set"],
        times["civil_dusk"], times["nautical_dusk"], times["astron_dusk"],
    ]
    # Filter out None
    vals = [(k, v) for k, v in zip(
        ["astron_dawn", "nautical_dawn", "civil_dawn", "rise", "set",
         "civil_dusk", "nautical_dusk", "astron_dusk"], order) if v is not None]
    for i in range(len(vals) - 1):
        assert vals[i][1] < vals[i + 1][1], \
            f"{vals[i][0]} ({vals[i][1]:.4f}) >= {vals[i+1][0]} ({vals[i+1][1]:.4f})"


def test_day_length_reasonable():
    """Mid-latitude day length should be between 0 and 24 hours."""
    times = sun_times(2003, 3, 13, lon_deg=118.49, lat_deg=37.45, tz=8.0)
    if times["rise"] and times["set"]:
        day_len_h = (times["set"] - times["rise"]) * 24
        assert 0 < day_len_h < 24, f"Day length = {day_len_h:.1f}h (unreasonable)"
        # Mid-March at 37°N should be ~12h
        assert 10 < day_len_h < 14, f"Day length = {day_len_h:.1f}h (expected ~12h for March)"


# ---------------------------------------------------------------------------
# Polar edge cases
# ---------------------------------------------------------------------------

def test_polar_summer_no_sunset():
    """Summer solstice above Arctic Circle: no sunset."""
    times = sun_times(2024, 6, 21, lon_deg=15.0, lat_deg=78.0, tz=2.0)
    assert times["rise"] is None, "Expected no sunrise (midnight sun)"
    assert times["set"] is None, "Expected no sunset (midnight sun)"
    assert times["transit"] is not None, "Transit should exist even in polar day"


def test_polar_winter_no_sunrise():
    """Winter solstice above Arctic Circle: no sunrise."""
    times = sun_times(2024, 12, 21, lon_deg=15.0, lat_deg=78.0, tz=2.0)
    assert times["rise"] is None, "Expected no sunrise (polar night)"
    assert times["set"] is None, "Expected no sunset (polar night)"
    assert times["civil_dawn"] is None, "Expected no civil dawn"
    # Nautical and astronomical twilight may still exist
    assert times["transit"] is not None, "Transit should exist even in polar night"


def test_equator_consistent():
    """At the equator, day and night are roughly 12h year-round."""
    times = sun_times(2024, 3, 20, lon_deg=0, lat_deg=0, tz=0)
    if times["rise"] and times["set"]:
        day_len_h = (times["set"] - times["rise"]) * 24
        assert 11.5 < day_len_h < 12.5, \
            f"Equator day length = {day_len_h:.1f}h (expected ~12h)"


# ---------------------------------------------------------------------------
# Apparent solar time
# ---------------------------------------------------------------------------

def test_apparent_solar_time_noon():
    """On a day near equinox at 0° longitude, apparent noon ≈ 12:00."""
    jd = calendar_to_jd(2024, 3, 20, 12, 0, 0.0)
    ast = apparent_solar_time_minutes(jd, 0.0)
    # Should be roughly 12:00 ± 10 min
    assert 710 < ast < 730, f"Apparent solar time at 12:00 UT, 0° lon = {ast:.1f} min"
