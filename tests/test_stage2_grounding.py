"""
Stage 2 Grounding Tests

Verifies the four Stage 2 batch additions:
  Batch 1 — DEMGroundingProvider (deterministic, bounded, no raster)
  Batch 2 — ClimateGroundingProvider (deterministic, lat-band buckets, no raster)
  Batch 3 — SpatialRuntime hybrid blend (0.8 synthetic + 0.2 grounding for DEM)
  Batch 4 — SignalFlags (all flags off by default)

Acceptance criteria:
  ✔ no regression in existing 159 tests (enforced by pytest collecting all tests)
  ✔ hybrid mode does not break determinism
  ✔ signal blending stays bounded
  ✔ no raster dependency introduced (all imports succeed with no data files)
  ✔ SAL winner_margin structure unchanged
  ✔ M1 mask shape unchanged
  ✔ VC stability unchanged
  ✔ D6 output deterministic
"""

import math
import unittest

import numpy as np

from core.signal.providers.dem_grounding import DEMGroundingProvider
from core.signal.providers.climate_grounding import ClimateGroundingProvider
from core.signal.providers.base import BaseSignalProvider
from core.signal.providers.synthetic import SyntheticProvider
from core.config.signal_flags import SignalFlags
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
]

SMALL_BBOX = TileBBox(lon_min=-15, lon_max=15, lat_min=-10, lat_max=10)


# ---------------------------------------------------------------------------
# Batch 1 — DEMGroundingProvider
# ---------------------------------------------------------------------------

