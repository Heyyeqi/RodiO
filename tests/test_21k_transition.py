"""
21.6K Transition Protocol dry-run tests.

This stage is a scale invariance test, not a semantic upgrade. It validates
that 8K and 21K resolution modes use the same spatial formula while preserving
SAL / M1 / VC / D6 output contracts.
"""

from __future__ import annotations

import unittest

import numpy as np

from core.data import RasterLayerRegistry
from core.m1 import M1Pipeline, TileBBox
from core.rendering import D6Renderer, TimeState
from core.runtime import SpatialAlignmentLock, SpatialProfile, SpatialRuntime
from core.sal import SemanticArbitrator
from core.signal.providers import RasterBackedProvider
from core.signal.providers.m1_bridge import M1BridgeProvider
from core.signal.providers.real_world_provider import RealWorldSignalProvider
from core.signal.raster_indexer import RasterIndexer
from core.vc import VisualConsistencyEngine


POINT = (35.5, 31.5)
TILE = TileBBox(lon_min=34.0, lon_max=37.0, lat_min=30.0, lat_max=33.0)


def _uniform_registry(elevation: int = 250, climate: int = 6) -> RasterLayerRegistry:
    reg = RasterLayerRegistry()
    reg.load_layer("ocean", np.full((18, 36), elevation, dtype=np.int16))
    reg.load_layer("dem", np.full((18, 36), elevation, dtype=np.int16))
    reg.load_layer("climate", np.full((18, 36), climate, dtype=np.int16))
    return reg


def _runtime(mode: str = "8k") -> SpatialRuntime:
    runtime = SpatialRuntime(
        real_world_provider=RasterBackedProvider(),
        resolution_mode=mode,
    )
    runtime.set_earth_loader(_uniform_registry())
    return runtime


def _sal_result(runtime: SpatialRuntime):
    provider = M1BridgeProvider(runtime)
    return SemanticArbitrator().resolve(**provider(*POINT))


class TestSpatialProfiles(unittest.TestCase):
    def test_profiles_are_explicit(self):
        profile = SpatialProfile()
        self.assertEqual(profile.get_resolution("8k"), (8192, 4096))
        self.assertEqual(profile.get_resolution("21k"), (21600, 10800))

    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            SpatialProfile().get_resolution("42k")

    def test_8k_behavior_unchanged(self):
        self.assertEqual(SpatialAlignmentLock(8192).normalize(-180.0, 90.0), (0, 0))
        self.assertEqual(SpatialAlignmentLock(8192).normalize(180.0, -90.0), (8191, 4095))

    def test_21k_uses_same_formula_at_different_scale(self):
        x8, y8 = SpatialAlignmentLock(resolution_mode="8k").normalize(*POINT)
        x21, y21 = SpatialAlignmentLock(resolution_mode="21k").normalize(*POINT)
        self.assertAlmostEqual(x8 / 8192.0, x21 / 21600.0, delta=1 / 8192.0)
        self.assertAlmostEqual(y8 / 4096.0, y21 / 10800.0, delta=1 / 4096.0)


class TestResolutionAwareRasterIndexer(unittest.TestCase):
    def test_resolution_mode_is_stored(self):
        idx = RasterIndexer.from_array(np.zeros((18, 36), dtype=np.int16), resolution_mode="21k")
        self.assertEqual(idx.resolution_mode, "21k")
        self.assertEqual(idx.resolution, 21600)

    def test_same_mode_is_deterministic(self):
        arr = np.arange(18 * 36, dtype=np.int32).reshape(18, 36)
        idx = RasterIndexer.from_array(arr, resolution_mode="21k")
        values = [idx.sample(*POINT) for _ in range(10)]
        self.assertEqual(len(set(values)), 1)

    def test_legacy_from_array_resolution_still_works(self):
        arr = np.arange(18 * 36, dtype=np.int32).reshape(18, 36)
        idx = RasterIndexer.from_array(arr)
        self.assertEqual(idx.resolution, 36)
        self.assertIsNone(idx.resolution_mode)


