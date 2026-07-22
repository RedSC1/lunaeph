"""House system oracle tests from taiyin C++ tests/test_houses_astrology.cpp.

Oracles are validated against Swiss Ephemeris at < 0.01 arcsec.
"""

import math
import unittest

from lunaeph._time import calendar_to_jd, jd_ut1_to_tt, gast_rad
from lunaeph._precession import iau2000b_nutation_angles, equation_of_equinoxes_rad
from lunaeph._houses import (
    HouseSystem,
    calc_houses,
    ascendant_rad,
    midheaven_rad,
    vertex_rad,
    east_point_rad,
    _gc_ecl_intersect as gc_ecl_intersect,
    _fill_quadrant,
)

# ---------------------------------------------------------------------------
# Swiss House Cases — ASC, MC, Vertex, East Point, Porphyry
# ---------------------------------------------------------------------------

_SWISS_HOUSE_CASES = [
    # (jd_ut, lat_deg, lon_deg, asc_deg, mc_deg, vertex_deg, ep_deg, porphyry[12])
    (
        2460311.0, 39.9167, 116.3833,
        137.955986373727, 39.424973002554, 275.514116285182, 124.685728170895,
        [137.955986373727, 165.112315250003, 192.268644126279, 219.424973002554,
         252.268644126279, 285.112315250003, 317.955986373727, 345.112315250003,
         12.268644126279, 39.424973002554, 72.268644126279, 105.112315250003],
    ),
    (
        2460482.5, 51.5074, -0.1276,
        358.934770200524, 269.592132878527, 179.639693640752, 359.515476779856,
        [358.934770200524, 29.153891093192, 59.373011985859, 89.592132878527,
         119.373011985859, 149.153891093192, 178.934770200524, 209.153891093192,
         239.373011985859, 269.592132878527, 299.373011985859, 329.153891093192],
    ),
    (
        2460311.0, 70.0, 0.0,
        315.981004600627, 279.783519001062, 190.009849336885, 11.576498989699,
        [315.981004600627, 3.915176067439, 51.849347534250, 99.783519001062,
         111.849347534250, 123.915176067439, 135.981004600627, 183.915176067439,
         231.849347534250, 279.783519001062, 291.849347534250, 303.915176067439],
    ),
]

# ---------------------------------------------------------------------------
# Swiss Placidus Cases
# ---------------------------------------------------------------------------

_SWISS_PLACIDUS_CASES = [
    (
        2460311.0, 39.9167, 116.3833,
        [137.955986373727, 159.905715838579, 186.829377344240, 219.424973002554,
         255.095673573944, 288.734504353569, 317.955986373727, 339.905715838579,
         6.829377344240, 39.424973002554, 75.095673573944, 108.734504353569],
    ),
    (
        2460482.5, 51.5074, -0.1276,
        [358.934770200524, 47.009824871508, 71.360142892116, 89.592132878527,
         107.745308151828, 131.764100163102, 178.934770200524, 227.009824871508,
         251.360142892116, 269.592132878527, 287.745308151828, 311.764100163102],
    ),
    (
        2460311.0, 65.0, 0.0,
        [75.230638668662, 86.334197484680, 93.082100179923, 99.783519001062,
         108.884006602794, 128.429626802114, 255.230638668662, 266.334197484680,
         273.082100179923, 279.783519001062, 288.884006602794, 308.429626802114],
    ),
]

# ---------------------------------------------------------------------------
# Pure geometry Placidus cases (ARMC → cusps, no GAST needed)
# ---------------------------------------------------------------------------

_SWISS_GEOMETRY_CASES = [
    # (armc_deg, lat_deg, obliquity_deg, cusps[12])
    (
        123.456, 39.9167, 23.436,
        [206.656040425304212, 234.691492433991698, 266.680535157863687, 301.227197185053740,
         334.384202778317672, 3.033100066811357, 26.656040425304241, 54.691492433991698,
         86.680535157863687, 121.227197185053740, 154.384202778317700, 183.033100066811357],
    ),
    (
        321.0, 65.0, 23.436,
        [109.520730098139978, 115.864458747021544, 124.643846626840386, 138.568579949071420,
         165.839339629716505, 235.249647239573562, 289.520730098140007, 295.864458747021558,
         304.643846626840400, 318.568579949071420, 345.839339629716505, 55.249647239573569],
    ),
]

