"""
Stage 7 — Earth visual grammar tests.

Visual grammar changes only expression: palette, tone, bathymetry colour, and
time balance. It must not alter SAL / M1 / VC semantic outputs.
"""

from __future__ import annotations

import unittest

import numpy as np

from core.m1 import M1Pipeline, TileBBox
from core.rendering import D6Renderer, RGB, TimeState, VisualGrammar
from core.runtime.runtime_types import FeatureVector, SpatialState
from core.sal import SemanticArbitrator
from core.signal.providers.synthetic import SyntheticProvider
from core.vc import VisualConsistencyEngine


TILE = TileBBox(lon_min=34.0, lon_max=37.0, lat_min=30.0, lat_max=33.0)


class FixedRuntime:
    resolution_mode = "21k"

    def __init__(self, state: SpatialState):
        self.state = state

    def query_point(self, lon, lat):
        return self.state


def _state(elevation: float, ocean: bool, climate_class: int | None) -> SpatialState:
    fv = FeatureVector(
        elevation=float(elevation),
        ocean_flag=1.0 if ocean else 0.0,
        climate_class=float(climate_class or 0),
        slope_proxy=0.0,
    )
    return SpatialState(
        elevation=float(elevation),
        ocean=ocean,
        climate_class=climate_class,
        biome_proxy=0.5,
        slope_proxy=0.0,
        feature_vector=fv,
        normalized_vector=fv,
        source={"test": "stage7_visual_grammar"},
    )


class TestVisualGrammarCore(unittest.TestCase):
    def test_climate_mapping_correctness(self):
        grammar = VisualGrammar()
        base = RGB(0.36, 0.36, 0.36)

        tropical = grammar.climate_color(1, base)
        arid = grammar.climate_color(5, base)
        temperate = grammar.climate_color(10, base)
        polar = grammar.climate_color(30, base)

        self.assertGreater(tropical.g, tropical.r)
        self.assertGreater(arid.r, arid.b)
        self.assertGreaterEqual(temperate.g, temperate.r)
        self.assertGreater(polar.b, polar.r)

    def test_elevation_tone_monotonicity(self):
        grammar = VisualGrammar()
        low = grammar.elevation_tone(0)
        mid = grammar.elevation_tone(1500)
        high = grammar.elevation_tone(4500)

        self.assertLess(low, mid)
        self.assertLess(mid, high)
        self.assertAlmostEqual(high, 1.0)

    def test_ocean_gradient_continuity(self):
        grammar = VisualGrammar()
        shallow = grammar.ocean_gradient(-50)
        mid = grammar.ocean_gradient(-1000)
        deep = grammar.ocean_gradient(-6000)

        self.assertGreater(shallow.g, deep.g)
        self.assertGreater(shallow.luminance(), mid.luminance())
        self.assertLess(deep.luminance(), mid.luminance())

        near_a = grammar.ocean_gradient(-990)
        near_b = grammar.ocean_gradient(-1010)
        delta = max(abs(a - b) for a, b in zip((near_a.r, near_a.g, near_a.b), (near_b.r, near_b.g, near_b.b)))
        self.assertLess(delta, 0.02)

    def test_time_shift_determinism(self):
        grammar = VisualGrammar()
        base = RGB(0.4, 0.42, 0.45)

        noon_a = grammar.time_shift(base, 90.0)
        noon_b = grammar.time_shift(base, 90.0)
        sunset = grammar.time_shift(base, 0.0)
        night = grammar.time_shift(base, -45.0)

        self.assertEqual(noon_a, noon_b)
        self.assertGreater(sunset.r - sunset.b, noon_a.r - noon_a.b)
        self.assertGreater(night.b, night.r)

    def test_texture_time_shift_is_deterministic(self):
        grammar = VisualGrammar()
        texture = np.arange(4 * 8 * 3, dtype=np.uint8).reshape(4, 8, 3)

        a = grammar.apply_to_texture(texture, sun_angle=-45.0)
        b = grammar.apply_to_texture(texture, sun_angle=-45.0)
        noon = grammar.apply_to_texture(texture, sun_angle=90.0)

        self.assertTrue(np.array_equal(a, b))
        self.assertTrue(np.array_equal(noon, texture))
        self.assertFalse(np.array_equal(a, texture))


class TestD6VisualGrammarIntegration(unittest.TestCase):
    def test_same_data_different_time_expression(self):
        renderer = D6Renderer(FixedRuntime(_state(50.0, False, 5)), resolution_mode="21k")

        noon = renderer.render_point(35.5, 31.5, TimeState(hour=12.0, day_of_year=180))
        sunset = renderer.render_point(35.5, 31.5, TimeState(hour=18.0, day_of_year=180))
        night = renderer.render_point(35.5, 31.5, TimeState(hour=0.0, day_of_year=180))

        self.assertNotEqual(noon.to_uint8(), sunset.to_uint8())
        self.assertNotEqual(noon.to_uint8(), night.to_uint8())
        self.assertGreater(sunset.r - sunset.b, noon.r - noon.b)

    def test_texture_bake_applies_visual_grammar_after_bake(self):
        base = np.full((4, 8, 3), 96, dtype=np.uint8)
        topo = np.full((4, 8, 3), 128, dtype=np.uint8)
        renderer = D6Renderer(FixedRuntime(_state(0.0, False, 10)), resolution_mode="21k")

        noon = renderer.render_window(
            (34.0, 30.0, 37.0, 33.0),
            TimeState(hour=12.0),
            texture_bake=True,
            bmng_base=base,
            bmng_topo=topo,
        )
        night = renderer.render_window(
            (34.0, 30.0, 37.0, 33.0),
            TimeState(hour=0.0),
            texture_bake=True,
            bmng_base=base,
            bmng_topo=topo,
        )

        self.assertIn("visual_grammar", noon)
        self.assertEqual(noon["visual_grammar"]["sun_angle"], 90.0)
        self.assertTrue(np.array_equal(noon["base_texture"], base))
        self.assertFalse(np.array_equal(night["base_texture"], base))


class TestNoSemanticLayerDrift(unittest.TestCase):
    def test_no_change_in_sal_m1_vc_outputs(self):
        provider = SyntheticProvider()
        sal_before = SemanticArbitrator().resolve(**provider(35.5, 31.5))
        tile_before = M1Pipeline(signal_provider=provider, tile_px_size=4).run_tile(TILE)
        vc_before = VisualConsistencyEngine().process(tile_before)

        grammar = VisualGrammar()
        _ = grammar.apply_to_rgb(RGB(0.4, 0.4, 0.4), climate_class=5, elevation=50.0, sun_angle=0.0)

        sal_after = SemanticArbitrator().resolve(**provider(35.5, 31.5))
        tile_after = M1Pipeline(signal_provider=provider, tile_px_size=4).run_tile(TILE)
        vc_after = VisualConsistencyEngine().process(tile_after)

        self.assertAlmostEqual(sal_before.winner_margin, sal_after.winner_margin, places=9)
        self.assertTrue(np.array_equal(tile_before.ocean_mask, tile_after.ocean_mask))
        self.assertTrue(np.array_equal(tile_before.land_mask, tile_after.land_mask))
        self.assertTrue(np.array_equal(vc_before.coastline_gradient_field, vc_after.coastline_gradient_field))


if __name__ == "__main__":
    unittest.main()
