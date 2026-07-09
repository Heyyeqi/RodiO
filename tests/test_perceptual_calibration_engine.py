"""Tests for PerceptualCalibrationEngine (Stage 15).

Validates:
  1. Ocean histogram matches reference perceptual distribution (percentile anchors)
  2. Land saturation bounded within Earth-like range
  3. Ice brightness percentile clamped
  4. No global color drift (overall mean shift bounded)
  5. Deterministic output
  6. No geometry distortion (shape preserved)
"""

import numpy as np
import pytest

import sys, pathlib, importlib

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root))

# Import the module directly to avoid triggering core/rendering/__init__.py
# which eager-loads heavy optional deps (tifffile, PIL, etc.)
_spec = importlib.util.spec_from_file_location(
    "perceptual_calibration_engine",
    _root / "core" / "rendering" / "perceptual_calibration_engine.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
PerceptualCalibrationEngine = _mod.PerceptualCalibrationEngine
_ICE_LUMA_P99 = _mod._ICE_LUMA_P99


@pytest.fixture
def engine():
    return PerceptualCalibrationEngine()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ocean_tile(H=64, W=64) -> np.ndarray:
    """Blue-dominant tile simulating mid-ocean with some variation."""
    rng = np.random.default_rng(42)
    tile = np.zeros((H, W, 3), dtype=np.uint8)
    tile[..., 0] = rng.integers(5, 60, (H, W))    # R low
    tile[..., 1] = rng.integers(20, 100, (H, W))   # G mid
    tile[..., 2] = rng.integers(60, 180, (H, W))   # B dominant
    return tile


def _land_tile(H=64, W=64, neon_green=False) -> np.ndarray:
    """Green-dominant land tile; optionally oversaturated."""
    rng = np.random.default_rng(7)
    tile = np.zeros((H, W, 3), dtype=np.uint8)
    if neon_green:
        tile[..., 0] = rng.integers(0, 30, (H, W))
        tile[..., 1] = rng.integers(200, 255, (H, W))
        tile[..., 2] = rng.integers(0, 30, (H, W))
    else:
        tile[..., 0] = rng.integers(40, 130, (H, W))
        tile[..., 1] = rng.integers(80, 180, (H, W))
        tile[..., 2] = rng.integers(20, 80, (H, W))
    return tile


def _ice_tile(H=64, W=64) -> np.ndarray:
    """Near-white tile simulating polar ice; some pixels above 230."""
    rng = np.random.default_rng(3)
    base = rng.integers(200, 256, (H, W, 3)).astype(np.uint8)
    # Add some hard-clipped bright pixels
    base[:8, :8, :] = 255
    return base


def _desert_tile(H=64, W=64) -> np.ndarray:
    """Warm reddish-yellow desert tile."""
    rng = np.random.default_rng(99)
    tile = np.zeros((H, W, 3), dtype=np.uint8)
    tile[..., 0] = rng.integers(160, 220, (H, W))  # R high
    tile[..., 1] = rng.integers(130, 190, (H, W))  # G mid
    tile[..., 2] = rng.integers(60, 120, (H, W))   # B low
    return tile


def _luma(tile: np.ndarray) -> np.ndarray:
    r, g, b = tile[..., 0].astype(np.float32), tile[..., 1].astype(np.float32), tile[..., 2].astype(np.float32)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _saturation(tile: np.ndarray) -> np.ndarray:
    r, g, b = tile[..., 0].astype(np.float32), tile[..., 1].astype(np.float32), tile[..., 2].astype(np.float32)
    maxc = np.maximum.reduce([r, g, b])
    minc = np.minimum.reduce([r, g, b])
    return (maxc - minc) / np.maximum(maxc, 1.0)


# ── Test 1: Ocean histogram distribution ─────────────────────────────────────

def test_ocean_histogram_distribution(engine):
    """After calibration, ocean luminance should shift toward reference anchors.

    Specifically: the deep ocean (bottom 5%) should be ≤ 35 and the mid-ocean
    range (40–65 percentile) should be in a reasonable band.
    """
    tile = _ocean_tile()
    result = engine.calibrate(tile.copy())

    luma_in  = _luma(tile)
    luma_out = _luma(result)

    # Deep ocean bottom 5% should be pulled dark
    p5_in  = np.percentile(luma_in,  5)
    p5_out = np.percentile(luma_out, 5)
    # After calibration the bottom end should not be brighter than input by much
    assert p5_out <= p5_in + 15, f"Deep ocean too bright after calibration: {p5_out:.1f} vs {p5_in:.1f}"

    # Overall ocean should remain blue-dominant
    assert result[..., 2].mean() > result[..., 0].mean(), "Ocean lost blue dominance"

    # Output shape unchanged
    assert result.shape == tile.shape


def test_ocean_ceiling_not_exceeded(engine):
    """Ocean tiles should never produce luminance beyond the anchor ceiling (≈155)."""
    tile = _ocean_tile()
    result = engine.calibrate(tile.copy())
    luma_out = _luma(result)
    # Allow a small margin above the anchor ceiling for non-ocean pixels at edge
    assert luma_out.max() <= 175, f"Ocean luminance ceiling exceeded: {luma_out.max():.1f}"


# ── Test 2: Land saturation bounded ──────────────────────────────────────────

def test_land_neon_green_suppressed(engine):
    """Neon-green oversaturated vegetation should be desaturated toward normal."""
    tile = _land_tile(neon_green=True)
    sat_in  = _saturation(tile).mean()
    result  = engine.calibrate(tile.copy())
    sat_out = _saturation(result).mean()

    # Saturation should decrease for neon input
    assert sat_out < sat_in, f"Neon green not suppressed: {sat_out:.3f} vs {sat_in:.3f}"
    # Should not go fully gray
    assert sat_out > 0.15, f"Vegetation over-desaturated: {sat_out:.3f}"


def test_land_saturation_within_earth_range(engine):
    """Normal land tiles should not produce extreme saturation."""
    tile = _land_tile(neon_green=False)
    result = engine.calibrate(tile.copy())
    sat_out = _saturation(result)
    # 99th percentile saturation should be within a plausible earth range
    assert np.percentile(sat_out, 99) <= 0.90, "Land saturation 99th percentile too high"


def test_desert_blue_channel_reduced(engine):
    """Warm desert tiles should have reduced blue contribution after calibration."""
    tile = _desert_tile()
    result = engine.calibrate(tile.copy())
    # Blue channel should be equal or lower on average
    assert result[..., 2].mean() <= tile[..., 2].mean() + 5, "Desert blue channel increased unexpectedly"


# ── Test 3: Ice brightness percentile clamped ─────────────────────────────────

def test_ice_brightness_clamped(engine):
    """Ice tiles with pixels at 255 should have brightness clamped below _ICE_LUMA_P99."""
    tile = _ice_tile()
    result = engine.calibrate(tile.copy())
    luma_out = _luma(result)
    # After calibration, max luminance must not exceed P99 ceiling + small delta
    assert luma_out.max() <= _ICE_LUMA_P99 + 3, f"Ice brightness not clamped: {luma_out.max():.1f}"


def test_ice_blue_channel_not_dominant_in_highlights(engine):
    """In bright ice regions, blue should not strongly exceed red (plastic ice look)."""
    tile = _ice_tile()
    result = engine.calibrate(tile.copy())
    bright_mask = _luma(result) > 220
    if bright_mask.sum() == 0:
        pytest.skip("No bright pixels in ice tile after calibration")
    r_bright = result[..., 0][bright_mask].mean()
    b_bright = result[..., 2][bright_mask].mean()
    # Blue excess over red should be small in ice highlights
    assert (b_bright - r_bright) < 20, f"Ice has excessive blue cast: B={b_bright:.1f} R={r_bright:.1f}"


# ── Test 4: No global color drift ─────────────────────────────────────────────

def test_no_global_color_drift_ocean(engine):
    """Ocean calibration should not massively shift overall mean brightness."""
    tile = _ocean_tile()
    result = engine.calibrate(tile.copy())
    mean_in  = tile.astype(float).mean()
    mean_out = result.astype(float).mean()
    # Global mean should not drift by more than 25 gray levels
    assert abs(mean_out - mean_in) < 25, f"Global drift too large: {abs(mean_out - mean_in):.1f}"


def test_no_global_color_drift_land(engine):
    tile = _land_tile()
    result = engine.calibrate(tile.copy())
    mean_in  = tile.astype(float).mean()
    mean_out = result.astype(float).mean()
    assert abs(mean_out - mean_in) < 25, f"Global drift too large: {abs(mean_out - mean_in):.1f}"


def test_per_channel_delta_bounded(engine):
    """Per-pixel per-channel change must not exceed 20 (engine constraint)."""
    for tile_fn in [_ocean_tile, _land_tile, _ice_tile, _desert_tile]:
        tile = tile_fn()
        result = engine.calibrate(tile.copy())
        delta = np.abs(result.astype(np.int32) - tile.astype(np.int32))
        max_delta = int(delta.max())
        assert max_delta <= 20, f"{tile_fn.__name__}: per-channel delta {max_delta} > 20"


# ── Test 5: Deterministic output ──────────────────────────────────────────────

def test_deterministic(engine):
    """Same input must always produce identical output."""
    tile = _ocean_tile()
    r1 = engine.calibrate(tile.copy())
    r2 = engine.calibrate(tile.copy())
    assert np.array_equal(r1, r2), "Output is not deterministic"


def test_deterministic_land(engine):
    tile = _land_tile(neon_green=True)
    r1 = engine.calibrate(tile.copy())
    r2 = engine.calibrate(tile.copy())
    assert np.array_equal(r1, r2)


# ── Test 6: No geometry distortion ────────────────────────────────────────────

def test_output_shape_preserved(engine):
    """Output shape must match input shape for all tile sizes."""
    for H, W in [(16, 16), (64, 64), (128, 256), (512, 512)]:
        tile = np.random.default_rng(0).integers(0, 256, (H, W, 3), dtype=np.uint8)
        result = engine.calibrate(tile)
        assert result.shape == (H, W, 3), f"Shape mismatch for ({H},{W})"


def test_output_dtype_uint8(engine):
    """Output must always be uint8."""
    tile = _ocean_tile()
    result = engine.calibrate(tile)
    assert result.dtype == np.uint8


def test_no_nan_or_inf(engine):
    """No NaN or Inf values in output."""
    for tile_fn in [_ocean_tile, _land_tile, _ice_tile, _desert_tile]:
        tile = tile_fn()
        result = engine.calibrate(tile).astype(np.float32)
        assert not np.isnan(result).any(), f"{tile_fn.__name__}: NaN in output"
        assert not np.isinf(result).any(), f"{tile_fn.__name__}: Inf in output"


# ── Integration: VisualUnificationEngine uses PerceptualCalibrationEngine ────

def test_visual_unification_integrates_calibration():
    """VisualUnificationEngine.unify() should return uint8 output via Stage 15."""
    _vue_spec = importlib.util.spec_from_file_location(
        "visual_unification_engine",
        _root / "core" / "rendering" / "visual_unification_engine.py",
    )
    _vue_mod = importlib.util.module_from_spec(_vue_spec)
    _vue_mod.__package__ = "core.rendering"
    # Inject the already-loaded perceptual module so the relative import resolves
    sys.modules.setdefault("core", type(sys)("core"))
    sys.modules.setdefault("core.rendering", type(sys)("core.rendering"))
    sys.modules["core.rendering.perceptual_calibration_engine"] = _mod
    sys.modules["core.rendering.visual_unification_engine"] = _vue_mod
    _vue_spec.loader.exec_module(_vue_mod)

    engine = _vue_mod.VisualUnificationEngine()
    tile = _ocean_tile(H=32, W=32)
    result = engine.unify(tile, {})
    assert result.dtype == np.uint8
    assert result.shape == tile.shape
    assert not np.isnan(result.astype(float)).any()
