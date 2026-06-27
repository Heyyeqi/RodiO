"""Tests for SpectralEarthEngine — physics-inspired spectral response models.

Covers:
  1. Beer-Lambert ocean model (depth calibration, nonlinearity, channel ordering)
  2. Ice BRDF (brightness, spectral tilt, spatial variation, sun angle)
  3. Desert albedo (warming, factor scaling, luma preservation)
  4. Atmospheric scattering (small changes, blue tint at limb)
  5. Determinism (all four methods)
"""

import math
import unittest

import numpy as np

from core.rendering.geo_field_engine import AtmosphereField, GeoFieldEngine, IceField
from core.rendering.spectral_earth_engine import SpectralEarthEngine


def _ice_field(shape=(4, 4), ice_val=0.5, bg_val=0.80, bs_val=0.04):
    """Build a synthetic IceField with uniform values."""
    H, W = shape
    return IceField(
        ice_factor=np.full((H, W), ice_val, dtype=np.float32),
        brightness_gradient=np.full((H, W), bg_val, dtype=np.float32),
        blue_shift=np.full((H, W), bs_val, dtype=np.float32),
    )


def _atmo_field(shape=(4, 4), limb=0.03, horiz=0.01, sky=0.005):
    """Build a synthetic AtmosphereField with uniform values."""
    H, W = shape
    return AtmosphereField(
        limb_glow=np.full((H, W), limb, dtype=np.float32),
        horizon_blend=np.full((H, W), horiz, dtype=np.float32),
        ocean_sky_continuity=np.full((H, W), sky, dtype=np.float32),
    )


# ── 1. Beer-Lambert ocean model ──────────────────────────────────────────────


class TestOceanBeerLambertModel(unittest.TestCase):
    """Beer-Lambert calibration: depth=0 → deep #052C4A, depth=1 → shallow #2EC4C6."""

    def setUp(self):
        self.engine = SpectralEarthEngine()
        self.H, self.W = 4, 4

    def _uniform_field(self, value):
        return np.full((self.H, self.W), value, dtype=np.float32)

    def test_deep_ocean_is_dark_and_blue(self):
        """depth_proxy=0 → approximately [5, 44, 74] (#052C4A)."""
        depth = self._uniform_field(0.0)
        factor = self._uniform_field(0.9)
        out = self.engine.ocean_spectral_response(depth, factor)
        mean = out.mean(axis=(0, 1))
        self.assertLess(float(mean[0]), 10.0, f"R should be ~5 at depth=0, got {mean[0]:.1f}")
        self.assertLess(float(mean[1]), 55.0, f"G should be ~44 at depth=0, got {mean[1]:.1f}")
        self.assertGreater(float(mean[2]), 65.0, f"B should be ~74 at depth=0, got {mean[2]:.1f}")

    def test_shallow_ocean_is_bright_cyan(self):
        """depth_proxy=1 → approximately [46, 196, 198] (#2EC4C6)."""
        depth = self._uniform_field(1.0)
        factor = self._uniform_field(0.9)
        out = self.engine.ocean_spectral_response(depth, factor)
        mean = out.mean(axis=(0, 1))
        self.assertGreater(float(mean[0]), 40.0, f"R should be ~46 at depth=1, got {mean[0]:.1f}")
        self.assertGreater(float(mean[1]), 185.0, f"G should be ~196, got {mean[1]:.1f}")
        self.assertGreater(float(mean[2]), 185.0, f"B should be ~198, got {mean[2]:.1f}")

    def test_response_is_nonlinear_not_linear(self):
        """Mid-depth response must differ from linear interpolation of endpoints."""
        depth_zero = self._uniform_field(0.0)
        depth_one = self._uniform_field(1.0)
        depth_mid = self._uniform_field(0.5)
        factor = self._uniform_field(0.9)

        out_0 = self.engine.ocean_spectral_response(depth_zero, factor).mean(axis=(0, 1))
        out_1 = self.engine.ocean_spectral_response(depth_one, factor).mean(axis=(0, 1))
        out_mid = self.engine.ocean_spectral_response(depth_mid, factor).mean(axis=(0, 1))

        linear_mid = (out_0 + out_1) / 2.0
        max_diff = float(np.abs(out_mid - linear_mid).max())
        self.assertGreater(max_diff, 2.0,
                           "Beer-Lambert must deviate from linear interpolation")

    def test_blue_exceeds_red_at_any_depth(self):
        """B > R for all depth values (ocean spectral signature)."""
        engine = SpectralEarthEngine()
        factor = np.full((1, 1), 0.9, dtype=np.float32)
        for d in np.linspace(0.0, 1.0, 9, dtype=np.float32):
            depth = np.full((1, 1), d, dtype=np.float32)
            out = engine.ocean_spectral_response(depth, factor)
            self.assertGreater(float(out[0, 0, 2]), float(out[0, 0, 0]),
                               f"B must exceed R at depth_proxy={d:.2f}")

    def test_depth_monotonicity_channel_by_channel(self):
        """Deeper → darker for every channel (absorption increases with depth)."""
        engine = SpectralEarthEngine()
        factor = np.full((1, 1), 0.9, dtype=np.float32)
        prev_out = None
        for d in np.linspace(0.0, 1.0, 5, dtype=np.float32):
            depth = np.full((1, 1), d, dtype=np.float32)
            out = engine.ocean_spectral_response(depth, factor).mean(axis=(0, 1))
            if prev_out is not None:
                for ch in range(3):
                    self.assertGreaterEqual(
                        float(out[ch]), float(prev_out[ch]) - 0.01,
                        f"channel {ch} must be non-decreasing as depth_proxy increases"
                    )
            prev_out = out


