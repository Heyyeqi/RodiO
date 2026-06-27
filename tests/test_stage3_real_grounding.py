"""
Stage 3 Real World Grounding Tests

Verifies the seven Stage 3 batch additions:
  Batch 1 — RealWorldSignalProvider skeleton (lazy, no crash without data)
  Batch 2 — RasterIndexer (formula, bounds, determinism, from_array)
  Batch 3 — EarthDataLoader (lazy, missing files → None, no crash)
  Batch 4 — SpatialRuntime real_world_provider priority + set_real_world_provider
  Batch 5 — EarthFlags (all off by default)
  Batch 6 — Fallback: RealWorldSignalProvider never raises, always returns safe defaults
  Batch 7 — Pipeline regression: SAL / M1 / VC / D6 unchanged

Acceptance criteria:
  ✔ no regression in existing 208 tests
  ✔ RealWorldSignalProvider with no data → synthetic-equivalent output
  ✔ Fallback always safe (no raise on missing / corrupt / out-of-bounds)
  ✔ Pipeline (SAL / M1 / VC / D6) deterministic with any provider
  ✔ SpatialRuntime priority chain correct
  ✔ No raster dependency in architecture (works with pure in-memory arrays)
"""

import unittest

import numpy as np

from core.signal.providers.real_world_provider import RealWorldSignalProvider
from core.signal.providers.base import BaseSignalProvider
from core.signal.providers.synthetic import SyntheticProvider
from core.signal.raster_indexer import RasterIndexer
from core.data.earth_sources.loader import EarthDataLoader
from core.config.earth_flags import EarthFlags
from core.runtime.spatial_runtime import SpatialRuntime
from core.m1 import M1Pipeline, TileBBox
from core.vc import VisualConsistencyEngine
from core.contract import ContractGuard


SAMPLE_POINTS = [
    (0.0, 0.0),
    (45.0, 30.0),
    (-90.0, -45.0),
    (10.0, 70.0),
    (0.0, -70.0),
    (170.0, 10.0),
    (-180.0, -90.0),
    (180.0, 90.0),   # edge of grid
]

SMALL_BBOX = TileBBox(lon_min=-15, lon_max=15, lat_min=-10, lat_max=10)


# ---------------------------------------------------------------------------
# Batch 2 — RasterIndexer
# ---------------------------------------------------------------------------

