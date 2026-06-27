"""Visual Weight Harmonizer tests.

Verifies:
1. Ocean intensity never exceeds constraint
2. Biome saturation clamped correctly
3. Ice brightness capped
4. Desert exposure normalized
5. Atmosphere opacity ≤ max allowed
6. Deterministic output
7. Under-limit values pass through unchanged
8. Constraint file parsing
9. Texture array harmonization
"""

from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from core.rendering.renderer_types import RGB
from core.rendering.visual_weight_harmonizer import (
    VisualConstraints,
    VisualWeightHarmonizer,
    harmonize_visual_output,
    load_noon_air_spec,
)

# ── Shared helpers ────────────────────────────────────────────────────────────

CONSTRAINTS = VisualConstraints(
    ocean_weight_max=0.72,
    biome_saturation_max=0.95,
    ice_brightness_max=0.97,
    desert_exposure_max=0.77,
    atmosphere_opacity_max=0.08,
)


def _lum(rgb: RGB) -> float:
    return 0.2126 * rgb.r + 0.7152 * rgb.g + 0.0722 * rgb.b


def _chroma_ratio(rgb: RGB) -> float:
    lum = _lum(rgb)
    if lum <= 0.01:
        return 0.0
    peak = max(abs(rgb.r - lum), abs(rgb.g - lum), abs(rgb.b - lum))
    return peak / lum


