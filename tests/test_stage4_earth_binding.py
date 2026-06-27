"""
Stage 3 Step 4 — EarthDataLoader Binding Layer Tests

Validates the complete binding path:
    RasterLayerRegistry → RasterBackedProvider → SpatialRuntime

Batch coverage:
    Batch 1 — RasterLayerRegistry (load_layer / get_layer / is_loaded / loaded_layers)
    Batch 2 — to_indexers() round-trip
    Batch 3 — RasterBackedProvider (gebco / etopo / koppen combination)
    Batch 4 — SpatialRuntime.set_earth_loader() one-call binding
    Batch 5 — EarthFlags ENABLE_REAL_DATA / ENABLE_FALLBACK
    Batch 6 — Geographic correctness (Dead Sea, Pacific, Death Valley)
    Batch 7 — Pipeline regression: SAL / M1 / VC / D6 untouched

Acceptance criteria:
    ✔ load_layer stores and retrieves correctly
    ✔ raster sample correctness through full chain
    ✔ Dead Sea → ocean False (below sea level, but Köppen veto)
    ✔ Pacific → ocean True (deep negative DEM, no climate class)
    ✔ Death Valley → ocean False (below sea level, but Köppen veto)
    ✔ climate consistency (valid class always forces land)
    ✔ SAL invariants unchanged
    ✔ M1 shape unchanged
    ✔ VC stability unchanged
    ✔ deterministic across repeated calls
    ✔ all fallbacks safe (no raise when layers absent)
"""

import unittest

import numpy as np

from core.data.earth_data_loader import RasterLayerRegistry, GLOBAL_BBOX
from core.signal.raster_indexer import RasterIndexer
from core.signal.providers.gebco_provider import GEBCOProvider
from core.signal.providers.etopo_provider import ETOPOProvider
from core.signal.providers.koppen_provider import KoppenProvider
from core.signal.providers.raster_backed_provider import RasterBackedProvider
from core.signal.providers.base import BaseSignalProvider
from core.signal.providers.synthetic import SyntheticProvider
from core.config.earth_flags import EarthFlags
from core.runtime.spatial_runtime import SpatialRuntime
from core.m1 import M1Pipeline, TileBBox
from core.vc import VisualConsistencyEngine
from core.sal import SemanticArbitrator
from core.contract import ContractGuard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uniform_array(value: int, height: int = 180, width: int = 360) -> np.ndarray:
    return np.full((height, width), value, dtype=np.int16)


def _registry(dem=None, ocean=None, climate=None, landcover=None) -> RasterLayerRegistry:
    """Build a RasterLayerRegistry from optional uniform-value arrays."""
    reg = RasterLayerRegistry(data_root="/tmp/_test")
    if dem is not None:
        reg.load_layer("dem", _uniform_array(dem))
    if ocean is not None:
        reg.load_layer("ocean", _uniform_array(ocean))
    if climate is not None:
        reg.load_layer("climate", _uniform_array(climate))
    if landcover is not None:
        reg.load_layer("landcover", _uniform_array(landcover))
    return reg


def _raster_backed(dem_val=0, ocean_val=None, climate_val=None) -> RasterBackedProvider:
    """Build a RasterBackedProvider with uniform-value indexers."""
    gebco  = GEBCOProvider(RasterIndexer.from_array(_uniform_array(ocean_val or dem_val)))  if ocean_val is not None else None
    etopo  = ETOPOProvider(RasterIndexer.from_array(_uniform_array(dem_val)))
    koppen = KoppenProvider(RasterIndexer.from_array(_uniform_array(climate_val or 0))) if climate_val is not None else None
    return RasterBackedProvider(gebco=gebco, etopo=etopo, koppen=koppen)


SAMPLE_POINTS = [
    (0.0, 0.0), (45.0, 30.0), (-90.0, -45.0),
    (10.0, 70.0), (-180.0, -90.0), (180.0, 90.0),
]

