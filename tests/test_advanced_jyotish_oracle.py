import pytest
from lunaeph import calculate_chart

def test_ashtakavarga_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    av = chart.ashtakavarga()
    assert av["total_bindus"] == 337
    assert len(av["sarvashtakavarga"]) == 12
    assert len(av["bhinnashtakavarga"]) == 7
    # Sagittarius should be the strongest house (37 bindus)
    assert av["sarvashtakavarga"][8] == 37  # idx 8 = Sagittarius

def test_arudha_padas_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    ap = chart.arudha_padas()
    assert ap["A1"]["arudha_sign"] == "Taurus"
    assert "arudha_lagna" in ap
    assert "upapada" in ap
    assert ap["arudha_lagna"]["arudha_sign"] == ap["A1"]["arudha_sign"]

def test_yogini_dasha_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    yd = chart.yogini_dasha(age_years=21.0)
    assert yd["cycle_years"] == 36
    assert yd["start_yogini"] == "Pingala"
    chain = yd["active_at_age"]["dasha_chain"]
    assert len(chain) >= 1
    assert chain[0]["yogini"] == "Siddha"
    assert chain[0]["planet"] == "venus"
