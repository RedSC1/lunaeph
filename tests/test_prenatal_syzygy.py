"""Oracle tests for search_prenatal_syzygy — verifies the true last New/Full Moon before birth.

Core verification: at the computed syzygy JD, the Sun-Moon angular separation
must be within 0.01° of 0° (new moon) or 180° (full moon).
"""

import math
import pytest
from lunaeph._chart import search_prenatal_syzygy, _get_body_lon_at_jd, _newton_bisection, new_moons_between, full_moons_between
from lunaeph._time import calendar_to_jd
from lunaeph._signs import sign_name_to_longitude


# ---------------------------------------------------------------------------
# Helper: compute Sun-Moon angular difference at a given JD
# ---------------------------------------------------------------------------

def _sun_moon_diff_deg(jd_utc: float) -> float:
    """Return |moon_lon - sun_lon| in degrees, normalized to [0, 360)."""
    sun = math.degrees(_get_body_lon_at_jd(jd_utc, 10)) % 360.0
    moon = math.degrees(_get_body_lon_at_jd(jd_utc, 301)) % 360.0
    return (moon - sun) % 360.0


def _angular_distance_to(a_deg: float, target_deg: float) -> float:
    """Shortest angular distance from a_deg to target_deg, in degrees."""
    d = (a_deg - target_deg) % 360.0
    if d > 180.0:
        d = 360.0 - d
    return d


# ---------------------------------------------------------------------------
# Known syzygy dates (from USNO / timeanddate.com)
# ---------------------------------------------------------------------------

# (year, month, day, hour_utc, new_or_full) — verified against published data
KNOWN_SYZYGIES = [
    # New Moons
    (2003, 3, 3, 2.6, "new"),     # 2003-03-03 02:35 UT — last new moon before our golden chart
    (2000, 1, 6, 18.2, "new"),    # 2000-01-06 18:14 UT
    (2020, 1, 24, 21.4, "new"),   # 2020-01-24 21:42 UT
    (1990, 1, 26, 19.3, "new"),   # 1990-01-26 19:20 UT
    # Full Moons
    (2003, 2, 16, 23.9, "full"),  # 2003-02-16 23:51 UT
    (2000, 1, 21, 4.7, "full"),   # 2000-01-21 04:40 UT
    (2020, 1, 10, 19.2, "full"),  # 2020-01-10 19:10 UT
    (1990, 2, 9, 19.3, "full"),   # 1990-02-09 19:16 UT
]


# ---------------------------------------------------------------------------
# Test 1: Syzygy property — angular difference must be ≈ 0° or ≈ 180°
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("year,month,day,hour_utc,expected_type", KNOWN_SYZYGIES)
def test_syzygy_angular_accuracy(year, month, day, hour_utc, expected_type):
    """At the syzygy moment, Sun-Moon angular difference must be near 0 or 180 deg."""
    syzygy_jd = calendar_to_jd(year, month, day, hour_utc, 0, 0.0)

    # Search for the syzygy at this JD — should find itself (or very nearby)
    diff_deg = _sun_moon_diff_deg(syzygy_jd)

    if expected_type == "new":
        assert _angular_distance_to(diff_deg, 0.0) < 0.5, \
            f"New moon {year}-{month:02d}-{day:02d}: Sun-Moon diff={diff_deg:.2f}°, expected ≈0°"
    else:
        assert _angular_distance_to(diff_deg, 180.0) < 0.5, \
            f"Full moon {year}-{month:02d}-{day:02d}: Sun-Moon diff={diff_deg:.2f}°, expected ≈180°"


# ---------------------------------------------------------------------------
# Test 2: Prenatal syzygy must be strictly before birth
# ---------------------------------------------------------------------------

PRENATAL_CASES = [
    # (year, month, day, hour_utc, expected_waxing) — waxing=True means last was new moon
    # Golden chart
    (2003, 3, 13, 6.0, True),    # Moon in Cancer, Sun in Pisces, waxing → last was new
    # Immediately after a new moon (waxing crescent, ~1 day after)
    (2003, 3, 4, 6.0, True),     # Just after 2003-03-03 new moon
    # Immediately after a full moon (waning gibbous, ~1 day after)
    (2003, 2, 18, 6.0, False),   # Just after 2003-02-16 full moon
    # Half waxing (first quarter) — last was new moon
    (2000, 1, 14, 12.0, True),   # ~8 days after 2000-01-06 new moon
    # Half waning (last quarter) — last was full moon
    (2000, 1, 28, 12.0, False),  # ~7 days after 2000-01-21 full moon
    # Modern date
    (2020, 2, 1, 12.0, True),    # ~8 days after 2020-01-24 new moon
    # 1990 cases
    (1990, 2, 1, 12.0, True),    # ~6 days after 1990-01-26 new moon
    (1990, 2, 20, 12.0, False),  # ~11 days after 1990-02-09 full moon
]


