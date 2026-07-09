"""Stage 12 BMNG tile data production pipeline tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from core.data.earth_tile_exporter import EarthTileExporter, sha256_file
from core.data.earth_tile_generator import EarthTileGenerator, TileCoordinateSystem


TEST_LOD_PYRAMID = {
    "l0": (16, 8),
    "16k": (16, 8),
    "8k": (8, 4),
    "4k": (4, 2),
}
TEST_TILE_SIZE_BY_LOD = {
    "16k": 4,
    "8k": 4,
    "4k": 2,
}


def write_fixture(path: Path, size: tuple[int, int] = (16, 8)) -> None:
    width, height = size
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            arr[y, x] = ((x * 11) % 256, (y * 23) % 256, ((x + y) * 7) % 256)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, "RGB").save(path, format="JPEG", quality=95, subsampling=0)


def build_source_cache(root: Path) -> None:
    write_fixture(
        root / "topo_bathy/21600x10800_jpeg_preview/world.topo.bathy.200408.3x21600x10800_geo.jpg"
    )
    write_fixture(
        root / "base_map/21600x10800_jpeg_preview/world.200408.3x21600x10800_geo.jpg"
    )


class TestTileCoordinateSystem(unittest.TestCase):
    def test_lonlat_mapping_correctness(self):
        coords = TileCoordinateSystem(TEST_LOD_PYRAMID, TEST_TILE_SIZE_BY_LOD)
        self.assertEqual(coords.compute_tile_grid("16k"), (4, 2))
        self.assertEqual(coords.lonlat_to_tile(-180, 90, "16k"), (0, 0))
        self.assertEqual(coords.lonlat_to_tile(179.999, -89.999, "16k"), (3, 1))
        self.assertEqual(coords.lonlat_to_tile(0, 0, "16k"), (2, 1))
        self.assertEqual(coords.tile_to_bounds(0, 0, "16k"), (-180.0, 0.0, -90.0, 90.0))

    def test_lod_pyramid_structure(self):
        generator = EarthTileGenerator(
            "unused.jpg",
            tile_size=TEST_TILE_SIZE_BY_LOD,
            lod_pyramid=TEST_LOD_PYRAMID,
        )
        self.assertEqual(generator.compute_tile_grid("16k"), (4, 2))
        self.assertEqual(generator.compute_tile_grid("8k"), (2, 1))
        self.assertEqual(generator.compute_tile_grid("4k"), (2, 1))
        with self.assertRaises(ValueError):
            list(generator.slice_tiles("l0"))


class TestEarthTilePipeline(unittest.TestCase):
    def test_tile_grid_completeness_and_naming(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "topo_bathy/source.jpg"
            write_fixture(source)
            generator = EarthTileGenerator(
                source,
                tile_size=TEST_TILE_SIZE_BY_LOD,
                lod_pyramid=TEST_LOD_PYRAMID,
            )

            paths = generator.generate_lod("16k")

            self.assertEqual(len(paths), 8)
            self.assertTrue((root / "topo_bathy/tiles/16k/tile_0_0.jpg").exists())
            self.assertTrue((root / "topo_bathy/tiles/16k/tile_3_1.jpg").exists())
            self.assertEqual(generator.missing_tiles("16k"), [])

    def test_reproducibility_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "topo_bathy/source.jpg"
            write_fixture(source)
            generator = EarthTileGenerator(
                source,
                tile_size=TEST_TILE_SIZE_BY_LOD,
                lod_pyramid=TEST_LOD_PYRAMID,
                overwrite=True,
            )

            generator.generate_lod("8k")
            first = sha256_file(root / "topo_bathy/tiles/8k/tile_0_0.jpg")
            generator.generate_lod("8k")
            second = sha256_file(root / "topo_bathy/tiles/8k/tile_0_0.jpg")

            self.assertEqual(first, second)

    def test_manifest_correctness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_source_cache(root)
            exporter = EarthTileExporter(
                root,
                tile_size_by_lod=TEST_TILE_SIZE_BY_LOD,
                lod_pyramid=TEST_LOD_PYRAMID,
            )

            result = exporter.generate_all(datasets=("topo_bathy",), lods=("8k",))[0]
            manifest = json.loads(result.manifest_path.read_text())

            self.assertTrue(result.complete)
            self.assertEqual(manifest["lod"], "8k")
            self.assertEqual(manifest["tiles_x"], 2)
            self.assertEqual(manifest["tiles_y"], 1)
            self.assertEqual(manifest["source"], "BMNG_21K")
            self.assertEqual(manifest["projection"], "EPSG:4326")
            self.assertEqual(manifest["tile_pattern"], "tile_{x}_{y}.jpg")
            self.assertTrue(manifest["complete"])

    def test_no_missing_tiles_in_lod_16k_and_8k(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_source_cache(root)
            exporter = EarthTileExporter(
                root,
                tile_size_by_lod=TEST_TILE_SIZE_BY_LOD,
                lod_pyramid=TEST_LOD_PYRAMID,
            )

            exporter.generate_all(datasets=("topo_bathy", "base_map"), lods=("16k", "8k"))
            missing = exporter.validate_completeness(datasets=("topo_bathy", "base_map"), lods=("16k", "8k"))

            self.assertEqual(missing["topo_bathy"]["16k"], [])
            self.assertEqual(missing["topo_bathy"]["8k"], [])
            self.assertEqual(missing["base_map"]["16k"], [])
            self.assertEqual(missing["base_map"]["8k"], [])

    def test_restart_safe_generation_preserves_existing_tiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "topo_bathy/source.jpg"
            write_fixture(source)
            generator = EarthTileGenerator(
                source,
                tile_size=TEST_TILE_SIZE_BY_LOD,
                lod_pyramid=TEST_LOD_PYRAMID,
                overwrite=False,
            )

            generator.generate_lod("4k")
            tile = root / "topo_bathy/tiles/4k/tile_0_0.jpg"
            first = sha256_file(tile)
            generator.generate_lod("4k")
            second = sha256_file(tile)

            self.assertEqual(first, second)

    def test_noon_air_profile_writes_candidate_tiles_without_overwriting_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_source_cache(root)
            raw_exporter = EarthTileExporter(
                root,
                tile_size_by_lod=TEST_TILE_SIZE_BY_LOD,
                lod_pyramid=TEST_LOD_PYRAMID,
            )
            noon_exporter = EarthTileExporter(
                root,
                tile_size_by_lod=TEST_TILE_SIZE_BY_LOD,
                lod_pyramid=TEST_LOD_PYRAMID,
                color_profile="noon_air",
            )

            raw_result = raw_exporter.generate_all(datasets=("topo_bathy",), lods=("8k",))[0]
            noon_result = noon_exporter.generate_all(datasets=("topo_bathy",), lods=("8k",))[0]
            raw_manifest = json.loads(raw_result.manifest_path.read_text())
            noon_manifest = json.loads(noon_result.manifest_path.read_text())

            self.assertTrue((root / "topo_bathy/tiles/8k/tile_0_0.jpg").exists())
            self.assertTrue((root / "topo_bathy/tiles_noon_air/8k/tile_0_0.jpg").exists())
            self.assertEqual(raw_manifest["color_profile"], "raw")
            self.assertEqual(noon_manifest["color_profile"], "noon_air")
            self.assertNotEqual(
                sha256_file(root / "topo_bathy/tiles/8k/tile_0_0.jpg"),
                sha256_file(root / "topo_bathy/tiles_noon_air/8k/tile_0_0.jpg"),
            )


if __name__ == "__main__":
    unittest.main()
