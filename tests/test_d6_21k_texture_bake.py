"""
D6 21K texture bake + frontend binding tests.

This is a visual activation layer. It must not change SAL / M1 / VC semantics.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from core.m1 import M1Pipeline, TileBBox
from core.rendering import D6Renderer, D6TextureBaker, TimeState, export_texture_payload
from core.sal import SemanticArbitrator
from core.signal.providers.synthetic import SyntheticProvider
from core.vc import VisualConsistencyEngine


TILE = TileBBox(lon_min=34.0, lon_max=37.0, lat_min=30.0, lat_max=33.0)
BMNG_21K_JPEG = Path(
    "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/"
    "topo_bathy/21600x10800_jpeg_preview/world.topo.bathy.200408.3x21600x10800_geo.jpg"
)


class NullRuntime:
    resolution_mode = "21k"

    def query_point(self, lon, lat):
        from core.runtime.runtime_types import FeatureVector, SpatialState

        fv = FeatureVector(elevation=120.0, ocean_flag=0.0, climate_class=6.0, slope_proxy=0.0)
        return SpatialState(
            elevation=120.0,
            ocean=False,
            climate_class=6,
            biome_proxy=0.5,
            slope_proxy=0.0,
            feature_vector=fv,
            normalized_vector=fv,
            source={"ocean_rule": "test"},
        )


def _rgb_fixture():
    base = np.zeros((4, 8, 3), dtype=np.uint8)
    base[:, :, 0] = 20
    base[:, :, 1] = 40
    base[:, :, 2] = 80
    topo = base.copy()
    topo[:, :, 0] = 35
    topo[:, :, 1] = 45
    topo[:, :, 2] = 70
    return base, topo


class TestD621KTextureBake(unittest.TestCase):
    def test_21k_texture_output_shape_correct(self):
        base, topo = _rgb_fixture()
        textures = D6TextureBaker("21k").bake(base, topo)

        self.assertEqual(textures["base_texture"].shape, (4, 8, 3))
        self.assertEqual(textures["overlay_texture"].shape, (4, 8, 3))
        self.assertEqual(textures["resolution"], "8x4")
        self.assertEqual(textures["resolution_mode"], "21k")
        self.assertEqual(textures["base_texture"].dtype, np.uint8)

    def test_deterministic_bake_output(self):
        base, topo = _rgb_fixture()
        baker = D6TextureBaker("21k")
        a = baker.bake(base, topo)
        b = baker.bake(base, topo)

        self.assertTrue(np.array_equal(a["base_texture"], b["base_texture"]))
        self.assertTrue(np.array_equal(a["overlay_texture"], b["overlay_texture"]))

    def test_frontend_payload_structure_valid_raw(self):
        base, topo = _rgb_fixture()
        payload = export_texture_payload(D6TextureBaker("21k").bake(base, topo), fmt="raw")

        self.assertEqual(payload["resolution"], "8x4")
        self.assertEqual(payload["resolutionMode"], "21k")
        self.assertEqual(payload["format"], "raw")
        self.assertEqual(payload["width"], 8)
        self.assertEqual(payload["height"], 4)
        self.assertEqual(len(payload["baseTexture"]), 4 * 8 * 3)
        self.assertEqual(len(payload["overlayTexture"]), 4 * 8 * 3)

    def test_frontend_payload_structure_valid_png(self):
        base, topo = _rgb_fixture()
        payload = export_texture_payload(D6TextureBaker("21k").bake(base, topo), fmt="png")

        self.assertEqual(payload["format"], "png")
        self.assertTrue(payload["baseTexture"].startswith(b"\x89PNG"))
        self.assertTrue(payload["overlayTexture"].startswith(b"\x89PNG"))

    def test_d6_renderer_explicit_texture_bake(self):
        base, topo = _rgb_fixture()
        renderer = D6Renderer(NullRuntime(), resolution_mode="21k")

        textures = renderer.render_window(
            (34.0, 30.0, 37.0, 33.0),
            TimeState(hour=12.0),
            texture_bake=True,
            bmng_base=base,
            bmng_topo=topo,
        )

        self.assertIn("base_texture", textures)
        self.assertIn("overlay_texture", textures)

    def test_fallback_to_8k_if_21k_missing(self):
        renderer = D6Renderer(NullRuntime(), resolution_mode="8k")
        out = renderer.render_window(
            (34.0, 30.0, 37.0, 33.0),
            TimeState(hour=12.0),
            width=4,
            height=4,
        )
        self.assertEqual(out.shape, (4, 4, 3))

        renderer21 = D6Renderer(NullRuntime(), resolution_mode="21k")
        with self.assertRaises(ValueError):
            renderer21.render_window(
                (34.0, 30.0, 37.0, 33.0),
                TimeState(hour=12.0),
                texture_bake=True,
            )

    def test_no_sal_m1_vc_drift(self):
        provider = SyntheticProvider()
        sal_a = SemanticArbitrator().resolve(**provider(35.5, 31.5))
        sal_b = SemanticArbitrator().resolve(**provider(35.5, 31.5))
        self.assertAlmostEqual(sal_a.winner_margin, sal_b.winner_margin, places=9)

        tile = M1Pipeline(signal_provider=provider, tile_px_size=4).run_tile(TILE)
        ctx = VisualConsistencyEngine().process(tile)

        self.assertEqual(tile.shape, (4, 4))
        self.assertEqual(ctx.base_color_field.shape, (4, 4, 3))

    def test_frontend_binding_candidate_exists(self):
        self.assertTrue(BMNG_21K_JPEG.exists())
        earth3d = Path("pwa/earth3d.js").read_text()
        server = Path("server.js").read_text()

        self.assertIn("bmng21k_stream", earth3d)
        self.assertIn("/assets/earth/bmng21k/topo_bathy/tiles/", earth3d)
        self.assertIn("FrontendTileStreamingManager", earth3d)
        self.assertNotIn("bmng_topo_bathy_21k:", earth3d)
        self.assertIn("/assets/earth/bmng21k", server)


if __name__ == "__main__":
    unittest.main()