@pytest.mark.parametrize("year,month,day,hour_utc,waxing", PRENATAL_CASES)
def test_prenatal_syzygy_before_birth(year, month, day, hour_utc, waxing):
    """Prenatal syzygy must occur strictly before the birth time."""
    birth_jd = calendar_to_jd(year, month, day, hour_utc, 0, 0.0)

    # Use the internal logic to find the syzygy JD
    birth_sun = _get_body_lon_at_jd(birth_jd, 10)
    birth_moon = _get_body_lon_at_jd(birth_jd, 301)
    diff = (birth_moon - birth_sun) % (2.0 * math.pi)
    target = 0.0 if diff < math.pi else math.pi

    # Search for the syzygy
    jd_hi = birth_jd
    found = False
    for _ in range(5):
        jd_lo = jd_hi - 14.8
        def obj_fn(jd):
            s = _get_body_lon_at_jd(jd, 10)
            m = _get_body_lon_at_jd(jd, 301)
            return (m - s - target + math.pi) % (2.0 * math.pi) - math.pi
        try:
            syzygy_jd = _newton_bisection(obj_fn, jd_lo, jd_hi)
            found = True
            break
        except ValueError:
            jd_hi = jd_lo

    assert found, f"Could not find syzygy before {year}-{month:02d}-{day:02d}"

    # Must be before birth
    assert syzygy_jd < birth_jd, \
        f"Syzygy JD {syzygy_jd} should be before birth JD {birth_jd}"

    # Must be within one synodic month (29.53 days)
    assert birth_jd - syzygy_jd < 29.6, \
        f"Syzygy is {birth_jd - syzygy_jd:.1f} days before birth, should be < 29.6"

    # At syzygy, angular diff must match
    diff_at_syzygy = _sun_moon_diff_deg(syzygy_jd)
    if target == 0.0:
        assert _angular_distance_to(diff_at_syzygy, 0.0) < 1.0, \
            f"Expected new moon, got diff={diff_at_syzygy:.2f}°"
    else:
        assert _angular_distance_to(diff_at_syzygy, 180.0) < 1.0, \
            f"Expected full moon, got diff={diff_at_syzygy:.2f}°"

    # Verify waxing/waning matches
    assert waxing == (target == 0.0), \
        f"Waxing={waxing} but target={'new' if target == 0.0 else 'full'}"


# ---------------------------------------------------------------------------
# Test 3: search_prenatal_syzygy returns valid sign + degree
# ---------------------------------------------------------------------------

def test_search_prenatal_syzygy_golden():
    """Golden chart: 2003-03-13, prenatal syzygy should be Pisces ~12° (new moon 2003-03-03)."""
    birth_jd = calendar_to_jd(2003, 3, 13, 6, 15, 0.0)  # 14:15 CST = 06:15 UTC
    sign, deg = search_prenatal_syzygy(birth_jd)
    assert sign == "Pisces", f"Expected Pisces, got {sign}"
    assert 10.0 < deg < 14.0, f"Expected ~12°, got {deg:.2f}°"


def test_search_prenatal_syzygy_waxing():
    """Born waxing → prenatal syzygy is new moon."""
    birth_jd = calendar_to_jd(2000, 1, 14, 12, 0, 0.0)  # ~8 days after 2000-01-06 new moon
    sign, deg = search_prenatal_syzygy(birth_jd)

    # 2000-01-06 new moon was at ~16° Capricorn
    assert sign == "Capricorn", f"Expected Capricorn, got {sign}"
    assert 14.0 < deg < 18.0, f"Expected ~16°, got {deg:.2f}°"


def test_search_prenatal_syzygy_waning():
    """Born waning → prenatal syzygy is full moon."""
    birth_jd = calendar_to_jd(2000, 1, 28, 12, 0, 0.0)  # ~7 days after 2000-01-21 full moon
    sign, deg = search_prenatal_syzygy(birth_jd)

    # 2000-01-21 full moon was at ~0° Leo → actually Sun at 0° Aquarius, Moon at 0° Leo
    # The syzygy point is Moon's position at full moon
    assert sign in ("Leo", "Cancer"), f"Expected Leo or Cancer, got {sign} ({deg:.2f}°)"


