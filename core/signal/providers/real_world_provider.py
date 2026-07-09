"""
RealWorldSignalProvider — BaseSignalProvider backed by real Earth data.

Wraps EarthDataLoader to translate real raster values into the four primitive
signal types (DEM elevation, ocean flag, landcover class, climate class).

Fallback contract (Batch 6):
    Every get_*() method is fully wrapped in try/except. Any failure —
    missing file, out-of-bounds index, corrupt data, import error — returns
    the same safe neutral default as SyntheticProvider, never raises.

    Fallbacks:
        get_dem()       → 0.0  (sea level)
        get_landcover() → 0    (unknown)
        get_climate()   → None (no data)
        get_ocean()     → False (assume land)

Mode:
    mode="lazy" (default) — data is not loaded until the first call to any
    get_*() method. Subsequent calls use the in-memory object from EarthDataLoader.

SAL / M1 / VC / D6 are never touched by this class.
"""

from __future__ import annotations

from typing import Optional

from .base import BaseSignalProvider
from core.signal.signal_types import ClimateClass, DEMValue, LandcoverClass, OceanFlag


class RealWorldSignalProvider(BaseSignalProvider):
    """
    BaseSignalProvider that reads from real Earth data layers via EarthDataLoader.

    Args:
        source_root: passed directly to EarthDataLoader. None → project cache default.
        mode:        "lazy" (default) — layers loaded on first access.
    """

    def __init__(
        self,
        source_root=None,
        mode: str = "lazy",
        resolution_mode: str = "8k",
    ) -> None:
        self.mode = mode
        self.resolution_mode = resolution_mode
        self._loader = None
        self._source_root = source_root

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_loader(self):
        if self._loader is None:
            from core.data.earth_sources.loader import EarthDataLoader
            self._loader = EarthDataLoader(self._source_root)
            if hasattr(self._loader, "set_resolution"):
                self._loader.set_resolution(self.resolution_mode)
        return self._loader

    def _lookup(self, layer: str, lon: float, lat: float):
        """
        Return the raw layer value at (lon, lat), or None on any failure.

        This is the central safe-fallback dispatch. All get_*() methods call here.
        """
        try:
            obj = self._get_loader().load_layer(layer)
            if obj is None:
                return None
            # DEM Registry: query(lon, lat)
            if hasattr(obj, "query"):
                return obj.query(float(lon), float(lat))
            # GEBCOAdapter / GeoTiffDEMAdapter: get_value(lon, lat)
            if hasattr(obj, "get_value"):
                return obj.get_value(float(lon), float(lat))
            # RasterIndexer: sample(lon, lat)
            if hasattr(obj, "sample"):
                return obj.sample(float(lon), float(lat))
            return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # BaseSignalProvider protocol
    # ------------------------------------------------------------------

    def get_dem(self, lon: float, lat: float) -> DEMValue:
        """
        Return surface elevation in metres from real DEM (ETOPO1/Copernicus priority).
        Falls back to 0.0 on missing data or any error.
        """
        try:
            value = self._lookup("dem", lon, lat)
            if value is None:
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    def get_landcover(self, lon: float, lat: float) -> LandcoverClass:
        """
        Return landcover class from real data, or 0 (unknown) on missing data or error.
        """
        try:
            value = self._lookup("landcover", lon, lat)
            if value is None:
                return 0
            return int(value)
        except Exception:
            return 0

    def get_climate(self, lon: float, lat: float) -> ClimateClass:
        """
        Return Köppen-Geiger class from real data, or None on missing data or error.
        """
        try:
            value = self._lookup("climate", lon, lat)
            if value is None or int(value) <= 0:
                return None
            return int(value)
        except Exception:
            return None

    def get_ocean(self, lon: float, lat: float) -> OceanFlag:
        """
        Derive ocean flag from real DEM, with Köppen land-class veto.
        Falls back to False on missing data or any error.
        """
        try:
            climate = self.get_climate(lon, lat)
            if climate is not None and int(climate) > 0:
                return False
            elev = self.get_dem(lon, lat)
            return elev < 0.0
        except Exception:
            return False
