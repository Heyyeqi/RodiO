"""
SyntheticProvider — fully synthetic signal provider using ambiguous defaults.

This is the canonical "default / fallback" provider that was previously
expressed as the _default_signal_provider lambda inside core/m1/mask_generator.py.
Moving it here makes the fallback explicit, named, and reusable.

Implements both BaseSignalProvider (raw values for SpatialRuntime) and
__call__ (SAL signal kwargs dict for M1Pipeline.signal_provider protocol)
so it can be used at either level of the pipeline.
"""

from .base import BaseSignalProvider
from core.signal.signal_types import ClimateClass, DEMValue, LandcoverClass, OceanFlag


class SyntheticProvider(BaseSignalProvider):
    """
    Fully synthetic provider — all values represent ambiguous, sea-level land.

    Implements the same neutral defaults that _default_signal_provider()
    produced inside MaskGenerator, now exposed as a named, importable class.

    Also callable as (lon, lat) → SAL signal kwargs dict so it can be
    passed directly as M1Pipeline(signal_provider=SyntheticProvider()).
    """

    # BaseSignalProvider protocol (raw values for SpatialRuntime)

    def get_dem(self, lon: float, lat: float) -> DEMValue:
        return 0.0

    def get_landcover(self, lon: float, lat: float) -> LandcoverClass:
        return 0

    def get_climate(self, lon: float, lat: float) -> ClimateClass:
        return None

    def get_ocean(self, lon: float, lat: float) -> OceanFlag:
        return False

    # M1Pipeline.signal_provider protocol (SAL signal kwargs dict)

    def __call__(self, lon: float, lat: float) -> dict:
        """Return SAL signal kwargs — equivalent to the old _default_signal_provider."""
        return dict(
            dem_signal="land",       dem_confidence=0.50,
            climate_signal="land",   climate_confidence=0.50,
            ocean_signal="land",     ocean_confidence=0.50,
            landcover_signal="land", landcover_confidence=0.50,
        )
