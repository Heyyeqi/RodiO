"""Noon Air Earth colorizer tests."""

from __future__ import annotations

import hashlib
import unittest

import numpy as np

from core.rendering.noon_air_colorizer import NoonAirColorizer


def digest(arr: np.ndarray) -> str:
    return hashlib.sha256(arr.tobytes()).hexdigest()


class TestNoonAirColorizer(unittest.TestCase):
    def setUp(self) -> None:
        self.colorizer = NoonAirColorizer()

    def test_ocean_pixels_become_darker_than_raw(self):
        raw = np.full((4, 4, 3), [20, 92, 168], dtype=np.uint8)
        out = self.colorizer.process_tile(raw, {"bounds": (-180, -30, -90, 30), "lod": "8k"})

        self.assertLess(out[..., :3].mean(), raw[..., :3].mean())
        self.assertGreater(out[..., 2].mean(), out[..., 0].mean())

    def test_shallow_water_is_brighter_than_deep_ocean(self):
        raw = np.array(
            [
                [[4, 42, 86], [4, 42, 86], [70, 196, 210], [70, 196, 210]],
                [[4, 42, 86], [4, 42, 86], [70, 196, 210], [70, 196, 210]],
            ],
            dtype=np.uint8,
        )
        out = self.colorizer.process_tile(raw, {"bounds": (-80, 18, -72, 28), "lod": "16k"})

        deep_luma = out[:, :2].mean()
        shallow_luma = out[:, 2:].mean()
        self.assertGreater(shallow_luma, deep_luma)
        self.assertGreater(out[:, 2:, 1].mean(), out[:, :2, 1].mean())

    def test_desert_hue_shifts_toward_warm_sand(self):
        raw = np.full((4, 4, 3), [178, 158, 96], dtype=np.uint8)
        out = self.colorizer.process_tile(raw, {"bounds": (-10, 15, 35, 30), "lod": "8k"})

        target = np.array([194, 160, 119], dtype=np.float32)
        before_distance = np.linalg.norm(raw.astype(np.float32).mean(axis=(0, 1)) - target)
        after_distance = np.linalg.norm(out.astype(np.float32).mean(axis=(0, 1)) - target)
        self.assertLess(after_distance, before_distance)
        self.assertGreater(out[..., 0].mean(), out[..., 2].mean())

    def test_ice_brightens_without_white_clipping(self):
        raw = np.full((4, 4, 3), [186, 196, 202], dtype=np.uint8)
        out = self.colorizer.process_tile(raw, {"bounds": (-60, 70, -20, 84), "lod": "8k"})

        self.assertGreater(out.mean(), raw.mean())
        self.assertLess(out.max(), 255)
        self.assertGreaterEqual(out[..., 2].mean(), out[..., 0].mean())

    def test_no_global_color_drift_for_mixed_tile(self):
        raw = np.array(
            [
                [[12, 70, 130], [32, 120, 160], [96, 124, 82], [190, 164, 110]],
                [[10, 52, 100], [70, 190, 205], [86, 118, 75], [184, 190, 196]],
                [[24, 88, 146], [54, 144, 172], [110, 124, 90], [170, 154, 110]],
                [[6, 42, 82], [44, 128, 170], [80, 105, 68], [196, 198, 202]],
            ],
            dtype=np.uint8,
        )
        out = self.colorizer.process_tile(raw, {"bounds": (-20, -20, 20, 20), "lod": "4k"})

        mean_delta = np.abs(out.astype(np.float32).mean(axis=(0, 1)) - raw.astype(np.float32).mean(axis=(0, 1)))
        self.assertLess(float(mean_delta.max()), 45.0)

    def test_deterministic_output_hash(self):
        raw = np.arange(8 * 8 * 3, dtype=np.uint8).reshape(8, 8, 3)
        metadata = {"bounds": (32, 12, 44, 30), "lod": "16k", "x": 1, "y": 0}

        a = self.colorizer.process_tile(raw, metadata)
        b = self.colorizer.process_tile(raw, metadata)

        self.assertEqual(digest(a), digest(b))


if __name__ == "__main__":
    unittest.main()
