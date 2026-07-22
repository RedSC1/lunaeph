# LunaEph

A thin, pure-Python western astrology library built on top of
[taiyin-ephemeris-semi-analytic](https://pypi.org/project/taiyin-ephemeris-semi-analytic/).

Pure Python.  Zero native C/C++ dependencies (`pip install` and go).  Covers −3000 to +3000.

## Quick start

```python
from lunaeph import calculate_chart

chart = calculate_chart(
    2003, 3, 13, 14, 15, 0,          # local date & time
    tz=8.0,                            # UTC+8
    latitude_deg=37.45,                # Dongying, Shandong
    longitude_deg=118.49,
)
```

`chart` is a dict-like `Chart` object.  Access everything by key or
convenience accessors:

```python
# Planets
chart.planet("sun")          # {'name': 'Sun', 'sign': 'Pisces',
                              #  'degree': 22, 'minute': 15,
                              #  'retrograde': False, ...}
chart.planets                # ['sun', 'moon', 'mercury', ...]

# Houses
chart.ascendant              # {'sign': 'Leo', 'degree': 5, 'minute': 32}
chart.midheaven              # {'sign': 'Aries', 'degree': 24, 'minute': 31}
chart.house_cusp(1)          # same as ascendant

# Aspects
chart["aspects"]             # flat list of all aspect entries
chart.aspects_to("moon")     # filter by body
chart.aspects_between("sun", "moon")

# Tuning
chart.set_orb(60, 1.0)       # sextile → 1 degree orb
chart.set_orb(100, 2.0)      # custom angle
chart.reset_orb(60)          # back to default
```

### Relationship & Predictive Charts

```python
chart_a = calculate_chart(1990, 1, 1, 12, 0, latitude_deg=51.5, longitude_deg=-0.1)
chart_b = calculate_chart(1992, 6, 15, 18, 30, latitude_deg=40.7, longitude_deg=-74.0)

# Synastry (Cross-chart aspects + house placements)
syn = chart_a.synastry_with(chart_b)

# Midpoint Composite Chart
comp = chart_a.composite_with(chart_b)

# Davison Time & Space Midpoint Chart
dav = chart_a.davison_with(chart_b, mode="spherical") # or mode="arithmetic"

# Progressions & Directions
prog = chart_a.secondary_progression(years=30.0)      # 1 day = 1 year (Age 30 = +30 days)
tert = chart_a.tertiary_progression(years=30.0)       # Tertiary I (1 day = 1 tropical month)
minor = chart_a.minor_progression(years=30.0)         # Minor (1 synodic month = 1 year of life)
sa = chart_a.solar_arc(years=30.0)                    # True Solar Arc (secondary Sun delta)
naibod = chart_a.naibod_direction(years=30.0)         # Naibod Arc (0.9856°/year)

# Solar & Lunar Returns (Exact root finding)
sr = chart_a.solar_return(2025)
lr = chart_a.lunar_return(2025, 3)

# Derived Compositions
comp_prog = chart_a.composite_secondary(chart_b, 30.0)
dav_tert = chart_a.davison_tertiary(chart_b, 30.0)
marks = chart_a.marks_secondary(chart_b, 30.0)
```

## Demo output

```
┌──────────┬───────────────┬──────┬────┬────┐
│ Planet   │ Position      │ Sign │ H  │ R  │
├──────────┼───────────────┼──────┼────┼────┤
│ Sun      │ Pis 22°15'    │ Pis  │  8 │    │
│ Moon     │ Can 14°46'    │ Can  │ 12 │    │
│ Mercury  │ Pis 14°17'    │ Pis  │  8 │    │
│ Venus    │ Aqu 12°42'    │ Aqu  │  7 │    │
│ Mars     │ Cap  5°19'    │ Cap  │  6 │    │
│ Jupiter  │ Leo  8°49'    │ Leo  │  1 │ ℞  │
│ Saturn   │ Gem 22°28'    │ Gem  │ 11 │    │
│ Uranus   │ Pis  0°08'    │ Pis  │  8 │    │
│ Neptune  │ Aqu 12°08'    │ Aqu  │  7 │    │
│ Pluto    │ Sag 19°55'    │ Sag  │  5 │    │
├──────────┼───────────────┼──────┼────┼────┤
│ ASC      │ Leo  5°32'    │ Leo  │  1 │    │
│ MC       │ Ari 24°31'    │ Ari  │ 10 │    │
└──────────┴───────────────┴──────┴────┴────┘

┌──────┬───────────────┐
│ Hous │ Cusp          │
├──────┼───────────────┤
│    1 │ Leo  5°32'    │
│    2 │ Leo 27°01'    │
│    3 │ Vir 22°51'    │
│    4 │ Lib 24°31'    │
│    5 │ Sag  0°20'    │
│    6 │ Cap  5°07'    │
│    7 │ Aqu  5°32'    │
│    8 │ Aqu 27°01'    │
│    9 │ Pis 22°51'    │
│   10 │ Ari 24°31'    │
│   11 │ Gem  0°20'    │
│   12 │ Can  5°07'    │
└──────┴───────────────┘

┌──────────┬──────────┬──────────────────┬───────┬──────┐
│ Body 1   │ Body 2   │ Aspect           │  Orb  │ A/S  │
├──────────┼──────────┼──────────────────┼───────┼──────┤
│ Mercury  │ Sun      │ conjunction      │ 7.96° │ A    │
│ Neptune  │ Venus    │ conjunction      │ 0.56° │ S    │
│ Mercury  │ Pluto    │ square           │ 5.63° │ S    │
│ Pluto    │ Sun      │ square           │ 2.33° │ S    │
│ Saturn   │ Sun      │ square           │ 0.22° │ A    │
│ Mercury  │ Moon     │ trine            │ 0.48° │ S    │
│ Jupiter  │ Neptune  │ opposition       │ 3.32° │ A    │
│ Jupiter  │ Venus    │ opposition       │ 3.88° │ A    │
│ Pluto    │ Saturn   │ opposition       │ 2.55° │ A    │
└──────────┴───────────────┴──────────────────┴───────┴──────┘
```

## Features

- **10 planets** — Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus,
  Neptune, Pluto — with retrograde detection
- **12 aspect angles** — conjunction, opposition, trine, square, sextile,
  quincunx, semisextile, semisquare, sesquiquadrate, quintile, biquintile,
  decile (36°)
- **Applying / separating** — using true-ecliptic-of-date longitude rates
- **8 house systems** — Placidus (default), Koch, Whole Sign, Equal, Porphyry,
  Regiomontanus, Campanus, Alcabitius — extensible registry
- **Custom aspect angles** — `set_orb(70, 2.0)` — all angles are first-class
- **Per-angle orb tuning** — `set_orb()` touches only that angle, others untouched
- **Relationship charts** — Synastry, Composite, Davison
- **Predictive charts** — Secondary progression, Tertiary progression I & Minor progression, True Solar Arc, Naibod direction, Solar Return, Lunar Return
- **Zero external solver dependencies** — Pure Python Brent root finding for exact return recurrence

## Astrological Conventions & Schools

| Feature | Method / Convention | Astrodienst / SwissEph Alignment |
|---|---|---|
| **Synastry** | Cross-chart aspects strictly between A and B; A-in-B and B-in-A house placements; bodies kept in distinct dictionary structures. | Astrodienst Synastry standard |
| **Composite** | Short-arc circular midpoints for planets; 180° ambiguity resolved towards Ascendant; house cusps recalculated from composite ARMC midpoint & spherical midpoint location. | Hand (1975) / Astrodienst Composite convention |
| **Davison** | Exact time midpoint; spherical 3D vector midpoint (default `mode="spherical"`) or arithmetic coordinate mean (`mode="arithmetic"`). | Davison Time/Space chart |
| **Secondary Progression** | 1 ephemeris day per tropical year of life ($365.2421897$ days). Age 30 corresponds to $+30$ ephemeris days after birth. | Astrodienst Secondary Progression |
| **Tertiary Progression I** | 1 ephemeris day = 1 tropical month of life (~$27.32158218$ days). | Astrodienst Tertiary I |
| **Minor Progression** | 1 synodic month of life (~$29.530589$ days) = 1 ephemeris day (Tertiary II). | Astrodienst Minor Progression |
| **Solar Arc** | True solar arc direction ($\Delta\lambda_{\odot} = \text{Sun}_{\text{progressed}} - \text{Sun}_{\text{natal}}$). | Astrodienst Solar Arc |
| **Naibod Arc** | Fixed mean solar rate direction ($0.9856^\circ/\text{year}$). | Naibod direction option |
| **Solar / Lunar Returns** | Pure-Python Brent's method solving exact true-ecliptic longitude recurrence ($< 10^{-5}$ rad error). | Astrodienst Solar/Lunar Return |

## Scope & Limitations

- **Pure Python focus**: Designed for lightweight Python applications that cannot build native C/C++ extensions (`pyswisseph`).
- **Celestial Bodies**: Currently includes 10 main planets. Lunar Nodes (True/Mean), Lilith, Chiron, and Fortuna are planned for v0.2.
- **Ephemeris Range**: −3000 to +3000 (inherited from Vondrák 2011 precession & taiyin semi-analytic model).

## Astronomy

| Correction | Model |
|---|---|
| Precession | Vondrák 2011 |
| Nutation | IAU 2000B |
| ΔT | Stephenson & Morrison (2004/2015) spline + annual table (Catmull-Rom) |
| Light-time | single-pass iteration |
| Stellar aberration | special-relativistic velocity form |
| Solar deflection | GR deflection vector formula |

All models are hardcoded (no runtime data files), same philosophy as taiyin.
Planetary positions inherit taiyin's precision (~0.2–3.7 arcsec RMS vs DE441).

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