SMALL_BBOX = TileBBox(lon_min=-15, lon_max=15, lat_min=-10, lat_max=10)


# ---------------------------------------------------------------------------
# Batch 1 — RasterLayerRegistry
# ---------------------------------------------------------------------------

class TestRasterLayerRegistry(unittest.TestCase):

    def test_empty_on_construction(self):
        reg = RasterLayerRegistry()
        self.assertEqual(reg.loaded_layers(), [])
        for name in ("dem", "ocean", "climate", "landcover"):
            with self.subTest(name=name):
                self.assertFalse(reg.is_loaded(name))

    def test_load_and_get_layer(self):
        reg = RasterLayerRegistry()
        arr = _uniform_array(42)
        reg.load_layer("dem", arr)
        layer = reg.get_layer("dem")
        self.assertIsNotNone(layer)
        self.assertIs(layer["array"], arr)
        self.assertEqual(layer["bbox"], GLOBAL_BBOX)

    def test_custom_bbox_stored(self):
        reg = RasterLayerRegistry()
        bbox = (-90.0, 90.0, -45.0, 45.0)
        reg.load_layer("climate", _uniform_array(5), bbox=bbox)
        self.assertEqual(reg.get_layer("climate")["bbox"], bbox)

    def test_is_loaded_after_load(self):
        reg = _registry(dem=100)
        self.assertTrue(reg.is_loaded("dem"))
        self.assertFalse(reg.is_loaded("ocean"))

    def test_loaded_layers_names(self):
        reg = _registry(dem=0, climate=5)
        loaded = reg.loaded_layers()
        self.assertIn("dem", loaded)
        self.assertIn("climate", loaded)
        self.assertNotIn("ocean", loaded)
        self.assertNotIn("landcover", loaded)

    def test_unknown_layer_raises_on_load(self):
        reg = RasterLayerRegistry()
        with self.assertRaises(ValueError):
            reg.load_layer("badlayer", _uniform_array(0))

    def test_unknown_layer_raises_on_get(self):
        reg = RasterLayerRegistry()
        with self.assertRaises(ValueError):
            reg.get_layer("badlayer")

    def test_non_2d_array_raises(self):
        reg = RasterLayerRegistry()
        with self.assertRaises(ValueError):
            reg.load_layer("dem", np.zeros((10, 10, 3), dtype=np.int16))

    def test_non_ndarray_raises(self):
        reg = RasterLayerRegistry()
        with self.assertRaises(TypeError):
            reg.load_layer("dem", [[0, 1], [2, 3]])

    def test_overwrite_layer(self):
        reg = _registry(dem=10)
        reg.load_layer("dem", _uniform_array(99))
        self.assertEqual(reg.get_layer("dem")["array"][0, 0], 99)

    def test_all_four_layers_loadable(self):
        reg = _registry(dem=1, ocean=-1000, climate=5, landcover=40)
        self.assertEqual(sorted(reg.loaded_layers()), ["climate", "dem", "landcover", "ocean"])


# ---------------------------------------------------------------------------
# Batch 2 — to_indexers() round-trip
# ---------------------------------------------------------------------------

class TestToIndexers(unittest.TestCase):

    def test_returns_indexer_for_loaded_layers(self):
        reg = _registry(dem=300, climate=7)
        indexers = reg.to_indexers()
        self.assertIn("dem", indexers)
        self.assertIn("climate", indexers)
        self.assertNotIn("ocean", indexers)

    def test_indexer_samples_correctly(self):
        reg = _registry(dem=42)
        idx = reg.to_indexers()["dem"]
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(idx.sample(lon, lat), 42)

    def test_nodata_propagated(self):
        reg = _registry(ocean=-9999)
        idx = reg.to_indexers(nodata=-9999)["ocean"]
        self.assertIsNone(idx.sample(0.0, 0.0))

    def test_empty_registry_returns_empty_dict(self):
        reg = RasterLayerRegistry()
        self.assertEqual(reg.to_indexers(), {})


