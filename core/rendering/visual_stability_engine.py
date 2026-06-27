"""Visual Stability Engine — temporal consistency layer.

Prevents per-pixel winner flickering at biome/ocean/ice boundaries by applying
exponential score smoothing and stability locking across frames.

Pipeline position:
    VisualGrammar → Candidates → VisualRuleResolver → STABILITY ENGINE → VisualWeightHarmonizer

Key guarantees:
  - Same sequence of inputs produces same sequence of outputs (deterministic).
  - Stability logic never modifies SAL / M1 / VC / VisualGrammar / Harmonizer.
  - Zero overhead when disabled: engine is never instantiated in the normal path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .visual_rule_resolver import FinalVisualState, _rule_to_climate_family


@dataclass
class StablePixelState:
    """Per-pixel temporal memory retained across frames."""

    last_winner: str
    smoothed_scores: dict[str, float]   # rule_type → exponentially smoothed weighted score
    stability_weight: float             # smoothed composite score of the winning rule
    frame_id: Optional[int] = None


class VisualStabilityEngine:
    """Temporal consistency filter for the visual rule resolver pipeline.

    Attach to a VisualRuleResolver via set_stability_engine(), or call stabilize()
    manually between resolve_conflicts() and the harmonizer.

    Usage::
        engine = VisualStabilityEngine(decay=0.85)
        engine.begin_frame(frame_id)
        for lon, lat in pixels:
            resolved = resolver.resolve_conflicts(candidates, ctx, pixel_key=(lon, lat))
            # engine.stabilize() is called automatically when attached to the resolver
        engine.end_frame(frame_id)
    """

    def __init__(self, decay: float = 0.85, lock_threshold: float = 0.10) -> None:
        self.decay = decay
        self.lock_threshold = lock_threshold
        self.previous_frame_state: dict = {}
        self.current_frame_state: dict = {}
        self._current_frame_id: Optional[int] = None

    # ── Frame lifecycle ───────────────────────────────────────────────────────

    def begin_frame(self, frame_id: int = 0) -> None:
        """Promote current-frame state to previous; open a fresh current-frame slate."""
        self.previous_frame_state = dict(self.current_frame_state)
        self.current_frame_state = {}
        self._current_frame_id = frame_id

    def end_frame(self, frame_id: int = 0) -> None:
        """Close current frame. State promotion happens at the next begin_frame()."""
        # No-op: lifecycle bookend for callers that need a symmetric API.
        pass

    # ── Core stability logic ──────────────────────────────────────────────────

    def stabilize(
        self,
        current_state: FinalVisualState,
        pixel_key,
        rule_weights: dict[str, float],
        pixel_context=None,
    ) -> FinalVisualState:
        """Apply temporal smoothing and stability locking to a resolver output.

        Args:
            current_state:  Output of VisualRuleResolver.resolve_conflicts().
            pixel_key:      Hashable spatial identifier (e.g. ``(lon, lat)`` tuple).
            rule_weights:   The resolver's rule_weights dict, used for weighted scoring.
            pixel_context:  PixelContext or None; used to derive climate_family when
                            locking to previous winner.

        Returns:
            A FinalVisualState that is either the original ``current_state`` or a
            locked copy using the previous winner when the score delta is below
            ``lock_threshold``. The input is never mutated.
        """
        prev = self.previous_frame_state.get(pixel_key)
        smoothed = self._blend_scores(current_state, prev, rule_weights)

        # ── No history: record and pass through ───────────────────────────────
        if prev is None:
            self.current_frame_state[pixel_key] = StablePixelState(
                last_winner=current_state.winning_rule,
                smoothed_scores=smoothed,
                stability_weight=current_state.composite_score,
                frame_id=self._current_frame_id,
            )
            return current_state

        # ── Same winner: smooth weight, pass through ──────────────────────────
        if current_state.winning_rule == prev.last_winner:
            new_weight = (
                self.decay * prev.stability_weight
                + (1.0 - self.decay) * current_state.composite_score
            )
            self.current_frame_state[pixel_key] = StablePixelState(
                last_winner=current_state.winning_rule,
                smoothed_scores=smoothed,
                stability_weight=new_weight,
                frame_id=self._current_frame_id,
            )
            return current_state

        # ── Winner changed: test whether change is significant ────────────────
        # Use smoothed score for current winner; fall back to composite_score if the
        # rule didn't appear in prev frame (new rule entering the scene).
        current_winner_score = smoothed.get(
            current_state.winning_rule, current_state.composite_score
        )
        # For previous winner: use its smoothed entry if it appears in current
        # candidates, otherwise fall back to its stored stability_weight.
        prev_winner_score = smoothed.get(prev.last_winner, prev.stability_weight)
        score_delta = abs(current_winner_score - prev_winner_score)

        if score_delta < self.lock_threshold:
            # Stability lock: revert output to previous winner.
            locked = self._lock_to_previous(
                current_state, prev.last_winner, prev_winner_score, pixel_context
            )
            new_weight = (
                self.decay * prev.stability_weight
                + (1.0 - self.decay) * prev_winner_score
            )
            self.current_frame_state[pixel_key] = StablePixelState(
                last_winner=prev.last_winner,
                smoothed_scores=smoothed,
                stability_weight=new_weight,
                frame_id=self._current_frame_id,
            )
            return locked

        # Accept new winner; blend weight toward current.
        new_weight = (
            self.decay * prev.stability_weight
            + (1.0 - self.decay) * current_winner_score
        )
        self.current_frame_state[pixel_key] = StablePixelState(
            last_winner=current_state.winning_rule,
            smoothed_scores=smoothed,
            stability_weight=new_weight,
            frame_id=self._current_frame_id,
        )
        return current_state

    # ── Inspection API ────────────────────────────────────────────────────────

    def pixel_state(self, pixel_key) -> Optional[StablePixelState]:
        """Return current-frame StablePixelState for a pixel, or None."""
        return self.current_frame_state.get(pixel_key)

    def previous_pixel_state(self, pixel_key) -> Optional[StablePixelState]:
        """Return previous-frame StablePixelState for a pixel, or None."""
        return self.previous_frame_state.get(pixel_key)

    # ── Private ───────────────────────────────────────────────────────────────

    def _blend_scores(
        self,
        current: FinalVisualState,
        prev: Optional[StablePixelState],
        rule_weights: dict[str, float],
    ) -> dict[str, float]:
        """Compute exponentially smoothed weighted scores for current candidates."""
        prev_scores = prev.smoothed_scores if prev is not None else {}
        blended: dict[str, float] = {}
        for cand in current.candidates:
            rt = cand.rule_type
            w = rule_weights.get(rt, 0.5)
            current_ws = cand.score * w
            if rt in prev_scores:
                blended[rt] = (
                    self.decay * prev_scores[rt]
                    + (1.0 - self.decay) * current_ws
                )
            else:
                blended[rt] = current_ws
        return blended

    def _lock_to_previous(
        self,
        current: FinalVisualState,
        prev_winner: str,
        prev_score: float,
        ctx,
    ) -> FinalVisualState:
        """Return a new FinalVisualState locked to the previous winning rule."""
        family = _rule_to_climate_family(prev_winner, ctx)
        return FinalVisualState(
            winning_rule=prev_winner,
            composite_score=round(prev_score, 6),
            ocean=(prev_winner == "ocean"),
            climate_family=family,
            candidates=current.candidates,   # preserve current candidates for inspection
        )
