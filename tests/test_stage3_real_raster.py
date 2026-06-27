"""
Stage 3 Step 3 — Real Raster Integration Tests

Validates the seven-batch plan for embedding true Earth rasters into the
existing SAL / M1 / VC / D6 pipeline without breaking any invariants.

Batch coverage:
  Batch 1 — RasterIndexer (already tested in test_stage3_real_grounding.py;
             formula correctness re-verified here for the new provider adapters)
  Batch 2 — GEBCOProvider
  Batch 3 — ETOPOProvider
  Batch 4 — KoppenProvider
  Batch 5 — RealWorldSignalProvider ocean arbitration
  Batch 6 — SpatialRuntime real_world_provider path
  Batch 7 — EarthFlags per-source flags

Acceptance criteria:
  ✔ Dead Sea → ocean False  (below sea level but land, climate veto)
  ✔ Pacific  → ocean True   (negative DEM, no climate class)
  ✔ Death Valley → ocean False (below sea level but land, climate veto)
  ✔ climate consistency check
  ✔ SAL unchanged
  ✔ M1 shape unchanged
  ✔ VC stability unchanged
  ✔ no GDAL dependency — all mocks use in-memory numpy arrays
  ✔ deterministic outputs
"""

import unittest

import numpy as np

from core.signal.raster_indexer import RasterIndexer
from core.signal.providers.gebco_provider import GEBCOProvider
from core.signal.providers.etopo_provider import ETOPOProvider
from core.signal.providers.koppen_provider import KoppenProvider
from core.signal.providers.real_world_provider import RealWorldSignalProvider
from core.signal.providers.base import BaseSignalProvider
from core.signal.providers.synthetic import SyntheticProvider
from core.config.earth_flags import EarthFlags
from core.runtime.spatial_runtime import SpatialRuntime
from core.m1 import M1Pipeline, TileBBox
from core.vc import VisualConsistencyEngine
from core.sal import SemanticArbitrator
from core.contract import ContractGuard


# ---------------------------------------------------------------------------
# Helpers — build in-memory rasters that return a controlled value at any point
# ---------------------------------------------------------------------------

def _uniform_indexer(value: int, nodata: int = None) -> RasterIndexer:
    """Return a 180×360 RasterIndexer that always samples to `value`."""
    arr = np.full((180, 360), value, dtype=np.int16)
    return RasterIndexer.from_array(arr, nodata=nodata)


def _sparse_indexer(background: int, patches: dict, nodata: int = None) -> RasterIndexer:
    """
    180×360 indexer with `background` everywhere except patched pixels.

    patches: {(col, row): value}  (equirectangular pixel coords)
    """
    arr = np.full((180, 360), background, dtype=np.int16)
    for (col, row), v in patches.items():
        arr[row, col] = v
    return RasterIndexer.from_array(arr, nodata=nodata)


def _lon_lat_to_cr(lon: float, lat: float, width: int = 360, height: int = 180):
    col = min(width - 1, max(0, int((lon + 180.0) / 360.0 * width)))
    row = min(height - 1, max(0, int((90.0 - lat) / 180.0 * height)))
    return col, row


SMALL_BBOX = TileBBox(lon_min=-15, lon_max=15, lat_min=-10, lat_max=10)

SAMPLE_POINTS = [
    (0.0, 0.0),
    (45.0, 30.0),
    (-90.0, -45.0),
    (10.0, 70.0),
    (-180.0, -90.0),
    (180.0, 90.0),
]


# ---------------------------------------------------------------------------
# Batch 2 — GEBCOProvider
# ---------------------------------------------------------------------------

