"""
Confidence Model — computes probability distributions over semantic classes.

Each source signal votes for its inferred class. Votes are weighted by the
signal's priority weight and raw confidence, then softmax-normalised to
produce a probability distribution.
"""

import math
from typing import Dict, List

from .sal_types import SemanticSignal, SEMANTIC_CLASSES


class ConfidenceModel:
    """
    Probabilistic fusion of multi-source semantic signals.

    Design notes
    ------------
    - Each signal contributes `weight * raw_confidence` mass to its class.
    - A small uniform prior (epsilon) prevents zero-probability classes.
    - Softmax with temperature T=1 is applied to produce final probabilities.
    """

    EPSILON = 1e-6   # uniform floor to avoid zero-prob classes
    TEMPERATURE = 1.0

    def compute_confidence(self, signals: List[SemanticSignal]) -> Dict[str, float]:
        """
        Fuse multi-source signals into a probability distribution.

        Args:
            signals: list of SemanticSignal objects

        Returns:
            Dict mapping each semantic class to its probability (sums to 1).
        """
        # Accumulate weighted votes per class
        raw_scores: Dict[str, float] = {cls: self.EPSILON for cls in SEMANTIC_CLASSES}

        for sig in signals:
            vote = sig.weight * sig.raw_confidence
            raw_scores[sig.inferred_class] = raw_scores[sig.inferred_class] + vote

        return self.normalize(raw_scores)

    def normalize(self, raw_scores: Dict[str, float]) -> Dict[str, float]:
        """
        Softmax normalisation over the raw score dict.

        Returns a valid probability distribution (values sum to 1).
        """
        values = list(raw_scores.values())
        keys = list(raw_scores.keys())

        # Numerically stable softmax: shift by max
        max_val = max(values)
        exp_vals = [math.exp((v - max_val) / self.TEMPERATURE) for v in values]
        total = sum(exp_vals)

        return {k: exp_vals[i] / total for i, k in enumerate(keys)}
