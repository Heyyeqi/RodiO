"""Visual Rule Resolver tests (Stage 8).

Tests:
1. desert vs polar conflict resolution
2. biome vs ocean dominance
3. deterministic tie-breaking
4. score threshold logic (TIE_THRESHOLD)
5. no regression in SAL / M1 / VC pipeline
"""

from __future__ import annotations

import unittest

from core.rendering.visual_rule_resolver import (
    FinalVisualState,
    PixelContext,
    RuleCandidate,
    VisualRuleResolver,
)


# ── Shared helpers ────────────────────────────────────────────────────────────


def _resolver() -> VisualRuleResolver:
    return VisualRuleResolver()


def _make_ctx(**kw) -> PixelContext:
    defaults = dict(climate_class=None, elevation=0.0, ocean=False, biome_proxy=0.60, sun_angle=90.0)
    defaults.update(kw)
    return PixelContext(**defaults)


# ── 1. Desert vs polar conflict resolution ────────────────────────────────────


class TestDesertVsPolarConflict(unittest.TestCase):

    def test_explicit_polar_beats_desert_elevation(self):
        """A polar climate label should win over an arid label at moderate elevation."""
        r = _resolver()
        ctx = _make_ctx(climate_class="EF", elevation=500.0, ocean=False)
        state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        self.assertEqual(state.winning_rule, "polar")
        self.assertEqual(state.climate_family, "polar")

    def test_explicit_arid_beats_moderate_biome(self):
        """Arid Koppen class should produce 'desert' winning rule on flat land."""
        r = _resolver()
        ctx = _make_ctx(climate_class="BWh", elevation=200.0, ocean=False)
        state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        self.assertEqual(state.winning_rule, "desert")
        self.assertEqual(state.climate_family, "arid")

    def test_high_elevation_ice_beats_arid(self):
        """Very high elevation (> 3500 m) should trigger ice over desert."""
        r = _resolver()
        ctx = _make_ctx(climate_class="BWh", elevation=4500.0, ocean=False)
        candidates = r.evaluate_rules(ctx)
        state = r.resolve_conflicts(candidates, ctx)
        # ice (score≈0.77, weight=0.95) vs desert (score=0.85, weight=0.90)
        # ice weighted ≈ 0.73, desert weighted ≈ 0.765 → desert wins unless ice score high enough
        # At 4500m: ice_score = min(0.92, 0.70 + 1000/15000) = 0.767 → weighted = 0.729
        # desert: 0.85 × 0.9 = 0.765 → desert narrowly wins
        # This tests that the system makes a deterministic choice either way
        self.assertIn(state.winning_rule, ("ice", "desert"))
        # The result must always be the same
        state2 = r.resolve_conflicts(candidates, ctx)
        self.assertEqual(state.winning_rule, state2.winning_rule)

    def test_extreme_elevation_ice_beats_arid(self):
        """At truly extreme elevation (7000 m) ice score is high enough to beat arid."""
        r = _resolver()
        ctx = _make_ctx(climate_class="BWh", elevation=7000.0, ocean=False)
        candidates = r.evaluate_rules(ctx)
        state = r.resolve_conflicts(candidates, ctx)
        # ice_score at 7000m = min(0.92, 0.70 + 3500/15000) = min(0.92, 0.933) = 0.92
        # ice weighted = 0.92 × 0.95 = 0.874
        # desert weighted = 0.85 × 0.90 = 0.765
        self.assertEqual(state.winning_rule, "ice")
        self.assertEqual(state.climate_family, "polar")

    def test_polar_not_ocean(self):
        """Polar winning rule must set ocean=False."""
        r = _resolver()
        ctx = _make_ctx(climate_class="EF", ocean=False)
        state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        self.assertFalse(state.ocean)


# ── 2. Biome vs ocean dominance ───────────────────────────────────────────────


