"""
ClimateGroundingProvider — coarse latitude-band climate correction layer.

Provides a weak, deterministic climate bias derived only from latitude.
No file I/O, no MODIS/Köppen raster access, no numpy required.

This is a Stage 2 grounding provider: it approximates broad climate zones
as a correction bias against the synthetic prior, never replacing it.

Climate zone mapping:
    |lat| < 23  → 1  (tropical)
    |lat| < 45  → 2  (temperate)
    else        → 3  (polar / subpolar)

Constraints:
    - Same (lon, lat) → same output (fully deterministic)
    - No file I/O, no network, no raster, no numpy
    - SAL / M1 / VC logic is never modified by this layer
"""

from .base import BaseSignalProvider
from core.signal.signal_types import ClimateClass, DEMValue, LandcoverClass, OceanFlag


class ClimateGroundingProvider(BaseSignalProvider):
    """
    Coarse latitude-band climate grounding provider for Stage 2 hybrid mode.

    Only get_climate() carries grounding signal; the remaining methods return
    safe neutral defaults so this provider can stand alone without side effects.
    """

    def get_dem(self, lon: float, lat: float) -> DEMValue:
        return 0.0

    def get_landcover(self, lon: float, lat: float) -> LandcoverClass:
        return 0

    def get_climate(self, lon: float, lat: float) -> ClimateClass:
        abs_lat = abs(float(lat))
        if abs_lat < 23.0:
            return 1
        if abs_lat < 45.0:
            return 2
        return 3

    def get_ocean(self, lon: float, lat: float) -> OceanFlag:
        return False
