import pytest
from lunaeph import calculate_chart

def test_light_aspects_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    # 1. Moiety of Orbs
    assert chart.moiety_of_orbs("sun", "moon") == 13.5
    assert chart.moiety_of_orbs("mars", "venus") == 7.5
    
    # 2. Translation of Light
    trans = chart.translation_of_light()
    assert len(trans) > 0
    assert any(t["translator"] == "Moon" for t in trans)