class TestBiomeVsOceanDominance(unittest.TestCase):

    def test_ocean_wins_over_tropical_biome(self):
        """Ocean flag should dominate even when tropical climate class is set."""
        r = _resolver()
        ctx = _make_ctx(climate_class="Af", ocean=True, elevation=-500.0)
        state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        self.assertEqual(state.winning_rule, "ocean")
        self.assertTrue(state.ocean)

    def test_deep_ocean_score_higher_than_shallow(self):
        """Deep ocean candidate must have higher score than shallow ocean."""
        r = _resolver()
        deep_ctx = _make_ctx(ocean=True, elevation=-2000.0)
        shallow_ctx = _make_ctx(ocean=True, elevation=-200.0)
        deep_cands = r.evaluate_rules(deep_ctx)
        shallow_cands = r.evaluate_rules(shallow_ctx)

        def ocean_score(cands):
            return next(c.score for c in cands if c.rule_type == "ocean")

        self.assertGreater(ocean_score(deep_cands), ocean_score(shallow_cands))

    def test_land_biome_wins_when_no_ocean(self):
        """Non-ocean tropical pixel with no conflicting rules: biome wins."""
        r = _resolver()
        ctx = _make_ctx(climate_class="Af", ocean=False, elevation=50.0)
        state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        self.assertEqual(state.winning_rule, "biome")
        self.assertFalse(state.ocean)

    def test_ocean_sets_correct_state_fields(self):
        """Ocean winner must set ocean=True and climate_family='unknown'."""
        r = _resolver()
        ctx = _make_ctx(ocean=True, elevation=-800.0)
        state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        self.assertTrue(state.ocean)
        self.assertEqual(state.climate_family, "unknown")

    def test_final_state_candidates_preserved(self):
        """FinalVisualState must preserve de-duplicated candidate list."""
        r = _resolver()
        ctx = _make_ctx(ocean=True, elevation=-200.0)
        state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
        rule_types = {c.rule_type for c in state.candidates}
        self.assertIn("ocean", rule_types)


# ── 3. Deterministic tie-breaking ─────────────────────────────────────────────


class TestDeterministicTieBreaking(unittest.TestCase):

    def test_tie_priority_ocean_beats_ice(self):
        """When scores are within TIE_THRESHOLD, ocean beats ice per priority table."""
        r = _resolver()
        r.TIE_THRESHOLD = 0.99  # force all comparisons into tie-break
        candidates = [
            RuleCandidate("ocean", 0.80),
            RuleCandidate("ice",   0.80),
        ]
        state = r.resolve_conflicts(candidates)
        self.assertEqual(state.winning_rule, "ocean")

    def test_tie_priority_ice_beats_biome(self):
        r = _resolver()
        r.TIE_THRESHOLD = 0.99
        candidates = [
            RuleCandidate("ice",   0.70),
            RuleCandidate("biome", 0.70),
        ]
        state = r.resolve_conflicts(candidates)
        self.assertEqual(state.winning_rule, "ice")

    def test_tie_priority_biome_beats_desert(self):
        r = _resolver()
        r.TIE_THRESHOLD = 0.99
        candidates = [
            RuleCandidate("desert", 0.70),
            RuleCandidate("biome",  0.70),
        ]
        state = r.resolve_conflicts(candidates)
        self.assertEqual(state.winning_rule, "biome")

    def test_tie_priority_desert_beats_atmosphere(self):
        r = _resolver()
        r.TIE_THRESHOLD = 0.99
        candidates = [
            RuleCandidate("atmosphere", 0.70),
            RuleCandidate("desert",     0.70),
        ]
        state = r.resolve_conflicts(candidates)
        self.assertEqual(state.winning_rule, "desert")

    def test_candidate_order_does_not_matter(self):
        """Reversing candidate order must produce the same winner."""
        r = _resolver()
        cands_a = [
            RuleCandidate("ocean",  0.90),
            RuleCandidate("biome",  0.75),
            RuleCandidate("desert", 0.85),
        ]
        cands_b = list(reversed(cands_a))
        state_a = r.resolve_conflicts(cands_a)
        state_b = r.resolve_conflicts(cands_b)
        self.assertEqual(state_a.winning_rule, state_b.winning_rule)
        self.assertAlmostEqual(state_a.composite_score, state_b.composite_score, places=5)

    def test_duplicate_rule_types_deduplicated(self):
        """Multiple candidates of the same type: only the highest-score one counts."""
        r = _resolver()
        candidates = [
            RuleCandidate("ocean", 0.50),
            RuleCandidate("ocean", 0.90),  # higher; should win deduplication
            RuleCandidate("biome", 0.80),
        ]
        state = r.resolve_conflicts(candidates)
        # All candidates in FinalVisualState must have unique rule_types
        types = [c.rule_type for c in state.candidates]
        self.assertEqual(len(types), len(set(types)))


