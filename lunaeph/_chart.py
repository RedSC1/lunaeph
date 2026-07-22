"""Chart calculation — wires time, precession, houses, signs, aspects."""

from __future__ import annotations

import math
from typing import Callable

from ._time import (
    calendar_to_jd,
    jd_to_calendar,
    jd_ut1_to_tt,
    jd_tt_to_ut1,
    delta_t_seconds_from_jd_ut1,
    gast_rad,
)
from ._precession import (
    iau2000b_nutation_angles,
    equation_of_equinoxes_rad,
    j2000_ecliptic_to_date,
    mean_obliquity_rad,
)
from ._aberration import apply_light_corrections
from ._deflection import apply_solar_deflection
from ._houses import calc_houses, HouseSystem
from ._signs import sign_degree_minute
from ._aspects import find_all_aspects, _ANGLE_NAMES


# ---------------------------------------------------------------------------
# Planet list
# ---------------------------------------------------------------------------

# taiyin body IDs + our name
_PLANETS: list[tuple[int, str, str]] = [
    # (body_id, key, display_name)
    (10, "sun",     "Sun"),
    (301, "moon",   "Moon"),
    (1,  "mercury", "Mercury"),
    (2,  "venus",   "Venus"),
    (4,  "mars",    "Mars"),
    (5,  "jupiter", "Jupiter"),
    (6,  "saturn",  "Saturn"),
    (7,  "uranus",  "Uranus"),
    (8,  "neptune", "Neptune"),
    (9,  "pluto",   "Pluto"),
]

ASTRODIENST_TROPICAL_MONTH_DAYS = 27.32158218
TROPICAL_YEAR_DAYS = 365.2421897


def _km_to_au(km: float) -> float:
    return km / 149597870.7


def _to_xyz(v: tuple[float, ...]) -> tuple[float, float, float]:
    """Narrow a variable-length tuple to a 3-tuple for the type checker."""
    return (v[0], v[1], v[2])


# ---------------------------------------------------------------------------
# Mathematical / Geometrical Helpers
# ---------------------------------------------------------------------------

def _spherical_midpoint(lat1_deg: float, lon1_deg: float,
                        lat2_deg: float, lon2_deg: float) -> tuple[float, float]:
    """Spherical geographic midpoint between two coordinates."""
    phi1, lam1 = math.radians(lat1_deg), math.radians(lon1_deg)
    phi2, lam2 = math.radians(lat2_deg), math.radians(lon2_deg)

    x1 = math.cos(phi1) * math.cos(lam1)
    y1 = math.cos(phi1) * math.sin(lam1)
    z1 = math.sin(phi1)

    x2 = math.cos(phi2) * math.cos(lam2)
    y2 = math.cos(phi2) * math.sin(lam2)
    z2 = math.sin(phi2)

    xm, ym, zm = x1 + x2, y1 + y2, z1 + z2
    rm = math.sqrt(xm * xm + ym * ym + zm * zm)

    if rm < 1e-9:
        return (lat1_deg, lon1_deg)

    phi_m = math.asin(zm / rm)
    lam_m = math.atan2(ym, xm) % (2.0 * math.pi)

    lat_m_deg = math.degrees(phi_m)
    lon_m_deg = math.degrees(lam_m)
    if lon_m_deg > 180.0:
        lon_m_deg -= 360.0

    return (lat_m_deg, lon_m_deg)


def _circular_midpoint(a_rad: float, b_rad: float,
                       ref_asc_rad: float | None = None) -> float:
    """Circular midpoint of two ecliptic longitudes in radians.

    Explicitly resolves the 180-degree midpoint ambiguity by measuring
    towards *ref_asc_rad* (or defaulting to +90 degrees from A).
    """
    a = a_rad % (2.0 * math.pi)
    b = b_rad % (2.0 * math.pi)
    diff = (b - a) % (2.0 * math.pi)
    if diff > math.pi:
        diff -= 2.0 * math.pi

    if abs(abs(diff) - math.pi) < 1e-7:
        cand1 = (a + math.pi / 2.0) % (2.0 * math.pi)
        cand2 = (a - math.pi / 2.0) % (2.0 * math.pi)
        if ref_asc_rad is not None:
            d1 = abs((cand1 - ref_asc_rad + math.pi) % (2.0 * math.pi) - math.pi)
            d2 = abs((cand2 - ref_asc_rad + math.pi) % (2.0 * math.pi) - math.pi)
            return cand1 if d1 <= d2 else cand2
        return cand1
    return (a + diff / 2.0) % (2.0 * math.pi)


def _house_placement(lon_rad: float, cusps: list[dict]) -> int:
    """Determine which house (1-indexed, 1..12) *lon_rad* falls into."""
    c_lons = [c["longitude_rad"] for c in cusps]
    for i in range(12):
        c_curr = c_lons[i]
        c_next = c_lons[(i + 1) % 12]
        span = (c_next - c_curr) % (2.0 * math.pi)
        offset = (lon_rad - c_curr) % (2.0 * math.pi)
        if offset < span:
            return i + 1
    return 1


def _brentq(f: Callable[[float], float], a: float, b: float,
            xtol: float = 1e-9, maxiter: int = 100) -> float:
    """Pure-Python Brent's method for root finding."""
    fa = f(a)
    fb = f(b)
    if fa * fb > 0:
        raise ValueError(f"Root not bracketed: f(a)={fa}, f(b)={fb}")
    if abs(fa) < abs(fb):
        a, b = b, a
        fa, fb = fb, fa
    c = a
    fc = fa
    mflag = True
    d = 0.0
    for _ in range(maxiter):
        if abs(b - a) < xtol or abs(fb) < xtol:
            return b
        if fa != fc and fb != fc:
            s = (a * fb * fc / ((fa - fb) * (fa - fc)) +
                 b * fa * fc / ((fb - fa) * (fb - fc)) +
                 c * fa * fb / ((fc - fa) * (fc - fb)))
        else:
            s = b - fb * (b - a) / (fb - fa)

        cond1 = not ((3 * a + b) / 4 <= s <= b or b <= s <= (3 * a + b) / 4)
        cond2 = mflag and abs(s - b) >= abs(b - c) / 2.0
        cond3 = not mflag and abs(s - b) >= abs(c - d) / 2.0
        cond4 = mflag and abs(b - c) < xtol
        cond5 = not mflag and abs(c - d) < xtol

        if cond1 or cond2 or cond3 or cond4 or cond5:
            s = (a + b) / 2.0
            mflag = True
        else:
            mflag = False

        fs = f(s)
        d = c
        c = b
        fc = fb
        if fa * fs < 0:
            b = s
            fb = fs
        else:
            a = s
            fa = fs
        if abs(fa) < abs(fb):
            a, b = b, a
            fa, fb = fb, fa
    return b


def _newton_bisection(f: Callable[[float], float], a: float, b: float,
                      xtol: float = 1e-9, maxiter: int = 50) -> float:
    """Hybrid Newton-Bisection root finding (finite differences)."""
    fa = f(a)
    fb = f(b)
    if fa * fb > 0:
        raise ValueError(f"Root not bracketed: f(a)={fa}, f(b)={fb}")
    
    if fa > 0:
        a, b = b, a
        fa, fb = fb, fa

    x = 0.5 * (a + b)
    fx = f(x)
    
    for _ in range(maxiter):
        if abs(b - a) < xtol or abs(fx) < xtol:
            return x
            
        eps = 1e-5
        dfx = (f(x + eps) - fx) / eps
        
        if dfx > 0.0:
            next_x = x - fx / dfx
        else:
            next_x = a - 1.0
            
        if (a < next_x < b):
            x = next_x
        else:
            x = 0.5 * (a + b)
            
        fx = f(x)
        
        if fx < 0:
            a = x
        else:
            b = x

    return x


