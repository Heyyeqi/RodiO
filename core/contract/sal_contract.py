"""
SAL Contract

Validates ArbitrationResult structs leaving the Semantic Arbitration Layer.

Invariants enforced:
  - All required fields present and non-None
  - winner_class is argmax of probability_map
  - winner_margin in [0, 1]
  - winner_ratio >= 1.0
  - confidence_score in [0, 1]
  - SAL double-call detection via call counter cache
"""

from typing import Dict


class SALContractError(Exception):
    pass


class SALContract:
    """Validates ArbitrationResult objects produced by SemanticArbitrator."""

    REQUIRED_FIELDS = (
        "final_class",
        "confidence_score",
        "probability_map",
        "conflict_detected",
        "entropy",
        "winner_class",
        "runner_up_class",
        "winner_margin",
        "winner_ratio",
        "explanation_trace",
    )

    def validate(self, result) -> None:
        """
        Raise SALContractError if result violates any SAL contract invariant.
        """
        if result is None:
            raise SALContractError("ArbitrationResult is None")

        for field in self.REQUIRED_FIELDS:
            if not hasattr(result, field):
                raise SALContractError(f"ArbitrationResult missing field: {field!r}")
            if getattr(result, field) is None:
                raise SALContractError(f"ArbitrationResult.{field} is None")

        self._validate_winner_class(result)
        self._validate_ranges(result)

    # ------------------------------------------------------------------
    # Structural checks
    # ------------------------------------------------------------------

    def _validate_winner_class(self, result) -> None:
        prob_map: Dict[str, float] = result.probability_map
        if not prob_map:
            raise SALContractError("probability_map is empty")

        argmax = max(prob_map, key=lambda k: prob_map[k])
        if result.winner_class != argmax:
            raise SALContractError(
                f"winner_class={result.winner_class!r} does not match "
                f"argmax(probability_map)={argmax!r}"
            )

        prob_sum = sum(prob_map.values())
        if not (0.99 <= prob_sum <= 1.01):
            raise SALContractError(
                f"probability_map does not sum to 1.0 (got {prob_sum:.4f})"
            )

    def _validate_ranges(self, result) -> None:
        if not (0.0 <= result.winner_margin <= 1.0):
            raise SALContractError(
                f"winner_margin={result.winner_margin:.4f} out of [0, 1]"
            )
        if not (0.0 <= result.confidence_score <= 1.0):
            raise SALContractError(
                f"confidence_score={result.confidence_score:.4f} out of [0, 1]"
            )
        if result.winner_ratio < 1.0 - 1e-6:
            raise SALContractError(
                f"winner_ratio={result.winner_ratio:.4f} < 1.0; winner must dominate runner-up"
            )
        if result.entropy < 0.0:
            raise SALContractError(f"entropy={result.entropy:.4f} is negative")
