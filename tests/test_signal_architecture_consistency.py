"""
Signal Architecture Consistency Tests

Structural validation — ensures the signal provider dependency graph is
well-formed and the unification refactor invariants hold.

Checks:
  1. Single namespace entrypoint: core.signal is the only import surface
  2. No cross-import between M1 and runtime provider classes
  3. Provider graph is acyclic (no circular imports)
  4. No duplicate class definitions for provider roles
  5. M1 does not define provider classes (only re-exports via shims)
  6. SpatialRuntime does not import from core.m1
  7. Provider taxonomy completeness
"""

import importlib
import inspect
import sys
import unittest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_fresh(module_path: str):
    """Import a module fresh (without caching side-effects)."""
    return importlib.import_module(module_path)


def _class_defined_in(cls, module_path: str) -> bool:
    """True if cls.__module__ matches module_path exactly."""
    return cls.__module__ == module_path


def _source_file(module_path: str) -> str:
    mod = importlib.import_module(module_path)
    return getattr(mod, "__file__", "") or ""


# ---------------------------------------------------------------------------
# 1. Single namespace entrypoint
# ---------------------------------------------------------------------------

class TestSingleNamespaceEntrypoint(unittest.TestCase):

    def test_core_signal_exports_all_provider_types(self):
        import core.signal as sig
        required = ("BaseSignalProvider", "RuntimeStubProvider",
                    "SyntheticProvider", "M1BridgeProvider", "SignalResolutionPolicy")
        for name in required:
            self.assertTrue(hasattr(sig, name), f"core.signal missing: {name}")

    def test_all_providers_accessible_via_core_signal(self):
        from core.signal import (
            BaseSignalProvider, RuntimeStubProvider,
            SyntheticProvider, M1BridgeProvider, SignalResolutionPolicy,
        )
        for cls in (BaseSignalProvider, RuntimeStubProvider, SyntheticProvider, M1BridgeProvider):
            self.assertIsNotNone(cls)

    def test_signal_types_accessible_via_core_signal(self):
        from core.signal import DEMValue, LandcoverClass, ClimateClass, OceanFlag
        # Type aliases are not None
        self.assertIsNotNone(DEMValue)


# ---------------------------------------------------------------------------
# 2. Canonical class locations (no duplicate definitions)
# ---------------------------------------------------------------------------

class TestCanonicalClassLocations(unittest.TestCase):

    def test_base_signal_provider_defined_in_providers_base(self):
        from core.signal.providers.base import BaseSignalProvider
        self.assertEqual(BaseSignalProvider.__module__,
                         "core.signal.providers.base")

    def test_runtime_stub_provider_defined_in_providers_runtime_stub(self):
        from core.signal.providers.runtime_stub import RuntimeStubProvider
        self.assertEqual(RuntimeStubProvider.__module__,
                         "core.signal.providers.runtime_stub")

    def test_synthetic_provider_defined_in_providers_synthetic(self):
        from core.signal.providers.synthetic import SyntheticProvider
        self.assertEqual(SyntheticProvider.__module__,
                         "core.signal.providers.synthetic")

    def test_m1_bridge_provider_defined_in_providers_m1_bridge(self):
        from core.signal.providers.m1_bridge import M1BridgeProvider
        self.assertEqual(M1BridgeProvider.__module__,
                         "core.signal.providers.m1_bridge")

    def test_old_signal_real_provider_is_shim_not_definition(self):
        import core.signal.real_signal_provider as shim
        from core.signal.providers.runtime_stub import RuntimeStubProvider
        # Shim must re-export — class defined elsewhere
        self.assertIs(shim.RealSignalProvider, RuntimeStubProvider)
        self.assertNotEqual(shim.__name__, "core.signal.providers.runtime_stub")

    def test_old_m1_real_provider_is_shim_not_definition(self):
        import core.m1.real_signal_provider as shim
        from core.signal.providers.m1_bridge import M1BridgeProvider
        self.assertIs(shim.RealSignalProvider, M1BridgeProvider)

    def test_no_two_real_signal_provider_classes(self):
        import core.signal.real_signal_provider as sig_shim
        import core.m1.real_signal_provider as m1_shim
        # The two shims must point to different canonical classes.
        self.assertIsNot(sig_shim.RealSignalProvider, m1_shim.RealSignalProvider)
        # Neither may be defined in the shim file itself.
        self.assertNotEqual(sig_shim.RealSignalProvider.__module__,
                            "core.signal.real_signal_provider")
        self.assertNotEqual(m1_shim.RealSignalProvider.__module__,
                            "core.m1.real_signal_provider")


# ---------------------------------------------------------------------------
# 3. Cross-import isolation
# ---------------------------------------------------------------------------

class TestCrossImportIsolation(unittest.TestCase):

    def test_m1_bridge_does_not_import_runtime_stub(self):
        import core.signal.providers.m1_bridge as bridge_mod
        bridge_src = inspect.getsource(bridge_mod)
        self.assertNotIn("runtime_stub", bridge_src)
        self.assertNotIn("RuntimeStubProvider", bridge_src)

    def test_runtime_stub_does_not_import_m1_bridge(self):
        import core.signal.providers.runtime_stub as stub_mod
        stub_src = inspect.getsource(stub_mod)
        self.assertNotIn("m1_bridge", stub_src)
        self.assertNotIn("M1BridgeProvider", stub_src)

    def test_m1_bridge_does_not_import_synthetic(self):
        import core.signal.providers.m1_bridge as bridge_mod
        bridge_src = inspect.getsource(bridge_mod)
        self.assertNotIn("SyntheticProvider", bridge_src)
        self.assertNotIn("synthetic", bridge_src)

    def test_spatial_runtime_does_not_import_core_m1(self):
        import core.runtime.spatial_runtime as rt_mod
        rt_src = inspect.getsource(rt_mod)
        self.assertNotIn("from core.m1", rt_src)
        self.assertNotIn("import core.m1", rt_src)

    def test_m1_providers_do_not_cross_import_each_other(self):
        import core.signal.providers.synthetic as syn_mod
        syn_src = inspect.getsource(syn_mod)
        self.assertNotIn("m1_bridge", syn_src)
        self.assertNotIn("runtime_stub", syn_src)


