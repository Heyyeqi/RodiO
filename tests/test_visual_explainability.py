"""Visual Explainability Layer tests.

Tests:
1. trace exists when debug=True
2. no trace when debug=False
3. winner rule recorded correctly
4. tie-break reason captured
5. deterministic trace output
6. rendering output unchanged with explainability on/off
"""

from __future__ import annotations

import unittest

from core.rendering.renderer_types import TimeState
from core.rendering.visual_explainability import (
    CandidateScore,
    VisualDecisionTrace,
    VisualExplainabilityEngine,
)
from core.rendering.visual_rule_resolver import (
    PixelContext,
    RuleCandidate,
    VisualRuleResolver,
)


# ── Shared helpers ─────────────────────────────────────────────────────────────


def _ocean_ctx() -> PixelContext:
    return PixelContext(ocean=True, elevation=-500.0, biome_proxy=0.10, sun_angle=90.0)


def _polar_ctx() -> PixelContext:
    return PixelContext(climate_class="EF", ocean=False, elevation=500.0, biome_proxy=0.10, sun_angle=90.0)


def _desert_ctx() -> PixelContext:
    return PixelContext(climate_class="BWh", ocean=False, elevation=200.0, biome_proxy=0.35, sun_angle=90.0)


def _make_stub_renderer(enable_explainability=False):
    from core.rendering import D6Renderer
    from core.runtime.runtime_types import FeatureVector, SpatialState

    fv = FeatureVector(elevation=50.0, ocean_flag=0.0, climate_class=8.0, slope_proxy=0.1)

    class StubRuntime:
        resolution_mode = "8k"
        def query_point(self, lon, lat):
            return SpatialState(
                climate_class=8, elevation=50.0, slope_proxy=0.1,
                ocean=False, biome_proxy=0.60,
                feature_vector=fv, normalized_vector=fv, source={},
            )

    return D6Renderer(StubRuntime(), enable_explainability=enable_explainability)


# ── 1. Trace exists when debug=True ───────────────────────────────────────────


class TestTraceExistsWhenDebugOn(unittest.TestCase):

    def test_resolver_debug_true_has_traces_attr(self):
        r = VisualRuleResolver(debug=True)
        self.assertTrue(hasattr(r, "traces"))

    def test_resolve_conflicts_appends_trace(self):
        r = VisualRuleResolver(debug=True)
        ctx = _ocean_ctx()
        candidates = r.evaluate_rules(ctx)
        r.resolve_conflicts(candidates, ctx)
        self.assertEqual(len(r.traces), 1)

    def test_trace_is_visual_decision_trace(self):
        r = VisualRuleResolver(debug=True)
        ctx = _ocean_ctx()
        r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        self.assertIsInstance(r.traces[0], VisualDecisionTrace)

    def test_multiple_resolves_accumulate_traces(self):
        r = VisualRuleResolver(debug=True)
        for ctx in [_ocean_ctx(), _polar_ctx(), _desert_ctx()]:
            r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        self.assertEqual(len(r.traces), 3)

    def test_renderer_with_explainability_on_produces_traces(self):
        renderer = _make_stub_renderer(enable_explainability=True)
        ts = TimeState(hour=12.0, day_of_year=180)
        renderer.render_point(0.0, 0.0, ts)
        meta = renderer.get_render_metadata()
        self.assertTrue(meta["resolver_enabled"])
        self.assertEqual(len(meta["visual_traces"]), 1)

    def test_clear_traces_resets_to_empty(self):
        r = VisualRuleResolver(debug=True)
        ctx = _ocean_ctx()
        r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        r.clear_traces()
        self.assertEqual(len(r.traces), 0)


# ── 2. No trace when debug=False ──────────────────────────────────────────────


