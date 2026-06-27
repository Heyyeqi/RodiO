"""
Signal Registry — unified input layer for SAL.

Collects semantic signals from multiple sources and exposes them as a
structured, weighted set for the arbitration pipeline.
"""

from typing import Dict, List, Optional
from .sal_types import SemanticSignal, DEFAULT_WEIGHTS, SEMANTIC_CLASSES


class SignalRegistry:
    """Stateful collector of per-point semantic signals."""

    def __init__(self):
        self._signals: Dict[str, SemanticSignal] = {}

    def register(
        self,
        name: str,
        value: str,
        weight: Optional[float] = None,
        raw_confidence: float = 1.0,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Store a semantic signal.

        Args:
            name:           signal source key (e.g. "dem", "climate")
            value:          inferred semantic class
            weight:         priority weight; defaults to DEFAULT_WEIGHTS[name]
            raw_confidence: source-layer confidence for the inferred class
            metadata:       optional passthrough dict
        """
        if value not in SEMANTIC_CLASSES:
            raise ValueError(f"Unknown semantic class '{value}'. Valid: {SEMANTIC_CLASSES}")

        resolved_weight = weight if weight is not None else DEFAULT_WEIGHTS.get(name, 0.1)

        self._signals[name] = SemanticSignal(
            source=name,
            inferred_class=value,
            raw_confidence=max(0.0, min(1.0, raw_confidence)),
            weight=resolved_weight,
            metadata=metadata or {},
        )

    def get_all(self) -> List[SemanticSignal]:
        """Return all registered signals as a list."""
        return list(self._signals.values())

    def get(self, name: str) -> Optional[SemanticSignal]:
        return self._signals.get(name)

    def clear(self) -> None:
        self._signals.clear()

    def __repr__(self) -> str:
        entries = ", ".join(
            f"{s.source}={s.inferred_class}({s.raw_confidence:.2f})"
            for s in self._signals.values()
        )
        return f"SignalRegistry([{entries}])"
