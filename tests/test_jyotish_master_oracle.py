import pytest
from lunaeph import calculate_chart

def test_jyotish_master_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    # 1. Upagrahas
    up = chart.upagrahas()
    assert up["dhuma"]["sign"] == "Cancer"
    assert up["vyatipata"]["sign"] == "Sagittarius"
    
    # 2. KP System Sub-lord
    kp = chart.kp_sublord("moon")
    assert kp["nakshatra"] == "Punarvasu"
    assert kp["star_lord"] == "jupiter"
    assert kp["sub_lord"] == "jupiter"
    
    # 3. Panchadha Maitri
    maitri = chart.panchadha_maitri()
    assert "sun" in maitri
    assert "saturn" in maitri["sun"]
