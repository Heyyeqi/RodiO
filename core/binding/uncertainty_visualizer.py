"""
Uncertainty Visualizer

Converts SAL entropy into a set of visual degradation parameters (blur proxy,
saturation reduction, noise proxy) and applies them to a color vector.

This is a CPU-only transform. No raster files, no GPU calls, no shaders.
Outputs are rendering *hints* that the D6 GPU pipeline can later consume.

Design:
    uncertainty = margin-derived ambiguity (0 = certain, 1 = max uncertain).
    SAL entropy remains available as a fallback/diagnostic metric.

    Effects applied:
        1. Saturation reduction  — certainty ↓ → grey shift ↑
        2. Brightness offset     — mild darkening near peak uncertainty
        3. Noise proxy           — conceptual noise intensity for shader
        4. Blur proxy            — conceptual blur weight for shader
"""

import math
from typing import Tuple

from .binding_types import ColorVector, VisualAdjustment


# SAL entropy range: [0, log2(9)] ≈ [0, 3.17] for 9 classes
_MAX_ENTROPY_BITS = math.log2(9)

# Probability gap that counts as a visually clear winner. Current SAL softmax
# usually yields pure-ocean margins around 0.06–0.07, so 0.08 keeps clean
# cases crisp while still marking close races as ambiguous.
_CLEAR_WINNER_MARGIN = 0.08

# Uncertainty thresholds for effect onset/saturation
_UNCERTAIN_LOW  = 0.20   # below this: no degradation
_UNCERTAIN_HIGH = 0.85   # above this: maximum degradation


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _rgb_to_luminance(c: ColorVector) -> float:
    """Perceptual luminance (BT.709)."""
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _desaturate(color: ColorVector, amount: float) -> ColorVector:
    """Blend a color toward its greyscale equivalent. amount ∈ [0, 1]."""
    luma = _rgb_to_luminance(color)
    return (
        color[0] + (luma - color[0]) * amount,
        color[1] + (luma - color[1]) * amount,
        color[2] + (luma - color[2]) * amount,
    )


def _brightness_shift(color: ColorVector, offset: float) -> ColorVector:
    """Additive brightness shift, clamped to [0, 1]."""
    return (
        _clamp(color[0] + offset),
        _clamp(color[1] + offset),
        _clamp(color[2] + offset),
    )


class UncertaintyVisualizer:
    """
    Applies uncertainty-driven visual degradation to a color vector.

    Uncertainty is derived from SAL winner margin when available and
    normalised to [0, 1]. Entropy is retained as a fallback.
    """

    def entropy_to_uncertainty(self, entropy: float) -> float:
        """Normalise SAL Shannon entropy (bits) to [0, 1]."""
        return _clamp(entropy / _MAX_ENTROPY_BITS)

    def margin_to_uncertainty(self, winner_margin: float) -> float:
        """
        Convert SAL top-1/top-2 probability gap into uncertainty.

        A wide margin means the winner is unambiguous, so uncertainty is low.
        A tiny margin means the top classes are close, so uncertainty is high.
        """
        return _clamp(1.0 - winner_margin / _CLEAR_WINNER_MARGIN)

    def sal_to_uncertainty(self, sal_state) -> float:
        """
        Prefer margin-derived uncertainty, falling back to entropy for older
        ArbitrationResult-like objects.
        """
        margin = getattr(sal_state, "winner_margin", None)
        if margin is not None:
            return self.margin_to_uncertainty(float(margin))
        return self.entropy_to_uncertainty(float(sal_state.entropy))

    def compute_adjustment(self, uncertainty: float) -> VisualAdjustment:
        """
        Compute degradation parameters from a normalised uncertainty value.

        Args:
            uncertainty: normalised uncertainty in [0, 1]

        Returns:
            VisualAdjustment with desaturation, brightness, noise, blur values.
        """
        # Effective scale: 0 at _UNCERTAIN_LOW, 1 at _UNCERTAIN_HIGH
        t = _clamp(
            (uncertainty - _UNCERTAIN_LOW) / (_UNCERTAIN_HIGH - _UNCERTAIN_LOW)
        )

        # Smooth step for more natural rolloff
        t_smooth = t * t * (3 - 2 * t)

        return VisualAdjustment(
            desaturation=0.55 * t_smooth,       # up to 55% grey at max uncertainty
            brightness_offset=-0.05 * t_smooth, # slight darkening
            noise_proxy=0.12 * t_smooth,        # conceptual noise hint
            blur_proxy=0.30 * t_smooth,         # conceptual blur hint
        )

    def apply(self, color: ColorVector, uncertainty: float) -> ColorVector:
        """
        Apply uncertainty-driven degradation to a color vector.

        Args:
            color:       input linear RGB
            uncertainty: normalised uncertainty [0, 1]

        Returns:
            Degraded ColorVector.
        """
        adj = self.compute_adjustment(uncertainty)
        c = _desaturate(color, adj.desaturation)
        c = _brightness_shift(c, adj.brightness_offset)
        return c

    def transition_blend(
        self,
        color_a: ColorVector,
        color_b: ColorVector,
        uncertainty: float,
    ) -> ColorVector:
        """
        Blend two colors for conflict / boundary zones.

        High uncertainty → equal blend (gradient transition).
        Low uncertainty  → color_a dominates.

        Args:
            color_a:     primary class color
            color_b:     secondary / neighbouring class color
            uncertainty: normalised uncertainty [0, 1]

        Returns:
            Blended ColorVector representing the transition gradient.
        """
        t = _clamp(uncertainty * 2.0)   # ramp up faster in conflict zones
        return (
            color_a[0] + (color_b[0] - color_a[0]) * t,
            color_a[1] + (color_b[1] - color_a[1]) * t,
            color_a[2] + (color_b[2] - color_a[2]) * t,
        )
