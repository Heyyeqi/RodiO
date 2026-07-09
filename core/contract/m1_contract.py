"""
M1 Contract

Validates SemanticMaskTile structs produced by the M1 mask generation layer.

Invariants enforced:
  - All four mask arrays present: ocean_mask, land_mask, biome_mask, uncertainty_mask
  - All shapes consistent (same H×W)
  - No NaN or Inf in float arrays
  - uncertainty_mask values in [0, 1]
  - SAL per-pixel double-call is prohibited (enforced at ContractGuard level)
"""

import numpy as np


class M1ContractError(Exception):
    pass


class M1Contract:
    """Validates SemanticMaskTile objects produced by MaskGenerator."""

    REQUIRED_ARRAYS = ("ocean_mask", "land_mask", "biome_mask", "uncertainty_mask")

    def validate(self, tile) -> None:
        """
        Raise M1ContractError if tile violates any M1 contract invariant.
        """
        if tile is None:
            raise M1ContractError("SemanticMaskTile is None")

        self._validate_fields_present(tile)
        self._validate_shapes_consistent(tile)
        self._validate_uncertainty(tile)
        self._validate_no_nan(tile)

    # ------------------------------------------------------------------
    # Structural checks
    # ------------------------------------------------------------------

    def _validate_fields_present(self, tile) -> None:
        for field in self.REQUIRED_ARRAYS:
            if not hasattr(tile, field):
                raise M1ContractError(f"SemanticMaskTile missing field: {field!r}")
            arr = getattr(tile, field)
            if arr is None:
                raise M1ContractError(f"SemanticMaskTile.{field} is None")
            if not isinstance(arr, np.ndarray):
                raise M1ContractError(
                    f"SemanticMaskTile.{field} must be np.ndarray, got {type(arr).__name__}"
                )
            if arr.ndim != 2:
                raise M1ContractError(
                    f"SemanticMaskTile.{field} must be 2D, got shape {arr.shape}"
                )

    def _validate_shapes_consistent(self, tile) -> None:
        shapes = {field: getattr(tile, field).shape for field in self.REQUIRED_ARRAYS}
        unique = set(shapes.values())
        if len(unique) != 1:
            raise M1ContractError(
                f"SemanticMaskTile array shapes are inconsistent: {shapes}"
            )

    def _validate_uncertainty(self, tile) -> None:
        unc = tile.uncertainty_mask.astype(np.float32)
        if unc.min() < -1e-6 or unc.max() > 1.0 + 1e-6:
            raise M1ContractError(
                f"uncertainty_mask values out of [0, 1]: "
                f"min={unc.min():.4f} max={unc.max():.4f}"
            )

    def _validate_no_nan(self, tile) -> None:
        for field in ("uncertainty_mask", "confidence_mask", "ocean_prob_mask"):
            if hasattr(tile, field):
                arr = getattr(tile, field).astype(np.float32)
                if np.any(~np.isfinite(arr)):
                    raise M1ContractError(
                        f"SemanticMaskTile.{field} contains NaN or Inf"
                    )
