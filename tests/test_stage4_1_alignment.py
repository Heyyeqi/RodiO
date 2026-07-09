"""
Stage 4.1 — Ingestion + Spatial Alignment Lock Layer Tests

Validates:
    1. file scan returns correct layers
    2. registry auto binding works
    3. spatial alignment stable for 8K
    4. same lon/lat maps to the same pixel always
    5. no drift across indexers / providers / runtime binding
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from core.data import FileLoader, RasterLayerRegistry
from core.runtime import SpatialAlignmentLock, SpatialRuntime
from core.signal.raster_indexer import RasterIndexer
from core.signal.providers import (
    ETOPOProvider,
    GEBCOProvider,
    KoppenProvider,
    RasterBackedProvider,
)


def _array(width: int = 360, height: int = 180) -> np.ndarray:
    """Array whose sampled value encodes row and col as row * width + col."""
    rows = np.arange(height, dtype=np.int32)[:, None]
    cols = np.arange(width, dtype=np.int32)[None, :]
    return rows * width + cols


def _expected_value(lon: float, lat: float, width: int, height: int) -> int:
    x, y = SpatialAlignmentLock(width, height).normalize(lon, lat)
    return y * width + x


class FakeRasterDecoder:
    def __init__(self) -> None:
        self.calls = []

    def load(self, path):
        self.calls.append(Path(path).name)
        return {
            "array": np.full((4, 8), len(self.calls), dtype=np.int16),
            "bbox": (-180.0, 180.0, -90.0, 90.0),
        }


class CaptureRegistry:
    def __init__(self) -> None:
        self.layers = {}

    def register(self, name, layer) -> None:
        self.layers[name] = layer


class TestFileLoader(unittest.TestCase):
    def test_scan_returns_correct_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in [
                "world_DEM_8192.tif",
                "GEBCO_ocean_8192.tif",
                "koppen_geiger_8192.tif",
                "MODIS_landcover_8192.tif",
                "notes.txt",
            ]:
                (root / name).write_text("x")

            scan = FileLoader(root).scan()

        self.assertEqual([p.name for p in scan["dem"]], ["world_DEM_8192.tif"])
        self.assertEqual([p.name for p in scan["ocean"]], ["GEBCO_ocean_8192.tif"])
        self.assertEqual([p.name for p in scan["climate"]], ["koppen_geiger_8192.tif"])
        self.assertEqual([p.name for p in scan["landcover"]], ["MODIS_landcover_8192.tif"])

    def test_scan_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["b_dem.tif", "A_dem.tif", "c_dem.tif"]:
                (root / name).write_text("x")

            names = [p.name for p in FileLoader(root).scan()["dem"]]

        self.assertEqual(names, ["A_dem.tif", "b_dem.tif", "c_dem.tif"])

    def test_missing_root_returns_empty_layers(self):
        scan = FileLoader("/tmp/rodio_stage4_1_missing_root").scan()
        self.assertEqual(scan, {"dem": [], "ocean": [], "climate": [], "landcover": []})


class TestAutoRegistration(unittest.TestCase):
    def test_auto_register_loads_first_file_per_layer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["a_dem.tif", "z_dem.tif", "gebco_global.tif", "koppen.tif"]:
                (root / name).write_text("x")

            decoder = FakeRasterDecoder()
            reg = RasterLayerRegistry()
            registered = reg.auto_register(FileLoader(root), decoder)

        self.assertEqual(registered, ["dem", "ocean", "climate"])
        self.assertEqual(decoder.calls, ["a_dem.tif", "gebco_global.tif", "koppen.tif"])
        self.assertTrue(reg.is_loaded("dem"))
        self.assertTrue(reg.is_loaded("ocean"))
        self.assertTrue(reg.is_loaded("climate"))
        self.assertFalse(reg.is_loaded("landcover"))

    def test_bind_to_registry_registers_loaded_layers(self):
        reg = RasterLayerRegistry()
        reg.load_layer("dem", np.ones((4, 8), dtype=np.int16))
        reg.load_layer("climate", np.ones((4, 8), dtype=np.int16) * 7)
        target = CaptureRegistry()

        bound = reg.bind_to_registry(target)

        self.assertEqual(bound, ["dem", "climate"])
        self.assertEqual(sorted(target.layers), ["climate", "dem"])
        self.assertIs(target.layers["dem"], reg.get_layer("dem"))


class TestSpatialAlignmentLock(unittest.TestCase):
    def test_8k_grid_is_locked_to_2_to_1_shape(self):
        lock = SpatialAlignmentLock(8192)
        self.assertEqual(lock.width, 8192)
        self.assertEqual(lock.height, 4096)
        self.assertEqual(lock.normalize(-180.0, 90.0), (0, 0))
        self.assertEqual(lock.normalize(180.0, -90.0), (8191, 4095))

    def test_same_lon_lat_same_pixel_always(self):
        lock = SpatialAlignmentLock(8192)
        samples = [lock.normalize(121.5, 31.2) for _ in range(20)]
        self.assertEqual(len(set(samples)), 1)

    def test_21600_grid_uses_same_formula(self):
        lon, lat = 35.5, 31.5
        x8, y8 = SpatialAlignmentLock(8192).normalize(lon, lat)
        x21, y21 = SpatialAlignmentLock(21600).normalize(lon, lat)
        self.assertAlmostEqual(x21 / 21600.0, x8 / 8192.0, delta=1 / 8192)
        self.assertAlmostEqual(y21 / 10800.0, y8 / 4096.0, delta=1 / 4096)


class TestNoDriftAcrossProviders(unittest.TestCase):
    def test_indexer_matches_alignment_lock(self):
        arr = _array()
        idx = RasterIndexer.from_array(arr)
        for lon, lat in [(0, 0), (121.5, 31.2), (-73.9, 40.7), (179.9, -89.9)]:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(idx.sample(lon, lat), _expected_value(lon, lat, 360, 180))

    def test_indexers_from_registry_share_mapping(self):
        arr = _array()
        reg = RasterLayerRegistry()
        reg.load_layer("dem", arr)
        reg.load_layer("ocean", arr)
        indexers = reg.to_indexers()
        point = (35.5, 31.5)
        self.assertEqual(indexers["dem"].sample(*point), indexers["ocean"].sample(*point))

    def test_providers_share_same_pixel_mapping(self):
        arr = _array()
        point = (35.5, 31.5)
        expected = float(_expected_value(*point, 360, 180))
        gebco = GEBCOProvider(RasterIndexer.from_array(arr))
        etopo = ETOPOProvider(RasterIndexer.from_array(arr))
        koppen = KoppenProvider(RasterIndexer.from_array(np.ones((180, 360), dtype=np.int16) * 5))
        provider = RasterBackedProvider(gebco=gebco, etopo=etopo, koppen=koppen)

        self.assertEqual(gebco.get_dem(*point), expected)
        self.assertEqual(etopo.get_dem(*point), expected)
        self.assertEqual(provider.get_dem(*point), expected)
        self.assertEqual(provider.get_climate(*point), 5)

    def test_runtime_set_earth_loader_preserves_alignment(self):
        ocean = _array()
        climate = np.zeros((180, 360), dtype=np.int16)
        point = (-150.0, 0.0)
        ocean_value = _expected_value(*point, 360, 180)

        reg = RasterLayerRegistry()
        reg.load_layer("ocean", ocean)
        reg.load_layer("climate", climate)
        runtime = SpatialRuntime(real_world_provider=RasterBackedProvider())
        runtime.set_earth_loader(reg)

        state = runtime.query_point(*point)
        self.assertEqual(state.elevation, float(ocean_value))


if __name__ == "__main__":
    unittest.main()
