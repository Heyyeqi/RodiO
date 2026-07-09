"""
Temporal Stabilizer

Prevents frame-to-frame visual discontinuities in D6 rendering by applying
exponential moving average (EMA) blending between consecutive VC contexts.

Key invariants:
  - frame_t+1 ≈ frame_t when the underlying semantic state barely changes
  - Sudden semantic flips (e.g. new SAL signal) are damped, not hidden
  - The stability_field surfaces how much each pixel changed, for downstream use

No GPU, no raster I/O, pure numpy CPU.
"""

import numpy as np
from typing import Optional, Tuple

from ._kernels import gaussian_blur, clamp


class TemporalStabilizer:
    """
    Blends VC field arrays across time using EMA.

    Args:
        alpha:         EMA smoothing factor (0=no history, 1=frozen).
                       Default 0.85: strong continuity, adapts within ~7 frames.
        change_sigma:  Gaussian σ (px) applied to per-pixel delta before
                       the stability field is computed.  Spreads rapid-change
                       regions slightly to avoid single-pixel flickers.
        change_threshold: normalised delta below which pixels are considered
                          "stable" for the stability field.
    """

    def __init__(
        self,
        alpha: float = 0.85,
        change_sigma: float = 0.8,
        change_threshold: float = 0.02,
    ):
        self.alpha = alpha
        self.change_sigma = change_sigma
        self.change_threshold = change_threshold

        # Internal EMA state — keyed by field name
        self._ema: dict = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def stabilize_frame(
        self,
        frame_t: np.ndarray,
        frame_t1: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply EMA blending between two consecutive field arrays.

        Args:
            frame_t:  current raw field from VC pipeline  (H, W) or (H, W, 3)
            frame_t1: previous stabilised field            same shape

        Returns:
            stabilised: EMA-blended output  (same shape as inputs)
            stability:  float32 (H, W) stability map, 1=no change, 0=full change
        """
        stabilised = self.alpha * frame_t1 + (1.0 - self.alpha) * frame_t

        # Per-pixel delta (take max across channels for RGB arrays)
        delta = np.abs(frame_t.astype(float) - frame_t1.astype(float))
        if delta.ndim == 3:
            delta = delta.max(axis=2)

        stability = self._delta_to_stability(delta)
        return stabilised.astype(np.float32), stability.astype(np.float32)

    def damp_transition(self, delta: np.ndarray) -> np.ndarray:
        """
        Apply smooth damping to a change-magnitude array.

        Uses a sigmoid-like function so small deltas are heavily suppressed
        (near-zero stability change) while large deltas are only partially
        reduced (not hidden, just smoothed).

        Args:
            delta: float array of per-pixel change magnitudes (≥ 0)

        Returns:
            damped: same shape, values in [0, 1], smaller = more damped
        """
        # Tanh damping: saturates at 1 for large deltas, near 0 for small
        k = 8.0  # steepness
        return np.tanh(k * delta).astype(np.float32)

    def update_ema_and_stability(
        self, key: str, field: np.ndarray
    ) -> "Tuple[np.ndarray, np.ndarray]":
        """
        Stateful EMA update that also returns a per-pixel stability field.

        Stability = how much the new raw field differs from the previous EMA.
        First call returns perfect stability (no history to compare).

        Returns:
            (ema_field, stability_field)  — both same spatial shape as field.
        """
        H = field.shape[0]
        W = field.shape[1]

        if key not in self._ema:
            self._ema[key] = field.astype(np.float32)
            return field.astype(np.float32), np.ones((H, W), dtype=np.float32)

        prev = self._ema[key]
        if prev.shape != field.shape:
            self._ema[key] = field.astype(np.float32)
            return field.astype(np.float32), np.ones((H, W), dtype=np.float32)

        # Delta: raw input vs previous EMA state
        delta = np.abs(field.astype(float) - prev.astype(float))
        if delta.ndim == 3:
            delta = delta.max(axis=2)

        stability = self._delta_to_stability(delta.astype(np.float32))

        ema = self.alpha * prev + (1.0 - self.alpha) * field.astype(np.float32)
        self._ema[key] = ema
        return ema, stability

    def update_ema(self, key: str, field: np.ndarray) -> np.ndarray:
        """
        Stateful EMA update for a named field.

        On first call, initialises with the given field (no blending).
        Subsequent calls blend with the stored history.

        Args:
            key:   string identifier (e.g. "coastline", "biome_blend")
            field: current raw field

        Returns:
            EMA-smoothed field.
        """
        if key not in self._ema:
            self._ema[key] = field.astype(np.float32)
            return field.astype(np.float32)

        prev = self._ema[key]
        if prev.shape != field.shape:
            # Resolution changed — restart
            self._ema[key] = field.astype(np.float32)
            return field.astype(np.float32)

        ema = self.alpha * prev + (1.0 - self.alpha) * field.astype(np.float32)
        self._ema[key] = ema
        return ema

    def reset(self) -> None:
        """Clear all stored EMA state (call when switching locations/tiles)."""
        self._ema.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _delta_to_stability(self, delta: np.ndarray) -> np.ndarray:
        """
        Convert a per-pixel change magnitude to a stability score in [0, 1].
        Pixels with delta < change_threshold → stability ≈ 1 (stable).
        Large delta → stability approaches 0 (changed).
        """
        # Blur the delta slightly to avoid isolated-pixel flickers
        if self.change_sigma > 0:
            delta = gaussian_blur(delta.astype(np.float32), self.change_sigma)

        # Normalise: below threshold → 1.0, linearly decay above
        stability = clamp(1.0 - delta / max(self.change_threshold * 5.0, 1e-6))
        return stability