def _get_body_lon_at_jd(jd_utc: float, body_id: int) -> float:
    """Compute ecliptic longitude of body_id at jd_utc."""
    from taiyin_semi_analytic import position as _pos, velocity_icrf as _vel
    jd_tt = jd_ut1_to_tt(jd_utc)
    earth_pos_km = _to_xyz(_pos(jd_tt, 399))
    earth_vel_km_per_day = _to_xyz(_vel(jd_tt, 399))
    earth_pos_au = _to_xyz(tuple(_km_to_au(v) for v in earth_pos_km))
    earth_vel_au_per_day = _to_xyz(tuple(_km_to_au(v) for v in earth_vel_km_per_day))

    geo_au = apply_light_corrections(
        jd_tt,
        lambda jd: _to_xyz(tuple(_km_to_au(v) for v in _pos(jd, body_id))),
        earth_pos_au,
        earth_vel_au_per_day,
        light_time=True,
        aberration=True,
    )
    geo_au = apply_solar_deflection(
        earth_pos_au,
        _to_xyz((earth_pos_au[0] + geo_au[0],
                 earth_pos_au[1] + geo_au[1],
                 earth_pos_au[2] + geo_au[2])),
    )
    from ._precession import rotate_equator_to_ecliptic, _J2000_OBLIQUITY_RAD
    geo_ecl = rotate_equator_to_ecliptic(geo_au, _J2000_OBLIQUITY_RAD)
    ecl_date = j2000_ecliptic_to_date(geo_ecl, jd_tt)
    x, y, z = ecl_date
    return math.atan2(y, x) % (2.0 * math.pi)


def search_solar_longitude(target_lon_rad: float, start_jd: float, end_jd: float) -> float:
    """Find the exact JD when the Sun reaches target_lon_rad within [start_jd, end_jd]."""
    def obj_fn(jd: float) -> float:
        sun_lon = _get_body_lon_at_jd(jd, 10)
        return (sun_lon - target_lon_rad + math.pi) % (2.0 * math.pi) - math.pi
        
    return _newton_bisection(obj_fn, start_jd, end_jd)


def search_lunar_longitude(target_lon_rad: float, start_jd: float, end_jd: float) -> float:
    """Find the exact JD when the Moon reaches target_lon_rad within [start_jd, end_jd]."""
    def obj_fn(jd: float) -> float:
        moon_lon = _get_body_lon_at_jd(jd, 301)
        return (moon_lon - target_lon_rad + math.pi) % (2.0 * math.pi) - math.pi
        
    return _newton_bisection(obj_fn, start_jd, end_jd)



# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

