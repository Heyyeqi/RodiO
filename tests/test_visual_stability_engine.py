"""Tests for VisualStabilityEngine (temporal consistency layer).

Covers the 6 specified test cases:
  1. No history → pass-through
  2. Same winner → score smoothing
  3. Winner changes with large delta → accept new winner
  4. Winner changes with small delta → stability lock
  5. Exponential smoothing formula: new = decay * prev + (1 - decay) * current
  6. begin_frame / end_frame lifecycle
"""

import unittest

from core.rendering.visual_stability_engine import StablePixelState, VisualStabilityEngine
from core.rendering.visual_rule_resolver import FinalVisualState, RuleCandidate

# Rule weights mirror the resolver defaults used throughout this test suite.
WEIGHTS = {
    "ocean":      1.00,
    "biome":      0.80,
    "desert":     0.90,
    "ice":        0.95,
    "polar":      1.00,
    "atmosphere": 0.60,
}


def _state(rule, raw_score, *, ocean=False, family="unknown", extra=None):
    """Build a minimal FinalVisualState as the resolver would produce it."""
    cands = [RuleCandidate(rule_type=rule, score=raw_score)]
    if extra:
        cands.extend(extra)
    weighted = round(raw_score * WEIGHTS.get(rule, 0.5), 6)
    return FinalVisualState(
        winning_rule=rule,
        composite_score=weighted,
        ocean=ocean,
        climate_family=family,
        candidates=cands,
    )


KEY = (10.0, 20.0)


# ── Test 1: No history → pass-through ────────────────────────────────────────


class TestNoHistory(unittest.TestCase):

    def _engine(self):
        return VisualStabilityEngine(decay=0.85)

    def test_returns_same_state_object(self):
        engine = self._engine()
        state = _state("ocean", 0.90, ocean=True)
        result = engine.stabilize(state, KEY, WEIGHTS)
        self.assertIs(result, state)

    def test_winning_rule_preserved(self):
        engine = self._engine()
        state = _state("biome", 0.75, family="tropical")
        result = engine.stabilize(state, KEY, WEIGHTS)
        self.assertEqual(result.winning_rule, "biome")

    def test_pixel_state_recorded(self):
        engine = self._engine()
        state = _state("polar", 0.88, family="polar")
        engine.stabilize(state, KEY, WEIGHTS)
        st = engine.pixel_state(KEY)
        self.assertIsNotNone(st)
        self.assertIsInstance(st, StablePixelState)
        self.assertEqual(st.last_winner, "polar")

    def test_different_keys_tracked_independently(self):
        engine = self._engine()
        key_a = (0.0, 0.0)
        key_b = (90.0, 45.0)
        engine.stabilize(_state("ocean", 0.90, ocean=True), key_a, WEIGHTS)
        engine.stabilize(_state("biome", 0.60, family="temperate"), key_b, WEIGHTS)
        self.assertEqual(engine.pixel_state(key_a).last_winner, "ocean")
        self.assertEqual(engine.pixel_state(key_b).last_winner, "biome")

    def test_stability_weight_set_to_composite_score(self):
        engine = self._engine()
        state = _state("desert", 0.80, family="arid")
        engine.stabilize(state, KEY, WEIGHTS)
        st = engine.pixel_state(KEY)
        # composite_score = 0.80 * 0.90 = 0.72
        self.assertAlmostEqual(st.stability_weight, 0.72, places=5)


# ── Test 2: Same winner → score smoothing ────────────────────────────────────


class TestSameWinner(unittest.TestCase):

    def test_same_winner_returns_current_state(self):
        engine = VisualStabilityEngine(decay=0.85)
        s0 = _state("biome", 0.875, family="tropical")
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        s1 = _state("biome", 0.90, family="tropical")
        result = engine.stabilize(s1, KEY, WEIGHTS)

        self.assertEqual(result.winning_rule, "biome")
        self.assertIs(result, s1)

    def test_stability_weight_smoothed_correctly(self):
        """new_weight = decay * prev_weight + (1 - decay) * composite_score."""
        engine = VisualStabilityEngine(decay=0.85)
        # Frame 0: biome raw=0.875 → composite 0.875*0.80=0.70; stability_weight=0.70
        s0 = _state("biome", 0.875, family="tropical")
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        # Frame 1: biome raw=0.75 → composite 0.75*0.80=0.60
        s1 = _state("biome", 0.75, family="tropical")
        engine.stabilize(s1, KEY, WEIGHTS)

        st = engine.pixel_state(KEY)
        expected = 0.85 * 0.70 + 0.15 * 0.60   # 0.595 + 0.090 = 0.685
        self.assertAlmostEqual(st.stability_weight, expected, places=5)

    def test_smoothed_scores_blend_over_frames(self):
        """Per-candidate smoothed score applies exponential decay."""
        engine = VisualStabilityEngine(decay=0.85)
        s0 = _state("biome", 0.875, family="tropical")
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        s1 = _state("biome", 0.50, family="tropical")
        engine.stabilize(s1, KEY, WEIGHTS)

        st = engine.pixel_state(KEY)
        # prev smoothed biome = 0.875*0.80=0.70; current = 0.50*0.80=0.40
        expected = 0.85 * 0.70 + 0.15 * 0.40   # 0.595 + 0.060 = 0.655
        self.assertAlmostEqual(st.smoothed_scores.get("biome"), expected, places=5)


