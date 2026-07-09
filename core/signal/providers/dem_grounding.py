"""
DEMGroundingProvider — lightweight analytical DEM correction layer.

Provides a weak, deterministic elevation bias derived purely from (lon, lat)
arithmetic. No file I/O, no raster access, no numpy required.

This is a Stage 2 grounding provider: it adds a "reality shape" to the
synthetic prior without replacing it. Always used as a correction layer
blended at low weight (e.g. 0.2) against the synthetic primary signal.

Formula:
    base       = sin(lat * 0.01) * 1000   → smooth elevation field ±1000 m
    correction = cos(lon * 0.01) * 200    → longitudinal texture ±200 m
    result     = base + correction         → range approximately ±1200 m

Constraints:
    - Same (lon, lat) → same output (fully deterministic)
    - No file I/O, no network, no raster, no numpy
    - SAL / M1 / VC logic is never modified by this layer
"""

import math

from .base import BaseSignalProvider
from core.signal.signal_types import ClimateClass, DEMValue, LandcoverClass, OceanFlag


class DEMGroundingProvider(BaseSignalProvider):
    """
    Analytical DEM grounding provider for Stage 2 hybrid mode.

    Only get_dem() carries grounding signal; the remaining methods return
    safe neutral defaults so this provider can stand alone without side effects.
    """

    def get_dem(self, lon: float, lat: float) -> DEMValue:
        base = math.sin(float(lat) * 0.01) * 1000.0
        correction = math.cos(float(lon) * 0.01) * 200.0
        return base + correction

    def get_landcover(self, lon: float, lat: float) -> LandcoverClass:
        return 0

    def get_climate(self, lon: float, lat: float) -> ClimateClass:
        return None

    def get_ocean(self, lon: float, lat: float) -> OceanFlag:
        return False