class TestNoTraceWhenDebugOff(unittest.TestCase):

    def test_resolver_debug_false_no_traces_attr(self):
        """When debug=False, the traces attribute must not be allocated."""
        r = VisualRuleResolver(debug=False)
        self.assertFalse(hasattr(r, "traces"))

    def test_get_debug_traces_returns_empty_when_off(self):
        r = VisualRuleResolver(debug=False)
        ctx = _ocean_ctx()
        r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        self.assertEqual(r.get_debug_traces(), [])

    def test_renderer_off_by_default_no_traces(self):
        renderer = _make_stub_renderer(enable_explainability=False)
        ts = TimeState(hour=12.0, day_of_year=180)
        renderer.render_point(0.0, 0.0, ts)
        meta = renderer.get_render_metadata()
        self.assertFalse(meta["resolver_enabled"])
        self.assertEqual(meta["visual_traces"], [])

    def test_clear_traces_noop_when_off(self):
        """clear_traces must not raise when debug=False."""
        r = VisualRuleResolver(debug=False)
        r.clear_traces()   # must not raise

    def test_no_explainability_import_at_module_level(self):
        """VisualExplainabilityEngine import happens only when debug=True."""
        # A fresh resolver in non-debug mode must not have _explain attribute
        r = VisualRuleResolver(debug=False)
        self.assertFalse(hasattr(r, "_explain"))


# ── 3. Winner rule recorded correctly ─────────────────────────────────────────


class TestWinnerRuleRecorded(unittest.TestCase):

    def test_ocean_pixel_winner_in_trace(self):
        r = VisualRuleResolver(debug=True)
        ctx = _ocean_ctx()
        state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        trace = r.traces[0]
        self.assertEqual(trace.winner_rule, state.winning_rule)
        self.assertEqual(trace.winner_rule, "ocean")

    def test_polar_pixel_winner_in_trace(self):
        r = VisualRuleResolver(debug=True)
        ctx = _polar_ctx()
        state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        trace = r.traces[0]
        self.assertEqual(trace.winner_rule, state.winning_rule)
        self.assertEqual(trace.winner_rule, "polar")

    def test_desert_pixel_winner_in_trace(self):
        r = VisualRuleResolver(debug=True)
        ctx = _desert_ctx()
        state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        trace = r.traces[0]
        self.assertEqual(trace.winner_rule, "desert")

    def test_trace_pixel_context_matches_input(self):
        r = VisualRuleResolver(debug=True)
        ctx = _ocean_ctx()
        r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        trace = r.traces[0]
        self.assertEqual(trace.pixel_context.get("ocean"), True)
        self.assertAlmostEqual(trace.pixel_context.get("elevation"), -500.0)

    def test_trace_scores_keyed_by_rule_type(self):
        r = VisualRuleResolver(debug=True)
        ctx = _ocean_ctx()
        r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        trace = r.traces[0]
        self.assertIn("ocean", trace.scores)
        self.assertIsInstance(trace.scores["ocean"], CandidateScore)

    def test_trace_candidates_list_populated(self):
        r = VisualRuleResolver(debug=True)
        ctx = _ocean_ctx()
        r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        trace = r.traces[0]
        self.assertIsInstance(trace.candidates, list)
        self.assertGreater(len(trace.candidates), 0)
        # Each entry is a dict with rule_type key
        self.assertIn("rule_type", trace.candidates[0])

    def test_final_color_source_non_empty(self):
        r = VisualRuleResolver(debug=True)
        ctx = _ocean_ctx()
        r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        trace = r.traces[0]
        self.assertIsInstance(trace.final_color_source, str)
        self.assertGreater(len(trace.final_color_source), 0)

    def test_final_color_source_labels(self):
        r = VisualRuleResolver(debug=True)
        cases = [
            (_ocean_ctx(),  "ocean:"),
            (_polar_ctx(),  "ice:"),
            (_desert_ctx(), "desert:"),
        ]
        for ctx, prefix in cases:
            r.clear_traces()
            r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
            self.assertTrue(
                r.traces[0].final_color_source.startswith(prefix),
                msg=f"Expected prefix '{prefix}', got '{r.traces[0].final_color_source}'"
            )


# ── 4. Tie-break reason captured ──────────────────────────────────────────────