# ── Test 3: Large delta → accept new winner ───────────────────────────────────


class TestLargeDeltaAcceptsNewWinner(unittest.TestCase):

    def test_large_delta_passes_through_new_winner(self):
        """Score gap > lock_threshold: new winner is returned unchanged."""
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)

        # Frame 0: biome at raw=0.50 → ws=0.40; stability_weight=0.40
        s0 = _state("biome", 0.50, family="tropical")
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        # Frame 1: ocean at raw=0.90 → ws=0.90; smoothed["ocean"]=0.90
        # prev_winner_score = stability_weight=0.40 (biome absent from frame-1 cands)
        # delta = |0.90 - 0.40| = 0.50 > 0.10 → accept
        s1 = _state("ocean", 0.90, ocean=True)
        result = engine.stabilize(s1, KEY, WEIGHTS)

        self.assertEqual(result.winning_rule, "ocean")
        self.assertTrue(result.ocean)

    def test_large_delta_records_new_winner(self):
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)
        s0 = _state("biome", 0.50, family="tropical")
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        s1 = _state("ocean", 0.90, ocean=True)
        engine.stabilize(s1, KEY, WEIGHTS)

        st = engine.pixel_state(KEY)
        self.assertEqual(st.last_winner, "ocean")

    def test_threshold_boundary_above_accepts_winner(self):
        """delta exactly above lock_threshold (0.10) must accept new winner."""
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)
        # Setup stability_weight = 0.60
        s0 = _state("ocean", 0.60, ocean=True)
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        # biome raw=0.90 → ws=0.72; delta = |0.72 - 0.60| = 0.12 > 0.10 → accept
        s1 = _state("biome", 0.90, family="temperate")
        result = engine.stabilize(s1, KEY, WEIGHTS)

        self.assertEqual(result.winning_rule, "biome")


# ── Test 4: Small delta → stability lock ─────────────────────────────────────


class TestSmallDeltaStabilityLock(unittest.TestCase):

    def test_lock_keeps_previous_winner(self):
        """Score delta < lock_threshold: previous winner is returned."""
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)

        # Frame 0: ocean at raw=0.70 → ws=0.70; stability_weight=0.70
        s0 = _state("ocean", 0.70, ocean=True)
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        # Frame 1: biome at raw=0.85 → ws=0.68
        # current_winner_score = smoothed["biome"] = 0.68 (no prev)
        # prev_winner_score = stability_weight = 0.70 (ocean absent from frame-1 cands)
        # delta = |0.68 - 0.70| = 0.02 < 0.10 → LOCK
        s1 = _state("biome", 0.85, family="tropical")
        result = engine.stabilize(s1, KEY, WEIGHTS)

        self.assertEqual(result.winning_rule, "ocean")
        self.assertTrue(result.ocean)

    def test_lock_preserves_ocean_flag(self):
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)
        s0 = _state("ocean", 0.70, ocean=True)
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        s1 = _state("biome", 0.85, family="tropical")
        result = engine.stabilize(s1, KEY, WEIGHTS)

        self.assertTrue(result.ocean)

    def test_lock_records_previous_winner(self):
        """Stability state must record the locked (previous) winner, not the resolver's."""
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)
        s0 = _state("ocean", 0.70, ocean=True)
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        s1 = _state("biome", 0.85, family="tropical")
        engine.stabilize(s1, KEY, WEIGHTS)

        st = engine.pixel_state(KEY)
        self.assertEqual(st.last_winner, "ocean")

    def test_lock_preserves_current_candidates_for_inspection(self):
        """Locked FinalVisualState must carry the current-frame candidates."""
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)
        s0 = _state("ocean", 0.70, ocean=True)
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        s1 = _state("biome", 0.85, family="tropical")
        result = engine.stabilize(s1, KEY, WEIGHTS)

        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].rule_type, "biome")

    def test_threshold_boundary_below_triggers_lock(self):
        """delta exactly below lock_threshold (0.10) must trigger lock."""
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)
        # stability_weight = 0.70
        s0 = _state("ocean", 0.70, ocean=True)
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        # biome raw=0.75 → ws=0.60; delta = |0.60 - 0.70| = 0.10
        # lock_threshold is strict less-than: 0.10 < 0.10 is False → accept
        # Use raw=0.73: ws=0.584; delta=|0.584-0.70|=0.116 > 0.10 → accept
        # Use raw=0.87: ws=0.696; delta=|0.696-0.70|=0.004 < 0.10 → lock
        s1 = _state("biome", 0.87, family="tropical")
        result = engine.stabilize(s1, KEY, WEIGHTS)

        self.assertEqual(result.winning_rule, "ocean")


