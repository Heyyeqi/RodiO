"""
D6 Contract

Enforces the rule that D6 rendering only accepts VCRenderContext as input
and only produces RGB frames as output.

Invariants enforced:
  - Input must be VCRenderContext — no M1 / SAL / M0 / SpatialState accepted
  - Output must be uint8 ndarray of shape (H, W, 3)
  - render_from_vc() is the only permitted D6 entry point in the contract path
"""

import numpy as np


class D6ContractError(Exception):
    pass


class D6Contract:
    """
    Validates D6 rendering I/O and provides the contract-compliant render
    entry point that accepts only VCRenderContext.
    """

    # Types that are explicitly forbidden as D6 input
    _FORBIDDEN_INPUT_TYPES = (
        "SemanticMaskTile",    # M1
        "ArbitrationResult",   # SAL
        "SpatialState",        # M0
        "D6RenderInput",       # binding layer (SAL→D6 bridge)
    )

    def validate_input(self, inp) -> None:
        """
        Raise D6ContractError if inp is not a VCRenderContext.
        D6 must only accept VC output — no M1 / SAL / M0 access allowed.
        """
        if inp is None:
            raise D6ContractError("D6 render input is None")

        type_name = type(inp).__name__
        if type_name in self._FORBIDDEN_INPUT_TYPES:
            raise D6ContractError(
                f"D6 received forbidden input type {type_name!r}; "
                "D6 must only consume VCRenderContext"
            )
        if type_name != "VCRenderContext":
            raise D6ContractError(
                f"D6 input must be VCRenderContext, got {type_name!r}"
            )

        # Verify the required VC fields are present
        required = (
            "base_color_field",
            "coastline_gradient_field",
            "temporal_stability_field",
            "uncertainty_modulation_field",
            "biome_blend_field",
        )
        for field in required:
            if not hasattr(inp, field) or getattr(inp, field) is None:
                raise D6ContractError(
                    f"VCRenderContext passed to D6 is missing field {field!r}"
                )

    def validate_output(self, out) -> None:
        """
        Raise D6ContractError if out is not a valid RGB frame.
        """
        if out is None:
            raise D6ContractError("D6 render output is None")
        if not isinstance(out, np.ndarray):
            raise D6ContractError(
                f"D6 output must be np.ndarray, got {type(out).__name__}"
            )
        if out.ndim != 3 or out.shape[2] != 3:
            raise D6ContractError(
                f"D6 output must be shape (H, W, 3), got {out.shape}"
            )
        if out.dtype != np.uint8:
            raise D6ContractError(
                f"D6 output dtype must be uint8, got {out.dtype}"
            )

    def render_from_vc(self, vc_context) -> np.ndarray:
        """
        Contract-compliant D6 render: VCRenderContext → uint8 RGB frame.

        Extracts the stabilised base_color_field from the VC context and
        applies temporal stability weighting. No SAL / M1 / M0 access.

        Returns:
            uint8 (H, W, 3) RGB array.
        """
        self.validate_input(vc_context)

        color = vc_context.base_color_field.astype(np.float32)          # (H, W, 3)
        stability = vc_context.temporal_stability_field[..., np.newaxis] # (H, W, 1)
        uncertainty = vc_context.uncertainty_modulation_field[..., np.newaxis]

        # Stability-weighted blend: stable regions render at full color;
        # unstable/uncertain regions are pulled toward a neutral grey.
        neutral = np.full_like(color, 0.5)
        blend_weight = np.clip(stability * (1.0 - uncertainty * 0.3), 0.0, 1.0)
        blended = color * blend_weight + neutral * (1.0 - blend_weight)

        rgb_u8 = (np.clip(blended, 0.0, 1.0) * 255.0).astype(np.uint8)
        self.validate_output(rgb_u8)
        return rgb_u8