class TestTieBreakReasonCaptured(unittest.TestCase):

    def _forced_tie(self) -> tuple[VisualRuleResolver, list[RuleCandidate]]:
        """Build a resolver and candidates that guarantee a tie-break."""
        r = VisualRuleResolver(debug=True)
        # Force TIE_THRESHOLD to cover any gap
        r.TIE_THRESHOLD = 0.99
        # ocean (weight=1.0) and ice (weight=0.95) with same raw score → tie
        cands = [
            RuleCandidate("ocean", 0.80),
            RuleCandidate("ice",   0.80),
        ]
        return r, cands

    def test_tie_break_reason_set_when_triggered(self):
        r, cands = self._forced_tie()
        r.resolve_conflicts(cands)
        trace = r.traces[0]
        self.assertIsNotNone(trace.tie_break_reason)

    def test_tie_break_reason_is_string(self):
        r, cands = self._forced_tie()
        r.resolve_conflicts(cands)
        self.assertIsInstance(r.traces[0].tie_break_reason, str)

    def test_tie_break_reason_mentions_priority(self):
        r, cands = self._forced_tie()
        r.resolve_conflicts(cands)
        reason = r.traces[0].tie_break_reason
        self.assertIn("priority", reason.lower())

    def test_no_tie_break_reason_when_clear_winner(self):
        """When the gap exceeds TIE_THRESHOLD, tie_break_reason must be None."""
        r = VisualRuleResolver(debug=True)
        cands = [
            RuleCandidate("ocean", 0.95),   # weighted = 0.95
            RuleCandidate("biome", 0.30),   # weighted = 0.24 → gap = 0.71 >> 0.05
        ]
        r.resolve_conflicts(cands)
        self.assertIsNone(r.traces[0].tie_break_reason)

    def test_tie_break_winner_consistent_with_priority(self):
        """Tie-break must select ocean over ice per priority table."""
        r, cands = self._forced_tie()
        state = r.resolve_conflicts(cands)
        self.assertEqual(state.winning_rule, "ocean")
        self.assertEqual(r.traces[0].winner_rule, "ocean")


# ── 5. Deterministic trace output ─────────────────────────────────────────────


class TestDeterministicTrace(unittest.TestCase):

    def _run(self, ctx: PixelContext) -> VisualDecisionTrace:
        r = VisualRuleResolver(debug=True)
        r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        return r.traces[0]

    def test_same_context_same_winner(self):
        ctx = _ocean_ctx()
        t1 = self._run(ctx)
        t2 = self._run(ctx)
        self.assertEqual(t1.winner_rule, t2.winner_rule)

    def test_same_context_same_tie_break_reason(self):
        ctx = _ocean_ctx()
        t1 = self._run(ctx)
        t2 = self._run(ctx)
        self.assertEqual(t1.tie_break_reason, t2.tie_break_reason)

    def test_same_context_same_scores(self):
        ctx = _polar_ctx()
        t1 = self._run(ctx)
        t2 = self._run(ctx)
        for rt in t1.scores:
            self.assertAlmostEqual(
                t1.scores[rt].weighted_score,
                t2.scores[rt].weighted_score,
                places=6,
            )

    def test_same_context_same_color_source(self):
        ctx = _desert_ctx()
        t1 = self._run(ctx)
        t2 = self._run(ctx)
        self.assertEqual(t1.final_color_source, t2.final_color_source)

    def test_different_context_may_differ(self):
        t_ocean = self._run(_ocean_ctx())
        t_polar = self._run(_polar_ctx())
        self.assertNotEqual(t_ocean.winner_rule, t_polar.winner_rule)


# ── 6. Rendering output unchanged ─────────────────────────────────────────────


