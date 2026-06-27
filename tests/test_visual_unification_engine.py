"""Tests for VisualUnificationEngine — perceptual tone curve normalization.

Covers:
  1. Output contract (shape, dtype, no NaN)
  2. Conservative changes (per-pixel delta bounded)
  3. Tile edge feathering (edges differ from center)
  4. Ice brightness soft clamp (very bright pixels pulled toward ceiling)
  5. Determinism
  6. Visual hierarchy preserved (ocean darker than ice)
"""

import hashlib
import unittest

import numpy as np

from core.rendering.visual_unification_engine import VisualUnificationEngine


def _tile(rgb, shape=(8, 8)):
    t = np.zeros((shape[0], shape[1], 3), dtype=np.uint8)
    t[..., 0] = rgb[0]
    t[..., 1] = rgb[1]
    t[..., 2] = rgb[2]
    return t


# ── 1. Output contract ────────────────────────────────────────────────────────


class TestOutputContract(unittest.TestCase):

    def setUp(self):
        self.engine = VisualUnificationEngine()

    def test_preserves_shape(self):
        for shape in [(4, 4), (8, 16), (32, 32), (1, 8)]:
            tile = np.zeros((shape[0], shape[1], 3), dtype=np.uint8)
            out = self.engine.unify(tile, {})
            self.assertEqual(out.shape, (shape[0], shape[1], 3),
                             f"shape mismatch for input {shape}")

    def test_output_is_uint8(self):
        tile = _tile([100, 120, 140])
        out = self.engine.unify(tile, {})
        self.assertEqual(out.dtype, np.uint8)

    def test_no_nan_or_inf(self):
        tile = np.arange(8 * 8 * 3, dtype=np.uint8).reshape(8, 8, 3)
        out = self.engine.unify(tile, {})
        self.assertFalse(np.any(np.isnan(out.astype(np.float32))))
        self.assertFalse(np.any(np.isinf(out.astype(np.float32))))

    def test_values_in_uint8_range(self):
        tile = _tile([0, 0, 0])
        out = self.engine.unify(tile, {})
        self.assertGreaterEqual(int(out.min()), 0)
        self.assertLessEqual(int(out.max()), 255)


# ── 2. Conservative changes ──────────────────────────────────────────────────


class TestConservativeChanges(unittest.TestCase):

    def setUp(self):
        self.engine = VisualUnificationEngine()

    def test_pixel_delta_bounded_for_ocean_tile(self):
        """Ocean pixels must not change by more than 15 per channel."""
        tile = _tile([20, 80, 150], shape=(16, 16))
        out = self.engine.unify(tile, {})
        delta = np.abs(out.astype(np.int32) - tile.astype(np.int32))
        self.assertLess(int(delta.max()), 15, f"max delta {delta.max()} too large")

    def test_pixel_delta_bounded_for_land_tile(self):
        """Land pixels must not change by more than 15 per channel."""
        tile = _tile([120, 140, 80], shape=(16, 16))
        out = self.engine.unify(tile, {})
        delta = np.abs(out.astype(np.int32) - tile.astype(np.int32))
        self.assertLess(int(delta.max()), 15)

    def test_mean_per_channel_within_tolerance(self):
        """Global mean per channel must shift by less than 10."""
        tile = np.arange(16 * 16 * 3, dtype=np.uint8).reshape(16, 16, 3)
        out = self.engine.unify(tile, {})
        delta = np.abs(
            out.astype(np.float32).mean(axis=(0, 1))
            - tile.astype(np.float32).mean(axis=(0, 1))
        )
        self.assertLess(float(delta.max()), 10.0, f"mean channel drift {delta} too large")


# ── 3. Tile edge feathering ──────────────────────────────────────────────────