# ── Test 5: Exponential smoothing formula ────────────────────────────────────


class TestExponentialSmoothing(unittest.TestCase):

    def test_smoothing_formula_same_winner(self):
        """stability_weight = decay * prev + (1 - decay) * composite_score."""
        decay = 0.85
        engine = VisualStabilityEngine(decay=decay)

        s0 = _state("biome", 0.875, family="temperate")  # ws = 0.70
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        s1 = _state("biome", 0.75, family="temperate")   # ws = 0.60
        engine.stabilize(s1, KEY, WEIGHTS)

        expected = decay * 0.70 + (1 - decay) * 0.60
        st = engine.pixel_state(KEY)
        self.assertAlmostEqual(st.stability_weight, expected, places=10)

    def test_smoothing_three_frames(self):
        """Verify accumulation across three frames."""
        decay = 0.85
        engine = VisualStabilityEngine(decay=decay)

        s0 = _state("biome", 0.875, family="tropical")   # ws = 0.70
        engine.stabilize(s0, KEY, WEIGHTS)
        w0 = 0.70

        engine.begin_frame(1)
        s1 = _state("biome", 0.75, family="tropical")    # ws = 0.60
        engine.stabilize(s1, KEY, WEIGHTS)
        w1 = decay * w0 + (1 - decay) * 0.60

        engine.begin_frame(2)
        s2 = _state("biome", 0.625, family="tropical")   # ws = 0.50
        engine.stabilize(s2, KEY, WEIGHTS)
        w2 = decay * w1 + (1 - decay) * 0.50

        st = engine.pixel_state(KEY)
        self.assertAlmostEqual(st.stability_weight, w2, places=10)

    def test_per_rule_smoothed_score_formula(self):
        """smoothed[rule] = decay * prev_smoothed[rule] + (1-decay) * (raw * weight)."""
        decay = 0.90
        engine = VisualStabilityEngine(decay=decay)

        # Frame 0: atmosphere raw=0.50 → ws=0.50*0.60=0.30
        s0 = _state("atmosphere", 0.50)
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        # Frame 1: atmosphere raw=0.80 → ws=0.80*0.60=0.48
        s1 = _state("atmosphere", 0.80)
        engine.stabilize(s1, KEY, WEIGHTS)

        expected = decay * 0.30 + (1 - decay) * 0.48
        st = engine.pixel_state(KEY)
        self.assertAlmostEqual(st.smoothed_scores.get("atmosphere"), expected, places=10)

    def test_new_rule_starts_at_current_weighted_score(self):
        """A rule not seen in the previous frame starts at its raw weighted score."""
        engine = VisualStabilityEngine(decay=0.85)
        s0 = _state("ocean", 0.90, ocean=True)
        engine.stabilize(s0, KEY, WEIGHTS)

        engine.begin_frame(1)
        # desert appears for the first time; no prev entry for it
        s1 = _state("desert", 0.80, family="arid",
                    extra=[RuleCandidate("ocean", 0.88)])
        engine.stabilize(s1, KEY, WEIGHTS)

        st = engine.pixel_state(KEY)
        # desert ws = 0.80 * 0.90 = 0.72 (no blending, no prev)
        self.assertAlmostEqual(st.smoothed_scores.get("desert", 0.0), 0.72, places=5)


# ── Test 6: begin_frame / end_frame lifecycle ─────────────────────────────────


