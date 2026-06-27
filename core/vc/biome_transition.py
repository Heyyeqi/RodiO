"""
Biome Transition Engine

Converts hard biome-code boundaries in an M1 SemanticMaskTile into smooth,
physically plausible colour gradients. Two operations:

  1. compute_blend()       — scalar blend factor for a point between two biomes
  2. apply_transition()    — full tile: biome_mask → blended colour field

No raster output, no GPU, pure numpy CPU.
"""

import math
import numpy as np
from typing import Tuple

from core.m1.mask_types import SemanticMaskTile, BIOME_NAMES
from .vc_types import BIOME_BASE_COLORS
from ._kernels import gaussian_blur, gaussian_blur_rgb, detect_boundary, clamp


# Perceptual distance between two biomes drives blend width.
# Small = subtle transition (e.g. forest/wetland), large = dramatic (ocean/desert).
_BLEND_SIGMA_BASE = 1.0       # minimum blur sigma (px)
_BLEND_SIGMA_SCALE = 3.0      # added per unit of colour distance

# Confidence → inverse blend: high confidence = less blending
_MIN_BLEND = 0.05
_MAX_BLEND = 0.90


def _biome_color_distance(biome_a: int, biome_b: int) -> float:
    """Perceptual RGB distance between two biome base colours."""
    ca = BIOME_BASE_COLORS.get(biome_a, (0.3, 0.3, 0.3))
    cb = BIOME_BASE_COLORS.get(biome_b, (0.3, 0.3, 0.3))
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(ca, cb)))


class BiomeTransition:
    """
    Smooths hard biome boundaries in M1 mask tiles.

    Design:
    - Each pixel gets its base colour from BIOME_BASE_COLORS.
    - Gaussian blur is applied to the colour field; width is modulated by
      the local uncertainty and colour distance at the boundary.
    - A blend weight field records how much blending occurred at each point.
    """

    def __init__(self, base_sigma: float = _BLEND_SIGMA_BASE):
        self.base_sigma = base_sigma

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_blend(
        self,
        biome_a: int,
        biome_b: int,
        confidence: float = 0.5,
    ) -> float:
        """
        Return the blend factor (0–1) for a boundary between biome_a and biome_b.

        Args:
            biome_a, biome_b: BIOME_* integer codes
            confidence:       SAL confidence at the point (0–1)

        Returns:
            Blend factor in [_MIN_BLEND, _MAX_BLEND].
            Higher confidence → less blending (sharper boundary).
            Greater colour distance → more blending (softer transition).
        """
        dist = _biome_color_distance(biome_a, biome_b)
        # High confidence suppresses blending
        conf_factor = 1.0 - min(1.0, confidence / 0.80)
        blend = _MIN_BLEND + (_MAX_BLEND - _MIN_BLEND) * dist * conf_factor
        return float(clamp(np.array([blend]), _MIN_BLEND, _MAX_BLEND)[0])

    def apply_transition(
        self,
        mask_tile: SemanticMaskTile,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Convert a hard biome_mask into a smoothly blended colour field.

        Args:
            mask_tile: SemanticMaskTile from M1

        Returns:
            base_color_field: (H, W, 3) float32 — blended RGB
            biome_blend_field: (H, W) float32 — blend weight per pixel
        """
        H, W = mask_tile.shape
        biome = mask_tile.biome_mask.astype(np.int32)
        mean_conf = mask_tile.mean_confidence()
        mean_unc  = mask_tile.mean_uncertainty()

        # 1. Build raw colour field (no blending yet)
        color_field = np.zeros((H, W, 3), dtype=np.float32)
        for code, rgb in BIOME_BASE_COLORS.items():
            mask = (biome == code)
            if mask.any():
                for c in range(3):
                    color_field[:, :, c][mask] = rgb[c]

        # 2. Compute boundary map (float, 0=interior, >0=boundary)
        boundary = detect_boundary(biome)
        has_boundary = boundary.max() > 0

        if not has_boundary:
            # Single-biome tile: no blending needed
            blend_field = np.full((H, W), _MIN_BLEND, dtype=np.float32)
            return color_field, blend_field

        # 3. Compute adaptive blur sigma from uncertainty and colour distance
        # Estimate typical boundary colour distance from boundary pixels
        boundary_mask = boundary > 0
        sigma = self.base_sigma + _BLEND_SIGMA_SCALE * mean_unc * 0.5
        sigma = min(sigma, max(H, W) / 4.0)   # cap at quarter of tile

        # 4. Blur the colour field
        blurred_color = gaussian_blur_rgb(color_field, sigma)

        # 5. Blend field: boundary pixels get high blend, interior gets low
        blend_proximity = gaussian_blur(boundary, sigma * 1.5)
        blend_proximity = clamp(blend_proximity / max(blend_proximity.max(), 1e-8))
        blend_field = (
            _MIN_BLEND + (_MAX_BLEND - _MIN_BLEND) * blend_proximity
        ).astype(np.float32)

        # 6. Final colour: lerp between raw and blurred by blend_field
        t = blend_field[:, :, np.newaxis]
        final_color = clamp(color_field * (1 - t) + blurred_color * t)

        return final_color.astype(np.float32), blend_field
