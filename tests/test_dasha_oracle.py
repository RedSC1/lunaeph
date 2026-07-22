import pytest
from lunaeph import calculate_chart

def test_vimshottari_dasha_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    vd = chart.vimshottari_dasha(21.0, ayanamsha_mode="lahiri", max_level=5)
    
    assert vd["nakshatra"]["nakshatra_name"] == "Punarvasu"
    assert vd["nakshatra"]["dasha_lord"] == "jupiter"
    
    # 5-level recursive breakdown verification
    assert vd["mahadasha"]["mahadasha_lord"] == "saturn"
    assert vd["antardasha"]["lord"] == "ketu"
    assert vd["pratyantardasha"]["lord"] == "moon"
    assert vd["sookshma_dasha"]["lord"] == "jupiter"
    assert vd["prana_dasha"]["lord"] == "ketu"
