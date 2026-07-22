import math

# Constants
KJ2000_JD = 2451545.0
KJULIAN_CENTURY_DAYS = 36525.0
KMEAN_LUNAR_INCLINATION_RAD = 5.145396 * math.pi / 180.0
EARTH_MOON_MU_AU3_PER_DAY2 = 8.997011392947348e-10

def _normalize_radians(rad: float) -> float:
    return rad % (2.0 * math.pi)

def _eval_iers_2003_argument(jd_tt: float, c0: float, c1: float, c2: float, c3: float, c4: float) -> tuple[float, float]:
    """Returns (value_rad, rate_rad_per_day)"""
    t = (jd_tt - KJ2000_JD) / KJULIAN_CENTURY_DAYS
    val_arcsec = c0 + t * (c1 + t * (c2 + t * (c3 + t * c4)))
    rate_arcsec_cen = c1 + t * (2.0 * c2 + t * (3.0 * c3 + t * 4.0 * c4))
    
    val_rad = _normalize_radians(val_arcsec * (math.pi / (180.0 * 3600.0)))
    rate_rad_day = (rate_arcsec_cen * (math.pi / (180.0 * 3600.0))) / KJULIAN_CENTURY_DAYS
    return val_rad, rate_rad_day

def calc_mean_node_ecliptic_of_date(jd_tt: float) -> float:
    """Mean Node (Ascending) longitude in radians in the Mean Ecliptic of Date.
    (Since nutation is small, this is often used directly as Mean Node)."""
    val_rad, _ = _eval_iers_2003_argument(jd_tt, 450160.398036, -6962890.5431, 7.4722, 0.007702, -0.00005939)
    return val_rad

def calc_mean_apogee_ecliptic_of_date(jd_tt: float) -> float:
    """Mean Lilith (Mean Apogee) longitude in radians in the Mean Ecliptic of Date."""
    anomaly_val, _ = _eval_iers_2003_argument(jd_tt, 485868.249036, 1717915923.2178, 31.8792, 0.051635, -0.00024470)
    lat_arg_val, _ = _eval_iers_2003_argument(jd_tt, 335779.526232, 1739527262.8478, -12.7512, -0.001037, 0.00000417)
    node_val, _ = _eval_iers_2003_argument(jd_tt, 450160.398036, -6962890.5431, 7.4722, 0.007702, -0.00005939)
    
    argument = _normalize_radians(lat_arg_val - anomaly_val + math.pi)
    
    sin_node = math.sin(node_val)
    cos_node = math.cos(node_val)
    sin_arg = math.sin(argument)
    cos_arg = math.cos(argument)
    cos_inc = math.cos(KMEAN_LUNAR_INCLINATION_RAD)
    
    x = cos_node * cos_arg - sin_node * sin_arg * cos_inc
    y = sin_node * cos_arg + cos_node * sin_arg * cos_inc
    
    return _normalize_radians(math.atan2(y, x))

def calc_true_node_and_lilith(moon_pos: tuple[float, float, float], moon_vel: tuple[float, float, float]) -> tuple[float, float]:
    """
    Given Moon's position and velocity in Ecliptic of Date, returns (true_node_rad, true_lilith_rad).
    pos and vel must be in AU and AU/day.
    """
    x, y, z = moon_pos
    vx, vy, vz = moon_vel
    
    # Angular momentum H = r x v
    hx = y * vz - z * vy
    hy = z * vx - x * vz
    hz = x * vy - y * vx
    
    # Node vector in ecliptic plane (intersect of orbital plane with ecliptic)
    # N = (-Hy, Hx, 0) for Ascending Node
    nx = -hy
    ny = hx
    
    true_node_rad = _normalize_radians(math.atan2(ny, nx))
    
    # Eccentricity vector e = (v x H) / mu - (r / |r|)
    r_mag = math.sqrt(x*x + y*y + z*z)
    
    v_cross_hx = vy * hz - vz * hy
    v_cross_hy = vz * hx - vx * hz
    v_cross_hz = vx * hy - vy * hx
    
    ex = (v_cross_hx / EARTH_MOON_MU_AU3_PER_DAY2) - (x / r_mag)
    ey = (v_cross_hy / EARTH_MOON_MU_AU3_PER_DAY2) - (y / r_mag)
    ez = (v_cross_hz / EARTH_MOON_MU_AU3_PER_DAY2) - (z / r_mag)
    
    # Apogee is opposite to pericenter (eccentricity vector points to pericenter)
    ax = -ex
    ay = -ey
    
    true_lilith_rad = _normalize_radians(math.atan2(ay, ax))
    
    return true_node_rad, true_lilith_rad
