"""Demo — 2003-03-13 14:15 UTC+8, 山东东营"""

from lunaeph import calculate_chart, HouseSystem

chart = calculate_chart(
    2003, 3, 13,           # 年月日
    14, 15, 0,             # 时分秒（本地时间）
    tz=8.0,                # UTC+8
    latitude_deg=37.45,    # 东营
    longitude_deg=118.49,
)

# === 命盘表格 ===

def fmt_angle(rad: float) -> str:
    """黄经 → 星座 度°分'"""
    from lunaeph._signs import sign_degree_minute
    s, d, m = sign_degree_minute(rad)
    return f"{s.abbrev} {d:2d}°{m:02d}'"

# 行星行
print("╔══════════════╤══════════════╤══════╤════╗")
print("║ Planet       │ Position     │ Sign │ H  ║")
print("╠══════════════╪══════════════╪══════╪════╣")

# 宫头映射：给黄经找所属宫位
cusps = [c["longitude_rad"] for c in chart["houses"]["cusps"]]
def house_of(lon_rad: float) -> int:
    for i in range(12):
        start = cusps[i]
        end = cusps[(i + 1) % 12]
        if start <= end:
            if start <= lon_rad < end:
                return i + 1
        else:  # wraps across 360°
            if lon_rad >= start or lon_rad < end:
                return i + 1
    return 12

order = ["sun","moon","mercury","venus","mars","jupiter","saturn","uranus","neptune","pluto"]
for key in order:
    p = chart.planet(key)
    pos = fmt_angle(p["longitude_rad"])
    h = house_of(p["longitude_rad"])
    print(f"║ {p['name']:12s} │ {pos:12s} │ {p['sign_abbrev']:4s} │ {h:2d} ║")

print("╠══════════════╪══════════════╪══════╪════╣")

# ASC & MC
asc = chart.ascendant
mc = chart.midheaven
print(f"║ ASC          │ {fmt_angle(asc['longitude_rad']):12s} │ {asc['sign_abbrev']:4s} │  1 ║")
print(f"║ MC           │ {fmt_angle(mc['longitude_rad']):12s} │ {mc['sign_abbrev']:4s} │ 10 ║")
print("╚══════════════╧══════════════╧══════╧════╝")

# === 宫位 ===
print()
print("╔══════╤══════════════╗")
print("║ Hous │ Cusp         ║")
print("╠══════╪══════════════╣")
for i in range(1, 13):
    c = chart.house_cusp(i)
    print(f"║ {i:4d} │ {fmt_angle(c['longitude_rad']):12s} ║")
print("╚══════╧══════════════╝")

# === 主要相位 ===
print()
print("╔══════════════╤══════════════╤══════════════════╤═══════╗")
print("║ Body 1       │ Body 2       │ Aspect           │  Orb  ║")
print("╠══════════════╪══════════════╪══════════════════╪═══════╣")
for a in chart["aspects"]:
    if a["major"]:
        b1 = chart.planet(a["body1"])["name"]
        b2 = chart.planet(a["body2"])["name"]
        print(f"║ {b1:12s} │ {b2:12s} │ {a['aspect']:16s} │ {a['orb_deg']:.2f}° ║")
print("╚══════════════╧══════════════╧══════════════════╧═══════╝")

# === 元信息 ===
print()
print(f"UTC: {chart['date_utc']}   ΔT: {chart['delta_t_s']:.1f}s   Houses: {chart['houses']['system']}")
