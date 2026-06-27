"""
Contract Layer — enforces the M0 → SAL → M1 → VC → D6 pipeline invariants.

Usage:
    from core.contract import ContractGuard
    guard = ContractGuard()
    guard.validate_sal(sal_result)
    guard.validate_m1(mask_tile)
    guard.validate_vc(vc_context)
    guard.validate_d6(rgb_frame)
"""

from .contract_guard import ContractGuard
from .sal_contract import SALContract, SALContractError
from .m1_contract import M1Contract, M1ContractError
from .vc_contract import VCContract, VCContractError
from .d6_contract import D6Contract, D6ContractError

__all__ = [
    "ContractGuard",
    "SALContract", "SALContractError",
    "M1Contract",  "M1ContractError",
    "VCContract",  "VCContractError",
    "D6Contract",  "D6ContractError",
]
