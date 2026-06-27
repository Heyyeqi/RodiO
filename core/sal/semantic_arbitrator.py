"""
Semantic Arbitrator — top-level SAL entry point.

Accepts four source signals (DEM, Climate, Ocean, Landcover), runs them
through the confidence model and decision engine, and returns a single
stable semantic decision with a full explanation trace.
"""

from typing import Optional, List

from .sal_types import (
    ArbitrationResult,
    SemanticSignal,
    SIGNAL_DEM,
    SIGNAL_CLIMATE,
    SIGNAL_OCEAN,
    SIGNAL_LANDCOVER,
    DEFAULT_WEIGHTS,
    SEMANTIC_CLASSES,
)
from .signal_registry import SignalRegistry
from .confidence_model import ConfidenceModel
from .decision_engine import DecisionEngine


class SemanticArbitrator:
    """
    Fuses DEM / Climate / Ocean / Landcover signals into a single,
    confidence-weighted semantic class for one geographic point.

    Priority weights (default):
        DEM:       0.35  — primary physical indicator
        Climate:   0.30  — land anchor (Köppen-based)
        Ocean:     0.20  — negative-elevation / bathymetry baseline
        Landcover: 0.15  — surface confirmation layer

    Conflict resolution:
        When sources disagree, a weighted probability vote is computed.
        The argmax of the resulting distribution is the final class.
        Entropy and a conflict flag are surfaced for downstream use.
    """

    def __init__(self, weights: Optional[dict] = None):
        self._weights = weights or DEFAULT_WEIGHTS
        self._confidence_model = ConfidenceModel()
        self._decision_engine = DecisionEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        dem_signal: Optional[str],
        climate_signal: Optional[str],
        ocean_signal: Optional[str],
        landcover_signal: Optional[str],
        dem_confidence: float = 1.0,
        climate_confidence: float = 1.0,
        ocean_confidence: float = 1.0,
        landcover_confidence: float = 1.0,
    ) -> ArbitrationResult:
        """
        Resolve multi-source signals into a single semantic decision.

        Args:
            *_signal:      inferred semantic class from each source layer,
                           or None if the source is unavailable.
            *_confidence:  source-layer confidence for that class (0–1).

        Returns:
            ArbitrationResult with final_class, confidence_score,
            probability_map, conflict_detected, entropy, explanation_trace.
        """
        trace: List[str] = []

        # --- 1. Collect signals ---
        registry = SignalRegistry()
        source_map = {
            SIGNAL_DEM:       (dem_signal,       dem_confidence),
            SIGNAL_CLIMATE:   (climate_signal,   climate_confidence),
            SIGNAL_OCEAN:     (ocean_signal,     ocean_confidence),
            SIGNAL_LANDCOVER: (landcover_signal, landcover_confidence),
        }

        for name, (value, conf) in source_map.items():
            if value is not None:
                registry.register(name, value, weight=self._weights[name],
                                  raw_confidence=conf)
                trace.append(f"[INPUT]  {name}: class={value!r}  conf={conf:.2f}  w={self._weights[name]:.2f}")
            else:
                trace.append(f"[INPUT]  {name}: ABSENT (skipped)")

        signals: List[SemanticSignal] = registry.get_all()

        # --- 1b. De-correlate elevation signals ---
        # DEM and Ocean are both elevation-derived; when they agree they must
        # not double-count. Merge them into one signal carrying only the
        # higher weight, so independent land-anchor signals (Climate, Landcover)
        # are not unfairly outweighed.
        signals = self._decorrelate_elevation(signals, trace)

        # --- 2. Detect conflict ---
        conflict = self._decision_engine.detect_conflict(signals)
        if conflict:
            trace.append("[CONFLICT] Sources disagree — weighted fusion applied")
        else:
            trace.append("[AGREE]   Sources largely agree")

        # --- 3. Compute probability distribution ---
        prob_map = self._confidence_model.compute_confidence(signals)
        top3 = sorted(prob_map.items(), key=lambda x: -x[1])[:3]
        trace.append("[PROBS]  " + "  ".join(f"{cls}={p:.3f}" for cls, p in top3))

        # --- 4. Final decision ---
        final_class, confidence_score, entropy = self._decision_engine.decide(prob_map)
        winner_class, runner_up_class, winner_margin = self._decision_engine.rank(prob_map)

        ranked = sorted(prob_map.items(), key=lambda x: -x[1])
        winner_prob    = ranked[0][1] if ranked else 0.0
        runner_up_prob = ranked[1][1] if len(ranked) > 1 else 0.0
        winner_ratio   = (winner_prob / runner_up_prob) if runner_up_prob > 1e-9 else (winner_prob * 100.0)

        trace.append(
            f"[DECIDE] final_class={final_class!r}  confidence={confidence_score:.3f}  "
            f"entropy={entropy:.3f}  margin={winner_margin:.3f}  ratio={winner_ratio:.3f}  "
            f"runner_up={runner_up_class!r}"
        )

        return ArbitrationResult(
            final_class=final_class,
            confidence_score=confidence_score,
            probability_map=prob_map,
            conflict_detected=conflict,
            entropy=entropy,
            winner_class=winner_class,
            runner_up_class=runner_up_class,
            winner_margin=winner_margin,
            winner_ratio=winner_ratio,
            explanation_trace=trace,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _decorrelate_elevation(
        self,
        signals: List[SemanticSignal],
        trace: List[str],
    ) -> List[SemanticSignal]:
        """
        DEM and Ocean both derive from elevation data; when they agree they
        must not be counted as two independent votes.

        Rule: if both are present and agree on the same class, merge them
        into one signal carrying the higher weight and the average confidence.
        If they disagree, keep them separate (genuine physical conflict).
        """
        by_source = {s.source: s for s in signals}
        dem_sig = by_source.get(SIGNAL_DEM)
        ocn_sig = by_source.get(SIGNAL_OCEAN)

        if dem_sig is None or ocn_sig is None:
            return signals  # nothing to de-correlate

        if dem_sig.inferred_class == ocn_sig.inferred_class:
            merged_weight = max(dem_sig.weight, ocn_sig.weight)
            merged_conf   = (dem_sig.raw_confidence + ocn_sig.raw_confidence) / 2.0
            merged = SemanticSignal(
                source="dem+ocean",
                inferred_class=dem_sig.inferred_class,
                raw_confidence=merged_conf,
                weight=merged_weight,
                metadata={"merged_from": [SIGNAL_DEM, SIGNAL_OCEAN]},
            )
            trace.append(
                f"[DECORR] dem+ocean agree on {dem_sig.inferred_class!r} → merged "
                f"w={merged_weight:.2f} conf={merged_conf:.2f}"
            )
            # Replace both with the merged signal
            return [s for s in signals if s.source not in (SIGNAL_DEM, SIGNAL_OCEAN)] + [merged]
        else:
            trace.append(
                f"[DECORR] dem={dem_sig.inferred_class!r} vs ocean={ocn_sig.inferred_class!r} "
                "→ kept separate (physical conflict)"
            )
            return signals
