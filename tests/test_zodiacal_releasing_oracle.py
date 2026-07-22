import pytest
from lunaeph import calculate_chart, calc_zr_l1_periods, get_current_zr

def test_zr_sign_durations():
    periods = calc_zr_l1_periods("Aries", max_years=250.0)
    
    expected_durations = {
        "Aries": 15.0, "Taurus": 8.0, "Gemini": 20.0, "Cancer": 25.0,
        "Leo": 19.0, "Virgo": 20.0, "Libra": 8.0, "Scorpio": 15.0,
        "Sagittarius": 12.0, "Capricorn": 27.0, "Aquarius": 30.0, "Pisces": 12.0
    }
    
    for p in periods[:12]:
        assert p["duration_years"] == expected_durations[p["sign"]]

def test_zr_loosing_of_the_bond():
    # Capricorn L1 has duration of 27 years > 17.58 years.
    # On L2, after 12 signs (from Cap through Sag), it must trigger LB and jump to Cancer (opposite of Cap)!
    from lunaeph._zodiacal_releasing import calc_zr_l2_subperiods
    l2 = calc_zr_l2_subperiods("Capricorn", l1_start_age=0.0, l1_duration=27.0)
    
    # 13th subperiod should be LB and jump to Cancer (opposite of Capricorn)
    assert len(l2) > 12
    assert l2[12]["is_loosing_of_the_bond"] == True
    assert l2[12]["sign"] == "Cancer"

def test_zr_oracle_chart():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    zr_spirit = chart.zodiacal_releasing(lot="spirit", age=21.0)
    assert zr_spirit["l1"]["sign"] == "Taurus"
    assert zr_spirit["l1"]["start_age"] == 15.0
    assert zr_spirit["l1"]["end_age"] == 23.0
    
    assert zr_spirit["l2"]["sign"] == "Virgo"