class TestRenderingOutputUnchanged(unittest.TestCase):

    def test_render_point_same_with_and_without_explainability(self):
        """Pixel RGB must be identical whether explainability is on or off."""
        ts = TimeState(hour=12.0, day_of_year=180)
        r_off = _make_stub_renderer(enable_explainability=False)
        r_on = _make_stub_renderer(enable_explainability=True)
        rgb_off = r_off.render_point(10.0, 20.0, ts)
        rgb_on = r_on.render_point(10.0, 20.0, ts)
        self.assertEqual(rgb_off, rgb_on)

    def test_multiple_renders_same_output_both_modes(self):
        ts = TimeState(hour=9.0, day_of_year=90)
        r_off = _make_stub_renderer(enable_explainability=False)
        r_on = _make_stub_renderer(enable_explainability=True)
        for lon, lat in [(0, 0), (45, -30), (120, 35)]:
            with self.subTest(lon=lon, lat=lat):
                self.assertEqual(
                    r_off.render_point(lon, lat, ts),
                    r_on.render_point(lon, lat, ts),
                )

    def test_resolver_output_unchanged_by_debug_mode(self):
        """resolve_conflicts must return identical FinalVisualState in both modes."""
        ctx = _ocean_ctx()
        cands_off = VisualRuleResolver(debug=False).evaluate_rules(ctx)
        cands_on = VisualRuleResolver(debug=True).evaluate_rules(ctx)

        state_off = VisualRuleResolver(debug=False).resolve_conflicts(cands_off, ctx)
        state_on = VisualRuleResolver(debug=True).resolve_conflicts(cands_on, ctx)

        self.assertEqual(state_off.winning_rule, state_on.winning_rule)
        self.assertAlmostEqual(state_off.composite_score, state_on.composite_score, places=6)
        self.assertEqual(state_off.ocean, state_on.ocean)
        self.assertEqual(state_off.climate_family, state_on.climate_family)

    def test_clear_metadata_does_not_affect_output(self):
        """Clearing traces mid-session must not change subsequent render output."""
        ts = TimeState(hour=12.0, day_of_year=180)
        renderer = _make_stub_renderer(enable_explainability=True)
        rgb_before = renderer.render_point(0.0, 0.0, ts)
        renderer.clear_render_metadata()
        rgb_after = renderer.render_point(0.0, 0.0, ts)
        self.assertEqual(rgb_before, rgb_after)

    def test_get_render_metadata_does_not_clear_traces(self):
        """Calling get_render_metadata() must be non-destructive."""
        ts = TimeState(hour=12.0, day_of_year=180)
        renderer = _make_stub_renderer(enable_explainability=True)
        renderer.render_point(0.0, 0.0, ts)
        meta1 = renderer.get_render_metadata()
        meta2 = renderer.get_render_metadata()
        self.assertEqual(len(meta1["visual_traces"]), len(meta2["visual_traces"]))


# ── 7. VisualExplainabilityEngine unit tests ──────────────────────────────────


class TestExplainabilityEngine(unittest.TestCase):

    def _engine(self):
        return VisualExplainabilityEngine()

    def _scored(self):
        weights = {"ocean": 1.0, "biome": 0.8}
        return [
            (0.90, RuleCandidate("ocean", 0.90, {"depth": 500.0})),
            (0.56, RuleCandidate("biome", 0.70, {"family": "tropical"})),
        ]

    def test_trace_scores_contain_raw_and_weighted(self):
        engine = self._engine()
        ctx = PixelContext(ocean=True, elevation=-500.0)
        trace = engine.trace_decision(
            context=ctx,
            scored_candidates=self._scored(),
            winner_rule="ocean",
            rule_weights={"ocean": 1.0, "biome": 0.8},
            tie_break_triggered=False,
            tie_break_detail=None,
            resolved_ocean=True,
            resolved_climate_family="unknown",
        )
        self.assertIn("ocean", trace.scores)
        cs = trace.scores["ocean"]
        self.assertAlmostEqual(cs.raw_score, 0.90, places=5)
        self.assertAlmostEqual(cs.weight, 1.0, places=5)
        self.assertAlmostEqual(cs.weighted_score, 0.90, places=5)

    def test_tie_break_not_triggered_means_none_reason(self):
        engine = self._engine()
        ctx = {}
        trace = engine.trace_decision(
            context=ctx,
            scored_candidates=self._scored(),
            winner_rule="ocean",
            rule_weights={"ocean": 1.0},
            tie_break_triggered=False,
            tie_break_detail=None,
            resolved_ocean=True,
            resolved_climate_family="unknown",
        )
        self.assertIsNone(trace.tie_break_reason)

    def test_tie_break_triggered_stores_detail(self):
        engine = self._engine()
        detail = "gap 0.001 < 0.05; priority: ocean > ice"
        trace = engine.trace_decision(
            context={},
            scored_candidates=self._scored(),
            winner_rule="ocean",
            rule_weights={"ocean": 1.0},
            tie_break_triggered=True,
            tie_break_detail=detail,
            resolved_ocean=True,
            resolved_climate_family="unknown",
        )
        self.assertEqual(trace.tie_break_reason, detail)

    def test_candidates_serialised_as_dicts(self):
        engine = self._engine()
        trace = engine.trace_decision(
            context={},
            scored_candidates=self._scored(),
            winner_rule="ocean",
            rule_weights={"ocean": 1.0, "biome": 0.8},
            tie_break_triggered=False,
            tie_break_detail=None,
            resolved_ocean=True,
            resolved_climate_family="unknown",
        )
        for entry in trace.candidates:
            self.assertIsInstance(entry, dict)
            self.assertIn("rule_type", entry)
            self.assertIn("score", entry)


if __name__ == "__main__":
    unittest.main()
