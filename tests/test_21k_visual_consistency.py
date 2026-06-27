"""
21.6K Visual Integration Layer tests.

Validates that resolution_mode reaches M1 / VC / D6 as visual sampling
metadata without changing SAL semantics or allocating a full 21K mask.
"""

from __future__ import annotations

import unittest

import numpy as np

from core.data import RasterLayerRegistry
from core.m1 import M1Pipeline, SemanticMaskTile, TileBBox
from core.rendering import D6Renderer, TimeState
from core.runtime import SpatialRuntime
from core.sal import SemanticArbitrator
from core.signal.providers import RasterBackedProvider
from core.signal.providers.m1_bridge import M1BridgeProvider
from core.vc import VisualConsistencyEngine


POINT = (35.5, 31.5)
TILE = TileBBox(lon_min=34.0, lon_max=37.0, lat_min=30.0, lat_max=33.0)


def _registry(elevation: int = 250, climate: int = 6) -> RasterLayerRegistry:
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
    runtime.set_earth_loader(_registry())
    return runtime


def _sal_margin(runtime: SpatialRuntime) -> float:
    signals = M1BridgeProvider(runtime)(*POINT)
    return SemanticArbitrator().resolve(**signals).winner_margin


def _coastal_tile() -> SemanticMaskTile:
    ocean = np.zeros((8, 8), dtype=bool)
    ocean[:, :4] = True
    land = ~ocean
    biome = np.where(ocean, 0, 2).astype(np.uint8)
    uncertainty = np.full((8, 8), 0.45, dtype=np.float32)
    confidence = np.full((8, 8), 0.65, dtype=np.float32)
    ocean_prob = np.where(ocean, 0.75, 0.10).astype(np.float32)
    return SemanticMaskTile(
        bbox=TILE,
        ocean_mask=ocean,
        land_mask=land,
        biome_mask=biome,
        uncertainty_mask=uncertainty,
        confidence_mask=confidence,
        ocean_prob_mask=ocean_prob,
    )


class Test21KVisualPropagation(unittest.TestCase):
    def test_runtime_propagates_resolution_to_visual_modules(self):
        runtime = _runtime("8k")
        m1 = M1Pipeline(runtime=runtime, tile_px_size=6)
        vc = VisualConsistencyEngine(m1=m1)
        d6 = D6Renderer(runtime)

        runtime.attach_visual_pipeline(m1=m1, vc=vc, d6_renderer=d6)
        runtime.set_resolution("21k")

        self.assertEqual(runtime.resolution_mode, "21k")
        self.assertEqual(m1.resolution_mode, "21k")
        self.assertEqual(vc.resolution_mode, "21k")
        self.assertEqual(d6.resolution_mode, "21k")

    def test_d6_default_window_density_increases_in_21k(self):
        renderer8 = D6Renderer(_runtime("8k"))
        renderer21 = D6Renderer(_runtime("21k"))

        self.assertEqual(renderer8.default_window_shape(), (64, 64))
        self.assertGreater(renderer21.default_window_shape()[0], 64)

        ts = TimeState(hour=12.0, day_of_year=180, year=2026)
        out8 = renderer8.render_window((34.0, 30.0, 37.0, 33.0), ts)
        out21 = renderer21.render_window((34.0, 30.0, 37.0, 33.0), ts)

        self.assertEqual(out8.shape, (64, 64, 3))
        self.assertEqual(out21.shape[2], 3)
        self.assertGreater(out21.shape[0], out8.shape[0])
        self.assertGreater(out21.shape[1], out8.shape[1])

    def test_d6_point_render_is_deterministic(self):
        renderer = D6Renderer(_runtime("21k"))
        ts = TimeState(hour=12.0, day_of_year=180, year=2026)

        rgb1 = renderer.render_point(*POINT, ts).to_uint8()
        rgb2 = renderer.render_point(*POINT, ts).to_uint8()

        self.assertEqual(rgb1, rgb2)
        self.assertTrue(all(0 <= channel <= 255 for channel in rgb1))

    def test_m1_21k_shape_is_profile_not_allocated_mask(self):
        runtime = _runtime("21k")
        m1 = M1Pipeline(runtime=runtime, tile_px_size=6)

        self.assertEqual(m1.full_resolution_shape(), (10800, 21600))
        self.assertGreater(m1.visual_tile_px_size(), 6)

        tile = m1.run_tile(TILE)
        self.assertEqual(tile.shape, (6, 6))

    def test_sal_winner_margin_unchanged_by_visual_mode(self):
        self.assertAlmostEqual(_sal_margin(_runtime("8k")), _sal_margin(_runtime("21k")), places=9)


class Test21KVCIntegration(unittest.TestCase):
    def test_vc_21k_uses_finer_smoothing_density(self):
        vc8 = VisualConsistencyEngine(resolution_mode="8k")
        vc21 = VisualConsistencyEngine(resolution_mode="21k")

        self.assertEqual(vc8.pixel_density(), 1.0)
        self.assertLess(vc21.pixel_density(), vc8.pixel_density())
        self.assertLess(vc21._smoother.base_sigma, vc8._smoother.base_sigma)

    def test_vc_gradient_smoothness_bounded(self):
        tile = _coastal_tile()
        ctx8 = VisualConsistencyEngine(resolution_mode="8k").process(tile)
        ctx21 = VisualConsistencyEngine(resolution_mode="21k").process(tile)

        self.assertEqual(ctx8.shape, ctx21.shape)
        self.assertTrue(np.all(ctx21.coastline_gradient_field >= 0.0))
        self.assertTrue(np.all(ctx21.coastline_gradient_field <= 1.0))
        self.assertLessEqual(
            float(np.max(np.abs(ctx21.coastline_gradient_field - ctx8.coastline_gradient_field))),
            1.0,
        )
        self.assertTrue(ctx21.has_gradient_transition(tolerance=0.01))


if __name__ == "__main__":
    unittest.main()
