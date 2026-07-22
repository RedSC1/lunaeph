"""Classical astrology dignities and conditions."""

from __future__ import annotations
import math

# Traditional planet keys
TRADITIONAL_PLANETS = {"sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"}

# Domicile & Detriment (Sign -> Ruler)
# Rulers
DOMICILE_RULERS = {
    "Aries": "mars", "Taurus": "venus", "Gemini": "mercury", "Cancer": "moon",
    "Leo": "sun", "Virgo": "mercury", "Libra": "venus", "Scorpio": "mars",
    "Sagittarius": "jupiter", "Capricorn": "saturn", "Aquarius": "saturn", "Pisces": "jupiter"
}

# Detriments are exactly opposite to Domiciles
DETRIMENT_RULERS = {
    "Aries": "venus", "Taurus": "mars", "Gemini": "jupiter", "Cancer": "saturn",
    "Leo": "saturn", "Virgo": "jupiter", "Libra": "mars", "Scorpio": "venus",
    "Sagittarius": "mercury", "Capricorn": "moon", "Aquarius": "sun", "Pisces": "mercury"
}

# Exaltation & Fall
EXALTATIONS = {
    "sun": "Aries", "moon": "Taurus", "mercury": "Virgo", "venus": "Pisces",
    "mars": "Capricorn", "jupiter": "Cancer", "saturn": "Libra"
}

FALLS = {
    "sun": "Libra", "moon": "Scorpio", "mercury": "Pisces", "venus": "Virgo",
    "mars": "Cancer", "jupiter": "Capricorn", "saturn": "Aries"
}

EXALTATION_DEGREES = {
    "sun": 19, "moon": 3, "mercury": 15, "venus": 27,
    "mars": 28, "jupiter": 15, "saturn": 21
}

# Dorothean Triplicities (Fire, Earth, Air, Water)
# Format: {Sign: {"day": ruler, "night": ruler, "participating": ruler}}
TRIPLICITIES = {
    "Aries": {"day": "sun", "night": "jupiter", "participating": "saturn"},
    "Leo": {"day": "sun", "night": "jupiter", "participating": "saturn"},
    "Sagittarius": {"day": "sun", "night": "jupiter", "participating": "saturn"},
    
    "Taurus": {"day": "venus", "night": "moon", "participating": "mars"},
    "Virgo": {"day": "venus", "night": "moon", "participating": "mars"},
    "Capricorn": {"day": "venus", "night": "moon", "participating": "mars"},
    
    "Gemini": {"day": "saturn", "night": "mercury", "participating": "jupiter"},
    "Libra": {"day": "saturn", "night": "mercury", "participating": "jupiter"},
    "Aquarius": {"day": "saturn", "night": "mercury", "participating": "jupiter"},
    
    "Cancer": {"day": "venus", "night": "mars", "participating": "moon"},
    "Scorpio": {"day": "venus", "night": "mars", "participating": "moon"},
    "Pisces": {"day": "venus", "night": "mars", "participating": "moon"},
}

# Ptolemaic Terms/Bounds (Sign -> [(planet, degree_limit), ...])
# The limit is exclusive upper bound, e.g. (jupiter, 6) means 0 to 5.999...
TERMS_PTOLEMAIC = {
    "Aries": [("jupiter", 6), ("venus", 14), ("mercury", 21), ("mars", 26), ("saturn", 30)],
    "Taurus": [("venus", 8), ("mercury", 15), ("jupiter", 22), ("saturn", 26), ("mars", 30)],
    "Gemini": [("mercury", 7), ("jupiter", 14), ("venus", 21), ("saturn", 25), ("mars", 30)],
    "Cancer": [("mars", 6), ("jupiter", 13), ("mercury", 20), ("venus", 27), ("saturn", 30)],
    "Leo": [("saturn", 6), ("mercury", 13), ("venus", 19), ("jupiter", 25), ("mars", 30)],
    "Virgo": [("mercury", 7), ("venus", 13), ("jupiter", 18), ("saturn", 24), ("mars", 30)],
    "Libra": [("saturn", 6), ("venus", 11), ("jupiter", 19), ("mercury", 24), ("mars", 30)],
    "Scorpio": [("mars", 6), ("jupiter", 14), ("venus", 21), ("mercury", 27), ("saturn", 30)],
    "Sagittarius": [("jupiter", 8), ("venus", 14), ("mercury", 19), ("saturn", 25), ("mars", 30)],
    "Capricorn": [("venus", 6), ("mercury", 12), ("jupiter", 19), ("mars", 25), ("saturn", 30)],
    "Aquarius": [("saturn", 6), ("mercury", 12), ("venus", 20), ("jupiter", 25), ("mars", 30)],
    "Pisces": [("venus", 8), ("jupiter", 14), ("mercury", 20), ("mars", 26), ("saturn", 30)],
}

