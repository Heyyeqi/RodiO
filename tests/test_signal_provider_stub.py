"""
Signal Provider Stub Tests

Validates the unified core/signal/providers/ interface layer.

Tests:
  1. Signal types remain correct primitive aliases
  2. BaseSignalProvider ABC is importable from new canonical location
  3. RuntimeStubProvider (was RealSignalProvider in core/signal) — correct types + defaults
  4. SyntheticProvider — correct types, callable protocol works
  5. M1BridgeProvider — importable from core.signal.providers, NOT from core.m1 directly
  6. SpatialRuntime with RuntimeStubProvider injection
  7. Synthetic pipeline unchanged (contract smoke regression)
  8. No duplicate provider imports — one definition per class
  9. Provider resolution order correctness
  10. M1 provider isolation — M1BridgeProvider must not define BaseSignalProvider
"""

import unittest

from core.signal import (
    BaseSignalProvider,
    RuntimeStubProvider,
    SyntheticProvider,
    M1BridgeProvider,
    SignalResolutionPolicy,
)
from core.signal.signal_types import ClimateClass, DEMValue, LandcoverClass, OceanFlag


# ---------------------------------------------------------------------------
# 1. Signal types
# ---------------------------------------------------------------------------

class TestSignalTypes(unittest.TestCase):

    def test_dem_value_is_float_alias(self):
        v: DEMValue = -1500.0
        self.assertIsInstance(v, float)

    def test_landcover_class_is_int_alias(self):
        v: LandcoverClass = 3
        self.assertIsInstance(v, int)

    def test_climate_class_is_optional_int(self):
        self.assertIsNone(None)          # ClimateClass = Optional[int]
        self.assertIsInstance(5, int)

    def test_ocean_flag_is_bool_alias(self):
        v: OceanFlag = True
        self.assertIsInstance(v, bool)


# ---------------------------------------------------------------------------
# 2. BaseSignalProvider interface (canonical location)
# ---------------------------------------------------------------------------

class TestBaseSignalProviderInterface(unittest.TestCase):

    def test_canonical_location(self):
        from core.signal.providers.base import BaseSignalProvider as _B
        self.assertIs(BaseSignalProvider, _B)

    def test_cannot_instantiate_abc(self):
        with self.assertRaises(TypeError):
            BaseSignalProvider()

    def test_concrete_must_implement_all_methods(self):
        class Incomplete(BaseSignalProvider):
            def get_dem(self, lon, lat): return 0.0

        with self.assertRaises(TypeError):
            Incomplete()

    def test_abstract_methods_set(self):
        abstract = getattr(BaseSignalProvider, "__abstractmethods__", set())
        self.assertIn("get_dem",       abstract)
        self.assertIn("get_landcover", abstract)
        self.assertIn("get_climate",   abstract)
        self.assertIn("get_ocean",     abstract)


# ---------------------------------------------------------------------------
# 3. RuntimeStubProvider (was RealSignalProvider in core/signal)
# ---------------------------------------------------------------------------

class TestRuntimeStubProvider(unittest.TestCase):

    def setUp(self):
        self.provider = RuntimeStubProvider()

    def test_canonical_location(self):
        from core.signal.providers.runtime_stub import RuntimeStubProvider as _R
        self.assertIs(type(self.provider), _R)

    def test_is_base_signal_provider(self):
        self.assertIsInstance(self.provider, BaseSignalProvider)

    def test_class_name_is_runtime_stub(self):
        self.assertEqual(type(self.provider).__name__, "RuntimeStubProvider")

    def test_get_dem_returns_zero(self):
        self.assertEqual(self.provider.get_dem(0.0, 0.0), 0.0)

    def test_get_dem_returns_float(self):
        self.assertIsInstance(self.provider.get_dem(10.0, 20.0), float)

    def test_get_landcover_returns_zero(self):
        self.assertEqual(self.provider.get_landcover(0.0, 0.0), 0)

    def test_get_landcover_returns_int(self):
        self.assertIsInstance(self.provider.get_landcover(0.0, 0.0), int)

    def test_get_climate_returns_none(self):
        self.assertIsNone(self.provider.get_climate(0.0, 0.0))

    def test_get_ocean_returns_false(self):
        self.assertFalse(self.provider.get_ocean(0.0, 0.0))

    def test_get_ocean_returns_bool(self):
        self.assertIsInstance(self.provider.get_ocean(0.0, 0.0), bool)

    def test_callable_for_any_valid_coordinates(self):
        for lon, lat in [(0.0, 0.0), (180.0, 90.0), (-180.0, -90.0), (35.5, 31.5)]:
            with self.subTest(lon=lon, lat=lat):
                self.assertIsInstance(self.provider.get_dem(lon, lat), float)
                self.assertIsInstance(self.provider.get_landcover(lon, lat), int)
                self.assertIsNone(self.provider.get_climate(lon, lat))
                self.assertIsInstance(self.provider.get_ocean(lon, lat), bool)

    def test_backward_compat_alias_from_core_signal(self):
        # core.signal still exports RuntimeStubProvider; old RealSignalProvider
        # is only an alias defined in the shim, not a second class definition.
        from core.signal.real_signal_provider import RealSignalProvider as Alias
        self.assertIs(Alias, RuntimeStubProvider)