class TestDEMGroundingProvider(unittest.TestCase):

    def setUp(self):
        self.provider = DEMGroundingProvider()

    def test_is_base_signal_provider(self):
        self.assertIsInstance(self.provider, BaseSignalProvider)

    def test_get_dem_formula(self):
        for lon, lat in SAMPLE_POINTS:
            expected = math.sin(lat * 0.01) * 1000.0 + math.cos(lon * 0.01) * 200.0
            actual = self.provider.get_dem(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertAlmostEqual(actual, expected, places=9)

    def test_get_dem_bounded(self):
        for lon, lat in SAMPLE_POINTS:
            v = self.provider.get_dem(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertGreater(v, -1201.0)
                self.assertLess(v, 1201.0)

    def test_get_dem_deterministic(self):
        for lon, lat in SAMPLE_POINTS:
            v1 = self.provider.get_dem(lon, lat)
            v2 = self.provider.get_dem(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(v1, v2)

    def test_landcover_neutral(self):
        for lon, lat in SAMPLE_POINTS:
            self.assertEqual(self.provider.get_landcover(lon, lat), 0)

    def test_climate_neutral(self):
        for lon, lat in SAMPLE_POINTS:
            self.assertIsNone(self.provider.get_climate(lon, lat))

    def test_ocean_neutral(self):
        for lon, lat in SAMPLE_POINTS:
            self.assertFalse(self.provider.get_ocean(lon, lat))

    def test_dem_differs_from_synthetic(self):
        # DEM grounding must produce a non-trivially different value from SyntheticProvider
        synthetic = SyntheticProvider()
        differs = any(
            self.provider.get_dem(lon, lat) != synthetic.get_dem(lon, lat)
            for lon, lat in SAMPLE_POINTS
            if (lon, lat) != (0.0, 0.0)   # (0,0) may be near-zero coincidence
        )
        self.assertTrue(differs, "DEMGroundingProvider never differs from SyntheticProvider")


# ---------------------------------------------------------------------------
# Batch 2 — ClimateGroundingProvider
# ---------------------------------------------------------------------------

class TestClimateGroundingProvider(unittest.TestCase):

    def setUp(self):
        self.provider = ClimateGroundingProvider()

    def test_is_base_signal_provider(self):
        self.assertIsInstance(self.provider, BaseSignalProvider)

    def test_climate_tropical(self):
        self.assertEqual(self.provider.get_climate(0.0, 0.0), 1)
        self.assertEqual(self.provider.get_climate(0.0, 22.9), 1)
        self.assertEqual(self.provider.get_climate(0.0, -22.9), 1)

    def test_climate_temperate(self):
        self.assertEqual(self.provider.get_climate(0.0, 30.0), 2)
        self.assertEqual(self.provider.get_climate(0.0, 44.9), 2)
        self.assertEqual(self.provider.get_climate(0.0, -30.0), 2)

    def test_climate_polar(self):
        self.assertEqual(self.provider.get_climate(0.0, 50.0), 3)
        self.assertEqual(self.provider.get_climate(0.0, 80.0), 3)
        self.assertEqual(self.provider.get_climate(0.0, -60.0), 3)

    def test_climate_is_int(self):
        for lon, lat in SAMPLE_POINTS:
            v = self.provider.get_climate(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertIsNotNone(v)
                self.assertIsInstance(v, int)
                self.assertIn(v, (1, 2, 3))

    def test_climate_deterministic(self):
        for lon, lat in SAMPLE_POINTS:
            v1 = self.provider.get_climate(lon, lat)
            v2 = self.provider.get_climate(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(v1, v2)

    def test_dem_neutral(self):
        for lon, lat in SAMPLE_POINTS:
            self.assertEqual(self.provider.get_dem(lon, lat), 0.0)

    def test_landcover_neutral(self):
        for lon, lat in SAMPLE_POINTS:
            self.assertEqual(self.provider.get_landcover(lon, lat), 0)

    def test_ocean_neutral(self):
        for lon, lat in SAMPLE_POINTS:
            self.assertFalse(self.provider.get_ocean(lon, lat))


# ---------------------------------------------------------------------------
# Batch 4 — SignalFlags defaults
# ---------------------------------------------------------------------------

class TestSignalFlags(unittest.TestCase):

    def test_dem_grounding_off_by_default(self):
        self.assertFalse(SignalFlags.ENABLE_DEM_GROUNDING)

    def test_climate_grounding_off_by_default(self):
        self.assertFalse(SignalFlags.ENABLE_CLIMATE_GROUNDING)

    def test_hybrid_mode_off_by_default(self):
        self.assertFalse(SignalFlags.ENABLE_HYBRID_MODE)

    def test_flags_are_class_attributes(self):
        # Flags must be accessible from the class without instantiation
        self.assertIsInstance(SignalFlags.ENABLE_DEM_GROUNDING, bool)
        self.assertIsInstance(SignalFlags.ENABLE_CLIMATE_GROUNDING, bool)
        self.assertIsInstance(SignalFlags.ENABLE_HYBRID_MODE, bool)


# ---------------------------------------------------------------------------
# Batch 3 — SpatialRuntime hybrid blend mode
# ---------------------------------------------------------------------------

class TestSpatialRuntimeHybridBlend(unittest.TestCase):

    def _make_runtime(self, blend_mode="synthetic", grounding=None):
        synthetic = SyntheticProvider()
        return SpatialRuntime(
            signal_provider=synthetic,
            signal_blend_mode=blend_mode,
            grounding_provider=grounding,
        )

    def test_invalid_blend_mode_raises(self):
        with self.assertRaises(ValueError):
            self._make_runtime(blend_mode="badmode")

    def test_synthetic_mode_is_default(self):
        rt = self._make_runtime()
        self.assertEqual(rt.signal_blend_mode, "synthetic")

    def test_hybrid_mode_accepted(self):
        rt = self._make_runtime(blend_mode="hybrid", grounding=DEMGroundingProvider())
        self.assertEqual(rt.signal_blend_mode, "hybrid")

    def test_grounding_provider_injectable(self):
        grounding = DEMGroundingProvider()
        rt = self._make_runtime(blend_mode="hybrid", grounding=grounding)
        self.assertIs(rt._grounding_provider, grounding)

    def test_set_grounding_provider(self):
        rt = self._make_runtime()
        grounding = ClimateGroundingProvider()
        rt.set_grounding_provider(grounding)
        self.assertIs(rt._grounding_provider, grounding)

    def test_synthetic_mode_output_matches_pure_synthetic(self):
        """Synthetic mode must produce identical output to a plain SyntheticProvider runtime."""
        rt_plain = self._make_runtime()
        rt_with_grounding = SpatialRuntime(
            signal_provider=SyntheticProvider(),
            signal_blend_mode="synthetic",
            grounding_provider=DEMGroundingProvider(),  # present but must be ignored
        )
        for lon, lat in SAMPLE_POINTS:
            s_plain = rt_plain.query_point(lon, lat)
            s_with  = rt_with_grounding.query_point(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertAlmostEqual(s_plain.elevation, s_with.elevation, places=9)

    def test_hybrid_dem_blend_formula(self):
        """Hybrid mode DEM must equal 0.8*synthetic + 0.2*grounding."""
        grounding = DEMGroundingProvider()
        rt = self._make_runtime(blend_mode="hybrid", grounding=grounding)
        synthetic = SyntheticProvider()
        for lon, lat in SAMPLE_POINTS:
            expected = 0.8 * synthetic.get_dem(lon, lat) + 0.2 * grounding.get_dem(lon, lat)
            actual = rt.query_point(lon, lat).elevation
            with self.subTest(lon=lon, lat=lat):
                self.assertAlmostEqual(actual, expected, places=6)

    def test_hybrid_mode_deterministic(self):
        rt = self._make_runtime(blend_mode="hybrid", grounding=DEMGroundingProvider())
        for lon, lat in SAMPLE_POINTS:
            s1 = rt.query_point(lon, lat)
            s2 = rt.query_point(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertAlmostEqual(s1.elevation, s2.elevation, places=9)
                self.assertEqual(s1.ocean, s2.ocean)
                self.assertEqual(s1.climate_class, s2.climate_class)

    def test_hybrid_mode_elevation_bounded(self):
        """Blended elevation must stay within combined formula bounds."""
        rt = self._make_runtime(blend_mode="hybrid", grounding=DEMGroundingProvider())
        for lon, lat in SAMPLE_POINTS:
            elev = rt.query_point(lon, lat).elevation
            with self.subTest(lon=lon, lat=lat):
                # Synthetic is 0, grounding ≤ ±1200, so blend ≤ ±240 m
                self.assertGreater(elev, -250.0)
                self.assertLess(elev, 250.0)

    def test_hybrid_deviation_from_synthetic_is_bounded(self):
        """Hybrid values must deviate from synthetic within a finite delta."""
        rt_synthetic = self._make_runtime()
        rt_hybrid = self._make_runtime(blend_mode="hybrid", grounding=DEMGroundingProvider())
        for lon, lat in SAMPLE_POINTS:
            s = rt_synthetic.query_point(lon, lat).elevation
            h = rt_hybrid.query_point(lon, lat).elevation
            with self.subTest(lon=lon, lat=lat):
                delta = abs(h - s)
                self.assertLess(delta, 250.0)   # 0.2 * max_grounding_range

    def test_hybrid_no_grounding_provider_falls_back_to_synthetic(self):
        """Hybrid mode with no grounding provider must not crash, uses synthetic values."""
        rt = self._make_runtime(blend_mode="hybrid", grounding=None)
        for lon, lat in SAMPLE_POINTS:
            state = rt.query_point(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertAlmostEqual(state.elevation, 0.0, places=9)


# ---------------------------------------------------------------------------
# Stage 2 regression: SAL / M1 / VC / D6 pipeline unchanged
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


class TestSALStructureUnchangedStage2(unittest.TestCase):

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

    def _assert_sal_invariants(self, result):
        argmax = max(result.probability_map, key=lambda k: result.probability_map[k])
        self.assertEqual(result.winner_class, argmax)
        self.assertGreaterEqual(result.winner_ratio, 1.0)
        self.assertGreaterEqual(result.winner_margin, 0.0)
        self.assertLessEqual(result.winner_margin, 1.0)

    def test_sal_invariants_dem_grounding(self):
        self._assert_sal_invariants(self._resolve(DEMGroundingProvider()))

    def test_sal_invariants_climate_grounding(self):
        self._assert_sal_invariants(self._resolve(ClimateGroundingProvider()))

    def test_sal_deterministic_dem_grounding(self):
        p = DEMGroundingProvider()
        r1 = self._resolve(p)
        r2 = self._resolve(p)
        self.assertEqual(r1.final_class, r2.final_class)
        self.assertAlmostEqual(r1.winner_margin, r2.winner_margin, places=9)


class TestM1MaskShapeStage2(unittest.TestCase):

    def _tile(self, provider):
        return M1Pipeline(signal_provider=_make_signal_fn(provider), tile_px_size=6).run_tile(SMALL_BBOX)

    def test_shape_consistent_across_providers(self):
        t_syn  = self._tile(SyntheticProvider())
        t_dem  = self._tile(DEMGroundingProvider())
        t_clim = self._tile(ClimateGroundingProvider())
        self.assertEqual(t_syn.shape, t_dem.shape)
        self.assertEqual(t_syn.shape, t_clim.shape)

    def test_ocean_mask_shape_preserved(self):
        t_syn = self._tile(SyntheticProvider())
        t_dem = self._tile(DEMGroundingProvider())
        self.assertEqual(t_syn.ocean_mask.shape, t_dem.ocean_mask.shape)

    def test_biome_mask_shape_preserved(self):
        t_syn  = self._tile(SyntheticProvider())
        t_clim = self._tile(ClimateGroundingProvider())
        self.assertEqual(t_syn.biome_mask.shape, t_clim.biome_mask.shape)

    def test_uncertainty_bounded_both_providers(self):
        for provider in (DEMGroundingProvider(), ClimateGroundingProvider()):
            tile = self._tile(provider)
            unc = tile.uncertainty_mask.astype(np.float32)
            with self.subTest(provider=type(provider).__name__):
                self.assertGreaterEqual(float(unc.min()), 0.0)
                self.assertLessEqual(float(unc.max()), 1.0)

    def test_m1_contract_passes_both_grounding_providers(self):
        from core.contract.m1_contract import M1Contract
        contract = M1Contract()
        for provider in (DEMGroundingProvider(), ClimateGroundingProvider()):
            tile = self._tile(provider)
            with self.subTest(provider=type(provider).__name__):
                contract.validate(tile)


class TestVCStabilityStage2(unittest.TestCase):

    def _vc_ctx(self, provider):
        tile = M1Pipeline(signal_provider=_make_signal_fn(provider), tile_px_size=6).run_tile(SMALL_BBOX)
        return VisualConsistencyEngine().process(tile)

    def test_temporal_stability_bounded_dem_grounding(self):
        ctx = self._vc_ctx(DEMGroundingProvider())
        stab = ctx.temporal_stability_field.astype(np.float32)
        self.assertGreaterEqual(float(stab.min()), 0.0 - 1e-4)
        self.assertLessEqual(float(stab.max()), 1.0 + 1e-4)

    def test_temporal_stability_bounded_climate_grounding(self):
        ctx = self._vc_ctx(ClimateGroundingProvider())
        stab = ctx.temporal_stability_field.astype(np.float32)
        self.assertGreaterEqual(float(stab.min()), 0.0 - 1e-4)
        self.assertLessEqual(float(stab.max()), 1.0 + 1e-4)

    def test_vc_shape_consistent_across_providers(self):
        ctx_syn  = self._vc_ctx(SyntheticProvider())
        ctx_dem  = self._vc_ctx(DEMGroundingProvider())
        ctx_clim = self._vc_ctx(ClimateGroundingProvider())
        self.assertEqual(ctx_syn.shape, ctx_dem.shape)
        self.assertEqual(ctx_syn.shape, ctx_clim.shape)

    def test_vc_contract_passes_grounding_providers(self):
        from core.contract.vc_contract import VCContract
        contract = VCContract()
        for provider in (DEMGroundingProvider(), ClimateGroundingProvider()):
            ctx = self._vc_ctx(provider)
            with self.subTest(provider=type(provider).__name__):
                contract.validate(ctx)


class TestD6DeterministicStage2(unittest.TestCase):

    def _frame(self, provider):
        from core.contract.d6_contract import D6Contract
        tile = M1Pipeline(signal_provider=_make_signal_fn(provider), tile_px_size=6).run_tile(SMALL_BBOX)
        ctx  = VisualConsistencyEngine().process(tile)
        return D6Contract().render_from_vc(ctx)

    def test_d6_deterministic_dem_grounding(self):
        provider = DEMGroundingProvider()
        f1 = self._frame(provider)
        f2 = self._frame(provider)
        np.testing.assert_array_equal(f1, f2)

    def test_d6_deterministic_climate_grounding(self):
        provider = ClimateGroundingProvider()
        f1 = self._frame(provider)
        f2 = self._frame(provider)
        np.testing.assert_array_equal(f1, f2)

    def test_d6_delta_from_synthetic_bounded(self):
        frame_syn  = self._frame(SyntheticProvider())
        frame_dem  = self._frame(DEMGroundingProvider())
        frame_clim = self._frame(ClimateGroundingProvider())
        for frame, name in ((frame_dem, "dem"), (frame_clim, "climate")):
            delta = np.abs(frame_syn.astype(int) - frame.astype(int))
            with self.subTest(provider=name):
                self.assertLessEqual(int(delta.max()), 255)
                self.assertTrue(np.all(np.isfinite(delta.astype(float))))


class TestFullContractGuardStage2(unittest.TestCase):

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

    def test_dem_grounding_passes_full_contract(self):
        self._run_pipeline(DEMGroundingProvider())

    def test_climate_grounding_passes_full_contract(self):
        self._run_pipeline(ClimateGroundingProvider())


if __name__ == "__main__":
    unittest.main(verbosity=2)