class TestRuntimeScaleSwitch(unittest.TestCase):
    def test_set_resolution_rejects_unknown_mode(self):
        runtime = _runtime("8k")
        with self.assertRaises(ValueError):
            runtime.set_resolution("42k")

    def test_set_resolution_affects_future_binding_only(self):
        runtime = SpatialRuntime(real_world_provider=RasterBackedProvider())
        runtime.set_resolution("21k")
        runtime.set_earth_loader(_uniform_registry())
        self.assertEqual(runtime.resolution_mode, "21k")
        self.assertEqual(runtime._real_world_provider._gebco.resolution_mode, "21k")

    def test_real_world_provider_accepts_resolution_mode(self):
        provider = RealWorldSignalProvider(source_root="/tmp/missing", resolution_mode="21k")
        self.assertEqual(provider.resolution_mode, "21k")

    def test_8k_and_21k_outputs_are_structurally_identical(self):
        s8 = _runtime("8k").query_point(*POINT)
        s21 = _runtime("21k").query_point(*POINT)

        self.assertEqual(type(s8), type(s21))
        self.assertEqual(s8.ocean, s21.ocean)
        self.assertEqual(s8.climate_class, s21.climate_class)
        self.assertEqual(s8.elevation, s21.elevation)
        self.assertEqual(s8.source["ocean_rule"], s21.source["ocean_rule"])


class TestPipelineDryRun(unittest.TestCase):
    def test_sal_winner_margin_unchanged_for_uniform_scale_transition(self):
        r8 = _sal_result(_runtime("8k"))
        r21 = _sal_result(_runtime("21k"))

        self.assertEqual(r8.winner_class, r21.winner_class)
        self.assertAlmostEqual(r8.winner_margin, r21.winner_margin, places=9)
        self.assertAlmostEqual(r8.confidence_score, r21.confidence_score, places=9)

    def test_m1_shape_invariance(self):
        t8 = M1Pipeline(runtime=_runtime("8k"), tile_px_size=6).run_tile(TILE)
        t21 = M1Pipeline(runtime=_runtime("21k"), tile_px_size=6).run_tile(TILE)

        self.assertEqual(t8.shape, t21.shape)
        self.assertEqual(t8.ocean_mask.shape, (6, 6))
        self.assertEqual(t8.biome_mask.shape, t21.biome_mask.shape)
        self.assertEqual(t8.uncertainty_mask.shape, t21.uncertainty_mask.shape)

    def test_vc_temporal_stability_bounded(self):
        tile8 = M1Pipeline(runtime=_runtime("8k"), tile_px_size=6).run_tile(TILE)
        tile21 = M1Pipeline(runtime=_runtime("21k"), tile_px_size=6).run_tile(TILE)
        vc = VisualConsistencyEngine()

        ctx8 = vc.process(tile8)
        ctx21 = vc.process(tile21)

        self.assertEqual(ctx8.base_color_field.shape, ctx21.base_color_field.shape)
        self.assertTrue(np.all(ctx21.temporal_stability_field >= 0.0))
        self.assertTrue(np.all(ctx21.temporal_stability_field <= 1.0))
        self.assertLessEqual(
            float(np.max(np.abs(ctx21.temporal_stability_field - ctx8.temporal_stability_field))),
            1.0,
        )

    def test_d6_rendering_stability(self):
        renderer8 = D6Renderer(_runtime("8k"))
        renderer21 = D6Renderer(_runtime("21k"))
        ts = TimeState(hour=12.0, day_of_year=180, year=2026)

        rgb8 = renderer8.render_point(*POINT, ts)
        rgb21 = renderer21.render_point(*POINT, ts)

        self.assertEqual(rgb8.to_uint8(), rgb21.to_uint8())
        self.assertTrue(all(0 <= channel <= 255 for channel in rgb21.to_uint8()))


if __name__ == "__main__":
    unittest.main()
