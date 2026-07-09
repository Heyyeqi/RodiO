"""
Semantic → Visual Mapper

Maps SAL final_class + optional climate context to a base color vector,
then adjusts that color by confidence (degrading appearance when uncertain).

All operations are CPU-only linear RGB arithmetic. No GPU / shader calls.

Design principles
-----------------
- High-confidence decisions produce vivid, saturated colors.
- Low-confidence decisions produce desaturated, muted variants of the same hue.
- Climate zone refines the "land" class into biome-appropriate tones without
  changing the SAL decision (separation of truth vs. representation).
"""

import math
from typing import Optional

from .binding_types import ColorVector, TemporalState


# ---------------------------------------------------------------------------
# Base color palette (linear RGB, perceptually tuned)
# ---------------------------------------------------------------------------

_BASE_COLORS: dict = {
    "ocean":         (0.04, 0.14, 0.44),   # deep ocean blue
    "shallow_water": (0.10, 0.50, 0.62),   # tropical teal
    "land":          (0.52, 0.42, 0.22),   # generic earth tone
    "desert":        (0.75, 0.58, 0.25),   # warm arid sand
    "forest":        (0.18, 0.38, 0.14),   # temperate green
    "wetland":       (0.28, 0.42, 0.24),   # muted swamp green
    "ice":           (0.85, 0.92, 0.98),   # polar white-blue
    "urban":         (0.44, 0.42, 0.40),   # concrete grey
    "unknown":       (0.30, 0.30, 0.30),   # neutral grey
}

# Low-confidence variants (pre-desaturated, shifted toward grey)
_LOW_CONF_COLORS: dict = {
    "ocean":         (0.18, 0.38, 0.58),   # washed-out cyan-blue
    "shallow_water": (0.25, 0.52, 0.60),
    "land":          (0.48, 0.45, 0.38),
    "desert":        (0.60, 0.55, 0.42),
    "forest":        (0.38, 0.44, 0.32),
    "wetland":       (0.40, 0.45, 0.38),
    "ice":           (0.78, 0.82, 0.88),
    "urban":         (0.50, 0.50, 0.50),
    "unknown":       (0.40, 0.40, 0.40),
}

# Climate-zone biome overrides applied when semantic_class == "land"
_CLIMATE_LAND_OVERRIDES: dict = {
    "arid":      "desert",
    "semi-arid": "desert",
    "tropical":  "forest",
    "temperate": "forest",
    "polar":     "ice",
    "tundra":    "wetland",
}

# Confidence threshold below which the low-confidence palette is blended in
_CONF_LOW_THRESHOLD  = 0.30
_CONF_HIGH_THRESHOLD = 0.80


def _lerp_color(a: ColorVector, b: ColorVector, t: float) -> ColorVector:
    """Linear interpolation between two RGB colors. t=0 → a, t=1 → b."""
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class SemanticToVisualMapper:
    """
    Converts a semantic class (+ optional climate hint) to a visual color,
    then adjusts it based on confidence.
    """

    def map(
        self,
        sal_class: str,
        temporal: Optional[TemporalState] = None,
    ) -> ColorVector:
        """
        Map a SAL semantic class to a base color vector.

        Args:
            sal_class: one of SAL's SEMANTIC_CLASSES
            temporal:  optional temporal state; climate_zone refines "land"

        Returns:
            Linear RGB ColorVector in [0, 1]³.
        """
        effective_class = sal_class

        # Refine "land" using climate zone when available
        if sal_class == "land" and temporal is not None and temporal.climate_zone:
            biome = _CLIMATE_LAND_OVERRIDES.get(temporal.climate_zone.lower())
            if biome:
                effective_class = biome

        return _BASE_COLORS.get(effective_class, _BASE_COLORS["unknown"])

    def adjust_by_confidence(
        self,
        color: ColorVector,
        confidence: float,
        sal_class: str = "unknown",
        temporal: Optional[TemporalState] = None,
    ) -> ColorVector:
        """
        Blend the confident color toward its low-confidence variant.

        High confidence (≥ 0.80): full vivid color.
        Low confidence  (≤ 0.30): fully blended toward the muted variant.
        Between:                  linear interpolation.

        Args:
            color:      base color from map()
            confidence: SAL confidence_score (0–1)
            sal_class:  used to look up the low-confidence palette
            temporal:   passed through for biome override on low-conf variant

        Returns:
            Adjusted ColorVector.
        """
        effective_class = sal_class
        if sal_class == "land" and temporal is not None and temporal.climate_zone:
            biome = _CLIMATE_LAND_OVERRIDES.get(temporal.climate_zone.lower())
            if biome:
                effective_class = biome

        low_conf_color = _LOW_CONF_COLORS.get(effective_class, _LOW_CONF_COLORS["unknown"])

        # Blend factor: 0 at high confidence, 1 at low confidence
        t = 1.0 - _clamp(
            (confidence - _CONF_LOW_THRESHOLD) / (_CONF_HIGH_THRESHOLD - _CONF_LOW_THRESHOLD)
        )
        return _lerp_color(color, low_conf_color, t)