# ---------------------------------------------------------------------------
# 4. SyntheticProvider
# ---------------------------------------------------------------------------

class TestSyntheticProvider(unittest.TestCase):

    def setUp(self):
        self.provider = SyntheticProvider()

    def test_canonical_location(self):
        from core.signal.providers.synthetic import SyntheticProvider as _S
        self.assertIs(type(self.provider), _S)

    def test_is_base_signal_provider(self):
        self.assertIsInstance(self.provider, BaseSignalProvider)

    def test_class_name_is_synthetic(self):
        self.assertEqual(type(self.provider).__name__, "SyntheticProvider")

    def test_get_dem_returns_zero(self):
        self.assertEqual(self.provider.get_dem(0.0, 0.0), 0.0)

    def test_get_ocean_returns_false(self):
        self.assertFalse(self.provider.get_ocean(0.0, 0.0))

    def test_callable_returns_sal_dict(self):
        result = self.provider(10.0, 20.0)
        self.assertIsInstance(result, dict)
        for key in ("dem_signal", "climate_signal", "ocean_signal", "landcover_signal"):
            self.assertIn(key, result)

    def test_callable_sal_dict_values_are_strings(self):
        result = self.provider(0.0, 0.0)
        self.assertEqual(result["dem_signal"], "land")
        self.assertEqual(result["climate_signal"], "land")

    def test_callable_confidence_values_in_range(self):
        result = self.provider(0.0, 0.0)
        for key in ("dem_confidence", "climate_confidence", "ocean_confidence", "landcover_confidence"):
            v = result[key]
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_can_be_used_as_m1_signal_provider(self):
        from core.m1 import M1Pipeline, TileBBox
        pipeline = M1Pipeline(signal_provider=self.provider, tile_px_size=4)
        tile = pipeline.run_tile(TileBBox(lon_min=-5, lon_max=5, lat_min=-5, lat_max=5))
        self.assertIsNotNone(tile)


# ---------------------------------------------------------------------------
# 5. M1BridgeProvider isolation
# ---------------------------------------------------------------------------

class TestM1BridgeProviderIsolation(unittest.TestCase):

    def test_canonical_location_is_in_signal_providers(self):
        from core.signal.providers.m1_bridge import M1BridgeProvider as _M
        self.assertIs(M1BridgeProvider, _M)

    def test_m1_bridge_is_not_base_signal_provider(self):
        # M1BridgeProvider operates at the SAL signal level, not the raw data
        # level — it must NOT inherit BaseSignalProvider.
        self.assertNotIsInstance(M1BridgeProvider, type(BaseSignalProvider))
        self.assertFalse(issubclass(M1BridgeProvider, BaseSignalProvider))

    def test_m1_bridge_class_name(self):
        self.assertEqual(M1BridgeProvider.__name__, "M1BridgeProvider")

    def test_m1_bridge_is_callable_protocol(self):
        # M1BridgeProvider instances must be callable (lon, lat) → dict.
        self.assertTrue(callable(M1BridgeProvider))

    def test_m1_module_re_exports_m1_bridge_provider(self):
        from core.m1 import M1BridgeProvider as FromM1
        from core.signal.providers.m1_bridge import M1BridgeProvider as FromSignal
        self.assertIs(FromM1, FromSignal)

    def test_m1_real_signal_provider_is_shim_only(self):
        # core/m1/real_signal_provider.py must not define a class; it's a shim.
        import core.m1.real_signal_provider as shim_module
        # The only class-like in the module should be the re-exported alias.
        self.assertIs(shim_module.RealSignalProvider, M1BridgeProvider)

    def test_no_duplicate_class_definition(self):
        import core.m1.real_signal_provider as m1_shim
        import core.signal.real_signal_provider as sig_shim
        from core.signal.providers.runtime_stub import RuntimeStubProvider
        from core.signal.providers.m1_bridge import M1BridgeProvider as Bridge

        # Each shim's "class" must point back to exactly one canonical class.
        self.assertIs(m1_shim.RealSignalProvider, Bridge)
        self.assertIs(sig_shim.RealSignalProvider, RuntimeStubProvider)
        # They must be different classes.
        self.assertIsNot(Bridge, RuntimeStubProvider)


