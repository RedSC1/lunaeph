import pytest
from lunaeph import calculate_chart

def test_nakshatra_chart_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    nc = chart.nakshatra_chart()
    
    # Moon in Punarvasu, Lord = Jupiter
    assert nc["moon"]["name"] == "Punarvasu"
    assert nc["moon"]["lord"] == "jupiter"
    assert nc["moon"]["gana"] == "Deva"
    assert nc["moon"]["pada"] == 1
    
    # Sun in Purva Bhadrapada, Lord = Jupiter
    assert nc["sun"]["name"] == "Purva Bhadrapada"
    assert nc["sun"]["lord"] == "jupiter"
    
    # Mars in Mula, Lord = Ketu
    assert nc["mars"]["name"] == "Mula"
    assert nc["mars"]["lord"] == "ketu"

def test_nakshatra_28_system():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    nc28 = chart.nakshatra_chart(system="28")
    assert "abhijit" in nc28["moon"]

def test_nakshatra_compatibility():
    chart_a = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    chart_b = calculate_chart(1998, 8, 18, 9, 30, 0.0, tz=8.0, latitude_deg=31.23, longitude_deg=121.47)
    compat = chart_a.nakshatra_compatibility(chart_b)
    assert compat["person_a_nakshatra"] == "Punarvasu"
    assert compat["person_b_nakshatra"] == "Ardra"
    assert compat["total_score"] >= 15  # Should be reasonably compatible
    assert compat["compatibility_pct"] > 70.0