def _write_spec(content: str) -> Path:
    """Write a temp spec file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    )
    f.write(content)
    f.close()
    return Path(f.name)


# ── 1. Ocean intensity cap ────────────────────────────────────────────────────


class TestOceanIntensityCap(unittest.TestCase):

    def test_over_bright_shallow_clamped(self):
        bright = RGB(0.95, 0.98, 0.99)
        result = harmonize_visual_output(
            bright, bright, CONSTRAINTS, ocean=True, elevation=0.0
        )
        self.assertLessEqual(_lum(result), CONSTRAINTS.ocean_weight_max + 1e-6)

    def test_ocean_at_limit_unchanged(self):
        target = CONSTRAINTS.ocean_weight_max
        pix = RGB(target, target, target)
        result = harmonize_visual_output(
            pix, pix, CONSTRAINTS, ocean=True, elevation=0.0
        )
        self.assertAlmostEqual(_lum(result), target, places=5)

    def test_deep_ocean_not_constrained(self):
        pix = RGB(0.80, 0.80, 0.90)
        result = harmonize_visual_output(
            pix, pix, CONSTRAINTS, ocean=True, elevation=-1500.0
        )
        self.assertAlmostEqual(result.r, pix.r, places=5)

    def test_ocean_cap_never_amplifies(self):
        dim = RGB(0.05, 0.15, 0.20)
        result = harmonize_visual_output(
            dim, dim, CONSTRAINTS, ocean=True, elevation=-200.0
        )
        self.assertLessEqual(_lum(result), _lum(dim) + 1e-6)


# ── 2. Biome saturation cap ───────────────────────────────────────────────────


class TestBiomeSaturationCap(unittest.TestCase):

    def test_over_saturated_tropical_clamped(self):
        vivid = RGB(0.02, 0.85, 0.10)
        result = harmonize_visual_output(
            vivid, vivid, CONSTRAINTS, ocean=False, climate_family="tropical"
        )
        self.assertLessEqual(_chroma_ratio(result), CONSTRAINTS.biome_saturation_max + 1e-6)

    def test_muted_temperate_unaffected(self):
        muted = RGB(0.22, 0.30, 0.20)
        result = harmonize_visual_output(
            muted, muted, CONSTRAINTS, ocean=False, climate_family="temperate"
        )
        self.assertAlmostEqual(result.r, muted.r, places=5)
        self.assertAlmostEqual(result.g, muted.g, places=5)
        self.assertAlmostEqual(result.b, muted.b, places=5)

    def test_saturation_cap_preserves_hue(self):
        vivid = RGB(0.05, 0.90, 0.08)
        result = harmonize_visual_output(
            vivid, vivid, CONSTRAINTS, ocean=False, climate_family="tropical"
        )
        self.assertGreater(result.g, result.r)
        self.assertGreater(result.g, result.b)

    def test_saturation_cap_deterministic(self):
        pix = RGB(0.02, 0.85, 0.10)
        r1 = harmonize_visual_output(pix, pix, CONSTRAINTS, ocean=False)
        r2 = harmonize_visual_output(pix, pix, CONSTRAINTS, ocean=False)
        self.assertEqual(r1, r2)


# ── 3. Ice brightness cap ─────────────────────────────────────────────────────


class TestIceBrightnessCap(unittest.TestCase):

    def test_over_bright_polar_clamped(self):
        blinding = RGB(0.99, 1.00, 1.00)
        result = harmonize_visual_output(
            blinding, blinding, CONSTRAINTS, ocean=False, climate_family="polar"
        )
        self.assertLessEqual(_lum(result), CONSTRAINTS.ice_brightness_max + 1e-6)

    def test_ice_at_limit_unchanged(self):
        target = CONSTRAINTS.ice_brightness_max
        pix = RGB(target, target, target)
        result = harmonize_visual_output(
            pix, pix, CONSTRAINTS, ocean=False, climate_family="polar"
        )
        self.assertAlmostEqual(_lum(result), target, places=5)

    def test_high_luminance_non_polar_capped(self):
        bright_land = RGB(0.95, 0.96, 0.98)
        result = harmonize_visual_output(
            bright_land, bright_land, CONSTRAINTS,
            ocean=False, climate_family="unknown"
        )
        self.assertLessEqual(_lum(result), CONSTRAINTS.ice_brightness_max + 1e-6)

    def test_ice_hue_preserved(self):
        tinted = RGB(0.90, 0.92, 0.99)
        result = harmonize_visual_output(
            tinted, tinted, CONSTRAINTS, ocean=False, climate_family="polar"
        )
        self.assertGreaterEqual(result.b, result.r - 1e-6)


# ── 4. Desert exposure normalization ─────────────────────────────────────────


class TestDesertExposure(unittest.TestCase):

    def test_over_bright_desert_clamped(self):
        blown_out = RGB(0.90, 0.82, 0.60)
        result = harmonize_visual_output(
            blown_out, blown_out, CONSTRAINTS, ocean=False, climate_family="arid"
        )
        self.assertLessEqual(_lum(result), CONSTRAINTS.desert_exposure_max + 1e-6)

    def test_moderate_desert_unaffected(self):
        sand = RGB(0.49, 0.38, 0.22)
        result = harmonize_visual_output(
            sand, sand, CONSTRAINTS, ocean=False, climate_family="arid"
        )
        self.assertAlmostEqual(result.r, sand.r, places=5)

    def test_desert_warmth_preserved(self):
        warm = RGB(0.95, 0.80, 0.55)
        result = harmonize_visual_output(
            warm, warm, CONSTRAINTS, ocean=False, climate_family="arid"
        )
        self.assertGreaterEqual(result.r, result.g - 1e-6)
        self.assertGreaterEqual(result.r, result.b - 1e-6)


# ── 5. Atmosphere opacity ≤ max ───────────────────────────────────────────────


class TestAtmosphereOpacity(unittest.TestCase):

    def test_default_atmosphere_opacity(self):
        self.assertLessEqual(CONSTRAINTS.atmosphere_opacity_max, 0.08)

    def test_load_spec_atmosphere_cap(self):
        spec = _write_spec("最大透明度：不得超过 8%\n")
        try:
            c = load_noon_air_spec(spec)
            self.assertAlmostEqual(c.atmosphere_opacity_max, 0.08, places=5)
        finally:
            spec.unlink(missing_ok=True)

    def test_load_spec_custom_percentage(self):
        spec = _write_spec("不得超过 5%\n")
        try:
            c = load_noon_air_spec(spec)
            self.assertAlmostEqual(c.atmosphere_opacity_max, 0.05, places=5)
        finally:
            spec.unlink(missing_ok=True)

    def test_harmonizer_exposes_constraint(self):
        h = VisualWeightHarmonizer()
        self.assertLessEqual(h.constraints.atmosphere_opacity_max, 0.08)


# ── 6. Deterministic output ───────────────────────────────────────────────────


class TestDeterminism(unittest.TestCase):

    CASES = [
        dict(ocean=True,  climate_family="unknown",  elevation=-500.0),
        dict(ocean=False, climate_family="polar",    elevation=3500.0),
        dict(ocean=False, climate_family="arid",     elevation=200.0),
        dict(ocean=False, climate_family="tropical", elevation=50.0),
        dict(ocean=False, climate_family="temperate", elevation=100.0),
    ]

    def test_all_cases_deterministic(self):
        pix = RGB(0.60, 0.75, 0.55)
        for ctx in self.CASES:
            r1 = harmonize_visual_output(pix, pix, CONSTRAINTS, **ctx)
            r2 = harmonize_visual_output(pix, pix, CONSTRAINTS, **ctx)
            self.assertEqual(r1, r2, msg=f"Non-deterministic for {ctx}")

    def test_harmonizer_class_deterministic(self):
        h = VisualWeightHarmonizer()
        pix = RGB(0.55, 0.80, 0.20)
        r1 = h.harmonize(pix, ocean=False, climate_family="tropical")
        r2 = h.harmonize(pix, ocean=False, climate_family="tropical")
        self.assertEqual(r1, r2)


# ── 7. Under-limit values pass through unchanged ──────────────────────────────


class TestPassThrough(unittest.TestCase):

    def test_dim_ocean_unchanged(self):
        dim = RGB(0.10, 0.25, 0.35)
        result = harmonize_visual_output(
            dim, dim, CONSTRAINTS, ocean=True, elevation=-300.0
        )
        self.assertAlmostEqual(result.r, dim.r, places=5)
        self.assertAlmostEqual(result.g, dim.g, places=5)

    def test_muted_land_unchanged(self):
        muted = RGB(0.30, 0.40, 0.25)
        result = harmonize_visual_output(
            muted, muted, CONSTRAINTS, ocean=False, climate_family="temperate"
        )
        self.assertAlmostEqual(result.r, muted.r, places=5)

    def test_output_always_clamped_to_unit(self):
        pix_r = RGB(0.5, 1.1, -0.1)
        result = harmonize_visual_output(pix_r, pix_r, CONSTRAINTS)
        self.assertGreaterEqual(result.r, 0.0)
        self.assertLessEqual(result.r, 1.0)
        self.assertGreaterEqual(result.g, 0.0)
        self.assertLessEqual(result.g, 1.0)
        self.assertGreaterEqual(result.b, 0.0)
        self.assertLessEqual(result.b, 1.0)


# ── 8. Constraint file parsing ────────────────────────────────────────────────


class TestConstraintFileParsing(unittest.TestCase):

    def test_missing_file_returns_defaults(self):
        c = load_noon_air_spec(Path("/nonexistent/spec.md"))
        defaults = VisualConstraints()
        self.assertAlmostEqual(
            c.atmosphere_opacity_max, defaults.atmosphere_opacity_max, places=5
        )

    def test_ice_hex_parsed(self):
        spec = _write_spec(
            "## 南极冰盖\n| 冰雪亮部 | `#F2F8FA` | 受光区 |\n"
        )
        try:
            c = load_noon_air_spec(spec)
            # #F2F8FA lum ≈ 0.966; cap must be > 0.966 and ≤ 0.985
            self.assertGreater(c.ice_brightness_max, 0.966)
            self.assertLessEqual(c.ice_brightness_max, 0.985)
        finally:
            spec.unlink(missing_ok=True)

    def test_desert_hex_parsed(self):
        spec = _write_spec(
            "撒哈拉和阿拉伯半岛不能大面积超过 `#D8BC91`\n"
        )
        try:
            c = load_noon_air_spec(spec)
            # #D8BC91 lum ≈ 0.75; cap should be ~0.77
            self.assertGreater(c.desert_exposure_max, 0.74)
            self.assertLessEqual(c.desert_exposure_max, 0.90)
        finally:
            spec.unlink(missing_ok=True)

    def test_harmonizer_with_spec_file(self):
        spec = _write_spec(
            "不得超过 8%\n撒哈拉不能大面积超过 `#D8BC91`\n"
        )
        try:
            h = VisualWeightHarmonizer(constraint_file=spec)
            self.assertAlmostEqual(h.constraints.atmosphere_opacity_max, 0.08, places=5)
        finally:
            spec.unlink(missing_ok=True)


# ── 9. Texture array harmonization ───────────────────────────────────────────


class TestTextureHarmonization(unittest.TestCase):

    def test_bright_texture_capped(self):
        h = VisualWeightHarmonizer()
        tex = np.full((4, 4, 3), 255, dtype=np.uint8)
        result = h.harmonize_texture(tex)
        f = result.astype(np.float32) / 255.0
        lum = 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]
        self.assertLessEqual(
            float(lum.max()), h.constraints.ice_brightness_max + 1 / 255.0
        )

    def test_dim_texture_unchanged(self):
        h = VisualWeightHarmonizer()
        tex = np.full((4, 4, 3), 40, dtype=np.uint8)
        result = h.harmonize_texture(tex)
        np.testing.assert_array_equal(result, tex)

    def test_output_dtype_uint8(self):
        h = VisualWeightHarmonizer()
        rng = np.random.default_rng(42)
        tex = rng.integers(0, 256, (8, 8, 3), dtype=np.uint8)
        result = h.harmonize_texture(tex)
        self.assertEqual(result.dtype, np.uint8)
        self.assertEqual(result.shape, tex.shape)

    def test_ocean_mask_applies_ocean_cap(self):
        h = VisualWeightHarmonizer()
        tex = np.full((2, 2, 3), 230, dtype=np.uint8)  # bright pixels
        ocean_mask = np.array([[True, True], [False, False]])
        result = h.harmonize_texture(tex, ocean_mask=ocean_mask)
        f = result.astype(np.float32) / 255.0
        lum = 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]
        # Ocean rows (0) must be capped at ocean_weight_max
        self.assertLessEqual(float(lum[0].max()), h.constraints.ocean_weight_max + 1 / 255.0)


if __name__ == "__main__":
    unittest.main()
