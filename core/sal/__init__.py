"""
core/sal — Semantic Arbitration Layer (SAL)

Public surface:
    SemanticArbitrator  — main entry point
    ArbitrationResult   — typed output
"""

from .semantic_arbitrator import SemanticArbitrator
from .sal_types import ArbitrationResult, SEMANTIC_CLASSES, DEFAULT_WEIGHTS

__all__ = ["SemanticArbitrator", "ArbitrationResult", "SEMANTIC_CLASSES", "DEFAULT_WEIGHTS"]
