"""Oracle tests for _time and _precession modules.

All oracles are sourced from taiyin-ephemeris C++ tests:
  tests/test_time_angle_interpolation.cpp  — deltaT year + JD oracles
  tests/test_coordinates.cpp               — nutation + earth rotation oracles
  tests/test_pure_functions_full.cpp       — Vondrak 2011 matrix oracles

Tolerance is kept at 1e-10 (double-precision oracle match).
"""

import math
import unittest

from lunaeph import _time
from lunaeph import _precession


def _rad_to_deg(rad: float) -> float:
    return rad * 180.0 / math.pi


class DeltaTYearOracleTests(unittest.TestCase):
    """Oracle table ported from test_time_angle_interpolation.cpp:362-389."""

    ORACLES = [
        # (year_decimal, expected_delta_t_seconds)
        (-1000.0,        25427.68),
        (-720.0,         20371.848),
        (-719.5,         20363.7843227998),
        (-100.0,         11557.668),
        (0.0,            10441.312575999998),
        (399.999,        6535.125452533171),
        (400.0,          6535.116),
        (1000.0,         1650.393),
        (1150.0,         1056.647),
        (1500.0,         292.343),
        (1600.0,         109.127),
        (1800.0,         18.367),
        (1850.0,         9.338),
        (1900.0,         -1.977),
        (1952.999,       30.00175459878804),
        (1953.0,         30.0),
        (1953.25,        30.049765625),
        (1961.5,         33.486875),
        (1972.5,         42.765625),
        (2000.0,         63.83),
        (2016.5,         68.35),
        (2024.25,        69.171171875),
        (2049.5,         71.329375),
        (2050.0,         71.44),
        (2050.5,         72.56600000000005),
        (2100.0,         191.95999999999998),
        (2200.0,         442.08),
    ]

    def test_delta_t_year_oracles(self):
        for year_dec, expected in self.ORACLES:
            with self.subTest(year=year_dec):
                actual = _time.delta_t_seconds_from_decimal_year(year_dec)
                self.assertAlmostEqual(actual, expected, delta=1e-10)


class DeltaTJDOracleTests(unittest.TestCase):
    """JD-based oracles from test_time_angle_interpolation.cpp:399-405."""

    def test_delta_t_from_ut1_jd(self):
        # Modern-era oracles — tight tolerance
        modern = [
            (_time.JD_J2000,                          63.83042335736016),
            (2460409.5,                               69.17035296181177),
            (2460409.262037037,                       69.17037911418967),
            (2448001.75,                              57.06055072295038),
        ]
        for jd_ut1, expected in modern:
            with self.subTest(jd=jd_ut1):
                actual = _time.delta_t_seconds_from_jd_ut1(jd_ut1)
                self.assertAlmostEqual(actual, expected, delta=1e-10)

        # JD 2086302.5 ≈ year 1000 — must use Julian leap-year rules
        actual = _time.delta_t_seconds_from_jd_ut1(2086302.5)
        self.assertAlmostEqual(actual, 1650.4617878426973, delta=1e-10)

    def test_delta_t_from_tt_jd(self):
        cases = [
            (_time.JD_J2000,                          63.830422732032133),
            (2460409.262837778,                       69.17037911417232),
        ]
        for jd_tt, expected in cases:
            with self.subTest(jd=jd_tt):
                actual = _time.delta_t_seconds_from_decimal_year(
                    _time.decimal_year_from_jd(
                        _time.jd_tt_to_ut1(jd_tt)))
                # TT-based deltaT is approximate; the oracle itself uses one
                # iterative step.  Allow a small tolerance.
                self.assertAlmostEqual(actual, expected, delta=1e-9)


