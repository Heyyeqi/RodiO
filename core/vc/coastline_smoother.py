"""
Coastline Smoother

Converts a binary ocean/land mask into a continuous probability band.

Instead of a hard edge (pixel is either 0=ocean or 1=land), the output
coastline_gradient_field contains smooth values in [0, 1] where:
  0.0 = deep ocean (far from any coastline)
  1.0 = solid land  (far from any coastline)
  0.0–1.0 gradient band = probabilistic shoreline zone

Width of the gradient band is modulated by SAL uncertainty:
  uncertainty ↑ → wider transition (more ambiguous coast)
  uncertainty ↓ → narrower transition (well-defined coast)

No raster output, no GPU, pure numpy CPU.
"""

import numpy as np
from typing import Optional

from ._kernels import gaussian_blur, clamp, detect_boundary
from .vc_types import BASE_SIGMA_PX, MAX_SIGMA_PX


class CoastlineSmoother:
    """
    Removes binary coastline artifacts by replacing hard mask edges with
    smooth probability gradients.

    Args:
        base_sigma: minimum Gaussian σ in pixels (default 1.2)
        max_sigma:  maximum σ (default 4.0)
    """

    def __init__(
        self,
        base_sigma: float = BASE_SIGMA_PX,
        max_sigma: float  = MAX_SIGMA_PX,
    ):
        self.base_sigma = base_sigma
        self.max_sigma  = max_sigma

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def smooth(
        self,
        ocean_mask: np.ndarray,
        uncertainty_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Convert a binary ocean_mask into a smooth coastline gradient field.

        Args:
            ocean_mask:       bool/float array, True/1 where SAL class = ocean
            uncertainty_mask: float32 array [0, 1], margin-derived uncertainty

        Returns:
            coastline_gradient_field: float32 (H, W) in [0, 1]
                0 = ocean, 1 = land, gradient band at coastline
        """
        # Start from land-fraction: 1 = land, 0 = ocean
        land_float = 1.0 - ocean_mask.astype(np.float32)

        # Adaptive blur sigma driven by mean uncertainty
        mean_unc = float(uncertainty_mask.mean())
        sigma = self._sigma(mean_unc, land_float.shape)

        if sigma < 0.1:
            return land_float

        smoothed = gaussian_blur(land_float, sigma)
        return clamp(smoothed)

    def gradient_edge(self, boundary_zone: np.ndarray) -> np.ndarray:
        """
        Given a binary boundary indicator (1 where ocean/land boundary detected),
        produce a probabilistic shoreline band with smooth falloff on both sides.

        Args:
            boundary_zone: float/bool (H, W), 1 at boundary pixels

        Returns:
            Gradient band: float32 (H, W), peak at boundary, decaying outward.
        """
        bz = boundary_zone.astype(np.float32)
        if bz.max() == 0:
            return bz

        sigma = self.base_sigma * 2.0
        band = gaussian_blur(bz, sigma)
        return clamp(band / max(band.max(), 1e-8))

    def coastline_width_px(self, uncertainty: float) -> float:
        """Return the expected transition band width in pixels for a given uncertainty."""
        return self._sigma(uncertainty, (1, 1)) * 3.0  # ~3σ covers 99.7% of Gaussian

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _sigma(self, uncertainty: float, shape: tuple) -> float:
        sigma = self.base_sigma + (self.max_sigma - self.base_sigma) * uncertainty
        # Never wider than 1/4 of the shortest tile dimension
        max_allowed = min(shape) / 4.0
        return min(sigma, max_allowed)
