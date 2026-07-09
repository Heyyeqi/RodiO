"""
RealSignalProvider v2-lite Tests — Light Grounding Layer

Validates that:
  1. Baseline mode (enable_lite_grounding=False) is byte-identical to v1 stub
  2. Lite mode (enable_lite_grounding=True) runs without crash and produces
     bounded, finite output
  3. SAL structure (winner_margin, winner_class logic) is unchanged
  4. M1 mask SHAPE is identical across modes; only values may differ
  5. VC temporal_stability_field remains in [0, 1] in both modes
  6. SpatialRuntime.enable_lite_grounding() works correctly
  7. All existing contract tests pass (regression guard)
"""

import math
import unittest

import numpy as np

from core.signal.providers.runtime_stub import RuntimeStubProvider
from core.signal.providers.base import BaseSignalProvider
from core.m1 import M1Pipeline, TileBBox
from core.vc import VisualConsistencyEngine
from core.contract import ContractGuard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_POINTS = [
    (0.0,    0.0),   # equator / prime meridian
    (45.0,  30.0),   # temperate land proxy
    (-90.0, -45.0),  # southern temperate
    (10.0,  70.0),   # polar — lite ocean heuristic may trigger
    (0.0,  -70.0),   # polar South
    (170.0, 10.0),   # tropical Pacific
]

SMALL_BBOX = TileBBox(lon_min=-15, lon_max=15, lat_min=-10, lat_max=10)
POLAR_BBOX = TileBBox(lon_min=-15, lon_max=15, lat_min=55,  lat_max=75)


def _make_pipeline(provider, tile_px=6):
    return M1Pipeline(signal_provider=provider, tile_px_size=tile_px)


# ---------------------------------------------------------------------------
# 1. Baseline mode — v1 compatibility
# ---------------------------------------------------------------------------

class TestBaselineMode(unittest.TestCase):
    """enable_lite_grounding=False must be identical to v1 stub."""

    def setUp(self):
        self.stub_v1 = RuntimeStubProvider()                        # old default
        self.stub_baseline = RuntimeStubProvider(enable_lite_grounding=False)

    def test_get_dem_identical_to_v1(self):
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(self.stub_v1.get_dem(lon, lat),
                                 self.stub_baseline.get_dem(lon, lat))

    def test_get_ocean_identical_to_v1(self):
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(self.stub_v1.get_ocean(lon, lat),
                                 self.stub_baseline.get_ocean(lon, lat))

    def test_get_climate_identical_to_v1(self):
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(self.stub_v1.get_climate(lon, lat),
                                 self.stub_baseline.get_climate(lon, lat))

    def test_get_landcover_identical_to_v1(self):
        for lon, lat in SAMPLE_POINTS:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(self.stub_v1.get_landcover(lon, lat),
                                 self.stub_baseline.get_landcover(lon, lat))

    def test_baseline_dem_is_zero(self):
        for lon, lat in SAMPLE_POINTS:
            self.assertEqual(self.stub_baseline.get_dem(lon, lat), 0.0)

    def test_baseline_ocean_is_false(self):
        for lon, lat in SAMPLE_POINTS:
            self.assertFalse(self.stub_baseline.get_ocean(lon, lat))

    def test_baseline_climate_is_none(self):
        for lon, lat in SAMPLE_POINTS:
            self.assertIsNone(self.stub_baseline.get_climate(lon, lat))

    def test_m1_tile_shapes_identical_baseline_vs_v1(self):
        """M1 mask shapes must be identical regardless of mode in baseline."""

        def _as_provider(stub):
            # Wrap stub as a callable SAL signal provider (land-always synthetic)
            def _provider(lon, lat):
                return dict(
                    dem_signal="land" if stub.get_dem(lon, lat) >= 0 else "ocean",
                    dem_confidence=0.7,
                    climate_signal="land",
                    climate_confidence=0.6,
                    ocean_signal="ocean" if stub.get_ocean(lon, lat) else "land",
                    ocean_confidence=0.7,
                    landcover_signal="land",
                    landcover_confidence=0.6,
                )
            return _provider

        tile_v1       = _make_pipeline(_as_provider(self.stub_v1)).run_tile(SMALL_BBOX)
        tile_baseline = _make_pipeline(_as_provider(self.stub_baseline)).run_tile(SMALL_BBOX)

        self.assertEqual(tile_v1.shape, tile_baseline.shape)
        np.testing.assert_array_equal(tile_v1.biome_mask, tile_baseline.biome_mask)


