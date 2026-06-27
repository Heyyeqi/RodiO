"""
VC Contract

Validates VCRenderContext structs produced by the Visual Consistency Layer.

Invariants enforced:
  - Required fields present: biome_blend_field, coastline_gradient_field,
    temporal_stability_field, uncertainty_modulation_field
  - coastline_gradient_field must be a gradient field (not binary mask):
    must contain values strictly between 0 and 1
  - temporal_stability_field values in [0, 1]
  - All fields have consistent shapes
  - VC must not expose references to SAL / M0 / M1 internals
"""

import numpy as np


class VCContractError(Exception):
    pass


class VCContract:
    """Validates VCRenderContext objects produced by VisualConsistencyEngine."""

    REQUIRED_FIELDS = (
        "biome_blend_field",
        "coastline_gradient_field",
        "temporal_stability_field",
        "uncertainty_modulation_field",
        "base_color_field",
    )

    def validate(self, context) -> None:
        """
        Raise VCContractError if context violates any VC contract invariant.
        """
        if context is None:
            raise VCContractError("VCRenderContext is None")

        self._validate_fields_present(context)
        self._validate_shapes_consistent(context)
        self._validate_coastline_is_gradient(context)
        self._validate_temporal_stability(context)
        self._validate_no_forbidden_attributes(context)

    # ------------------------------------------------------------------
    # Structural checks
    # ------------------------------------------------------------------

    def _validate_fields_present(self, ctx) -> None:
        for field in self.REQUIRED_FIELDS:
            if not hasattr(ctx, field):
                raise VCContractError(f"VCRenderContext missing field: {field!r}")
            val = getattr(ctx, field)
            if val is None:
                raise VCContractError(f"VCRenderContext.{field} is None")
            if not isinstance(val, np.ndarray):
                raise VCContractError(
                    f"VCRenderContext.{field} must be np.ndarray, got {type(val).__name__}"
                )

    def _validate_shapes_consistent(self, ctx) -> None:
        scalar_fields = [f for f in self.REQUIRED_FIELDS if f != "base_color_field"]
        shapes = {f: getattr(ctx, f).shape for f in scalar_fields}
        unique = set(shapes.values())
        if len(unique) != 1:
            raise VCContractError(
                f"VCRenderContext 2D field shapes are inconsistent: {shapes}"
            )
        H, W = next(iter(unique))
        color_shape = ctx.base_color_field.shape
        if color_shape != (H, W, 3):
            raise VCContractError(
                f"base_color_field shape {color_shape} does not match (H={H}, W={W}, 3)"
            )

    def _validate_coastline_is_gradient(self, ctx) -> None:
        """Coastline field must contain gradient values, not a binary 0/1 mask."""
        grad = ctx.coastline_gradient_field.astype(np.float32)
        if grad.min() < -1e-4 or grad.max() > 1.0 + 1e-4:
            raise VCContractError(
                f"coastline_gradient_field out of [0, 1]: "
                f"min={grad.min():.4f} max={grad.max():.4f}"
            )
        # At least some values must be non-trivially between 0 and 1 OR
        # the tile is entirely ocean or entirely land (acceptable edge case).
        lo, hi = float(grad.min()), float(grad.max())
        span = hi - lo
        if span > 0.05:
            mid = grad[(grad > 0.05) & (grad < 0.95)]
            if len(mid) == 0:
                raise VCContractError(
                    "coastline_gradient_field has range but no transition values; "
                    "binary mask detected — gradient field required"
                )

    def _validate_temporal_stability(self, ctx) -> None:
        stab = ctx.temporal_stability_field.astype(np.float32)
        if stab.min() < -1e-4 or stab.max() > 1.0 + 1e-4:
            raise VCContractError(
                f"temporal_stability_field out of [0, 1]: "
                f"min={stab.min():.4f} max={stab.max():.4f}"
            )

    def _validate_no_forbidden_attributes(self, ctx) -> None:
        """VC context must not carry references to SAL/M0 internals."""
        forbidden = ("sal_result", "arbitration_result", "m0_state", "spatial_state", "runtime")
        for attr in forbidden:
            if hasattr(ctx, attr) and getattr(ctx, attr) is not None:
                raise VCContractError(
                    f"VCRenderContext carries forbidden attribute {attr!r}; "
                    "VC must not expose SAL/M0 internals to D6"
                )