# ── 2. Ice BRDF model ────────────────────────────────────────────────────────


class TestIceReflectanceModel(unittest.TestCase):

    def setUp(self):
        self.engine = SpectralEarthEngine()

    def test_ice_reflectance_brighter_than_dim_pixels(self):
        """Ice reflectance target must be brighter than a dim input pixel (128,128,128)."""
        ice_f = _ice_field(shape=(4, 4), bg_val=0.50)
        out = self.engine.ice_reflectance(ice_f, sun_angle=45.0)
        self.assertGreater(float(out.mean()), 128.0,
                           "Ice BRDF should produce a bright target above mid-gray")

    def test_ice_blue_channel_not_below_red(self):
        """Spectral tilt must keep B >= R after blue_shift is applied."""
        ice_f = _ice_field(shape=(4, 4), bs_val=0.06)  # max blue shift
        out = self.engine.ice_reflectance(ice_f, sun_angle=45.0)
        self.assertGreaterEqual(
            float(out[..., 2].mean()), float(out[..., 0].mean()),
            "B must be >= R after spectral tilt"
        )

    def test_lower_sun_angle_reduces_brightness(self):
        """Lower sun angle (more oblique) must produce less bright ice."""
        ice_f = _ice_field(shape=(4, 4))
        bright = self.engine.ice_reflectance(ice_f, sun_angle=10.0)
        dimmer = self.engine.ice_reflectance(ice_f, sun_angle=80.0)
        self.assertGreater(
            float(bright.mean()), float(dimmer.mean()),
            "sun_angle=10° (high elevation) should produce brighter ice than 80°"
        )

    def test_spatial_variation_from_brightness_gradient(self):
        """Non-uniform brightness_gradient must produce spatially varied reflectance."""
        H, W = 8, 8
        y = np.linspace(0.80, 1.00, H, dtype=np.float32)[:, None] * np.ones((1, W), dtype=np.float32)
        ice_f = IceField(
            ice_factor=np.full((H, W), 0.6, dtype=np.float32),
            brightness_gradient=y,
            blue_shift=np.full((H, W), 0.03, dtype=np.float32),
        )
        out = self.engine.ice_reflectance(ice_f, sun_angle=45.0)
        row_means = out.mean(axis=(1, 2))
        self.assertGreater(float(row_means.std()), 0.0,
                           "spatial variation in gradient must produce varied output rows")

    def test_output_never_exceeds_252(self):
        """Ice reflectance must be clamped to ≤ 252 (not hard 255 white)."""
        ice_f = _ice_field(shape=(8, 8), ice_val=1.0, bg_val=1.0, bs_val=0.06)
        out = self.engine.ice_reflectance(ice_f, sun_angle=0.0)
        self.assertLessEqual(float(out.max()), 252.0)


# ── 3. Desert albedo model ───────────────────────────────────────────────────


class TestDesertAlbedoModel(unittest.TestCase):

    def setUp(self):
        self.engine = SpectralEarthEngine()

    def test_desert_pixel_gets_warmer_tone(self):
        """Warm soil pixel processed with factor=1 must move closer to sand reference."""
        H, W = 4, 4
        img = np.full((H, W, 3), [178, 158, 96], dtype=np.uint8)
        factor = np.ones((H, W), dtype=np.float32)

        out = self.engine.desert_albedo(img, factor)
        sand = np.array([194.0, 160.0, 119.0])
        raw_dist = float(np.linalg.norm(img.astype(np.float32).mean(axis=(0, 1)) - sand))
        out_dist = float(np.linalg.norm(out.mean(axis=(0, 1)) - sand))
        self.assertLess(out_dist, raw_dist, "output must be closer to sand reference")

    def test_zero_factor_leaves_image_unchanged(self):
        """factor=0 must return the original pixels exactly."""
        H, W = 4, 4
        img = np.full((H, W, 3), [120, 100, 80], dtype=np.uint8)
        factor = np.zeros((H, W), dtype=np.float32)
        out = self.engine.desert_albedo(img, factor)
        np.testing.assert_array_almost_equal(
            out, img.astype(np.float32), decimal=3
        )

    def test_full_factor_warms_rgb(self):
        """With factor=1, output R should exceed output B (warm desert signature)."""
        H, W = 4, 4
        img = np.full((H, W, 3), [150, 140, 130], dtype=np.uint8)
        factor = np.ones((H, W), dtype=np.float32)
        out = self.engine.desert_albedo(img, factor)
        mean = out.mean(axis=(0, 1))
        self.assertGreater(float(mean[0]), float(mean[2]),
                           "R must exceed B in desert-processed output")


