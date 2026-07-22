"""Nakshatra (27/28 星宿) comprehensive module.

Supports:
- 27-Nakshatra standard system (standard Jyotish)
- 28-Nakshatra system with Abhijit (Muhurta / electional astrology)
- Full attribute table: Lord, Deity, Symbol, Gana, Tattva, Yoni, Pada
- Nakshatra-based Ashta Kuta compatibility scoring
"""

from __future__ import annotations
import math
from typing import Dict, Any, List, Tuple
from ._signs import SIGN_NAMES

# ─────────────────────────────────────────────────────────────────
# 27 Nakshatras Master Table
# (name, lord, deity, symbol, gana, tattva, yoni_animal, yoni_gender)
# ─────────────────────────────────────────────────────────────────
NAKSHATRA_27 = [
    ("Ashwini",           "ketu",    "Ashwini Kumaras", "Horse Head",       "Deva",     "Earth",  "Horse",    "M"),
    ("Bharani",           "venus",   "Yama",            "Yoni/Triangle",    "Manushya", "Earth",  "Elephant", "M"),
    ("Krittika",          "sun",     "Agni",            "Razor/Flame",      "Rakshasa", "Earth",  "Sheep",    "F"),
    ("Rohini",            "moon",    "Brahma",          "Cart/Chariot",     "Manushya", "Earth",  "Serpent",  "M"),
    ("Mrigashira",        "mars",    "Soma",            "Deer Head",        "Deva",     "Earth",  "Serpent",  "F"),
    ("Ardra",             "rahu",    "Rudra",           "Teardrop/Diamond", "Manushya", "Water",  "Dog",      "F"),
    ("Punarvasu",         "jupiter", "Aditi",           "Bow & Quiver",     "Deva",     "Water",  "Cat",      "F"),
    ("Pushya",            "saturn",  "Brihaspati",      "Lotus/Arrow",      "Deva",     "Water",  "Sheep",    "M"),
    ("Ashlesha",          "mercury", "Nagas",           "Coiled Serpent",   "Rakshasa", "Water",  "Cat",      "M"),
    ("Magha",             "ketu",    "Pitris",          "Royal Throne",     "Rakshasa", "Water",  "Rat",      "M"),
    ("Purva Phalguni",    "venus",   "Bhaga",           "Hammock/Couch",    "Manushya", "Water",  "Rat",      "F"),
    ("Uttara Phalguni",   "sun",     "Aryaman",         "Bed/Hammock",      "Manushya", "Fire",   "Cow",      "M"),
    ("Hasta",             "moon",    "Savitr",          "Open Hand/Fist",   "Deva",     "Fire",   "Buffalo",  "F"),
    ("Chitra",            "mars",    "Tvastar",         "Pearl/Jewel",      "Rakshasa", "Fire",   "Tiger",    "F"),
    ("Swati",             "rahu",    "Vayu",            "Young Sprout",     "Deva",     "Fire",   "Buffalo",  "M"),
    ("Vishakha",          "jupiter", "Indra-Agni",      "Triumphal Arch",   "Rakshasa", "Fire",   "Tiger",    "M"),
    ("Anuradha",          "saturn",  "Mitra",           "Lotus/Archway",    "Deva",     "Fire",   "Deer",     "F"),
    ("Jyeshtha",          "mercury", "Indra",           "Earring/Umbrella", "Rakshasa", "Air",    "Deer",     "M"),
    ("Mula",              "ketu",    "Nirriti",         "Bunch of Roots",   "Rakshasa", "Air",    "Dog",      "M"),
    ("Purva Ashadha",     "venus",   "Apah",            "Elephant Tusk",    "Manushya", "Air",    "Monkey",   "M"),
    ("Uttara Ashadha",    "sun",     "Vishwadevas",     "Elephant Tusk",    "Manushya", "Air",    "Mongoose", "M"),
    ("Shravana",          "moon",    "Vishnu",          "Three Footprints", "Deva",     "Air",    "Monkey",   "F"),
    ("Dhanishta",         "mars",    "Vasus",           "Drum/Flute",       "Rakshasa", "Ether",  "Lion",     "F"),
    ("Shatabhisha",       "rahu",    "Varuna",          "Empty Circle",     "Rakshasa", "Ether",  "Horse",    "F"),
    ("Purva Bhadrapada",  "jupiter", "Aja Ekapada",     "Two-faced Man",    "Manushya", "Ether",  "Lion",     "M"),
    ("Uttara Bhadrapada", "saturn",  "Ahir Budhnya",    "Twins/Bed",        "Manushya", "Ether",  "Cow",      "F"),
    ("Revati",            "mercury", "Pushan",          "Fish/Drum",        "Deva",     "Ether",  "Elephant", "F"),
]

