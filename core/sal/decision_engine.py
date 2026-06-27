"""
Decision Engine — arbitration core that converts probability maps into
final decisions and detects inter-source conflicts.
"""

import math
from typing import Dict, List, Tuple

from .sal_types import SemanticSignal, SEMANTIC_CLASSES


# Conflict is declared when no single class holds more than this fraction of
# the total signal mass (before normalisation).
CONFLICT_THRESHOLD = 0.55


class DecisionEngine:
    """
    Converts a probability distribution into a final class + entropy score,
    and detects meaningful disagreement between source signals.
    """

    def decide(self, probability_map: Dict[str, float]) -> Tuple[str, float, float]:
        """
        Select the winning class and compute Shannon entropy.

        Args:
            probability_map: output of ConfidenceModel.compute_confidence()

        Returns:
            (final_class, confidence_score, entropy)
            - final_class:      argmax of the distribution
            - confidence_score: probability of the winning class
            - entropy:          Shannon entropy in bits (lower = more certain)
        """
        final_class = max(probability_map, key=lambda k: probability_map[k])
        confidence_score = probability_map[final_class]
        entropy = self._shannon_entropy(probability_map)
        return final_class, confidence_score, entropy

    def rank(self, probability_map: Dict[str, float]) -> Tuple[str, str, float]:
        """
        Return the top-1 class, top-2 class, and their probability margin.

        The margin is the downstream-friendly certainty signal: high margin
        means the winner is clearly separated from the runner-up even when
        absolute softmax probabilities are diluted across many classes.
        """
        ranked = sorted(probability_map.items(), key=lambda item: item[1], reverse=True)
        if not ranked:
            return "unknown", "unknown", 0.0
        winner_class, winner_prob = ranked[0]
        if len(ranked) == 1:
            return winner_class, "unknown", winner_prob
        runner_up_class, runner_up_prob = ranked[1]
        return winner_class, runner_up_class, max(0.0, winner_prob - runner_up_prob)

    def detect_conflict(self, signals: List[SemanticSignal]) -> bool:
        """
        Return True when source signals disagree significantly.

        Conflict is detected when the most-voted class captures less than
        CONFLICT_THRESHOLD of the total weighted vote mass, meaning
        meaningful dissent exists from at least one source.

        Args:
            signals: registered SemanticSignal objects

        Returns:
            True if conflict exists, False if signals largely agree.
        """
        if not signals:
            return False

        # Tally raw weighted votes per class
        votes: Dict[str, float] = {}
        total_weight = 0.0
        for sig in signals:
            votes[sig.inferred_class] = votes.get(sig.inferred_class, 0.0) + sig.weight
            total_weight += sig.weight

        if total_weight == 0.0:
            return False

        top_share = max(votes.values()) / total_weight
        return top_share < CONFLICT_THRESHOLD

    def _shannon_entropy(self, prob_map: Dict[str, float]) -> float:
        """Shannon entropy in bits."""
        entropy = 0.0
        for p in prob_map.values():
            if p > 0:
                entropy -= p * math.log2(p)
        return entropy
