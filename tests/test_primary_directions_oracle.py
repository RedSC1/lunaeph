import pytest
from lunaeph import calculate_chart

def test_primary_directions_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    pdirs = chart.primary_directions(key="naibod")
    
    assert len(pdirs) > 0
    # First event should be Jupiter -> Ascendant
    assert pdirs[0]["promittor"] == "Jupiter"
    assert pdirs[0]["significator"] == "Ascendant"
    assert abs(pdirs[0]["age_years"] - 3.25) < 0.2