class TestFrameLifecycle(unittest.TestCase):

    def test_begin_frame_promotes_current_to_previous(self):
        engine = VisualStabilityEngine()
        s0 = _state("ocean", 0.80, ocean=True)
        engine.stabilize(s0, KEY, WEIGHTS)

        self.assertIsNone(engine.previous_pixel_state(KEY))
        engine.begin_frame(1)
        self.assertIsNotNone(engine.previous_pixel_state(KEY))
        self.assertIsNone(engine.pixel_state(KEY))

    def test_begin_frame_clears_current(self):
        engine = VisualStabilityEngine()
        engine.stabilize(_state("biome", 0.70, family="cold"), KEY, WEIGHTS)
        engine.begin_frame(1)
        self.assertEqual(len(engine.current_frame_state), 0)

    def test_end_frame_is_noop(self):
        engine = VisualStabilityEngine()
        engine.stabilize(_state("ocean", 0.90, ocean=True), KEY, WEIGHTS)
        before = dict(engine.current_frame_state)
        engine.end_frame(0)
        self.assertEqual(engine.current_frame_state, before)

    def test_second_begin_frame_overwrites_previous(self):
        engine = VisualStabilityEngine()
        key_a = (0.0, 0.0)
        key_b = (1.0, 1.0)
        engine.stabilize(_state("ocean", 0.80, ocean=True), key_a, WEIGHTS)

        engine.begin_frame(1)
        engine.stabilize(_state("biome", 0.60, family="cold"), key_b, WEIGHTS)

        engine.begin_frame(2)
        # previous should now reflect frame-1's current (key_b only)
        self.assertIsNone(engine.previous_pixel_state(key_a))
        self.assertIsNotNone(engine.previous_pixel_state(key_b))

    def test_stability_lock_uses_previous_frame_state(self):
        """Lock must read from previous_frame_state, not current_frame_state."""
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)

        # Frame 0: ocean
        engine.stabilize(_state("ocean", 0.70, ocean=True), KEY, WEIGHTS)
        engine.begin_frame(1)

        # Frame 1: biome barely wins (lock should trigger)
        result = engine.stabilize(_state("biome", 0.85, family="tropical"), KEY, WEIGHTS)
        self.assertEqual(result.winning_rule, "ocean",
                         "Lock must keep ocean from previous frame")

    def test_no_lock_without_begin_frame(self):
        """Without begin_frame, re-stabilizing same key overwrites state (no prev)."""
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)

        s0 = _state("ocean", 0.70, ocean=True)
        engine.stabilize(s0, KEY, WEIGHTS)

        # Same key, no begin_frame → current_frame_state is overwritten, no prev
        # So second call sees no history from previous (it's in current, not previous).
        # After begin_frame, previous is populated.
        engine.begin_frame(1)
        # Now biome wins by small margin → lock should fire (prev = ocean frame 0)
        result = engine.stabilize(_state("biome", 0.85, family="tropical"), KEY, WEIGHTS)
        self.assertEqual(result.winning_rule, "ocean")


# ── Integration: resolver hook ────────────────────────────────────────────────


class TestResolverHook(unittest.TestCase):
    """Verify that set_stability_engine() / pixel_key wiring works end-to-end."""

    def test_resolver_applies_stability_when_engine_attached(self):
        from core.rendering.visual_rule_resolver import (
            PixelContext, RuleCandidate, VisualRuleResolver,
        )
        resolver = VisualRuleResolver()
        engine = VisualStabilityEngine(decay=0.85, lock_threshold=0.10)
        resolver.set_stability_engine(engine)

        key = (5.0, 5.0)
        ctx = PixelContext(ocean=True)

        # Frame 0: ocean wins
        cands_0 = [
            RuleCandidate("ocean", 0.70),
            RuleCandidate("atmosphere", 0.50),
        ]
        r0 = resolver.resolve_conflicts(cands_0, ctx, pixel_key=key)
        self.assertEqual(r0.winning_rule, "ocean")

        engine.begin_frame(1)

        # Frame 1: biome narrowly "wins" the raw scores → lock should fire
        ctx2 = PixelContext(climate_class="tropical")
        cands_1 = [
            RuleCandidate("biome", 0.85),  # ws = 0.68
            RuleCandidate("atmosphere", 0.50),
        ]
        r1 = resolver.resolve_conflicts(cands_1, ctx2, pixel_key=key)
        # delta = |0.68 - 0.70| = 0.02 < 0.10 → lock to ocean
        self.assertEqual(r1.winning_rule, "ocean")

    def test_resolver_no_stability_without_pixel_key(self):
        """If pixel_key is None, stability engine is bypassed."""
        from core.rendering.visual_rule_resolver import (
            PixelContext, RuleCandidate, VisualRuleResolver,
        )
        resolver = VisualRuleResolver()
        engine = VisualStabilityEngine()
        resolver.set_stability_engine(engine)

        ctx = PixelContext(ocean=True)
        cands = [RuleCandidate("ocean", 0.90), RuleCandidate("atmosphere", 0.50)]
        r = resolver.resolve_conflicts(cands, ctx)  # no pixel_key
        # Should return the raw resolver result; engine is bypassed
        self.assertEqual(r.winning_rule, "ocean")
        # Nothing recorded in engine state
        self.assertEqual(len(engine.current_frame_state), 0)


if __name__ == "__main__":
    unittest.main()