class NutationOracleTests(unittest.TestCase):
    """IAU2000B nutation oracles from test_coordinates.cpp:175-179.

    Each oracle: jd_tt, (dpsi_rad, deps_rad, mean_obliquity_rad, true_obliquity_rad).
    """

    ORACLES = [
        (
            2451545.0,
            (-0.000067542612539922361, -0.000027970923310985653,
             0.40909260060058289,       0.40906462967727192),
        ),
        (
            2460000.0,
            (-0.000044811878657808338,  0.000037607177053908570,
             0.40904003706375935,       0.40907764424081328),
        ),
        (
            2415020.5,
            ( 0.000084518702696893369, -0.000011103153586824906,
             0.40931965795344111,       0.40930855479985429),
        ),
    ]

    def test_iau2000b_nutation_oracles(self):
        for jd_tt, (edpsi, edeps, emean, etrue) in self.ORACLES:
            with self.subTest(jd=jd_tt):
                nut = _precession.iau2000b_nutation_angles(jd_tt)
                self.assertAlmostEqual(nut["dpsi_rad"], edpsi, delta=1e-14)
                self.assertAlmostEqual(nut["deps_rad"], edeps, delta=1e-14)
                self.assertAlmostEqual(
                    nut["mean_obliquity_rad"], emean, delta=1e-14)
                self.assertAlmostEqual(
                    nut["true_obliquity_rad"], etrue, delta=1e-14)

    def test_mean_obliquity_matches_iau2006(self):
        """IAU2006 mean obliquity polynomial vs nutation oracle."""
        for jd_tt, (_, _, emean, _) in self.ORACLES:
            with self.subTest(jd=jd_tt):
                actual = _precession.mean_obliquity_rad(jd_tt)
                self.assertAlmostEqual(actual, emean, delta=1e-14)

    def test_nutation_matrix_orthonormal(self):
        """Nutation rotation matrix must be orthonormal (R·Rᵀ = I)."""
        nut = _precession.iau2000b_nutation_angles(2451545.0)
        mean = nut["mean_obliquity_rad"]
        dpsi = nut["dpsi_rad"]

        m = _precession._3x3_multiply(
            _precession._3x3_multiply(
                _precession._rotation_x(-mean),
                _precession._rotation_z(-dpsi),
            ),
            _precession._rotation_x(mean),
        )
        mt = tuple(
            tuple(m[j][i] for j in range(3)) for i in range(3)
        )
        prod = _precession._3x3_multiply(m, mt)
        identity = (
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
        )
        for i in range(3):
            for j in range(3):
                with self.subTest(i=i, j=j):
                    self.assertAlmostEqual(prod[i][j], identity[i][j], delta=1e-14)


class EarthRotationOracleTests(unittest.TestCase):
    """ERA / GMST oracles from test_coordinates.cpp:221-227."""

    ORACLES = [
        # (jd_ut1,              jd_tt,              era_rad,              gmst_rad)
        (2451545.0,             2451545.0,           4.894961212823756,    4.8949612831508285),
        (2460000.0,             2460000.0008,        5.826127456378991,    5.831303984358957),
        (2440000.0,             2440000.0007,        1.0745425392021062,   1.0674755105895786),
        (2460409.26203588,      2460409.262837778,   1.9463758662917954,   1.9518029776572094),
        (2448001.749997685,     2448001.750661852,   5.204380593691198,    5.20221157346126),
        (2457754.5000046296,    2457754.500800741,   1.7561815779592962,   1.7599832590147506),
    ]

    def test_era_oracles(self):
        for jd_ut1, _, era_exp, _ in self.ORACLES:
            with self.subTest(jd=jd_ut1):
                actual = _time._earth_rotation_angle_rad(jd_ut1)
                self.assertAlmostEqual(actual, era_exp, delta=1e-9)

    def test_gmst_oracles(self):
        for jd_ut1, jd_tt, _, gmst_exp in self.ORACLES:
            with self.subTest(jd=jd_ut1):
                actual = _time.gmst_rad(jd_ut1, jd_tt)
                self.assertAlmostEqual(actual, gmst_exp, delta=1e-9)

    def test_gmst_minus_era_oracles(self):
        """GMST – ERA matches for each oracle."""
        for jd_ut1, jd_tt, era_exp, gmst_exp in self.ORACLES:
            with self.subTest(jd=jd_ut1):
                gmst_minus_era = (
                    (gmst_exp - era_exp)
                    + (2.0 * math.pi if gmst_exp < era_exp else 0.0)
                ) % (2.0 * math.pi)
                # Normalize signed
                if gmst_minus_era > math.pi:
                    gmst_minus_era -= 2.0 * math.pi
                actual = _time._gmst_minus_era_rad(jd_tt)
                self.assertAlmostEqual(actual, gmst_minus_era, delta=1e-9)