# Pada goals (each Nakshatra has 4 Padas of 3°20')
PADA_GOALS = ["Dharma", "Artha", "Kama", "Moksha"]

# Navamsha sign start for each Nakshatra's Pada 1
# Fire signs start from Aries, Earth from Cap, Air from Libra, Water from Cancer
_NAV_STARTS = [0,9,6,3] * 7  # Repeats for 27 (actually cycles by rashi element)

# Abhijit (28th Nakshatra) - intercalary between Uttara Ashadha and Shravana
# Spans 06°40' to 10°53'20" Sidereal Capricorn (276°40' to 280°53'20")
ABHIJIT = {
    "name": "Abhijit",
    "lord": "sun",   # Some texts: Brahma; modern: associated with Sun
    "deity": "Brahma",
    "symbol": "Lotus/Triangle",
    "gana": "Deva",
    "start_deg": 276.0 + 40.0/60.0,   # 276°40'
    "end_deg": 280.0 + 53.333/60.0,    # 280°53'20"
    "note": "Intercalary 28th Nakshatra, used in Muhurta & Sarvatobhadra Chakra"
}

# Extract just the names for modules that need a simple list
NAKSHATRA_NAMES = [row[0] for row in NAKSHATRA_27]

# ─────────────────────────────────────────────────────────────────
# Pada → Navamsha Sign Mapping
# 108 Padas cycle through 12 signs starting from Aries:
# Pada global index = (nakshatra_index * 4) + (pada - 1)
# Navamsha sign index = pada_global_index % 12
# ─────────────────────────────────────────────────────────────────

# SIGN_NAMES imported from _signs (line 12) — canonical source for sign name list

# ─────────────────────────────────────────────────────────────────
# Pushkara Navamsha: Specific Navamsha ranges per sign element
# Fire signs (Aries/Leo/Sag): 20°00'-23°20' and 26°40'-30°00'
# Earth signs (Tau/Vir/Cap):  06°40'-10°00' and 13°20'-16°40'
# Air signs (Gem/Lib/Aqu):    16°40'-20°00' and 23°20'-26°40'
# Water signs (Can/Sco/Pis):  00°00'-03°20' and 06°40'-10°00'
# ─────────────────────────────────────────────────────────────────

_PUSHKARA_NAV_RANGES = {
    "Fire":  [(20.0, 23.333333), (26.666667, 30.0)],
    "Earth": [(6.666667, 10.0), (13.333333, 16.666667)],
    "Air":   [(16.666667, 20.0), (23.333333, 26.666667)],
    "Water": [(0.0, 3.333333), (6.666667, 10.0)],
}

_SIGN_ELEMENTS = {
    "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
    "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
    "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
    "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
}

# Pushkara Bhaga: Exact degrees per sign (Jataka Parijata)
_PUSHKARA_BHAGA = {
    "Aries": 21, "Leo": 19, "Sagittarius": 23,
    "Taurus": 14, "Virgo": 9, "Capricorn": 14,
    "Gemini": 18, "Libra": 24, "Aquarius": 19,
    "Cancer": 8, "Scorpio": 11, "Pisces": 9,
}

# ─────────────────────────────────────────────────────────────────
# Gandanta Zones (karmic knots at Water→Fire sign junctions)
# Cancer(29°46'40")-Leo(0°), Scorpio(29°46'40")-Sag(0°), Pisces(29°46'40")-Aries(0°)
# Traditionally: last 3°20' of water sign + first 3°20' of fire sign
# = last Pada of Ashlesha/Jyeshtha/Revati + first Pada of Magha/Mula/Ashwini
# ─────────────────────────────────────────────────────────────────