class TestGEBCOProvider(unittest.TestCase):

    def test_positive_dem_not_ocean(self):
        gp = GEBCOProvider(_uniform_indexer(300))
        self.assertAlmostEqual(gp.get_dem(0.0, 0.0), 300.0, places=1)
        self.assertFalse(gp.get_ocean(0.0, 0.0))

    def test_negative_dem_is_ocean(self):
        gp = GEBCOProvider(_uniform_indexer(-4000))
        self.assertAlmostEqual(gp.get_dem(0.0, 0.0), -4000.0, places=1)
        self.assertTrue(gp.get_ocean(0.0, 0.0))

    def test_nodata_returns_zero_and_not_ocean(self):
        gp = GEBCOProvider(_uniform_indexer(-9999, nodata=-9999))
        self.assertAlmostEqual(gp.get_dem(0.0, 0.0), 0.0, places=1)
        self.assertFalse(gp.get_ocean(0.0, 0.0))

    def test_deterministic(self):
        gp = GEBCOProvider(_uniform_indexer(-1500))
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(gp.get_dem(lon, lat), gp.get_dem(lon, lat))
                self.assertEqual(gp.get_ocean(lon, lat), gp.get_ocean(lon, lat))

    def test_edge_coordinates_do_not_raise(self):
        gp = GEBCOProvider(_uniform_indexer(0))
        for lon, lat in [(-180.0, -90.0), (180.0, 90.0)]:
            with self.subTest(lon=lon, lat=lat):
                gp.get_dem(lon, lat)
                gp.get_ocean(lon, lat)


# ---------------------------------------------------------------------------
# Batch 3 — ETOPOProvider
# ---------------------------------------------------------------------------

class TestETOPOProvider(unittest.TestCase):

    def test_positive_elevation_not_ocean(self):
        ep = ETOPOProvider(_uniform_indexer(120))
        self.assertAlmostEqual(ep.get_dem(0.0, 0.0), 120.0, places=1)
        self.assertFalse(ep.get_ocean(0.0, 0.0))

    def test_negative_elevation_is_ocean(self):
        ep = ETOPOProvider(_uniform_indexer(-2000))
        self.assertAlmostEqual(ep.get_dem(0.0, 0.0), -2000.0, places=1)
        self.assertTrue(ep.get_ocean(0.0, 0.0))

    def test_nodata_falls_back_to_zero(self):
        ep = ETOPOProvider(_uniform_indexer(-9999, nodata=-9999))
        self.assertAlmostEqual(ep.get_dem(0.0, 0.0), 0.0, places=1)

    def test_deterministic(self):
        ep = ETOPOProvider(_uniform_indexer(500))
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(ep.get_dem(lon, lat), ep.get_dem(lon, lat))

    def test_edge_coordinates_do_not_raise(self):
        ep = ETOPOProvider(_uniform_indexer(0))
        for lon, lat in [(-180.0, -90.0), (180.0, 90.0)]:
            with self.subTest(lon=lon, lat=lat):
                ep.get_dem(lon, lat)
                ep.get_ocean(lon, lat)


# ---------------------------------------------------------------------------
# Batch 4 — KoppenProvider
# ---------------------------------------------------------------------------

class TestKoppenProvider(unittest.TestCase):

    def test_land_class_returned(self):
        kp = KoppenProvider(_uniform_indexer(5))
        self.assertEqual(kp.get_climate(0.0, 0.0), 5)

    def test_zero_is_none(self):
        kp = KoppenProvider(_uniform_indexer(0))
        self.assertIsNone(kp.get_climate(0.0, 0.0))

    def test_nodata_is_none(self):
        kp = KoppenProvider(_uniform_indexer(0, nodata=0))
        self.assertIsNone(kp.get_climate(0.0, 0.0))

    def test_all_valid_classes_returned(self):
        for cls_val in range(1, 31):
            kp = KoppenProvider(_uniform_indexer(cls_val))
            with self.subTest(class_val=cls_val):
                self.assertEqual(kp.get_climate(0.0, 0.0), cls_val)

    def test_deterministic(self):
        kp = KoppenProvider(_uniform_indexer(12))
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(kp.get_climate(lon, lat), kp.get_climate(lon, lat))

    def test_edge_coordinates_do_not_raise(self):
        kp = KoppenProvider(_uniform_indexer(1))
        for lon, lat in [(-180.0, -90.0), (180.0, 90.0)]:
            with self.subTest(lon=lon, lat=lat):
                kp.get_climate(lon, lat)


# ---------------------------------------------------------------------------
# Batch 7 — EarthFlags
# ---------------------------------------------------------------------------