class Vondrak2011OracleTests(unittest.TestCase):
    """Vondrak 2011 matrix oracles from test_pure_functions_full.cpp:177-193."""

    ORACLES = [
        (
            2451545.0,
            (
                ( 1.0000000000000000, -7.0782797432736689e-8,  8.0561489398790301e-8),
                ( 7.0782797433127277e-8,  1.0000000000000000,  3.3055566297944602e-8),
                (-8.0561489398447120e-8, -3.3055566297944596e-8, 1.0000000000000000),
            ),
        ),
        (
            2460000.0,
            (
                ( 0.99998407267080236, -0.0051765046329333838, -0.0022490452445638656),
                ( 0.0051765047729521365, 0.99998660179283250, -5.7588872958970894e-6),
                ( 0.0022490449222988557, -5.8833978765631683e-6, 0.99999747087796709),
            ),
        ),
        (
            1219339.078000,
            (
                ( 0.68473393269150270,  0.66647787827593630,  0.29486722298289560),
                (-0.66669476097832980,  0.73625641556112600, -0.11595079227472853),
                (-0.29437652267952263, -0.11719099075396050,  0.94847706065103420),
            ),
        ),
    ]

    def test_vondrak_matrix_oracles(self):
        for jd_tt, expected_matrix in self.ORACLES:
            with self.subTest(jd=jd_tt):
                actual, _ = _precession.vondrak2011_precession_matrix(jd_tt)
                for i in range(3):
                    for j in range(3):
                        with self.subTest(i=i, j=j):
                            self.assertAlmostEqual(
                                actual[i][j], expected_matrix[i][j],
                                delta=2e-14)


class J2000ToDateRoundtripTests(unittest.TestCase):
    """Ecliptic coordinate conversion tests."""

    def test_at_j2000_near_identity(self):
        """J2000 ecliptic → date at J2000 epoch should differ only by nutation."""
        jd = 2451545.0  # J2000
        v = (1.0, 0.0, 0.0)  # equinox direction
        v_date = _precession.j2000_ecliptic_to_date(v, jd)
        # Should be very close to (1, 0, 0)
        self.assertAlmostEqual(v_date[0], 1.0, delta=1e-7)
        self.assertAlmostEqual(v_date[1], 0.0, delta=1e-4)  # ~dpsi
        self.assertAlmostEqual(v_date[2], 0.0, delta=2e-7)

    def test_j2000_to_date_longitude(self):
        """Known ecliptic longitude shift from J2000 to 2026.

        The current equinox drifts WESTWARD on the ecliptic, so the
        fixed J2000 equinox direction appears at a small POSITIVE
        longitude in the true-ecliptic-of-date frame.
        """
        jd = _time.calendar_to_jd(2026, 7, 22, 14, 30, 0)
        jd_tt = _time.jd_ut1_to_tt(jd)

        # J2000 equinox (lon=0) → date at 2026 should be ~+0.37°
        lon, lat, r = _precession.j2000_ecliptic_longitude_to_date(
            0.0, 0.0, 1.0, jd_tt)
        self.assertAlmostEqual(math.degrees(lon), 0.373, delta=0.01)


class EquationOfEquinoxesTests(unittest.TestCase):
    """Equation of equinoxes sanity checks."""

    def test_eqeq_j2000(self):
        """EqEq at J2000 should be ~12.8 arcsec."""
        eqeq = _precession.equation_of_equinoxes_rad(2451545.0)
        arcsec = eqeq * 206264.80624709636
        self.assertAlmostEqual(arcsec, -12.8, delta=0.2)

    def test_gast_equals_gmst_plus_eqeq(self):
        """GAST = GMST + EqEq."""
        jd_tt = 2451545.0
        jd_ut1 = 2451545.0
        gmst = _time.gmst_rad(jd_ut1, jd_tt)
        eqeq = _precession.equation_of_equinoxes_rad(jd_tt)
        gast = _time.gast_rad(jd_ut1, jd_tt, eqeq)
        self.assertAlmostEqual(
            gast, (gmst + eqeq) % (2.0 * math.pi), delta=1e-14)


if __name__ == "__main__":
    unittest.main()
