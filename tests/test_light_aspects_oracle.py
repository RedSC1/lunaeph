import pytest
from lunaeph import calculate_chart

def test_light_aspects_oracle():
    chart = calculate_chart(2003, 3, 13, 14, 15, 0.0, tz=8.0, latitude_deg=37.45, longitude_deg=118.5833)
    
    # 1. Moiety of Orbs
    assert chart.moiety_of_orbs("sun", "moon") == 13.5
    assert chart.moiety_of_orbs("mars", "venus") == 7.5
    
    # 2. Besiegement
    besieged = chart.besiegement()
    assert len(besieged) >= 4
    sun_b = [b for b in besieged if b["target_planet"] == "Sun"]
    assert len(sun_b) >= 2
    
    # 3. Translation of Light
    trans = chart.translation_of_light()
    assert len(trans) >= 2
    assert any("☿ 向 ☉" in t["description"] for t in trans)
    assert any("♂ 向 ☉" in t["description"] for t in trans)
    
    # 4. Collection of Light
    coll = chart.collection_of_light()
    assert len(coll) >= 1
    assert coll[0]["collector"] == "Sun"
    
    # 5. Prohibition of Light
    proh = chart.prohibition()
    assert len(proh) >= 1
    assert proh[0]["intervener"] == "Saturn"
