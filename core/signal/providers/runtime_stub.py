"""
RuntimeStubProvider — BaseSignalProvider for SpatialRuntime with optional lite grounding.

Two modes:

  enable_lite_grounding=False (default, v1 behaviour):
    All methods return safe, neutral defaults. Behaviour is identical to v1.
    No computation, no external data, pure determinism.

  enable_lite_grounding=True (v2-lite):
    Returns lightweight analytical proxies derived only from (lon, lat)
    arithmetic — no file I/O, no raster access, no numpy.
    Values are intentionally coarse; they add a "reality shape" to the
    prior without changing SAL/M1/VC decision logic.

    Proxies used:
      DEM:     sin(lat * 0.01) * 1000  — smooth elevation field ±1 km
      ocean:   abs(lat) > 60 and abs(lon) < 20  — polar / North-Atlantic hint
      climate: lat-band bucket (1=tropical, 2=temperate, 3=polar)

Constraints enforced:
  - Same (lon, lat) → same output in both modes (fully deterministic)
  - No file I/O, no network, no raster
  - No numpy or vectorisation
  - SAL / M1 / VC logic unchanged
"""

import math

from .base import BaseSignalProvider
from core.signal.signal_types import ClimateClass, DEMValue, LandcoverClass, OceanFlag


class RuntimeStubProvider(BaseSignalProvider):
    """
    BaseSignalProvider that can operate in stub mode or lite-grounding mode.

    Args:
        enable_lite_grounding: when True, analytical proxies replace neutral
                               defaults. Default False (v1-compatible).
    """

    def __init__(self, enable_lite_grounding: bool = False) -> None:
        self.enable_lite_grounding = enable_lite_grounding

    # ------------------------------------------------------------------
    # BaseSignalProvider protocol
    # ------------------------------------------------------------------

    def get_dem(self, lon: float, lat: float) -> DEMValue:
        """
        Stub:   0.0 (sea level)
        Lite:   sin(lat * 0.01) * 1000  — smooth proxy in range ±1000 m.
                Positive over mid-latitudes, near-zero at equator.
        """
        if not self.enable_lite_grounding:
            return 0.0
        return math.sin(float(lat) * 0.01) * 1000.0

    def get_landcover(self, lon: float, lat: float) -> LandcoverClass:
        """Always 0 (unknown). Lite grounding does not enrich landcover."""
        return 0

    def get_climate(self, lon: float, lat: float) -> ClimateClass:
        """
        Stub:   None
        Lite:   coarse lat-band bucket:
                  |lat| < 23 → 1  (tropical)
                  |lat| < 45 → 2  (temperate)
                  else       → 3  (polar / subpolar)
        """
        if not self.enable_lite_grounding:
            return None
        abs_lat = abs(float(lat))
        if abs_lat < 23.0:
            return 1
        if abs_lat < 45.0:
            return 2
        return 3

    def get_ocean(self, lon: float, lat: float) -> OceanFlag:
        """
        Stub:   False
        Lite:   True when abs(lat) > 60 and abs(lon) < 20
                (high-latitude North-Atlantic / Arctic proxy)
        """
        if not self.enable_lite_grounding:
            return False
        return abs(float(lat)) > 60.0 and abs(float(lon)) < 20.0