# ---------------------------------------------------------------------------
# Batch 3 — RasterBackedProvider
# ---------------------------------------------------------------------------

class TestRasterBackedProvider(unittest.TestCase):

    def test_is_base_signal_provider(self):
        p = RasterBackedProvider()
        self.assertIsInstance(p, BaseSignalProvider)

    def test_all_none_returns_safe_defaults(self):
        p = RasterBackedProvider()
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(p.get_dem(lon, lat), 0.0)
                self.assertFalse(p.get_ocean(lon, lat))
                self.assertIsNone(p.get_climate(lon, lat))
                self.assertEqual(p.get_landcover(lon, lat), 0)

    def test_dem_gebco_priority(self):
        gebco = GEBCOProvider(RasterIndexer.from_array(_uniform_array(-3000)))
        etopo = ETOPOProvider(RasterIndexer.from_array(_uniform_array(500)))
        p = RasterBackedProvider(gebco=gebco, etopo=etopo)
        self.assertAlmostEqual(p.get_dem(0.0, 0.0), -3000.0, places=1)

    def test_dem_etopo_fallback_when_no_gebco(self):
        etopo = ETOPOProvider(RasterIndexer.from_array(_uniform_array(800)))
        p = RasterBackedProvider(etopo=etopo)
        self.assertAlmostEqual(p.get_dem(0.0, 0.0), 800.0, places=1)

    def test_ocean_true_negative_dem_no_climate(self):
        p = _raster_backed(ocean_val=-5000)
        self.assertTrue(p.get_ocean(0.0, 0.0))

    def test_ocean_false_positive_dem(self):
        p = _raster_backed(ocean_val=200)
        self.assertFalse(p.get_ocean(0.0, 0.0))

    def test_koppen_veto_overrides_negative_dem(self):
        p = _raster_backed(ocean_val=-430, climate_val=6)
        self.assertFalse(p.get_ocean(0.0, 0.0))

    def test_climate_returned_correctly(self):
        p = _raster_backed(climate_val=12)
        self.assertEqual(p.get_climate(0.0, 0.0), 12)

    def test_climate_zero_is_none(self):
        p = _raster_backed(climate_val=0)
        self.assertIsNone(p.get_climate(0.0, 0.0))

    def test_landcover_always_zero(self):
        p = _raster_backed(dem_val=100, climate_val=5)
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(p.get_landcover(lon, lat), 0)

    def test_deterministic(self):
        p = _raster_backed(ocean_val=-2000, climate_val=None)
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(p.get_dem(lon, lat), p.get_dem(lon, lat))
                self.assertEqual(p.get_ocean(lon, lat), p.get_ocean(lon, lat))
                self.assertEqual(p.get_climate(lon, lat), p.get_climate(lon, lat))

    def test_edge_coordinates_do_not_raise(self):
        p = _raster_backed(ocean_val=-1000, climate_val=3)
        for lon, lat in [(-180.0, -90.0), (180.0, 90.0)]:
            with self.subTest(lon=lon, lat=lat):
                p.get_dem(lon, lat)
                p.get_ocean(lon, lat)
                p.get_climate(lon, lat)


# ---------------------------------------------------------------------------
# Batch 4 — SpatialRuntime.set_earth_loader()
# ---------------------------------------------------------------------------