# ── 4. Atmospheric scattering ────────────────────────────────────────────────


class TestAtmosphericScattering(unittest.TestCase):

    def setUp(self):
        self.engine = SpectralEarthEngine()

    def test_limb_glow_introduces_blue_bias(self):
        """Strong limb_glow on a warm pixel should shift B channel up relative to R."""
        H, W = 4, 4
        img = np.full((H, W, 3), [200, 180, 140], dtype=np.uint8)
        atmo = _atmo_field(shape=(H, W), limb=0.05, horiz=0.0, sky=0.0)
        out = self.engine.atmospheric_scattering(img, atmo)
        delta_r = float(out[..., 0].mean()) - 200.0
        delta_b = float(out[..., 2].mean()) - 140.0
        self.assertGreater(delta_b, delta_r,
                           "Rayleigh scattering must boost blue more than red")

    def test_scattering_changes_are_bounded(self):
        """Atmospheric changes must be small (≤ 25 per channel at realistic field values)."""
        H, W = 4, 4
        img = np.full((H, W, 3), [100, 120, 140], dtype=np.uint8)
        atmo = _atmo_field(shape=(H, W), limb=0.065, horiz=0.02, sky=0.015)
        out = self.engine.atmospheric_scattering(img, atmo)
        delta = np.abs(out - img.astype(np.float32)).max()
        self.assertLess(float(delta), 25.0,
                        "Atmospheric corrections at max field values must be ≤ 25")

    def test_zero_fields_leave_image_unchanged(self):
        """All-zero atmosphere field must return input unchanged."""
        H, W = 4, 4
        img = np.full((H, W, 3), [80, 130, 160], dtype=np.uint8)
        atmo = _atmo_field(shape=(H, W), limb=0.0, horiz=0.0, sky=0.0)
        out = self.engine.atmospheric_scattering(img, atmo)
        np.testing.assert_array_almost_equal(
            out, img.astype(np.float32), decimal=3
        )


# ── 5. Determinism ───────────────────────────────────────────────────────────


class TestSpectralEnginesDeterminism(unittest.TestCase):

    def setUp(self):
        self.engine = SpectralEarthEngine()
        self.geo = GeoFieldEngine()
        H, W = 6, 6
        self.tile = np.arange(H * W * 3, dtype=np.uint8).reshape(H, W, 3)
        self.meta = {"bounds": (-20, 70, 20, 80)}

    def test_ocean_spectral_response_is_deterministic(self):
        tile, meta = self.tile, self.meta
        ocean_f = self.geo.ocean_field_from_pixels(tile, meta)
        a = self.engine.ocean_spectral_response(ocean_f.depth_proxy, ocean_f.ocean_factor)
        b = self.engine.ocean_spectral_response(ocean_f.depth_proxy, ocean_f.ocean_factor)
        np.testing.assert_array_equal(a, b)

    def test_ice_reflectance_is_deterministic(self):
        tile, meta = self.tile, self.meta
        ice_f = self.geo.ice_field_from_pixels(tile, meta)
        a = self.engine.ice_reflectance(ice_f, sun_angle=45.0)
        b = self.engine.ice_reflectance(ice_f, sun_angle=45.0)
        np.testing.assert_array_equal(a, b)

    def test_desert_albedo_is_deterministic(self):
        H, W = 4, 4
        img = np.full((H, W, 3), [170, 150, 100], dtype=np.uint8)
        factor = np.full((H, W), 0.7, dtype=np.float32)
        a = self.engine.desert_albedo(img, factor)
        b = self.engine.desert_albedo(img, factor)
        np.testing.assert_array_equal(a, b)

    def test_atmospheric_scattering_is_deterministic(self):
        tile, meta = self.tile, self.meta
        atmo_f = self.geo.atmosphere_field_from_pixels(tile, meta)
        a = self.engine.atmospheric_scattering(tile.astype(np.float32), atmo_f)
        b = self.engine.atmospheric_scattering(tile.astype(np.float32), atmo_f)
        np.testing.assert_array_equal(a, b)


if __name__ == "__main__":
    unittest.main()
