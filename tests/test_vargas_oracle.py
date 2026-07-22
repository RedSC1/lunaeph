import pytest
from lunaeph import calculate_chart

def test_vargas_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    divs = chart.divisional_charts(ayanamsha_mode="lahiri")
    
    assert divs["d1_rashi"]["sun"]["sign"] == "Aquarius"
    assert divs["d9_navamsha"]["sun"]["sign"] == "Gemini"
    assert divs["d10_dasamsa"]["sun"]["sign"] == "Scorpio"
    
    assert divs["d1_rashi"]["jupiter"]["sign"] == "Cancer"
    assert divs["d10_dasamsa"]["jupiter"]["sign"] == "Cancer"
