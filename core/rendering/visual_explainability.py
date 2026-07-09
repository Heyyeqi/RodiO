"""Visual Explainability Layer — diagnostic trace for rule resolution decisions.

This module is a pure observer.  It records WHY each visual rule was selected
but never modifies resolver logic or rendering output.

Design invariants:
  - When disabled (default), there is literally nothing to execute at render time.
  - When enabled, traces are stored in the resolver instance; never on the call stack.
  - No mutable global state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Trace types ───────────────────────────────────────────────────────────────


@dataclass
class CandidateScore:
    """Per-candidate score breakdown for one pixel decision."""

    rule_type: str
    raw_score: float
    weight: float
    weighted_score: float


@dataclass
class VisualDecisionTrace:
    """Full audit record for a single pixel's rule selection.

    Fields:
        pixel_context     — snapshot of the PixelContext that drove evaluation
        candidates        — all unique candidates after deduplication
        scores            — per-rule score breakdown (rule_type → CandidateScore)
        winner_rule       — winning rule_type
        tie_break_reason  — human-readable explanation if tie-break triggered, else None
        final_color_source — description of what drove the resolved output
                             (e.g. "ocean:shallow", "biome:tropical", "polar:EF")
    """

    pixel_context: dict
    candidates: list[dict]             # serialisable snapshots of RuleCandidates
    scores: dict[str, CandidateScore]  # keyed by rule_type
    winner_rule: str
    tie_break_reason: Optional[str]
    final_color_source: str


# ── Engine ────────────────────────────────────────────────────────────────────


class VisualExplainabilityEngine:
    """Builds VisualDecisionTrace objects from resolver internals.

    Called by VisualRuleResolver when debug=True.  Never instantiated in the
    normal rendering path.
    """

    def trace_decision(
        self,
        context,                         # PixelContext or dict
        scored_candidates: list,         # list of (weighted_score, RuleCandidate)
        winner_rule: str,
        rule_weights: dict[str, float],
        tie_break_triggered: bool,
        tie_break_detail: Optional[str],
        resolved_ocean: bool,
        resolved_climate_family: str,
    ) -> VisualDecisionTrace:
        """Build a VisualDecisionTrace from resolver internals.

        Args:
            context:              PixelContext (or dict) that was evaluated.
            scored_candidates:    List of (weighted_score, RuleCandidate) after
                                  deduplication, in the order the resolver sees them.
            winner_rule:          rule_type of the winning candidate.
            rule_weights:         The resolver's rule_weights dict at the time of
                                  decision (captured by value, not reference).
            tie_break_triggered:  True if the score gap was below TIE_THRESHOLD.
            tie_break_detail:     Human-readable string explaining which priority-
                                  table entry won the tie, or None.
            resolved_ocean:       FinalVisualState.ocean field.
            resolved_climate_family: FinalVisualState.climate_family field.

        Returns:
            VisualDecisionTrace suitable for storage and later inspection.
        """
        # Serialise context
        if hasattr(context, '__dataclass_fields__'):
            ctx_dict = {f: getattr(context, f) for f in context.__dataclass_fields__}
        elif isinstance(context, dict):
            ctx_dict = dict(context)
        else:
            ctx_dict = {}

        # Build score breakdown
        scores: dict[str, CandidateScore] = {}
        for ws, cand in scored_candidates:
            w = rule_weights.get(cand.rule_type, 0.5)
            scores[cand.rule_type] = CandidateScore(
                rule_type=cand.rule_type,
                raw_score=round(cand.score, 6),
                weight=w,
                weighted_score=round(ws, 6),
            )

        # Serialise candidates (payload may contain arbitrary dicts; kept as-is)
        cand_snapshots = [
            {"rule_type": c.rule_type, "score": round(c.score, 6), "payload": dict(c.payload)}
            for _, c in scored_candidates
        ]

        # Derive final_color_source label
        final_color_source = _color_source_label(
            winner_rule, resolved_ocean, resolved_climate_family, ctx_dict
        )

        return VisualDecisionTrace(
            pixel_context=ctx_dict,
            candidates=cand_snapshots,
            scores=scores,
            winner_rule=winner_rule,
            tie_break_reason=tie_break_detail if tie_break_triggered else None,
            final_color_source=final_color_source,
        )


# ── Private helpers ───────────────────────────────────────────────────────────


def _color_source_label(
    winner_rule: str,
    ocean: bool,
    climate_family: str,
    ctx: dict,
) -> str:
    """Produce a compact label describing what drove the final colour."""
    if winner_rule == "ocean":
        depth = ctx.get("elevation", 0)
        kind = "deep" if isinstance(depth, (int, float)) and depth < -1000 else "shallow"
        return f"ocean:{kind}"
    if winner_rule in ("ice", "polar"):
        elev = ctx.get("elevation", 0)
        cc = ctx.get("climate_class", "unknown")
        return f"ice:{cc}@{elev:.0f}m"
    if winner_rule == "desert":
        return f"desert:{climate_family}"
    if winner_rule == "biome":
        return f"biome:{climate_family}"
    if winner_rule == "atmosphere":
        sun = ctx.get("sun_angle", 0)
        return f"atmosphere:sun={sun:.1f}°"
    return f"{winner_rule}:{climate_family}"
