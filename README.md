# LunaEph

**A lightweight, arcsecond-precision astrology engine for ±3000 years.**

Pure Python.  Zero native C/C++ dependencies.  `pip install` and go.

Covers western tropical, Indian sidereal, and classical medieval techniques —
all from a single `calculate_chart()` call.  Built on
[taiyin-ephemeris-semi-analytic](https://pypi.org/project/taiyin-ephemeris-semi-analytic/)
(∼0.2–3.7″ RMS vs DE441) with Vondrák 2011 precession, IAU 2000B nutation,
WGS84 ellipsoid, and hybrid atmospheric refraction — hardcoded, no runtime
data files.

## Quick start

```python
from lunaeph import calculate_chart

chart = calculate_chart(
    2003, 3, 13, 14, 15, 0,          # local date & time
    tz=8.0,                            # UTC+8
    latitude_deg=37.45,                # Dongying, Shandong
    longitude_deg=118.49,
)

# Planets
chart.planet("sun")          # {'name': 'Sun', 'sign': 'Pisces', 'degree': 22, ...}
chart.planets                # ['sun', 'moon', 'mercury', ...]

# Houses
chart.ascendant              # {'sign': 'Leo', 'degree': 5, 'minute': 32}
chart.midheaven              # {'sign': 'Aries', 'degree': 24, 'minute': 31}

# Aspects
chart.aspects_to("moon")     # filter by body
chart.aspects_between("sun", "moon")

# Custom orbs
chart.set_orb(60, 1.0)       # sextile → 1° orb
chart.reset_orb(60)          # back to default
```

## Feature overview

| Category | What | Detail |
|---|---|---|
| **Planets** | 10 bodies + lunar nodes + Lilith | Sun through Pluto, True/Mean Node, True/Mean Lilith |
| **Houses** | 8 systems | Placidus, Koch, Whole Sign, Equal, Porphyry, Regiomontanus, Campanus, Alcabitius |
| **Aspects** | 12 angles + custom | Conjunction, opposition, trine, square, sextile, quincunx, semisextile, semisquare, sesquiquadrate, quintile, biquintile, decile; applying/separating via true velocity |
| **Signs** | Tropical + sidereal | 12 tropical signs (element/modality/triplicity); 6 ayanamshas (Lahiri, Fagan-Bradley, Raman, Krishnamurti, Yukteswar, True Chitra) |
| **Dignities** | Essential + accidental | Domicile, detriment, exaltation, fall, Dorothean triplicities, Chaldean faces, Ptolemaic & Egyptian terms, sect, combustion, cazimi |
| **Lots** | Hellenistic / Arabic Parts | Fortune, Spirit, Eros, Nemesis, Victory, Courage, Necessity, and more |
| **Relationship** | Synastry, Composite, Davison | Cross-chart aspects + house overlays; midpoint composite; time/space Davison |
| **Predictive** | Progressions + directions | Secondary, Tertiary I & II, Minor; True Solar Arc; Naibod direction |
| **Returns** | Solar + Lunar Returns | Exact Brent root-finding on true ecliptic longitude recurrence |
| **Medieval** | Almuten, Firdaria, ZR, Profections, Primary Directions | Ibn Ezra / Bonatti / Lilly schools; Valens/Brennan ZR; Naibod/Ptolemy keys |
| **Jyotish** | Nakshatra, Dasha, Vargas, Karakas | 27/28 Nakshatras with Ashta Kuta; Vimshottari (5-level) & Yogini Dasha; 16 Vargas (D1–D60); Chara/Sthira/Naisargika Karakas |
| **Jyotish II** | Ashtakavarga, Arudha, Upagraha, KP | Sarvashtakavarga; Jaimini Arudha Padas; 5 Upagrahas; KP sub-lord; Panchadha Maitri |
| **Time utils** | EoT, sunrise/sunset, syzygy | Equation of time; WGS84 ellipsoid + hybrid Bennett/Smart refraction; new/full moon sequence; apparent solar time |

## Western astrology

### Houses & signs

```python
from lunaeph import calculate_chart, HouseSystem

chart = calculate_chart(1990, 1, 1, 12, 0,
                        latitude_deg=51.5, longitude_deg=-0.1,
                        house_system=HouseSystem.KOCH)

for i in range(1, 13):
    cusp = chart.house_cusp(i)
    print(f"House {i:2d}: {cusp['sign_abbrev']:>3s} {cusp['degree']:2d}°{cusp['minute']:02d}'")

# Custom orbs
chart.set_orb(72, 2.0)   # quintile → 2°
chart.set_orb(100, 1.5)  # custom angle → 1.5°
```

### Relationship charts

```python
a = calculate_chart(1990, 1, 1, 12, 0, latitude_deg=51.5, longitude_deg=-0.1)
b = calculate_chart(1992, 6, 15, 18, 30, latitude_deg=40.7, longitude_deg=-74.0)

syn = a.synastry_with(b)                # cross-chart aspects + house placements
comp = a.composite_with(b)              # midpoint composite
dav = a.davison_with(b, mode="spherical")  # Davison time/space chart

# Synastry cross-aspects (planet-to-planet only, top 5)
for entry in syn["cross_aspects"][:5]:
    print(f"{entry['chart_a_body']:8s}─{entry['chart_b_body']:8s}  "
          f"{entry['aspect']:14s}  {entry['orb_deg']:.2f}°  "
          f"{'A' if entry.get('applying') else 'S'}")
#  sun     ─moon      quincunx        1.14°  A
#  sun     ─mercury   square          4.29°  S
#  sun     ─mars      biquintile      1.37°  S
#  sun     ─saturn    square          4.69°  A
#  sun     ─neptune   semisquare      1.42°  A
```

### Progressions & returns

```python
chart = calculate_chart(1990, 1, 1, 12, 0, latitude_deg=51.5, longitude_deg=-0.1)

prog  = chart.secondary_progression(years=30.0)  # 1 day = 1 year
tert  = chart.tertiary_progression(years=30.0)   # Tertiary I
sa    = chart.solar_arc(years=30.0)              # True Solar Arc
sr25  = chart.solar_return(2025)                 # Solar Return for 2025
lr    = chart.lunar_return(2025, 3)              # Lunar Return for Mar 2025
```

### Classical techniques

```python
# Almuten Figuris (Victor of the Chart)
alm = chart.almuten_figuris()             # → 'venus', score 33

# Firdaria (Persian time-lord periods)
from lunaeph import get_current_firdaria
fird = chart.firdaria(age=33.5)           # active major & minor periods

# Zodiacal Releasing (Valens)
zr = chart.zodiacal_releasing(lot="spirit", age=33.5)

# Annual / Monthly / Daily Profections
prof = chart.profection(age=33.5)

# Primary Directions (Naibod key)
from lunaeph import calc_primary_directions
dirs = chart.primary_directions(key="naibod")

# Arabic Lots
from lunaeph import calculate_lots
lots = calculate_lots(asc_deg, sun_deg, moon_deg, ...)
```

## Indian / Vedic (Jyotish)

### Nakshatras & compatibility

```python
from lunaeph import calc_nakshatra_chart, calc_nakshatra_compatibility, get_nakshatra_info

# Planetary nakshatra placements (27 or 28 system)
nak = chart.nakshatra_chart(ayanamsha_mode="lahiri", system="27")
# → {'sun': {'nakshatra': 'Purva Bhadrapada', 'pada': 3, ...}, ...}

# Ashta Kuta compatibility
score = chart_a.nakshatra_compatibility(chart_b, ayanamsha_mode="lahiri")
# → {'total': 24.5, 'varna': 1, 'vashya': 2, 'tara': 3, ...}

# Single nakshatra info
info = get_nakshatra_info("Rohini")
# → {'lord': 'moon', 'deity': 'Brahma', 'gana': 'Manushya', ...}
```

### Dasha systems

```python
# Vimshottari Dasha (120-year, 5-level recursive)
dasha = chart.vimshottari_dasha(age=20.35, ayanamsha_mode="lahiri")
# → maha, antara, pratyantara, sookshma, prana breakdown

# Yogini Dasha (36-year cycle)
from lunaeph import calc_yogini_dasha
yog = chart.yogini_dasha(age_years=20.35)

# Convenience: current active period
from lunaeph import get_current_dasha
active = get_current_dasha(chart, age=20.35)
```

### Divisional charts (Vargas)

```python
# All 16 Vargas (D1 Rashi through D60 Shashtiamsha)
from lunaeph import calculate_divisional_charts
vargas = chart.divisional_charts(ayanamsha_mode="lahiri")
# → D1, D2 Hora, D3 Drekkana, D4, D7, D9 Navamsha, D10, D12, D16,
#   D20, D24, D27 Bhamsha, D30 Trimshamsha, D40, D45, D60
```

### More Jyotish tools

```python
# Jaimini Chara Karakas (7 or 8 planet scheme)
k = chart.jaimini_chara_karakas(scheme="8_karaka")

# Ashtakavarga (Sarvashtakavarga, max 337 bindus)
av = chart.ashtakavarga()        # → bhinnashtakavarga per planet + sarva totals

# Arudha Padas (A1–A12, including Upapada/UL)
ap = chart.arudha_padas()        # → {'A1': ..., 'upapada': ...}

# Sade Sati (Saturn 7.5-year transit)
chart.sade_sati("Capricorn")     # is Saturn transiting over natal Moon?

# Upagrahas (5 shadow planets)
chart.upagrahas()                # → Dhuma, Vyatipata, Parivesha, Indrachapa, Upaketu

# KP system
chart.kp_sublord(planet="moon")  # → star-lord + sub-lord

# All three karaka systems
from lunaeph import calc_all_karakas
all_k = chart.karakas()          # → Naisargika, Sthira, Chara
```

## Time & calendar utilities

### Equation of time

```python
from lunaeph import equation_of_time_minutes, apparent_solar_time_minutes
from lunaeph._time import calendar_to_jd

jd = calendar_to_jd(2024, 11, 3, 12, 0, 0.0)
eot = equation_of_time_minutes(jd)          # → +16.48 min (sundial ahead of clock)
ast = apparent_solar_time_minutes(jd, lon_deg=116.4)  # → minutes since midnight
```

### Sunrise, sunset & twilight

```python
from lunaeph import sun_times

times = sun_times(2003, 3, 13, lon_deg=118.49, lat_deg=37.45, tz=8.0)
# → {'rise': JD, 'transit': JD, 'set': JD,
#     'civil_dawn': JD, 'civil_dusk': JD,
#     'nautical_dawn': JD, 'nautical_dusk': JD,
#     'astron_dawn': JD, 'astron_dusk': JD}
# Uses WGS84 ellipsoid + hybrid Bennett/Smart refraction model.
# Also accepts height_m, pressure_mbar, temperature_c for precision.
```

### New & full moons

```python
from lunaeph import new_moons_between, full_moons_between, calendar_to_jd, jd_to_calendar

jd1 = calendar_to_jd(2003, 1, 1)
jd2 = calendar_to_jd(2004, 1, 1)

for jd in new_moons_between(jd1, jd2):    # 12–13 per year
    y, m, d, h, mi, s = jd_to_calendar(jd)
    print(f"New moon: {y}-{m:02d}-{d:02d} {h:02d}:{mi:02d} UT")
# Accuracy: < 5 minutes vs USNO across −3000 to +3000.
```

## Astronomy

| Correction | Model |
|---|---|
| Planetary ephemeris | taiyin semi-analytic (~0.2–3.7″ RMS vs DE441) |
| Precession | Vondrák 2011 |
| Nutation | IAU 2000B (77 lunisolar + planetary terms) |
| ΔT | Stephenson & Morrison (2004/2015) spline + annual Catmull-Rom table |
| Light-time | single-pass iteration |
| Stellar aberration | special-relativistic velocity form |
| Solar deflection | GR deflection vector |
| Atmospheric refraction | Hybrid Bennett + Smart, scaled by P/T |
| Earth shape | WGS84 ellipsoid (a=6378137 m, 1/f=298.257223563) |

All models are hardcoded — no runtime data files, same philosophy as taiyin.

## Installation

```bash
pip install lunaeph
```

Depends on `taiyin-ephemeris-semi-analytic>=0.2.0`.

## License

Apache 2.0.

## Acknowledgements

- **寿星天文历 (sxwnl)** by 许剑伟 — [https://github.com/sxwnl/sxwnl](https://github.com/sxwnl/sxwnl)  
  The Equation of Time, sunrise/sunset/twilight, and syzygy sequence algorithms
  are adapted from this project. See [NOTICE](NOTICE) for the full copyright notice.