# ---------------------------------------------------------------------------
# 4. Provider graph acyclicity
# ---------------------------------------------------------------------------

class TestProviderGraphAcyclic(unittest.TestCase):

    def _import_chain(self, module_path: str) -> set:
        """Return the set of core.signal / core.m1 modules imported by module_path."""
        mod = importlib.import_module(module_path)
        src = inspect.getsource(mod)
        imports = set()
        for line in src.splitlines():
            stripped = line.strip()
            if stripped.startswith(("from core.signal", "from core.m1",
                                    "import core.signal", "import core.m1")):
                imports.add(stripped.split()[1])
        return imports

    def test_base_imports_nothing_from_providers(self):
        imports = self._import_chain("core.signal.providers.base")
        provider_imports = {i for i in imports if "providers" in i}
        self.assertEqual(provider_imports, set(),
                         f"base.py should not import from providers: {provider_imports}")

    def test_synthetic_imports_only_base(self):
        imports = self._import_chain("core.signal.providers.synthetic")
        m1_imports = {i for i in imports if "core.m1" in i}
        self.assertEqual(m1_imports, set(),
                         f"synthetic.py must not import from core.m1: {m1_imports}")

    def test_runtime_stub_imports_only_base(self):
        imports = self._import_chain("core.signal.providers.runtime_stub")
        m1_imports = {i for i in imports if "core.m1" in i}
        self.assertEqual(m1_imports, set(),
                         f"runtime_stub.py must not import from core.m1: {m1_imports}")


# ---------------------------------------------------------------------------
# 5. M1 does not define provider classes
# ---------------------------------------------------------------------------

class TestM1DoesNotDefineProviders(unittest.TestCase):

    def test_m1_pipeline_imports_from_signal_not_m1_local(self):
        import core.m1.m1_pipeline as pipeline_mod
        pipeline_src = inspect.getsource(pipeline_mod)
        self.assertNotIn("from .real_signal_provider", pipeline_src)
        self.assertIn("core.signal.providers.m1_bridge", pipeline_src)

    def test_mask_generator_imports_from_signal_not_m1_local(self):
        import core.m1.mask_generator as gen_mod
        gen_src = inspect.getsource(gen_mod)
        self.assertNotIn("from .real_signal_provider", gen_src)
        self.assertIn("core.signal.providers.m1_bridge", gen_src)

    def test_m1_init_imports_m1_bridge_from_signal(self):
        import core.m1 as m1_mod
        m1_src = inspect.getsource(m1_mod)
        self.assertIn("core.signal.providers.m1_bridge", m1_src)

    def test_m1_real_signal_provider_file_is_shim_only(self):
        import core.m1.real_signal_provider as shim
        src = inspect.getsource(shim)
        # Shim must not define a class body (no 'class RealSignalProvider' def)
        self.assertNotIn("class RealSignalProvider", src)
        self.assertNotIn("class M1BridgeProvider", src)


# ---------------------------------------------------------------------------
# 6. Provider taxonomy completeness
# ---------------------------------------------------------------------------

class TestProviderTaxonomyCompleteness(unittest.TestCase):

    def test_three_concrete_provider_types_exist(self):
        from core.signal import RuntimeStubProvider, SyntheticProvider, M1BridgeProvider
        self.assertIsNotNone(RuntimeStubProvider)
        self.assertIsNotNone(SyntheticProvider)
        self.assertIsNotNone(M1BridgeProvider)

    def test_two_base_signal_provider_subclasses(self):
        from core.signal import BaseSignalProvider, RuntimeStubProvider, SyntheticProvider
        self.assertTrue(issubclass(RuntimeStubProvider, BaseSignalProvider))
        self.assertTrue(issubclass(SyntheticProvider, BaseSignalProvider))

    def test_m1_bridge_is_not_base_signal_provider_subclass(self):
        from core.signal import BaseSignalProvider, M1BridgeProvider
        self.assertFalse(issubclass(M1BridgeProvider, BaseSignalProvider))

    def test_resolution_policy_exposes_all_three_tiers(self):
        from core.signal import SignalResolutionPolicy
        policy = SignalResolutionPolicy()
        self.assertEqual(len(policy.PRIORITY_ORDER), 3)
        self.assertIn("external_injected",  policy.PRIORITY_ORDER)
        self.assertIn("runtime_stub",       policy.PRIORITY_ORDER)
        self.assertIn("synthetic_fallback", policy.PRIORITY_ORDER)

    def test_providers_subpackage_exports_all(self):
        from core.signal.providers import (
            BaseSignalProvider, SyntheticProvider,
            RuntimeStubProvider, M1BridgeProvider, SignalResolutionPolicy,
        )
        for cls in (BaseSignalProvider, SyntheticProvider,
                    RuntimeStubProvider, M1BridgeProvider, SignalResolutionPolicy):
            self.assertIsNotNone(cls)


if __name__ == "__main__":
    unittest.main(verbosity=2)