# Egyptian Terms
TERMS_EGYPTIAN = {
    "Aries": [("jupiter", 6), ("venus", 12), ("mercury", 20), ("mars", 25), ("saturn", 30)],
    "Taurus": [("venus", 8), ("mercury", 14), ("jupiter", 22), ("saturn", 27), ("mars", 30)],
    "Gemini": [("mercury", 6), ("venus", 12), ("jupiter", 19), ("mars", 24), ("saturn", 30)],
    "Cancer": [("mars", 7), ("venus", 13), ("mercury", 19), ("jupiter", 26), ("saturn", 30)],
    "Leo": [("jupiter", 6), ("venus", 11), ("saturn", 18), ("mercury", 24), ("mars", 30)],
    "Virgo": [("mercury", 7), ("venus", 17), ("jupiter", 21), ("mars", 28), ("saturn", 30)],
    "Libra": [("saturn", 6), ("mercury", 14), ("jupiter", 21), ("venus", 28), ("mars", 30)],
    "Scorpio": [("mars", 7), ("venus", 11), ("mercury", 19), ("jupiter", 24), ("saturn", 30)],
    "Sagittarius": [("jupiter", 12), ("venus", 17), ("mercury", 21), ("saturn", 26), ("mars", 30)],
    "Capricorn": [("mercury", 7), ("jupiter", 14), ("venus", 22), ("saturn", 26), ("mars", 30)],
    "Aquarius": [("mercury", 7), ("venus", 13), ("jupiter", 20), ("mars", 25), ("saturn", 30)],
    "Pisces": [("venus", 12), ("jupiter", 16), ("mercury", 19), ("mars", 28), ("saturn", 30)],
}

# Chaldean Faces/Decans (Sign -> [(planet, degree_limit), ...])
FACES = {
    "Aries": [("mars", 10), ("sun", 20), ("venus", 30)],
    "Taurus": [("mercury", 10), ("moon", 20), ("saturn", 30)],
    "Gemini": [("jupiter", 10), ("mars", 20), ("sun", 30)],
    "Cancer": [("venus", 10), ("mercury", 20), ("moon", 30)],
    "Leo": [("saturn", 10), ("jupiter", 20), ("mars", 30)],
    "Virgo": [("sun", 10), ("venus", 20), ("mercury", 30)],
    "Libra": [("moon", 10), ("saturn", 20), ("jupiter", 30)],
    "Scorpio": [("mars", 10), ("sun", 20), ("venus", 30)],
    "Sagittarius": [("mercury", 10), ("moon", 20), ("saturn", 30)],
    "Capricorn": [("jupiter", 10), ("mars", 20), ("sun", 30)],
    "Aquarius": [("venus", 10), ("mercury", 20), ("moon", 30)],
    "Pisces": [("saturn", 10), ("jupiter", 20), ("mars", 30)],
}

def get_rulers(sign: str, degree_in_sign: float, is_day_chart: bool, use_egyptian_terms: bool = True) -> dict:
    """Get the rulers for a specific sign and degree."""
    rulers = {}
    
    if sign in DOMICILE_RULERS:
        rulers["domicile"] = DOMICILE_RULERS[sign]
        
    for p, s in EXALTATIONS.items():
        if s == sign:
            rulers["exaltation"] = p
            break
            
    triplicity_rulers = TRIPLICITIES.get(sign, {})
    if triplicity_rulers:
        rulers["triplicity_day"] = triplicity_rulers.get("day")
        rulers["triplicity_night"] = triplicity_rulers.get("night")
        rulers["triplicity_participating"] = triplicity_rulers.get("participating")
        
    terms = TERMS_EGYPTIAN.get(sign, []) if use_egyptian_terms else TERMS_PTOLEMAIC.get(sign, [])
    for term_ruler, limit in terms:
        if degree_in_sign < limit:
            rulers["term"] = term_ruler
            break
            
    for face_ruler, limit in FACES.get(sign, []):
        if degree_in_sign < limit:
            rulers["face"] = face_ruler
            break
            
    return rulers