class Chart(dict):
    """A calculated astrology chart.

    Dict-like (chart["planets"], chart["houses"], etc.) plus ``set_orb()``
    to tweak aspect orbs after the fact.  The built-in default orb table
    (in ``_aspects.DEFAULT_ORBS``) is never modified.
    """

    def __init__(self, data: dict, body_rates: dict[str, float]):
        super().__init__(data)
        self._body_lons = {k: p["longitude_rad"]
                           for k, p in data["planets"].items()}
        self._body_rates = body_rates
        from ._aspects import DEFAULT_ORBS
        self._orbs: dict[float, float] = dict(DEFAULT_ORBS)

    def set_orb(self, angle: float | str | int, orb_deg: float) -> "Chart":
        """Set aspect *orb_deg* (in degrees) for *angle* and recompute.

        Only recomputes that one angle — other aspects are untouched.
        Pass *orb_deg* = 0.0 to disable the aspect entirely.
        """
        angle = float(angle)
        self._orbs[angle] = float(orb_deg)

        # Delete old entries by aspect_angle_deg (works for custom angles too)
        self["aspects"] = [
            a for a in self["aspects"] if a["aspect_angle_deg"] != angle
        ]

        # Recompute if orb > 0
        if orb_deg > 0.0:
            from ._aspects import _compute_angle_aspects
            self["aspects"].extend(
                _compute_angle_aspects(self._body_lons, angle, orb_deg,
                                       self._body_rates))
        return self

    def reset_orb(self, angle: float | str | int) -> "Chart":
        """Restore the default orb for *angle*."""
        from ._aspects import DEFAULT_ORBS
        if float(angle) in DEFAULT_ORBS:
            self.set_orb(angle, DEFAULT_ORBS[float(angle)])
        return self

    def firdaria(self, age: float | None = None, *, nodes_after_mercury: bool = True):
        """Calculate Firdaria (法达星限法).

        If *age* (years) is given, returns current active Major & Minor Firdar.
        If *age* is None, returns full Firdaria timeline.
        *nodes_after_mercury*: If True (default/爱星盘流派), places Lunar Nodes after Mercury/sequence.
        """
        from ._firdaria import calc_firdaria_timeline, get_current_firdaria
        import math
        sun_lon = self["planets"]["sun"]["longitude_rad"]
        asc_lon = self["houses"]["ascendant"]["longitude_rad"]
        is_day_chart = ((sun_lon - asc_lon) % (2.0 * math.pi)) > math.pi

        if age is not None:
            return get_current_firdaria(is_day_chart, age, nodes_after_mercury)
        return calc_firdaria_timeline(is_day_chart, nodes_after_mercury)

    def profection(self, age: float, *, start_point: str = "ascendant") -> dict:
        """Calculate Annual, Monthly, and Daily Profections (小限推运).

        *age*: Age in years (e.g. 21.0).
        *start_point*: 'ascendant', 'sun', 'moon', or a custom point name.
        """
        from ._profections import calc_profection, get_sign_index
        asc_info = self["houses"]["ascendant"]
        asc_deg = (get_sign_index(asc_info["sign"]) * 30.0) + asc_info["degree"] + (asc_info["minute"] / 60.0)
        
        start_deg = asc_deg
        if start_point.lower() == "sun":
            sun_p = self["planets"]["sun"]
            start_deg = (get_sign_index(sun_p["sign"]) * 30.0) + sun_p["degree"] + (sun_p["minute"] / 60.0)
        elif start_point.lower() == "moon":
            moon_p = self["planets"]["moon"]
            start_deg = (get_sign_index(moon_p["sign"]) * 30.0) + moon_p["degree"] + (moon_p["minute"] / 60.0)
        elif start_point in self["planets"]:
            p = self["planets"][start_point]
            start_deg = (get_sign_index(p["sign"]) * 30.0) + p["degree"] + (p["minute"] / 60.0)
            
        return calc_profection(asc_deg, age, start_point_deg=start_deg)

    def ayanamsha(self, mode: str = "lahiri") -> float:
        """Calculate Sidereal Ayanamsha (度数) for this chart.

        *mode*: 'lahiri', 'true_chitra'/'true_lahiri', 'fagan_bradley', 'raman', 'krishnamurti', 'yukteswar'.
        """
        from ._ayanamsha import calc_ayanamsha_deg
        return calc_ayanamsha_deg(self["jd_tt"], mode)

    def sidereal_planets(self, mode: str = "lahiri") -> dict:
        """Get all planet positions converted to Sidereal Zodiac (恒星黄道)."""
        from ._ayanamsha import calc_ayanamsha_deg
        from ._signs import degrees_to_zodiac
        ayan = calc_ayanamsha_deg(self["jd_tt"], mode)
        
        result = {"ayanamsha_deg": round(ayan, 4), "mode": mode, "planets": {}}
        for k, p in self["planets"].items():
            trop_lon = math.degrees(p["longitude_rad"])
            sid_lon = (trop_lon - ayan) % 360.0
            sign, deg_in_sign = degrees_to_zodiac(sid_lon)
            result["planets"][k] = {
                "name": p["name"],
                "sidereal_longitude_deg": round(sid_lon, 4),
                "sign": sign,
                "degree_in_sign": round(deg_in_sign, 4)
            }
        return result

    def zodiacal_releasing(self, lot: str = "spirit", age: float | None = None) -> dict:
        """Calculate Zodiacal Releasing (希腊化黄道释放).

        *lot*: 'spirit' (精神点/事业), 'fortune' (福德点/健康), 'eros' (桃花/欲望).
        *age*: If given, returns active L1 and L2 periods for that age. If None, returns L1 timeline.
        """
        from ._zodiacal_releasing import calc_zr_l1_periods, get_current_zr
        lot_key = lot.lower()
        if lot_key not in self["lots"]:
            lot_key = "spirit"
            
        start_sign = self["lots"][lot_key]["sign"]
        
        if age is not None:
            return get_current_zr(start_sign, age)
        return {"lot": lot_key, "start_sign": start_sign, "l1_timeline": calc_zr_l1_periods(start_sign)}

    def almuten_figuris(self, school: str = "ibn_ezra") -> dict:
        """Calculate Almuten Figuris (生命主宰星 / 胜者星算法).

        *school*: 'ibn_ezra' (standard), 'bonatti' (strict sect triplicity), 'lilly' (cadent filter).
        """
        from ._almuten import calculate_almuten_figuris
        return calculate_almuten_figuris(self, school=school)

    def vimshottari_dasha(self, age: float | None = None, *, ayanamsha_mode: str = "lahiri", max_level: int = 5) -> dict:
        """Calculate Vimshottari Dasha (印度 120 年九曜大运 - 五级递归展开).

        *age*: If given, returns active Dasha hierarchy down to *max_level* (1 to 5).
        *max_level*: 1=Mahadasha, 2=Antardasha, 3=Pratyantardasha, 4=Sookshma, 5=Prana.
        *ayanamsha_mode*: 'lahiri', 'true_chitra'/'true_lahiri', 'fagan_bradley', 'raman', 'krishnamurti', 'yukteswar'.
        """
        from ._dasha import calc_vimshottari_timeline, get_current_dasha
        from ._ayanamsha import calc_ayanamsha_deg
        
        moon_trop_lon = math.degrees(self["planets"]["moon"]["longitude_rad"])
        ayan = calc_ayanamsha_deg(self["jd_tt"], ayanamsha_mode)
        sid_moon_lon = (moon_trop_lon - ayan) % 360.0
        
        if age is not None:
            return get_current_dasha(sid_moon_lon, age, max_level=max_level)
        return {
            "ayanamsha_mode": ayanamsha_mode,
            "sidereal_moon_lon_deg": round(sid_moon_lon, 4),
            "timeline": calc_vimshottari_timeline(sid_moon_lon)
        }

    def divisional_charts(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Indian Divisional Charts (十六大分盘 Shodasha Vargas & D9 Navamsha).

        Calculates D1 (Rashi), D3 (Drekkana), D9 (Navamsha), D10 (Dasamsa), D12 (Dwadasamsa), D60 (Shashtiamsa),
        and identifies Vargottama planets (同度共鸣).
        """
        from ._vargas import calculate_divisional_charts
        return calculate_divisional_charts(self, ayanamsha_mode=ayanamsha_mode)

    def primary_directions(self, key: str = "naibod", mode: str = "direct", system: str = "zodiacal") -> list:
        """Calculate Primary Directions (西方古典主限法 / 弓限轴向推运).

        *key*: 'naibod' (0°59'08"/yr), 'ptolemy' (1°/yr), 'true_sun' (Cardan true Sun motion).
        *mode*: 'direct' (顺向), 'converse' (逆向).
        *system*: 'zodiacal' (黄道弧), 'placidus' (普拉西德半弧).
        """
        from ._primary_directions import calc_primary_directions
        return calc_primary_directions(self, key=key, mode=mode, system=system)

    def bhava_chalit(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Bhava Chalit (印占宫位调整盘).

        Determines if planets shift houses based on exact Ascendant degree cusps.
        """
        from ._bhava_gochar import calc_bhava_chalit
        return calc_bhava_chalit(self, ayanamsha_mode=ayanamsha_mode)

    def sade_sati(self, transit_saturn_sidereal_sign: str, ayanamsha_mode: str = "lahiri") -> dict:
        """Check Indian Sade Sati (土星萨德萨蒂 - 7.5年大难/考验运).

        *transit_saturn_sidereal_sign*: Current transit Saturn sign in Sidereal Zodiac.
        """
        from ._bhava_gochar import calc_sade_sati
        from ._ayanamsha import calc_ayanamsha_deg
        from ._signs import degrees_to_zodiac
        
        moon_trop_lon = math.degrees(self["planets"]["moon"]["longitude_rad"])
        ayan = calc_ayanamsha_deg(self["jd_tt"], ayanamsha_mode)
        sid_moon_lon = (moon_trop_lon - ayan) % 360.0
        moon_sign, _ = degrees_to_zodiac(sid_moon_lon)
        
        return calc_sade_sati(moon_sign, transit_saturn_sidereal_sign)

    def upagrahas(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Indian Upagrahas (五大太阳虚星: Dhuma, Vyatipata, Parivesha, Indrachapa, Upaketu)."""
        from ._jyotish_master import calc_upagrahas
        from ._ayanamsha import calc_ayanamsha_deg
        sun_trop_lon = math.degrees(self["planets"]["sun"]["longitude_rad"])
        ayan = calc_ayanamsha_deg(self["jd_tt"], ayanamsha_mode)
        sid_sun_lon = (sun_trop_lon - ayan) % 360.0
        return calc_upagrahas(sid_sun_lon)

    def kp_sublord(self, planet: str = "moon", ayanamsha_mode: str = "kp") -> dict:
        """Calculate KP System Star-Lord and Sub-Lord (KP 派星主与副主星)."""
        from ._jyotish_master import calc_kp_sublord
        from ._ayanamsha import calc_ayanamsha_deg
        p_name = planet.lower()
        p_trop_lon = math.degrees(self["planets"][p_name]["longitude_rad"])
        ayan = calc_ayanamsha_deg(self["jd_tt"], ayanamsha_mode)
        sid_lon = (p_trop_lon - ayan) % 360.0
        return calc_kp_sublord(sid_lon)

    def panchadha_maitri(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Panchadha Maitri (五分法印占复合敌友关系)."""
        from ._jyotish_master import calc_panchadha_maitri
        return calc_panchadha_maitri(self, ayanamsha_mode=ayanamsha_mode)

    def jaimini_chara_karakas(self, scheme: str = "7_karaka", ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Jaimini Chara Karakas (贾伊米尼动态生命星系).

        *scheme*: '7_karaka' (7星制) or '8_karaka' (8星制含罗睺).
        """
        from ._jaimini_huber import calc_jaimini_chara_karakas
        return calc_jaimini_chara_karakas(self, scheme=scheme, ayanamsha_mode=ayanamsha_mode)

    def huber_age_point(self, age_years: float) -> dict:
        """Calculate Huber School Age Point (胡伯心理学派 6年/宫 年龄点推运)."""
        from ._jaimini_huber import calc_huber_age_point
        return calc_huber_age_point(self, age_years)

    def ashtakavarga(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Sarvashtakavarga (八分点/行运力量评估 337点系统)."""
        from ._ashtakavarga import calc_ashtakavarga
        return calc_ashtakavarga(self, ayanamsha_mode=ayanamsha_mode)

    def arudha_padas(self, ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Jaimini Arudha Padas (贾伊米尼虚象宫/映射宫位 A1-A12)."""
        from ._arudha_pada import calc_arudha_padas
        return calc_arudha_padas(self, ayanamsha_mode=ayanamsha_mode)

    def yogini_dasha(self, age_years: float = 0.0, ayanamsha_mode: str = "lahiri",
                     max_level: int = 2) -> dict:
        """Calculate Yogini Dasha (瑜伽女神大运 36年周期)."""
        from ._yogini_dasha import calc_yogini_dasha
        return calc_yogini_dasha(self, age_years=age_years, ayanamsha_mode=ayanamsha_mode, max_level=max_level)

    def nakshatra_chart(self, ayanamsha_mode: str = "lahiri", system: str = "27") -> dict:
        """Calculate Nakshatra positions for all planets (27/28 星宿系统).

        *system*: '27' (标准) or '28' (含 Abhijit 毕宿).
        """
        from ._nakshatra import calc_nakshatra_chart
        return calc_nakshatra_chart(self, ayanamsha_mode=ayanamsha_mode, system=system)

    def nakshatra_compatibility(self, other: "Chart", ayanamsha_mode: str = "lahiri") -> dict:
        """Calculate Nakshatra-based Ashta Kuta compatibility (合婚八元素评分)."""
        from ._nakshatra import calc_nakshatra_compatibility, get_nakshatra_info
        from ._ayanamsha import calc_ayanamsha_deg
        ayan_a = calc_ayanamsha_deg(self["jd_tt"], ayanamsha_mode)
        ayan_b = calc_ayanamsha_deg(other["jd_tt"], ayanamsha_mode)
        moon_a = (math.degrees(self["planets"]["moon"]["longitude_rad"]) - ayan_a) % 360.0
        moon_b = (math.degrees(other["planets"]["moon"]["longitude_rad"]) - ayan_b) % 360.0
        nak_a = get_nakshatra_info(moon_a)
        nak_b = get_nakshatra_info(moon_b)
        compat = calc_nakshatra_compatibility(nak_a["index"], nak_b["index"])
        compat["person_a_nakshatra"] = nak_a["name"]
        compat["person_b_nakshatra"] = nak_b["name"]
        return compat

    def karakas(self, ayanamsha_mode: str = "lahiri", chara_scheme: str = "7_karaka") -> dict:
        """Calculate all three Karaka (指标星) systems: Naisargika + Sthira + Chara."""
        from ._karaka import calc_all_karakas
        return calc_all_karakas(self, ayanamsha_mode=ayanamsha_mode, chara_scheme=chara_scheme)

    # -- convenience accessors --

    def planet(self, name: str) -> dict:
        """Return a planet dict e.g. chart.planet('sun')."""
        return self["planets"][name]

    @property
    def planets(self) -> list[str]:
        """List of planet keys."""
        return list(self["planets"].keys())

    def house_cusp(self, n: int) -> dict:
        """Return house *n* cusp (1-indexed) e.g. chart.house_cusp(1)."""
        return self["houses"]["cusps"][n - 1]

    @property
    def ascendant(self) -> dict:
        return self["houses"]["ascendant"]

    @property
    def midheaven(self) -> dict:
        return self["houses"]["midheaven"]

    @property
    def vertex(self) -> dict:
        return self["houses"]["vertex"]

    def aspects_to(self, body: str) -> list[dict]:
        """All aspects involving *body*."""
        return [a for a in self["aspects"]
                if a["body1"] == body or a["body2"] == body]

    def aspects_between(self, a: str, b: str) -> list[dict]:
        """Aspects between two specific bodies."""
        return [x for x in self["aspects"]
                if {x["body1"], x["body2"]} == {a, b}]

    # -- synastry / composite / davison --

    def synastry_with(self, other: "Chart") -> dict:
        """Synastry relationship analysis between two charts.

        Returns a dictionary containing:
        - ``cross_aspects``: list of aspects strictly between Chart A and Chart B
        - ``chart_a_in_chart_b_houses``: house placement of Chart A bodies in B
        - ``chart_b_in_chart_a_houses``: house placement of Chart B bodies in A
        """
        cross_aspects = []
        for b1_key, lon1 in self._body_lons.items():
            rate1 = self._body_rates.get(b1_key, 0.0)
            for b2_key, lon2 in other._body_lons.items():
                rate2 = other._body_rates.get(b2_key, 0.0)
                diff_deg = math.degrees((lon2 - lon1) % (2.0 * math.pi))
                if diff_deg > 180.0:
                    diff_deg = 360.0 - diff_deg
                for aspect_angle, orb in self._orbs.items():
                    if orb <= 0.0:
                        continue
                    orb_val = abs(diff_deg - aspect_angle)
                    if orb_val <= orb:
                        rel_rate = rate2 - rate1
                        ang_dist = (lon2 - lon1) % (2.0 * math.pi)
                        target_rad = math.radians(aspect_angle)
                        applying = (rel_rate * (ang_dist - target_rad)) < 0 if rel_rate != 0 else False
                        name = _ANGLE_NAMES.get(aspect_angle, f"{aspect_angle}°")
                        cross_aspects.append({
                            "chart_a_body": b1_key,
                            "chart_b_body": b2_key,
                            "aspect": name,
                            "aspect_angle_deg": aspect_angle,
                            "orb_deg": round(orb_val, 4),
                            "applying": applying,
                        })

        a_in_b = {k: _house_placement(lon, other["houses"]["cusps"])
                  for k, lon in self._body_lons.items()}
        b_in_a = {k: _house_placement(lon, self["houses"]["cusps"])
                  for k, lon in self._body_lons.items()}

        return {
            "chart_a_in_chart_b_houses": a_in_b,
            "chart_b_in_chart_a_houses": b_in_a,
            "cross_aspects": cross_aspects,
        }

    def composite_with(self, other: "Chart") -> "Chart":
        """Midpoint composite chart between two natal charts."""
        ref_asc = self["houses"]["ascendant"]["longitude_rad"]
        comp_body_lons = {}
        planets = {}
        for key in self._body_lons:
            if key in other._body_lons:
                lon_a = self._body_lons[key]
                lon_b = other._body_lons[key]
                m_lon = _circular_midpoint(lon_a, lon_b, ref_asc_rad=ref_asc)
                lat_a = self["planets"][key]["latitude_rad"]
                lat_b = other["planets"][key]["latitude_rad"]
                m_lat = (lat_a + lat_b) / 2.0
                dist_a = self["planets"][key]["distance_au"]
                dist_b = other["planets"][key]["distance_au"]
                m_dist = (dist_a + dist_b) / 2.0

                comp_body_lons[key] = m_lon
                sign_info, deg, min_ = sign_degree_minute(m_lon)
                planets[key] = {
                    "name": self["planets"][key]["name"],
                    "longitude_rad": m_lon,
                    "latitude_rad": m_lat,
                    "distance_au": m_dist,
                    "sign": sign_info.name,
                    "sign_abbrev": sign_info.abbrev,
                    "degree": deg,
                    "minute": min_,
                    "retrograde": False,
                }

        # Composite houses via ARMC midpoint
        armc_a = self["houses"]["armc_rad"]
        armc_b = other["houses"]["armc_rad"]
        comp_armc = _circular_midpoint(armc_a, armc_b, ref_asc_rad=ref_asc)

        lat_m_deg, lon_m_deg = _spherical_midpoint(
            self["observer"]["lat_deg"], self["observer"]["lon_deg"],
            other["observer"]["lat_deg"], other["observer"]["lon_deg"],
        )

        jd_mid = (self["jd_utc"] + other["jd_utc"]) / 2.0
        jd_tt_mid = jd_ut1_to_tt(jd_mid)
        obl = mean_obliquity_rad(jd_tt_mid)

        hs = HouseSystem(self["houses"]["system"])
        houses_data = calc_houses(comp_armc - math.radians(lon_m_deg),
                                  math.radians(lon_m_deg),
                                  math.radians(lat_m_deg),
                                  obl, hs)

        aspects = find_all_aspects(comp_body_lons)
        y, mo, d, h, mi, s = jd_to_calendar(jd_mid)

        data = {
            "jd_utc": jd_mid,
            "jd_tt": jd_tt_mid,
            "delta_t_s": delta_t_seconds_from_jd_ut1(jd_mid),
            "date_utc": f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{int(s):02d}Z",
            "observer": {
                "lat_deg": lat_m_deg,
                "lon_deg": lon_m_deg,
            },
            "planets": planets,
            "houses": {
                "system": houses_data["system"].value,
                "armc_rad": houses_data["armc_rad"],
                "ascendant": _format_angle(houses_data["ascendant_rad"]),
                "midheaven": _format_angle(houses_data["midheaven_rad"]),
                "vertex": _format_angle(houses_data["vertex_rad"]),
                "east_point": _format_angle(houses_data["east_point_rad"]),
                "cusps": [_format_angle(c) for c in houses_data["cusps_rad"]],
            },
            "aspects": aspects,
        }
        rates = {k: 0.0 for k in comp_body_lons}
        return Chart(data, rates)

    def davison_with(self, other: "Chart", *, mode: str = "spherical") -> "Chart":
        """Davison relationship chart (time and geographic midpoint).

        *mode* can be:
        - ``"spherical"``: 3D vector spherical geographic midpoint (default)
        - ``"arithmetic"``: simple arithmetic average of latitude and longitude
        """
        jd_mid = (self["jd_utc"] + other["jd_utc"]) / 2.0
        if mode == "arithmetic":
            lat_m_deg = (self["observer"]["lat_deg"] + other["observer"]["lat_deg"]) / 2.0
            lon_m_deg = (self["observer"]["lon_deg"] + other["observer"]["lon_deg"]) / 2.0
        else:
            lat_m_deg, lon_m_deg = _spherical_midpoint(
                self["observer"]["lat_deg"], self["observer"]["lon_deg"],
                other["observer"]["lat_deg"], other["observer"]["lon_deg"],
            )

        return calculate_chart(
            *self._jd_to_cal(jd_mid),
            tz=0.0,
            latitude_deg=lat_m_deg,
            longitude_deg=lon_m_deg,
        )

    # -- progressions / directions --

    def secondary_progression(self, age_years: float | None = None, *,
                              years: float | None = None,
                              target_jd: float | None = None,
                              latitude_deg: float | None = None,
                              longitude_deg: float | None = None) -> "Chart":
        """Secondary progression (1 ephemeris day per tropical year of life).

        Pass either *age_years* (or *years*), or *target_jd*.
        Note: Age 30 corresponds to 30 ephemeris days after birth.
        """
        val_years = age_years if age_years is not None else years
        if target_jd is not None:
            elapsed_years = (target_jd - self["jd_utc"]) / TROPICAL_YEAR_DAYS
            jd_prog = self["jd_utc"] + elapsed_years
        elif val_years is not None:
            jd_prog = self["jd_utc"] + val_years
        else:
            raise ValueError("Must specify either age_years/years or target_jd")

        lat = latitude_deg if latitude_deg is not None else self["observer"]["lat_deg"]
        lon = longitude_deg if longitude_deg is not None else self["observer"]["lon_deg"]
        return calculate_chart(
            *self._jd_to_cal(jd_prog),
            tz=0.0,
            latitude_deg=lat,
            longitude_deg=lon,
        )

    def progressed(self, years: float, rate: float = 1.0) -> "Chart":
        """Backwards-compatible alias for secondary progression."""
        return self.secondary_progression(age_years=years * rate)

    def tertiary_i(self, age_years: float | None = None, *,
                   years: float | None = None,
                   target_jd: float | None = None,
                   latitude_deg: float | None = None,
                   longitude_deg: float | None = None) -> "Chart":
        """Tertiary Progression I (1 ephemeris day per 27.32158218 days of life)."""
        val_years = age_years if age_years is not None else years
        if target_jd is not None:
            elapsed_life_days = target_jd - self["jd_utc"]
        elif val_years is not None:
            elapsed_life_days = val_years * TROPICAL_YEAR_DAYS
        else:
            raise ValueError("Must specify either age_years/years or target_jd")

        ephemeris_days_offset = elapsed_life_days / ASTRODIENST_TROPICAL_MONTH_DAYS
        jd_prog = self["jd_utc"] + ephemeris_days_offset
        lat = latitude_deg if latitude_deg is not None else self["observer"]["lat_deg"]
        lon = longitude_deg if longitude_deg is not None else self["observer"]["lon_deg"]
        return calculate_chart(
            *self._jd_to_cal(jd_prog),
            tz=0.0,
            latitude_deg=lat,
            longitude_deg=lon,
        )

    def tertiary_ii(self, age_years: float | None = None, *,
                    years: float | None = None,
                    target_jd: float | None = None,
                    latitude_deg: float | None = None,
                    longitude_deg: float | None = None) -> "Chart":
        """Tertiary Progression II (27.32158218 ephemeris days per tropical year of life).

        Astrodienst compatible constant: 27.32158218 ephemeris days = 1 year of life.
        """
        val_years = age_years if age_years is not None else years
        if target_jd is not None:
            elapsed_life_years = (target_jd - self["jd_utc"]) / TROPICAL_YEAR_DAYS
        elif val_years is not None:
            elapsed_life_years = val_years
        else:
            raise ValueError("Must specify either age_years/years or target_jd")

        ephemeris_days_offset = elapsed_life_years * ASTRODIENST_TROPICAL_MONTH_DAYS
        jd_prog = self["jd_utc"] + ephemeris_days_offset
        lat = latitude_deg if latitude_deg is not None else self["observer"]["lat_deg"]
        lon = longitude_deg if longitude_deg is not None else self["observer"]["lon_deg"]
        return calculate_chart(
            *self._jd_to_cal(jd_prog),
            tz=0.0,
            latitude_deg=lat,
            longitude_deg=lon,
        )

    def tertiary_progression(self, age_years: float | None = None, *,
                             years: float | None = None,
                             target_jd: float | None = None,
                             latitude_deg: float | None = None,
                             longitude_deg: float | None = None) -> "Chart":
        """Alias for tertiary_i."""
        return self.tertiary_i(age_years=age_years, years=years, target_jd=target_jd,
                               latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    def minor_progression(self, age_years: float | None = None, *,
                          years: float | None = None,
                          target_jd: float | None = None,
                          latitude_deg: float | None = None,
                          longitude_deg: float | None = None) -> "Chart":
        """Alias for tertiary_ii."""
        return self.tertiary_ii(age_years=age_years, years=years, target_jd=target_jd,
                                latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    def solar_arc(self, age_years: float | None = None, *,
                  years: float | None = None,
                  target_jd: float | None = None) -> "Chart":
        """True Solar Arc directed chart — advance all positions by Sun's secondary arc."""
        val_years = age_years if age_years is not None else years
        prog = self.secondary_progression(age_years=val_years, target_jd=target_jd)
        natal_sun_lon = self["planets"]["sun"]["longitude_rad"]
        prog_sun_lon = prog["planets"]["sun"]["longitude_rad"]
        arc = (prog_sun_lon - natal_sun_lon) % (2.0 * math.pi)

        # Shift all planets
        shifted_planets = {}
        shifted_body_lons = {}
        for k, p in self["planets"].items():
            new_lon = (p["longitude_rad"] + arc) % (2.0 * math.pi)
            shifted_body_lons[k] = new_lon
            sign_info, deg, min_ = sign_degree_minute(new_lon)
            shifted_planets[k] = {
                "name": p["name"],
                "longitude_rad": new_lon,
                "latitude_rad": p["latitude_rad"],
                "distance_au": p["distance_au"],
                "sign": sign_info.name,
                "sign_abbrev": sign_info.abbrev,
                "degree": deg,
                "minute": min_,
                "retrograde": p.get("retrograde", False),
            }

        # Shift houses & angles
        old_h = self["houses"]
        shifted_houses = {
            "system": old_h["system"],
            "armc_rad": (old_h["armc_rad"] + arc) % (2.0 * math.pi),
            "ascendant": _format_angle((old_h["ascendant"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "midheaven": _format_angle((old_h["midheaven"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "vertex": _format_angle((old_h["vertex"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "east_point": _format_angle((old_h["east_point"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "cusps": [_format_angle((c["longitude_rad"] + arc) % (2.0 * math.pi))
                      for c in old_h["cusps"]],
        }

        aspects = find_all_aspects(shifted_body_lons, body_rates=self._body_rates)

        data = dict(self)
        data["planets"] = shifted_planets
        data["houses"] = shifted_houses
        data["aspects"] = aspects
        return Chart(data, self._body_rates)

    def naibod_direction(self, age_years: float | None = None, *,
                         years: float | None = None,
                         target_jd: float | None = None) -> "Chart":
        """Naibod arc direction chart — advance all positions by mean solar motion (~0.98564733 deg/year)."""
        val_years = age_years if age_years is not None else years
        if target_jd is not None:
            val_years = (target_jd - self["jd_utc"]) / TROPICAL_YEAR_DAYS
        elif val_years is None:
            raise ValueError("Must specify either age_years/years or target_jd")

        arc = math.radians(val_years * 0.98564733)

        shifted_planets = {}
        shifted_body_lons = {}
        for k, p in self["planets"].items():
            new_lon = (p["longitude_rad"] + arc) % (2.0 * math.pi)
            shifted_body_lons[k] = new_lon
            sign_info, deg, min_ = sign_degree_minute(new_lon)
            shifted_planets[k] = {
                "name": p["name"],
                "longitude_rad": new_lon,
                "latitude_rad": p["latitude_rad"],
                "distance_au": p["distance_au"],
                "sign": sign_info.name,
                "sign_abbrev": sign_info.abbrev,
                "degree": deg,
                "minute": min_,
                "retrograde": p.get("retrograde", False),
            }

        old_h = self["houses"]
        shifted_houses = {
            "system": old_h["system"],
            "armc_rad": (old_h["armc_rad"] + arc) % (2.0 * math.pi),
            "ascendant": _format_angle((old_h["ascendant"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "midheaven": _format_angle((old_h["midheaven"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "vertex": _format_angle((old_h["vertex"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "east_point": _format_angle((old_h["east_point"]["longitude_rad"] + arc) % (2.0 * math.pi)),
            "cusps": [_format_angle((c["longitude_rad"] + arc) % (2.0 * math.pi))
                      for c in old_h["cusps"]],
        }

        aspects = find_all_aspects(shifted_body_lons, body_rates=self._body_rates)

        data = dict(self)
        data["planets"] = shifted_planets
        data["houses"] = shifted_houses
        data["aspects"] = aspects
        return Chart(data, self._body_rates)

    # -- returns --

    def solar_return(self, target_year: int, *,
                     latitude_deg: float | None = None,
                     longitude_deg: float | None = None) -> "Chart":
        """Solar Return chart for target_year solving exact Sun longitude recurrence."""
        natal_sun_lon = self["planets"]["sun"]["longitude_rad"]
        lat = latitude_deg if latitude_deg is not None else self["observer"]["lat_deg"]
        lon = longitude_deg if longitude_deg is not None else self["observer"]["lon_deg"]

        y, mo, d, h, mi, s = self._jd_to_cal(self["jd_utc"])
        elapsed_years = target_year - y
        jd_approx = self["jd_utc"] + elapsed_years * TROPICAL_YEAR_DAYS

        def obj_fn(jd: float) -> float:
            sun_lon = _get_body_lon_at_jd(jd, 10)
            return (sun_lon - natal_sun_lon + math.pi) % (2.0 * math.pi) - math.pi

        a, b = jd_approx - 5.0, jd_approx + 5.0
        if obj_fn(a) * obj_fn(b) > 0:
            a, b = jd_approx - 15.0, jd_approx + 15.0
            if obj_fn(a) * obj_fn(b) > 0:
                raise ValueError(f"Solar return not bracketed. Guess was jd={jd_approx}")

        jd_exact = search_solar_longitude(natal_sun_lon, a, b)
        return calculate_chart(*self._jd_to_cal(jd_exact), tz=0.0,
                               latitude_deg=lat, longitude_deg=lon)

    def lunar_return(self, target_year: int, target_month: int, *,
                     latitude_deg: float | None = None,
                     longitude_deg: float | None = None) -> "Chart":
        """Lunar Return chart for target_year & target_month solving exact Moon longitude recurrence."""
        natal_moon_lon = self["planets"]["moon"]["longitude_rad"]
        lat = latitude_deg if latitude_deg is not None else self["observer"]["lat_deg"]
        lon = longitude_deg if longitude_deg is not None else self["observer"]["lon_deg"]

        target_jd_approx = calendar_to_jd(target_year, target_month, 15, 12, 0, 0.0)
        elapsed_days = target_jd_approx - self["jd_utc"]
        lunar_cycles = round(elapsed_days / ASTRODIENST_TROPICAL_MONTH_DAYS)
        jd_approx = self["jd_utc"] + lunar_cycles * ASTRODIENST_TROPICAL_MONTH_DAYS

        def obj_fn(jd: float) -> float:
            moon_lon = _get_body_lon_at_jd(jd, 301)
            return (moon_lon - natal_moon_lon + math.pi) % (2.0 * math.pi) - math.pi

        a, b = jd_approx - 2.5, jd_approx + 2.5
        if obj_fn(a) * obj_fn(b) > 0:
            raise ValueError(f"Lunar return not bracketed in +/- 2.5 days. Guess was jd={jd_approx}")

        jd_exact = search_lunar_longitude(natal_moon_lon, a, b)
        return calculate_chart(*self._jd_to_cal(jd_exact), tz=0.0,
                               latitude_deg=lat, longitude_deg=lon)

    # -- derived methods (compositions) --

    def composite_secondary(self, other: "Chart", years: float,
                            latitude_deg: float | None = None,
                            longitude_deg: float | None = None) -> "Chart":
        """Derived method: Composite chart secondary progression."""
        return self.composite_with(other).secondary_progression(
            age_years=years, latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    def davison_tertiary(self, other: "Chart", years: float,
                         latitude_deg: float | None = None,
                         longitude_deg: float | None = None) -> "Chart":
        """Derived method: Davison chart tertiary progression (Tertiary I)."""
        return self.davison_with(other).tertiary_i(
            age_years=years, latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    def marks_with(self, other: "Chart", *, mode: str = "davison") -> "Chart":
        """Marks Relationship Chart (马盘).

        The chart of one person's internal experience of the relationship.
        Calculated as the midpoint between the natal chart (self) and the relationship chart.

        *mode* can be:
        - ``"davison"`` (default): self midpoint with Davison(self, other)
        - ``"composite"``: self midpoint with Composite(self, other)
        """
        if mode == "davison":
            rel = self.davison_with(other)
            return self.davison_with(rel)
        elif mode == "composite":
            rel = self.composite_with(other)
            return self.composite_with(rel)
        else:
            raise ValueError("mode must be 'davison' or 'composite'")

    def marks_secondary(self, other: "Chart", years: float,
                        latitude_deg: float | None = None,
                        longitude_deg: float | None = None) -> "Chart":
        """Derived method: Marks secondary progression."""
        return self.marks_with(other).secondary_progression(
            age_years=years, latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    def marks_tertiary(self, other: "Chart", years: float,
                       latitude_deg: float | None = None,
                       longitude_deg: float | None = None) -> "Chart":
        """Derived method: Marks tertiary progression."""
        return self.marks_with(other).tertiary_i(
            age_years=years, latitude_deg=latitude_deg, longitude_deg=longitude_deg)

    @staticmethod
    def _jd_to_cal(jd: float) -> tuple[int, int, int, int, int, float]:
        from ._time import jd_to_calendar
        return jd_to_calendar(jd)


def calculate_chart(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: float = 0.0,
    *,
    tz: float = 0.0,
    latitude_deg: float = 0.0,
    longitude_deg: float = 0.0,
    house_system: HouseSystem = HouseSystem.PLACIDUS,
    taiyin_position_fn: Callable[[float, int], tuple[float, float, float]]
        | None = None,
    taiyin_velocity_fn: Callable[[float, int], tuple[float, float, float]]
        | None = None,
) -> Chart:
    """Calculate a western astrology chart.

    Returns a Chart (dict subclass) with planets, houses, aspects.
    """
    # --- time ---
    # Convert local time → UTC: compute JD in local, then shift by tz
    jd_local = calendar_to_jd(year, month, day, hour, minute, second)
    jd_utc = jd_local - tz / 24.0
    jd_tt = jd_ut1_to_tt(jd_utc)  # approximation: UTC≈UT1

    lat_rad = math.radians(latitude_deg)
    lon_rad = math.radians(longitude_deg)

    # --- ephemeris ---
    if taiyin_position_fn is None:
        from taiyin_semi_analytic import position as _pos
        taiyin_position_fn = _pos                          # type: ignore[assignment]
    if taiyin_velocity_fn is None:
        from taiyin_semi_analytic import velocity_icrf as _vel
        taiyin_velocity_fn = _vel                          # type: ignore[assignment]

    # Earth position + velocity for geocentric conversion
    earth_pos_km = _to_xyz(taiyin_position_fn(jd_tt, 399))
    earth_vel_km_per_day = _to_xyz(taiyin_velocity_fn(jd_tt, 399))
    earth_pos_au = _to_xyz(tuple(_km_to_au(v) for v in earth_pos_km))
    earth_vel_au_per_day = _to_xyz(tuple(_km_to_au(v) for v in earth_vel_km_per_day))

    # --- precession / nutation ---
    nut = iau2000b_nutation_angles(jd_tt)
    eqeq = equation_of_equinoxes_rad(jd_tt)
    jd_ut1 = jd_tt_to_ut1(jd_tt)
    gast = gast_rad(jd_ut1, jd_tt, eqeq)

    # --- houses ---
    houses = calc_houses(gast, lon_rad, lat_rad,
                         nut["true_obliquity_rad"], house_system)

    # --- planets ---
    planets = {}
    for body_id, key, name in _PLANETS:
        # Heliocentric ICRF position (km)
        helio_pos_km = _to_xyz(taiyin_position_fn(jd_tt, body_id))
        helio_pos_au = _to_xyz(tuple(_km_to_au(v) for v in helio_pos_km))

        # Geocentric
        geo_au = (
            helio_pos_au[0] - earth_pos_au[0],
            helio_pos_au[1] - earth_pos_au[1],
            helio_pos_au[2] - earth_pos_au[2],
        )

        # Light-time + aberration
        geo_au = apply_light_corrections(
            jd_tt,
            lambda jd: _to_xyz(tuple(_km_to_au(v)
                                     for v in taiyin_position_fn(jd, body_id))),
            earth_pos_au,
            earth_vel_au_per_day,
            light_time=True,
            aberration=True,
        )

        # Solar deflection
        geo_au = apply_solar_deflection(
            earth_pos_au,
            _to_xyz((earth_pos_au[0] + geo_au[0],
                     earth_pos_au[1] + geo_au[1],
                     earth_pos_au[2] + geo_au[2])),
        )

        # ICRF equatorial → J2000 ecliptic → true ecliptic of date
        from ._precession import rotate_equator_to_ecliptic, _J2000_OBLIQUITY_RAD
        geo_ecl = rotate_equator_to_ecliptic(geo_au, _J2000_OBLIQUITY_RAD)
        ecl_date = j2000_ecliptic_to_date(geo_ecl, jd_tt)

        # Spherical
        x, y, z = ecl_date
        r = math.sqrt(x * x + y * y + z * z)
        lon = math.atan2(y, x) % (2.0 * math.pi)
        lat = math.asin(z / r) if r > 0.0 else 0.0

        sign_info, deg, min_ = sign_degree_minute(lon)

        if key == "moon":
            from ._moon_points import calc_true_node_and_lilith, calc_mean_node_ecliptic_of_date, calc_mean_apogee_ecliptic_of_date
            
            # Compute geometric (unaberrated) Moon velocity in True Ecliptic of Date with dt = 1e-4
            dt = 1e-4
            def _moon_geo_ecl_raw(t_eval: float) -> tuple[float, float, float]:
                h_pos_km = _to_xyz(taiyin_position_fn(t_eval, body_id))
                e_pos_km = _to_xyz(taiyin_position_fn(t_eval, 399))
                g_au = (_km_to_au(h_pos_km[0] - e_pos_km[0]),
                        _km_to_au(h_pos_km[1] - e_pos_km[1]),
                        _km_to_au(h_pos_km[2] - e_pos_km[2]))
                g_ecl = rotate_equator_to_ecliptic(g_au, _J2000_OBLIQUITY_RAD)
                return j2000_ecliptic_to_date(g_ecl, t_eval)

            pos_geo = _moon_geo_ecl_raw(jd_tt)
            pos_plus = _moon_geo_ecl_raw(jd_tt + dt)
            pos_minus = _moon_geo_ecl_raw(jd_tt - dt)
            
            moon_vel = ((pos_plus[0] - pos_minus[0]) / (2.0 * dt),
                        (pos_plus[1] - pos_minus[1]) / (2.0 * dt),
                        (pos_plus[2] - pos_minus[2]) / (2.0 * dt))
                        
            true_node_rad, true_lilith_rad = calc_true_node_and_lilith(pos_geo, moon_vel)
            mean_node_rad = calc_mean_node_ecliptic_of_date(jd_tt)
            mean_lilith_rad = calc_mean_apogee_ecliptic_of_date(jd_tt)
            
            def _insert_point(p_key: str, p_name: str, p_rad: float):
                p_sinfo, p_deg, p_min = sign_degree_minute(p_rad)
                planets[p_key] = {
                    "name": p_name,
                    "longitude_rad": p_rad,
                    "latitude_rad": 0.0,
                    "distance_au": 1.0,
                    "sign": p_sinfo.name,
                    "sign_abbrev": p_sinfo.abbrev,
                    "degree": p_deg,
                    "minute": p_min,
                    "retrograde": False,
                }
            
            _insert_point("true_node", "True Node", true_node_rad)
            _insert_point("mean_node", "Mean Node", mean_node_rad)
            _insert_point("true_lilith", "True Lilith", true_lilith_rad)
            _insert_point("mean_lilith", "Mean Lilith", mean_lilith_rad)

        planets[key] = {
            "name": name,
            "longitude_rad": lon,
            "latitude_rad": lat,
            "distance_au": r,
            "sign": sign_info.name,
            "sign_abbrev": sign_info.abbrev,
            "degree": deg,
            "minute": min_,
        }

    # --- longitude rates (for applying/separating) ---
    from ._precession import rotate_equator_to_ecliptic, _J2000_OBLIQUITY_RAD
    dt = 0.001  # ~1.4 minutes
    body_lons = {k: p["longitude_rad"] for k, p in planets.items()}
    body_rates: dict[str, float] = {}
    for body_id, key, name in _PLANETS:
        helio_km2 = _to_xyz(taiyin_position_fn(jd_tt + dt, body_id))
        geo_au2 = _to_xyz(tuple(_km_to_au(v) for v in helio_km2))
        geo_au2 = (
            geo_au2[0] - earth_pos_au[0],
            geo_au2[1] - earth_pos_au[1],
            geo_au2[2] - earth_pos_au[2],
        )
        geo_ecl2 = rotate_equator_to_ecliptic(geo_au2, _J2000_OBLIQUITY_RAD)
        ecl_date2 = j2000_ecliptic_to_date(geo_ecl2, jd_tt + dt)
        x2, y2, z2 = ecl_date2
        lon2 = math.atan2(y2, x2) % (2.0 * math.pi)
        body_rates[key] = (lon2 - body_lons[key]) / dt

    # tag retrograde
    for key, p in planets.items():
        p["retrograde"] = body_rates.get(key, 0.0) < 0.0

    # classical dignities, receptions, and antiscia
    from ._classical import get_essential_dignities, get_accidental_dignities, get_rulers, TRADITIONAL_PLANETS
    
    sun_lon = body_lons.get("sun", 0.0)
    asc_lon = houses["ascendant_rad"]
    is_day_chart = ((sun_lon - asc_lon) % (2.0 * math.pi)) > math.pi
    
    for key, p in planets.items():
        lon = p["longitude_rad"]
        p["antiscia_rad"] = (math.pi - lon) % (2.0 * math.pi)
        p["contra_antiscia_rad"] = (2.0 * math.pi - lon) % (2.0 * math.pi)
        
        if key in TRADITIONAL_PLANETS:
            deg_in_sign = p["degree"] + p["minute"] / 60.0
            essential = get_essential_dignities(key, p["sign"], deg_in_sign, is_day_chart)
            speed_deg = math.degrees(body_rates.get(key, 0.0))
            accidental = get_accidental_dignities(key, lon, sun_lon, speed_deg, is_day_chart)
            
            # Receptions (who receives this planet?)
            rulers = get_rulers(p["sign"], deg_in_sign, is_day_chart)
            received_by = {}
            for dignity, ruler in rulers.items():
                if ruler and ruler != key: # Exclude self-reception
                    base_dignity = dignity.split("_")[0]
                    if ruler not in received_by:
                        received_by[ruler] = []
                    if base_dignity not in received_by[ruler]:
                        received_by[ruler].append(base_dignity)
            
            p["classical"] = {
                "essential_dignities": essential["details"],
                "accidental_conditions": accidental,
                "received_by": received_by,
                "essential_score": essential["score"],
                "systems": essential["systems"]
            }

    # Extract Mutual Receptions
    mutual_receptions = []
    trad_keys = [k for k in planets if k in TRADITIONAL_PLANETS]
    for i in range(len(trad_keys)):
        for j in range(i + 1, len(trad_keys)):
            k1 = trad_keys[i]
            k2 = trad_keys[j]
            k1_rec_k2 = planets[k2]["classical"]["received_by"].get(k1)
            k2_rec_k1 = planets[k1]["classical"]["received_by"].get(k2)
            if k1_rec_k2 and k2_rec_k1:
                mutual_receptions.append({
                    "planets": [k1, k2],
                    k1: k2_rec_k1,  # k1 is received by k2 by these dignities
                    k2: k1_rec_k2   # k2 is received by k1 by these dignities
                })

    # --- aspects ---
    aspects = find_all_aspects(body_lons, body_rates=body_rates)

    # --- assemble ---
    y, mo, d, h, mi, s = jd_to_calendar(jd_utc)
    # Extract same degree relationships (同度)
    degree_groups = {}
    
    # 1. Planets and nodes
    for k, p in planets.items():
        deg = p["degree"]
        if deg not in degree_groups:
            degree_groups[deg] = []
        degree_groups[deg].append(k)
        
    # 2. Angles (Ascendant, MC, Descendant, IC)
    _, asc_deg, _ = sign_degree_minute(houses["ascendant_rad"])
    if asc_deg not in degree_groups:
        degree_groups[asc_deg] = []
    degree_groups[asc_deg].append("ascendant")
    
    _, mc_deg, _ = sign_degree_minute(houses["midheaven_rad"])
    if mc_deg not in degree_groups:
        degree_groups[mc_deg] = []
    degree_groups[mc_deg].append("midheaven")
    
    # Keep only groups with 2 or more points
    same_degrees = []
    for deg, pts in degree_groups.items():
        if len(pts) >= 2:
            same_degrees.append({
                "degree": deg,
                "points": pts
            })

    # --- lots / arabic parts ---
    from ._lots import calculate_lots
    lots = calculate_lots(
        asc_deg=math.degrees(houses["ascendant_rad"]),
        sun_deg=math.degrees(body_lons.get("sun", 0.0)),
        moon_deg=math.degrees(body_lons.get("moon", 0.0)),
        venus_deg=math.degrees(body_lons.get("venus", 0.0)),
        mars_deg=math.degrees(body_lons.get("mars", 0.0)),
        jupiter_deg=math.degrees(body_lons.get("jupiter", 0.0)),
        saturn_deg=math.degrees(body_lons.get("saturn", 0.0)),
        mercury_deg=math.degrees(body_lons.get("mercury", 0.0)),
        is_day_chart=is_day_chart
    )

    # Return final chart object
    data = {
        "jd_utc": jd_utc,
        "jd_tt": jd_tt,
        "delta_t_s": delta_t_seconds_from_jd_ut1(jd_utc),
        "date_utc": f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{int(s):02d}Z",
        "observer": {
            "lat_deg": latitude_deg,
            "lon_deg": longitude_deg,
        },
        "date": {
            "jd_ut": jd_utc,
            "jd_tt": jd_tt,
        },
        "location": {
            "lat_deg": latitude_deg,
            "lon_deg": longitude_deg,
        },
        "planets": planets,
        "lots": lots,
        "mutual_receptions": mutual_receptions,
        "same_degrees": same_degrees,
        "houses": {
            "system": houses["system"].value,
            "armc_rad": houses["armc_rad"],
            "ascendant": _format_angle(houses["ascendant_rad"]),
            "midheaven": _format_angle(houses["midheaven_rad"]),
            "vertex": _format_angle(houses["vertex_rad"]),
            "east_point": _format_angle(houses["east_point_rad"]),
            "cusps": [_format_angle(c) for c in houses["cusps_rad"]],
        },
        "aspects": aspects,
    }
    return Chart(data, body_rates)


def _format_angle(rad: float) -> dict:
    sign, deg, min_ = sign_degree_minute(rad)
    return {
        "sign": sign.name,
        "sign_abbrev": sign.abbrev,
        "degree": deg,
        "minute": min_,
        "longitude_rad": rad,
    }
