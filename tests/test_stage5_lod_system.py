"""
Stage 5 — Earth renderer LOD system tests.

LOD separates 21K computation resolution from GPU-safe canonical render
textures. It must not alter SAL / M1 / VC semantics.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from core.m1 import M1Pipeline, TileBBox
from core.rendering import CanonicalTextureBuilder, D6Renderer, LODManager
from core.runtime import SpatialRuntime
from core.sal import SemanticArbitrator
from core.signal.providers import RasterBackedProvider
from core.signal.providers.synthetic import SyntheticProvider
from core.vc import VisualConsistencyEngine


TILE = TileBBox(lon_min=34.0, lon_max=37.0, lat_min=30.0, lat_max=33.0)


class NullRuntime:
    resolution_mode = "21k"

    def query_point(self, lon, lat):  # pragma: no cover - D6 init tests do not render
        raise AssertionError("query_point should not be called by LOD tests")


class TestLODManager(unittest.TestCase):
    def test_21k_logical_resolution_preserved(self):
        runtime = SpatialRuntime(real_world_provider=RasterBackedProvider(), resolution_mode="21k")
        self.assertEqual(runtime.resolution_mode, "21k")

    def test_render_resolution_capped_at_gpu_limit(self):
        lod = LODManager()
        self.assertEqual(lod.select_render_resolution("21600x10800", capability="high"), (16384, 8192))
        self.assertEqual(lod.select_render_resolution("21600x10800", capability="medium"), (8192, 4096))
        self.assertEqual(lod.select_render_resolution("21600x10800", max_texture_size=4096), (4096, 2048))

    def test_fallback_chain_is_deterministic(self):
        lod = LODManager()
        a = lod.fallback_chain("21600x10800", capability="high")
        b = lod.fallback_chain("21600x10800", capability="high")
        self.assertEqual(a, b)
        self.assertEqual(a, [(16384, 8192), (8192, 4096), (4096, 2048)])


class TestCanonicalTextureBuilder(unittest.TestCase):
    def test_downsample_preserves_aspect_ratio(self):
        src = np.arange(8 * 16 * 3, dtype=np.uint8).reshape(8, 16, 3)
        out = CanonicalTextureBuilder().build(src, (8, 4))
        self.assertEqual(out.shape, (4, 8, 3))
        self.assertEqual(out.dtype, np.uint8)

    def test_downsample_is_deterministic(self):
        src = np.arange(8 * 16 * 3, dtype=np.uint8).reshape(8, 16, 3)
        builder = CanonicalTextureBuilder()
        a = builder.build(src, (8, 4))
        b = builder.build(src, (8, 4))
        self.assertTrue(np.array_equal(a, b))


class TestD6RendererLOD(unittest.TestCase):
    def test_d6_renderer_uses_canonical_render_resolution(self):
        renderer = D6Renderer(NullRuntime(), resolution_mode="21k")
        self.assertEqual(renderer.profile_resolution(), (21600, 10800))
        self.assertEqual(renderer.canonical_render_resolution, (16384, 8192))

    def test_resolution_switch_updates_lod(self):
        renderer = D6Renderer(NullRuntime(), resolution_mode="8k")
        self.assertEqual(renderer.canonical_render_resolution, (8192, 4096))
        renderer.set_resolution("21k")
        self.assertEqual(renderer.canonical_render_resolution, (16384, 8192))


class TestNoSemanticDivergence(unittest.TestCase):
    def test_no_sal_m1_vc_divergence(self):
        provider = SyntheticProvider()
        sal_a = SemanticArbitrator().resolve(**provider(35.5, 31.5))
        sal_b = SemanticArbitrator().resolve(**provider(35.5, 31.5))
        self.assertAlmostEqual(sal_a.winner_margin, sal_b.winner_margin, places=9)

        tile = M1Pipeline(signal_provider=provider, tile_px_size=4).run_tile(TILE)
        ctx = VisualConsistencyEngine().process(tile)
        self.assertEqual(tile.shape, (4, 4))
        self.assertEqual(ctx.coastline_gradient_field.shape, (4, 4))


class TestFrontendLODBinding(unittest.TestCase):
    def test_frontend_streaming_lod_chain_is_declared(self):
        earth3d = Path("pwa/earth3d.js").read_text()
        self.assertIn("resolveEarthTextureLOD", earth3d)
        self.assertIn("FrontendTileStreamingManager", earth3d)
        self.assertIn("maxTextureSize", earth3d)
        self.assertIn("lod = '16k'", earth3d)
        self.assertIn("lod = '8k'", earth3d)
        self.assertIn("lod = '4k'", earth3d)
        self.assertIn("/assets/earth/bmng21k/topo_bathy/tiles/", earth3d)
        self.assertNotIn("earth_day_8k.jpg", earth3d)


if __name__ == "__main__":
    unittest.main()
