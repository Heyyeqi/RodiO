"""
16K canonical BMNG asset bake validation.

These tests verify persisted LOD assets without re-running the expensive full
21K → 16K bake. Small-array tests cover deterministic builder behavior.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from core.rendering import CanonicalTextureBuilder, LODManager


Image.MAX_IMAGE_PIXELS = None

TOPO_21K = Path(
    "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/"
    "topo_bathy/21600x10800_jpeg_preview/world.topo.bathy.200408.3x21600x10800_geo.jpg"
)
BASE_21K = Path(
    "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/"
    "base_map/21600x10800_jpeg_preview/world.200407.3x21600x10800_geo.jpg"
)
TOPO_16K = Path(
    "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/"
    "topo_bathy/lod/world.topo.bathy.200408.16384x8192.jpg"
)
BASE_16K = Path(
    "d5b_processor_v3/source_cache/01_raw/NASA_BlueMarble_BMNG/"
    "base_map/lod/world.base_map.16384x8192.jpg"
)


class TestLOD16KAssetBake(unittest.TestCase):
    def test_output_assets_exist_and_shape_correct(self):
        for path in (TOPO_16K, BASE_16K):
            with self.subTest(path=path):
                self.assertTrue(path.exists(), path)
                with Image.open(path) as im:
                    self.assertEqual(im.size, (16384, 8192))
                    self.assertEqual(im.mode, "RGB")

    def test_source_assets_are_21k_rgb(self):
        for path in (TOPO_21K, BASE_21K):
            with self.subTest(path=path):
                with Image.open(path) as im:
                    self.assertEqual(im.size, (21600, 10800))
                    self.assertEqual(im.mode, "RGB")

    def test_builder_repeatability_small_fixture(self):
        src = np.arange(18 * 36 * 3, dtype=np.uint8).reshape(18, 36, 3)
        builder = CanonicalTextureBuilder()
        a = builder.build(src, (16, 8))
        b = builder.build(src, (16, 8))
        self.assertTrue(np.array_equal(a, b))

    def test_no_sample_color_drift_above_threshold(self):
        # Compare corresponding lon/lat samples in source vs 16K output.
        # JPEG re-encoding and Lanczos resampling allow small deltas; this
        # threshold catches broken channel/order/asset mismatches.
        points = [
            (35.5, 31.5),
            (-150.0, 0.0),
            (121.5, 31.2),
            (-116.86, 36.46),
        ]
        for src_path, out_path in ((TOPO_21K, TOPO_16K), (BASE_21K, BASE_16K)):
            with Image.open(src_path) as src, Image.open(out_path) as out:
                src_px = src.load()
                out_px = out.load()
                for lon, lat in points:
                    sx, sy = _xy(lon, lat, 21600, 10800)
                    ox, oy = _xy(lon, lat, 16384, 8192)
                    delta = max(abs(int(a) - int(b)) for a, b in zip(src_px[sx, sy], out_px[ox, oy]))
                    self.assertLessEqual(delta, 35, (src_path, out_path, lon, lat, delta))

    def test_lod_manager_asset_registry_has_16k_mapping(self):
        registry = LODManager().asset_registry
        self.assertEqual(
            registry["bmng_topo_bathy"]["canonical_16k"],
            "/assets/earth/bmng21k/topo_bathy/lod/world.topo.bathy.200408.16384x8192.jpg",
        )
        self.assertEqual(
            registry["bmng_base_map"]["canonical_16k"],
            "/assets/earth/bmng21k/base_map/lod/world.base_map.16384x8192.jpg",
        )

    def test_frontend_streaming_selects_16k_before_8k(self):
        earth3d = Path("pwa/earth3d.js").read_text()
        lod16k = earth3d.index("lod = '16k'")
        lod8k = earth3d.index("lod = '8k'")
        lod4k = earth3d.index("lod = '4k'")
        self.assertLess(lod16k, lod8k)
        self.assertLess(lod8k, lod4k)
        self.assertIn("maxSize >= 16384", earth3d)
        self.assertIn("maxSize >= 8192", earth3d)
        self.assertIn("/assets/earth/bmng21k/topo_bathy/tiles/", earth3d)

    def test_gpu_max_texture_size_respected(self):
        lod = LODManager()
        self.assertEqual(
            lod.select_render_resolution("21600x10800", max_texture_size=16384),
            (16384, 8192),
        )


def _xy(lon: float, lat: float, width: int, height: int) -> tuple[int, int]:
    x = min(width - 1, max(0, int((lon + 180.0) / 360.0 * width)))
    y = min(height - 1, max(0, int((90.0 - lat) / 180.0 * height)))
    return x, y


if __name__ == "__main__":
    unittest.main()
