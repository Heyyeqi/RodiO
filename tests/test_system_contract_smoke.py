"""
System Contract Smoke Tests

Validates the M0 → SAL → M1 → VC → D6 pipeline against the contract layer.

Tests:
  1. SAL contract: winner fields, determinism, ratio ≥ 1
  2. M1 contract: mask shapes, uncertainty bounds
  3. VC contract: gradient coastline, temporal stability bounds
  4. D6 contract: VC-only input, deterministic RGB output
  5. ContractGuard: end-to-end pipeline with full guard
  6. SAL double-call detection
  7. System invariants: all five checks pass

All tests use synthetic signal providers — no real data files required.
"""

import unittest
import numpy as np

from core.sal import SemanticArbitrator
from core.m1 import M1Pipeline, TileBBox
from core.vc import VisualConsistencyEngine
from core.contract import ContractGuard, SALContractError, M1ContractError, VCContractError
from core.contract.d6_contract import D6Contract, D6ContractError
from core.contract.sal_contract import SALContract
from core.contract.m1_contract import M1Contract
from core.contract.vc_contract import VCContract


# ---------------------------------------------------------------------------
# Synthetic signal providers
# ---------------------------------------------------------------------------

def _ocean_provider(lon, lat):
    return dict(
        dem_signal="ocean",      dem_confidence=0.90,
        climate_signal="ocean",  climate_confidence=0.85,
        ocean_signal="ocean",    ocean_confidence=0.95,
        landcover_signal="ocean", landcover_confidence=0.80,
    )


def _land_provider(lon, lat):
    return dict(
        dem_signal="land",       dem_confidence=0.85,
        climate_signal="forest", climate_confidence=0.80,
        ocean_signal=None,       ocean_confidence=0.50,
        landcover_signal="forest", landcover_confidence=0.75,
    )


def _mixed_provider(lon, lat):
    return _ocean_provider(lon, lat) if lon < 0 else _land_provider(lon, lat)


def _make_small_tile() -> TileBBox:
    return TileBBox(lon_min=-10, lon_max=10, lat_min=-5, lat_max=5)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestSALContract(unittest.TestCase):

    def setUp(self):
        self.sal = SemanticArbitrator()
        self.contract = SALContract()

    def test_ocean_result_passes(self):
        r = self.sal.resolve(
            dem_signal="ocean", climate_signal="ocean",
            ocean_signal="ocean", landcover_signal=None)
        self.contract.validate(r)  # must not raise

    def test_land_result_passes(self):
        r = self.sal.resolve(
            dem_signal="land", climate_signal="forest",
            ocean_signal=None, landcover_signal="forest")
        self.contract.validate(r)

    def test_winner_ratio_gte_1(self):
        r = self.sal.resolve(
            dem_signal="ice", climate_signal="ice",
            ocean_signal="ocean", landcover_signal=None)
        self.assertGreaterEqual(r.winner_ratio, 1.0 - 1e-6)

    def test_winner_class_is_argmax(self):
        r = self.sal.resolve(
            dem_signal="desert", climate_signal="desert",
            ocean_signal="land", landcover_signal="desert")
        argmax = max(r.probability_map, key=lambda k: r.probability_map[k])
        self.assertEqual(r.winner_class, argmax)

    def test_determinism_same_input_same_output(self):
        kwargs = dict(dem_signal="ocean", dem_confidence=0.9,
                      climate_signal="ocean", climate_confidence=0.8,
                      ocean_signal="ocean", ocean_confidence=0.95,
                      landcover_signal="land", landcover_confidence=0.4)
        r1 = self.sal.resolve(**kwargs)
        r2 = self.sal.resolve(**kwargs)
        self.assertEqual(r1.final_class, r2.final_class)
        self.assertAlmostEqual(r1.winner_margin, r2.winner_margin, places=9)
        self.assertAlmostEqual(r1.winner_ratio, r2.winner_ratio, places=9)

    def test_winner_margin_in_range(self):
        r = self.sal.resolve(
            dem_signal="ocean", climate_signal="land",
            ocean_signal="ocean", landcover_signal="land")
        self.assertGreaterEqual(r.winner_margin, 0.0)
        self.assertLessEqual(r.winner_margin, 1.0)

    def test_confidence_in_range(self):
        r = self.sal.resolve(dem_signal="ocean", climate_signal="ocean",
                             ocean_signal=None, landcover_signal=None)
        self.assertGreaterEqual(r.confidence_score, 0.0)
        self.assertLessEqual(r.confidence_score, 1.0)


