"""Tests for relationship and predictive chart types in LunaEph.

Verifies Synastry, Composite, Davison, Progressions, Solar Arc, Naibod Direction, Returns,
and derived compositions against Astrodienst astrological conventions and golden benchmarks.
"""

from __future__ import annotations

import math
import pytest

from lunaeph import calculate_chart, Chart
from lunaeph._chart import _spherical_midpoint, _circular_midpoint, ASTRODIENST_TROPICAL_MONTH_DAYS, TROPICAL_YEAR_DAYS


def test_spherical_midpoint():
    # Equator midpoint: (0, 0) and (0, 90) -> (0, 45)
    lat_m, lon_m = _spherical_midpoint(0.0, 0.0, 0.0, 90.0)
    assert abs(lat_m - 0.0) < 1e-5
    assert abs(lon_m - 45.0) < 1e-5

    # Antipodal fallback test
    lat_m2, lon_m2 = _spherical_midpoint(0.0, 0.0, 0.0, 180.0)
    assert lat_m2 == 0.0 and lon_m2 == 0.0

    # Crossing prime meridian: (40, -10) and (40, 10) -> (43.6..., 0)
    lat_m3, lon_m3 = _spherical_midpoint(40.0, -10.0, 40.0, 10.0)
    assert abs(lon_m3 - 0.0) < 1e-5
    assert lat_m3 > 40.0  # Spherical arc goes higher in latitude towards pole


def test_circular_midpoint_and_180_ambiguity():
    # 1. Normal short arc: 10 deg and 30 deg -> 20 deg
    m1 = _circular_midpoint(math.radians(10.0), math.radians(30.0))
    assert abs(math.degrees(m1) - 20.0) < 1e-5

    # 2. Wrapping around 0 deg: 350 deg and 10 deg -> 0 deg
    m2 = _circular_midpoint(math.radians(350.0), math.radians(10.0))
    assert abs(math.degrees(m2) - 0.0) < 1e-5 or abs(math.degrees(m2) - 360.0) < 1e-5

    # 3. 180 degree ambiguity: 0 deg and 180 deg.
    # Ref Asc at 45 deg -> should pick 90 deg (closest to 45 deg)
    m3_1 = _circular_midpoint(math.radians(0.0), math.radians(180.0), ref_asc_rad=math.radians(45.0))
    assert abs(math.degrees(m3_1) - 90.0) < 1e-5

    # Ref Asc at 225 deg -> should pick 270 deg
    m3_2 = _circular_midpoint(math.radians(0.0), math.radians(180.0), ref_asc_rad=math.radians(225.0))
    assert abs(math.degrees(m3_2) - 270.0) < 1e-5


@pytest.fixture
def chart_a():
    # Person A: 1990-01-01 12:00 UTC at London (51.5, -0.1)
    return calculate_chart(1990, 1, 1, 12, 0, latitude_deg=51.5, longitude_deg=-0.1)


@pytest.fixture
def chart_b():
    # Person B: 1992-06-15 18:30 UTC at New York (40.7, -74.0)
    return calculate_chart(1992, 6, 15, 18, 30, latitude_deg=40.7, longitude_deg=-74.0)


def test_synastry(chart_a, chart_b):
    syn = chart_a.synastry_with(chart_b)

    assert "cross_aspects" in syn
    assert "chart_a_in_chart_b_houses" in syn
    assert "chart_b_in_chart_a_houses" in syn

    # 1. Cross-chart aspects only: every aspect must connect body from A to body from B
    for asp in syn["cross_aspects"]:
        assert asp["chart_a_body"] in chart_a.planets
        assert asp["chart_b_body"] in chart_b.planets

    # 2. House placements: check 1-12 validity
    for body, h in syn["chart_a_in_chart_b_houses"].items():
        assert 1 <= h <= 12
    for body, h in syn["chart_b_in_chart_a_houses"].items():
        assert 1 <= h <= 12


def test_composite(chart_a, chart_b):
    comp = chart_a.composite_with(chart_b)

    assert isinstance(comp, Chart)
    assert "planets" in comp
    assert "houses" in comp

    # Planet longitude checks
    for key in comp.planets:
        lon_a = chart_a["planets"][key]["longitude_rad"]
        lon_b = chart_b["planets"][key]["longitude_rad"]
        expected_lon = _circular_midpoint(lon_a, lon_b, ref_asc_rad=chart_a["houses"]["ascendant"]["longitude_rad"])
        assert abs(comp["planets"][key]["longitude_rad"] - expected_lon) < 1e-5


def test_davison(chart_a, chart_b):
    # Spherical mode
    dav_sph = chart_a.davison_with(chart_b, mode="spherical")
    assert isinstance(dav_sph, Chart)

    expected_jd = (chart_a["jd_utc"] + chart_b["jd_utc"]) / 2.0
    assert abs(dav_sph["jd_utc"] - expected_jd) < 1e-5

    lat_m, lon_m = _spherical_midpoint(51.5, -0.1, 40.7, -74.0)
    assert abs(dav_sph["observer"]["lat_deg"] - lat_m) < 1e-5
    assert abs(dav_sph["observer"]["lon_deg"] - lon_m) < 1e-5

    # Arithmetic mode
    dav_ari = chart_a.davison_with(chart_b, mode="arithmetic")
    assert isinstance(dav_ari, Chart)
    assert abs(dav_ari["observer"]["lat_deg"] - (51.5 + 40.7) / 2.0) < 1e-5
    assert abs(dav_ari["observer"]["lon_deg"] - (-0.1 + -74.0) / 2.0) < 1e-5


