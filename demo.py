"""LunaEph demo — 2003-03-13 14:15 UTC+8, 山东东营"""

from lunaeph import calculate_chart, HouseSystem

chart = calculate_chart(
    2003, 3, 13, 14, 15, 0,
    tz=8.0,
    latitude_deg=37.45,
    longitude_deg=118.49,
    house_system=HouseSystem.PLACIDUS,
)


def fmt_angle(rad: float) -> str:
    from lunaeph._signs import sign_degree_minute
    s, d, m = sign_degree_minute(rad)
    return f"{s.abbrev} {d:2d}°{m:02d}'"


def house_of(lon_rad: float, cusps: list[dict]) -> int:
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

# ── Planets ──
print("┌──────────┬───────────────┬──────┬────┬────┐")
print("│ Planet   │ Position      │ Sign │ H  │ R  │")
print("├──────────┼───────────────┼──────┼────┼────┤")
order = ["sun", "moon", "mercury", "venus", "mars",
         "jupiter", "saturn", "uranus", "neptune", "pluto"]
for key in order:
    p = chart.planet(key)
    pos = fmt_angle(p["longitude_rad"])
    h = house_of(p["longitude_rad"], cusps)
    r = "℞" if p["retrograde"] else " "
    print(f"│ {p['name']:8s} │ {pos:13s} │ {p['sign_abbrev']:4s} │ {h:2d} │ {r}  │")

# ASC / MC
asc = chart.ascendant
mc = chart.midheaven
print("├──────────┼───────────────┼──────┼────┼────┤")
print(f"│ ASC      │ {fmt_angle(asc['longitude_rad']):13s} │ {asc['sign_abbrev']:4s} │  1 │    │")
print(f"│ MC       │ {fmt_angle(mc['longitude_rad']):13s} │ {mc['sign_abbrev']:4s} │ 10 │    │")
print("└──────────┴───────────────┴──────┴────┴────┘")

# ── Houses ──
print()
print("┌──────┬───────────────┐")
print("│ Hous │ Cusp          │")
print("├──────┼───────────────┤")
for i in range(1, 13):
    print(f"│ {i:4d} │ {fmt_angle(cusps[i-1]['longitude_rad']):13s} │")
print("└──────┴───────────────┘")

# ── Aspects ──
print()
print("┌──────────┬──────────┬──────────────────┬───────┬──────┐")
print("│ Body 1   │ Body 2   │ Aspect           │  Orb  │ A/S  │")
print("├──────────┼──────────┼──────────────────┼───────┼──────┤")
for a in chart["aspects"]:
    if a.get("major"):
        b1 = chart.planet(a["body1"])["name"]
        b2 = chart.planet(a["body2"])["name"]
        arrow = "→" if a.get("applying") else "←"
        print(f"│ {b1:8s} │ {b2:8s} │ {a['aspect']:16s} │ {a['orb_deg']:.2f}° │ {arrow}    │")
print("└──────────┴──────────┴──────────────────┴───────┴──────┘")

# ── Meta ──
print()
print(f"UTC: {chart['date_utc']}  ·  ΔT: {chart['delta_t_s']:.1f}s  ·  {chart['houses']['system']}")