def get_essential_dignities(planet: str, sign: str, degree_in_sign: float, is_day_chart: bool, use_egyptian_terms: bool = True) -> dict:
    """Calculate the essential dignities for a traditional planet."""
    if planet not in TRADITIONAL_PLANETS:
        return {}
        
    dignities = {}
    score = 0
    
    # Systems metadata
    systems = {
        "triplicity": "dorothean",
        "terms": "egyptian" if use_egyptian_terms else "ptolemaic",
        "faces": "chaldean",
        "scoring": "william_lilly"
    }
    
    # Domicile & Detriment
    if DOMICILE_RULERS.get(sign) == planet:
        dignities["domicile"] = True
        score += 5
    if DETRIMENT_RULERS.get(sign) == planet:
        dignities["detriment"] = True
        score -= 5
        
    # Exaltation & Fall
    if EXALTATIONS.get(planet) == sign:
        dignities["exaltation"] = True
        score += 4
    if FALLS.get(planet) == sign:
        dignities["fall"] = True
        score -= 4
        
    # Triplicity
    triplicity_rulers = TRIPLICITIES.get(sign, {})
    sect_ruler = triplicity_rulers.get("day" if is_day_chart else "night")
    if sect_ruler == planet or triplicity_rulers.get("participating") == planet:
        dignities["triplicity"] = True
        score += 3
        
    # Term/Bound
    terms = TERMS_EGYPTIAN.get(sign, []) if use_egyptian_terms else TERMS_PTOLEMAIC.get(sign, [])
    for term_ruler, limit in terms:
        if degree_in_sign < limit:
            if term_ruler == planet:
                dignities["term"] = True
                score += 2
            break
            
    # Face/Decan
    for face_ruler, limit in FACES.get(sign, []):
        if degree_in_sign < limit:
            if face_ruler == planet:
                dignities["face"] = True
                score += 1
            break
            
            
    if not dignities:
        dignities["peregrine"] = True  # Wanderer, no essential dignity
        
    return {
        "systems": systems,
        "score": score,
        "details": dignities
    }

def get_accidental_dignities(planet: str, planet_lon_rad: float, sun_lon_rad: float, speed_deg: float, is_day_chart: bool) -> dict:
    """Calculate the accidental dignities/conditions of a planet."""
    if planet not in TRADITIONAL_PLANETS:
        return {}
        
    conditions = {}
    
    # Sect (宗派)
    # Day chart: Sun, Jupiter, Saturn are in sect.
    # Night chart: Moon, Venus, Mars are in sect.
    # Mercury is diurnal if oriental, nocturnal if occidental.
    if planet in ("sun", "jupiter", "saturn"):
        conditions["sect"] = "in_sect" if is_day_chart else "out_of_sect"
    elif planet in ("moon", "venus", "mars"):
        conditions["sect"] = "in_sect" if not is_day_chart else "out_of_sect"
    
    # Speed & Direction
    if speed_deg < 0:
        conditions["retrograde"] = True
    elif speed_deg < 0.05 and planet not in ("sun", "moon"): # Arbitrary threshold for stationary
        conditions["stationary"] = True
        
    if planet not in ("sun", "moon"):
        # Sun relationship: Combust / Cazimi / Under Sunbeams
        # Distance in longitude, normalized to 0-180
        dist_rad = (planet_lon_rad - sun_lon_rad) % (2.0 * math.pi)
        if dist_rad > math.pi:
            dist_rad = 2.0 * math.pi - dist_rad
            
        dist_deg = math.degrees(dist_rad)
        
        solar_cond = {
            "longitude_separation_deg": round(dist_deg, 4),
            "cazimi_limit_deg": 0.2833,
            "combust_limit_deg": 8.5,
            "under_beams_limit_deg": 17.0
        }
        
        if dist_deg <= 0.2833: # ~17 arc minutes
            solar_cond["condition"] = "cazimi"
        elif dist_deg <= 8.5:
            solar_cond["condition"] = "combust"
        elif dist_deg <= 17.0:
            solar_cond["condition"] = "under_beams"
        else:
            solar_cond["condition"] = "free_of_beams"
            
        conditions["solar_condition"] = solar_cond
            
        # Oriental / Occidental
        # A planet is oriental if it rises before the Sun.
        diff = (sun_lon_rad - planet_lon_rad) % (2.0 * math.pi)
        if diff < math.pi and diff > 0:
            conditions["phase"] = "oriental"
        elif diff > math.pi:
            conditions["phase"] = "occidental"
            
        # Mercury Sect correction
        if planet == "mercury":
            if (is_day_chart and conditions.get("phase") == "oriental") or (not is_day_chart and conditions.get("phase") == "occidental"):
                conditions["sect"] = "in_sect"
            else:
                conditions["sect"] = "out_of_sect"
            
    return conditions
