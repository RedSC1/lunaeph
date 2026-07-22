# LunaEph

A thin western astrology library built on top of
[taiyin-ephemeris-semi-analytic](https://pypi.org/project/taiyin-ephemeris-semi-analytic/).

Pure Python.  Zero native deps beyond taiyin.  `pip install` and go.

```python
from lunaeph import calculate_chart, HouseSystem

chart = calculate_chart(2026, 7, 22, 14, 30,
                         latitude_deg=39.9, longitude_deg=116.4)

print(chart["planets"]["sun"]["sign"])       # Leo
print(chart["houses"]["ascendant"]["sign"])  # Aries
```

## Features

- **10 planets**: Sun, Moon, Mercury–Pluto
- **8 house systems**: Placidus, Koch, Whole Sign, Equal, Porphyry,
  Regiomontanus, Campanus, Alcabitius — plus extensible custom registry
- **11 aspects**: conjunction, opposition, trine, square, sextile,
  quincunx, semisextile, semisquare, sesquiquadrate, quintile, biquintile
  — plus configurable orbs
- **Zodiac signs** with element, modality, ruler, detriment, exaltation, fall
- J2000.0 → true-ecliptic-of-date conversion via Vondrák 2011 precession +
  IAU2000B nutation
- Light-time, stellar aberration, and solar gravitational deflection
  corrections
- All models are hardcoded (no runtime data files), same philosophy as taiyin

## Accuracy

Planetary positions inherit taiyin's precision (~0.2–3.7 arcsec RMS vs DE441).
Precession/nutation models are validated against taiyin C++ oracle tests
at 1e-10 tolerance.

## House systems

```python
from lunaeph import calc_houses, HouseSystem

# Use any built-in system:
houses = calc_houses(gast_rad, lon_rad, lat_rad, true_obliquity_rad,
                     HouseSystem.KOCH)

# Register a custom system:
from lunaeph._houses import register_house_system

def my_system(armc, obl, lat, asc, mc, out):
    ...  # fill out[0..11] with ecliptic longitudes in radians
    return True

register_house_system(HouseSystem("my_system"), my_system)
```

## Structure

```
lunaeph/
├── __init__.py       # public API
├── _time.py          # calendar, deltaT, GMST
├── _precession.py    # Vondrák 2011 + IAU2000B nutation
├── _aberration.py    # light-time + stellar aberration
├── _deflection.py    # solar gravitational deflection
├── _houses.py        # 8 house systems + extensible registry
├── _signs.py         # zodiac signs, elements, modalities
├── _aspects.py       # aspect calculation + configurable orbs
└── _chart.py         # calculate_chart() — wires everything together
tests/
├── test_time_precession.py  # 14 oracle tests from taiyin C++
```

## License

Apache 2.0.