# ---------------------------------------------------------------------------
# Additional house systems — quadrant cusp oracles
# ---------------------------------------------------------------------------

_ADDITIONAL_CASES = [
    # (system, armc_deg, lat_deg, obl_deg, c2_deg, c3_deg, c11_deg, c12_deg)
    (HouseSystem.KOCH,          123.456, 39.9167, 23.436,
     234.936776485515, 264.540999813118, 149.525868341525, 178.068623489599),
    (HouseSystem.REGIOMONTANUS, 123.456, 39.9167, 23.436,
     232.029664046312, 263.651016632266, 155.643965346680, 182.866290863818),
    (HouseSystem.CAMPANUS,      123.456, 39.9167, 23.436,
     238.684892427877, 271.036150663853, 149.252902070722, 177.029840838188),
    (HouseSystem.ALCABITIUS,    123.456, 39.9167, 23.436,
     239.826121268091, 270.502069098862, 148.389454658680, 177.426355568296),
    (HouseSystem.KOCH,          321.0,   65.0,    23.436,
     119.344913352104, 128.938230419202, 82.484343265263, 98.666577162776),
    (HouseSystem.REGIOMONTANUS, 321.0,   65.0,    23.436,
     121.070718502448, 128.972829527681, 341.940060281711, 71.787536792854),
    (HouseSystem.CAMPANUS,      321.0,   65.0,    23.436,
     127.358616102587, 133.614395141578, 325.751093387276, 353.257807002318),
    (HouseSystem.ALCABITIUS,    321.0,   65.0,    23.436,
     118.948482059822, 128.616543530730, 12.007366882351, 63.123405808513),
]

# tolerances
_TOL_ARCSEC_DEG = 0.01 / 3600.0   # 0.01 arcsec in degrees
_TOL_ASC_MC_DEG  = 0.01 / 3600.0


class SwissHouseCaseTests(unittest.TestCase):
    """ASC, MC, Vertex, East Point, Porphyry cusps."""

    def test_houses(self):
        for jd_ut, lat_d, lon_d, asc_d, mc_d, vx_d, ep_d, porph in _SWISS_HOUSE_CASES:
            with self.subTest(jd=jd_ut, lat=lat_d):
                jd_tt = jd_ut1_to_tt(jd_ut)
                nut = iau2000b_nutation_angles(jd_tt)
                eqeq = equation_of_equinoxes_rad(jd_tt)
                gast = gast_rad(jd_ut, jd_tt, eqeq)

                h = calc_houses(gast, math.radians(lon_d), math.radians(lat_d),
                                nut["true_obliquity_rad"], HouseSystem.PORPHYRY)

                self.assertAlmostEqual(math.degrees(h["ascendant_rad"]), asc_d,
                                       delta=_TOL_ASC_MC_DEG)
                self.assertAlmostEqual(math.degrees(h["midheaven_rad"]), mc_d,
                                       delta=_TOL_ASC_MC_DEG)
                self.assertAlmostEqual(math.degrees(h["vertex_rad"]), vx_d,
                                       delta=_TOL_ASC_MC_DEG)
                self.assertAlmostEqual(math.degrees(h["east_point_rad"]), ep_d,
                                       delta=_TOL_ASC_MC_DEG)
                for i in range(12):
                    with self.subTest(cusp=i):
                        self.assertAlmostEqual(
                            math.degrees(h["cusps_rad"][i]), porph[i],
                            delta=_TOL_ARCSEC_DEG)


class SwissPlacidusCaseTests(unittest.TestCase):
    """Full Placidus cusps via GAST→ARMC path."""

    def test_placidus(self):
        for jd_ut, lat_d, lon_d, expected in _SWISS_PLACIDUS_CASES:
            with self.subTest(jd=jd_ut, lat=lat_d):
                jd_tt = jd_ut1_to_tt(jd_ut)
                nut = iau2000b_nutation_angles(jd_tt)
                eqeq = equation_of_equinoxes_rad(jd_tt)
                gast = gast_rad(jd_ut, jd_tt, eqeq)

                h = calc_houses(gast, math.radians(lon_d), math.radians(lat_d),
                                nut["true_obliquity_rad"], HouseSystem.PLACIDUS)

                for i in range(12):
                    with self.subTest(cusp=i):
                        self.assertAlmostEqual(
                            math.degrees(h["cusps_rad"][i]), expected[i],
                            delta=_TOL_ARCSEC_DEG)