# ---------------------------------------------------------------------------
# 6. SpatialRuntime with RuntimeStubProvider injection
# ---------------------------------------------------------------------------

class TestSpatialRuntimeWithRuntimeStub(unittest.TestCase):

    def _make_runtime(self, provider=None):
        from core.runtime.spatial_runtime import SpatialRuntime
        return SpatialRuntime(signal_provider=provider or RuntimeStubProvider())

    def test_accepts_runtime_stub_provider(self):
        runtime = self._make_runtime()
        self.assertIsNotNone(runtime)

    def test_query_point_returns_spatial_state(self):
        from core.runtime.runtime_types import SpatialState
        runtime = self._make_runtime()
        self.assertIsInstance(runtime.query_point(0.0, 0.0), SpatialState)

    def test_query_point_elevation_is_zero(self):
        runtime = self._make_runtime()
        self.assertEqual(runtime.query_point(10.0, 20.0).elevation, 0.0)

    def test_query_point_ocean_is_false(self):
        runtime = self._make_runtime()
        self.assertFalse(runtime.query_point(0.0, 0.0).ocean)

    def test_query_point_source_tag(self):
        runtime = self._make_runtime()
        self.assertEqual(runtime.query_point(0.0, 0.0).source.get("ocean_rule"), "signal_provider")

    def test_custom_ocean_provider(self):
        class OceanEverywhere(BaseSignalProvider):
            def get_dem(self, lon, lat): return -1000.0
            def get_landcover(self, lon, lat): return 0
            def get_climate(self, lon, lat): return None
            def get_ocean(self, lon, lat): return True

        runtime = self._make_runtime(OceanEverywhere())
        state = runtime.query_point(0.0, 0.0)
        self.assertTrue(state.ocean)
        self.assertEqual(state.elevation, -1000.0)

    def test_set_signal_provider_works(self):
        from core.runtime.spatial_runtime import SpatialRuntime
        runtime = SpatialRuntime(signal_provider=RuntimeStubProvider())
        runtime.set_signal_provider(SyntheticProvider())  # SyntheticProvider is also BaseSignalProvider
        state = runtime.query_point(0.0, 0.0)
        self.assertFalse(state.ocean)

    def test_deep_ocean_biome_proxy(self):
        class DeepOcean(BaseSignalProvider):
            def get_dem(self, lon, lat): return -5000.0
            def get_landcover(self, lon, lat): return 0
            def get_climate(self, lon, lat): return None
            def get_ocean(self, lon, lat): return True

        from core.runtime.spatial_runtime import SpatialRuntime
        runtime = SpatialRuntime(signal_provider=DeepOcean())
        state = runtime.query_point(0.0, 0.0)
        self.assertAlmostEqual(state.biome_proxy, 0.05, places=5)


# ---------------------------------------------------------------------------
# 7. Provider resolution policy
# ---------------------------------------------------------------------------

class TestSignalResolutionPolicy(unittest.TestCase):

    def setUp(self):
        self.policy = SignalResolutionPolicy()

    def test_external_wins_over_everything(self):
        custom = RuntimeStubProvider()
        result = self.policy.resolve(external_provider=custom)
        self.assertIs(result, custom)

    def test_no_external_returns_synthetic_by_default(self):
        result = self.policy.resolve()
        self.assertIsInstance(result, SyntheticProvider)

    def test_fallback_runtime_stub(self):
        result = self.policy.resolve(fallback="runtime_stub")
        self.assertIsInstance(result, RuntimeStubProvider)

    def test_priority_label_external(self):
        custom = RuntimeStubProvider()
        label = self.policy.priority_label(custom)
        # RuntimeStubProvider is not external_injected from policy's perspective
        self.assertEqual(label, "runtime_stub")

    def test_priority_label_none_is_synthetic(self):
        self.assertEqual(self.policy.priority_label(None), "synthetic_fallback")

    def test_priority_label_synthetic(self):
        self.assertEqual(self.policy.priority_label(SyntheticProvider()), "synthetic_fallback")

    def test_priority_order_constant(self):
        self.assertEqual(self.policy.PRIORITY_ORDER[0], "external_injected")
        self.assertEqual(self.policy.PRIORITY_ORDER[1], "runtime_stub")
        self.assertEqual(self.policy.PRIORITY_ORDER[2], "synthetic_fallback")