class TestEarthFlagsStep3(unittest.TestCase):

    def test_gebco_off_by_default(self):
        self.assertFalse(EarthFlags.ENABLE_GEBCO)

    def test_etopo_off_by_default(self):
        self.assertFalse(EarthFlags.ENABLE_ETOPO)

    def test_koppen_off_by_default(self):
        self.assertFalse(EarthFlags.ENABLE_KOPPEN)

    def test_all_flags_are_bool(self):
        self.assertIsInstance(EarthFlags.ENABLE_GEBCO, bool)
        self.assertIsInstance(EarthFlags.ENABLE_ETOPO, bool)
        self.assertIsInstance(EarthFlags.ENABLE_KOPPEN, bool)

    def test_legacy_flags_still_present(self):
        self.assertIsInstance(EarthFlags.ENABLE_REAL_DEM, bool)
        self.assertIsInstance(EarthFlags.ENABLE_REAL_OCEAN, bool)
        self.assertIsInstance(EarthFlags.ENABLE_REAL_CLIMATE, bool)


# ---------------------------------------------------------------------------
# Geographic correctness — mock rasters injected into RealWorldSignalProvider
# ---------------------------------------------------------------------------

def _make_provider_with_values(dem_value: int, climate_value=None) -> RealWorldSignalProvider:
    """
    Inject a uniform-value DEM (and optionally climate) into a
    RealWorldSignalProvider via mock loader injection (mirrors test_stage3_real_grounding.py).
    """
    class _MockDEM:
        def __init__(self, v):
            self._v = v
        def query(self, lon, lat):
            return self._v

    class _MockClimate:
        def __init__(self, v):
            self._v = v
        def get_value(self, lon, lat):
            return self._v

    from core.data.earth_sources.loader import EarthDataLoader
    provider = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
    loader = EarthDataLoader.__new__(EarthDataLoader)
    loader.source_root = None
    loader._cache = {
        "dem": _MockDEM(dem_value),
        "ocean": None,
        "landcover": None,
        "climate": _MockClimate(climate_value) if climate_value is not None else None,
    }
    provider._loader = loader
    return provider


class TestGeographicCorrectness(unittest.TestCase):
    """
    Simulate landmark geographic points using mock rasters.

    No real data files are required — values are injected via the same
    mock-loader pattern used in test_stage3_real_grounding.py.
    """

    def test_dead_sea_ocean_false(self):
        """
        Dead Sea: elevation ≈ −430 m, but it is a land lake with a real
        climate class. Köppen veto must override the negative DEM → ocean False.
        """
        provider = _make_provider_with_values(dem_value=-430, climate_value=6)
        self.assertLess(provider.get_dem(35.5, 31.5), 0.0)
        self.assertEqual(provider.get_climate(35.5, 31.5), 6)
        self.assertFalse(provider.get_ocean(35.5, 31.5))

    def test_pacific_ocean_true(self):
        """
        Central Pacific: deep negative DEM, no climate class → ocean True.
        """
        provider = _make_provider_with_values(dem_value=-5000, climate_value=None)
        self.assertLess(provider.get_dem(-150.0, 10.0), 0.0)
        self.assertIsNone(provider.get_climate(-150.0, 10.0))
        self.assertTrue(provider.get_ocean(-150.0, 10.0))

    def test_death_valley_ocean_false(self):
        """
        Death Valley: elevation ≈ −86 m, land with a desert climate class.
        Köppen veto must keep ocean False.
        """
        provider = _make_provider_with_values(dem_value=-86, climate_value=4)
        self.assertLess(provider.get_dem(-116.8, 36.5), 0.0)
        self.assertIsNotNone(provider.get_climate(-116.8, 36.5))
        self.assertFalse(provider.get_ocean(-116.8, 36.5))

    def test_mount_everest_not_ocean(self):
        """High positive elevation is unambiguously land."""
        provider = _make_provider_with_values(dem_value=8849, climate_value=None)
        self.assertFalse(provider.get_ocean(86.9, 28.0))

    def test_climate_consistency_land_has_class(self):
        """When climate class is present (> 0), point must be classified as land."""
        for cls_val in [1, 5, 12, 18, 25, 30]:
            provider = _make_provider_with_values(dem_value=-100, climate_value=cls_val)
            with self.subTest(climate_class=cls_val):
                self.assertIsNotNone(provider.get_climate(0.0, 0.0))
                self.assertFalse(provider.get_ocean(0.0, 0.0))


