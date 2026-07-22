"""Karaka (指标星/象征星) — Three Significator Systems module.

Supports:
1. Naisargika Karaka (自然指标星) — Universal, fixed for all charts
2. Sthira Karaka (固定指标星) — Fixed planet→family role mapping
3. Chara Karaka (动态指标星) — Already in _jaimini_huber.py, re-exported here
"""

from __future__ import annotations
from typing import Dict, Any, List

# ─────────────────────────────────────────────────────────────────
# 1. Naisargika Karaka (自然指标星) — Universal
# Each planet naturally signifies certain life themes & house matters
# ─────────────────────────────────────────────────────────────────

NAISARGIKA_KARAKA = {
    "sun": {
        "signifies": ["Soul (Atma)", "Father", "Authority", "Vitality", "Government", "Ego"],
        "house_karaka": [1, 9, 10],  # Natural karaka for 1st, 9th, 10th houses
        "description": "灵魂/自我/父亲/权威/生命力",
    },
    "moon": {
        "signifies": ["Mind (Manas)", "Mother", "Emotions", "Public", "Water", "Fertility"],
        "house_karaka": [4],
        "description": "心智/母亲/情感/公众/滋养",
    },
    "mars": {
        "signifies": ["Courage", "Younger Siblings", "Land", "Warfare", "Energy", "Surgery"],
        "house_karaka": [3, 6],
        "description": "勇气/弟妹/土地/战斗/精力",
    },
    "mercury": {
        "signifies": ["Intelligence", "Communication", "Commerce", "Maternal Uncle", "Skill"],
        "house_karaka": [6, 10],
        "description": "智力/沟通/商业/舅舅/技能",
    },
    "jupiter": {
        "signifies": ["Wisdom", "Children", "Teacher (Guru)", "Wealth", "Husband (Female chart)", "Dharma"],
        "house_karaka": [2, 5, 9, 11],
        "description": "智慧/子女/导师/财富/丈夫(女盘)/法",
    },
    "venus": {
        "signifies": ["Love", "Spouse (Male chart)", "Luxury", "Art", "Vehicle", "Beauty"],
        "house_karaka": [7, 12],
        "description": "爱情/配偶(男盘)/奢华/艺术/美",
    },
    "saturn": {
        "signifies": ["Discipline", "Longevity", "Grief", "Servants", "Old Age", "Karma", "Labor"],
        "house_karaka": [8, 12],
        "description": "纪律/寿命/悲伤/劳工/老年/业力",
    },
    "rahu": {
        "signifies": ["Foreign", "Obsession", "Illusion", "Taboo", "Technology", "Outcaste"],
        "house_karaka": [],
        "description": "异国/执念/幻象/禁忌/科技",
    },
    "ketu": {
        "signifies": ["Spirituality", "Detachment", "Moksha", "Past Lives", "Isolation"],
        "house_karaka": [],
        "description": "灵性/超脱/解脱/前世/孤独",
    },
}

# ─────────────────────────────────────────────────────────────────
# 2. Sthira Karaka (固定指标星) — Fixed family/longevity roles
# Used for assessing longevity & health of specific relatives
# ─────────────────────────────────────────────────────────────────

STHIRA_KARAKA = {
    "sun":     {"role": "Father (父亲)",            "life_area": "Father's health & longevity"},
    "moon":    {"role": "Mother (母亲)",            "life_area": "Mother's health & longevity"},
    "mars":    {"role": "Younger Siblings (弟妹)",   "life_area": "Siblings' vitality & courage"},
    "mercury": {"role": "Maternal Uncle (舅舅)",     "life_area": "Maternal relatives' welfare"},
    "jupiter": {"role": "Children / Husband (子女/夫)", "life_area": "Children's fortune & spouse (female)"},
    "venus":   {"role": "Spouse / Wife (配偶/妻)",   "life_area": "Marriage partner's well-being"},
    "saturn":  {"role": "Longevity (寿命)",          "life_area": "Overall life span & karmic debts"},
}


def calc_all_karakas(chart_data: Dict[str, Any], ayanamsha_mode: str = "lahiri",
                     chara_scheme: str = "7_karaka") -> Dict[str, Any]:
    """
    Calculate all three Karaka (指标星) systems in one call.

    Returns:
    - 'naisargika': Universal natural significators for each planet
    - 'sthira': Fixed family/longevity significator roles
    - 'chara': Dynamic Jaimini Chara Karakas (AK/AmK/BK/MK/PiK/PK/GK/DK)
    """
    from ._jaimini_huber import calc_jaimini_chara_karakas

    planets = chart_data["planets"]

    # 1. Naisargika Karaka
    naisargika = {}
    for pk in ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]:
        if pk in NAISARGIKA_KARAKA:
            nk = dict(NAISARGIKA_KARAKA[pk])
            # Check if this planet exists in chart
            if pk in planets:
                nk["planet_name"] = planets[pk]["name"]
                nk["sign"] = planets[pk]["sign"]
            elif pk == "rahu" and "north_node" in planets:
                nk["planet_name"] = planets["north_node"]["name"]
                nk["sign"] = planets["north_node"]["sign"]
            elif pk == "ketu" and "south_node" in planets:
                nk["planet_name"] = planets["south_node"]["name"]
                nk["sign"] = planets["south_node"]["sign"]
            naisargika[pk] = nk

    # 2. Sthira Karaka
    sthira = {}
    for pk, sk_info in STHIRA_KARAKA.items():
        entry = dict(sk_info)
        if pk in planets:
            entry["planet_name"] = planets[pk]["name"]
            entry["sign"] = planets[pk]["sign"]
        sthira[pk] = entry

    # 3. Chara Karaka (delegate to existing Jaimini engine)
    chara = calc_jaimini_chara_karakas(chart_data, scheme=chara_scheme,
                                        ayanamsha_mode=ayanamsha_mode)

    return {
        "naisargika": naisargika,
        "sthira": sthira,
        "chara": chara,
    }