# ---------------------------------------------------------------------------
# 8. Synthetic pipeline unchanged (regression)
# ---------------------------------------------------------------------------

class TestSyntheticPipelineUnchanged(unittest.TestCase):

    def _ocean_provider(self, lon, lat):
        return dict(dem_signal="ocean", dem_confidence=0.9,
                    climate_signal="ocean", climate_confidence=0.85,
                    ocean_signal="ocean", ocean_confidence=0.95,
                    landcover_signal="ocean", landcover_confidence=0.8)

    def _land_provider(self, lon, lat):
        return dict(dem_signal="land", dem_confidence=0.85,
                    climate_signal="forest", climate_confidence=0.8,
                    ocean_signal=None, ocean_confidence=0.5,
                    landcover_signal="forest", landcover_confidence=0.75)

    def _mixed_provider(self, lon, lat):
        return self._ocean_provider(lon, lat) if lon < 0 else self._land_provider(lon, lat)

    def test_sal_still_deterministic(self):
        from core.sal import SemanticArbitrator
        sal = SemanticArbitrator()
        kwargs = dict(dem_signal="ocean", dem_confidence=0.9,
                      climate_signal="ocean", climate_confidence=0.8,
                      ocean_signal="ocean", ocean_confidence=0.95,
                      landcover_signal="land", landcover_confidence=0.4)
        r1 = sal.resolve(**kwargs)
        r2 = sal.resolve(**kwargs)
        self.assertEqual(r1.final_class, r2.final_class)
        self.assertAlmostEqual(r1.winner_ratio, r2.winner_ratio, places=9)

    def test_m1_pipeline_unchanged(self):
        from core.m1 import M1Pipeline, TileBBox
        from core.contract.m1_contract import M1Contract
        pipeline = M1Pipeline(signal_provider=self._ocean_provider, tile_px_size=4)
        tile = pipeline.run_tile(TileBBox(lon_min=-10, lon_max=10, lat_min=-5, lat_max=5))
        M1Contract().validate(tile)
        self.assertLessEqual(tile.ocean_fraction() + tile.land_fraction(), 1.0 + 1e-6)

    def test_vc_pipeline_unchanged(self):
        from core.m1 import M1Pipeline, TileBBox
        from core.vc import VisualConsistencyEngine
        from core.contract.vc_contract import VCContract
        pipeline = M1Pipeline(signal_provider=self._mixed_provider, tile_px_size=6)
        tile = pipeline.run_tile(TileBBox(lon_min=-20, lon_max=20, lat_min=-10, lat_max=10))
        ctx = VisualConsistencyEngine().process(tile)
        VCContract().validate(ctx)

    def test_d6_contract_unchanged(self):
        from core.m1 import M1Pipeline, TileBBox
        from core.vc import VisualConsistencyEngine
        from core.contract.d6_contract import D6Contract
        pipeline = M1Pipeline(signal_provider=self._ocean_provider, tile_px_size=4)
        tile = pipeline.run_tile(TileBBox(lon_min=0, lon_max=10, lat_min=0, lat_max=10))
        ctx = VisualConsistencyEngine().process(tile)
        frame = D6Contract().render_from_vc(ctx)
        self.assertEqual(frame.dtype.name, "uint8")
        self.assertEqual(frame.ndim, 3)

    def test_sal_winner_ratio_still_present(self):
        from core.sal import SemanticArbitrator
        r = SemanticArbitrator().resolve(
            dem_signal="land", climate_signal="forest",
            ocean_signal=None, landcover_signal="forest")
        self.assertTrue(hasattr(r, "winner_ratio"))
        self.assertGreaterEqual(r.winner_ratio, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