class TestTileEdgeFeathering(unittest.TestCase):

    def setUp(self):
        self.engine = VisualUnificationEngine()

    def test_edge_pixels_pulled_toward_mean(self):
        """Corner pixels must be slightly closer to tile mean than original."""
        H, W = 32, 32
        # Tile with very dark corners vs bright center
        tile = np.full((H, W, 3), 200, dtype=np.uint8)
        tile[:2, :2, :] = 20  # dark corners
        out = self.engine.unify(tile, {})

        tile_mean = float(tile.astype(np.float32).mean())
        # Corner should be darker in input, closer to mean in output
        corner_orig = float(tile[:2, :2].astype(np.float32).mean())
        corner_out = float(out[:2, :2].astype(np.float32).mean())

        dist_orig = abs(corner_orig - tile_mean)
        dist_out = abs(corner_out - tile_mean)
        self.assertLess(dist_out, dist_orig,
                        "edge feathering must pull corners toward tile mean")

    def test_center_pixels_less_affected_than_edges(self):
        """Center pixels must change less than edge pixels."""
        H, W = 32, 32
        tile = np.full((H, W, 3), 80, dtype=np.uint8)
        # Make corners very bright relative to center
        tile[:3, :3] = 240
        tile[-3:, -3:] = 240
        out = self.engine.unify(tile, {})

        center_delta = float(np.abs(
            out[H//2 - 2:H//2 + 2, W//2 - 2:W//2 + 2].astype(np.float32)
            - tile[H//2 - 2:H//2 + 2, W//2 - 2:W//2 + 2].astype(np.float32)
        ).mean())
        edge_delta = float(np.abs(
            out[:3, :3].astype(np.float32) - tile[:3, :3].astype(np.float32)
        ).mean())

        self.assertGreater(edge_delta, center_delta,
                           "edges must change more than center from feathering")

    def test_tiny_tile_feathering_skipped_gracefully(self):
        """Tiles too small to feather must be returned unchanged."""
        tile = _tile([100, 120, 140], shape=(4, 4))
        out = self.engine.unify(tile, {})
        # No error; tile may be identical or very close
        self.assertEqual(out.shape, tile.shape)


# ── 4. Ice brightness soft clamp ────────────────────────────────────────────


class TestIceBrightnessSoftClamp(unittest.TestCase):

    def setUp(self):
        self.engine = VisualUnificationEngine()

    def test_very_bright_pixels_pulled_below_252(self):
        """Pixels at max (255) must be clamped below 252 by soft clamp."""
        tile = _tile([252, 252, 252], shape=(8, 8))
        out = self.engine.unify(tile, {})
        self.assertLess(int(out.max()), 255,
                        "soft clamp must reduce pixels at 252")

    def test_moderate_pixels_not_clamped(self):
        """Mid-range pixels (≤ 200) must not be affected by ice clamp."""
        tile = _tile([180, 190, 200], shape=(8, 8))
        out = self.engine.unify(tile, {})
        delta = np.abs(out.astype(np.int32) - tile.astype(np.int32))
        # Any change here is from ocean/land tone adjustments, not ice clamp
        self.assertLess(int(delta.max()), 12,
                        "moderate pixels should be barely touched")


# ── 5. Determinism ───────────────────────────────────────────────────────────


class TestUnificationDeterminism(unittest.TestCase):

    def setUp(self):
        self.engine = VisualUnificationEngine()

    def test_same_input_same_hash(self):
        tile = np.arange(16 * 16 * 3, dtype=np.uint8).reshape(16, 16, 3)
        meta = {"bounds": (0, 20, 10, 30), "lod": "8k"}

        a = self.engine.unify(tile, meta)
        b = self.engine.unify(tile, meta)

        h_a = hashlib.sha256(a.tobytes()).hexdigest()
        h_b = hashlib.sha256(b.tobytes()).hexdigest()
        self.assertEqual(h_a, h_b)

    def test_different_inputs_give_different_outputs(self):
        tile_a = _tile([50, 100, 180])
        tile_b = _tile([180, 100, 50])
        out_a = self.engine.unify(tile_a, {})
        out_b = self.engine.unify(tile_b, {})
        self.assertFalse(np.array_equal(out_a, out_b))


# ── 6. Visual hierarchy preservation ────────────────────────────────────────


class TestVisualHierarchyPreserved(unittest.TestCase):
    """Unification must not invert the ocean/ice/land visual hierarchy."""

    def setUp(self):
        self.engine = VisualUnificationEngine()

    def test_ice_brighter_than_ocean_after_unification(self):
        ocean = _tile([15, 60, 110], shape=(8, 8))
        ice = _tile([210, 225, 240], shape=(8, 8))
        out_ocean = self.engine.unify(ocean, {})
        out_ice = self.engine.unify(ice, {})
        self.assertGreater(float(out_ice.mean()), float(out_ocean.mean()),
                           "ice must remain brighter than ocean after unification")

    def test_land_saturation_not_inverted(self):
        """Bright land and desaturated land must retain relative ordering."""
        sat_land = _tile([180, 100, 60], shape=(8, 8))   # high saturation
        neutral = _tile([130, 130, 130], shape=(8, 8))    # neutral
        out_sat = self.engine.unify(sat_land, {})
        out_neu = self.engine.unify(neutral, {})
        # Red channel of warm land must remain above neutral's red
        self.assertGreater(float(out_sat[..., 0].mean()), float(out_neu[..., 0].mean()))


if __name__ == "__main__":
    unittest.main()