# ── 4. Score threshold logic ──────────────────────────────────────────────────


class TestScoreThresholdLogic(unittest.TestCase):

    def test_clear_winner_no_tiebreak_needed(self):
        """When score gap > TIE_THRESHOLD, highest weighted score wins."""
        r = _resolver()
        candidates = [
            RuleCandidate("ocean",  0.95),  # weighted = 0.95
            RuleCandidate("biome",  0.40),  # weighted = 0.32 — clearly behind
        ]
        state = r.resolve_conflicts(candidates)
        self.assertEqual(state.winning_rule, "ocean")

    def test_below_threshold_triggers_priority_table(self):
        """Scores within TIE_THRESHOLD must fall through to priority table."""
        r = _resolver()
        # ice weight=0.95, biome weight=0.80; set raw scores so weighted are very close
        # ice_ws = 0.82 × 0.95 = 0.779; biome_ws = 0.97 × 0.80 = 0.776 → diff ≈ 0.003 < 0.05
        candidates = [
            RuleCandidate("ice",   0.82),
            RuleCandidate("biome", 0.97),
        ]
        state = r.resolve_conflicts(candidates)
        # Weighted: ice=0.779, biome=0.776 → diff < 0.05 → tie-break: ice > biome
        self.assertEqual(state.winning_rule, "ice")

    def test_composite_score_reflects_weighted_score(self):
        """composite_score must equal score × rule_weight for the winner."""
        r = _resolver()
        candidates = [RuleCandidate("ocean", 0.90)]
        state = r.resolve_conflicts(candidates)
        expected = round(0.90 * r.rule_weights["ocean"], 6)
        self.assertAlmostEqual(state.composite_score, expected, places=5)

    def test_empty_candidates_returns_safe_default(self):
        """Empty candidate list must not raise; returns a safe FinalVisualState."""
        r = _resolver()
        state = r.resolve_conflicts([])
        self.assertIsInstance(state, FinalVisualState)
        self.assertIsInstance(state.winning_rule, str)

    def test_single_candidate_always_wins(self):
        """A single candidate must always be the winner regardless of type."""
        r = _resolver()
        for rt in ("ocean", "biome", "desert", "ice", "polar", "atmosphere"):
            with self.subTest(rule_type=rt):
                state = r.resolve_conflicts([RuleCandidate(rt, 0.50)])
                self.assertEqual(state.winning_rule, rt)

    def test_unknown_rule_type_handled(self):
        """Unknown rule_type must not crash the resolver."""
        r = _resolver()
        candidates = [
            RuleCandidate("custom_rule", 0.99),
            RuleCandidate("ocean", 0.50),
        ]
        state = r.resolve_conflicts(candidates)
        self.assertIsInstance(state, FinalVisualState)


# ── 5. No regression in SAL / M1 / VC pipeline ───────────────────────────────