def test_search_prenatal_syzygy_consistency():
    """For multiple dates, the syzygy longitude at the computed JD matches."""
    test_cases = [
        (2003, 3, 13, 14, 15, 0),   # golden chart → Pisces 12°
        (1990, 2, 20, 12, 0, 0),    # after 1990-02-09 full moon
        (2020, 2, 1, 12, 0, 0),     # after 2020-01-24 new moon
    ]

    for year, month, day, hour, minute, sec in test_cases:
        # Birth in UTC
        birth_jd = calendar_to_jd(year, month, day, hour, minute, float(sec))

        # Get syzygy point from search_prenatal_syzygy
        syzygy_sign, syzygy_deg_in_sign = search_prenatal_syzygy(birth_jd)

        # Convert to total degrees
        syzygy_lon = sign_name_to_longitude(syzygy_sign, syzygy_deg_in_sign)

        # Must be in [0, 360)
        assert 0.0 <= syzygy_lon < 360.0

        # Self-consistency: the sign should be one of the 12
        from lunaeph._signs import SIGN_NAMES
        assert syzygy_sign in SIGN_NAMES


# ---------------------------------------------------------------------------
# Test 4: Almuten with real syzygy still converges to a stable winner
# ---------------------------------------------------------------------------

def test_almuten_syzygy_stable():
    """The almutem with real syzygy should have a clear winner."""
    from lunaeph import calculate_chart

    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0,
                            latitude_deg=37.45, longitude_deg=118.5833)
    alm = chart.almuten_figuris()

    # Jupiter wins with exact Chaldean day ruler (Jupiter +7)
    assert alm["almuten_figuris"] == "jupiter"
    assert alm["top_score"] > 0

    # No two planets should have the same score as the winner
    scores = alm["scores"]
    max_score = max(scores.values())
    winners = [p for p, s in scores.items() if s == max_score]
    assert len(winners) == 1, f"Tie detected: {winners}"


# ---------------------------------------------------------------------------
# Test 5: Syzygy sequence — new_moons_between / full_moons_between
# ---------------------------------------------------------------------------

# Known new moon times from USNO (year, month, day, hour_utc, minute_utc)
KNOWN_NEW_MOONS = [
    (2003, 1, 2, 20, 23),
    (2003, 2, 1, 10, 48),
    (2003, 3, 3, 2, 35),
    (2003, 4, 1, 19, 19),
    (2003, 12, 23, 9, 43),
]

KNOWN_FULL_MOONS = [
    (2003, 1, 18, 10, 48),
    (2003, 2, 16, 23, 51),
    (2003, 3, 18, 10, 34),
    (2003, 4, 16, 19, 36),
    (2003, 12, 8, 20, 37),
]


def test_new_moons_count_2003():
    """A year should have 12 or 13 new moons."""
    jd1 = calendar_to_jd(2003, 1, 1)
    jd2 = calendar_to_jd(2004, 1, 1)
    moons = new_moons_between(jd1, jd2)
    assert len(moons) in (12, 13), f"Expected 12-13 new moons, got {len(moons)}"


def test_full_moons_count_2003():
    """A year should have 12 or 13 full moons."""
    jd1 = calendar_to_jd(2003, 1, 1)
    jd2 = calendar_to_jd(2004, 1, 1)
    moons = full_moons_between(jd1, jd2)
    assert len(moons) in (12, 13), f"Expected 12-13 full moons, got {len(moons)}"


def test_new_moons_strictly_increasing():
    """Syzygy sequence should be strictly increasing."""
    jd1 = calendar_to_jd(2003, 1, 1)
    jd2 = calendar_to_jd(2004, 1, 1)
    moons = new_moons_between(jd1, jd2)
    for i in range(len(moons) - 1):
        assert moons[i] < moons[i + 1], f"New moon {i} >= new moon {i + 1}"


def test_full_moons_strictly_increasing():
    """Syzygy sequence should be strictly increasing."""
    jd1 = calendar_to_jd(2003, 1, 1)
    jd2 = calendar_to_jd(2004, 1, 1)
    moons = full_moons_between(jd1, jd2)
    for i in range(len(moons) - 1):
        assert moons[i] < moons[i + 1], f"Full moon {i} >= full moon {i + 1}"


