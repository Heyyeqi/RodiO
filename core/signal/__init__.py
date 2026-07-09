"""
core/signal — unified signal provider interface for RodiO geospatial pipeline.

All provider classes live in core/signal/providers/.
This module re-exports them at the top level for convenience and maintains
backward-compatible names for existing call sites.

Provider taxonomy (resolution priority):
    1. external injected provider  — user-supplied
    2. RuntimeStubProvider         — safe neutral defaults (no real data files)
    3. SyntheticProvider           — ambiguous fallback (M0 internal default)

Usage:
    from core.signal import BaseSignalProvider, RuntimeStubProvider
    from core.signal import SignalResolutionPolicy

    provider = RuntimeStubProvider()
    runtime = SpatialRuntime(signal_provider=provider)
"""

from .providers.base import BaseSignalProvider
from .providers.synthetic import SyntheticProvider
from .providers.runtime_stub import RuntimeStubProvider
from .providers.m1_bridge import M1BridgeProvider
from .providers.resolution_policy import SignalResolutionPolicy
from .signal_types import ClimateClass, DEMValue, LandcoverClass, OceanFlag

__all__ = [
    # Provider classes
    "BaseSignalProvider",
    "SyntheticProvider",
    "RuntimeStubProvider",
    "M1BridgeProvider",
    "SignalResolutionPolicy",
    # Type aliases
    "DEMValue",
    "LandcoverClass",
    "ClimateClass",
    "OceanFlag",
]
