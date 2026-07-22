import pytest
from lunaeph import calculate_chart

def test_jaimini_and_huber_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    # 1. Jaimini Chara Karakas
    j7 = chart.jaimini_chara_karakas(scheme="7_karaka")
    assert j7["karakas"]["AK"]["planet_key"] == "saturn"
    assert j7["karakas"]["AmK"]["planet_key"] == "sun"
    
    # 2. Huber Age Point
    hap = chart.huber_age_point(21.0)
    assert hap["active_house"] == 4
    assert hap["sign"] == "Scorpio"