class TestM1Contract(unittest.TestCase):

    def setUp(self):
        self.contract = M1Contract()
        self.pipeline = M1Pipeline(signal_provider=_ocean_provider, tile_px_size=4)

    def test_ocean_tile_passes(self):
        tile = self.pipeline.run_tile(_make_small_tile())
        self.contract.validate(tile)

    def test_mixed_tile_passes(self):
        pipeline = M1Pipeline(signal_provider=_mixed_provider, tile_px_size=6)
        tile = pipeline.run_tile(_make_small_tile())
        self.contract.validate(tile)

    def test_shapes_consistent(self):
        tile = self.pipeline.run_tile(_make_small_tile())
        shapes = {
            "ocean": tile.ocean_mask.shape,
            "land":  tile.land_mask.shape,
            "biome": tile.biome_mask.shape,
            "unc":   tile.uncertainty_mask.shape,
        }
        self.assertEqual(len(set(shapes.values())), 1, f"Inconsistent shapes: {shapes}")

    def test_uncertainty_bounds(self):
        tile = self.pipeline.run_tile(_make_small_tile())
        unc = tile.uncertainty_mask.astype(np.float32)
        self.assertGreaterEqual(float(unc.min()), 0.0)
        self.assertLessEqual(float(unc.max()), 1.0)

    def test_ocean_land_sum_le_1(self):
        tile = self.pipeline.run_tile(_make_small_tile())
        total = tile.ocean_fraction() + tile.land_fraction()
        self.assertLessEqual(total, 1.0 + 1e-6)


class TestVCContract(unittest.TestCase):

    def setUp(self):
        self.contract = VCContract()
        pipeline = M1Pipeline(signal_provider=_mixed_provider, tile_px_size=8)
        self.tile = pipeline.run_tile(_make_small_tile())
        self.vc = VisualConsistencyEngine()

    def test_vc_context_passes(self):
        ctx = self.vc.process(self.tile)
        self.contract.validate(ctx)

    def test_coastline_is_gradient_not_binary(self):
        ctx = self.vc.process(self.tile)
        grad = ctx.coastline_gradient_field.astype(np.float32)
        lo, hi = float(grad.min()), float(grad.max())
        # If range is meaningful, must have transition values
        if hi - lo > 0.05:
            mid = grad[(grad > 0.05) & (grad < 0.95)]
            self.assertGreater(len(mid), 0, "coastline_gradient_field is binary — no transition values")

    def test_temporal_stability_in_range(self):
        ctx = self.vc.process(self.tile)
        stab = ctx.temporal_stability_field.astype(np.float32)
        self.assertGreaterEqual(float(stab.min()), 0.0 - 1e-4)
        self.assertLessEqual(float(stab.max()), 1.0 + 1e-4)

    def test_all_required_fields_present(self):
        ctx = self.vc.process(self.tile)
        for field in VCContract.REQUIRED_FIELDS:
            self.assertTrue(hasattr(ctx, field), f"Missing field: {field}")
            self.assertIsNotNone(getattr(ctx, field))

    def test_shapes_consistent(self):
        ctx = self.vc.process(self.tile)
        H, W = ctx.shape
        for field in ("biome_blend_field", "coastline_gradient_field",
                      "temporal_stability_field", "uncertainty_modulation_field"):
            self.assertEqual(getattr(ctx, field).shape, (H, W), f"Shape mismatch: {field}")
        self.assertEqual(ctx.base_color_field.shape, (H, W, 3))


