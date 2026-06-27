"""Perceptual Calibration Engine — Stage 15.

Pipeline position (FINAL step after VisualUnificationEngine):
    VisualUnificationEngine → PerceptualCalibrationEngine → Tile Output

Role: align tile output to the perceptual distribution of real Earth imagery
(NASA Blue Marble / Google Earth statistics). This is NOT physics — it is
pure perceptual grounding: map the physically-correct output to the luminance
and saturation ranges that human vision expects to see.

Three calibration domains:
  1. Ocean — luminance percentile anchoring to reference distribution
  2. Land  — green/desert tone anchoring, soil desaturation
  3. Ice   — brightness percentile clamp + blue channel rolloff

Constraints:
  - No physics computation, no geo fields, no spectral math
  - All operations are per-pixel tone mappings only (no spatial convolution)
  - Per-channel delta ≤ 20 per pixel (slightly wider than Stage 14 to allow
    histogram matching freedom, but still conservative)
  - Deterministic, CPU-only, no random state
  - Does NOT modify geometry or UV coordinates
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import numpy as np


# ── Reference perceptual anchors (derived from Blue Marble statistics) ──────
# These are luminance (0–255) percentile targets for each surface type.
# Values chosen to match human perception of "typical Earth from orbit".

_OCEAN_ANCHORS: Tuple[Tuple[float, float], ...] = (
    # (source_percentile, target_luminance)
    (0.02,  10.0),   # deep abyssal ocean — nearly black
    (0.15,  28.0),   # deep ocean average
    (0.40,  52.0),   # mid ocean
    (0.65,  80.0),   # mid-shallow ocean
    (0.82, 105.0),   # shallow coastal
    (0.94, 130.0),   # reef / very shallow — brightest before ice
    (1.00, 148.0),   # ceiling for ocean tone (never brighter than this)
)

_LAND_SAT_MAX = 0.72        # vegetation saturation ceiling (prevent neon green)
_DESERT_WARMTH_B_SCALE = 0.88   # blue channel scale-down for warm desert tones
_SOIL_DESAT_THRESHOLD = 0.55    # saturation above which soil/rock gets pulled back
_SOIL_DESAT_STRENGTH = 0.12     # fraction of desat applied above threshold

_ICE_LUMA_P99 = 248.0       # top 1% brightness clamp target
_ICE_LUMA_P97 = 240.0       # top 3% brightness clamp target
_ICE_BLUE_SCALE_MAX = 0.92  # blue channel max scale-down in ice highlights


class PerceptualCalibrationEngine:
    """Apply perceptual distribution calibration as the absolute final pipeline step."""

    def calibrate(self, tile: np.ndarray, metadata: Dict[str, Any] | None = None) -> np.ndarray:
        """Run all three calibration passes. Returns uint8 array of same shape.

        tile:     (H, W, 3) uint8
        metadata: optional tile metadata (reserved)
        """
        arr = tile.astype(np.float32)

        arr = self.calibrate_ocean(arr)
        arr = self.calibrate_land(arr)
        arr = self.calibrate_ice(arr)

        return np.clip(np.rint(arr), 0, 255).astype(np.uint8)

    # ── 1. Ocean perceptual histogram calibration ────────────────────────────

    def calibrate_ocean(self, img: np.ndarray) -> np.ndarray:
        """Histogram match ocean tones to reference perceptual distribution.

        Strategy:
          - Identify ocean pixels via blue-dominant + moderate brightness mask
          - Compute per-pixel luminance
          - Map luminance through anchor table using smooth piecewise interpolation
          - Apply correction proportionally to ocean mask weight
          - Per-channel delta bounded to ≤ 18
        """
        arr = img.copy()
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

        # Ocean mask: blue channel dominant, not ice-white
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
        blue_excess = b - np.maximum(r, g) * 0.85
        ocean_w = np.clip(blue_excess / 35.0, 0.0, 1.0)
        # Exclude very bright pixels (ice/clouds)
        bright_suppress = np.clip(1.0 - (luma - 180.0) / 40.0, 0.0, 1.0)
        ocean_w = ocean_w * bright_suppress

        if ocean_w.max() < 0.01:
            return arr  # no ocean pixels in this tile

        # Build percentile → target luminance mapping from anchors
        src_percentiles = np.array([a[0] for a in _OCEAN_ANCHORS], dtype=np.float32)
        tgt_luminances  = np.array([a[1] for a in _OCEAN_ANCHORS], dtype=np.float32)

        # Compute current luminance percentiles over ocean-weighted pixels
        ocean_flat = luma[ocean_w > 0.1]
        if ocean_flat.size < 16:
            return arr

        # Map each anchor's source percentile to an actual luminance threshold
        src_luminances = np.percentile(ocean_flat, src_percentiles * 100.0).astype(np.float32)

        # Build monotonic mapping: current luma → target luma (piecewise linear)
        # Ensure strict monotonicity
        src_lum_mono = _ensure_monotone(src_luminances)
        tgt_lum_mono = _ensure_monotone(tgt_luminances)

        # Map all pixel luminances
        mapped_luma = np.interp(luma, src_lum_mono, tgt_lum_mono).astype(np.float32)

        # Compute scale factor (avoid div-by-zero on black pixels)
        safe_luma = np.maximum(luma, 1.0)
        scale = np.clip(mapped_luma / safe_luma, 0.5, 2.0)

        # Apply scaled correction blended by ocean weight
        correction_scale = 1.0 + ocean_w * (scale - 1.0)
        for ch in range(3):
            arr[..., ch] = np.clip(arr[..., ch] * correction_scale, 0.0, 255.0)

        # Enforce per-channel delta bound
        delta = np.abs(arr - img)
        exceed = delta > 18.0
        if exceed.any():
            arr = np.where(exceed, img + np.sign(arr - img) * 18.0, arr)

        return np.clip(arr, 0.0, 255.0)

    # ── 2. Land tone anchoring ───────────────────────────────────────────────

    def calibrate_land(self, img: np.ndarray) -> np.ndarray:
        """Anchor land tones to Earth visual priors.

        Three sub-passes:
          a. Vegetation green clamp (prevent neon/oversaturated green)
          b. Desert warm tone anchoring (reduce blue cast in sandy regions)
          c. Soil/rock desaturation normalization
        """
        arr = img.copy()
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

        # Land mask: not blue-dominant, not ice-white
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
        blue_dom = np.clip((b - np.maximum(r, g) * 0.85) / 35.0, 0.0, 1.0)
        land_w = np.clip(1.0 - blue_dom, 0.0, 1.0)
        land_w = land_w * np.clip(1.0 - (luma - 210.0) / 30.0, 0.0, 1.0)

        if land_w.max() < 0.01:
            return arr

        # ── a. Vegetation green clamp ────────────────────────────────────────
        maxc = np.maximum.reduce([r, g, b])
        minc = np.minimum.reduce([r, g, b])
        saturation = (maxc - minc) / np.maximum(maxc, 1.0)

        # Green-dominant pixels with excess saturation
        green_dom = np.clip((g - np.maximum(r, b) * 0.75) / 30.0, 0.0, 1.0)
        veg_over_sat = np.clip((saturation - _LAND_SAT_MAX) / 0.20, 0.0, 1.0)
        veg_w = land_w * green_dom * veg_over_sat

        if veg_w.max() > 0.001:
            gray = luma[..., None]
            blend = veg_w[..., None] * 0.25
            arr = arr * (1.0 - blend) + gray * blend

        # ── b. Desert warm tone anchoring ────────────────────────────────────
        # Desert: red or yellow dominant, moderate brightness, not too saturated
        r2, g2, b2 = arr[..., 0], arr[..., 1], arr[..., 2]
        warm_dom = np.clip((r2 - b2 * 1.1) / 30.0, 0.0, 1.0)
        moderate_bright = np.clip(1.0 - np.abs(luma - 140.0) / 80.0, 0.0, 1.0)
        desert_w = land_w * warm_dom * moderate_bright

        if desert_w.max() > 0.001:
            # Reduce blue slightly in warm desert pixels
            scale_b = 1.0 - desert_w * (1.0 - _DESERT_WARMTH_B_SCALE)
            arr[..., 2] = np.clip(arr[..., 2] * scale_b, 0.0, 255.0)

        # ── c. Soil/rock desaturation normalization ──────────────────────────
        r3, g3, b3 = arr[..., 0], arr[..., 1], arr[..., 2]
        maxc3 = np.maximum.reduce([r3, g3, b3])
        minc3 = np.minimum.reduce([r3, g3, b3])
        sat3 = (maxc3 - minc3) / np.maximum(maxc3, 1.0)

        # Non-green, non-blue land with high saturation → soil
        not_green = np.clip(1.0 - np.clip((g3 - np.maximum(r3, b3) * 0.75) / 20.0, 0.0, 1.0), 0.0, 1.0)
        soil_over_sat = np.clip((sat3 - _SOIL_DESAT_THRESHOLD) / 0.25, 0.0, 1.0)
        soil_w = land_w * not_green * soil_over_sat

        if soil_w.max() > 0.001:
            luma3 = 0.2126 * r3 + 0.7152 * g3 + 0.0722 * b3
            gray3 = luma3[..., None]
            blend = soil_w[..., None] * _SOIL_DESAT_STRENGTH
            arr = arr * (1.0 - blend) + gray3 * blend

        # Enforce per-channel delta bound
        delta = np.abs(arr - img)
        exceed = delta > 18.0
        if exceed.any():
            arr = np.where(exceed, img + np.sign(arr - img) * 18.0, arr)

        return np.clip(arr, 0.0, 255.0)

    # ── 3. Ice perceptual normalization ──────────────────────────────────────

    def calibrate_ice(self, img: np.ndarray) -> np.ndarray:
        """Normalize ice reflectance to avoid plastic / overexposed appearance.

        Three sub-passes:
          a. Top-1% brightness clamp to _ICE_LUMA_P99
          b. Top-3% range soft rolloff
          c. Blue channel scale-down for bright ice highlights
        """
        arr = img.copy()
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b

        # Ice mask: near-white, low saturation
        maxc = np.maximum.reduce([r, g, b])
        minc = np.minimum.reduce([r, g, b])
        saturation = (maxc - minc) / np.maximum(maxc, 1.0)
        ice_w = np.clip((luma - 190.0) / 40.0, 0.0, 1.0)
        ice_w = ice_w * np.clip(1.0 - (saturation - 0.15) / 0.15, 0.0, 1.0)

        if ice_w.max() < 0.01:
            return arr

        # ── a. Hard clamp at P99 ceiling ────────────────────────────────────
        luma_p99_apply = np.clip((luma - _ICE_LUMA_P99) / 10.0, 0.0, 1.0) * ice_w
        target_p99 = np.minimum(arr, _ICE_LUMA_P99)
        arr = arr * (1.0 - luma_p99_apply[..., None]) + target_p99 * luma_p99_apply[..., None]

        # ── b. Soft rolloff for P97–P99 range ───────────────────────────────
        luma2 = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
        rolloff_w = np.clip((luma2 - _ICE_LUMA_P97) / (_ICE_LUMA_P99 - _ICE_LUMA_P97), 0.0, 1.0)
        rolloff_w = rolloff_w * ice_w
        # Compress toward P97 value (soft shoulder)
        arr = arr * (1.0 - rolloff_w[..., None] * 0.30) + \
              arr * (_ICE_LUMA_P97 / np.maximum(luma2, 1.0))[..., None] * (rolloff_w[..., None] * 0.30)

        # ── c. Blue channel scale-down in ice highlights ─────────────────────
        luma3 = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
        blue_excess_ice = np.clip((arr[..., 2] / np.maximum(arr[..., 0], 1.0) - 1.05) / 0.15, 0.0, 1.0)
        blue_scale_w = ice_w * blue_excess_ice * np.clip((luma3 - 200.0) / 40.0, 0.0, 1.0)
        b_scale = 1.0 - blue_scale_w * (1.0 - _ICE_BLUE_SCALE_MAX)
        arr[..., 2] = np.clip(arr[..., 2] * b_scale, 0.0, 255.0)

        # Enforce per-channel delta bound
        delta = np.abs(arr - img)
        exceed = delta > 20.0
        if exceed.any():
            arr = np.where(exceed, img + np.sign(arr - img) * 20.0, arr)

        return np.clip(arr, 0.0, 255.0)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_monotone(arr: np.ndarray) -> np.ndarray:
    """Return array with strictly non-decreasing values (running max)."""
    out = arr.copy()
    for i in range(1, len(out)):
        if out[i] <= out[i - 1]:
            out[i] = out[i - 1] + 0.5
    return out
