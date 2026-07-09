"""
GEBCOProvider — thin adapter exposing ocean and DEM queries from a GEBCO raster.

Wraps a RasterIndexer whose array contains GEBCO elevation/depth values
(metres, negative = below sea level, positive = above). No GDAL dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.signal.raster_indexer import RasterIndexer


class GEBCOProvider:
    """
    Adapter for a global GEBCO raster loaded as a RasterIndexer.

    Args:
        indexer: RasterIndexer wrapping the GEBCO array (values in metres).
    """

    def __init__(self, indexer: "RasterIndexer", resolution_mode: str = "8k") -> None:
        self.resolution_mode = resolution_mode
        self.indexer = _coerce_indexer(indexer, resolution_mode)

    def get_dem(self, lon: float, lat: float) -> float:
        """Return GEBCO elevation/depth in metres at (lon, lat). 0.0 on missing data."""
        value = self.indexer.sample(lon, lat)
        if value is None:
            return 0.0
        return float(value)

    def get_ocean(self, lon: float, lat: float) -> bool:
        """Return True when GEBCO depth is below 0 (open ocean / sub-ice)."""
        return self.get_dem(lon, lat) < 0.0


def _coerce_indexer(indexer, resolution_mode: str):
    if hasattr(indexer, "sample"):
        return indexer
    from core.signal.raster_indexer import RasterIndexer
    return RasterIndexer(indexer, resolution_mode=resolution_mode)
