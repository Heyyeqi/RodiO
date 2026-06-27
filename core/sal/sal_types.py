"""
SAL Types — shared data structures for the Semantic Arbitration Layer.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List


# Canonical semantic classes output by SAL
SEMANTIC_CLASSES = [
    "ocean",
    "land",
    "ice",
    "shallow_water",
    "wetland",
    "desert",
    "forest",
    "urban",
    "unknown",
]

# Source signal names
SIGNAL_DEM = "dem"
SIGNAL_CLIMATE = "climate"
SIGNAL_OCEAN = "ocean"
SIGNAL_LANDCOVER = "landcover"

# Default priority weights (sum to 1.0)
DEFAULT_WEIGHTS: Dict[str, float] = {
    SIGNAL_DEM: 0.35,
    SIGNAL_CLIMATE: 0.30,
    SIGNAL_OCEAN: 0.20,
    SIGNAL_LANDCOVER: 0.15,
}


@dataclass
class SemanticSignal:
    """A single source signal with its inferred class and confidence."""
    source: str                        # e.g. "dem", "climate"
    inferred_class: str                # one of SEMANTIC_CLASSES
    raw_confidence: float              # 0.0–1.0, from the source layer
    weight: float = 1.0               # priority weight
    metadata: Dict = field(default_factory=dict)


@dataclass
class ArbitrationResult:
    """Output of a single SAL resolve() call."""
    final_class: str
    confidence_score: float            # max of the probability distribution
    probability_map: Dict[str, float]  # full distribution over SEMANTIC_CLASSES
    conflict_detected: bool
    entropy: float
    winner_class: str                  # top-1 class in probability_map
    runner_up_class: str               # top-2 class in probability_map
    winner_margin: float               # top-1 probability minus top-2 probability
    winner_ratio: float                # top-1 probability / top-2 probability (≥1.0)
    explanation_trace: List[str]       # human-readable reasoning steps
