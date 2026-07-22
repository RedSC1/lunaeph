"""Tests for solar terms (24 Jieqi) accuracy against Purple Mountain Observatory 2026 data."""

from __future__ import annotations

import math
import pytest
from lunaeph import search_solar_longitude, calendar_to_jd, jd_to_calendar

# 2026 Purple Mountain Observatory Solar Terms (Beijing Time, UTC+8)
# Format: (Month, Day, Hour, Minute, Target Ecliptic Longitude (Degrees))
SOLAR_TERMS_2026 = [
    (1, 5, 16, 23, 285.0),   # 小寒
    (1, 20, 9, 45, 300.0),   # 大寒
    (2, 4, 4, 2, 315.0),     # 立春
    (2, 18, 23, 52, 330.0),  # 雨水
    (3, 5, 21, 59, 345.0),   # 惊蛰
    (3, 20, 22, 46, 0.0),    # 春分
    (4, 5, 2, 40, 15.0),     # 清明
    (4, 20, 9, 39, 30.0),    # 谷雨
    (5, 5, 19, 49, 45.0),    # 立夏
    (5, 21, 8, 37, 60.0),    # 小满
    (6, 5, 23, 48, 75.0),    # 芒种
    (6, 21, 16, 25, 90.0),   # 夏至
    (7, 7, 9, 57, 105.0),    # 小暑
    (7, 23, 3, 13, 120.0),   # 大暑
    (8, 7, 19, 43, 135.0),   # 立秋
    (8, 23, 10, 19, 150.0),  # 处暑
    (9, 7, 22, 41, 165.0),   # 白露
    (9, 23, 8, 5, 180.0),    # 秋分
    (10, 8, 14, 29, 195.0),  # 寒露
    (10, 23, 17, 38, 210.0), # 霜降
    (11, 7, 17, 52, 225.0),  # 立冬
    (11, 22, 15, 23, 240.0), # 小雪
    (12, 7, 10, 53, 255.0),  # 大雪
    (12, 22, 4, 50, 270.0),  # 冬至
]

@pytest.mark.parametrize("month,day,hour,minute,lon_deg", SOLAR_TERMS_2026)
def test_solar_terms_2026(month, day, hour, minute, lon_deg):
    target_lon_rad = math.radians(lon_deg)
    
    # Estimate a bracket around the known date (we search +/- 5 days around the ~15th of the month)
    # The search function takes [start_jd, end_jd] bounds
    base_jd_utc = calendar_to_jd(2026, month, day, 12, 0, 0.0)
    start_jd = base_jd_utc - 5.0
    end_jd = base_jd_utc + 5.0
    
    # Find exact JD in UTC
    jd_exact = search_solar_longitude(target_lon_rad, start_jd, end_jd)
    
    # Convert JD back to Beijing Time (UTC+8)
    jd_bjt = jd_exact + 8.0 / 24.0
    y, mo, d, h, m, s = jd_to_calendar(jd_bjt)
    
    # Check if the calculated time matches PMO down to the minute
    # Allow a tolerance of +/- 1 minute since PMO minutes are rounded.
    # Note: jd_to_calendar gives exact seconds, we should round to nearest minute.
    
    total_minutes_calculated = d * 1440 + h * 60 + m + s / 60.0
    total_minutes_expected = day * 1440 + hour * 60 + minute
    
    diff_minutes = abs(total_minutes_calculated - total_minutes_expected)
    assert diff_minutes <= 1.0, f"Solar term at {lon_deg} deg failed: Expected {day} {hour}:{minute}, got {d} {h}:{m}:{s:.1f}"
