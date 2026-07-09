"""
core/signal/providers — unified signal provider registry.

Provider taxonomy (resolution priority):
    1. external injected provider  — user-supplied at construction time
    2. RuntimeStubProvider         — safe neutral defaults (no real data)
    3. SyntheticProvider           — ambiguous fallback (M0 internal)

Composite providers implement the BaseSignalProvider protocol. Single-layer
adapters such as GEBCOProvider / ETOPOProvider / KoppenProvider expose only
their layer-specific methods.
"""

from .base import BaseSignalProvider
from .synthetic import SyntheticProvider
from .runtime_stub import RuntimeStubProvider
from .m1_bridge import M1BridgeProvider
from .resolution_policy import SignalResolutionPolicy
from .dem_grounding import DEMGroundingProvider
from .climate_grounding import ClimateGroundingProvider
from .real_world_provider import RealWorldSignalProvider
from .gebco_provider import GEBCOProvider
from .etopo_provider import ETOPOProvider
from .koppen_provider import KoppenProvider
from .raster_backed_provider import RasterBackedProvider

__all__ = [
    "BaseSignalProvider",
    "SyntheticProvider",
    "RuntimeStubProvider",
    "M1BridgeProvider",
    "SignalResolutionPolicy",
    "DEMGroundingProvider",
    "ClimateGroundingProvider",
    "RealWorldSignalProvider",
    "GEBCOProvider",
    "ETOPOProvider",
    "KoppenProvider",
    "RasterBackedProvider",
]