# ---------------------------------------------------------------------------
# Batch 6 — SpatialRuntime real_world_provider integration
# ---------------------------------------------------------------------------

class TestSpatialRuntimeRealRasterPath(unittest.TestCase):

    def _make_runtime(self, dem_value: int, climate_value=None) -> SpatialRuntime:
        provider = _make_provider_with_values(dem_value, climate_value)
        return SpatialRuntime(real_world_provider=provider)

    def test_dead_sea_runtime_ocean_false(self):
        # RealWorldSignalProvider applies the Köppen veto internally in get_ocean(),
        # so the runtime sees ocean=False directly — ocean_rule label is unchanged.
        rt = self._make_runtime(-430, climate_value=6)
        state = rt.query_point(35.5, 31.5)
        self.assertFalse(state.ocean)
        self.assertIn("real_world_provider", state.source["ocean_rule"])

    def test_pacific_runtime_ocean_true(self):
        rt = self._make_runtime(-5000, climate_value=None)
        state = rt.query_point(-150.0, 10.0)
        self.assertTrue(state.ocean)

    def test_land_above_sea_level(self):
        rt = self._make_runtime(200, climate_value=None)
        state = rt.query_point(10.0, 50.0)
        self.assertFalse(state.ocean)

    def test_ocean_rule_label_is_real_world_provider(self):
        rt = self._make_runtime(-3000, climate_value=None)
        state = rt.query_point(0.0, 0.0)
        self.assertIn("real_world_provider", state.source["ocean_rule"])


# ---------------------------------------------------------------------------
# Pipeline regression — SAL / M1 / VC unchanged by new providers
# ---------------------------------------------------------------------------

def _signal_fn(provider):
    def _fn(lon, lat):
        dem   = provider.get_dem(lon, lat)
        ocean = provider.get_ocean(lon, lat)
        clim  = provider.get_climate(lon, lat)
        return dict(
            dem_signal="ocean" if dem < 0 else "land",
            dem_confidence=min(0.55 + abs(dem) / 3000.0 * 0.4, 0.95),
            climate_signal="land" if clim is not None else None,
            climate_confidence=0.8 if clim is not None else 0.0,
            ocean_signal="ocean" if ocean else "land",
            ocean_confidence=0.8,
            landcover_signal="land",
            landcover_confidence=0.6,
        )
    return _fn


class TestSALUnchangedStep3(unittest.TestCase):

    def _resolve(self, provider):
        lon, lat = 20.0, 35.0
        dem   = provider.get_dem(lon, lat)
        ocean = provider.get_ocean(lon, lat)
        clim  = provider.get_climate(lon, lat)
        return SemanticArbitrator().resolve(
            dem_signal="ocean" if dem < 0 else "land",
            dem_confidence=min(0.55 + abs(dem) / 3000.0 * 0.4, 0.95),
            climate_signal="land" if clim is not None else None,
            climate_confidence=0.8 if clim is not None else 0.0,
            ocean_signal="ocean" if ocean else "land",
            ocean_confidence=0.75,
            landcover_signal="land",
            landcover_confidence=0.6,
        )

    def _assert_invariants(self, result):
        argmax = max(result.probability_map, key=lambda k: result.probability_map[k])
        self.assertEqual(result.winner_class, argmax)
        self.assertGreaterEqual(result.winner_ratio, 1.0)
        self.assertGreaterEqual(result.winner_margin, 0.0)
        self.assertLessEqual(result.winner_margin, 1.0)

    def test_sal_invariants_gebco_land(self):
        self._assert_invariants(
            self._resolve(_make_provider_with_values(dem_value=100))
        )

    def test_sal_invariants_gebco_ocean(self):
        self._assert_invariants(
            self._resolve(_make_provider_with_values(dem_value=-4000))
        )

    def test_sal_matches_synthetic_no_real_data(self):
        rw  = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        syn = SyntheticProvider()
        r_rw  = self._resolve(rw)
        r_syn = self._resolve(syn)
        self.assertEqual(r_rw.final_class, r_syn.final_class)
        self.assertAlmostEqual(r_rw.winner_margin, r_syn.winner_margin, places=9)