class TestSetEarthLoader(unittest.TestCase):

    def _runtime_from_registry(self, **kwargs) -> SpatialRuntime:
        reg = _registry(**kwargs)
        rt = SpatialRuntime(signal_provider=SyntheticProvider())
        rt.set_earth_loader(reg)
        return rt

    def test_set_earth_loader_activates_real_world_provider(self):
        rt = self._runtime_from_registry(dem=100)
        self.assertIsNotNone(rt._real_world_provider)
        self.assertIsInstance(rt._real_world_provider, RasterBackedProvider)

    def test_ocean_rule_is_real_world_provider(self):
        rt = self._runtime_from_registry(ocean=-4000)
        state = rt.query_point(0.0, 0.0)
        self.assertIn("real_world_provider", state.source["ocean_rule"])

    def test_empty_registry_still_safe(self):
        reg = RasterLayerRegistry()
        rt = SpatialRuntime(signal_provider=SyntheticProvider())
        rt.set_earth_loader(reg)
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                rt.query_point(lon, lat)

    def test_can_replace_loader(self):
        rt = self._runtime_from_registry(ocean=-3000)
        self.assertTrue(rt.query_point(0.0, 0.0).ocean)
        reg2 = _registry(ocean=200)
        rt.set_earth_loader(reg2)
        self.assertFalse(rt.query_point(0.0, 0.0).ocean)

    def test_set_earth_loader_overrides_signal_provider(self):
        rt = self._runtime_from_registry(ocean=-5000)
        state = rt.query_point(-150.0, 10.0)
        self.assertIn("real_world_provider", state.source["ocean_rule"])


# ---------------------------------------------------------------------------
# Batch 5 — EarthFlags
# ---------------------------------------------------------------------------

class TestEarthFlagsStep4(unittest.TestCase):

    def test_enable_real_data_true(self):
        self.assertTrue(EarthFlags.ENABLE_REAL_DATA)

    def test_enable_fallback_true(self):
        self.assertTrue(EarthFlags.ENABLE_FALLBACK)

    def test_step3_flags_still_false(self):
        self.assertFalse(EarthFlags.ENABLE_GEBCO)
        self.assertFalse(EarthFlags.ENABLE_ETOPO)
        self.assertFalse(EarthFlags.ENABLE_KOPPEN)


# ---------------------------------------------------------------------------
# Batch 6 — Geographic correctness through full binding chain
# ---------------------------------------------------------------------------

class TestGeographicCorrectnessStep4(unittest.TestCase):
    """
    All three landmark points tested through the full binding chain:
    RasterLayerRegistry → set_earth_loader() → SpatialRuntime.query_point()
    """

    def _runtime(self, ocean_val, climate_val=None) -> SpatialRuntime:
        reg = _registry(ocean=ocean_val, climate=climate_val)
        rt = SpatialRuntime(signal_provider=SyntheticProvider())
        rt.set_earth_loader(reg)
        return rt

    def test_dead_sea_ocean_false(self):
        """−430 m but climate class 6 → land."""
        rt = self._runtime(ocean_val=-430, climate_val=6)
        state = rt.query_point(35.5, 31.5)
        self.assertFalse(state.ocean)
        self.assertEqual(state.climate_class, 6)

    def test_pacific_ocean_true(self):
        """−5000 m, no climate class → ocean."""
        rt = self._runtime(ocean_val=-5000, climate_val=None)
        state = rt.query_point(-150.0, 10.0)
        self.assertTrue(state.ocean)
        self.assertIsNone(state.climate_class)

    def test_death_valley_ocean_false(self):
        """−86 m but climate class 4 → land."""
        rt = self._runtime(ocean_val=-86, climate_val=4)
        state = rt.query_point(-116.8, 36.5)
        self.assertFalse(state.ocean)

    def test_high_mountain_not_ocean(self):
        rt = self._runtime(ocean_val=8849, climate_val=None)
        self.assertFalse(rt.query_point(86.9, 28.0).ocean)

    def test_climate_consistency_any_valid_class_is_land(self):
        for cls_val in [1, 5, 12, 18, 25, 30]:
            rt = self._runtime(ocean_val=-200, climate_val=cls_val)
            with self.subTest(climate_class=cls_val):
                state = rt.query_point(0.0, 0.0)
                self.assertFalse(state.ocean)
                self.assertIsNotNone(state.climate_class)


