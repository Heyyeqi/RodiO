"""
Rendering Context Builder

Assembles a complete D6RenderInput from a SAL ArbitrationResult and a
TemporalState. Handles:
  - Base color from semantic class + climate zone
  - Confidence-driven color adjustment
  - Uncertainty-driven degradation
  - Temporal modulation (time of day, season, snow)
  - Conflict zone detection → gradient rendering flag

CPU-only. No raster I/O, no GPU calls.
"""

import math
from typing import Optional

from .binding_types import ColorVector, D6RenderInput, TemporalState
from .semantic_to_visual_mapper import SemanticToVisualMapper
from .uncertainty_visualizer import UncertaintyVisualizer


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * _clamp(t)


# ---------------------------------------------------------------------------
# Temporal modulation helpers
# ---------------------------------------------------------------------------

def _solar_elevation_factor(hour: int, lat: float) -> float:
    """
    Approximate solar elevation factor for brightness modulation.
    Returns 0 (night) → 1 (solar noon).
    """
    # Hour angle from solar noon (noon = 12h)
    hour_angle = math.radians((hour - 12) * 15)
    lat_rad = math.radians(lat)
    # Simplified: ignore declination
    factor = math.cos(hour_angle) * math.cos(lat_rad)
    return _clamp(factor)


def _seasonal_modifier(month: int, lat: float) -> float:
    """
    Seasonal vegetation / albedo modifier.
    Northern summer (Jun–Aug) at mid-latitudes → peak green (+modifier).
    Southern hemisphere is inverted.
    Polar regions suppress vegetation year-round.
    Returns a modifier in [0.5, 1.2].
    """
    # Convert month to a phase in [0, 2π] aligned so June = peak north
    phase = math.radians((month - 6) / 12 * 360)
    # Hemisphere sign
    hemi = 1.0 if lat >= 0 else -1.0
    raw = math.cos(phase * hemi)
    # Scale to [0.5, 1.2]: baseline 0.85, amplitude 0.35
    return _clamp(0.85 + 0.35 * raw, 0.5, 1.2)


def _snow_blend(color: ColorVector, snow_cover: float) -> ColorVector:
    """Blend color toward snow white proportionally to snow_cover."""
    snow_white: ColorVector = (0.92, 0.94, 0.98)
    t = _clamp(snow_cover)
    return (
        color[0] + (snow_white[0] - color[0]) * t,
        color[1] + (snow_white[1] - color[1]) * t,
        color[2] + (snow_white[2] - color[2]) * t,
    )


def _cloud_dim(color: ColorVector, cloud_cover: float) -> ColorVector:
    """Darken color under cloud cover."""
    factor = _clamp(1.0 - 0.30 * cloud_cover)
    return (color[0] * factor, color[1] * factor, color[2] * factor)


class RenderingContextBuilder:
    """
    Builds the unified D6RenderInput context from SAL output + temporal state.
    """

    def __init__(self):
        self._mapper = SemanticToVisualMapper()
        self._uv = UncertaintyVisualizer()

    def build(self, sal_state, temporal: Optional[TemporalState] = None) -> D6RenderInput:
        """
        Construct a D6RenderInput from an ArbitrationResult.

        Args:
            sal_state: ArbitrationResult from SemanticArbitrator.resolve()
            temporal:  optional TemporalState for seasonal/diurnal modulation

        Returns:
            D6RenderInput ready for the D6 renderer pipeline.
        """
        notes = []
        t = temporal or TemporalState(month=6, hour=12, lat=0.0)

        # 1. Base color from semantic class + climate context
        base_color = self._mapper.map(sal_state.final_class, t)
        notes.append(f"base_color from class={sal_state.final_class!r} zone={t.climate_zone!r}")

        # 2. Confidence-driven color adjustment
        adj_color = self._mapper.adjust_by_confidence(
            base_color, sal_state.confidence_score, sal_state.final_class, t
        )
        notes.append(f"confidence_adjustment confidence={sal_state.confidence_score:.3f}")

        # 3. Uncertainty from winner margin (entropy fallback for old states)
        uncertainty = self._uv.sal_to_uncertainty(sal_state)
        adj_color = self._uv.apply(adj_color, uncertainty)
        margin = getattr(sal_state, "winner_margin", None)
        if margin is None:
            notes.append(f"uncertainty={uncertainty:.3f} source=entropy entropy={sal_state.entropy:.3f}")
        else:
            notes.append(
                f"uncertainty={uncertainty:.3f} source=winner_margin "
                f"margin={margin:.3f} entropy={sal_state.entropy:.3f}"
            )

        # 4. Temporal: solar brightness
        light_factor = _solar_elevation_factor(t.hour, t.lat)
        notes.append(f"light_factor={light_factor:.3f} (hour={t.hour} lat={t.lat})")

        # 5. Seasonal modifier
        seas_mod = _seasonal_modifier(t.month, t.lat)
        notes.append(f"seasonal_modifier={seas_mod:.3f} (month={t.month})")

        # 6. Snow and cloud
        if t.snow_cover > 0.0:
            adj_color = _snow_blend(adj_color, t.snow_cover)
            notes.append(f"snow_blend snow={t.snow_cover:.2f}")
        if t.cloud_cover > 0.0:
            adj_color = _cloud_dim(adj_color, t.cloud_cover)
            notes.append(f"cloud_dim cloud={t.cloud_cover:.2f}")

        # 7. Uncertainty weight for downstream D6 consumption
        unc_weight = _clamp(uncertainty * (1.0 - sal_state.confidence_score))
        notes.append(f"uncertainty_weight={unc_weight:.3f}")

        return D6RenderInput(
            semantic_class=sal_state.final_class,
            base_color=base_color,
            adjusted_color=adj_color,
            confidence=sal_state.confidence_score,
            uncertainty=uncertainty,
            light_factor=light_factor,
            seasonal_modifier=seas_mod,
            uncertainty_weight=unc_weight,
            is_conflict_zone=sal_state.conflict_detected,
            notes=notes,
        )