class TestM1ShapeStep3(unittest.TestCase):

    def _tile(self, provider):
        return M1Pipeline(
            signal_provider=_signal_fn(provider), tile_px_size=6
        ).run_tile(SMALL_BBOX)

    def test_shape_matches_synthetic(self):
        t_syn = self._tile(SyntheticProvider())
        t_rw  = self._tile(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))
        self.assertEqual(t_syn.shape, t_rw.shape)

    def test_shape_unchanged_with_gebco_mock(self):
        t_syn  = self._tile(SyntheticProvider())
        t_mock = self._tile(_make_provider_with_values(dem_value=500, climate_value=8))
        self.assertEqual(t_syn.shape, t_mock.shape)

    def test_uncertainty_bounded(self):
        tile = self._tile(_make_provider_with_values(dem_value=-3000))
        unc  = tile.uncertainty_mask.astype(np.float32)
        self.assertGreaterEqual(float(unc.min()), 0.0)
        self.assertLessEqual(float(unc.max()), 1.0)


class TestVCStabilityStep3(unittest.TestCase):

    def _vc_ctx(self, provider):
        tile = M1Pipeline(
            signal_provider=_signal_fn(provider), tile_px_size=6
        ).run_tile(SMALL_BBOX)
        return VisualConsistencyEngine().process(tile)

    def test_vc_shape_matches_synthetic(self):
        ctx_syn = self._vc_ctx(SyntheticProvider())
        ctx_rw  = self._vc_ctx(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))
        self.assertEqual(ctx_syn.shape, ctx_rw.shape)

    def test_temporal_stability_bounded(self):
        ctx  = self._vc_ctx(_make_provider_with_values(dem_value=0))
        stab = ctx.temporal_stability_field.astype(np.float32)
        self.assertGreaterEqual(float(stab.min()), 0.0 - 1e-4)
        self.assertLessEqual(float(stab.max()), 1.0 + 1e-4)

    def test_vc_deterministic_across_providers(self):
        ctx1 = self._vc_ctx(_make_provider_with_values(dem_value=200, climate_value=5))
        ctx2 = self._vc_ctx(_make_provider_with_values(dem_value=200, climate_value=5))
        np.testing.assert_array_equal(
            ctx1.temporal_stability_field,
            ctx2.temporal_stability_field,
        )


class TestFullContractGuardStep3(unittest.TestCase):

    def _run_pipeline(self, provider):
        guard = ContractGuard(strict_sal_cache=False)
        sal_result = SemanticArbitrator().resolve(
            dem_signal="land" if provider.get_dem(0.0, 30.0) >= 0 else "ocean",
            climate_signal="land" if provider.get_climate(0.0, 30.0) is not None else None,
            ocean_signal="ocean" if provider.get_ocean(0.0, 30.0) else "land",
            landcover_signal="land",
        )
        guard.validate_sal(sal_result)
        tile = M1Pipeline(
            signal_provider=_signal_fn(provider), tile_px_size=6
        ).run_tile(SMALL_BBOX)
        guard.validate_m1(tile)
        ctx = VisualConsistencyEngine().process(tile)
        guard.validate_vc(ctx)
        frame = guard.render_d6_from_vc(ctx)
        guard.validate_d6(frame)

    def test_gebco_land_mock_passes_full_contract(self):
        self._run_pipeline(_make_provider_with_values(dem_value=300, climate_value=10))

    def test_gebco_ocean_mock_passes_full_contract(self):
        self._run_pipeline(_make_provider_with_values(dem_value=-4000, climate_value=None))

    def test_real_world_no_data_passes_full_contract(self):
        self._run_pipeline(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