class SwissPlacidusGeometryTests(unittest.TestCase):
    """Placidus cusps from pure ARMC geometry (no deltaT/GAST path)."""

    def test_geometry(self):
        for armc_d, lat_d, obl_d, expected in _SWISS_GEOMETRY_CASES:
            with self.subTest(armc=armc_d):
                armc = math.radians(armc_d)
                lat = math.radians(lat_d)
                obl = math.radians(obl_d)
                asc = ascendant_rad(armc, obl, lat)
                mc = midheaven_rad(armc, obl)

                cusps = [0.0] * 12
                from lunaeph._houses import _eval_placidus
                ok = _eval_placidus(armc, obl, lat, asc, mc, cusps)
                self.assertTrue(ok)

                for i in range(12):
                    with self.subTest(cusp=i):
                        self.assertAlmostEqual(
                            math.degrees(cusps[i]), expected[i],
                            delta=_TOL_ARCSEC_DEG)


class AdditionalHouseSystemTests(unittest.TestCase):
    """Koch, Regiomontanus, Campanus, Alcabitius quadrant cusps."""

    _EVALS = {
        HouseSystem.KOCH: "koch",
        HouseSystem.REGIOMONTANUS: "regiomontanus",
        HouseSystem.CAMPANUS: "campanus",
        HouseSystem.ALCABITIUS: "alcabitius",
    }

    def test_additional(self):
        from lunaeph._houses import _EVALUATORS

        for system, armc_d, lat_d, obl_d, e2, e3, e11, e12 in _ADDITIONAL_CASES:
            with self.subTest(system=system.value, armc=armc_d):
                armc = math.radians(armc_d)
                lat = math.radians(lat_d)
                obl = math.radians(obl_d)
                asc = ascendant_rad(armc, obl, lat)
                mc = midheaven_rad(armc, obl)

                cusps = [0.0] * 12
                evaluator = _EVALUATORS.get(system)
                self.assertIsNotNone(evaluator)
                ok = evaluator(armc, obl, lat, asc, mc, cusps)
                self.assertTrue(ok)

                for i, expected in [(1, e2), (2, e3), (10, e11), (11, e12)]:
                    with self.subTest(cusp=i):
                        self.assertAlmostEqual(
                            math.degrees(cusps[i]), expected,
                            delta=_TOL_ARCSEC_DEG)


class WholeSignEqualTests(unittest.TestCase):
    """Whole Sign and Equal are trivial — basic sanity."""

    def test_equal(self):
        armc = math.radians(123.0)
        lat = math.radians(39.9)
        obl = math.radians(23.436)
        asc = ascendant_rad(armc, obl, lat)
        mc = midheaven_rad(armc, obl)

        cusps = [0.0] * 12
        from lunaeph._houses import _eval_equal
        _eval_equal(armc, obl, lat, asc, mc, cusps)
        # Equal: cusp[i+1] – cusp[i] = 30°
        for i in range(11):
            diff = math.degrees(cusps[i+1] - cusps[i]) % 360
            self.assertAlmostEqual(diff, 30.0, delta=0.001)

    def test_whole_sign(self):
        armc = math.radians(123.0)
        lat = math.radians(39.9)
        obl = math.radians(23.436)
        asc = ascendant_rad(armc, obl, lat)
        mc = midheaven_rad(armc, obl)

        cusps = [0.0] * 12
        from lunaeph._houses import _eval_whole_sign
        _eval_whole_sign(armc, obl, lat, asc, mc, cusps)
        # Whole Sign: cusp[0] starts at ASC's sign boundary
        asc_deg = math.degrees(asc)
        sign_start = int(asc_deg // 30) * 30
        self.assertAlmostEqual(math.degrees(cusps[0]), sign_start, delta=0.001)
        for i in range(11):
            diff = math.degrees(cusps[i+1] - cusps[i]) % 360
            self.assertAlmostEqual(diff, 30.0, delta=0.001)


if __name__ == "__main__":
    unittest.main()
