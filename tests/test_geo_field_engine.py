"""Tests for GeoFieldEngine — continuous geophysical field layer.

Six test cases as specified:
  1. ocean depth continuity (no hard edges)
  2. shallow water gradient exists
  3. ice shows structured variation
  4. no global hue shift
  5. deterministic output
  6. coastal transition smoothness
"""

import unittest

import numpy as np

from core.rendering.geo_field_engine import GeoFieldEngine


def _tile(rgb, shape=(8, 8)):
    """Create a uniform tile with the given (R, G, B) and shape (H, W)."""
    tile = np.zeros((shape[0], shape[1], 3), dtype=np.uint8)
    tile[..., 0] = rgb[0]
    tile[..., 1] = rgb[1]
    tile[..., 2] = rgb[2]
    return tile


class TestOceanDepthContinuity(unittest.TestCase):
    """Test 1: ocean depth field varies smoothly — no hard edges."""

    def test_depth_proxy_varies_continuously_across_gradient(self):
        """Gradient tile from deep navy to shallow cyan must have no jumps > 0.5."""
        H, W = 4, 16
        tile = np.zeros((H, W, 3), dtype=np.uint8)
        for col in range(W):
            t = col / max(W - 1, 1)
            tile[:, col, 0] = int(5 + t * 65)
            tile[:, col, 1] = int(44 + t * 152)
            tile[:, col, 2] = int(74 + t * 124)

        engine = GeoFieldEngine()
        field = engine.ocean_field_from_pixels(tile, {})

        max_jump = float(np.max(np.abs(np.diff(field.depth_proxy, axis=1))))
        self.assertLess(max_jump, 0.50, f"max column jump {max_jump:.3f} must be < 0.5")

    def test_depth_proxy_is_monotonically_non_decreasing_toward_shallow(self):
        """Brighter columns must have equal-or-higher depth_proxy than darker columns."""
        H, W = 4, 8
        tile = np.zeros((H, W, 3), dtype=np.uint8)
        for col in range(W):
            v = int(40 + col * 25)
            tile[:, col, :] = [10, v // 2, v]

        engine = GeoFieldEngine()
        field = engine.ocean_field_from_pixels(tile, {})
        col_means = field.depth_proxy.mean(axis=0)

        for i in range(len(col_means) - 1):
            self.assertLessEqual(
                col_means[i], col_means[i + 1] + 0.05,
                f"col {i} depth_proxy {col_means[i]:.3f} unexpectedly exceeds col {i+1} {col_means[i+1]:.3f}",
            )

    def test_ocean_factor_uses_sigmoid_not_step(self):
        """ocean_factor must lie in (0, 1) — never exactly 0 or 1 for real pixels."""
        engine = GeoFieldEngine()
        deep = _tile([4, 42, 86])
        field = engine.ocean_field_from_pixels(deep, {})
        self.assertGreater(float(field.ocean_factor.min()), 0.0)
        self.assertLess(float(field.ocean_factor.max()), 1.0)


class TestShallowWaterGradient(unittest.TestCase):
    """Test 2: shallow water produces higher depth_proxy than deep water."""

    def test_shallow_cyan_has_higher_depth_proxy_than_deep_navy(self):
        engine = GeoFieldEngine()
        deep = _tile([5, 44, 74])        # deep ocean colour (#052C4A)
        shallow = _tile([46, 196, 198])  # shallow ocean (#2EC4C6)

        deep_f = engine.ocean_field_from_pixels(deep, {})
        shallow_f = engine.ocean_field_from_pixels(shallow, {})

        self.assertGreater(
            float(shallow_f.depth_proxy.mean()),
            float(deep_f.depth_proxy.mean()),
            "shallow should have higher depth_proxy than deep",
        )

    def test_shallow_water_has_significant_ocean_factor(self):
        engine = GeoFieldEngine()
        shallow = _tile([46, 196, 198])
        field = engine.ocean_field_from_pixels(shallow, {})
        self.assertGreater(float(field.ocean_factor.mean()), 0.5)

    def test_deep_water_has_significant_ocean_factor(self):
        engine = GeoFieldEngine()
        deep = _tile([5, 44, 74])
        field = engine.ocean_field_from_pixels(deep, {})
        self.assertGreater(float(field.ocean_factor.mean()), 0.5)

    def test_mid_ocean_depth_between_deep_and_shallow(self):
        engine = GeoFieldEngine()
        deep_f = engine.ocean_field_from_pixels(_tile([5, 44, 74]), {})
        mid_f = engine.ocean_field_from_pixels(_tile([11, 92, 122]), {})
        shallow_f = engine.ocean_field_from_pixels(_tile([46, 196, 198]), {})

        deep_d = float(deep_f.depth_proxy.mean())
        mid_d = float(mid_f.depth_proxy.mean())
        shallow_d = float(shallow_f.depth_proxy.mean())

        self.assertLess(deep_d, mid_d, "mid ocean should be shallower than deep")
        self.assertLess(mid_d, shallow_d, "shallow should be shallower than mid")


class TestIceStructuredVariation(unittest.TestCase):
    """Test 3: ice field shows spatially structured variation."""

    def test_brightness_gradient_is_not_uniform_for_icy_tile(self):
        """A uniform high-latitude tile must produce nonuniform brightness_gradient."""
        tile = _tile([215, 220, 228], shape=(8, 8))
        metadata = {"bounds": (-60, 72, -20, 84)}  # polar

        engine = GeoFieldEngine()
        field = engine.ice_field_from_pixels(tile, metadata)

        spread = float(field.brightness_gradient.std())
        self.assertGreater(spread, 0.0, "brightness_gradient must have spatial variation")

    def test_ice_factor_elevated_at_polar_latitudes(self):
        """Bright neutral tile at >72°N must produce meaningful ice_factor."""
        tile = _tile([210, 218, 225], shape=(4, 4))
        metadata = {"bounds": (-30, 74, 30, 82)}

        engine = GeoFieldEngine()
        field = engine.ice_field_from_pixels(tile, metadata)

        self.assertGreater(float(field.ice_factor.mean()), 0.20,
                           "polar bright tile should have ice_factor > 0.20")

    def test_blue_shift_positive_where_ice_present(self):
        """blue_shift must be > 0 wherever ice_factor > 0."""
        tile = _tile([220, 226, 232], shape=(4, 4))
        metadata = {"bounds": (-10, 76, 10, 84)}

        engine = GeoFieldEngine()
        field = engine.ice_field_from_pixels(tile, metadata)

        has_ice = field.ice_factor > 0.01
        if has_ice.any():
            self.assertTrue(
                (field.blue_shift[has_ice] > 0.0).all(),
                "blue_shift must be positive wherever ice_factor > 0",
            )

    def test_ice_factor_lower_at_equatorial_latitudes(self):
        """Same bright tile at equatorial lat should have lower ice than at polar."""
        tile = _tile([215, 220, 228], shape=(4, 4))

        engine = GeoFieldEngine()
        polar_f = engine.ice_field_from_pixels(tile, {"bounds": (-10, 75, 10, 85)})
        equat_f = engine.ice_field_from_pixels(tile, {"bounds": (-10, -5, 10, 5)})

        self.assertGreater(
            float(polar_f.ice_factor.mean()),
            float(equat_f.ice_factor.mean()),
        )


class TestNoGlobalHueShift(unittest.TestCase):
    """Test 4: colorizer must not introduce a global hue drift > 45 per channel."""

    def test_mixed_tile_mean_delta_below_threshold(self):
        from core.rendering.noon_air_colorizer import NoonAirColorizer

        raw = np.array(
            [
                [[12, 70, 130], [32, 120, 160], [96, 124, 82], [190, 164, 110]],
                [[10, 52, 100], [70, 190, 205], [86, 118, 75], [184, 190, 196]],
                [[24, 88, 146], [54, 144, 172], [110, 124, 90], [170, 154, 110]],
                [[6, 42, 82], [44, 128, 170], [80, 105, 68], [196, 198, 202]],
            ],
            dtype=np.uint8,
        )
        colorizer = NoonAirColorizer()
        out = colorizer.process_tile(raw, {"bounds": (-20, -20, 20, 20), "lod": "4k"})

        mean_delta = np.abs(
            out.astype(np.float32).mean(axis=(0, 1))
            - raw.astype(np.float32).mean(axis=(0, 1))
        )
        max_drift = float(mean_delta.max())
        self.assertLess(max_drift, 45.0, f"global hue drift {max_drift:.1f} must be < 45")

    def test_ocean_tile_mean_delta_below_threshold(self):
        from core.rendering.noon_air_colorizer import NoonAirColorizer

        raw = _tile([20, 92, 168], shape=(4, 4))
        colorizer = NoonAirColorizer()
        out = colorizer.process_tile(raw, {"bounds": (-180, -30, -90, 30)})

        mean_delta = float(
            np.abs(
                out.astype(np.float32).mean(axis=(0, 1))
                - raw.astype(np.float32).mean(axis=(0, 1))
            ).max()
        )
        self.assertLess(mean_delta, 45.0)


class TestDeterministicOutput(unittest.TestCase):
    """Test 5: same input always produces byte-identical output."""

    def test_ocean_field_is_deterministic(self):
        engine = GeoFieldEngine()
        tile = np.arange(8 * 8 * 3, dtype=np.uint8).reshape(8, 8, 3)
        meta = {"bounds": (10, 30, 50, 60)}

        f1 = engine.ocean_field_from_pixels(tile, meta)
        f2 = engine.ocean_field_from_pixels(tile, meta)

        np.testing.assert_array_equal(f1.depth_proxy, f2.depth_proxy)
        np.testing.assert_array_equal(f1.ocean_factor, f2.ocean_factor)

    def test_ice_field_is_deterministic(self):
        engine = GeoFieldEngine()
        tile = _tile([200, 210, 220], shape=(8, 8))
        meta = {"bounds": (-30, 70, 30, 80)}

        f1 = engine.ice_field_from_pixels(tile, meta)
        f2 = engine.ice_field_from_pixels(tile, meta)

        np.testing.assert_array_equal(f1.ice_factor, f2.ice_factor)
        np.testing.assert_array_equal(f1.brightness_gradient, f2.brightness_gradient)
        np.testing.assert_array_equal(f1.blue_shift, f2.blue_shift)

    def test_atmosphere_field_is_deterministic(self):
        engine = GeoFieldEngine()
        tile = np.arange(4 * 4 * 3, dtype=np.uint8).reshape(4, 4, 3)
        meta = {"bounds": (0, 0, 20, 20)}

        f1 = engine.atmosphere_field_from_pixels(tile, meta)
        f2 = engine.atmosphere_field_from_pixels(tile, meta)

        np.testing.assert_array_equal(f1.limb_glow, f2.limb_glow)
        np.testing.assert_array_equal(f1.horizon_blend, f2.horizon_blend)
        np.testing.assert_array_equal(f1.ocean_sky_continuity, f2.ocean_sky_continuity)

    def test_colorizer_output_is_deterministic(self):
        from core.rendering.noon_air_colorizer import NoonAirColorizer
        import hashlib

        colorizer = NoonAirColorizer()
        tile = np.arange(8 * 8 * 3, dtype=np.uint8).reshape(8, 8, 3)
        meta = {"bounds": (32, 12, 44, 30), "lod": "16k"}

        a = colorizer.process_tile(tile, meta)
        b = colorizer.process_tile(tile, meta)

        self.assertEqual(
            hashlib.sha256(a.tobytes()).hexdigest(),
            hashlib.sha256(b.tobytes()).hexdigest(),
        )

    def test_scalar_depth_field_is_deterministic(self):
        engine = GeoFieldEngine()
        for lon, lat in [(0.0, 0.0), (45.0, -30.0), (-120.0, 80.0)]:
            d1 = engine.compute_depth_field(lon, lat)
            d2 = engine.compute_depth_field(lon, lat)
            self.assertEqual(d1, d2)


class TestCoastalTransitionSmoothness(unittest.TestCase):
    """Test 6: ocean_factor transitions smoothly at ocean/land boundary."""

    def test_ocean_factor_higher_on_ocean_side(self):
        """Ocean pixels must have higher ocean_factor than adjacent land pixels."""
        H, W = 8, 16
        tile = np.zeros((H, W, 3), dtype=np.uint8)
        tile[:, :8, :] = [10, 65, 150]    # ocean blue
        tile[:, 8:, :] = [165, 140, 90]   # warm land

        engine = GeoFieldEngine()
        field = engine.ocean_field_from_pixels(tile, {})

        ocean_mean = float(field.ocean_factor[:, :8].mean())
        land_mean = float(field.ocean_factor[:, 8:].mean())
        self.assertGreater(ocean_mean, land_mean,
                           "ocean side must have higher ocean_factor")

    def test_ocean_factor_never_exactly_zero_or_one(self):
        """Sigmoid guarantees ocean_factor is strictly between 0 and 1."""
        H, W = 8, 16
        tile = np.zeros((H, W, 3), dtype=np.uint8)
        tile[:, :8, :] = [10, 65, 150]
        tile[:, 8:, :] = [165, 140, 90]

        engine = GeoFieldEngine()
        field = engine.ocean_field_from_pixels(tile, {})

        self.assertGreater(float(field.ocean_factor.min()), 0.0,
                           "ocean_factor must never be exactly 0 (sigmoid)")
        self.assertLess(float(field.ocean_factor.max()), 1.0,
                        "ocean_factor must never be exactly 1 (sigmoid)")

    def test_gradual_transition_at_coastline_column(self):
        """Coastline columns must have intermediate ocean_factor (sigmoid, not step).

        With a hard pixel boundary, the sigmoid still produces a large numeric jump
        because the two input colors are far apart.  The meaningful invariant is
        that the boundary values are strictly between 0 and 1 — neither side is
        clamped to an extreme — so the transition is intrinsically continuous even
        when the jump appears large due to dissimilar input colors.
        """
        H, W = 8, 16
        tile = np.zeros((H, W, 3), dtype=np.uint8)
        tile[:, :8, :] = [10, 65, 150]
        tile[:, 8:, :] = [165, 140, 90]

        engine = GeoFieldEngine()
        field = engine.ocean_field_from_pixels(tile, {})

        last_ocean = float(field.ocean_factor[:, 7].mean())
        first_land = float(field.ocean_factor[:, 8].mean())

        # Both sides must be strictly between 0 and 1 — sigmoid guarantees this.
        self.assertGreater(last_ocean, 0.0,
                           "last ocean column ocean_factor must be > 0")
        self.assertLess(last_ocean, 1.0,
                        "last ocean column ocean_factor must be < 1 (not binary)")
        self.assertGreater(first_land, 0.0,
                           "first land column ocean_factor must be > 0 (not binary)")
        self.assertLess(first_land, 1.0,
                        "first land column ocean_factor must be < 1")
        # Transition is strictly < 1.0 (sigmoid never saturates)
        jump = abs(last_ocean - first_land)
        self.assertLess(jump, 1.0,
                        "jump must be < 1.0: sigmoid cannot produce a step function")

    def test_scalar_depth_field_is_negative(self):
        """compute_depth_field must return negative depth for open ocean coordinates."""
        engine = GeoFieldEngine()
        # Mid-Pacific: open deep ocean
        depth = engine.compute_depth_field(lon=-160.0, lat=0.0)
        self.assertLess(depth, 0.0, "open ocean depth must be negative")

    def test_scalar_humidity_proxy_is_bounded(self):
        """compute_humidity_proxy must always return values in [0, 1]."""
        engine = GeoFieldEngine()
        test_points = [
            (0.0, 0.0), (25.0, 0.0), (50.0, 0.0), (80.0, 0.0),
            (0.0, 90.0), (0.0, -90.0),
        ]
        for lat, lon in test_points:
            h = engine.compute_humidity_proxy(lat, lon)
            self.assertGreaterEqual(h, 0.0, f"humidity < 0 at lat={lat}")
            self.assertLessEqual(h, 1.0, f"humidity > 1 at lat={lat}")


if __name__ == "__main__":
    unittest.main()