class TestD6Contract(unittest.TestCase):

    def setUp(self):
        pipeline = M1Pipeline(signal_provider=_ocean_provider, tile_px_size=4)
        tile = pipeline.run_tile(TileBBox(lon_min=0, lon_max=10, lat_min=0, lat_max=10))
        vc = VisualConsistencyEngine()
        self.ctx = vc.process(tile)
        self.d6 = D6Contract()

    def test_render_from_vc_succeeds(self):
        frame = self.d6.render_from_vc(self.ctx)
        self.assertIsInstance(frame, np.ndarray)
        self.assertEqual(frame.ndim, 3)
        self.assertEqual(frame.shape[2], 3)
        self.assertEqual(frame.dtype, np.uint8)

    def test_render_is_deterministic(self):
        frame1 = self.d6.render_from_vc(self.ctx)
        frame2 = self.d6.render_from_vc(self.ctx)
        np.testing.assert_array_equal(frame1, frame2)

    def test_forbidden_input_types_rejected(self):
        from core.sal.sal_types import ArbitrationResult

        sal = SemanticArbitrator()
        sal_result = sal.resolve(dem_signal="ocean", climate_signal="ocean",
                                 ocean_signal="ocean", landcover_signal=None)
        with self.assertRaises(D6ContractError):
            self.d6.validate_input(sal_result)

    def test_none_input_rejected(self):
        with self.assertRaises(D6ContractError):
            self.d6.validate_input(None)

    def test_output_shape_validated(self):
        bad_frame = np.zeros((4, 4, 4), dtype=np.uint8)  # shape (H, W, 4) is invalid
        with self.assertRaises(D6ContractError):
            self.d6.validate_output(bad_frame)

    def test_output_dtype_validated(self):
        bad_frame = np.zeros((4, 4, 3), dtype=np.float32)  # float32 is invalid
        with self.assertRaises(D6ContractError):
            self.d6.validate_output(bad_frame)


class TestContractGuardEndToEnd(unittest.TestCase):

    def test_full_pipeline_with_guard(self):
        guard = ContractGuard(strict_sal_cache=False)

        sal = SemanticArbitrator()
        sal_result = sal.resolve(
            dem_signal="ocean", climate_signal="ocean",
            ocean_signal="ocean", landcover_signal=None)
        guard.validate_sal(sal_result)

        pipeline = M1Pipeline(signal_provider=_mixed_provider, tile_px_size=6)
        tile = pipeline.run_tile(_make_small_tile())
        guard.validate_m1(tile)

        vc = VisualConsistencyEngine()
        ctx = vc.process(tile)
        guard.validate_vc(ctx)

        frame = guard.render_d6_from_vc(ctx)
        guard.validate_d6(frame)

        self.assertEqual(frame.dtype, np.uint8)
        self.assertEqual(frame.ndim, 3)

    def test_sal_double_call_detection(self):
        guard = ContractGuard(strict_sal_cache=True)
        sal = SemanticArbitrator()
        result = sal.resolve(dem_signal="land", climate_signal="forest",
                             ocean_signal=None, landcover_signal="forest")

        key = (10.0, 20.0)
        guard.validate_sal(result, input_key=key)

        from core.contract.contract_guard import ContractViolation
        with self.assertRaises(ContractViolation):
            guard.validate_sal(result, input_key=key)

    def test_guard_reset_sal_cache(self):
        guard = ContractGuard(strict_sal_cache=True)
        sal = SemanticArbitrator()
        result = sal.resolve(dem_signal="ocean", climate_signal="ocean",
                             ocean_signal="ocean", landcover_signal=None)
        key = (5.0, 5.0)
        guard.validate_sal(result, input_key=key)
        guard.reset_sal_cache()
        guard.validate_sal(result, input_key=key)  # must not raise after reset


class TestSystemInvariants(unittest.TestCase):

    def test_deterministic_pipeline(self):
        from core.contract.system_invariants import deterministic_pipeline_test
        result = deterministic_pipeline_test()
        self.assertTrue(result["passed"], result["details"])

    def test_sal_consistency(self):
        from core.contract.system_invariants import sal_consistency_check
        result = sal_consistency_check()
        self.assertTrue(result["passed"], result["details"])

    def test_m1_alignment(self):
        from core.contract.system_invariants import m1_alignment_check
        result = m1_alignment_check()
        self.assertTrue(result["passed"], result["details"])

    def test_vc_temporal_stability(self):
        from core.contract.system_invariants import vc_temporal_stability_check
        result = vc_temporal_stability_check()
        self.assertTrue(result["passed"], result["details"])

    def test_d6_determinism(self):
        from core.contract.system_invariants import d6_determinism_check
        result = d6_determinism_check()
        self.assertTrue(result["passed"], result["details"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
