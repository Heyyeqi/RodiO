"""
Visual Consistency Engine

Top-level orchestrator for the VC Layer. Receives M1 SemanticMaskTile
objects, runs the full consistency pipeline, and returns a VCRenderContext
ready for D6 renderer consumption.

Pipeline:
  M1 SemanticMaskTile
       ↓ BiomeTransition.apply_transition()
       ↓ CoastlineSmoother.smooth()
       ↓ TemporalStabilizer.update_ema() (per field)
       ↓ uncertainty_modulation
       ↓
  VCRenderContext

No raster output, no GPU, no modification of M1 / SAL / D6 core logic.
"""

import numpy as np
from typing import Optional

from core.runtime import SpatialProfile
from core.m1 import M1Pipeline, TileBBox
from core.m1.mask_types import SemanticMaskTile
from core.binding import TemporalState
from .vc_types import VCRenderContext, BIOME_BASE_COLORS
from .biome_transition import BiomeTransition
from .coastline_smoother import CoastlineSmoother
from .temporal_stabilizer import TemporalStabilizer
from ._kernels import clamp, gaussian_blur


class VisualConsistencyEngine:
    """
    Stabilises M1 semantic masks into visually continuous D6 input contexts.

    Args:
        m1:             M1Pipeline instance (used when generating masks inline)
        sal:            SemanticArbitrator (optional; forwarded to M1Pipeline)
        biome_sigma:    base Gaussian σ for biome blending
        temporal_alpha: EMA α for temporal stabilisation (0=none, 1=frozen)
    """

    def __init__(
        self,
        m1: Optional[M1Pipeline] = None,
        sal=None,
        biome_sigma: float  = 1.0,
        temporal_alpha: float = 0.85,
        resolution_mode: Optional[str] = None,
    ):
        self._m1       = m1
        self._sal      = sal
        self._base_biome_sigma = biome_sigma
        self._base_coast_sigma = CoastlineSmoother().base_sigma
        self._base_coast_max_sigma = CoastlineSmoother().max_sigma
        self.resolution_mode = resolution_mode or getattr(m1, "resolution_mode", "8k")
        self._biome_tr = BiomeTransition(base_sigma=self._scaled_sigma(self._base_biome_sigma))
        self._smoother = CoastlineSmoother(
            base_sigma=self._scaled_sigma(self._base_coast_sigma),
            max_sigma=self._scaled_sigma(self._base_coast_max_sigma),
        )
        self._stabilizer = TemporalStabilizer(alpha=temporal_alpha)

    def set_resolution(self, mode: str) -> None:
        """Set VC resolution profile for future smoothing passes."""
        SpatialProfile().get_resolution(mode)
        self.resolution_mode = mode
        self._biome_tr = BiomeTransition(base_sigma=self._scaled_sigma(self._base_biome_sigma))
        self._smoother = CoastlineSmoother(
            base_sigma=self._scaled_sigma(self._base_coast_sigma),
            max_sigma=self._scaled_sigma(self._base_coast_max_sigma),
        )

    def resolution_scale(self) -> float:
        """Return horizontal scale relative to 8K."""
        return SpatialProfile().scale(self.resolution_mode)

    def pixel_density(self) -> float:
        """Return per-pixel world-size factor; higher resolution means smaller pixels."""
        return 1.0 / self.resolution_scale()

    def _scaled_sigma(self, sigma: float) -> float:
        return max(0.05, float(sigma) * self.pixel_density())

    # ------------------------------------------------------------------
    # Primary entry point
    # ------------------------------------------------------------------

    def process(
        self,
        m1_tile: SemanticMaskTile,
        sal_state=None,
        temporal_state: Optional[TemporalState] = None,
    ) -> VCRenderContext:
        """
        Run the full VC pipeline on one M1 tile.

        Args:
            m1_tile:       SemanticMaskTile from M1Pipeline.run_tile()
            sal_state:     ArbitrationResult (optional; unused currently but
                           reserved for future per-tile confidence override)
            temporal_state: TemporalState (currently unused in VC; reserved
                            for seasonal colour modulation pass)

        Returns:
            VCRenderContext with all five fields populated.
        """
        ctx = _VCContext(m1_tile)
        ctx = self._step_biome_transition(ctx)
        ctx = self._step_coastline_smooth(ctx)
        ctx = self._step_temporal_stabilize(ctx)
        ctx = self._step_uncertainty_modulation(ctx)
        return self._build_result(ctx, m1_tile)

    def apply_all(self, context: VCRenderContext) -> VCRenderContext:
        """
        Re-run all consistency passes on an already-built VCRenderContext.
        Useful for applying a second stabilization pass or post-processing.

        Returns a new VCRenderContext with fields re-processed.
        """
        # Rebuild a synthetic mask tile-like struct from the context
        # and re-apply the pipeline.  Currently applies temporal EMA only
        # (biome and coastline are already stable in a built context).
        temporal_stability = self._stabilizer.update_ema(
            "repass_coastline", context.coastline_gradient_field
        )
        base_color = self._stabilizer.update_ema(
            "repass_color", context.base_color_field
        )
        return VCRenderContext(
            base_color_field=base_color,
            biome_blend_field=context.biome_blend_field,
            coastline_gradient_field=context.coastline_gradient_field,
            temporal_stability_field=temporal_stability,
            uncertainty_modulation_field=context.uncertainty_modulation_field,
            bbox=context.bbox,
        )

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    def _step_biome_transition(self, ctx: "_VCContext") -> "_VCContext":
        color, blend = self._biome_tr.apply_transition(ctx.tile)
        ctx.color_field = color
        ctx.blend_field = blend
        return ctx

    def _step_coastline_smooth(self, ctx: "_VCContext") -> "_VCContext":
        ctx.coastline = self._smoother.smooth(
            ctx.tile.ocean_mask, ctx.tile.uncertainty_mask
        )
        return ctx

    def _step_temporal_stabilize(self, ctx: "_VCContext") -> "_VCContext":
        ctx.color_field, _       = self._stabilizer.update_ema_and_stability("color", ctx.color_field)
        ctx.coastline, ctx.stability = self._stabilizer.update_ema_and_stability("coastline", ctx.coastline)
        return ctx

    def _step_uncertainty_modulation(self, ctx: "_VCContext") -> "_VCContext":
        # Smooth the uncertainty mask for downstream use as a softness weight
        unc = ctx.tile.uncertainty_mask.astype(np.float32)
        ctx.unc_modulation = gaussian_blur(unc, sigma=0.8)
        return ctx

    def _build_result(self, ctx: "_VCContext", tile: SemanticMaskTile) -> VCRenderContext:
        return VCRenderContext(
            base_color_field=clamp(ctx.color_field),
            biome_blend_field=clamp(ctx.blend_field),
            coastline_gradient_field=clamp(ctx.coastline),
            temporal_stability_field=ctx.stability,
            uncertainty_modulation_field=clamp(ctx.unc_modulation),
            bbox=tile.bbox,
        )


class _VCContext:
    """Mutable intermediate state passed between pipeline steps."""

    def __init__(self, tile: SemanticMaskTile):
        self.tile = tile
        H, W = tile.shape
        self.color_field    = np.zeros((H, W, 3), dtype=np.float32)
        self.blend_field    = np.zeros((H, W),    dtype=np.float32)
        self.coastline      = np.zeros((H, W),    dtype=np.float32)
        self.unc_modulation = np.zeros((H, W),    dtype=np.float32)
        # Populated by temporal step (EMA delta → stability)
        self.stability      = np.ones((H, W),     dtype=np.float32)
