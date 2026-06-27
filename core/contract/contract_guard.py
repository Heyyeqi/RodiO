"""
Contract Guard — unified validation entry point for the M0 → SAL → M1 → VC → D6 pipeline.

Enforces:
  1. All per-layer structural contracts (SAL / M1 / VC / D6)
  2. SAL double-call detection: the same input key must not be re-resolved
     (callers must cache and reuse ArbitrationResult)
  3. VC isolation: VC context must not carry SAL / M0 / M1 references

Usage:
    guard = ContractGuard()
    guard.validate_sal(sal_result)        # after SemanticArbitrator.resolve()
    guard.validate_m1(mask_tile)          # after M1Pipeline.run_tile()
    guard.validate_vc(vc_context)         # after VisualConsistencyEngine.process()
    guard.validate_d6(rgb_frame)          # after D6Contract.render_from_vc()
"""

from typing import Any, Optional

from .sal_contract import SALContract, SALContractError
from .m1_contract  import M1Contract,  M1ContractError
from .vc_contract  import VCContract,  VCContractError
from .d6_contract  import D6Contract,  D6ContractError


class ContractViolation(Exception):
    """Raised by ContractGuard when any layer contract is violated."""


class ContractGuard:
    """
    Unified guard that validates data structures at each pipeline stage.

    Thread-safety: each instance maintains its own SAL call cache; do not
    share a single ContractGuard across threads without external locking.
    """

    def __init__(self, strict_sal_cache: bool = True):
        """
        Args:
            strict_sal_cache: when True, raise ContractViolation if the same
                              SAL input key is resolved more than once per
                              guard instance (enforces result reuse).
        """
        self._sal_contract = SALContract()
        self._m1_contract  = M1Contract()
        self._vc_contract  = VCContract()
        self._d6_contract  = D6Contract()

        self._strict_sal_cache = strict_sal_cache
        # Maps frozenset-of-signal-kwargs → ArbitrationResult for double-call detection
        self._sal_cache: dict = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_sal(self, result, input_key: Optional[Any] = None) -> None:
        """
        Validate an ArbitrationResult from SemanticArbitrator.

        Args:
            result:    ArbitrationResult to validate
            input_key: hashable key identifying the call site (e.g. (lon, lat))
                       used for double-call detection; skip check if None
        """
        try:
            self._sal_contract.validate(result)
        except SALContractError as e:
            raise ContractViolation(f"[SAL] {e}") from e

        if self._strict_sal_cache and input_key is not None:
            if input_key in self._sal_cache:
                raise ContractViolation(
                    f"[SAL] Double-call detected for key {input_key!r}. "
                    "SAL must be called once per point; reuse the cached result."
                )
            self._sal_cache[input_key] = result

    def validate_m1(self, mask_tile) -> None:
        """Validate a SemanticMaskTile from M1Pipeline."""
        try:
            self._m1_contract.validate(mask_tile)
        except M1ContractError as e:
            raise ContractViolation(f"[M1] {e}") from e

    def validate_vc(self, context) -> None:
        """
        Validate a VCRenderContext from VisualConsistencyEngine.

        Also enforces the VC isolation rule: VC output must not carry
        references to SAL / M0 layers (checked inside VCContract).
        """
        try:
            self._vc_contract.validate(context)
        except VCContractError as e:
            raise ContractViolation(f"[VC] {e}") from e

    def validate_d6(self, rgb_frame) -> None:
        """Validate a uint8 RGB frame produced by D6Contract.render_from_vc()."""
        try:
            self._d6_contract.validate_output(rgb_frame)
        except D6ContractError as e:
            raise ContractViolation(f"[D6] {e}") from e

    def render_d6_from_vc(self, vc_context):
        """
        Contract-enforced D6 render entry point.

        Validates input, renders, validates output, returns RGB frame.
        D6 is prohibited from accessing anything other than vc_context.
        """
        try:
            self._d6_contract.validate_input(vc_context)
        except D6ContractError as e:
            raise ContractViolation(f"[D6 input] {e}") from e

        rgb_frame = self._d6_contract.render_from_vc(vc_context)
        self.validate_d6(rgb_frame)
        return rgb_frame

    def reset_sal_cache(self) -> None:
        """Clear the SAL call cache (e.g. between tiles or test runs)."""
        self._sal_cache.clear()
