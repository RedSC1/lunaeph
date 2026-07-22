# LunaEph

A thin western astrology library on top of
[taiyin-ephemeris-semi-analytic](https://pypi.org/project/taiyin-ephemeris-semi-analytic/).

Pure Python.  Zero native deps beyond taiyin.  `pip install` and go.

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
└──────────┴──────────┴──────────────────┴───────┴──────┘
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
- **Zodiac signs** with element, modality, ruler, detriment, exaltation, fall

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
