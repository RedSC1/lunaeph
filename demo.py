"""LunaEph demo — 2003-03-13 14:15 UTC+8, Shandong Dongying (37.45°N 118.49°E)

Demonstrates: chart calculation, houses, aspects, synastry, progressions,
solar return, classical almuten, nakshatras, vimshottari dasha,
EoT, sunrise/sunset, and new/full moon sequence.
"""

from lunaeph import (
    calculate_chart, HouseSystem,
    sun_times, equation_of_time_minutes, apparent_solar_time_minutes,
    new_moons_between, full_moons_between,
)
from lunaeph._time import calendar_to_jd, jd_to_calendar

# ── Golden chart ──────────────────────────────────────────────────────────

chart = calculate_chart(
    2003, 3, 13, 14, 15, 0,
    tz=8.0,
    latitude_deg=37.45,
    longitude_deg=118.49,
    house_system=HouseSystem.PLACIDUS,
)

def fmt_angle(rad):
    from lunaeph._signs import sign_degree_minute
    s, d, m = sign_degree_minute(rad)
    return f"{s.abbrev} {d:2d}°{m:02d}'"

def house_of(lon_rad, cusps):
    c = [h["longitude_rad"] for h in cusps]
    for i in range(12):
        start, end = c[i], c[(i + 1) % 12]
        if start <= end:
            if start <= lon_rad < end:
                return i + 1
        elif lon_rad >= start or lon_rad < end:
            return i + 1
    return 12

cusps = chart["houses"]["cusps"]

# == Planets ==
print("┌──────────┬───────────────┬──────┬────┬────┐")
print("│ Planet   │ Position      │ Sign │ H  │ R  │")
print("├──────────┼───────────────┼──────┼────┼────┤")
for key in ["sun", "moon", "mercury", "venus", "mars",
            "jupiter", "saturn", "uranus", "neptune", "pluto"]:
    p = chart.planet(key)
    pos = fmt_angle(p["longitude_rad"])
    h = house_of(p["longitude_rad"], cusps)
    r = "℞" if p["retrograde"] else " "
    print(f"│ {p['name']:8s} │ {pos:13s} │ {p['sign_abbrev']:4s} │ {h:2d} │ {r}  │")
asc = chart.ascendant
mc = chart.midheaven
print("├──────────┼───────────────┼──────┼────┼────┤")
print(f"│ ASC      │ {fmt_angle(asc['longitude_rad']):13s} │ {asc['sign_abbrev']:4s} │  1 │    │")
print(f"│ MC       │ {fmt_angle(mc['longitude_rad']):13s} │ {mc['sign_abbrev']:4s} │ 10 │    │")
print("└──────────┴───────────────┴──────┴────┴────┘")

# == Houses ==
print()
print("┌──────┬───────────────┐")
print("│ Hous │ Cusp          │")
print("├──────┼───────────────┤")
for i in range(1, 13):
    print(f"│ {i:4d} │ {fmt_angle(cusps[i-1]['longitude_rad']):13s} │")
print("└──────┴───────────────┘")

# == Aspects ==
print()
print("┌──────────┬──────────┬──────────────────┬───────┬──────┐")
print("│ Body 1   │ Body 2   │ Aspect           │  Orb  │ A/S  │")
print("├──────────┼──────────┼──────────────────┼───────┼──────┤")
PLANET_KEYS = {"sun", "moon", "mercury", "venus", "mars",
                "jupiter", "saturn", "uranus", "neptune", "pluto"}

for a in chart["aspects"]:
    if (a.get("major") and a["body1"] in PLANET_KEYS
                       and a["body2"] in PLANET_KEYS):
        b1 = chart.planet(a["body1"])["name"]
        b2 = chart.planet(a["body2"])["name"]
        arrow = "A" if a.get("applying") else "S"
        print(f"│ {b1:8s} │ {b2:8s} │ {a['aspect']:16s} │ {a['orb_deg']:.2f}° │ {arrow}    │")
print("└──────────┴──────────┴──────────────────┴───────┴──────┘")

# ── Synastry ──────────────────────────────────────────────────────────────

print()
print("────────────── Synastry (Dongying natal × a friend) ──────────────")
friend = calculate_chart(2002, 12, 1, 8, 30, 0, tz=8.0,
                         latitude_deg=36.0, longitude_deg=120.0)
