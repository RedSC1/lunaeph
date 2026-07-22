import pytest
from lunaeph import calculate_chart

def test_bhava_chalit_and_sade_sati():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    bhava = chart.bhava_chalit(ayanamsha_mode="lahiri")
    assert bhava["sun"]["shifted"] == True
    assert bhava["sun"]["bhava_house"] == 9
    
    # Sade Sati test: Natal Moon is in Gemini (Sidereal)
    ss_t = chart.sade_sati("Taurus")
    assert ss_t["is_active"] == True
    assert "Phase 1" in ss_t["phase"]
    
    ss_g = chart.sade_sati("Gemini")
    assert ss_g["is_active"] == True
    assert "Phase 2" in ss_g["phase"]
    
    ss_c = chart.sade_sati("Cancer")
    assert ss_c["is_active"] == True
    assert "Phase 3" in ss_c["phase"]
    
    ss_a = chart.sade_sati("Aries")
    assert ss_a["is_active"] == False