def test_secondary_progression(chart_a):
    # Age 30 -> 30 ephemeris days after birth
    prog = chart_a.secondary_progression(30.0)

    assert isinstance(prog, Chart)
    assert abs(prog["jd_utc"] - (chart_a["jd_utc"] + 30.0)) < 1e-5

    # Target JD mode: 30 tropical years later
    target_jd = chart_a["jd_utc"] + 30.0 * TROPICAL_YEAR_DAYS
    prog_target = chart_a.secondary_progression(target_jd=target_jd)
    assert abs(prog_target["jd_utc"] - (chart_a["jd_utc"] + 30.0)) < 1e-5


def test_tertiary_i_and_ii(chart_a):
    # Tertiary I: 1 day = 1 tropical month (27.32158218 days of life)
    tert1 = chart_a.tertiary_i(30.0)
    expected_offset1 = (30.0 * TROPICAL_YEAR_DAYS) / ASTRODIENST_TROPICAL_MONTH_DAYS
    assert isinstance(tert1, Chart)
    assert abs(tert1["jd_utc"] - (chart_a["jd_utc"] + expected_offset1)) < 1e-5

    # Tertiary II (Astrodienst compatible): 27.32158218 ephemeris days per tropical year of life
    tert2 = chart_a.tertiary_ii(30.0)
    expected_offset2 = 30.0 * ASTRODIENST_TROPICAL_MONTH_DAYS
    assert isinstance(tert2, Chart)
    assert abs(tert2["jd_utc"] - (chart_a["jd_utc"] + expected_offset2)) < 1e-5


def test_solar_arc_and_naibod(chart_a):
    years = 25.0

    # True Solar Arc (secondary Sun longitude advancement)
    sa = chart_a.solar_arc(years)
    assert isinstance(sa, Chart)

    prog = chart_a.secondary_progression(years)
    expected_arc = (prog["planets"]["sun"]["longitude_rad"] - chart_a["planets"]["sun"]["longitude_rad"]) % (2.0 * math.pi)

    for key in sa.planets:
        natal_lon = chart_a["planets"][key]["longitude_rad"]
        expected_lon = (natal_lon + expected_arc) % (2.0 * math.pi)
        assert abs(sa["planets"][key]["longitude_rad"] - expected_lon) < 1e-5

    # Naibod Direction (fixed 0.98564733 deg/year)
    naibod = chart_a.naibod_direction(years)
    assert isinstance(naibod, Chart)
    naibod_arc = math.radians(years * 0.98564733)
    for key in naibod.planets:
        natal_lon = chart_a["planets"][key]["longitude_rad"]
        expected_lon = (natal_lon + naibod_arc) % (2.0 * math.pi)
        assert abs(naibod["planets"][key]["longitude_rad"] - expected_lon) < 1e-5


def test_solar_return(chart_a):
    sr = chart_a.solar_return(2025)

    assert isinstance(sr, Chart)

    natal_sun_lon = chart_a["planets"]["sun"]["longitude_rad"]
    return_sun_lon = sr["planets"]["sun"]["longitude_rad"]

    # Sun longitude in return chart must match natal Sun longitude exactly
    diff = (return_sun_lon - natal_sun_lon + math.pi) % (2.0 * math.pi) - math.pi
    assert abs(diff) < 1e-5


def test_lunar_return(chart_a):
    lr = chart_a.lunar_return(2025, 3)

    assert isinstance(lr, Chart)

    natal_moon_lon = chart_a["planets"]["moon"]["longitude_rad"]
    return_moon_lon = lr["planets"]["moon"]["longitude_rad"]

    # Moon longitude in return chart must match natal Moon longitude exactly
    diff = (return_moon_lon - natal_moon_lon + math.pi) % (2.0 * math.pi) - math.pi
    assert abs(diff) < 1e-5


def test_derived_compositions(chart_a, chart_b):
    cs = chart_a.composite_secondary(chart_b, 20.0)
    assert isinstance(cs, Chart)

    dt = chart_a.davison_tertiary(chart_b, 20.0)
    assert isinstance(dt, Chart)

    ms = chart_a.marks_secondary(chart_b, 20.0)
    assert isinstance(ms, Chart)

    mt = chart_a.marks_tertiary(chart_b, 20.0)
    assert isinstance(mt, Chart)

    mw_davison = chart_a.marks_with(chart_b, mode="davison")
    assert isinstance(mw_davison, Chart)

    mw_comp = chart_a.marks_with(chart_b, mode="composite")
    assert isinstance(mw_comp, Chart)
