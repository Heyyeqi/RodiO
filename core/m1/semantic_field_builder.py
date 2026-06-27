"""
Semantic Field Builder

Converts a SAL ArbitrationResult + D6RenderInput pair into a structured
set of scalar field tensors (elevation_field, ocean_field, climate_field,
uncertainty_field) that can be accumulated across a tile grid.

All operations are in-memory numpy. No files, no GPU, no rendering.
"""

from typing import Optional, Dict, Any
import numpy as np

from .mask_types import SEMANTIC_TO_BIOME, BIOME_UNKNOWN


class SemanticFieldBuilder:
    """
    Converts a (sal_state, d6_input) pair into a set of scalar fields.

    Usage:
        builder = SemanticFieldBuilder()
        builder.ingest(sal_result, d6_input)
        fields = builder.compute_fields()
    """

    def __init__(self):
        self._sal_state = None
        self._d6_input  = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, sal_state, d6_input) -> Dict[str, float]:
        """
        Convert a (sal_state, d6_input) pair into a flat scalar field dict.

        Args:
            sal_state: ArbitrationResult from SemanticArbitrator
            d6_input:  D6RenderInput from SALD6Bridge / RenderingContextBuilder

        Returns:
            Dict with keys: elevation_field, ocean_field, climate_field,
                            uncertainty_field, biome_code, confidence
        """
        self._sal_state = sal_state
        self._d6_input  = d6_input
        return self.compute_fields()

    def compute_fields(self) -> Dict[str, float]:
        """
        Compute scalar field values from the currently ingested state.

        Returns:
            elevation_field:  SAL probability_map["ocean"] as a proxy for
                              "how ocean-like" — higher = more submerged
            ocean_field:      normalised ocean probability [0, 1]
            climate_field:    land-class probability (complement to ocean)
            uncertainty_field: D6/SAL winner-margin uncertainty [0, 1]
            biome_code:       integer biome code (see SEMANTIC_TO_BIOME)
            confidence:       SAL max class probability
        """
        s = self._sal_state
        d = self._d6_input

        # Elevation field: proxy from ocean probability
        ocean_prob   = s.probability_map.get("ocean", 0.0)
        land_prob    = s.probability_map.get("land", 0.0)
        climate_prob = max(land_prob, s.probability_map.get("forest", 0.0),
                           s.probability_map.get("desert", 0.0))

        # Uncertainty from D6 binding. Binding prefers SAL winner_margin and
        # falls back to entropy only for old ArbitrationResult-like objects.
        uncertainty  = d.uncertainty

        # Biome from D6 (which may have biome-refined class via climate zone)
        biome_code   = SEMANTIC_TO_BIOME.get(s.final_class, BIOME_UNKNOWN)

        return {
            "elevation_field":  ocean_prob,
            "ocean_field":      ocean_prob,
            "climate_field":    climate_prob,
            "uncertainty_field": uncertainty,
            "biome_code":       float(biome_code),
            "confidence":       s.confidence_score,
        }

    def fields_to_point_masks(self, fields: Dict[str, float]) -> Dict[str, Any]:
        """
        Convert scalar fields to per-point binary mask values.

        Args:
            fields: output of compute_fields()

        Returns:
            Dict with boolean / uint8 values for mask arrays:
                ocean_mask, land_mask, biome_code, uncertainty, confidence
        """
        sal = self._sal_state
        final = sal.final_class

        ocean_mask = final == "ocean"
        land_mask  = final in ("land", "desert", "forest", "wetland", "urban", "ice")

        return {
            "ocean_mask":       ocean_mask,
            "land_mask":        land_mask,
            "biome_code":       int(fields["biome_code"]),
            "uncertainty":      float(fields["uncertainty_field"]),
            "confidence":       float(fields["confidence"]),
            "ocean_prob":       float(fields["ocean_field"]),
        }
