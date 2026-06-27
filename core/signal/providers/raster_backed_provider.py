"""
RasterBackedProvider — BaseSignalProvider backed by real raster adapter trio.

Combines GEBCOProvider (ocean / bathy DEM), ETOPOProvider (land DEM fallback),
and KoppenProvider (climate class) into a single BaseSignalProvider that the
SpatialRuntime real_world_provider slot can consume.

DEM priority:
    GEBCO → ETOPO1 → 0.0 (sea level default)

Ocean arbitration:
    1. If Köppen returns a valid land class (≥ 1), the point is land regardless
       of DEM sign (handles Dead Sea / Death Valley / Caspian Depression).
    2. Otherwise: ocean = (DEM elevation < 0).

Landcover:
    Not available from this source set; always returns 0 (unknown).

All methods are safe: any exception returns the neutral default value.
SAL / M1 / VC / D6 are never referenced here.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .base import BaseSignalProvider
from core.signal.signal_types import ClimateClass, DEMValue, LandcoverClass, OceanFlag

if TYPE_CHECKING:
    from .gebco_provider import GEBCOProvider
    from .etopo_provider import ETOPOProvider
    from .koppen_provider import KoppenProvider


class RasterBackedProvider(BaseSignalProvider):
    """
    BaseSignalProvider assembled from three raster adapter providers.

    Any or all of gebco / etopo / koppen may be None — missing providers
    fall back to safe neutral defaults (0.0 / False / None / 0).

    Args:
        gebco:  GEBCOProvider for ocean / bathymetry DEM
        etopo:  ETOPOProvider for land / fallback DEM
        koppen: KoppenProvider for Köppen-Geiger climate class
    """

    def __init__(
        self,
        gebco: Optional["GEBCOProvider"] = None,
        etopo: Optional["ETOPOProvider"] = None,
        koppen: Optional["KoppenProvider"] = None,
    ) -> None:
        self._gebco = gebco
        self._etopo = etopo
        self._koppen = koppen

    # ------------------------------------------------------------------
    # BaseSignalProvider protocol
    # ------------------------------------------------------------------

    def get_dem(self, lon: float, lat: float) -> DEMValue:
        """
        Return elevation in metres. GEBCO has priority; ETOPO1 is the fallback.
        Returns 0.0 when neither source is available.
        """
        try:
            if self._gebco is not None:
                return float(self._gebco.get_dem(lon, lat))
            if self._etopo is not None:
                return float(self._etopo.get_dem(lon, lat))
        except Exception:
            pass
        return 0.0

    def get_landcover(self, lon: float, lat: float) -> LandcoverClass:
        """GEBCO / ETOPO1 / Köppen do not carry landcover data. Always returns 0."""
        return 0

    def get_climate(self, lon: float, lat: float) -> ClimateClass:
        """Return Köppen-Geiger class, or None when not available."""
        try:
            if self._koppen is not None:
                return self._koppen.get_climate(lon, lat)
        except Exception:
            pass
        return None

    def get_ocean(self, lon: float, lat: float) -> OceanFlag:
        """
        Return True for ocean pixels.

        Köppen land-class veto applies: any valid climate class (≥ 1) forces
        ocean = False regardless of DEM sign.
        """
        try:
            climate = self.get_climate(lon, lat)
            if climate is not None and int(climate) > 0:
                return False
            return self.get_dem(lon, lat) < 0.0
        except Exception:
            return False
