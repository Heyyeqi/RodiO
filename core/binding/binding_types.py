"""
Binding Types — shared data structures for the SAL → D6 Binding Layer.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, List

# RGB color vector, each channel in [0.0, 1.0]
ColorVector = Tuple[float, float, float]


@dataclass
class TemporalState:
    """
    Caller-supplied time and environment context used for
    seasonal modulation and climate-aware visual mapping.
    """
    month: int                          # 1–12
    hour: int                           # 0–23 UTC
    lat: float                          # latitude (degrees)
    climate_zone: Optional[str] = None  # Köppen-derived hint: "arid", "tropical", "polar", etc.
    snow_cover: float = 0.0             # 0.0–1.0 fractional snow cover
    cloud_cover: float = 0.0            # 0.0–1.0 fractional cloud cover


@dataclass
class D6RenderInput:
    """
    Standardized per-point rendering input consumed by the D6 renderer.

    All color values are linear RGB in [0.0, 1.0].
    """
    semantic_class: str                 # SAL final_class
    base_color: ColorVector             # class-derived base color
    adjusted_color: ColorVector         # after confidence + uncertainty adjustment
    confidence: float                   # SAL confidence_score (0–1)
    uncertainty: float                  # derived from SAL winner_margin (0–1, 0=certain)
    light_factor: float                 # time-of-day / seasonal brightness modifier
    seasonal_modifier: float            # seasonal albedo / vegetation modifier
    uncertainty_weight: float           # how strongly uncertainty degrades appearance
    is_conflict_zone: bool              # True when SAL detected cross-source conflict
    notes: List[str] = field(default_factory=list)  # human-readable trace


@dataclass
class VisualAdjustment:
    """Intermediate product from uncertainty / confidence adjustments."""
    desaturation: float       # 0=none, 1=fully grey
    brightness_offset: float  # additive: negative darkens, positive brightens
    noise_proxy: float        # CPU noise intensity (0–1)
    blur_proxy: float         # conceptual blur weight (0–1, no GPU ops)