syn = chart.synastry_with(friend)
count = 0
for entry in syn["cross_aspects"]:
    if (entry['chart_a_body'] in PLANET_KEYS and entry['chart_b_body'] in PLANET_KEYS):
        print(f"  {entry['chart_a_body']:8s}─{entry['chart_b_body']:8s}  "
              f"{entry['aspect']:14s}  {entry['orb_deg']:.2f}°  "
              f"{'A' if entry.get('applying') else 'S'}")
        count += 1
        if count >= 5:
            break

# ── Predictive ────────────────────────────────────────────────────────────

print()
print("────────────── Progressions & Returns ──────────────────────────────")
prog = chart.secondary_progression(years=20.0)
print(f"  Age 20 (secondary progressed): Sun = {fmt_angle(prog['planets']['sun']['longitude_rad'])}")

sa = chart.solar_arc(years=20.0)
print(f"  Age 20 (solar arc):            Sun = {fmt_angle(sa['planets']['sun']['longitude_rad'])}")

sr = chart.solar_return(2023)
print(f"  Solar Return 2023:             Sun = {fmt_angle(sr['planets']['sun']['longitude_rad'])}")

# ── Classical ─────────────────────────────────────────────────────────────

print()
print("────────────── Almuten Figuris ────────────────────────────────────")
alm = chart.almuten_figuris()
print(f"  Winner: {alm['almuten_figuris']} (score {alm['top_score']})")
print(f"  Day ruler: {alm['day_ruler']}, Hour ruler: {alm['hour_ruler']}")
print(f"  Top 3: ", end="")
for p, s in sorted(alm["scores"].items(), key=lambda x: -x[1])[:3]:
    print(f"{p}={s}  ", end="")
print()

# ── Jyotish ───────────────────────────────────────────────────────────────

print()
print("────────────── Jyotish / Vedic ────────────────────────────────────")

# Nakshatra chart
nak = chart.nakshatra_chart(ayanamsha_mode="lahiri")
print("  Nakshatras:")
for key in ["sun", "moon"]:
    n = nak[key]
    print(f"    {key:10s}: {n['name']:20s} pada {n['pada']}  ({n['lord']})")

# Vimshottari Dasha at age 20
dasha = chart.vimshottari_dasha(age=20.35, ayanamsha_mode="lahiri", max_level=2)
for key in ["mahadasha", "antardasha"]:
    entry = dasha[key]
    lord = entry.get("mahadasha_lord", entry.get("lord", "?"))
    print(f"    {key:12s}: {lord:8s}  "
          f"≈{entry['start_age']:.1f}–{entry['end_age']:.1f}y  "
          f"({entry['duration_years']:.1f}y)")

# Ashtakavarga total
av = chart.ashtakavarga()
print(f"  Sarvashtakavarga total: {av['total_bindus']} (max 337)")

# ── Time utilities ────────────────────────────────────────────────────────

print()
print("────────────── Time & Calendar ────────────────────────────────────")

# EoT
jd = calendar_to_jd(2003, 3, 13, 6, 15, 0.0)  # birth UTC
eot = equation_of_time_minutes(jd)
print(f"  EoT at birth: {eot:+.2f} min (positive = sundial ahead)")

# Sunrise / sunset
times = sun_times(2003, 3, 13, lon_deg=118.49, lat_deg=37.45, tz=8.0)
def _local(jd_ut):
    y, m, d, h, mi, s = jd_to_calendar(jd_ut + 8/24)
    return f"{h:02d}:{mi:02d}"
print(f"  Sunrise: {_local(times['rise'])},  Sunset: {_local(times['set'])},  "
      f"Transit: {_local(times['transit'])}")

# New moons in March 2003
jd1 = calendar_to_jd(2003, 3, 1)
jd2 = calendar_to_jd(2003, 4, 1)
print("  New moons in March 2003:", end="")
for jd in new_moons_between(jd1, jd2):
    y, m, d, h, mi, s = jd_to_calendar(jd)
    print(f"  {d} {h:02d}:{mi:02d} UT", end="")
print()

# ── Meta ──────────────────────────────────────────────────────────────────

print()
print(f"UTC: {chart['date_utc']}  ·  ΔT: {chart['delta_t_s']:.1f}s  ·  "
      f"{chart['houses']['system']}")