# ---------------------------------------------------------------------------
# 2. Lite mode — proxy values are bounded and deterministic
# ---------------------------------------------------------------------------

class TestLiteMode(unittest.TestCase):
    """enable_lite_grounding=True must produce bounded, deterministic output."""

    def setUp(self):
        self.lite = RuntimeStubProvider(enable_lite_grounding=True)

    def test_get_dem_is_bounded(self):
        for lon, lat in SAMPLE_POINTS:
            v = self.lite.get_dem(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertIsInstance(v, float)
                self.assertGreater(v, -1001.0)
                self.assertLess(v, 1001.0)

    def test_get_dem_matches_formula(self):
        for lon, lat in SAMPLE_POINTS:
            expected = math.sin(lat * 0.01) * 1000.0
            actual = self.lite.get_dem(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertAlmostEqual(actual, expected, places=9)

    def test_get_dem_is_deterministic(self):
        for lon, lat in SAMPLE_POINTS:
            v1 = self.lite.get_dem(lon, lat)
            v2 = self.lite.get_dem(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(v1, v2)

    def test_get_ocean_is_bool(self):
        for lon, lat in SAMPLE_POINTS:
            v = self.lite.get_ocean(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertIsInstance(v, bool)

    def test_get_ocean_polar_heuristic(self):
        # abs(lat)>60, abs(lon)<20 → True
        self.assertTrue(self.lite.get_ocean(10.0, 70.0))
        self.assertTrue(self.lite.get_ocean(-5.0, -65.0))
        # not polar or not near meridian → False
        self.assertFalse(self.lite.get_ocean(0.0, 0.0))
        self.assertFalse(self.lite.get_ocean(90.0, 65.0))   # abs(lon) >= 20

    def test_get_climate_bucket_tropical(self):
        self.assertEqual(self.lite.get_climate(0.0, 0.0),  1)
        self.assertEqual(self.lite.get_climate(0.0, 22.9), 1)

    def test_get_climate_bucket_temperate(self):
        self.assertEqual(self.lite.get_climate(0.0, 30.0), 2)
        self.assertEqual(self.lite.get_climate(0.0, 44.9), 2)

    def test_get_climate_bucket_polar(self):
        self.assertEqual(self.lite.get_climate(0.0, 50.0), 3)
        self.assertEqual(self.lite.get_climate(0.0, 80.0), 3)

    def test_get_climate_is_int(self):
        for lon, lat in SAMPLE_POINTS:
            v = self.lite.get_climate(lon, lat)
            with self.subTest(lon=lon, lat=lat):
                self.assertIsNotNone(v)
                self.assertIsInstance(v, int)
                self.assertIn(v, (1, 2, 3))

    def test_get_landcover_still_zero(self):
        for lon, lat in SAMPLE_POINTS:
            self.assertEqual(self.lite.get_landcover(lon, lat), 0)

    def test_is_still_base_signal_provider(self):
        self.assertIsInstance(self.lite, BaseSignalProvider)


# ---------------------------------------------------------------------------
# 3. Mode switch — toggling enable_lite_grounding on an existing instance
# ---------------------------------------------------------------------------

class TestModeSwitching(unittest.TestCase):

    def test_default_is_false(self):
        p = RuntimeStubProvider()
        self.assertFalse(p.enable_lite_grounding)

    def test_explicit_false(self):
        p = RuntimeStubProvider(enable_lite_grounding=False)
        self.assertFalse(p.enable_lite_grounding)

    def test_explicit_true(self):
        p = RuntimeStubProvider(enable_lite_grounding=True)
        self.assertTrue(p.enable_lite_grounding)

    def test_toggle_at_runtime(self):
        p = RuntimeStubProvider(enable_lite_grounding=False)
        self.assertEqual(p.get_dem(0.0, 45.0), 0.0)
        p.enable_lite_grounding = True
        expected = math.sin(45.0 * 0.01) * 1000.0
        self.assertAlmostEqual(p.get_dem(0.0, 45.0), expected, places=9)

    def test_spatial_runtime_enable_lite_grounding_method(self):
        from core.runtime.spatial_runtime import SpatialRuntime
        stub = RuntimeStubProvider(enable_lite_grounding=False)
        runtime = SpatialRuntime(signal_provider=stub)
        self.assertFalse(stub.enable_lite_grounding)
        runtime.enable_lite_grounding()
        self.assertTrue(stub.enable_lite_grounding)

    def test_spatial_runtime_enable_lite_grounding_raises_on_dem_registry(self):
        # A runtime using dem_registry (no signal_provider) cannot use lite grounding.
        # We can't test this without a real dem_registry, so just verify
        # that enable_lite_grounding() raises when signal_provider is None.
        from core.runtime.spatial_runtime import SpatialRuntime
        stub = RuntimeStubProvider()
        runtime = SpatialRuntime(signal_provider=stub)
        runtime._signal_provider = None  # simulate no provider
        with self.assertRaises(ValueError):
            runtime.enable_lite_grounding()

    def test_spatial_runtime_enable_raises_on_incompatible_provider(self):
        from core.runtime.spatial_runtime import SpatialRuntime
        from core.signal.providers.synthetic import SyntheticProvider

        class NoLiteAttr(BaseSignalProvider):
            def get_dem(self, lon, lat): return 0.0
            def get_landcover(self, lon, lat): return 0
            def get_climate(self, lon, lat): return None
            def get_ocean(self, lon, lat): return False

        runtime = SpatialRuntime(signal_provider=NoLiteAttr())
        with self.assertRaises(ValueError):
            runtime.enable_lite_grounding()


# ---------------------------------------------------------------------------
# 4. SAL structure unchanged
# ---------------------------------------------------------------------------

class TestSALStructureUnchanged(unittest.TestCase):
    """
    SAL logic / algorithm must be identical regardless of signal inputs.
    We verify structural properties: winner_class == argmax, ratio ≥ 1,
    margin ∈ [0,1]. Actual values may differ between modes because inputs differ.
    """

    def _resolve(self, provider):
        from core.sal import SemanticArbitrator
        # Build SAL kwargs from provider at a temperate land point
        lon, lat = 20.0, 35.0
        dem  = provider.get_dem(lon, lat)
        ocean = provider.get_ocean(lon, lat)
        climate = provider.get_climate(lon, lat)
        sal = SemanticArbitrator()
        return sal.resolve(
            dem_signal="ocean" if dem < 0 else "land",
            dem_confidence=min(0.55 + abs(dem) / 3000.0 * 0.4, 0.95),
            climate_signal="land" if climate is not None else None,
            climate_confidence=0.8 if climate is not None else 0.0,
            ocean_signal="ocean" if ocean else "land",
            ocean_confidence=0.75,
            landcover_signal="land",
            landcover_confidence=0.6,
        )

    def test_sal_structural_invariants_baseline(self):
        result = self._resolve(RuntimeStubProvider(enable_lite_grounding=False))
        argmax = max(result.probability_map, key=lambda k: result.probability_map[k])
        self.assertEqual(result.winner_class, argmax)
        self.assertGreaterEqual(result.winner_ratio, 1.0)
        self.assertGreaterEqual(result.winner_margin, 0.0)
        self.assertLessEqual(result.winner_margin, 1.0)

    def test_sal_structural_invariants_lite(self):
        result = self._resolve(RuntimeStubProvider(enable_lite_grounding=True))
        argmax = max(result.probability_map, key=lambda k: result.probability_map[k])
        self.assertEqual(result.winner_class, argmax)
        self.assertGreaterEqual(result.winner_ratio, 1.0)
        self.assertGreaterEqual(result.winner_margin, 0.0)
        self.assertLessEqual(result.winner_margin, 1.0)

    def test_sal_deterministic_in_both_modes(self):
        for flag in (False, True):
            p = RuntimeStubProvider(enable_lite_grounding=flag)
            r1 = self._resolve(p)
            r2 = self._resolve(p)
            with self.subTest(lite=flag):
                self.assertEqual(r1.final_class, r2.final_class)
                self.assertAlmostEqual(r1.winner_margin, r2.winner_margin, places=9)


# ---------------------------------------------------------------------------
# 5. M1 mask shape identical across modes
# ---------------------------------------------------------------------------

class TestM1MaskShape(unittest.TestCase):

    def _tile_via_provider(self, provider, bbox=SMALL_BBOX, tile_px=6):
        def _signal_fn(lon, lat):
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
        return M1Pipeline(signal_provider=_signal_fn, tile_px_size=tile_px).run_tile(bbox)

    def test_shape_identical_baseline_vs_lite(self):
        tile_b = self._tile_via_provider(RuntimeStubProvider(enable_lite_grounding=False))
        tile_l = self._tile_via_provider(RuntimeStubProvider(enable_lite_grounding=True))
        self.assertEqual(tile_b.shape, tile_l.shape)

    def test_ocean_mask_shape_preserved(self):
        tile_b = self._tile_via_provider(RuntimeStubProvider(enable_lite_grounding=False))
        tile_l = self._tile_via_provider(RuntimeStubProvider(enable_lite_grounding=True))
        self.assertEqual(tile_b.ocean_mask.shape, tile_l.ocean_mask.shape)

    def test_biome_mask_shape_preserved(self):
        tile_b = self._tile_via_provider(RuntimeStubProvider(enable_lite_grounding=False))
        tile_l = self._tile_via_provider(RuntimeStubProvider(enable_lite_grounding=True))
        self.assertEqual(tile_b.biome_mask.shape, tile_l.biome_mask.shape)

    def test_uncertainty_mask_bounded_in_both_modes(self):
        for flag in (False, True):
            tile = self._tile_via_provider(RuntimeStubProvider(enable_lite_grounding=flag))
            unc = tile.uncertainty_mask.astype(np.float32)
            with self.subTest(lite=flag):
                self.assertGreaterEqual(float(unc.min()), 0.0)
                self.assertLessEqual(float(unc.max()), 1.0)

    def test_polar_bbox_lite_may_differ_but_shape_identical(self):
        tile_b = self._tile_via_provider(RuntimeStubProvider(enable_lite_grounding=False),
                                         bbox=POLAR_BBOX)
        tile_l = self._tile_via_provider(RuntimeStubProvider(enable_lite_grounding=True),
                                         bbox=POLAR_BBOX)
        self.assertEqual(tile_b.shape, tile_l.shape)

    def test_m1_contract_passes_both_modes(self):
        from core.contract.m1_contract import M1Contract
        contract = M1Contract()
        for flag in (False, True):
            tile = self._tile_via_provider(RuntimeStubProvider(enable_lite_grounding=flag))
            with self.subTest(lite=flag):
                contract.validate(tile)   # must not raise


# ---------------------------------------------------------------------------
# 6. VC temporal stability unchanged
# ---------------------------------------------------------------------------

class TestVCTemporalStability(unittest.TestCase):

    def _vc_context(self, provider, bbox=SMALL_BBOX, tile_px=6):
        def _signal_fn(lon, lat):
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
        tile = M1Pipeline(signal_provider=_signal_fn, tile_px_size=tile_px).run_tile(bbox)
        return VisualConsistencyEngine().process(tile)

    def test_temporal_stability_in_range_baseline(self):
        ctx = self._vc_context(RuntimeStubProvider(enable_lite_grounding=False))
        stab = ctx.temporal_stability_field.astype(np.float32)
        self.assertGreaterEqual(float(stab.min()), 0.0 - 1e-4)
        self.assertLessEqual(float(stab.max()), 1.0 + 1e-4)

    def test_temporal_stability_in_range_lite(self):
        ctx = self._vc_context(RuntimeStubProvider(enable_lite_grounding=True))
        stab = ctx.temporal_stability_field.astype(np.float32)
        self.assertGreaterEqual(float(stab.min()), 0.0 - 1e-4)
        self.assertLessEqual(float(stab.max()), 1.0 + 1e-4)

    def test_vc_shape_identical_across_modes(self):
        ctx_b = self._vc_context(RuntimeStubProvider(enable_lite_grounding=False))
        ctx_l = self._vc_context(RuntimeStubProvider(enable_lite_grounding=True))
        self.assertEqual(ctx_b.shape, ctx_l.shape)

    def test_vc_coastline_gradient_bounded_both_modes(self):
        for flag in (False, True):
            ctx = self._vc_context(RuntimeStubProvider(enable_lite_grounding=flag))
            grad = ctx.coastline_gradient_field.astype(np.float32)
            with self.subTest(lite=flag):
                self.assertGreaterEqual(float(grad.min()), 0.0 - 1e-4)
                self.assertLessEqual(float(grad.max()), 1.0 + 1e-4)

    def test_vc_contract_passes_both_modes(self):
        from core.contract.vc_contract import VCContract
        contract = VCContract()
        for flag in (False, True):
            ctx = self._vc_context(RuntimeStubProvider(enable_lite_grounding=flag))
            with self.subTest(lite=flag):
                contract.validate(ctx)


# ---------------------------------------------------------------------------
# 7. Baseline vs lite bounded delta
# ---------------------------------------------------------------------------

class TestBaselineVsLiteBoundedDelta(unittest.TestCase):
    """
    Output differences between baseline and lite must be finite and bounded.
    We do NOT require identity — lite grounding is designed to change values.
    """

    def _tile(self, provider, bbox=SMALL_BBOX, tile_px=6):
        def _signal_fn(lon, lat):
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
        return M1Pipeline(signal_provider=_signal_fn, tile_px_size=tile_px).run_tile(bbox)

    def test_uncertainty_delta_is_finite(self):
        tile_b = self._tile(RuntimeStubProvider(enable_lite_grounding=False))
        tile_l = self._tile(RuntimeStubProvider(enable_lite_grounding=True))
        delta = np.abs(tile_b.uncertainty_mask.astype(np.float32) -
                       tile_l.uncertainty_mask.astype(np.float32))
        self.assertTrue(np.all(np.isfinite(delta)),
                        "uncertainty delta contains NaN or Inf")
        self.assertLessEqual(float(delta.max()), 1.0)

    def test_confidence_delta_is_finite(self):
        tile_b = self._tile(RuntimeStubProvider(enable_lite_grounding=False))
        tile_l = self._tile(RuntimeStubProvider(enable_lite_grounding=True))
        delta = np.abs(tile_b.confidence_mask.astype(np.float32) -
                       tile_l.confidence_mask.astype(np.float32))
        self.assertTrue(np.all(np.isfinite(delta)),
                        "confidence delta contains NaN or Inf")
        self.assertLessEqual(float(delta.max()), 1.0)

    def test_d6_frame_delta_bounded(self):
        from core.contract.d6_contract import D6Contract
        d6 = D6Contract()

        def _ctx(provider):
            def _signal_fn(lon, lat):
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
            tile = M1Pipeline(signal_provider=_signal_fn, tile_px_size=6).run_tile(SMALL_BBOX)
            return VisualConsistencyEngine().process(tile)

        frame_b = d6.render_from_vc(_ctx(RuntimeStubProvider(enable_lite_grounding=False)))
        frame_l = d6.render_from_vc(_ctx(RuntimeStubProvider(enable_lite_grounding=True)))

        self.assertEqual(frame_b.shape, frame_l.shape)
        delta = np.abs(frame_b.astype(int) - frame_l.astype(int))
        self.assertLessEqual(int(delta.max()), 255)   # bounded by uint8 range
        self.assertTrue(np.all(np.isfinite(delta.astype(float))))


# ---------------------------------------------------------------------------
# 8. Full contract guard — both modes pass
# ---------------------------------------------------------------------------

class TestContractGuardBothModes(unittest.TestCase):

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

        def _signal_fn(lon, lat):
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
        tile = M1Pipeline(signal_provider=_signal_fn, tile_px_size=6).run_tile(SMALL_BBOX)
        guard.validate_m1(tile)

        ctx = VisualConsistencyEngine().process(tile)
        guard.validate_vc(ctx)

        frame = guard.render_d6_from_vc(ctx)
        guard.validate_d6(frame)

    def test_baseline_passes_full_contract(self):
        self._run_pipeline(RuntimeStubProvider(enable_lite_grounding=False))

    def test_lite_passes_full_contract(self):
        self._run_pipeline(RuntimeStubProvider(enable_lite_grounding=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