# ---------------------------------------------------------------------------
# Batch 7 — Pipeline regression: SAL / M1 / VC unchanged
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


class TestSALUnchangedStep4(unittest.TestCase):

    def _resolve(self, provider):
        dem   = provider.get_dem(20.0, 35.0)
        ocean = provider.get_ocean(20.0, 35.0)
        clim  = provider.get_climate(20.0, 35.0)
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

    def test_sal_land_mock(self):
        self._assert_invariants(self._resolve(_raster_backed(ocean_val=300, climate_val=8)))

    def test_sal_ocean_mock(self):
        self._assert_invariants(self._resolve(_raster_backed(ocean_val=-4000)))

    def test_sal_matches_synthetic_empty_registry(self):
        empty_provider = RasterBackedProvider()
        syn = SyntheticProvider()
        r_rw  = self._resolve(empty_provider)
        r_syn = self._resolve(syn)
        self.assertEqual(r_rw.final_class, r_syn.final_class)
        self.assertAlmostEqual(r_rw.winner_margin, r_syn.winner_margin, places=9)


class TestM1ShapeStep4(unittest.TestCase):

    def _tile(self, provider):
        return M1Pipeline(
            signal_provider=_signal_fn(provider), tile_px_size=6
        ).run_tile(SMALL_BBOX)

    def test_shape_unchanged_land_mock(self):
        t_syn  = self._tile(SyntheticProvider())
        t_real = self._tile(_raster_backed(ocean_val=500, climate_val=10))
        self.assertEqual(t_syn.shape, t_real.shape)

    def test_shape_unchanged_ocean_mock(self):
        t_syn  = self._tile(SyntheticProvider())
        t_real = self._tile(_raster_backed(ocean_val=-3000))
        self.assertEqual(t_syn.shape, t_real.shape)

    def test_uncertainty_bounded(self):
        tile = self._tile(_raster_backed(ocean_val=-5000))
        unc  = tile.uncertainty_mask.astype(np.float32)
        self.assertGreaterEqual(float(unc.min()), 0.0)
        self.assertLessEqual(float(unc.max()), 1.0)


class TestVCStabilityStep4(unittest.TestCase):

    def _vc_ctx(self, provider):
        tile = M1Pipeline(
            signal_provider=_signal_fn(provider), tile_px_size=6
        ).run_tile(SMALL_BBOX)
        return VisualConsistencyEngine().process(tile)

    def test_vc_shape_unchanged(self):
        ctx_syn  = self._vc_ctx(SyntheticProvider())
        ctx_real = self._vc_ctx(_raster_backed(ocean_val=200))
        self.assertEqual(ctx_syn.shape, ctx_real.shape)

    def test_temporal_stability_bounded(self):
        ctx  = self._vc_ctx(_raster_backed(ocean_val=-2000))
        stab = ctx.temporal_stability_field.astype(np.float32)
        self.assertGreaterEqual(float(stab.min()), 0.0 - 1e-4)
        self.assertLessEqual(float(stab.max()), 1.0 + 1e-4)

    def test_deterministic_through_binding_chain(self):
        p = _raster_backed(ocean_val=150, climate_val=7)
        ctx1 = self._vc_ctx(p)
        ctx2 = self._vc_ctx(p)
        np.testing.assert_array_equal(
            ctx1.temporal_stability_field,
            ctx2.temporal_stability_field,
        )


class TestFullContractGuardStep4(unittest.TestCase):

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

    def test_raster_backed_land_mock_passes_full_contract(self):
        self._run_pipeline(_raster_backed(ocean_val=400, climate_val=12))

    def test_raster_backed_ocean_mock_passes_full_contract(self):
        self._run_pipeline(_raster_backed(ocean_val=-4500))

    def test_empty_raster_backed_passes_full_contract(self):
        self._run_pipeline(RasterBackedProvider())


if __name__ == "__main__":
    unittest.main(verbosity=2)