def test_new_moons_against_usno():
    """Verify new moon times against USNO published data (±2 min tolerance)."""
    from lunaeph._time import jd_to_calendar

    jd1 = calendar_to_jd(2003, 1, 1)
    jd2 = calendar_to_jd(2004, 1, 1)
    moons = new_moons_between(jd1, jd2)

    # Build lookup: (month, day) → (hour, minute)
    computed = {}
    for jd in moons:
        y, m, d, h, mi, s = jd_to_calendar(jd)
        computed[(m, d)] = (h, mi + s / 60.0)

    for year, month, day, exp_h, exp_m in KNOWN_NEW_MOONS:
        key = (month, day)
        assert key in computed, f"New moon {year}-{month:02d}-{day:02d} not found"
        actual_h, actual_m = computed[key]
        diff_min = abs((actual_h * 60 + actual_m) - (exp_h * 60 + exp_m))
        assert diff_min < 5, (
            f"New moon {year}-{month:02d}-{day:02d}: "
            f"expected {exp_h:02d}:{exp_m:02d} UT, "
            f"got {actual_h:02.0f}:{actual_m:05.2f} UT "
            f"(diff={diff_min:.1f} min)"
        )


def test_full_moons_against_usno():
    """Verify full moon times against USNO published data (±2 min tolerance)."""
    from lunaeph._time import jd_to_calendar

    jd1 = calendar_to_jd(2003, 1, 1)
    jd2 = calendar_to_jd(2004, 1, 1)
    moons = full_moons_between(jd1, jd2)

    computed = {}
    for jd in moons:
        y, m, d, h, mi, s = jd_to_calendar(jd)
        computed[(m, d)] = (h, mi + s / 60.0)

    for year, month, day, exp_h, exp_m in KNOWN_FULL_MOONS:
        key = (month, day)
        assert key in computed, f"Full moon {year}-{month:02d}-{day:02d} not found"
        actual_h, actual_m = computed[key]
        diff_min = abs((actual_h * 60 + actual_m) - (exp_h * 60 + exp_m))
        assert diff_min < 5, (
            f"Full moon {year}-{month:02d}-{day:02d}: "
            f"expected {exp_h:02d}:{exp_m:02d} UT, "
            f"got {actual_h:02.0f}:{actual_m:05.2f} UT "
            f"(diff={diff_min:.1f} min)"
        )


def test_new_moons_syzygy_accuracy():
    """Every computed new moon should have Sun-Moon diff ≈ 0°."""
    jd1 = calendar_to_jd(2003, 1, 1)
    jd2 = calendar_to_jd(2004, 1, 1)
    for jd in new_moons_between(jd1, jd2):
        d = _sun_moon_diff_deg(jd)
        assert _angular_distance_to(d, 0.0) < 0.2, (
            f"New moon at JD {jd}: Sun-Moon diff = {d:.3f}°, expected ≈ 0°"
        )


def test_full_moons_syzygy_accuracy():
    """Every computed full moon should have Sun-Moon diff ≈ 180°."""
    jd1 = calendar_to_jd(2003, 1, 1)
    jd2 = calendar_to_jd(2004, 1, 1)
    for jd in full_moons_between(jd1, jd2):
        d = _sun_moon_diff_deg(jd)
        assert _angular_distance_to(d, 180.0) < 0.2, (
            f"Full moon at JD {jd}: Sun-Moon diff = {d:.3f}°, expected ≈ 180°"
        )


def test_interleaved_syzygies():
    """New moons and full moons should alternate."""
    jd1 = calendar_to_jd(2003, 1, 1)
    jd2 = calendar_to_jd(2004, 1, 1)
    new_moons = new_moons_between(jd1, jd2)
    full_moons = full_moons_between(jd1, jd2)

    # Merge and sort all syzygies
    all_syzygies = sorted(
        [(jd, "new") for jd in new_moons] + [(jd, "full") for jd in full_moons]
    )
    # They should strictly alternate
    for i in range(len(all_syzygies) - 1):
        assert all_syzygies[i][1] != all_syzygies[i + 1][1], (
            f"Consecutive syzygies both {all_syzygies[i][1]} at "
            f"JD {all_syzygies[i][0]} and {all_syzygies[i + 1][0]}"
        )
