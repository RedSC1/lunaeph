"""Tests for Lunar Points (Node & Lilith) against C++ ephemeris oracle values."""

from __future__ import annotations

import math
import pytest
from lunaeph import calculate_chart
from lunaeph._moon_points import (
    calc_mean_node_ecliptic_of_date,
    calc_mean_apogee_ecliptic_of_date,
)

# Benchmark Epoch: JD 2460409.0 (2024-04-10 12:00:00 TT)
# Exact values from taiyin-ephemeris C++ test_lunar_points_astrology.cpp:
# Mean Node (IERS 2003): 15.662505452962762 deg
# Mean Lilith (Delaunay): 170.92150432407695 deg
# True Node (Geometric): ~15.627613595150201 deg
# True Lilith (Osculating): ~182.7274859203948 deg

JD_TT_BENCH = 2460409.0

def test_mean_node_cpp_oracle():
    node_deg = calc_mean_node_ecliptic_of_date(JD_TT_BENCH) * 180.0 / math.pi
    expected_deg = 15.662505452962762
    # Expect accuracy within 1e-8 degrees (0.00003 arcsec)
    assert abs(node_deg - expected_deg) < 1e-8, f"Mean node deviation: {node_deg} vs {expected_deg}"

def test_mean_lilith_cpp_oracle():
    lilith_deg = calc_mean_apogee_ecliptic_of_date(JD_TT_BENCH) * 180.0 / math.pi
    expected_deg = 170.92150432407695
    # Expect accuracy within 1e-8 degrees
    assert abs(lilith_deg - expected_deg) < 1e-8, f"Mean Lilith deviation: {lilith_deg} vs {expected_deg}"

def test_chart_moon_points_cpp_oracle():
    # 2024-04-08 12:00:00 UTC corresponds to JD 2460409.0
    chart = calculate_chart(2024, 4, 8, 12, 0, 0.0, tz=0.0)
    planets = chart["planets"]
    
    # Test Mean Node
    mean_node_deg = planets["mean_node"]["longitude_rad"] * 180.0 / math.pi
    assert abs(mean_node_deg - 15.662505) < 0.001
    
    # Test Mean Lilith
    mean_lilith_deg = planets["mean_lilith"]["longitude_rad"] * 180.0 / math.pi
    assert abs(mean_lilith_deg - 170.921504) < 0.001
    
    # Test True Node (within ~1 arcmin of geometric C++ oracle)
    true_node_deg = planets["true_node"]["longitude_rad"] * 180.0 / math.pi
    assert abs(true_node_deg - 15.6276) < 0.05
    
    # Test True Lilith (within ~0.05 deg of C++ two-body osculating oracle)
    true_lilith_deg = planets["true_lilith"]["longitude_rad"] * 180.0 / math.pi
    assert abs(true_lilith_deg - 182.727) < 0.05

def test_classical_dignities_and_receptions_oracle():
    # Test Oracle Chart: 2003-03-13 14:15 BJT, Beijing
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    # Mutual Receptions check
    mrs = chart["mutual_receptions"]
    pairs = [set(mr["planets"]) for mr in mrs]
    assert {"sun", "jupiter"} in pairs
    assert {"mercury", "venus"} in pairs
    
    # Check Moon receptions
    moon_received = chart["planets"]["moon"]["classical"]["received_by"]
    assert "mercury" in moon_received
    assert "term" in moon_received["mercury"]
    assert "face" in moon_received["mercury"]

def test_same_degrees_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    sds = chart["same_degrees"]
    
    deg_map = {sd["degree"]: set(sd["points"]) for sd in sds}
    assert 22 in deg_map and {"sun", "saturn"}.issubset(deg_map[22])
    assert 14 in deg_map and {"moon", "mercury"}.issubset(deg_map[14])
    assert 12 in deg_map and {"venus", "neptune"}.issubset(deg_map[12])
    assert 5 in deg_map and {"mars", "ascendant"}.issubset(deg_map[5])

def test_firdaria_oracle():
    # Day chart (Sun above horizon)
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    # Timeline
    timeline = chart.firdaria()
    assert timeline[0]["ruler"] == "sun"
    assert timeline[0]["end_age"] == 10.0
    assert timeline[1]["ruler"] == "venus"
    assert timeline[2]["ruler"] == "mercury"
    
    # Active Firdaria at age 21
    current = chart.firdaria(21.0)
    assert current["major_ruler"] == "mercury"
    assert current["minor_ruler"] == "moon"

