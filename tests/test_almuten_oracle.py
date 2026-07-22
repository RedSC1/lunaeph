import pytest
from lunaeph import calculate_chart, calculate_almuten_figuris

def test_almuten_figuris_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    alm = chart.almuten_figuris()
    
    # Check victor planet
    assert alm["almuten_figuris"] == "jupiter"
    assert alm["top_score"] == 38

    # Check day/hour rulers
    assert alm["day_ruler"] == "jupiter"
    assert alm["hour_ruler"] == "mars"

    # Check scores ranking
    scores = alm["scores"]
    assert scores["jupiter"] > scores["venus"]
    assert scores["venus"] > scores["moon"]