class TestRasterIndexer(unittest.TestCase):

    def _make_indexer(self, height=180, width=360, fill=42):
        arr = np.full((height, width), fill, dtype=np.int16)
        return RasterIndexer.from_array(arr)

    def test_from_array_no_file_io(self):
        """Construction from array must not touch the filesystem."""
        idx = self._make_indexer()
        self.assertEqual(idx.sample(0.0, 0.0), 42)

    def test_sample_returns_int(self):
        idx = self._make_indexer()
        for lon, lat in SAMPLE_POINTS:
            v = idx.sample(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertIsNotNone(v)
                self.assertIsInstance(v, int)

    def test_sample_formula_column(self):
        """col = int((lon+180)/360 * width) — verify for known inputs."""
        width, height = 360, 180
        arr = np.zeros((height, width), dtype=np.int16)
        arr[90, 180] = 99   # equator / prime meridian → row=90, col=180
        idx = RasterIndexer.from_array(arr)
        self.assertEqual(idx.sample(0.0, 0.0), 99)

    def test_sample_formula_row(self):
        """row = int((90-lat)/180 * height) — verify top-left corner."""
        width, height = 360, 180
        arr = np.zeros((height, width), dtype=np.int16)
        arr[0, 0] = 77   # north pole / antimeridian
        idx = RasterIndexer.from_array(arr)
        self.assertEqual(idx.sample(-180.0, 90.0), 77)

    def test_sample_nodata_returns_none(self):
        arr = np.full((180, 360), -9999, dtype=np.int16)
        idx = RasterIndexer.from_array(arr, nodata=-9999)
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertIsNone(idx.sample(lon, lat))

    def test_sample_deterministic(self):
        idx = self._make_indexer()
        for lon, lat in SAMPLE_POINTS:
            v1 = idx.sample(lon, lat)
            v2 = idx.sample(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(v1, v2)

    def test_edge_coordinates_do_not_raise(self):
        """Out-of-range coordinates must be clamped, never raise."""
        idx = self._make_indexer()
        for lon, lat in [(-180.0, -90.0), (180.0, 90.0), (-999.0, 999.0)]:
            with self.subTest(lon=lon, lat=lat):
                result = idx.sample(lon, lat)
                self.assertIsNotNone(result)

    def test_shape_property(self):
        arr = np.zeros((100, 200), dtype=np.int16)
        idx = RasterIndexer.from_array(arr)
        self.assertEqual(idx.shape, (100, 200))


# ---------------------------------------------------------------------------
# Batch 3 — EarthDataLoader
# ---------------------------------------------------------------------------

class TestEarthDataLoader(unittest.TestCase):

    def setUp(self):
        # Use a non-existent path — all layers should return None gracefully.
        self._loader = EarthDataLoader(source_root="/tmp/_rodio_nonexistent_data_root")

    def test_known_layer_names_accepted(self):
        for name in ("dem", "ocean", "landcover", "climate"):
            with self.subTest(layer=name):
                result = self._loader.load_layer(name)
                self.assertIsNone(result)   # data absent → None

    def test_unknown_layer_raises(self):
        with self.assertRaises(ValueError):
            self._loader.load_layer("badlayer")

    def test_missing_data_returns_none(self):
        self.assertIsNone(self._loader.load_layer("dem"))
        self.assertIsNone(self._loader.load_layer("climate"))

    def test_cache_returns_same_object(self):
        r1 = self._loader.load_layer("dem")
        r2 = self._loader.load_layer("dem")
        self.assertIs(r1, r2)   # cached, same None object

    def test_no_crash_on_missing_root(self):
        loader = EarthDataLoader(source_root="/tmp/_absolutely_no_data_here")
        for name in ("dem", "ocean", "landcover", "climate"):
            with self.subTest(layer=name):
                self.assertIsNone(loader.load_layer(name))


# ---------------------------------------------------------------------------
# Batch 5 — EarthFlags
# ---------------------------------------------------------------------------

class TestEarthFlags(unittest.TestCase):

    def test_enable_real_dem_off(self):
        self.assertFalse(EarthFlags.ENABLE_REAL_DEM)

    def test_enable_real_ocean_off(self):
        self.assertFalse(EarthFlags.ENABLE_REAL_OCEAN)

    def test_enable_real_climate_off(self):
        self.assertFalse(EarthFlags.ENABLE_REAL_CLIMATE)

    def test_flags_are_class_attributes(self):
        self.assertIsInstance(EarthFlags.ENABLE_REAL_DEM, bool)
        self.assertIsInstance(EarthFlags.ENABLE_REAL_OCEAN, bool)
        self.assertIsInstance(EarthFlags.ENABLE_REAL_CLIMATE, bool)


# ---------------------------------------------------------------------------
# Batch 1 + 6 — RealWorldSignalProvider (skeleton + fallback)
# ---------------------------------------------------------------------------

class TestRealWorldSignalProviderFallback(unittest.TestCase):
    """When no data is present, provider must behave like SyntheticProvider."""

    def setUp(self):
        self.provider = RealWorldSignalProvider(
            source_root="/tmp/_rodio_nonexistent_data_root"
        )

    def test_is_base_signal_provider(self):
        self.assertIsInstance(self.provider, BaseSignalProvider)

    def test_get_dem_falls_back_to_zero(self):
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(self.provider.get_dem(lon, lat), 0.0)

    def test_get_ocean_falls_back_to_false(self):
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertFalse(self.provider.get_ocean(lon, lat))

    def test_get_climate_falls_back_to_none(self):
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertIsNone(self.provider.get_climate(lon, lat))

    def test_get_landcover_falls_back_to_zero(self):
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(self.provider.get_landcover(lon, lat), 0)

    def test_mode_attribute(self):
        self.assertEqual(self.provider.mode, "lazy")

    def test_lazy_mode_does_not_load_on_construction(self):
        """Provider must not touch any data file during __init__."""
        p = RealWorldSignalProvider(source_root="/tmp/_rodio_nonexistent")
        self.assertIsNone(p._loader)   # loader not yet constructed

    def test_no_raise_on_edge_coordinates(self):
        extremes = [(-180.0, -90.0), (180.0, 90.0), (0.0, 0.0)]
        for lon, lat in extremes:
            with self.subTest(lon=lon, lat=lat):
                self.provider.get_dem(lon, lat)
                self.provider.get_ocean(lon, lat)
                self.provider.get_climate(lon, lat)
                self.provider.get_landcover(lon, lat)

    def test_deterministic_with_no_data(self):
        for lon, lat in SAMPLE_POINTS:
            v1 = self.provider.get_dem(lon, lat)
            v2 = self.provider.get_dem(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(v1, v2)


class TestRealWorldSignalProviderWithMockData(unittest.TestCase):
    """
    Verify RealWorldSignalProvider reads correctly when the loader returns
    an in-memory mock adapter (simulates real data present).
    """

    def _make_provider_with_mock_dem(
        self,
        elevation_value: int,
        climate_value=None,
    ) -> RealWorldSignalProvider:
        """Return a provider whose DEM always returns elevation_value."""

        class MockDEMRegistry:
            def query(self, lon, lat):
                return elevation_value

        class MockClimate:
            def get_value(self, lon, lat):
                return climate_value

        provider = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        # Pre-build loader and inject mock
        from core.data.earth_sources.loader import EarthDataLoader
        loader = EarthDataLoader.__new__(EarthDataLoader)
        loader.source_root = None
        loader._cache = {
            "dem": MockDEMRegistry(),
            "ocean": None,
            "landcover": None,
            "climate": MockClimate() if climate_value is not None else None,
        }
        provider._loader = loader
        return provider

    def test_positive_elevation_ocean_false(self):
        provider = self._make_provider_with_mock_dem(500)
        self.assertAlmostEqual(provider.get_dem(0.0, 0.0), 500.0, places=1)
        self.assertFalse(provider.get_ocean(0.0, 0.0))

    def test_negative_elevation_ocean_true(self):
        provider = self._make_provider_with_mock_dem(-200)
        self.assertAlmostEqual(provider.get_dem(0.0, 0.0), -200.0, places=1)
        self.assertTrue(provider.get_ocean(0.0, 0.0))

    def test_negative_elevation_with_climate_veto_is_land(self):
        provider = self._make_provider_with_mock_dem(-430, climate_value=6)
        self.assertAlmostEqual(provider.get_dem(0.0, 0.0), -430.0, places=1)
        self.assertEqual(provider.get_climate(0.0, 0.0), 6)
        self.assertFalse(provider.get_ocean(0.0, 0.0))

    def test_none_dem_falls_back_to_zero(self):
        provider = self._make_provider_with_mock_dem(None)
        self.assertEqual(provider.get_dem(0.0, 0.0), 0.0)


# ---------------------------------------------------------------------------
# Batch 4 — SpatialRuntime real_world_provider priority
# ---------------------------------------------------------------------------

class TestSpatialRuntimeRealWorldProvider(unittest.TestCase):

    def _make_runtime(self, real_world=None, signal_prov=None):
        if real_world is None and signal_prov is None:
            signal_prov = SyntheticProvider()
        return SpatialRuntime(
            signal_provider=signal_prov,
            real_world_provider=real_world,
        )

    def test_real_world_provider_accepted(self):
        rw = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        rt = SpatialRuntime(real_world_provider=rw)
        self.assertIs(rt._real_world_provider, rw)

    def test_real_world_provider_alone_accepted(self):
        """real_world_provider alone satisfies the constructor requirement."""
        rw = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        rt = SpatialRuntime(real_world_provider=rw)
        self.assertIsNotNone(rt)

    def test_set_real_world_provider(self):
        rt = self._make_runtime()
        rw = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        rt.set_real_world_provider(rw)
        self.assertIs(rt._real_world_provider, rw)

    def test_clear_real_world_provider(self):
        rw = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        rt = self._make_runtime(real_world=rw)
        rt.set_real_world_provider(None)
        self.assertIsNone(rt._real_world_provider)

    def test_real_world_takes_priority_over_signal_provider(self):
        """When real_world_provider is set, signal_provider must not be queried."""
        real = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        rt = SpatialRuntime(
            signal_provider=SyntheticProvider(),
            real_world_provider=real,
        )
        # Both return 0.0 / False / None in fallback mode — verify ocean_rule
        state = rt.query_point(0.0, 0.0)
        self.assertIn("real_world_provider", state.source["ocean_rule"])

    def test_signal_provider_used_when_no_real_world(self):
        rt = self._make_runtime()
        state = rt.query_point(0.0, 0.0)
        self.assertIn("signal_provider", state.source["ocean_rule"])

    def test_query_point_does_not_raise_with_real_world_no_data(self):
        rw = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        rt = SpatialRuntime(real_world_provider=rw)
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                rt.query_point(lon, lat)   # must not raise

    def test_runtime_applies_climate_veto_to_real_world_provider(self):
        class ConflictingRealProvider(BaseSignalProvider):
            def get_dem(self, lon, lat):
                return -430.0
            def get_landcover(self, lon, lat):
                return 0
            def get_climate(self, lon, lat):
                return 6
            def get_ocean(self, lon, lat):
                return True

        rt = SpatialRuntime(real_world_provider=ConflictingRealProvider())
        state = rt.query_point(35.5, 31.5)
        self.assertFalse(state.ocean)
        self.assertEqual(state.climate_class, 6)
        self.assertIn("overridden", state.source["ocean_rule"])

    def test_real_source_cache_dead_sea_climate_veto_when_available(self):
        provider = RealWorldSignalProvider(source_root="d5b_processor_v3/source_cache/gee_global")
        if provider.get_climate(35.5, 31.5) is None:
            self.skipTest("local Köppen layer unavailable")
        self.assertLess(provider.get_dem(35.5, 31.5), 0.0)
        self.assertFalse(provider.get_ocean(35.5, 31.5))

    def test_no_dem_registry_and_no_signal_provider_raises(self):
        """Constructor must raise when no data source is given at all."""
        with self.assertRaises(ValueError):
            SpatialRuntime()


# ---------------------------------------------------------------------------
# Stage 3 regression: SAL / M1 / VC / D6 pipeline unchanged
# ---------------------------------------------------------------------------

def _make_signal_fn(provider):
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


class TestSALUnchangedStage3(unittest.TestCase):

    def _resolve(self, provider):
        from core.sal import SemanticArbitrator
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

    def test_sal_invariants_real_world_provider_no_data(self):
        provider = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        self._assert_invariants(self._resolve(provider))

    def test_sal_output_matches_synthetic_when_no_real_data(self):
        """Without data, RealWorldSignalProvider and SyntheticProvider give same SAL result."""
        rw = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        syn = SyntheticProvider()
        r_rw  = self._resolve(rw)
        r_syn = self._resolve(syn)
        self.assertEqual(r_rw.final_class, r_syn.final_class)
        self.assertAlmostEqual(r_rw.winner_margin, r_syn.winner_margin, places=9)


class TestM1ShapeStage3(unittest.TestCase):

    def _tile(self, provider):
        return M1Pipeline(
            signal_provider=_make_signal_fn(provider), tile_px_size=6
        ).run_tile(SMALL_BBOX)

    def test_shape_matches_synthetic(self):
        t_syn = self._tile(SyntheticProvider())
        t_rw  = self._tile(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))
        self.assertEqual(t_syn.shape, t_rw.shape)

    def test_uncertainty_bounded(self):
        tile = self._tile(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))
        unc = tile.uncertainty_mask.astype(np.float32)
        self.assertGreaterEqual(float(unc.min()), 0.0)
        self.assertLessEqual(float(unc.max()), 1.0)

    def test_m1_contract_passes(self):
        from core.contract.m1_contract import M1Contract
        tile = self._tile(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))
        M1Contract().validate(tile)


