"""Visual Rule Resolver — Stage 8 conflict resolution system.

Replaces sequential rule application with a weighted scoring and deterministic
conflict resolution layer.

Pipeline position:
    BMNG base → VisualGrammar (candidates) → VisualRuleResolver → VisualWeightHarmonizer → D6 output

Key guarantee: same pixel_context → same FinalVisualState, regardless of the
order in which candidates are passed in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union


# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class RuleCandidate:
    """A single visual rule competing for a pixel.

    score is the per-candidate confidence (0.0–1.0) before rule_weight scaling.
    The resolver multiplies score × rule_weight to get the final weighted score.
    payload carries auxiliary data for downstream consumers (not used in
    conflict resolution itself, so it does not affect determinism).
    """

    rule_type: str     # "ocean" | "biome" | "desert" | "ice" | "polar" | "atmosphere"
    score: float       # raw confidence, 0.0–1.0
    payload: dict = field(default_factory=dict)


@dataclass
class PixelContext:
    """Semantic context for a single pixel, consumed by evaluate_rules."""

    climate_class: Union[str, int, None] = None
    elevation: float = 0.0
    ocean: bool = False
    biome_proxy: float = 0.60
    sun_angle: float = 90.0
    slope_proxy: float = 0.0


@dataclass
class FinalVisualState:
    """Output of resolve_conflicts: the authoritative visual classification.

    ocean and climate_family are the resolved values that downstream modules
    (VisualGrammar.apply_to_rgb, VisualWeightHarmonizer.harmonize) must use.
    candidates is preserved for inspection / debugging.
    """

    winning_rule: str
    composite_score: float
    ocean: bool
    climate_family: str
    candidates: list[RuleCandidate] = field(default_factory=list)


# ── Resolver ──────────────────────────────────────────────────────────────────


class VisualRuleResolver:
    """Weighted scoring + deterministic conflict resolution.

    Usage::
        resolver = VisualRuleResolver()
        candidates = resolver.evaluate_rules(ctx)
        state = resolver.resolve_conflicts(candidates)

    The same pixel_context always produces the same FinalVisualState:
    - scoring is purely deterministic (no RNG)
    - ties are broken by a fixed priority table
    - candidates list order does not affect output
    """

    # Base weight per rule type (before candidate-level score scaling).
    rule_weights: dict[str, float]

    # Deterministic tie-breaker: lower index = wins in a tie.
    # Task spec: ocean > ice > biome > desert > atmosphere.
    # "polar" is treated as a sub-class of ice for tie-breaking.
    TIE_PRIORITY: tuple[str, ...] = (
        "ocean",
        "ice",
        "polar",
        "biome",
        "desert",
        "atmosphere",
    )

    # Score difference threshold below which tie-breaking kicks in.
    TIE_THRESHOLD: float = 0.05

    def __init__(self, debug: bool = False) -> None:
        self.rule_weights = {
            "ocean":      1.00,
            "biome":      0.80,
            "desert":     0.90,
            "ice":        0.95,
            "polar":      1.00,
            "atmosphere": 0.60,
        }
        self.debug = debug
        # Traces are only allocated when debug=True; the attribute doesn't exist
        # at all in normal mode so callers can't accidentally iterate over it.
        if debug:
            self.traces: list = []
            from .visual_explainability import VisualExplainabilityEngine
            self._explain = VisualExplainabilityEngine()

    # ── Public API ────────────────────────────────────────────────────────────

    def evaluate_rules(
        self,
        pixel_context: Union[PixelContext, dict],
    ) -> list[RuleCandidate]:
        """Generate all applicable rule candidates for a pixel context.

        Rules are NOT executed here; only scored.  The caller must pass the
        list to resolve_conflicts() to obtain the winning rule.
        """
        ctx = _as_context(pixel_context)
        candidates: list[RuleCandidate] = []

        # ── Ocean ─────────────────────────────────────────────────────────────
        if ctx.ocean:
            depth = abs(ctx.elevation) if ctx.elevation < 0 else 0.0
            ocean_score = 0.95 if depth >= 1000.0 else 0.88
            candidates.append(RuleCandidate(
                rule_type="ocean",
                score=ocean_score,
                payload={"depth": depth, "shallow": depth < 1000.0},
            ))

        # ── Climate-based land rules ───────────────────────────────────────────
        family = _climate_family(ctx.climate_class)

        if family == "polar":
            candidates.append(RuleCandidate(
                rule_type="polar",
                score=0.90,
                payload={"family": "polar", "elevation": ctx.elevation},
            ))
        elif family == "arid":
            candidates.append(RuleCandidate(
                rule_type="desert",
                score=0.85,
                payload={"family": "arid", "elevation": ctx.elevation},
            ))
        else:
            # Biome strength scales with biome_proxy richness
            biome_score = 0.50 + 0.25 * min(1.0, max(0.0, ctx.biome_proxy))
            candidates.append(RuleCandidate(
                rule_type="biome",
                score=biome_score,
                payload={"family": family, "biome_proxy": ctx.biome_proxy},
            ))

        # ── Elevation-inferred ice (overrides biome for high-altitude land) ───
        if not ctx.ocean and ctx.elevation >= 3500.0:
            # High non-ocean elevation: ice / glacial regardless of Koppen class
            ice_score = min(0.92, 0.70 + (ctx.elevation - 3500.0) / 15000.0)
            candidates.append(RuleCandidate(
                rule_type="ice",
                score=ice_score,
                payload={"elevation": ctx.elevation},
            ))

        # Also trigger ice for low biome_proxy non-ocean land (glacial inliers)
        if not ctx.ocean and ctx.biome_proxy < 0.20 and family != "polar":
            candidates.append(RuleCandidate(
                rule_type="ice",
                score=0.72,
                payload={"biome_proxy": ctx.biome_proxy, "reason": "low_proxy_glacial"},
            ))

        # ── Atmosphere (always present) ────────────────────────────────────────
        # Score scales with sun angle: full noon = 0.50, night ≈ 0.10.
        atmo_t = max(0.0, min(1.0, ctx.sun_angle / 90.0))
        atmo_score = 0.10 + 0.40 * atmo_t
        candidates.append(RuleCandidate(
            rule_type="atmosphere",
            score=atmo_score,
            payload={"sun_angle": ctx.sun_angle},
        ))

        return candidates

    def resolve_conflicts(
        self,
        candidates: list[RuleCandidate],
        pixel_context: Union[PixelContext, dict, None] = None,
        pixel_key=None,
    ) -> FinalVisualState:
        """Select the winning rule deterministically.

        Algorithm:
          1. weighted_score = candidate.score × rule_weights[candidate.rule_type]
          2. Sort descending by weighted_score.
          3. If the top-two weighted scores differ by < TIE_THRESHOLD → select by
             TIE_PRIORITY table (lower index wins).
          4. Derive FinalVisualState from winner.

        Guaranteed: same input (same candidates, same weights) → same output.
        """
        if not candidates:
            ctx = _as_context(pixel_context or {})
            return FinalVisualState(
                winning_rule="biome",
                composite_score=0.0,
                ocean=ctx.ocean,
                climate_family=_climate_family(ctx.climate_class),
                candidates=[],
            )

        # De-duplicate: if the same rule_type appears multiple times, keep the
        # highest-scoring instance only (prevents double-counting).
        seen: dict[str, RuleCandidate] = {}
        for c in candidates:
            if c.rule_type not in seen or c.score > seen[c.rule_type].score:
                seen[c.rule_type] = c
        unique = list(seen.values())

        # Compute weighted scores.
        scored: list[tuple[float, RuleCandidate]] = []
        for c in unique:
            w = self.rule_weights.get(c.rule_type, 0.5)
            scored.append((c.score * w, c))

        # Sort descending by weighted score; secondary: stable tie_priority index.
        def sort_key(item: tuple[float, RuleCandidate]) -> tuple[float, int]:
            ws, c = item
            pri = self.TIE_PRIORITY.index(c.rule_type) if c.rule_type in self.TIE_PRIORITY else 99
            # Negate ws for descending; pri is ascending (lower = higher priority).
            return (-ws, pri)

        scored.sort(key=sort_key)
        top_ws, top_c = scored[0]

        # Tie-break: if second-best is within threshold, use priority table.
        winner = top_c
        tie_break_triggered = False
        tie_break_detail: Optional[str] = None
        if len(scored) >= 2:
            second_ws, second_c = scored[1]
            if (top_ws - second_ws) < self.TIE_THRESHOLD:
                pri_top = self.TIE_PRIORITY.index(top_c.rule_type) if top_c.rule_type in self.TIE_PRIORITY else 99
                pri_sec = self.TIE_PRIORITY.index(second_c.rule_type) if second_c.rule_type in self.TIE_PRIORITY else 99
                tie_break_triggered = True
                if pri_sec < pri_top:
                    tie_break_detail = (
                        f"score gap {top_ws - second_ws:.4f} < threshold {self.TIE_THRESHOLD}; "
                        f"priority table: {second_c.rule_type}(pri={pri_sec}) > {top_c.rule_type}(pri={pri_top})"
                    )
                    winner = second_c
                    top_ws = second_ws
                else:
                    tie_break_detail = (
                        f"score gap {top_ws - second_ws:.4f} < threshold {self.TIE_THRESHOLD}; "
                        f"priority table: {top_c.rule_type}(pri={pri_top}) kept over {second_c.rule_type}(pri={pri_sec})"
                    )

        final_state = FinalVisualState(
            winning_rule=winner.rule_type,
            composite_score=round(top_ws, 6),
            ocean=winner.rule_type == "ocean",
            climate_family=_rule_to_climate_family(winner.rule_type, pixel_context),
            candidates=list(unique),
        )

        # Temporal stability hook — zero overhead when no engine is attached.
        if getattr(self, "_stability_engine", None) is not None and pixel_key is not None:
            final_state = self._stability_engine.stabilize(
                final_state, pixel_key, self.rule_weights, pixel_context
            )

        # Debug trace — zero overhead when self.debug is False.
        if self.debug:
            trace = self._explain.trace_decision(
                context=pixel_context or {},
                scored_candidates=scored,
                winner_rule=winner.rule_type,
                rule_weights=self.rule_weights,
                tie_break_triggered=tie_break_triggered,
                tie_break_detail=tie_break_detail,
                resolved_ocean=final_state.ocean,
                resolved_climate_family=final_state.climate_family,
            )
            self.traces.append(trace)

        return final_state


    def set_stability_engine(self, engine) -> None:
        """Attach a VisualStabilityEngine for temporal consistency filtering.

        When set, resolve_conflicts() passes the result through the engine before
        returning it.  ``pixel_key`` must be supplied at each resolve_conflicts() call.
        """
        self._stability_engine = engine

    def get_debug_traces(self) -> list:
        """Return accumulated VisualDecisionTrace objects.  Empty list if debug=False."""
        return list(getattr(self, "traces", []))

    def clear_traces(self) -> None:
        """Clear accumulated traces.  No-op when debug=False."""
        if self.debug:
            self.traces.clear()


# ── Private helpers ───────────────────────────────────────────────────────────


def _as_context(src: Union[PixelContext, dict]) -> PixelContext:
    if isinstance(src, PixelContext):
        return src
    return PixelContext(
        climate_class=src.get("climate_class"),
        elevation=float(src.get("elevation", 0.0)),
        ocean=bool(src.get("ocean", False)),
        biome_proxy=float(src.get("biome_proxy", 0.60)),
        sun_angle=float(src.get("sun_angle", 90.0)),
        slope_proxy=float(src.get("slope_proxy", 0.0)),
    )


def _climate_family(climate_class) -> str:
    """Mirror of VisualGrammar.climate_family to avoid a circular import."""
    if climate_class is None:
        return "unknown"
    if isinstance(climate_class, str):
        v = climate_class.strip().lower()
        for known in ("tropical", "arid", "temperate", "cold", "polar", "unknown"):
            if v == known:
                return v
        if v.startswith("a"):
            return "tropical"
        if v.startswith("b"):
            return "arid"
        if v.startswith("c"):
            return "temperate"
        if v.startswith("d"):
            return "cold"
        if v.startswith("e"):
            return "polar"
        return "unknown"
    try:
        cls = int(climate_class)
    except (TypeError, ValueError):
        return "unknown"
    if 1 <= cls <= 3:
        return "tropical"
    if 4 <= cls <= 7:
        return "arid"
    if 8 <= cls <= 16:
        return "temperate"
    if 17 <= cls <= 28:
        return "cold"
    if 29 <= cls <= 30:
        return "polar"
    return "unknown"


def _rule_to_climate_family(
    rule_type: str,
    ctx: Union[PixelContext, dict, None],
) -> str:
    """Derive climate_family for VisualWeightHarmonizer from the winning rule."""
    if rule_type in ("ice", "polar"):
        return "polar"
    if rule_type == "desert":
        return "arid"
    if rule_type == "ocean":
        return "unknown"
    # biome / atmosphere: use whatever the pixel context says
    if ctx is not None:
        c = _as_context(ctx) if isinstance(ctx, dict) else ctx
        return _climate_family(c.climate_class)
    return "unknown"
