"""
VC Types — shared data structures for the Visual Consistency Layer.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional
import numpy as np

from core.m1.mask_types import TileBBox


# ---------------------------------------------------------------------------
# Biome → base color (linear RGB) — mirrors D6 binding palette.
# Defined here so VC is independent of D6 internal constants.
# ---------------------------------------------------------------------------
BIOME_BASE_COLORS: dict = {
    0:   (0.04, 0.14, 0.44),   # ocean
    1:   (0.10, 0.50, 0.62),   # shallow_water
    2:   (0.52, 0.42, 0.22),   # land (generic)
    3:   (0.75, 0.58, 0.25),   # desert
    4:   (0.18, 0.38, 0.14),   # forest
    5:   (0.28, 0.42, 0.24),   # wetland
    6:   (0.85, 0.92, 0.98),   # ice
    7:   (0.44, 0.42, 0.40),   # urban
    255: (0.30, 0.30, 0.30),   # unknown
}

# Uncertainty σ (in pixels) → Gaussian blur width for coastline / biome edges
# Higher uncertainty → wider transition band
BASE_SIGMA_PX = 1.2
MAX_SIGMA_PX  = 4.0


@dataclass
class VCRenderContext:
    """
    Stabilised, continuous per-tile visual context output by the VC Layer.
    Consumed by D6 renderer as per-tile uniform data.

    All array shapes are (rows, cols).
    """
    # Per-point base RGB color after biome blending  shape (H, W, 3) float32
    base_color_field: np.ndarray

    # Blend weight field: 0=pure source biome, 1=fully blended  (H, W) float32
    biome_blend_field: np.ndarray

    # Continuous coastline gradient: 0=deep ocean, 1=solid land  (H, W) float32
    coastline_gradient_field: np.ndarray

    # Temporal stability: 0=changed from prev frame, 1=identical  (H, W) float32
    temporal_stability_field: np.ndarray

    # Uncertainty-driven softness weight for D6                    (H, W) float32
    uncertainty_modulation_field: np.ndarray

    bbox: TileBBox
    shape: Tuple[int, int] = field(init=False)

    def __post_init__(self):
        self.shape = self.coastline_gradient_field.shape

    # ------------------------------------------------------------------
    # Convenience metrics
    # ------------------------------------------------------------------

    def coastline_gradient_range(self) -> Tuple[float, float]:
        arr = self.coastline_gradient_field
        return float(arr.min()), float(arr.max())

    def mean_temporal_stability(self) -> float:
        return float(self.temporal_stability_field.mean())

    def mean_uncertainty_modulation(self) -> float:
        return float(self.uncertainty_modulation_field.mean())

    def has_gradient_transition(self, tolerance: float = 0.05) -> bool:
        """True when the coastline field contains values strictly between 0 and 1."""
        lo, hi = self.coastline_gradient_range()
        mid_values = self.coastline_gradient_field[
            (self.coastline_gradient_field > tolerance) &
            (self.coastline_gradient_field < 1.0 - tolerance)
        ]
        return len(mid_values) > 0
