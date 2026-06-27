"""Stage 10 — production optimization layer tests."""

from __future__ import annotations

import unittest

import numpy as np

from core.rendering import (
    D6Renderer,
    FrameBudgetController,
    GPUTextureManager,
    TextureStreamingLayer,
    TimeState,
    get_visible_tiles,
)


class NullRuntime:
    resolution_mode = "8k"

    def query_point(self, lon, lat):
        from core.runtime.runtime_types import FeatureVector, SpatialState

        ocean = lon < 0
        elevation = -3000.0 if ocean else 240.0
        climate_class = 0 if ocean else 8
        biome_proxy = 0.05 if ocean else 0.60
        fv = FeatureVector(
            elevation=elevation,
            ocean_flag=1.0 if ocean else 0.0,
            climate_class=float(climate_class),
            slope_proxy=0.0,
        )
        return SpatialState(
            elevation=elevation,
            ocean=ocean,
            climate_class=climate_class,
            biome_proxy=biome_proxy,
            slope_proxy=0.0,
            feature_vector=fv,
            normalized_vector=fv,
            source={"ocean_rule": "stage10_test"},
        )


class TestGPUTextureManager(unittest.TestCase):
    def test_gpu_memory_usage_bounded_by_lru_eviction(self):
        manager = GPUTextureManager(max_memory_mb=1)
        a = np.zeros((256, 256, 3), dtype=np.uint8)
        b = np.ones((256, 256, 3), dtype=np.uint8)
        c = np.full((256, 256, 3), 2, dtype=np.uint8)

        manager.load_texture_lod("a", "8k", a, memory_bytes=600_000)
        manager.load_texture_lod("b", "8k", b, memory_bytes=600_000)
        manager.load_texture_lod("c", "8k", c, memory_bytes=600_000)

        pressure = manager.memory_pressure_check()
        self.assertLessEqual(manager.current_memory_bytes, manager.max_memory_bytes)
        self.assertFalse(pressure["over_budget"])
        self.assertLessEqual(pressure["resident_textures"], 1)

    def test_memory_pressure_recommends_lower_lod(self):
        manager = GPUTextureManager(max_memory_mb=1)
        tex = np.zeros((128, 128, 3), dtype=np.uint8)
        manager.load_texture_lod("near_limit", "16k", tex, memory_bytes=900_000)

        pressure = manager.memory_pressure_check()
        self.assertEqual(pressure["pressure"], "high")
        self.assertEqual(pressure["recommended_lod"], "8k")


class TestTextureStreaming(unittest.TestCase):
    def test_split_16k_texture_into_4k_tile_views(self):
        texture = np.arange(8 * 16 * 3, dtype=np.uint8).reshape(8, 16, 3)
        streaming = TextureStreamingLayer(tile_size=4, max_cached_tiles=8)

        tiles = streaming.split_16k_texture(texture)

        self.assertEqual(len(tiles), 8)
        first = tiles[min(tiles)]
        self.assertEqual(first.shape, (4, 4, 3))
        self.assertTrue(np.shares_memory(texture, first))

    def test_tile_streaming_changes_under_camera_movement(self):
        texture = np.zeros((8, 16, 3), dtype=np.uint8)
        streaming = TextureStreamingLayer(tile_size=4, max_cached_tiles=4)

        west = streaming.lazy_load_tiles(texture, {"lon": -135.0, "lat": 0.0, "fov_degrees": 20})
        east = streaming.lazy_load_tiles(texture, {"lon": 135.0, "lat": 0.0, "fov_degrees": 20})

        self.assertNotEqual(set(west), set(east))
        self.assertLessEqual(len(streaming.tile_cache), streaming.max_cached_tiles)

    def test_get_visible_tiles_is_deterministic(self):
        camera = {"lon": 45.0, "lat": 10.0, "fov_degrees": 45, "tile_cols": 4, "tile_rows": 2}
        self.assertEqual(get_visible_tiles(camera), get_visible_tiles(camera))


class TestFrameBudget(unittest.TestCase):
    def test_frame_time_stays_stable_under_budget(self):
        budget = FrameBudgetController(max_frame_time_ms=16.0, current_lod="16k")
        status = budget.record_frame_time(12.5)

        self.assertFalse(status["over_budget"])
        self.assertFalse(status["fallback_triggered"])
        self.assertEqual(status["current_lod"], "16k")

    def test_lod_fallback_triggers_when_frame_exceeds_budget(self):
        budget = FrameBudgetController(max_frame_time_ms=16.0, current_lod="16k")
        status = budget.record_frame_time(22.0)

        self.assertTrue(status["over_budget"])
        self.assertTrue(status["fallback_triggered"])
        self.assertEqual(status["current_lod"], "8k")
        self.assertEqual(status["tile_resolution"], 2048)


class TestD6RendererProductionIntegration(unittest.TestCase):
    def test_no_visual_regression_vs_stage9_output(self):
        ts = TimeState(hour=12.0, day_of_year=180)
        baseline = D6Renderer(NullRuntime(), enable_texture_streaming=False)
        optimized = D6Renderer(NullRuntime(), enable_texture_streaming=True)

        for lon, lat in [(-120.0, 0.0), (20.0, 15.0), (90.0, -20.0)]:
            self.assertEqual(
                baseline.render_point(lon, lat, ts),
                optimized.render_point(lon, lat, ts),
            )

    def test_renderer_streams_tiles_without_full_gpu_duplication(self):
        texture = np.zeros((8, 16, 3), dtype=np.uint8)
        renderer = D6Renderer(NullRuntime(), max_gpu_memory_mb=1, enable_texture_streaming=True)
        renderer.texture_streaming.tile_size = 4

        tiles = renderer.prepare_texture_stream(texture, {"lon": 0.0, "lat": 0.0, "fov_degrees": 20})
        meta = renderer.get_production_metadata()

        self.assertGreater(len(tiles), 0)
        self.assertEqual(meta["gpu_memory"]["pressure"], "normal")
        self.assertEqual(meta["streamed_tile_count"], len(tiles))
        logical = renderer.gpu_texture_manager.loaded_textures["earth_day:16px"]
        self.assertEqual(logical.memory_bytes, 0)

    def test_d6_metadata_reports_compressed_decision_core(self):
        renderer = D6Renderer(NullRuntime(), enable_temporal_stability=True)
        renderer.begin_frame(1)
        renderer.render_point(0.0, 0.0, TimeState(hour=12.0))
        renderer.end_frame(1)

        meta = renderer.get_production_metadata()
        self.assertEqual(meta["decision_core"], "VisualRuleResolver(stability_embedded)")
        self.assertIn("TileStream", meta["pipeline"])


if __name__ == "__main__":
    unittest.main()