class TestVCStabilityStage3(unittest.TestCase):

    def _vc_ctx(self, provider):
        tile = M1Pipeline(
            signal_provider=_make_signal_fn(provider), tile_px_size=6
        ).run_tile(SMALL_BBOX)
        return VisualConsistencyEngine().process(tile)

    def test_vc_shape_matches_synthetic(self):
        ctx_syn = self._vc_ctx(SyntheticProvider())
        ctx_rw  = self._vc_ctx(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))
        self.assertEqual(ctx_syn.shape, ctx_rw.shape)

    def test_temporal_stability_bounded(self):
        ctx = self._vc_ctx(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))
        stab = ctx.temporal_stability_field.astype(np.float32)
        self.assertGreaterEqual(float(stab.min()), 0.0 - 1e-4)
        self.assertLessEqual(float(stab.max()), 1.0 + 1e-4)

    def test_vc_contract_passes(self):
        from core.contract.vc_contract import VCContract
        ctx = self._vc_ctx(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))
        VCContract().validate(ctx)


class TestD6DeterministicStage3(unittest.TestCase):

    def _frame(self, provider):
        from core.contract.d6_contract import D6Contract
        tile = M1Pipeline(
            signal_provider=_make_signal_fn(provider), tile_px_size=6
        ).run_tile(SMALL_BBOX)
        ctx  = VisualConsistencyEngine().process(tile)
        return D6Contract().render_from_vc(ctx)

    def test_d6_deterministic(self):
        provider = RealWorldSignalProvider(source_root="/tmp/_nonexistent")
        f1 = self._frame(provider)
        f2 = self._frame(provider)
        np.testing.assert_array_equal(f1, f2)

    def test_d6_matches_synthetic_when_no_real_data(self):
        """Without data files, D6 output must equal pure synthetic."""
        frame_syn = self._frame(SyntheticProvider())
        frame_rw  = self._frame(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))
        np.testing.assert_array_equal(frame_syn, frame_rw)


class TestFullContractGuardStage3(unittest.TestCase):

    def _run_pipeline(self, provider):
        from core.sal import SemanticArbitrator
        guard = ContractGuard(strict_sal_cache=False)

        sal_result = SemanticArbitrator().resolve(
            dem_signal="land" if provider.get_dem(0.0, 30.0) >= 0 else "ocean",
            climate_signal="land" if provider.get_climate(0.0, 30.0) is not None else None,
            ocean_signal="ocean" if provider.get_ocean(0.0, 30.0) else "land",
            landcover_signal="land",
        )
        guard.validate_sal(sal_result)

        tile = M1Pipeline(
            signal_provider=_make_signal_fn(provider), tile_px_size=6
        ).run_tile(SMALL_BBOX)
        guard.validate_m1(tile)

        ctx = VisualConsistencyEngine().process(tile)
        guard.validate_vc(ctx)

        frame = guard.render_d6_from_vc(ctx)
        guard.validate_d6(frame)

    def test_real_world_provider_no_data_passes_full_contract(self):
        self._run_pipeline(RealWorldSignalProvider(source_root="/tmp/_nonexistent"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
