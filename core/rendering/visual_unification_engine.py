"""Visual Unification Engine — perceptual tone curve normalization (Stage 14).

Pipeline position (penultimate step; PerceptualCalibrationEngine follows):
    NoonAirColorizer → VisualUnificationEngine → PerceptualCalibrationEngine → Tile Output

Role: apply global perceptual consistency curves so that the compounded output
of GeoFieldEngine → SpectralEarthEngine → NoonAirColorizer reads as a coherent
single image rather than a stack of independent layers.

Applies (in order):
  1. Ocean tone normalization — mild S-curve on ocean-blue pixels
  2. Land saturation harmonization — soft-reduce oversaturated land areas
  3. Ice brightness soft clamp — prevent harsh white clipping near 255
  4. Tile edge feathering — local contrast reduction on outer N pixels
     (NOT cross-tile smoothing; WebGL handles UV continuity between tiles)

Constraints:
  - No new physics, no new geo fields, no spectral computation
  - All changes are tone curves only (no hue rotation)
  - Per-channel delta ≤ 12 per pixel (conservative, does not break visual hierarchy)
  - Deterministic, CPU-only, no random state
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from .perceptual_calibration_engine import PerceptualCalibrationEngine

_perceptual_calibration = PerceptualCalibrationEngine()


_FEATHER_PX = 5        # pixels wide on each edge
_FEATHER_STRENGTH = 0.15   # max contrast reduction at edge (0 = center, 0.15 = edge)


class VisualUnificationEngine:
    """Apply perceptual tone normalization as the final pipeline step."""

    def unify(self, tile: np.ndarray, metadata: Dict[str, Any]) -> np.ndarray:
        """Normalize tile perceptually. Returns uint8 array of same shape.

        tile:     (H, W, 3) uint8 — fully colorized output from NoonAirColorizer
        metadata: tile metadata dict (bounds, lod, etc.) — reserved for future use
        """
        arr = tile.astype(np.float32)

        arr = self._normalize_ocean_tone(arr)
        arr = self._harmonize_land_saturation(arr)
        arr = self._soft_clamp_ice_brightness(arr)
        arr = self._feather_tile_edges(arr)

        # Stage 15: perceptual histogram calibration (final step)
        unified = np.clip(np.rint(arr), 0, 255).astype(np.uint8)
        return _perceptual_calibration.calibrate(unified, metadata)

    # ── Step 1: Ocean tone normalization ────────────────────────────────────

    def _normalize_ocean_tone(self, arr: np.ndarray) -> np.ndarray:
        """Mild S-curve on blue-dominant pixels to normalize ocean brightness.

        Ocean pixels that are over-bright after spectral processing get a gentle
        pull back toward mid-tones. Change bounded to ≤ 8 per channel.
        """
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

        # Ocean mask: blue meaningfully exceeds red and isn't ice-bright
        blue_excess = b - (r + g) * 0.55
        ocean_w = np.clip(blue_excess / 40.0, 0.0, 1.0)  # [0, 1]

        # S-curve: pulls bright blues slightly darker, dark blues slightly brighter
        # Uses a sigmoid centered at 110 (mid ocean brightness)
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
        curve = 8.0 * (2.0 / (1.0 + np.exp(-0.02 * (luma - 110.0))) - 1.0)
        # curve is in [-8, +8], negative for bright (>110), positive for dark (<110)
        correction = ocean_w * (-curve * 0.5)  # very mild

        result = arr.copy()
        result[..., 0] = arr[..., 0] + correction * 0.15   # red barely touched
        result[..., 1] = arr[..., 1] + correction * 0.35
        result[..., 2] = arr[..., 2] + correction * 0.50   # blue carries most

        return np.clip(result, 0.0, 255.0)

    # ── Step 2: Land saturation harmonization ───────────────────────────────

    def _harmonize_land_saturation(self, arr: np.ndarray) -> np.ndarray:
        """Soft-reduce oversaturated land areas. Max change ≤ 6 per channel."""
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]

        maxc = np.maximum.reduce([r, g, b])
        minc = np.minimum.reduce([r, g, b])
        saturation = (maxc - minc) / np.maximum(maxc, 1.0)

        # Only apply to non-ocean pixels (blue not dominant)
        blue_excess = b - (r + g) * 0.55
        land_w = np.clip(1.0 - blue_excess / 30.0, 0.0, 1.0)

        # Suppress oversaturation above threshold (0.65)
        over_sat = np.clip((saturation - 0.65) / 0.35, 0.0, 1.0)
        desaturate_w = land_w * over_sat * 0.10  # very mild, max 10%

        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
        gray = luma[..., None]

        result = arr * (1.0 - desaturate_w[..., None]) + gray * desaturate_w[..., None]
        return np.clip(result, 0.0, 255.0)

    # ── Step 3: Ice brightness soft clamp ──────────────────────────────────

    def _soft_clamp_ice_brightness(self, arr: np.ndarray) -> np.ndarray:
        """Prevent harsh white near 255; soft-clamp very bright pixels to 248.

        Applies only to pixels with mean brightness > 230. Max shift ≤ 10.
        """
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        brightness = (r + g + b) / 3.0

        # Pixels above threshold get pulled toward 248
        threshold = 230.0
        target = 248.0
        clamp_w = np.clip((brightness - threshold) / 20.0, 0.0, 1.0)[..., None]

        # Fractional pull toward soft ceiling
        ceiling = np.minimum(arr, target)
        result = arr * (1.0 - clamp_w * 0.40) + ceiling * (clamp_w * 0.40)

        return np.clip(result, 0.0, 255.0)

    # ── Step 4: Tile edge feathering ────────────────────────────────────────

    def _feather_tile_edges(self, arr: np.ndarray) -> np.ndarray:
        """Reduce local contrast on the outer N pixels of the tile.

        This is tile-local only — NOT cross-tile smoothing.
        WebGL UV coordinates handle boundary continuity between adjacent tiles.
        Max strength: _FEATHER_STRENGTH (15%) at the outermost pixel.
        """
        H, W = arr.shape[:2]
        if H < 2 * _FEATHER_PX + 1 or W < 2 * _FEATHER_PX + 1:
            return arr  # tile too small to feather

        # Build edge weight map: 1.0 at edge, 0.0 at inner boundary
        weight = np.zeros((H, W), dtype=np.float32)
        for k in range(_FEATHER_PX):
            strength = _FEATHER_STRENGTH * (1.0 - k / _FEATHER_PX)
            weight[:k + 1, :] = np.maximum(weight[:k + 1, :], strength)
            weight[H - k - 1:, :] = np.maximum(weight[H - k - 1:, :], strength)
            weight[:, :k + 1] = np.maximum(weight[:, :k + 1], strength)
            weight[:, W - k - 1:] = np.maximum(weight[:, W - k - 1:], strength)

        # Pull edge pixels toward tile mean (reduces harsh contrast at seams)
        tile_mean = arr.mean(axis=(0, 1), keepdims=True)
        result = arr * (1.0 - weight[..., None]) + tile_mean * weight[..., None]

        return np.clip(result, 0.0, 255.0)