_GANDANTA_ZONES = [
    (120.0 - 3.333333, 120.0 + 3.333333),  # Cancer/Leo junction (116°40' - 123°20')
    (240.0 - 3.333333, 240.0 + 3.333333),  # Scorpio/Sag junction (236°40' - 243°20')
    (360.0 - 3.333333, 360.0 + 3.333333),  # Pisces/Aries junction (356°40' - 363°20')
]


def get_nakshatra_info(sidereal_lon_deg: float, system: str = "27") -> Dict[str, Any]:
    """
    Get comprehensive Nakshatra information for a sidereal longitude.

    Includes: Pada→Navamsha sign mapping, Pushkara Navamsha/Bhaga detection,
    Gandanta zone detection, Vargottama check, and optional Abhijit (28th).

    :param sidereal_lon_deg: Sidereal ecliptic longitude in degrees (0-360)
    :param system: '27' (standard) or '28' (includes Abhijit check)
    """
    deg = sidereal_lon_deg % 360.0
    nak_span = 360.0 / 27.0  # 13.3333°

    nak_idx = int(deg / nak_span)
    if nak_idx >= 27:
        nak_idx = 26

    nak_deg = deg - (nak_idx * nak_span)  # degree within nakshatra
    pada = int(nak_deg / (nak_span / 4.0)) + 1
    if pada > 4:
        pada = 4

    name, lord, deity, symbol, gana, tattva, yoni_animal, yoni_gender = NAKSHATRA_27[nak_idx]

    # ── Pada → Navamsha Sign ──
    pada_global_idx = (nak_idx * 4) + (pada - 1)
    navamsha_sign_idx = pada_global_idx % 12
    navamsha_sign = SIGN_NAMES[navamsha_sign_idx]

    # ── Rashi (sidereal sign) ──
    rashi_sign_idx = int(deg // 30.0) % 12
    rashi_sign = SIGN_NAMES[rashi_sign_idx]
    deg_in_sign = deg % 30.0

    # ── Vargottama: same sign in D1 and D9 ──
    vargottama = (rashi_sign_idx == navamsha_sign_idx)

    # ── Pushkara Navamsha check ──
    element = _SIGN_ELEMENTS.get(rashi_sign, "Fire")
    pushkara_nav = False
    for lo, hi in _PUSHKARA_NAV_RANGES.get(element, []):
        if lo <= deg_in_sign < hi:
            pushkara_nav = True
            break

    # ── Pushkara Bhaga check (exact degree ±0.5°) ──
    pb_deg = _PUSHKARA_BHAGA.get(rashi_sign, -999)
    pushkara_bhaga = abs(deg_in_sign - pb_deg) < 0.5

    # ── Gandanta check ──
    gandanta = False
    for lo, hi in _GANDANTA_ZONES:
        check_deg = deg if deg >= lo else deg + 360.0
        if lo <= check_deg < hi:
            gandanta = True
            break

    result = {
        "index": nak_idx,
        "name": name,
        "lord": lord,
        "deity": deity,
        "symbol": symbol,
        "gana": gana,
        "tattva": tattva,
        "yoni_animal": yoni_animal,
        "yoni_gender": yoni_gender,
        "pada": pada,
        "pada_goal": PADA_GOALS[pada - 1],
        "degree_in_nakshatra": round(nak_deg, 4),
        "progress_pct": round((nak_deg / nak_span) * 100.0, 2),
        # New Pada sub-system fields
        "navamsha_sign": navamsha_sign,
        "rashi_sign": rashi_sign,
        "vargottama": vargottama,
        "pushkara_navamsha": pushkara_nav,
        "pushkara_bhaga": pushkara_bhaga,
        "gandanta": gandanta,
    }

    # 28-nakshatra check: is this degree within Abhijit?
    if system == "28":
        if ABHIJIT["start_deg"] <= deg < ABHIJIT["end_deg"]:
            result["abhijit"] = True
            result["abhijit_info"] = ABHIJIT
        else:
            result["abhijit"] = False

    return result


def calc_nakshatra_chart(chart_data: Dict[str, Any], ayanamsha_mode: str = "lahiri",
                         system: str = "27") -> Dict[str, Any]:
    """
    Calculate Nakshatra positions for all planets in the chart.

    :param chart_data: Chart dictionary
    :param ayanamsha_mode: Sidereal ayanamsha mode
    :param system: '27' or '28' (with Abhijit)
    :return: Dict mapping planet keys to their Nakshatra info
    """
    from ._ayanamsha import calc_ayanamsha_deg

    jd_tt = chart_data["jd_tt"]
    ayan = calc_ayanamsha_deg(jd_tt, ayanamsha_mode)
    planets = chart_data["planets"]

    results = {}
    for pk, pv in planets.items():
        sid_deg = (math.degrees(pv["longitude_rad"]) - ayan) % 360.0
        info = get_nakshatra_info(sid_deg, system=system)
        info["planet"] = pv["name"]
        info["sidereal_longitude_deg"] = round(sid_deg, 4)
        results[pk] = info

    return results


# ─────────────────────────────────────────────────────────────────
# Ashta Kuta (八元素合婚) Compatibility Scoring
# ─────────────────────────────────────────────────────────────────

# Gana compatibility matrix (Deva=0, Manushya=1, Rakshasa=2)
_GANA_SCORE = {
    (0,0): 6, (0,1): 6, (0,2): 1,
    (1,0): 5, (1,1): 6, (1,2): 0,
    (2,0): 1, (2,1): 0, (2,2): 6,
}
_GANA_MAP = {"Deva": 0, "Manushya": 1, "Rakshasa": 2}

def calc_nakshatra_compatibility(nak_idx_a: int, nak_idx_b: int) -> Dict[str, Any]:
    """
    Calculate Nakshatra-based compatibility (Ashta Kuta 合婚八元素评分).

    Scores: Dina (3), Gana (6), Yoni (4), Rashi (7), Rashyadhipati (5),
            Nadi (8), Vasya (2), Mahendra (1) = Max 36 points.
    Simplified: returns Gana Kuta + Yoni Kuta + Nadi Kuta core scores.
    """
    a = NAKSHATRA_27[nak_idx_a % 27]
    b = NAKSHATRA_27[nak_idx_b % 27]

    # 1. Gana Kuta (max 6)
    ga = _GANA_MAP[a[4]]
    gb = _GANA_MAP[b[4]]
    gana_score = _GANA_SCORE[(ga, gb)]

    # 2. Yoni Kuta (max 4)
    # Same animal = 4, same animal diff gender = 3, friendly = 2, neutral = 1, enemy = 0
    if a[6] == b[6]:
        if a[7] != b[7]:
            yoni_score = 4  # Perfect match
        else:
            yoni_score = 3  # Same gender same animal
    else:
        yoni_score = 2  # Different animals

    # 3. Nadi Kuta (max 8)
    # Nadi: Vata (0), Pitta (1), Kapha (2) repeating cycle
    nadi_a = nak_idx_a % 3
    nadi_b = nak_idx_b % 3
    if nadi_a != nadi_b:
        nadi_score = 8
    else:
        nadi_score = 0  # Nadi Dosha!

    # 4. Dina Kuta (max 3)
    dina_diff = ((nak_idx_b - nak_idx_a) % 27) + 1
    dina_remainder = dina_diff % 9
    if dina_remainder in (2, 4, 6, 8, 0):
        dina_score = 3
    else:
        dina_score = 0

    total = gana_score + yoni_score + nadi_score + dina_score
    max_total = 6 + 4 + 8 + 3  # 21

    return {
        "gana_kuta": {"score": gana_score, "max": 6},
        "yoni_kuta": {"score": yoni_score, "max": 4},
        "nadi_kuta": {"score": nadi_score, "max": 8, "nadi_dosha": nadi_score == 0},
        "dina_kuta": {"score": dina_score, "max": 3},
        "total_score": total,
        "max_score": max_total,
        "compatibility_pct": round(total / max_total * 100.0, 1),
    }