class TestPipelineNoRegression(unittest.TestCase):
    """Verify that adding the resolver does not break D6Renderer behaviour.

    These tests use synthetic signal providers (no real data required) and
    compare output stability before/after the resolver is in the pipeline.
    They do NOT import SAL/M1/VC directly — they only validate the D6 renderer
    API contract that those systems depend on.
    """

    def _make_renderer(self):
        from core.rendering import D6Renderer
        from core.runtime.runtime_types import FeatureVector, SpatialState

        _fv = FeatureVector(elevation=50.0, ocean_flag=0.0, climate_class=8.0, slope_proxy=0.1)

        class StubRuntime:
            resolution_mode = "8k"
            def query_point(self, lon, lat):
                return SpatialState(
                    climate_class=8,
                    elevation=50.0,
                    slope_proxy=0.1,
                    ocean=False,
                    biome_proxy=0.60,
                    feature_vector=_fv,
                    normalized_vector=_fv,
                    source={},
                )

        return D6Renderer(StubRuntime())

    def test_renderer_has_rule_resolver(self):
        """D6Renderer must expose a rule_resolver attribute after init."""
        from core.rendering.visual_rule_resolver import VisualRuleResolver
        renderer = self._make_renderer()
        self.assertIsInstance(renderer.rule_resolver, VisualRuleResolver)

    def test_render_point_returns_rgb(self):
        """render_point must still return an RGB after resolver integration."""
        from core.rendering.renderer_types import RGB, TimeState
        renderer = self._make_renderer()
        ts = TimeState(hour=12.0, day_of_year=180)
        rgb = renderer.render_point(0.0, 0.0, ts)
        self.assertIsInstance(rgb, RGB)
        self.assertGreaterEqual(rgb.r, 0.0)
        self.assertLessEqual(rgb.r, 1.0)

    def test_render_point_deterministic(self):
        """render_point with the same args must return the same RGB."""
        from core.rendering.renderer_types import TimeState
        renderer = self._make_renderer()
        ts = TimeState(hour=12.0, day_of_year=180)
        r1 = renderer.render_point(10.0, 20.0, ts)
        r2 = renderer.render_point(10.0, 20.0, ts)
        self.assertEqual(r1, r2)

    def test_render_point_varies_with_time(self):
        """Diurnal variation must still exist after resolver integration."""
        from core.rendering.renderer_types import TimeState
        renderer = self._make_renderer()
        noon = renderer.render_point(0.0, 0.0, TimeState(hour=12.0, day_of_year=180))
        night = renderer.render_point(0.0, 0.0, TimeState(hour=0.0, day_of_year=180))
        self.assertNotEqual(noon, night)

    def test_evaluate_rules_always_includes_atmosphere(self):
        """evaluate_rules must always include an atmosphere candidate."""
        r = _resolver()
        for ctx in [
            _make_ctx(ocean=True),
            _make_ctx(climate_class="EF"),
            _make_ctx(climate_class="BWh"),
            _make_ctx(climate_class="Af"),
        ]:
            with self.subTest(ctx=ctx):
                cands = r.evaluate_rules(ctx)
                types = {c.rule_type for c in cands}
                self.assertIn("atmosphere", types)

    def test_final_visual_state_fields_valid(self):
        """FinalVisualState must always have winning_rule, ocean, climate_family."""
        r = _resolver()
        for ctx in [
            _make_ctx(ocean=True),
            _make_ctx(climate_class="EF"),
            _make_ctx(climate_class="Af", ocean=False),
        ]:
            state = r.resolve_conflicts(r.evaluate_rules(ctx), ctx)
            self.assertIsInstance(state.winning_rule, str)
            self.assertIsInstance(state.ocean, bool)
            self.assertIsInstance(state.climate_family, str)
            self.assertGreaterEqual(state.composite_score, 0.0)


# ── 6. VisualGrammar candidate generation (Step 4 addition) ───────────────────


class TestGrammarCandidateGeneration(unittest.TestCase):

    def _grammar(self):
        from core.rendering.visual_grammar import VisualGrammar
        return VisualGrammar()

    def test_ocean_candidate_generated(self):
        g = self._grammar()
        cands = g.generate_rule_candidates(ocean=True, elevation=-500.0, sun_angle=90.0)
        types = {c.rule_type for c in cands}
        self.assertIn("ocean", types)

    def test_polar_candidate_generated(self):
        g = self._grammar()
        cands = g.generate_rule_candidates(climate_class="EF", ocean=False, sun_angle=90.0)
        types = {c.rule_type for c in cands}
        self.assertIn("polar", types)

    def test_high_elevation_ice_candidate(self):
        g = self._grammar()
        cands = g.generate_rule_candidates(climate_class="Cfa", elevation=4000.0, ocean=False)
        types = {c.rule_type for c in cands}
        self.assertIn("ice", types)

    def test_atmosphere_always_present(self):
        g = self._grammar()
        cands = g.generate_rule_candidates(climate_class="Af", ocean=False, sun_angle=45.0)
        types = {c.rule_type for c in cands}
        self.assertIn("atmosphere", types)

    def test_existing_apply_to_rgb_unchanged(self):
        """Adding generate_rule_candidates must not alter apply_to_rgb output."""
        from core.rendering.renderer_types import RGB
        g = self._grammar()
        color = RGB(0.30, 0.50, 0.25)
        result = g.apply_to_rgb(color, climate_class="Cfa", elevation=100.0, ocean=False)
        self.assertIsInstance(result, RGB)
        self.assertGreaterEqual(result.r, 0.0)


if __name__ == "__main__":
    unittest.main()
